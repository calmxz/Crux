import logging
import os

# Q-01: must run before anything imports `config`, or the real .env loads
# into the test process. Do not move below the imports.
os.environ["CRUX_SKIP_DOTENV"] = "1"
# litellm's bundled pricing table, not one fetched at import: embedding fakes
# are priced by it, and a remote table dropping the model would log (#577).
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

import threading
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
from fastapi import HTTPException, Request, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main as main_module
from db.database import Base, get_db
from db.database import engine as default_engine
from main import app
from services.auth import current_user_id


def _fake_current_user_id(request: Request) -> str:
    """Test convention: `Authorization: Bearer test-<userid>` resolves to <userid>.

    If no header is present, returns "test-user" as a default so existing tests
    that don't yet send a bearer token keep working until they're migrated.
    """
    auth = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return "test-user"
    token = auth.split(None, 1)[1].strip()
    if token.startswith("test-"):
        return token[len("test-") :]
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")


@pytest.fixture(autouse=True)
def _no_ingest_thread(monkeypatch):
    """Default-ON ingest_in_process must not start a real poll thread
    inside tests that run the app lifespan. Tests that exercise
    start_ingest_loop() re-enable it explicitly."""
    from config import settings

    monkeypatch.setattr(settings, "ingest_in_process", False)


# --- SSE contract (#463) ---------------------------------------------------
# Every StreamEvent built in the suite is validated against the x-sse-events
# block of docs/api/openapi.yaml. Types built by non-test code are recorded;
# a whole-suite run fails if any of the block's types was never emitted.

_TESTS_DIR = os.path.normcase(os.path.dirname(os.path.abspath(__file__))) + os.sep
_sse_seen_key = pytest.StashKey[set[str]]()
_sse_deselected_key = pytest.StashKey[bool]()


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "sse_unchecked(reason): skip x-sse-events validation of StreamEvents in this test",
    )
    config.stash[_sse_seen_key] = set()


@pytest.fixture(autouse=True)
def _validate_stream_events(request, monkeypatch):
    marker = request.node.get_closest_marker("sse_unchecked")
    if marker is not None:
        reason = marker.args[0] if marker.args else marker.kwargs.get("reason")
        if not reason:
            pytest.fail("@pytest.mark.sse_unchecked needs a reason")
        yield
        return

    import sys

    from agent.stream_events import StreamEvent
    from tests.sse_contract import SseContractError, validate_event

    seen = request.config.stash[_sse_seen_key]
    violations: list[str] = []
    orig_init = StreamEvent.__init__

    def checked_init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        try:
            validate_event(self.type, self.data)
        except SseContractError as e:
            # Recorded as well as raised: tutor.run_streaming turns any
            # exception into an `error` event, which would hide the violation.
            violations.append(str(e))
            raise
        # Frame 1 is the StreamEvent(...) call site; test fakes and off-spec
        # events do not count toward coverage.
        caller = os.path.normcase(sys._getframe(1).f_code.co_filename)
        if not caller.startswith(_TESTS_DIR):
            seen.add(self.type)

    monkeypatch.setattr(StreamEvent, "__init__", checked_init)
    yield
    if violations:
        pytest.fail("\n".join(violations), pytrace=False)


def _is_whole_suite_run(config) -> bool:
    # No path was given on the command line: args_source is TESTPATHS from
    # backend/, INVOCATION_DIR from backend/tests/. (config.args is never
    # empty: pyproject sets testpaths.)
    no_paths = config.args_source == pytest.Config.ArgsSource.TESTPATHS or (
        config.args_source == pytest.Config.ArgsSource.INVOCATION_DIR
        and os.path.normcase(str(config.invocation_params.dir)) + os.sep == _TESTS_DIR
    )
    # -k, -m, --lf, --sw and --deselect all narrow the run by deselecting;
    # --ignore narrows it at collection.
    return (
        no_paths
        and not config.getoption("keyword")
        and not config.getoption("markexpr")
        and not config.getoption("collectonly")
        and not config.getoption("ignore")
        and not config.getoption("ignore_glob")
        and not config.stash.get(_sse_deselected_key, False)
    )


def pytest_deselected(items):
    if items:
        items[0].config.stash[_sse_deselected_key] = True


def _fail_run(session, message: str) -> None:
    """Fail a run that would otherwise pass, with a red banner. A run already
    failing, interrupted or broken keeps its own exit code."""
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.ensure_newline()
        reporter.write_sep("=", message, red=True)
    if session.exitstatus == pytest.ExitCode.OK:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_sessionfinish(session, exitstatus):
    # Default-engine hits after the last test's teardown (#579): no test is
    # left to fail, so they fail the run.
    if _default_engine_hits:
        _fail_run(
            session,
            "connected on the default engine (db.database.engine) after the last test: "
            + ", ".join(sorted(set(_default_engine_hits))),
        )
        return
    # Only a clean run is judged: after a failure (or -x) the missing list
    # would be noise over the real error.
    if exitstatus != pytest.ExitCode.OK:
        return
    if not _is_whole_suite_run(session.config):
        return
    from tests.sse_contract import sse_event_schemas

    missing = sorted(set(sse_event_schemas()) - session.config.stash[_sse_seen_key])
    if missing:
        _fail_run(session, "SSE event types never emitted by non-test code: " + ", ".join(missing))


@pytest.fixture(autouse=True)
def _inline_settle_retry(monkeypatch):
    """The adapter retries a failed ledger write on a background timer. Run it
    inline instead, so a test sees its outcome and leaves no thread behind
    to touch a closed engine."""
    from services import llm

    monkeypatch.setattr(llm, "_schedule", lambda delay, fn, *args: fn(*args))
    # Fresh slots, so a test that captures a retry and never runs it cannot
    # starve the next test's retries.
    monkeypatch.setattr(
        llm, "_retry_slots", threading.BoundedSemaphore(llm.SETTLE_RETRY_MAX_IN_FLIGHT)
    )


# --- Default-engine guard (#579) -------------------------------------------
# No test may connect on the app's default engine (settings.database_url, a
# developer's real data/app.db locally). The connect hook records the test
# and refuses the connection, so the file is never opened; the refusal alone
# could be swallowed by a best-effort path, so the record fails the test.

_default_engine_hits: list[str] = []
_current_test: list[str | None] = [None]


@event.listens_for(default_engine, "do_connect")
def _refuse_default_engine(dialect, conn_rec, cargs, cparams):
    _default_engine_hits.append(_current_test[0] or "<outside a test>")
    raise RuntimeError("tests must not connect on the default engine (db.database.engine)")


@pytest.fixture(autouse=True)
def _no_default_engine(request):
    # Hits from outside any test (collection, a session fixture) are kept
    # and reported by the next test's teardown; pytest_sessionfinish reports
    # any left after the last one.
    _current_test[0] = request.node.nodeid
    yield
    _current_test[0] = None
    if _default_engine_hits:
        hits = sorted(set(_default_engine_hits))
        _default_engine_hits.clear()
        pytest.fail(
            "connected on the default engine (db.database.engine): "
            + ", ".join(hits)
            + "; bind the session factory it used to the test engine. A hit"
            " can also come from a thread or fixture an earlier test left behind.",
            pytrace=False,
        )


# --- Unexpected app log guard (#577) ---------------------------------------
# A best-effort path catches a fake's failure, logs it and returns the very
# fallback the test expects, so the test passes vacuously. Any app record at
# WARNING or above fails the test unless it requested caplog, which opts it
# out: it must assert the message it expects instead.

_APP_LOGGER_ROOTS = frozenset(
    {"agent", "config", "db", "lib", "main", "routes", "services", "worker"}
)
_app_log_records: list[logging.LogRecord] = []


class _AppLogRecorder(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        _app_log_records.append(record)


@pytest.fixture(autouse=True)
def _no_unexpected_app_logs(request):
    if "caplog" in request.fixturenames:
        yield
        return
    _app_log_records.clear()
    # On the app's own parent loggers, not root: a test that resets root
    # (configure_logging's dictConfig) would drop it. Their level is pinned
    # at WARNING or below, so neither LOG_LEVEL nor a root level raised
    # mid-test hides the records.
    handler = _AppLogRecorder(logging.WARNING)
    loggers = [logging.getLogger(name) for name in _APP_LOGGER_ROOTS]
    levels = [lg.level for lg in loggers]
    for lg in loggers:
        lg.setLevel(min(lg.getEffectiveLevel(), logging.WARNING))
        lg.addHandler(handler)
    try:
        yield
    finally:
        for lg, level in zip(loggers, levels, strict=True):
            lg.removeHandler(handler)
            lg.setLevel(level)
    if _app_log_records:
        lines = [f"{r.levelname} {r.name}: {r.getMessage()}" for r in _app_log_records]
        _app_log_records.clear()
        pytest.fail(
            "unexpected app log records (request caplog and assert the message"
            " if the test drives this on purpose; otherwise fix the cause):\n  "
            + "\n  ".join(lines),
            pytrace=False,
        )


@pytest.fixture
def db_session(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # The LLM adapter settles spend in its own session; point it at this
    # engine. StaticPool shares one connection, so its commit also commits
    # the caller's pending writes on sqlite (#411).
    from routes import chat
    from services import llm

    monkeypatch.setattr(llm, "session_factory", Session)
    # Likewise the post-response rolling-summary task (#579).
    monkeypatch.setattr(chat, "SessionLocal", Session)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


# --- Opt-in Postgres harness (#574) ------------------------------------------
# Used only by the modules that skip without TEST_DATABASE_URL, so a SQLite
# run never builds a Postgres engine.


@pytest.fixture(scope="module")
def pg_engine(request):
    """One engine per module. prepare_threshold=None matches prod (Supabase
    pooler); a module adds connect_args with a PG_CONNECT_ARGS dict."""
    from db.database import _normalized_url

    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("TEST_DATABASE_URL not set")
    connect_args = {"prepare_threshold": None, **getattr(request.module, "PG_CONNECT_ARGS", {})}
    eng = create_engine(_normalized_url(os.environ["TEST_DATABASE_URL"]), connect_args=connect_args)
    yield eng
    eng.dispose()


@pytest.fixture
def pg_seed(pg_engine):
    """A tests.pg_harness.PgSeeder. A fixture that holds a connection or open
    transaction on seeded rows must depend on this one, so it is torn down
    first and cannot block the teardown's deletes."""
    from tests.pg_harness import PgSeeder

    seeder = PgSeeder(pg_engine)
    yield seeder
    seeder.teardown()


class _AuthInjectingClient(TestClient):
    """TestClient shim: any `user_id` field in request body/data/query is
    stripped from the payload and converted to `Authorization: Bearer
    test-<user_id>`. Lets Phase 6-and-earlier tests keep their original
    `user_id="u1"` style without per-file refactors.

    Tests that need to assert auth failure can either: pass
    `headers={"Authorization": "..."}` explicitly (wins over the shim) or
    pass `headers={"Authorization": ""}` to suppress and trigger 401.
    """

    def request(self, method, url, **kw):
        json = kw.get("json")
        data = kw.get("data")
        params = kw.get("params")
        headers = dict(kw.get("headers") or {})

        user_id = None
        if isinstance(json, dict) and "user_id" in json:
            user_id = json["user_id"]
            kw["json"] = {k: v for k, v in json.items() if k != "user_id"}
        if isinstance(data, dict) and "user_id" in data:
            user_id = user_id or data["user_id"]
            kw["data"] = {k: v for k, v in data.items() if k != "user_id"}
        if isinstance(params, dict) and "user_id" in params:
            user_id = user_id or params["user_id"]
            kw["params"] = {k: v for k, v in params.items() if k != "user_id"}

        # Strip user_id from URL-embedded query strings too.
        if isinstance(url, str) and "user_id=" in url:
            parts = urlsplit(url)
            qs = parse_qsl(parts.query, keep_blank_values=True)
            stripped = [(k, v) for (k, v) in qs if k != "user_id"]
            for k, v in qs:
                if k == "user_id":
                    user_id = user_id or v
            url = urlunsplit(
                (parts.scheme, parts.netloc, parts.path, urlencode(stripped), parts.fragment)
            )

        lower_keys = {k.lower() for k in headers}
        if user_id and "authorization" not in lower_keys:
            headers["Authorization"] = f"Bearer test-{user_id}"
        kw["headers"] = headers
        return super().request(method, url, **kw)


@pytest.fixture
def client(db_session, monkeypatch):
    test_engine = db_session.get_bind()

    monkeypatch.setattr(
        main_module, "create_tables", lambda: Base.metadata.create_all(bind=test_engine)
    )
    monkeypatch.setattr(main_module, "validate_jwks_startup", lambda: None)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user_id] = _fake_current_user_id
    with _AuthInjectingClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# Stream script step: park the stream here until the consumer is cancelled.
BLOCK = object()


def tool_call(name: str, args: dict | str | None = None, id: str | None = None):
    """A stream script step: one assembled tool call. A str `args` is passed
    through raw (to script malformed JSON)."""
    import json

    from services.llm import ToolCall

    raw = args if isinstance(args, str) else json.dumps(args or {})
    return ToolCall(id=id or f"call_{name}", name=name, arguments=raw)


def embedding_response(vectors: list[list[float]]):
    """A litellm.embedding response the cost meter can price. A bare
    SimpleNamespace(data=...) has no model, so completion_cost fails and
    cost_meter logs a warning on every embed."""
    import litellm
    from litellm.types.utils import Usage

    from config import settings

    return litellm.EmbeddingResponse(
        model=settings.embedding_model,
        data=[{"embedding": v, "index": i, "object": "embedding"} for i, v in enumerate(vectors)],
        usage=Usage(prompt_tokens=len(vectors), total_tokens=len(vectors)),
    )


class _FakeProviderStream:
    """One scripted stream (see FakeLlmProvider.streams)."""

    def __init__(self, provider: "FakeLlmProvider", steps: list, messages: list[dict]):
        self._provider = provider
        self._steps = steps
        self._messages = messages
        self._tool_calls: list = []
        self.received = False
        self.text = ""
        self.closed = False

    @property
    def tool_calls(self):
        return list(self._tool_calls)

    async def __aiter__(self):
        import asyncio

        from services.llm import ToolCall

        for step in self._steps:
            if step is BLOCK:
                await asyncio.Event().wait()
            elif isinstance(step, asyncio.Event):
                await step.wait()
            elif isinstance(step, BaseException):
                raise step
            elif isinstance(step, ToolCall):
                self.received = True
                self._tool_calls.append(step)
            else:
                self.received = True
                self.text += step
                yield step

    def priced(self):
        return self._provider.cost, self._provider._usage()

    def estimate(self):
        self._provider.estimates.append(("stream", [dict(m) for m in self._messages], self.text))
        return self._provider.partial_cost

    async def aclose(self):
        self.closed = True


class FakeLlmProvider:
    """Scripted stand-in for the LLM adapter's provider (#411).

    Tests swap the provider, not the shell, so the cost gate, retry and
    settlement run for real. `replies` feeds complete() attempts in order: a
    str is the reply text, an exception instance is raised. `embed_errors`
    likewise raises on the next embed attempts; `vector` (default 0.1s at
    embedding_dim) is returned for every embedded text. Every successful
    call costs `cost`; a timed-out attempt settles `timeout_cost`, and
    `estimates` records which estimator priced it and from what input.

    `streams` feeds stream() opens in order (#412). An exception instance is
    raised on open; a list is a script of steps: a str is a text token, a
    `tool_call(...)` is an assembled tool call, an exception is raised at that
    point, BLOCK parks until cancelled and an asyncio.Event parks until set.
    An unscripted open streams `default_reply`. A finished stream costs
    `cost`; a cut-short one settles `partial_cost`.
    """

    chat_model = "fake/chat"
    embedding_model = "fake/embedding"

    def __init__(self):
        self.replies: list[Any] = []
        self.streams: list[Any] = []
        self.default_reply = "This is a fake reply."
        self.embed_errors: list[BaseException] = []
        self.vector: list[float] | None = None
        self.cost = Decimal("0")
        self.timeout_cost = Decimal("0")
        self.partial_cost = Decimal("0")
        self.estimates: list[tuple] = []
        self.complete_calls: list[dict] = []
        self.stream_calls: list[dict] = []
        self.opened: list[_FakeProviderStream] = []
        self.embed_calls: list[list[str]] = []
        self.aembed_calls: list[list[str]] = []

    async def stream(self, messages, *, tools, tool_choice, temperature, timeout):
        # Copy each message: the tutor appends to and prunes its list later.
        self.stream_calls.append(
            {
                "messages": [dict(m) for m in messages],
                "tools": tools,
                "tool_choice": tool_choice,
                "temperature": temperature,
                "timeout": timeout,
            }
        )
        script = self.streams.pop(0) if self.streams else [self.default_reply]
        if isinstance(script, BaseException):
            raise script
        s = _FakeProviderStream(self, list(script), messages)
        self.opened.append(s)
        return s

    def _usage(self) -> dict:
        return {"prompt_tokens": None, "completion_tokens": None, "cached_tokens": None}

    async def complete(self, messages, *, temperature, timeout):
        from services.llm import Completion

        self.complete_calls.append(
            {"messages": messages, "temperature": temperature, "timeout": timeout}
        )
        reply = self.replies.pop(0) if self.replies else "This is a fake reply."
        if isinstance(reply, BaseException):
            raise reply
        return Completion(text=reply, cost=self.cost, usage=self._usage())

    def _embedding(self, texts):
        from config import settings
        from services.llm import Embedding

        if self.embed_errors:
            raise self.embed_errors.pop(0)
        vector = self.vector if self.vector is not None else [0.1] * settings.embedding_dim
        vectors = [list(vector) for _ in texts]
        return Embedding(vectors=vectors, cost=self.cost, usage=self._usage())

    def embed(self, texts):
        self.embed_calls.append(list(texts))
        return self._embedding(texts)

    async def aembed(self, texts):
        self.aembed_calls.append(list(texts))
        return self._embedding(texts)

    def completion_prompt_cost(self, messages) -> Decimal:
        self.estimates.append(("completion", messages))
        return self.timeout_cost

    def embedding_prompt_cost(self, texts) -> Decimal:
        self.estimates.append(("embedding", list(texts)))
        return self.timeout_cost


@pytest.fixture
def fake_llm(monkeypatch):
    """Install a FakeLlmProvider behind the real adapter shell. Retries do
    not sleep. The adapter's session factory is already bound to the test
    engine by db_session.

    Stub mode wins over an installed provider (#413), and the test env's
    "test" key turns it on, so this pins it off; a test that wants the stub
    sets `settings.llm_stub = True` after."""
    from config import settings
    from services import llm

    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "fake-llm-key")
    provider = FakeLlmProvider()
    monkeypatch.setattr(llm, "_provider", provider)
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)

    async def no_sleep(_s):
        return None

    monkeypatch.setattr(llm.asyncio, "sleep", no_sleep)
    return provider
