"""Task 13: Tests for POST /api/chat/stream (SSE).

These tests are written FIRST (TDD). They will fail until the route is implemented.

Setup mirrors test_chat.py exactly: uses the `client` and `db_session` fixtures
from conftest.py, seeds a SessionModel, and patches tutor.run_streaming at the
module level so _prepare_turn still runs for real (cost/rate checks, session
lookup, user-message persistence).

Auth note: the _AuthInjectingClient shim only intercepts `.request()`, NOT
`.stream()`. For streaming tests we pass `Authorization: Bearer test-<user_id>`
explicitly in headers and omit `user_id` from the JSON body (ChatRequest has
extra="forbid" so extra fields cause 422).

Disconnect/cancellation note
-----------------------------
The sync Starlette TestClient does not reliably trigger `request.is_disconnected()`
under ASGI test transport - there is no network layer to disconnect. Attempting to
force a network-level disconnect test produces flaky/non-deterministic results.

Instead, we test the cancellation WIRING via a focused unit test: a fake
run_streaming that yields a `cancelled` terminal event (simulating what the real
agent yields after asyncio.CancelledError) confirms that the stream terminates
cleanly after that event and does not hang. True network-disconnect cancellation
(the `await request.is_disconnected()` guard path) is verified manually against
a running server; it is not reliably testable under TestClient.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, func, select

from agent.stream_events import StreamEvent
from contracts import ChatRequest, TopicProfile
from db.models import Session as SessionModel
from db.models import UsageCounter, User
from routes.chat import _prepare_turn
from services import rate_limit, summary_service

SESSION_ID = "stream-s1"
USER_ID = "stream-u1"
AUTH_HEADERS = {"Authorization": f"Bearer test-{USER_ID}"}


@pytest.fixture(autouse=True)
def seed_session(db_session):
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


def _make_fake_run_streaming(*events):
    """Return an async generator function that yields the given StreamEvent objects."""
    async def fake(messages, system_prompt, ctx):
        for event in events:
            yield event
    return fake


# ---------------------------------------------------------------------------
# Test: content-type
# ---------------------------------------------------------------------------


def test_chat_stream_content_type(client, monkeypatch):
    """POST /api/chat/stream returns 200 with text/event-stream content-type."""
    fake = _make_fake_run_streaming(
        StreamEvent("assistant_delta", {"text": "Hi"}),
        StreamEvent("done", {"message_id": "1"}),
    )
    monkeypatch.setattr("agent.tutor.run_streaming", fake)

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "hello"},
        headers=AUTH_HEADERS,
    ) as resp:
        assert resp.status_code == 200
        ct = resp.headers.get("content-type", "")
        assert ct.startswith("text/event-stream")


# ---------------------------------------------------------------------------
# Test: delta then done events appear in order
# ---------------------------------------------------------------------------


def test_chat_stream_emits_delta_then_done(client, monkeypatch):
    """Stream body contains event: assistant_delta before event: done."""
    fake = _make_fake_run_streaming(
        StreamEvent("assistant_delta", {"text": "Hi"}),
        StreamEvent("done", {"message_id": "42"}),
    )
    monkeypatch.setattr("agent.tutor.run_streaming", fake)

    lines = []
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "hello"},
        headers=AUTH_HEADERS,
    ) as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            lines.append(line)

    body = "\n".join(lines)
    delta_pos = body.find("event: assistant_delta")
    done_pos = body.find("event: done")
    assert delta_pos != -1, "expected event: assistant_delta in stream"
    assert done_pos != -1, "expected event: done in stream"
    assert delta_pos < done_pos, "assistant_delta must precede done"


# ---------------------------------------------------------------------------
# Test: unknown session -> 404 (pre-flight guard applies to stream route)
# ---------------------------------------------------------------------------


def test_chat_stream_unknown_session_404(client, monkeypatch):
    """_prepare_turn raises 404 before StreamingResponse is returned.
    HTTPException propagates as a normal 404 JSON response."""
    fake = _make_fake_run_streaming(
        StreamEvent("done", {"message_id": "1"}),
    )
    monkeypatch.setattr("agent.tutor.run_streaming", fake)

    r = client.post(
        "/api/chat/stream",
        json={"session_id": "does-not-exist", "message": "x"},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Test: ended session -> 409 session_ended (F-05)
# ---------------------------------------------------------------------------


def test_chat_stream_on_ended_session_returns_409(client, db_session, monkeypatch):
    """_prepare_turn must reject chat turns on an ended session before any
    tutor/LLM work happens."""
    fake = _make_fake_run_streaming(
        StreamEvent("done", {"message_id": "1"}),
    )
    monkeypatch.setattr("agent.tutor.run_streaming", fake)

    session = db_session.get(SessionModel, SESSION_ID)
    session.ended_at = datetime.now(timezone.utc)
    db_session.commit()

    r = client.post(
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "hi"},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "session_ended"


# ---------------------------------------------------------------------------
# Test: cancellation wiring - cancelled terminal event ends the stream cleanly
# ---------------------------------------------------------------------------


def test_chat_stream_cancelled_event_terminates_stream(client, monkeypatch):
    """When run_streaming yields a 'cancelled' terminal event, the stream
    terminates without hanging or emitting further events.

    This verifies the cancellation-wiring logic (the `if event.type in
    ('done', 'error', 'cancelled'): break` guard in event_stream). It does NOT
    test the network-disconnect path (request.is_disconnected()), which is not
    reliably exercisable under the sync TestClient ASGI transport.
    """
    fake = _make_fake_run_streaming(
        StreamEvent("assistant_delta", {"text": "partial"}),
        StreamEvent(
            "cancelled",
            {"message_id": "99", "partial_content_chars": 7, "estimated_cost_usd": "0"},
        ),
        # Any event after cancelled must NOT appear in the stream output.
        StreamEvent("assistant_delta", {"text": "should not appear"}),
    )
    monkeypatch.setattr("agent.tutor.run_streaming", fake)

    lines = []
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "hello"},
        headers=AUTH_HEADERS,
    ) as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            lines.append(line)

    body = "\n".join(lines)
    assert "event: cancelled" in body
    assert "should not appear" not in body


def test_chat_stream_includes_quiz_readiness(client, db_session, monkeypatch):
    from services import check_question_service
    check_question_service.set_quiz_cooldown(
        db_session, SESSION_ID, {"gap": "joins", "last_score": "0/1", "missed": ["q0"]}
    )

    captured = {}

    async def fake(messages, system_prompt, ctx):
        captured["system_prompt"] = system_prompt
        yield StreamEvent("done", {"message_id": "1"})

    monkeypatch.setattr("agent.tutor.run_streaming", fake)

    with client.stream(
        "POST", "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "hello"},
        headers=AUTH_HEADERS,
    ) as resp:
        assert resp.status_code == 200
        for _ in resp.iter_lines():
            pass

    # Assert on the session-specific rendered QUIZ_READINESS line, not the bare
    # word "cooling_down" (which also appears in the immutable POST-QUIZ PROTOCOL
    # prose). "gap": "joins" can only come from threading this turn's cooldown.
    sp = captured["system_prompt"]
    assert '"gap": "joins"' in sp
    assert '"status": "cooling_down"' in sp


# ---------------------------------------------------------------------------
# Test: post-stream rolling summary trigger (Task 5, P2 AC3)
# ---------------------------------------------------------------------------


def test_stream_schedules_rolling_summary(client, monkeypatch):
    """The stream response attaches a BackgroundTask that calls
    summary_service.update_rolling_summary(db, session_id) after the SSE
    body is fully consumed. TestClient runs background tasks once the
    response completes, so a synchronous .post() (which reads the full
    body) is enough to observe the call."""
    fake = _make_fake_run_streaming(
        StreamEvent("assistant_delta", {"text": "Hi"}),
        StreamEvent("done", {"message_id": "1"}),
    )
    monkeypatch.setattr("agent.tutor.run_streaming", fake)

    calls = []

    async def fake_update(db, session_id):
        calls.append(session_id)
        return None

    monkeypatch.setattr(summary_service, "update_rolling_summary", fake_update)

    resp = client.post(
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "hello"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    _ = resp.text  # drain the SSE body; TestClient runs background tasks after

    assert calls == [SESSION_ID]


def test_semantic_fallback_escalates_gate(client, monkeypatch):
    """D2.2: lexical gate is False (default empty kw_index_json), so the
    semantic fallback runs and its True result escalates retrieval_required
    all the way through to _build_prompt_state."""
    message = "hello"
    calls = {}

    async def fake_fallback(db, session_id, query, *, user_id=None, cost_holder=None):
        calls["args"] = (session_id, query)
        calls["user_id"] = user_id
        return True, None

    monkeypatch.setattr(
        "routes.chat.retrieval_service.semantic_fallback_required", fake_fallback
    )

    captured = {}
    from routes import chat as chat_module

    real_build = chat_module._build_prompt_state

    def spy_build(**kwargs):
        captured["retrieval_required"] = kwargs.get("retrieval_required")
        return real_build(**kwargs)

    monkeypatch.setattr(chat_module, "_build_prompt_state", spy_build)

    fake = _make_fake_run_streaming(StreamEvent("done", {"message_id": "1"}))
    monkeypatch.setattr("agent.tutor.run_streaming", fake)

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": message},
        headers=AUTH_HEADERS,
    ) as resp:
        assert resp.status_code == 200
        for _ in resp.iter_lines():
            pass

    assert calls["args"] == (SESSION_ID, message)
    assert calls["user_id"] == USER_ID  # F-19: caller must attribute the metered call
    assert captured["retrieval_required"] is True


def test_semantic_fallback_not_called_when_lexical_gate_true(client, db_session, monkeypatch):
    """D2.2: when the lexical gate already matches, the semantic fallback
    must never run. A raising stub proves the OPTIONAL-only escalation
    path (the `if not retrieval_required:` guard) is respected."""
    import json

    from lib import keyword_index

    message = "explain foreign keys"
    stems = keyword_index.build_from_text(message)
    session = db_session.get(SessionModel, SESSION_ID)
    session.kw_index_json = json.dumps(sorted(stems))
    db_session.commit()

    def fail_if_called(db, session_id, query):
        raise AssertionError("fallback must not run when lexical gate is True")

    monkeypatch.setattr(
        "routes.chat.retrieval_service.semantic_fallback_required", fail_if_called
    )

    fake = _make_fake_run_streaming(StreamEvent("done", {"message_id": "1"}))
    monkeypatch.setattr("agent.tutor.run_streaming", fake)

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": message},
        headers=AUTH_HEADERS,
    ) as resp:
        assert resp.status_code == 200
        for _ in resp.iter_lines():
            pass


def test_stream_rolling_summary_failure_does_not_break_turn(client, monkeypatch):
    """A raising update_rolling_summary must not surface to the client: the
    chat turn already completed and sent its response before the background
    task runs. The helper's try/except/finally is what's under test here."""
    fake = _make_fake_run_streaming(
        StreamEvent("assistant_delta", {"text": "Hi"}),
        StreamEvent("done", {"message_id": "1"}),
    )
    monkeypatch.setattr("agent.tutor.run_streaming", fake)

    async def fake_update_raises(db, session_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(summary_service, "update_rolling_summary", fake_update_raises)

    resp = client.post(
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "hello"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.text  # drain the SSE body; background task raises after this
    assert "event: done" in body


# ---------------------------------------------------------------------------
# Task 3: _prepare_turn ordering - F-36 + Batch-1 deferred rate-limit slot
#
# Session.user_id has a FK to users.id (db/models.py), but the db_session
# fixture's sqlite engine (tests/conftest.py) never issues `PRAGMA
# foreign_keys=ON`, so sqlite does not enforce it here. That lets these tests
# re-home a session onto a not-yet-created user id and then delete any
# pre-existing row for that id, producing the "valid JWT, no users row" state
# F-36 targets, without a delete-blocked-by-FK failure.
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded_session(db_session):
    uid = "prep-guard-user"
    db_session.add(User(id=uid))
    sess = SessionModel(id="prep-guard-session", user_id=uid, topic="algebra")
    db_session.add(sess)
    db_session.commit()
    return sess


@pytest.fixture
def seeded_ended_session(db_session):
    uid = "prep-guard-ended-user"
    db_session.add(User(id=uid))
    sess = SessionModel(
        id="prep-guard-ended-session",
        user_id=uid,
        topic="algebra",
        ended_at=datetime.now(timezone.utc),
    )
    db_session.add(sess)
    db_session.commit()
    return sess


def _today_counter_count(db):
    return db.execute(select(func.count()).select_from(UsageCounter)).scalar_one()


def test_ended_session_409_consumes_no_rate_slot(db_session, seeded_ended_session):
    """Batch-1 deferral: a 409'd turn must not burn a daily rate-limit slot."""
    req = ChatRequest(session_id=seeded_ended_session.id, message="hi")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(_prepare_turn(req, seeded_ended_session.user_id, db_session))
    assert exc.value.status_code == 409
    assert _today_counter_count(db_session) == 0


def test_foreign_session_404_consumes_no_rate_slot(db_session, seeded_session):
    req = ChatRequest(session_id=seeded_session.id, message="hi")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(_prepare_turn(req, "someone-else", db_session))
    assert exc.value.status_code == 404
    assert _today_counter_count(db_session) == 0


def test_first_turn_creates_user_before_rate_limit_insert(db_session, seeded_session, monkeypatch):
    """F-36: the users row must exist when check_and_increment INSERTs the
    FK-bearing usage_counters row (sqlite doesn't enforce the FK; assert
    ordering explicitly)."""
    new_uid = "brand-new-user"
    # Re-home the seeded session onto the new user so the session guard passes.
    seeded_session.user_id = new_uid
    db_session.commit()
    db_session.execute(delete(User).where(User.id == new_uid))
    db_session.commit()

    real = rate_limit.check_and_increment

    def spy(db, uid):
        assert db.execute(select(User.id).where(User.id == uid)).scalar_one_or_none() is not None, (
            "usage-counter insert would FK-violate: users row missing"
        )
        return real(db, uid)

    monkeypatch.setattr(rate_limit, "check_and_increment", spy)
    asyncio.run(_prepare_turn(ChatRequest(session_id=seeded_session.id, message="hi"), new_uid, db_session))
    assert db_session.get(User, new_uid) is not None


# ---------------------------------------------------------------------------
# Test: disconnect must drain the producer before the reserve is released
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disconnect_drains_producer_before_releasing_reserve(
    db_session, monkeypatch
):
    """B-05: on a real client disconnect the ambient anyio cancel scope is
    cancelled level-triggered, so an unshielded `await task` in the finally
    returns immediately (its CancelledError swallowed) while the tutor's
    cancel arm is still mid-unwind. _release_reserve then rolls back the
    shared Session and discards the pending 'cancelled' assistant message.

    The drain must therefore run under the same shield as the release, so the
    producer has fully finished with ctx.db before the release touches it.
    """
    from types import SimpleNamespace

    import anyio

    from db.models import ChatMessage
    from routes import chat as chat_route
    from services import cost_meter

    state = {"arm_done": False, "release_saw_arm_done": None}
    started = asyncio.Event()

    async def fake_run_streaming(messages, system_prompt, ctx):
        try:
            yield StreamEvent("assistant_delta", {"text": "partial"})
            started.set()
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            # Mirrors tutor.py's cancel arm: the row is staged on ctx.db, then
            # the arm suspends (draining its shielded tool dispatch) before the
            # commit. A rollback from another coroutine in that window loses it.
            ctx.db.add(
                ChatMessage(
                    session_id=SESSION_ID,
                    role="assistant",
                    content="partial",
                    status="cancelled",
                    cancelled_at=datetime.now(timezone.utc),
                )
            )
            await asyncio.sleep(0.05)
            ctx.db.commit()
            state["arm_done"] = True
            raise

    monkeypatch.setattr("agent.tutor.run_streaming", fake_run_streaming)
    monkeypatch.setattr(chat_route, "accepted_terms_from_request", lambda r: False)

    real_release = chat_route._release_reserve

    def spy_release(db, user_id):
        state["release_saw_arm_done"] = state["arm_done"]
        return real_release(db, user_id)

    monkeypatch.setattr(chat_route, "_release_reserve", spy_release)

    async def _not_disconnected():
        return False

    request = SimpleNamespace(headers={}, is_disconnected=_not_disconnected)

    resp = await chat_route.chat_stream(
        ChatRequest(session_id=SESSION_ID, message="hello"),
        request,
        user_id=USER_ID,
        db=db_session,
    )

    async def consume():
        async for _chunk in resp.body_iterator:
            pass

    async with anyio.create_task_group() as tg:
        tg.start_soon(consume)
        await started.wait()
        # Simulate Starlette's disconnect handling: cancel the scope the
        # response body iterator runs in.
        tg.cancel_scope.cancel()

    assert state["release_saw_arm_done"] is True, (
        "_release_reserve ran while the tutor producer was still unwinding"
    )
    cancelled = (
        db_session.execute(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.status == "cancelled")
        ).scalar_one()
    )
    assert cancelled == 1, "the cancelled assistant message was not persisted"
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0000"), (
        "the per-turn reserve was left on the ledger"
    )


@pytest.mark.asyncio
async def test_prepare_failure_under_cancel_releases_the_reservation(
    db_session, seeded_session, monkeypatch
):
    """#421: a cancel after the cost reservation (B-05) is committed, but
    before the stream starts, must still hand the reservation back. Under a
    level-triggered cancel an unshielded release is cancelled with it.
    """
    import anyio

    from routes import chat as chat_route
    from services import cost_meter

    uid = seeded_session.user_id
    before = cost_meter.current_spend(db_session, uid)
    reserved = asyncio.Event()

    async def hang_after_guards(*args, **kwargs):
        reserved.set()
        await asyncio.sleep(3600)

    monkeypatch.setattr(chat_route, "_prepare_turn_after_guards", hang_after_guards)

    async def prepare():
        await _prepare_turn(
            ChatRequest(session_id=seeded_session.id, message="hi"), uid, db_session
        )

    async with anyio.create_task_group() as tg:
        tg.start_soon(prepare)
        await reserved.wait()
        assert cost_meter.current_spend(db_session, uid) > before
        tg.cancel_scope.cancel()

    assert cost_meter.current_spend(db_session, uid) == before, (
        "the per-turn reservation was left on the ledger"
    )
