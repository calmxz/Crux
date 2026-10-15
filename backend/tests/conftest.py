import os

# Q-01: must run before anything imports `config`, or the real .env loads
# into the test process. Do not move below the imports.
os.environ["CRUX_SKIP_DOTENV"] = "1"

import threading
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
from fastapi import HTTPException, Request, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main as main_module
from db.database import Base, get_db
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


def pytest_sessionfinish(session, exitstatus):
    # Only a clean run is judged: after a failure (or -x) the missing list
    # would be noise over the real error.
    if exitstatus != pytest.ExitCode.OK:
        return
    if not _is_whole_suite_run(session.config):
        return
    from tests.sse_contract import sse_event_schemas

    missing = sorted(set(sse_event_schemas()) - session.config.stash[_sse_seen_key])
    if missing:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.ensure_newline()
            reporter.write_sep(
                "=",
                "SSE event types never emitted by non-test code: " + ", ".join(missing),
                red=True,
            )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


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
    from services import llm

    monkeypatch.setattr(llm, "session_factory", Session)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


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


class FakeLlmProvider:
    """Scripted stand-in for the LLM adapter's provider (#411).

    Tests swap the provider, not the shell, so the cost gate, retry and
    settlement run for real. `replies` feeds complete() attempts in order: a
    str is the reply text, an exception instance is raised. `embed_errors`
    likewise raises on the next embed attempts; `vector` (default 0.1s at
    embedding_dim) is returned for every embedded text. Every successful
    call costs `cost`; a timed-out attempt settles `timeout_cost`, and
    `estimates` records which estimator priced it and from what input.
    """

    chat_model = "fake/chat"
    embedding_model = "fake/embedding"

    def __init__(self):
        self.replies: list[Any] = []
        self.embed_errors: list[BaseException] = []
        self.vector: list[float] | None = None
        self.cost = Decimal("0")
        self.timeout_cost = Decimal("0")
        self.estimates: list[tuple[str, Any]] = []
        self.complete_calls: list[dict] = []
        self.embed_calls: list[list[str]] = []
        self.aembed_calls: list[list[str]] = []

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
    engine by db_session."""
    from services import llm

    provider = FakeLlmProvider()
    monkeypatch.setattr(llm, "_provider", provider)
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)

    async def no_sleep(_s):
        return None

    monkeypatch.setattr(llm.asyncio, "sleep", no_sleep)
    return provider
