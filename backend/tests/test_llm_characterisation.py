"""#410: characterisation tests for every LLM call path (llm-adapter 1/4).

Pins what each exit path does TODAY -- the SSE event sequence, the persisted
assistant message status, the daily ledger total and the LlmCallLog rows --
so the adapter refactor (#411-#413) is checked against observed behaviour.

Every fake is installed on the GLOBAL `litellm` module (never a module-scoped
path such as "agent.tutor.litellm.acompletion"): the adapter still calls
`litellm`, so these tests keep running unmodified through the refactor.
Rows whose expected values a later part changes on purpose carry a comment
naming that part.
"""

import asyncio
import contextlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import litellm
import pytest
from sqlalchemy import func, select

from agent import tools, tutor
from agent.types import ToolContext
from config import settings
from contracts import TopicProfile
from db.models import ChatMessage, DailyCostLedger, Document, LlmCallLog, User
from db.models import Session as SessionModel
from lib import chunking, keyword_index
from services import (
    cost_meter,
    ingestion_service,
    pgvector_store,
    profile_service,
    summary_service,
)

USER_ID = "char-u1"
SESSION_ID = "char-s1"
MODEL = "gemini/gemini-3.5-flash-lite"

EMBEDDING_MODEL = "gemini/gemini-embedding-2"

# token_counter fake: every prompt snapshot counts PROMPT_TOKENS, streamed
# text TOKENS_PER_WORD per word, so the estimate shows WHICH text was billed.
# MODEL's rates are $0.30 / $2.50 per 1M tokens.
PROMPT_TOKENS = 1000
TOKENS_PER_WORD = 200
FIRST_TEXT = "Let me note that. "  # iteration 1, billed at its real price
TAIL_TEXT = "partial answer "  # iteration 2, cut short
# Cancel bills the cut-short call's own prompt plus the 2 words it streamed:
# (1000 * 0.0003 + 400 * 0.0025) / 1000.
CANCEL_TAIL_ESTIMATE = Decimal("0.0013")
# Changed by #412: an error bills only the failed call, the same math as the
# cancel (one prompt plus the 2 words it streamed); it used to re-estimate the
# whole turn, both snapshots plus all 6 words, $0.0036.
ERROR_CALL_ESTIMATE = CANCEL_TAIL_ESTIMATE

PROFILE_PATCH = {"add_confirmed_gap": "joins", "evidence_type": "declared"}


# ---------------------------------------------------------------------------
# litellm-shaped fakes (kept in this file on purpose; #412 exempts it)
# ---------------------------------------------------------------------------


def _chunk(content=None, tool_calls=None) -> SimpleNamespace:
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _text_chunk(token: str) -> SimpleNamespace:
    return _chunk(content=token)


def _tool_chunk(call_id: str, name: str, args: dict) -> SimpleNamespace:
    fn = SimpleNamespace(arguments=json.dumps(args))
    fn.name = name
    frag = SimpleNamespace(index=0, id=call_id, function=fn)
    return _chunk(tool_calls=[frag])


async def _litellm_stream(*chunks, block: asyncio.Event | None = None, error=None):
    """What `await litellm.acompletion(stream=True)` resolves to: an async
    iterator of chunks. `block` parks the stream after the chunks (a cancel
    lands there); `error` raises after them (a provider failure mid-stream)."""
    for c in chunks:
        yield c
    if block is not None:
        await block.wait()
    if error is not None:
        raise error


def _completion(content: str) -> SimpleNamespace:
    """A non-streamed acompletion response (the summaries)."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))], usage=None
    )


class FakeLitellm:
    """Scriptable stand-in for the litellm calls the app makes.

    `responses` feeds acompletion in order; `costs` feeds completion_cost in
    order (one entry per priced call, chat or embedding). An unscripted call
    is recorded in `unexpected` as well as raised: production code catches
    the AssertionError and falls back, so the fixture checks the record.
    """

    def __init__(self, monkeypatch):
        self.responses: list = []
        self.costs: list[float] = []
        self.acompletion_calls: list[dict] = []
        # Sync (threadpool) and async (event-loop) embeds kept apart.
        self.embedding_calls: list[list[str]] = []
        self.aembedding_calls: list[list[str]] = []
        self.unexpected: list[str] = []
        monkeypatch.setattr(litellm, "acompletion", self.acompletion)
        monkeypatch.setattr(litellm, "completion_cost", self.completion_cost)
        monkeypatch.setattr(litellm, "stream_chunk_builder", self.stream_chunk_builder)
        monkeypatch.setattr(litellm, "token_counter", self.token_counter)
        monkeypatch.setattr(litellm, "embedding", self.embedding)
        monkeypatch.setattr(litellm, "aembedding", self.aembedding)

    async def acompletion(self, **kwargs):
        self.acompletion_calls.append(kwargs)
        if not self.responses:
            self.unexpected.append("acompletion")
            raise AssertionError("unexpected litellm.acompletion call")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    def completion_cost(self, completion_response=None, **kwargs):
        if not self.costs:
            self.unexpected.append("completion_cost")
            raise AssertionError("unexpected litellm.completion_cost call")
        return self.costs.pop(0)

    def stream_chunk_builder(self, chunks, messages=None, **kwargs):
        return SimpleNamespace(usage=None)

    def token_counter(self, model=None, messages=None, text=None, **kwargs):
        if messages is not None:
            return PROMPT_TOKENS
        return TOKENS_PER_WORD * len((text or "").split())

    def _embed_response(self, inputs):
        vec = [0.1] * settings.embedding_dim
        return SimpleNamespace(data=[{"embedding": vec} for _ in inputs], usage=None)

    def embedding(self, model=None, input=(), **kwargs):
        self.embedding_calls.append(list(input))
        return self._embed_response(input)

    async def aembedding(self, model=None, input=(), **kwargs):
        self.aembedding_calls.append(list(input))
        return self._embed_response(input)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _real_llm_settings(monkeypatch):
    # The test env enables the stub (gemini_api_key == "test"); turn it off
    # so the real paths run against the fakes. The stub test turns it on.
    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")
    monkeypatch.setattr(settings, "model", MODEL)
    monkeypatch.setattr(settings, "embedding_model", EMBEDDING_MODEL)
    monkeypatch.setattr(settings, "llm_soft_cap_usd", 2.00)
    monkeypatch.setattr(settings, "llm_hard_cap_usd", 3.00)
    monkeypatch.setattr(settings, "global_daily_cost_cap_usd", None)
    monkeypatch.setattr(settings, "llm_turn_reserve_usd", 0.02)
    # The estimate constants above assume these rates; pin them so a pricing
    # update to MODEL_RATES does not read as a behaviour change.
    monkeypatch.setitem(
        cost_meter.MODEL_RATES,
        MODEL,
        {"input_per_1k": Decimal("0.000300"), "output_per_1k": Decimal("0.002500")},
    )


@pytest.fixture
def fake_litellm(monkeypatch):
    fake = FakeLitellm(monkeypatch)
    yield fake
    # Every scripted response and price was consumed, and nothing unscripted
    # was called (even if production code swallowed the tripwire).
    assert fake.unexpected == []
    assert fake.responses == []
    assert fake.costs == []


@pytest.fixture
def seeded(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()


def _ctx(db, *, suppress_check=False) -> ToolContext:
    return ToolContext(
        db=db,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc),
        suppress_check=suppress_check,
    )


async def _run(ctx, system_prompt="sys", **kwargs):
    return [
        ev
        async for ev in tutor.run_streaming(
            [{"role": "user", "content": "hi"}], system_prompt, ctx, **kwargs
        )
    ]


def _types(events) -> list[str]:
    return [e.type for e in events]


def _assistant(db) -> ChatMessage:
    return db.execute(
        select(ChatMessage).where(
            ChatMessage.session_id == SESSION_ID, ChatMessage.role == "assistant"
        )
    ).scalar_one()


def _ledger(db) -> Decimal:
    return cost_meter.current_spend(db, USER_ID)


def _log_rows(db) -> list[tuple[str, Decimal]]:
    rows = db.execute(select(LlmCallLog.purpose, LlmCallLog.cost_usd).order_by(LlmCallLog.id)).all()
    return [(purpose, Decimal(str(cost))) for purpose, cost in rows]


def _log_attribution(db) -> set[tuple[str, str, str]]:
    """The distinct (model, user_id, session_id) the log rows are billed to."""
    return set(
        db.execute(select(LlmCallLog.model, LlmCallLog.user_id, LlmCallLog.session_id)).all()
    )


CHAT_ATTRIBUTION = {(MODEL, USER_ID, SESSION_ID)}
EMBEDDING_ATTRIBUTION = {(EMBEDDING_MODEL, USER_ID, SESSION_ID)}


def _assert_chat_call(call: dict) -> None:
    """The tutor's per-iteration acompletion contract."""
    assert call["model"] == MODEL
    assert call["stream"] is True
    assert call["tools"] == tools.TOOLS
    assert call["tool_choice"] == "auto"
    assert call["temperature"] == settings.llm_temperature
    assert call["timeout"] == settings.llm_timeout_s


def _assert_summary_call(call: dict) -> None:
    """The summaries' single non-streamed acompletion contract."""
    assert call["model"] == MODEL
    assert "stream" not in call
    assert "tools" not in call
    assert call["temperature"] == settings.summary_temperature
    assert call["timeout"] == settings.summary_timeout_s


# ---------------------------------------------------------------------------
# run_streaming exit paths
# ---------------------------------------------------------------------------


async def test_single_text_iteration(db_session, seeded, fake_litellm):
    fake_litellm.responses = [_litellm_stream(_text_chunk("Hello "), _text_chunk("there"))]
    fake_litellm.costs = [0.001]

    events = await _run(_ctx(db_session))

    assert _types(events) == ["assistant_delta", "assistant_delta", "done"]
    msg = _assistant(db_session)
    assert events[-1].data == {"message_id": str(msg.id)}
    assert (msg.status, msg.content) == ("complete", "Hello there")
    assert len(fake_litellm.acompletion_calls) == 1
    _assert_chat_call(fake_litellm.acompletion_calls[0])
    assert _ledger(db_session) == Decimal("0.0010")
    assert _log_rows(db_session) == [("chat", Decimal("0.0010"))]
    assert _log_attribution(db_session) == CHAT_ATTRIBUTION


async def test_tool_iteration_then_text_bills_both(db_session, seeded, fake_litellm):
    fake_litellm.responses = [
        _litellm_stream(_tool_chunk("tc1", "update_topic_profile", PROFILE_PATCH)),
        _litellm_stream(_text_chunk("Noted.")),
    ]
    fake_litellm.costs = [0.001, 0.002]

    events = await _run(_ctx(db_session))

    assert _types(events) == ["tool_call_start", "tool_call_done", "assistant_delta", "done"]
    assert events[0].data["name"] == "update_topic_profile"
    assert events[1].data["status"] == "ok"
    assert _assistant(db_session).status == "complete"
    assert len(fake_litellm.acompletion_calls) == 2
    for call in fake_litellm.acompletion_calls:
        _assert_chat_call(call)
    assert _ledger(db_session) == Decimal("0.0030")
    assert _log_rows(db_session) == [
        ("chat", Decimal("0.0010")),
        ("chat", Decimal("0.0020")),
    ]
    assert _log_attribution(db_session) == CHAT_ATTRIBUTION


async def test_cancel_during_iteration_two(db_session, seeded, fake_litellm):
    """Iteration 1 is billed at its real price; the cancelled iteration 2 is
    billed by token math over its prompt snapshot plus only the text streamed
    since iteration 1 was billed."""
    parked = asyncio.Event()  # never set: iteration 2 hangs until cancelled
    fake_litellm.responses = [
        _litellm_stream(
            _text_chunk(FIRST_TEXT),
            _tool_chunk("tc1", "update_topic_profile", PROFILE_PATCH),
        ),
        _litellm_stream(_text_chunk(TAIL_TEXT), block=parked),
    ]
    fake_litellm.costs = [0.001]

    events: list = []
    reached = asyncio.Event()

    async def consume():
        async for ev in tutor.run_streaming(
            [{"role": "user", "content": "hi"}], "sys", _ctx(db_session)
        ):
            events.append(ev)
            if ev.type == "assistant_delta" and ev.data["text"] == TAIL_TEXT:
                reached.set()

    task = asyncio.create_task(consume())
    try:
        await asyncio.wait_for(reached.wait(), timeout=5)
    except TimeoutError:
        # Let the cancel arm finish with db_session before teardown drops it.
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.gather(task)
        raise
    task.cancel()
    # gather(), not a bare `await task`: same wait and re-raise, and CodeQL
    # does not misread it as a statement with no effect.
    with pytest.raises(asyncio.CancelledError):
        await asyncio.gather(task)

    assert _types(events) == [
        "assistant_delta",
        "tool_call_start",
        "tool_call_done",
        "assistant_delta",
        "cancelled",
    ]
    cancelled = events[-1].data
    msg = _assistant(db_session)
    assert cancelled["message_id"] == str(msg.id)
    assert cancelled["partial_content_chars"] == len(FIRST_TEXT + TAIL_TEXT)
    assert Decimal(cancelled["estimated_cost_usd"]) == CANCEL_TAIL_ESTIMATE
    assert (msg.status, msg.content) == ("cancelled", FIRST_TEXT + TAIL_TEXT)
    assert msg.cancelled_at is not None
    assert _ledger(db_session) == Decimal("0.0010") + CANCEL_TAIL_ESTIMATE
    assert _log_rows(db_session) == [
        ("chat", Decimal("0.0010")),
        ("chat", CANCEL_TAIL_ESTIMATE),
    ]
    assert _log_attribution(db_session) == CHAT_ATTRIBUTION


async def test_provider_error_mid_stream(db_session, seeded, fake_litellm):
    fake_litellm.responses = [
        _litellm_stream(
            _text_chunk(FIRST_TEXT),
            _tool_chunk("tc1", "update_topic_profile", PROFILE_PATCH),
        ),
        _litellm_stream(_text_chunk(TAIL_TEXT), error=RuntimeError("provider 503")),
    ]
    fake_litellm.costs = [0.001]

    events = await _run(_ctx(db_session))

    assert _types(events) == [
        "assistant_delta",
        "tool_call_start",
        "tool_call_done",
        "assistant_delta",
        "error",
    ]
    assert events[-1].data["code"] == "llm_failed"
    msg = _assistant(db_session)
    assert (msg.status, msg.content) == ("error", FIRST_TEXT + TAIL_TEXT)
    # Changed by #412: the failed call settles its own estimate once; the
    # error arm no longer re-estimates the whole turn on top of iteration 1.
    assert _ledger(db_session) == Decimal("0.0010") + ERROR_CALL_ESTIMATE
    assert _log_rows(db_session) == [
        ("chat", Decimal("0.0010")),
        ("chat", ERROR_CALL_ESTIMATE),
    ]
    assert _log_attribution(db_session) == CHAT_ATTRIBUTION


async def test_transient_429_before_the_first_token_retries(
    db_session, seeded, fake_litellm, monkeypatch
):
    """New in #412: a 429 before any chunk retries instead of failing the
    turn, and the refused attempt costs nothing."""
    monkeypatch.setattr(settings, "llm_retry_base_delay_s", 0)
    fake_litellm.responses = [
        litellm.RateLimitError(message="slow down", llm_provider="gemini", model=MODEL),
        _litellm_stream(_text_chunk("Hello")),
    ]
    fake_litellm.costs = [0.001]

    events = await _run(_ctx(db_session))

    assert _types(events) == ["assistant_delta", "done"]
    assert _assistant(db_session).status == "complete"
    assert len(fake_litellm.acompletion_calls) == 2
    assert _ledger(db_session) == Decimal("0.0010")
    assert _log_rows(db_session) == [("chat", Decimal("0.0010"))]


async def test_mid_turn_hard_cap(db_session, seeded, fake_litellm, monkeypatch):
    """Iteration 1's real cost reaches the hard cap; the adapter gate on
    iteration 2's stream refuses, stopping the turn without another provider
    call."""
    monkeypatch.setattr(settings, "llm_soft_cap_usd", 0.0005)
    monkeypatch.setattr(settings, "llm_hard_cap_usd", 0.001)
    fake_litellm.responses = [
        _litellm_stream(
            _text_chunk("Checking. "),
            _tool_chunk("tc1", "update_topic_profile", PROFILE_PATCH),
        ),
    ]
    fake_litellm.costs = [0.001]

    events = await _run(_ctx(db_session))

    assert _types(events) == ["assistant_delta", "tool_call_start", "tool_call_done", "error"]
    assert events[-1].data["code"] == "daily_cost_cap_reached"
    assert len(fake_litellm.acompletion_calls) == 1
    msg = _assistant(db_session)
    assert (msg.status, msg.content) == ("partial", "Checking. ")
    assert _ledger(db_session) == Decimal("0.0010")
    assert _log_rows(db_session) == [("chat", Decimal("0.0010"))]
    assert _log_attribution(db_session) == CHAT_ATTRIBUTION


async def test_max_iters_reached(db_session, seeded, fake_litellm):
    fake_litellm.responses = [
        _litellm_stream(
            _text_chunk("Step one. "),
            _tool_chunk("tc1", "update_topic_profile", PROFILE_PATCH),
        ),
        _litellm_stream(
            _text_chunk("Step two. "),
            _tool_chunk("tc2", "update_topic_profile", PROFILE_PATCH),
        ),
    ]
    fake_litellm.costs = [0.001, 0.002]

    events = await _run(_ctx(db_session), max_iters=2)

    assert _types(events) == [
        "assistant_delta",
        "tool_call_start",
        "tool_call_done",
        "assistant_delta",
        "tool_call_start",
        "tool_call_done",
        "error",
    ]
    assert events[-1].data["code"] == "max_iters_reached"
    msg = _assistant(db_session)
    assert (msg.status, msg.content) == ("partial", "Step one. Step two. ")
    assert _ledger(db_session) == Decimal("0.0030")
    assert _log_rows(db_session) == [
        ("chat", Decimal("0.0010")),
        ("chat", Decimal("0.0020")),
    ]
    assert _log_attribution(db_session) == CHAT_ATTRIBUTION


async def test_stub_mode_fresh_and_resumed(db_session, seeded, fake_litellm, monkeypatch):
    monkeypatch.setattr(settings, "llm_stub", True)

    fresh = await _run(_ctx(db_session))
    assert set(_types(fresh[:-1])) == {"assistant_delta"}
    assert fresh[-1].type == "done"
    assert "".join(e.data["text"] for e in fresh[:-1]) == "[STUB:fresh] Echo: hi"

    resumed = await _run(
        _ctx(db_session), system_prompt="rules\nLAST_SESSION_SUMMARY: covered joins\n"
    )
    assert resumed[-1].type == "done"
    text = "".join(e.data["text"] for e in resumed[:-1])
    assert text.startswith("[STUB:resumed:")
    assert text.endswith("] Echo: hi")

    statuses = db_session.execute(
        select(ChatMessage.status).where(ChatMessage.role == "assistant")
    ).scalars()
    assert list(statuses) == ["complete", "complete"]
    assert fake_litellm.acompletion_calls == []
    assert db_session.execute(select(func.count()).select_from(DailyCostLedger)).scalar_one() == 0
    assert _log_rows(db_session) == []


async def test_check_followup_turn_logs_followup_purpose(db_session, seeded, fake_litellm):
    fake_litellm.responses = [_litellm_stream(_text_chunk("Right."))]
    fake_litellm.costs = [0.001]

    events = await _run(_ctx(db_session, suppress_check=True))

    assert _types(events) == ["assistant_delta", "done"]
    assert _assistant(db_session).status == "complete"
    _assert_chat_call(fake_litellm.acompletion_calls[0])
    assert _ledger(db_session) == Decimal("0.0010")
    assert _log_rows(db_session) == [("followup", Decimal("0.0010"))]
    assert _log_attribution(db_session) == CHAT_ATTRIBUTION


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def _seed_messages(db, n: int) -> None:
    for i in range(n):
        db.add(
            ChatMessage(
                session_id=SESSION_ID,
                role="user" if i % 2 == 0 else "assistant",
                content=f"message {i}",
            )
        )
    db.commit()


@pytest.fixture
def ledger_down(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("ledger down")

    monkeypatch.setattr(cost_meter, "record_cost", boom)


async def test_generate_and_persist_meters_summary(db_session, seeded, fake_litellm):
    _seed_messages(db_session, 2)
    fake_litellm.responses = [_completion("Covered joins; foreign keys remain a gap.")]
    fake_litellm.costs = [0.002]

    session = db_session.get(SessionModel, SESSION_ID)
    summary = await summary_service.generate_and_persist(db_session, session)

    assert summary == "Covered joins; foreign keys remain a gap."
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert profile.last_session_summary == summary
    _assert_summary_call(fake_litellm.acompletion_calls[0])
    assert _ledger(db_session) == Decimal("0.0020")
    assert _log_rows(db_session) == [("summary", Decimal("0.0020"))]
    assert _log_attribution(db_session) == CHAT_ATTRIBUTION


async def test_generate_and_persist_record_cost_failure_keeps_summary(
    db_session, seeded, fake_litellm, ledger_down
):
    _seed_messages(db_session, 2)
    fake_litellm.responses = [_completion("Covered joins.")]
    fake_litellm.costs = [0.002]

    session = db_session.get(SessionModel, SESSION_ID)
    summary = await summary_service.generate_and_persist(db_session, session)

    # Changed by #411: settlement never raises, so a failed ledger write no
    # longer throws the paid summary away for the mechanical one.
    assert len(fake_litellm.acompletion_calls) == 1
    assert fake_litellm.costs == []
    assert summary == "Covered joins."
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert profile.last_session_summary == summary
    # The receipt row is kept even though the ledger write failed.
    assert _log_rows(db_session) == [("summary", Decimal("0.0020"))]


async def test_update_rolling_summary_meters_rolling_summary(db_session, seeded, fake_litellm):
    _seed_messages(db_session, 31)  # 11 dropped past the 20-message window
    fake_litellm.responses = [_completion("Earlier the learner practised joins.")]
    fake_litellm.costs = [0.002]

    result = await summary_service.update_rolling_summary(db_session, SESSION_ID)

    assert result == "Earlier the learner practised joins."
    session = db_session.get(SessionModel, SESSION_ID)
    assert session.rolling_summary == result
    assert session.rolling_summary_count == 11
    _assert_summary_call(fake_litellm.acompletion_calls[0])
    assert _ledger(db_session) == Decimal("0.0020")
    assert _log_rows(db_session) == [("rolling_summary", Decimal("0.0020"))]
    assert _log_attribution(db_session) == CHAT_ATTRIBUTION


async def test_update_rolling_summary_record_cost_failure_keeps_summary(
    db_session, seeded, fake_litellm, ledger_down
):
    _seed_messages(db_session, 31)
    fake_litellm.responses = [_completion("Earlier the learner practised joins.")]
    fake_litellm.costs = [0.002]

    result = await summary_service.update_rolling_summary(db_session, SESSION_ID)

    # Changed by #411: settlement never raises, so a failed ledger write no
    # longer discards the paid rolling summary.
    assert len(fake_litellm.acompletion_calls) == 1
    assert fake_litellm.costs == []
    assert result == "Earlier the learner practised joins."
    session = db_session.get(SessionModel, SESSION_ID)
    assert session.rolling_summary == result
    assert session.rolling_summary_count == 11
    # The receipt row is kept even though the ledger write failed.
    assert _log_rows(db_session) == [("rolling_summary", Decimal("0.0020"))]


# ---------------------------------------------------------------------------
# Chat prepare failure after the prefetch embedding (B-08)
# ---------------------------------------------------------------------------


def test_prepare_failure_after_prefetch_keeps_embedding_spend(
    client, db_session, seeded, fake_litellm, monkeypatch
):
    message = "explain foreign keys"
    session = db_session.get(SessionModel, SESSION_ID)
    # The lexical gate matches, so _prepare_turn prefetches (and pays for) a
    # query embedding before the prompt build.
    session.kw_index_json = json.dumps(sorted(keyword_index.build_from_text(message)))
    db_session.add(Document(session_id=SESSION_ID, filename="ref.txt", status="ready"))
    db_session.commit()

    fake_litellm.costs = [0.0005]
    monkeypatch.setattr(pgvector_store, "query_chunks", lambda *a, **k: [])

    def boom(prompt_state):
        raise RuntimeError("prompt build exploded")

    monkeypatch.setattr("agent.prompts.build_system_prompt", boom)

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": message},
        headers={"Authorization": f"Bearer test-{USER_ID}"},
    ) as resp:
        assert resp.status_code == 500

    # The request path embeds on the event loop (async), never the sync call.
    assert fake_litellm.aembedding_calls == [[message]]
    assert fake_litellm.embedding_calls == []
    user_msgs = db_session.execute(
        select(ChatMessage.content).where(ChatMessage.role == "user")
    ).scalars()
    assert list(user_msgs) == [message]
    # Reservation released; the embedding spend recorded once, by the
    # adapter, in its own transaction.
    assert _ledger(db_session) == Decimal("0.0005")
    # Changed by #411: the embedding's LlmCallLog row used to be lost with
    # the rollback (only the ledger amount was re-recorded); now it survives.
    assert _log_rows(db_session) == [("embedding", Decimal("0.0005"))]
    assert _log_attribution(db_session) == EMBEDDING_ATTRIBUTION


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


@pytest.fixture
def ingest_doc(db_session, seeded, monkeypatch):
    doc = Document(session_id=SESSION_ID, filename="ref.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    # sqlite has no vector type; the storage call itself is not under test.
    monkeypatch.setattr(pgvector_store, "insert_chunks", lambda db, *, rows, **k: len(rows))
    monkeypatch.setattr(ingestion_service, "EMBED_BATCH", 1)
    return doc


def _chunks(n: int) -> list[chunking.Chunk]:
    return [chunking.Chunk(text=f"chunk {i}", page=None, chunk_idx=i) for i in range(n)]


def test_ingestion_meters_each_batch(db_session, ingest_doc, fake_litellm):
    fake_litellm.costs = [0.0005, 0.0005, 0.0005]

    stored = ingestion_service._embed_and_store(db_session, ingest_doc, _chunks(3), user_id=USER_ID)

    assert stored == 3
    # Ingestion embeds synchronously (worker / threadpool), never async.
    assert fake_litellm.embedding_calls == [["chunk 0"], ["chunk 1"], ["chunk 2"]]
    assert fake_litellm.aembedding_calls == []
    assert _ledger(db_session) == Decimal("0.0015")
    assert _log_rows(db_session) == [("embedding", Decimal("0.0005"))] * 3
    assert _log_attribution(db_session) == EMBEDDING_ATTRIBUTION


def test_ingestion_capped_user_stops_at_next_batch(
    db_session, ingest_doc, fake_litellm, monkeypatch
):
    monkeypatch.setattr(settings, "llm_soft_cap_usd", 0.0005)
    monkeypatch.setattr(settings, "llm_hard_cap_usd", 0.001)
    fake_litellm.costs = [0.0005, 0.0005]

    with pytest.raises(cost_meter.CostCapExceeded):
        ingestion_service._embed_and_store(db_session, ingest_doc, _chunks(3), user_id=USER_ID)

    # Batch 2 brought spend to the cap; batch 3 is refused before embedding.
    assert fake_litellm.embedding_calls == [["chunk 0"], ["chunk 1"]]
    assert _ledger(db_session) == Decimal("0.0010")
    assert _log_rows(db_session) == [("embedding", Decimal("0.0005"))] * 2
    assert _log_attribution(db_session) == EMBEDDING_ATTRIBUTION


def test_stub_mode_ingestion_still_embeds_and_meters(
    db_session, ingest_doc, fake_litellm, monkeypatch
):
    monkeypatch.setattr(settings, "llm_stub", True)
    fake_litellm.costs = [0.0005]

    ingestion_service._embed_and_store(db_session, ingest_doc, _chunks(1), user_id=USER_ID)

    # #413 changes this: stub mode does not gate embeddings today, so the
    # provider is called and billed. After #413 the stub provider returns
    # fake vectors at cost 0 without touching the network.
    assert fake_litellm.embedding_calls == [["chunk 0"]]
    assert _ledger(db_session) == Decimal("0.0005")
    assert _log_rows(db_session) == [("embedding", Decimal("0.0005"))]
