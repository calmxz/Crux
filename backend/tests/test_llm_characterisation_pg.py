"""#410/#411: LLM paths on Postgres (llm-adapter 1/4 and 2/4).

The #411 section at the end proves the adapter's settlement is isolated
from the caller's transaction, through the conftest FakeLlmProvider; the
rest of this docstring describes the #410 cancel-path test.

#410: characterisation of the real /chat/stream cancel path on Postgres.

Drives the real route and the real run_streaming against a streaming
`litellm.acompletion` fake, disconnects the client mid-stream, and pins what
happens today: the B-05 reservation is released exactly once, the
`cancelled` assistant message is persisted, and the partial cost lands on
the ledger. test_chat_stream_route.py fakes run_streaming entirely, so this
is the only test where the real cancel arm's persistence and the route's
release run together.

TestClient cannot disconnect mid-stream, so the ASGI app is called directly
with a `receive` that returns `http.disconnect` once N SSE events were sent.
Fakes patch the GLOBAL `litellm` module only, so the file runs unmodified
through the adapter refactor (#411-#413).

**Opt-in**: skipped unless `TEST_DATABASE_URL` is set, same as
test_pgvector_retrieval.py (CI sets it and runs `alembic upgrade head`
first). Never point it at a production database.
"""

from __future__ import annotations

import asyncio
import json
import os
from decimal import Decimal
from types import SimpleNamespace

import litellm
import pytest
from sqlalchemy import select

from config import settings
from contracts import TopicProfile
from db.database import get_db
from db.models import ChatMessage, LlmCallLog
from main import app
from routes import chat as chat_route
from services import cost_meter, summary_service, velocity_limit
from services.auth import current_user_id

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB,
    reason="TEST_DATABASE_URL not set - skipping live Postgres characterisation test",
)

MODEL = "gemini/gemini-3.5-flash-lite"
# token_counter fake: 1000 tokens per prompt, 200 per streamed word. The
# cancelled iteration streamed "one two " (2 words), so its token-math
# estimate is (1000 * $0.30 + 400 * $2.50) per 1M.
PROMPT_TOKENS = 1000
TOKENS_PER_WORD = 200
CANCEL_ESTIMATE = Decimal("0.0013")
EVENTS_BEFORE_DISCONNECT = 2


def _text_chunk(token: str) -> SimpleNamespace:
    delta = SimpleNamespace(content=token, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


async def _litellm_stream(*chunks, block: asyncio.Event):
    """A streamed acompletion that sends `chunks`, then parks on `block` so
    the disconnect is guaranteed to land mid-stream."""
    for c in chunks:
        yield c
    await block.wait()


@pytest.fixture
def seeded(pg_seed):
    """A unique user + session per run, removed by the shared teardown
    (conftest pg_seed)."""
    return pg_seed("char-pg", topic="sql", topic_profile_json=TopicProfile().model_dump_json())


@pytest.fixture
def app_on_postgres(seeded):
    """The real app on a Postgres session, authenticated as the seeded user.
    The LLM adapter's gate and settlement open their own sessions on the same
    database (#412: the tutor's spend settles there; pg_seed binds
    SessionLocal). Yields the seeded (Session, uid, sid)."""
    Session, uid, _ = seeded

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user_id] = lambda: uid
    velocity_limit.reset()
    try:
        yield seeded
    finally:
        app.dependency_overrides.clear()
        velocity_limit.reset()


async def test_disconnect_mid_stream_persists_cancel_and_releases_reserve_once(
    app_on_postgres, monkeypatch
):
    Session, uid, sid = app_on_postgres

    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")
    monkeypatch.setattr(settings, "model", MODEL)
    monkeypatch.setattr(settings, "llm_soft_cap_usd", 2.00)
    monkeypatch.setattr(settings, "llm_hard_cap_usd", 3.00)
    monkeypatch.setattr(settings, "llm_turn_reserve_usd", 0.02)
    monkeypatch.setattr(settings, "global_daily_cost_cap_usd", None)

    parked = asyncio.Event()  # never set: the provider stream hangs until cancelled
    acompletion_calls: list[dict] = []

    async def fake_acompletion(**kwargs):
        acompletion_calls.append(kwargs)
        return _litellm_stream(_text_chunk("one "), _text_chunk("two "), block=parked)

    def fake_token_counter(model=None, messages=None, text=None, **kwargs):
        if messages is not None:
            return PROMPT_TOKENS
        return TOKENS_PER_WORD * len((text or "").split())

    # No embedding happens on this turn (no ready document). Faked so an
    # unexpected one is recorded instead of reaching the real provider and
    # being swallowed by the best-effort retrieval gate.
    embedding_calls: list[str] = []

    def fake_embedding(**kwargs):
        embedding_calls.append("embedding")
        raise AssertionError("unexpected litellm.embedding call")

    async def fake_aembedding(**kwargs):
        embedding_calls.append("aembedding")
        raise AssertionError("unexpected litellm.aembedding call")

    # Recorded, not just raised: the tutor's cost block catches exceptions
    # and would fall back to the same token-math estimate.
    completion_cost_calls: list[dict] = []

    def no_completion_cost(**kwargs):
        completion_cost_calls.append(kwargs)
        raise AssertionError("a cancelled iteration is never priced by completion_cost")

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(litellm, "token_counter", fake_token_counter)
    monkeypatch.setattr(litellm, "completion_cost", no_completion_cost)
    monkeypatch.setattr(litellm, "embedding", fake_embedding)
    monkeypatch.setattr(litellm, "aembedding", fake_aembedding)
    # CANCEL_ESTIMATE assumes these rates; a pricing update is not a
    # behaviour change.
    monkeypatch.setitem(
        cost_meter.MODEL_RATES,
        MODEL,
        {"input_per_1k": Decimal("0.000300"), "output_per_1k": Decimal("0.002500")},
    )

    # Skip the post-response rolling summary: it would make an extra LLM call.
    async def no_rolling_summary(db, session_id):
        return None

    monkeypatch.setattr(summary_service, "update_rolling_summary", no_rolling_summary)

    releases: list[str] = []
    real_release = chat_route._release_reserve

    def counting_release(db, user_id):
        releases.append(user_id)
        return real_release(db, user_id)

    monkeypatch.setattr(chat_route, "_release_reserve", counting_release)

    body = json.dumps({"session_id": sid, "message": "explain joins"}).encode()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/chat/stream",
        "raw_path": b"/api/chat/stream",
        "root_path": "",
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }

    body_sent = False
    disconnect = asyncio.Event()
    sent_events: list[str] = []
    status: list[int] = []

    async def receive():
        nonlocal body_sent
        if not body_sent:
            body_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await disconnect.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            status.append(message["status"])
        elif message["type"] == "http.response.body":
            text = bytes(message.get("body", b"")).decode()
            sent_events.extend(
                line.removeprefix("event: ")
                for line in text.splitlines()
                if line.startswith("event: ")
            )
            if len(sent_events) >= EVENTS_BEFORE_DISCONNECT:
                disconnect.set()

    await asyncio.wait_for(app(scope, receive, send), timeout=15)

    assert status == [200]
    assert sent_events == ["assistant_delta", "assistant_delta"]
    assert len(acompletion_calls) == 1
    call = acompletion_calls[0]
    assert (call["model"], call["stream"], call["tool_choice"]) == (MODEL, True, "auto")
    assert completion_cost_calls == []
    assert embedding_calls == []

    with Session() as db:
        msg = db.execute(
            select(ChatMessage).where(
                ChatMessage.session_id == sid, ChatMessage.role == "assistant"
            )
        ).scalar_one()
        assert (msg.status, msg.content) == ("cancelled", "one two ")
        assert msg.cancelled_at is not None

        # Released exactly once: the 0.02 reserve nets out and only the
        # cancelled iteration's token-math estimate stays on the ledger.
        assert releases == [uid]
        assert cost_meter.current_spend(db, uid) == CANCEL_ESTIMATE
        rows = db.execute(
            select(
                LlmCallLog.purpose, LlmCallLog.model, LlmCallLog.session_id, LlmCallLog.cost_usd
            ).where(LlmCallLog.user_id == uid)
        ).all()
        assert [(p, m, s, Decimal(str(c))) for p, m, s, c in rows] == [
            ("chat", MODEL, sid, CANCEL_ESTIMATE)
        ]


# ---------------------------------------------------------------------------
# #411: the adapter settles in its own transaction
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter_on_postgres(seeded, monkeypatch, fake_llm):
    """The LLM adapter's gate and settlement on the seeded Postgres, behind
    the scripted fake provider (pg_seed binds SessionLocal). Yields the
    seeded (Session, uid, sid)."""
    monkeypatch.setattr(settings, "llm_soft_cap_usd", 2.00)
    monkeypatch.setattr(settings, "llm_hard_cap_usd", 3.00)
    monkeypatch.setattr(settings, "global_daily_cost_cap_usd", None)
    fake_llm.cost = Decimal("0.0005")
    return seeded


def _call_log(db, uid):
    rows = db.execute(
        select(LlmCallLog.purpose, LlmCallLog.cost_usd).where(LlmCallLog.user_id == uid)
    ).all()
    return [(p, Decimal(str(c))) for p, c in rows]


async def test_settlement_survives_a_caller_rollback(adapter_on_postgres):
    from services import llm

    Session, uid, sid = adapter_on_postgres

    with Session() as caller:
        caller.add(ChatMessage(session_id=sid, role="user", content="rolled back"))
        caller.flush()
        await llm.get().aembed(
            ["q"], meter=llm.Meter(user_id=uid, session_id=sid, purpose="embedding")
        )
        caller.rollback()

    with Session() as db:
        assert cost_meter.current_spend(db, uid) == Decimal("0.0005")
        assert _call_log(db, uid) == [("embedding", Decimal("0.0005"))]
        assert db.execute(select(ChatMessage).where(ChatMessage.session_id == sid)).first() is None


def test_settlement_behind_a_held_ledger_row_keeps_the_receipt_and_retries(
    adapter_on_postgres, caplog, monkeypatch
):
    """A caller holding an uncommitted ledger write across a call violates the
    adapter's invariant. Settlement waits on that row lock only until
    lock_timeout, keeps the LlmCallLog row, and returns the result instead of
    hanging; the deferred ledger write lands once the lock is released."""
    import logging
    import threading
    import time

    from services import llm

    Session, uid, sid = adapter_on_postgres
    # Shorter than the production value to keep the test quick.
    monkeypatch.setattr(llm, "SETTLE_LOCK_TIMEOUT", "1s")
    scheduled = []
    monkeypatch.setattr(llm, "_schedule", lambda delay, fn, *a: scheduled.append((fn, a)))

    with Session() as caller:
        cost_meter.record_cost(caller, uid, Decimal("0.01"))  # holds the ledger row
        # On a worker thread so a broken lock_timeout fails this test at the
        # join instead of deadlocking it against the caller's lock.
        outcome: dict = {}

        def call():
            outcome["result"] = llm.get().embed(
                ["q"], meter=llm.Meter(user_id=uid, session_id=sid, purpose="embedding")
            )

        worker = threading.Thread(target=call)
        started = time.monotonic()
        with caplog.at_level(logging.ERROR, logger="services.llm"):
            worker.start()
            worker.join(timeout=10)
        elapsed = time.monotonic() - started
        hung = worker.is_alive()
        with Session() as db:
            # Committed while the caller still holds the ledger row.
            assert _call_log(db, uid) == [("embedding", Decimal("0.0005"))]
        caller.rollback()  # releases the lock, so a hung worker can finish
        worker.join(timeout=10)

    assert not hung, f"settlement hung for {elapsed:.1f}s"
    assert len(outcome["result"].vectors) == 1
    [record] = [r for r in caplog.records if r.name == "services.llm"]
    assert (record.user_id, record.purpose, record.cost_usd) == (uid, "embedding", "0.0005")
    with Session() as db:
        assert cost_meter.current_spend(db, uid) == Decimal("0")

    [(fn, args)] = scheduled
    fn(*args)  # the background retry, now that the row is free

    with Session() as db:
        assert cost_meter.current_spend(db, uid) == Decimal("0.0005")
        assert _call_log(db, uid) == [("embedding", Decimal("0.0005"))]


# ---------------------------------------------------------------------------
# #412: the tutor streams through the adapter
# ---------------------------------------------------------------------------


async def test_tool_turn_with_retrieve_settles_every_call_without_lock_waits(
    adapter_on_postgres, fake_llm, monkeypatch, caplog
):
    """The tutor holds no ledger write across tool dispatch, so the retrieve
    tool's embedding settles at once: chat, embedding and chat each land on
    the ledger, and no settlement is deferred behind a held row lock."""
    from datetime import datetime, timezone

    from agent import tutor
    from agent.types import ToolContext
    from db.models import Document
    from tests.conftest import tool_call

    Session, uid, sid = adapter_on_postgres
    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")
    with Session() as db:
        db.add(Document(session_id=sid, filename="ref.txt", status="ready"))
        db.commit()
    fake_llm.streams = [
        ["Let me look. ", tool_call("retrieve_chunks", {"session_id": sid, "query": "joins"})],
        ["Here it is."],
    ]

    with Session() as db:
        ctx = ToolContext(
            db=db, session_id=sid, user_id=uid, turn_started_at=datetime.now(timezone.utc)
        )
        events = [
            ev
            async for ev in tutor.run_streaming(
                [{"role": "user", "content": "explain joins"}], "sys", ctx
            )
        ]

    assert events[-1].type == "done"
    assert fake_llm.embed_calls == [["joins"]]
    with Session() as db:
        assert cost_meter.current_spend(db, uid) == Decimal("0.0015")
        assert sorted(_call_log(db, uid)) == [
            ("chat", Decimal("0.0005")),
            ("chat", Decimal("0.0005")),
            ("embedding", Decimal("0.0005")),
        ]
    assert not [r for r in caplog.records if "settlement" in r.getMessage()]
