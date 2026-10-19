"""The LLM adapter (B3, docs/decisions.md 2026-09-27; llm-adapter 2/4 to 4/4).

A shell that owns the cost gate, retry and settlement, around a swappable
provider that owns the vendor call and its pricing. Callers never pass a DB
session:

- Gate: before every call, cost_meter.assert_within_caps (user cap plus the
  global ceiling) runs in the adapter's own short session. A refusal raises
  CostCapExceeded; a failing spend read propagates. Either way the model is
  not called. A Meter without a user skips the gate and the ledger, and so
  does the stub provider, which never spends.
- Providers: LiteLlmProvider in production; StubProvider whenever stub mode
  is on (get() is the only reader of settings.llm_stub_enabled). The stub
  refuses completions and embeddings with LlmUnavailable, a CallRefused that
  is not a cap; callers fall back as they would without a model.
- Settlement: after each attempt that cost something, one short session
  writes the ledger upsert and the LlmCallLog row and commits, so spend is
  permanent whatever the caller's transaction does next. It never raises. If
  that fails, the LlmCallLog row is written on its own and the ledger write
  is retried once off the request path (see _defer_ledger). Every deferral
  logs at error level with what reconciliation needs, so spend whose retry
  never lands (a failed retry, a restart before it runs) is always on record.
- Failed attempts: a Timeout settles the provider's prompt-token estimate (a
  non-streamed call has no output to add); a 429, 503, 500 or connection
  error settles $0, since the provider never processed the prompt.
- Retry: 429, 503, 500 and connection errors retry with backoff
  (llm_retry_attempts, llm_retry_base_delay_s). Timeout retries for
  embeddings only, never completions.
- Streams (stream(), the tutor): the gate runs on entering the block, retry
  only before any chunk arrives, and the block's exit settles once -- see
  LlmStream for the per-exit rule.

Invariant for callers: no uncommitted ledger write in the caller's session
across a call. Settlement upserts the same ledger row and would wait on it;
lock_timeout (SETTLE_LOCK_TIMEOUT) bounds that wait, then the ledger write
is deferred to the retry instead of hanging the request.
"""

import asyncio
import logging
import threading
import time
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol, TypeVar

import litellm
import sqlalchemy.exc
from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool

from agent import _stub
from config import settings
from db.database import SessionLocal
from lib.llm_errors import CallRefused, LlmUnavailable
from services import cost_meter

__all__ = [
    "CallRefused",
    "Completion",
    "Embedding",
    "LiteLlmProvider",
    "Llm",
    "LlmStream",
    "LlmUnavailable",
    "Meter",
    "StubProvider",
    "TextDelta",
    "ToolCall",
    "get",
]

log = logging.getLogger(__name__)

T = TypeVar("T")

# Settlement waits at most this long for the ledger row lock, then defers the
# ledger write. Every LLM spend settles through this adapter in a short
# transaction of its own, and the chat route's turn reservation is published by
# its admission commit, so a legitimate wait is a single short transaction.
SETTLE_LOCK_TIMEOUT = "5s"
# The deferred ledger write runs once, this long after the failed settlement,
# on a background thread; no request waits on it, so it may wait longer for
# the row lock.
SETTLE_RETRY_DELAY_S = 5.0
SETTLE_RETRY_LOCK_TIMEOUT = "30s"
# Each waiting retry holds a pooled connection. At most this many wait at once
# per process; past that the spend is logged as unsettled rather than letting
# a stuck ledger row starve the request pool.
SETTLE_RETRY_MAX_IN_FLIGHT = 2
_retry_slots = threading.BoundedSemaphore(SETTLE_RETRY_MAX_IN_FLIGHT)

_RETRYABLE: tuple[type[BaseException], ...] = (
    litellm.APIConnectionError,
    litellm.ServiceUnavailableError,
    litellm.InternalServerError,
    litellm.RateLimitError,
)


@dataclass(frozen=True)
class Meter:
    """Who a call is billed to, and why (LlmCallLog.purpose)."""

    user_id: str | None
    session_id: str | None
    purpose: str


@dataclass(frozen=True)
class Completion:
    text: str
    cost: Decimal
    usage: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Embedding:
    vectors: list[list[float]]
    cost: Decimal
    usage: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class ToolCall:
    """One assembled tool call. `arguments` is the raw JSON string the model
    streamed; the caller parses it (and handles a malformed one)."""

    id: str | None
    name: str | None
    arguments: str


class ProviderStream(Protocol):
    """One open streamed completion, as the provider hands it to the shell.

    Iterating yields text tokens. `received` turns true on the first chunk of
    any kind; `text` and `tool_calls` accumulate as chunks arrive."""

    received: bool
    text: str

    @property
    def tool_calls(self) -> list[ToolCall]:
        """The tool calls assembled so far, in index order."""

    def __aiter__(self) -> AsyncIterator[str]:
        """The text tokens, as they arrive."""

    def priced(self) -> tuple[Decimal, dict]:
        """(cost, usage) of the finished stream. Never raises."""

    def estimate(self) -> Decimal:
        """Prompt plus the output received so far (text and tool-call
        arguments), by token math. Never raises."""

    async def aclose(self) -> None:
        """Release the underlying response."""


class Provider(Protocol):
    """The vendor call and its pricing. Never touches the database."""

    @property
    def chat_model(self) -> str:
        """Model name recorded on completion call log rows."""

    @property
    def embedding_model(self) -> str:
        """Model name recorded on embedding call log rows."""

    async def complete(
        self, messages: list[dict], *, temperature: float, timeout: float
    ) -> Completion:
        """One non-streamed chat completion, priced."""

    async def stream(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None,
        tool_choice: str | None,
        temperature: float,
        timeout: float,
    ) -> ProviderStream:
        """Open one streamed chat completion."""

    def embed(self, texts: list[str]) -> Embedding:
        """One embedding batch, priced."""

    async def aembed(self, texts: list[str]) -> Embedding:
        """Async form of embed."""

    def completion_prompt_cost(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> Decimal:
        """Estimated prompt cost of a completion sent with `tools`. Never raises."""

    def embedding_prompt_cost(self, texts: list[str]) -> Decimal:
        """Estimated prompt cost of an embedding batch. Never raises."""


def _to_decimal(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v or 0))


def _prompt_tokens(messages: list[dict], tools: list | None) -> int:
    """Prompt tokens of the chat model for `messages` sent with `tools`.
    litellm's tool formatter skips `$defs` and `$ref`, so the count errs low:
    it puts the tutor's tools at about 1.1k tokens, their JSON at 2.7k. A schema it cannot
    format at all drops the tools from the count rather than the whole count."""
    try:
        return litellm.token_counter(model=settings.model, messages=messages, tools=tools)
    except Exception as e:  # noqa: BLE001 - an estimate must not raise
        if tools is None:
            raise
        log.warning("tool schema count failed: %s", e)
        return litellm.token_counter(model=settings.model, messages=messages)


class LiteLlmProvider:
    """The production provider. Calls through the `litellm` module attribute
    (never `from litellm import ...`) so global patches keep intercepting."""

    @property
    def chat_model(self) -> str:
        return settings.model

    @property
    def embedding_model(self) -> str:
        return settings.embedding_model

    async def complete(self, messages, *, temperature, timeout) -> Completion:
        resp = await litellm.acompletion(
            model=settings.model,
            temperature=temperature,
            messages=messages,
            timeout=timeout,
        )
        content = resp.choices[0].message.content or ""
        return Completion(
            text=content,
            cost=self._completion_cost(resp, messages, content),
            usage=cost_meter.extract_usage(resp),
        )

    def _completion_cost(
        self, resp, messages, content: str, tools: list[dict] | None = None
    ) -> Decimal:
        """litellm's price over the response usage, at the MODEL_RATES we
        registered; on failure, the response's usage at those rates, else
        token math over the prompt, its `tools` and the reply. Never raises."""
        if cost_meter.register_rates(settings.model):
            try:
                # model= supplies the provider prefix: Gemini responses carry
                # the bare name, which resolves to a different (unregistered)
                # entry.
                return _to_decimal(
                    litellm.completion_cost(completion_response=resp, model=settings.model)
                )
            except Exception as e:  # noqa: BLE001 - pricing must not fail the call
                log.warning("completion_cost failed: %s", e)
        # Unregistered, litellm's map may hold an old price; usage keeps the
        # thinking and tool-call tokens that token math over the text misses.
        try:
            cost = cost_meter.usage_cost(settings.model, cost_meter.extract_usage(resp))
        except Exception as e:  # noqa: BLE001
            log.warning("usage cost failed: %s", e)
            cost = None
        return cost if cost is not None else self._token_math(messages, content, tools)

    def _token_math(self, messages, content: str, tools: list[dict] | None = None) -> Decimal:
        """Prompt tokens, the tool schemas included (#628), plus `content`
        priced at the chat model's rates. Never raises."""
        try:
            pt = _prompt_tokens(messages, tools)
            return cost_meter.estimate_cancelled_cost(settings.model, content, pt)
        except Exception as e:  # noqa: BLE001 - an estimate must not raise
            # Local tokenization only; no credential in the exception.
            # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
            log.warning("completion token-math estimate failed: %s", e)
            return Decimal("0")

    async def stream(self, messages, *, tools, tool_choice, temperature, timeout):
        kwargs = {}
        if tools is not None:
            kwargs = {"tools": tools, "tool_choice": tool_choice}
        resp = await litellm.acompletion(
            model=settings.model,
            temperature=temperature,
            messages=messages,
            stream=True,
            timeout=timeout,
            **kwargs,
        )
        return _LiteLlmStream(self, resp, messages, tools)

    def _embedding(self, resp, texts: list[str]) -> Embedding:
        vectors = [d["embedding"] if isinstance(d, dict) else d.embedding for d in resp.data]
        return Embedding(
            vectors=vectors,
            cost=cost_meter.embedding_cost(settings.embedding_model, resp, texts),
            usage=cost_meter.extract_usage(resp),
        )

    def embed(self, texts) -> Embedding:
        resp = litellm.embedding(
            model=settings.embedding_model,
            input=list(texts),
            dimensions=settings.embedding_dim,
            timeout=settings.embedding_timeout_s,
        )
        return self._embedding(resp, texts)

    async def aembed(self, texts) -> Embedding:
        resp = await litellm.aembedding(
            model=settings.embedding_model,
            input=list(texts),
            dimensions=settings.embedding_dim,
            timeout=settings.embedding_timeout_s,
        )
        return self._embedding(resp, texts)

    def completion_prompt_cost(self, messages, tools=None) -> Decimal:
        return self._token_math(messages, "", tools)

    def embedding_prompt_cost(self, texts) -> Decimal:
        model = settings.embedding_model
        try:
            pt = sum(litellm.token_counter(model=model, text=t or "") for t in texts)
            return cost_meter.estimate_cancelled_cost(model, "", pt)
        except Exception as e:  # noqa: BLE001
            log.warning("embedding prompt estimate failed: %s", e)
            return Decimal("0")


class _LiteLlmStream:
    """litellm's streamed chunks, reduced to text tokens plus assembled tool
    calls. Pricing reads the kept chunks back through stream_chunk_builder."""

    def __init__(
        self, provider: LiteLlmProvider, resp, messages: list[dict], tools: list[dict] | None
    ):
        self._provider = provider
        self._resp = resp
        self._messages = messages
        self._tools = tools
        self._chunks: list = []
        self._frags: dict[int, dict] = {}
        self.received = False
        self.text = ""

    async def __aiter__(self):
        async for chunk in self._resp:
            self.received = True
            self._chunks.append(chunk)
            delta = chunk.choices[0].delta
            for tcd in getattr(delta, "tool_calls", None) or []:
                slot = self._frags.setdefault(
                    getattr(tcd, "index", 0), {"id": None, "name": None, "args": ""}
                )
                if getattr(tcd, "id", None):
                    slot["id"] = tcd.id
                fn = getattr(tcd, "function", None)
                if fn is not None:
                    if getattr(fn, "name", None):
                        slot["name"] = fn.name
                    if getattr(fn, "arguments", None):
                        slot["args"] += fn.arguments
            token = getattr(delta, "content", None)
            if token:
                self.text += token
                yield token

    @property
    def tool_calls(self) -> list[ToolCall]:
        return [
            ToolCall(id=s["id"], name=s["name"], arguments=s["args"])
            for _, s in sorted(self._frags.items())
        ]

    def priced(self) -> tuple[Decimal, dict]:
        try:
            # Without usage in the chunks, litellm counts the prompt itself;
            # this count keeps the tool schemas in it (#628).
            built = litellm.stream_chunk_builder(
                self._chunks,
                messages=self._messages,
                count_prompt_tokens=lambda: _prompt_tokens(self._messages, self._tools),
            )
        except Exception as e:  # noqa: BLE001 - pricing must not fail the call
            log.warning("stream_chunk_builder failed: %s", e)
            return self.estimate(), {}
        # F-19: a pricing-table gap falls back to token math, never $0.
        return (
            self._provider._completion_cost(built, self._messages, self._output(), self._tools),
            cost_meter.extract_usage(built),
        )

    def _output(self) -> str:
        # Tool-call arguments received so far are billed output too.
        return self.text + "".join(slot["args"] for slot in self._frags.values())

    def estimate(self) -> Decimal:
        return self._provider._token_math(self._messages, self._output(), self._tools)

    async def aclose(self) -> None:
        close = getattr(self._resp, "aclose", None)
        if close is not None:
            await close()


class StubProvider:
    """Stub mode (`settings.llm_stub_enabled`): never touches the network.
    The tutor's stream echoes the learner deterministically (agent/_stub.py)
    with no tool calls at cost 0; completions and embeddings raise
    LlmUnavailable, and each caller falls back as it would without a model."""

    chat_model = "stub"
    embedding_model = "stub"

    async def complete(self, messages, *, temperature, timeout) -> Completion:
        raise LlmUnavailable()

    async def stream(self, messages, *, tools, tool_choice, temperature, timeout):
        system_prompt = next(
            (m.get("content") or "" for m in messages if m.get("role") == "system"), ""
        )
        return _StubStream(_chunk_text(_stub.stub_response(messages, system_prompt)))

    def embed(self, texts) -> Embedding:
        raise LlmUnavailable()

    async def aembed(self, texts) -> Embedding:
        raise LlmUnavailable()

    def completion_prompt_cost(self, messages, tools=None) -> Decimal:
        return Decimal("0")

    def embedding_prompt_cost(self, texts) -> Decimal:
        return Decimal("0")


def _chunk_text(text: str, parts: int = 3) -> list[str]:
    """Split text into ~`parts` word-boundary chunks, so stub streaming still
    exercises the delta path."""
    words = text.split(" ")
    if len(words) <= 1:
        return [text]
    parts = max(1, min(parts, len(words)))
    size = -(-len(words) // parts)  # ceil division
    out: list[str] = []
    for i in range(0, len(words), size):
        group = words[i : i + size]
        sep = " " if (i + size) < len(words) else ""
        out.append(" ".join(group) + sep)
    return out


class _StubStream:
    def __init__(self, tokens: list[str]):
        self._tokens = tokens
        self.received = False
        self.text = ""

    @property
    def tool_calls(self) -> list[ToolCall]:
        return []

    async def __aiter__(self):
        for token in self._tokens:
            self.received = True
            self.text += token
            yield token

    def priced(self) -> tuple[Decimal, dict]:
        return Decimal("0"), {}

    def estimate(self) -> Decimal:
        return Decimal("0")

    async def aclose(self) -> None:
        return None


def _gate(meter: Meter, provider: Provider) -> None:
    if meter.user_id is None or isinstance(provider, StubProvider):
        return
    with SessionLocal() as db:
        cost_meter.assert_within_caps(db, meter.user_id)


def _lock_timeout(db, timeout: str) -> None:
    if db.get_bind().dialect.name == "postgresql":
        # SET LOCAL via set_config: bind-safe, scoped to this transaction.
        db.execute(select(func.set_config("lock_timeout", timeout, True)))


def _log_call(db, meter: Meter, model: str, cost: Decimal, usage: dict) -> bool:
    return cost_meter.log_call(
        db,
        user_id=meter.user_id,
        session_id=meter.session_id,
        purpose=meter.purpose,
        model=model,
        cost_usd=cost,
        **usage,
    )


def _schedule(delay: float, fn: Callable[..., None], *args) -> None:
    """Run fn(*args) once after `delay` seconds on a daemon thread. Tests
    replace this to run the retry inline."""
    timer = threading.Timer(delay, fn, args)
    timer.daemon = True
    timer.start()


def _settle(meter: Meter, model: str, cost: Decimal, usage: dict) -> None:
    if meter.user_id is None or cost <= 0:
        return
    reconciliation = {
        "user_id": meter.user_id,
        "session_id": meter.session_id,
        "purpose": meter.purpose,
        "model": model,
        "cost_usd": str(cost),
        "usage": usage,
    }
    try:
        with SessionLocal() as db:
            _lock_timeout(db, SETTLE_LOCK_TIMEOUT)
            cost_meter.record_cost(db, meter.user_id, cost)
            logged = _log_call(db, meter, model, cost, usage)
            db.commit()
    except Exception as e:  # noqa: BLE001 - settlement never fails the call
        _defer_ledger(meter, model, cost, usage, reconciliation, e)
        return
    if not logged:
        # The ledger committed; only the attribution row was lost.
        log.error("llm call log row lost", extra=reconciliation)


def _defer_ledger(
    meter: Meter, model: str, cost: Decimal, usage: dict, reconciliation: dict, exc: Exception
) -> None:
    """The settlement failed. Keep the LlmCallLog row now (it never waits on
    the ledger row lock), then retry the ledger write once in the background,
    booked to today's row as of now, so a held lock delays the spend instead
    of losing it.

    The deferral itself logs at error level: it is the reconciliation record
    if the retry never lands (a restart before it runs, or it fails too).
    "llm deferred settlement landed" at info level closes it. Normally the
    failed settlement rolled back whole; a connection lost mid-COMMIT can leave
    it committed, and then the retry counts the spend twice -- the safe
    direction, since an overcount only shortens the user's own budget."""
    day = cost_meter._today_utc()
    logged = False
    # A pool timeout means no connection is free: don't queue a second
    # checkout on the request path; the retry writes the row instead.
    if not isinstance(exc, sqlalchemy.exc.TimeoutError):
        try:
            with SessionLocal() as db:
                logged = _log_call(db, meter, model, cost, usage)
                db.commit()
        except Exception:  # noqa: BLE001 - the retry writes the row instead
            logged = False
    reconciliation = {**reconciliation, "call_logged": logged, "date_utc": day}
    if not _retry_slots.acquire(blocking=False):
        log.error(
            "llm settlement failed: retry capacity full, first error: %s", exc, extra=reconciliation
        )
        return
    log.error("llm settlement deferred: %s", exc, extra=reconciliation)
    _schedule(SETTLE_RETRY_DELAY_S, _retry_ledger, meter, model, cost, usage, reconciliation)


def _retry_ledger(
    meter: Meter, model: str, cost: Decimal, usage: dict, reconciliation: dict
) -> None:
    try:
        with SessionLocal() as db:
            _lock_timeout(db, SETTLE_RETRY_LOCK_TIMEOUT)
            cost_meter.record_cost(db, meter.user_id, cost, date_utc=reconciliation["date_utc"])
            if not reconciliation["call_logged"]:
                reconciliation = {
                    **reconciliation,
                    "call_logged": _log_call(db, meter, model, cost, usage),
                }
            db.commit()
    except Exception as e:  # noqa: BLE001 - background thread; nothing to raise into
        log.error("llm settlement failed: %s", e, extra=reconciliation)
        return
    finally:
        _retry_slots.release()
    log.info("llm deferred settlement landed", extra=reconciliation)


def _failed_attempt(exc: Exception, *, retry_timeout: bool) -> tuple[bool, bool]:
    """(retry?, settle a prompt estimate?) for a failed attempt."""
    if isinstance(exc, litellm.Timeout):
        return retry_timeout, True
    return isinstance(exc, _RETRYABLE), False


def _backoff(i: int) -> float:
    return max(0.0, settings.llm_retry_base_delay_s) * (2**i)


async def _close_quietly(ps: ProviderStream) -> None:
    try:
        await ps.aclose()
    except Exception as e:  # noqa: BLE001 - closing never masks the caller's path
        log.warning("closing the llm stream failed: %s", e)


class LlmStream:
    """One streamed completion: `async with llm.get().stream(...) as s`.

    Entering runs the gate. Iterating yields TextDelta events; `s.text` and
    `s.tool_calls` are complete once the iteration ends. Leaving the block
    settles exactly once, and `s.cost` holds what was settled:

    - normal end: the provider's price of the built response (token math if
      pricing fails);
    - a provider error: an estimate of the prompt plus the output received if
      any chunk arrived or the error was a Timeout, otherwise $0;
    - any other exit (cancellation, the caller's generator closed, an error in
      the caller's block): always the estimate.

    A 429, 503, 500 or connection error before any chunk arrives retries with
    backoff; a failed attempt with nothing received costs nothing, and its
    stream (if it opened) is closed. Timeout is never retried.
    """

    def __init__(
        self,
        provider: Provider,
        messages: list[dict],
        *,
        meter: Meter,
        tools: list[dict] | None,
        tool_choice: str | None,
        temperature: float,
        timeout: float,
    ):
        self._provider = provider
        self._messages = messages
        self._meter = meter
        self._open_kwargs = {
            "tools": tools,
            "tool_choice": tool_choice,
            "temperature": temperature,
            "timeout": timeout,
        }
        self._ps: ProviderStream | None = None
        self._gen: AsyncGenerator[TextDelta, None] | None = None
        # True while an attempt's request may be in flight or answered.
        self._attempt_open = False
        self._finished = False
        self._provider_error: Exception | None = None
        self.cost: Decimal | None = None

    @property
    def text(self) -> str:
        return self._ps.text if self._ps is not None else ""

    @property
    def tool_calls(self) -> list[ToolCall]:
        return self._ps.tool_calls if self._ps is not None else []

    async def __aenter__(self) -> "LlmStream":
        await run_in_threadpool(_gate, self._meter, self._provider)
        return self

    def __aiter__(self) -> AsyncIterator[TextDelta]:
        self._gen = self._events()
        return self._gen

    async def _events(self) -> AsyncGenerator[TextDelta, None]:
        attempts = max(0, settings.llm_retry_attempts)
        for i in range(attempts + 1):
            try:
                self._attempt_open = True
                self._ps = await self._provider.stream(self._messages, **self._open_kwargs)
                async for token in self._ps:
                    yield TextDelta(token)
                self._finished = True
                return
            except Exception as e:
                ps = self._ps
                received = ps is not None and ps.received
                retry, _ = _failed_attempt(e, retry_timeout=False)
                if received or not retry or i == attempts:
                    self._provider_error = e
                    raise
                # Nothing received: this attempt cost nothing, and until the
                # next opens no request is in flight.
                self._attempt_open = False
                self._ps = None
                if ps is not None:
                    await _close_quietly(ps)
            await asyncio.sleep(_backoff(i))

    def _exit_cost(self) -> tuple[Decimal, dict]:
        ps = self._ps
        if self._finished and ps is not None:
            return ps.priced()
        if not self._attempt_open:
            return Decimal("0"), {}
        err = self._provider_error
        if err is not None and not (
            isinstance(err, litellm.Timeout) or (ps is not None and ps.received)
        ):
            return Decimal("0"), {}
        if ps is None:
            # The request went out but no stream object came back yet.
            return (
                self._provider.completion_prompt_cost(self._messages, self._open_kwargs["tools"]),
                {},
            )
        return ps.estimate(), {}

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        # Settle before any await: a second cancellation cannot interrupt a
        # synchronous write, so the spend is on record whatever happens next.
        cost, usage = self._exit_cost()
        _settle(self._meter, self._provider.chat_model, cost, usage)
        self.cost = cost
        try:
            if self._gen is not None:
                await self._gen.aclose()
            if self._ps is not None:
                await self._ps.aclose()
        except Exception as e:  # noqa: BLE001 - closing never masks the exit
            log.warning("closing the llm stream failed: %s", e)
        return False


class Llm:
    def __init__(self, provider: Provider):
        self.provider = provider

    def stream(
        self,
        messages: list[dict],
        *,
        meter: Meter,
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        temperature: float,
        timeout: float,
    ) -> LlmStream:
        return LlmStream(
            self.provider,
            messages,
            meter=meter,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            timeout=timeout,
        )

    def _run_sync(
        self,
        call: Callable[[], T],
        *,
        meter: Meter,
        model: str,
        estimate: Callable[[], Decimal],
        retry_timeout: bool,
    ) -> T:
        attempts = max(0, settings.llm_retry_attempts)
        for i in range(attempts + 1):
            try:
                return call()
            except Exception as e:
                retry, estimated = _failed_attempt(e, retry_timeout=retry_timeout)
                if estimated:
                    _settle(meter, model, estimate(), {})
                if not retry or i == attempts:
                    raise
            time.sleep(_backoff(i))
        raise RuntimeError("unreachable: retry loop exited without returning or raising")

    async def _run_async(
        self,
        call: Callable[[], Awaitable[T]],
        *,
        meter: Meter,
        model: str,
        estimate: Callable[[], Decimal],
        retry_timeout: bool,
    ) -> T:
        attempts = max(0, settings.llm_retry_attempts)
        for i in range(attempts + 1):
            try:
                return await call()
            except Exception as e:
                retry, estimated = _failed_attempt(e, retry_timeout=retry_timeout)
                if estimated:
                    # The estimate tokenizes the prompt: keep it off the loop.
                    await run_in_threadpool(lambda: _settle(meter, model, estimate(), {}))
                if not retry or i == attempts:
                    raise
            await asyncio.sleep(_backoff(i))
        raise RuntimeError("unreachable: retry loop exited without returning or raising")

    async def complete(
        self, messages: list[dict], *, meter: Meter, temperature: float, timeout: float
    ) -> Completion:
        await run_in_threadpool(_gate, meter, self.provider)
        model = self.provider.chat_model
        result = await self._run_async(
            lambda: self.provider.complete(messages, temperature=temperature, timeout=timeout),
            meter=meter,
            model=model,
            estimate=lambda: self.provider.completion_prompt_cost(messages),
            retry_timeout=False,
        )
        await run_in_threadpool(_settle, meter, model, result.cost, result.usage)
        return result

    def embed(self, texts: list[str], *, meter: Meter) -> Embedding:
        _gate(meter, self.provider)
        model = self.provider.embedding_model
        result = self._run_sync(
            lambda: self.provider.embed(texts),
            meter=meter,
            model=model,
            estimate=lambda: self.provider.embedding_prompt_cost(texts),
            retry_timeout=True,
        )
        _settle(meter, model, result.cost, result.usage)
        return result

    async def aembed(self, texts: list[str], *, meter: Meter) -> Embedding:
        await run_in_threadpool(_gate, meter, self.provider)
        model = self.provider.embedding_model
        result = await self._run_async(
            lambda: self.provider.aembed(texts),
            meter=meter,
            model=model,
            estimate=lambda: self.provider.embedding_prompt_cost(texts),
            retry_timeout=True,
        )
        await run_in_threadpool(_settle, meter, model, result.cost, result.usage)
        return result


# The installed provider; None means LiteLlmProvider. Tests install a fake.
_provider: Provider | None = None


def get() -> Llm:
    """The active adapter. Resolved per call, not once at startup, so a
    per-test settings toggle takes effect. Stub mode wins over any installed
    provider; this is the only reader of `llm_stub_enabled` (#413)."""
    if settings.llm_stub_enabled:
        return Llm(StubProvider())
    return Llm(_provider or LiteLlmProvider())
