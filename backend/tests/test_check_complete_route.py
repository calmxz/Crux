"""TDD: POST /sessions/{id}/check/complete fires the hidden follow-up."""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from agent.stream_events import StreamEvent
from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from services import check_question_service, pending_check_store, profile_service

USER_ID = "u_done_1"


@pytest.fixture
def seeded_session(db_session):
    db_session.add(User(id=USER_ID))
    session = SessionModel(
        id="s_done_1", user_id=USER_ID, topic="bio",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(session)
    db_session.commit()
    return session


def _resolved_batch(db, sid):
    ctx = ToolContext(db=db, session_id=sid, user_id=USER_ID,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    check_question_service.register(db, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=sid, gap="atp",
        items=[{"question": "Q1?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a."}]))
    check_question_service.answer(db, sid, index=0, selected_index=0)


def _make_fake_run_streaming(db, session_id):
    """Fake run_streaming: persists one assistant message (owns persistence like the
    real tutor) and yields done event. Mirrors test_chat_stream_route.py pattern."""
    async def fake(messages, system_prompt, ctx):
        msg = ChatMessage(session_id=session_id, role="assistant",
                          content="Great job!")
        ctx.db.add(msg)
        ctx.db.commit()
        yield StreamEvent("assistant_delta", {"text": "Great job!"})
        yield StreamEvent("done", {"message_id": str(msg.id)})
    return fake


@pytest.fixture
def resolved_diagnostic_batch_session(db_session):
    """A diagnostic batch fully resolved by writing pending_check_json DIRECTLY
    onto the session row -- bypassing check_question_service.answer(), which
    would grade. Simulates the F-24 crash window: the per-item grade call
    never ran (e.g. process died right after the answer commit), but the
    batch itself is fully done. knowledge_level must still be None here."""
    db_session.add(User(id=USER_ID))
    row = SessionModel(
        id="s_diag_backstop", user_id=USER_ID, topic="bio",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(row)
    db_session.commit()
    ctx = ToolContext(db=db_session, session_id=row.id, user_id=USER_ID,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                      diagnostic_required=True)
    check_question_service.register(db_session, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=row.id, gap="atp",
        items=[{"question": "Q1?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a."}]))
    pc = check_question_service.get_pending_check(db_session, row.id)
    pc["items"][0]["status"] = "answered"
    pc["items"][0]["selected_index"] = 0
    pc["items"][0]["correct"] = True
    pc["current_index"] = 1
    row.pending_check_json = json.dumps(pc)
    db_session.commit()
    return row.id


def test_complete_grades_diagnostic_before_clearing(client, db_session, resolved_diagnostic_batch_session, monkeypatch):
    # F-24 crash-window backstop: the batch is fully resolved but
    # grade_if_diagnostic never ran per-item. POST /check/complete must grade
    # before clearing the batch.
    sid = resolved_diagnostic_batch_session
    monkeypatch.setattr("agent.tutor.run_streaming",
                        _make_fake_run_streaming(db_session, sid))
    assert profile_service.load_profile(db_session, sid).knowledge_level is None
    resp = client.post(f"/api/sessions/{sid}/check/complete", json={"user_id": USER_ID})
    assert resp.status_code == 200
    assert profile_service.load_profile(db_session, sid).knowledge_level is not None


def test_complete_streams_reply_clears_batch_no_user_message(client, db_session, seeded_session, monkeypatch):
    sid = seeded_session.id
    _resolved_batch(db_session, sid)

    monkeypatch.setattr("agent.tutor.run_streaming",
                        _make_fake_run_streaming(db_session, sid))

    r = client.post(f"/api/sessions/{sid}/check/complete", json={"user_id": USER_ID})
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    body = r.text
    assert "event: done" in body
    assert check_question_service.get_pending_check(db_session, sid) is None
    rows = db_session.execute(
        select(ChatMessage).where(ChatMessage.session_id == sid)
    ).scalars().all()
    assert [m.role for m in rows] == ["assistant"]


def test_complete_409_when_not_done(client, db_session, seeded_session, monkeypatch):
    sid = seeded_session.id
    ctx = ToolContext(db=db_session, session_id=sid, user_id=USER_ID,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    check_question_service.register(db_session, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=sid, gap="g",
        items=[{"question": "q", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a."}]))
    monkeypatch.setattr("agent.tutor.run_streaming",
                        _make_fake_run_streaming(db_session, sid))
    r = client.post(f"/api/sessions/{sid}/check/complete", json={"user_id": USER_ID})
    assert r.status_code == 409


def test_complete_409_when_no_batch(client, db_session, seeded_session, monkeypatch):
    sid = seeded_session.id
    monkeypatch.setattr("agent.tutor.run_streaming",
                        _make_fake_run_streaming(db_session, sid))
    r = client.post(f"/api/sessions/{sid}/check/complete", json={"user_id": USER_ID})
    assert r.status_code == 409


def test_complete_foreign_session_404(client, db_session, monkeypatch):
    db_session.add(User(id=USER_ID))
    db_session.commit()
    monkeypatch.setattr("agent.tutor.run_streaming",
                        _make_fake_run_streaming(db_session, "nope"))
    r = client.post("/api/sessions/nope/check/complete", json={"user_id": USER_ID})
    assert r.status_code == 404


def test_complete_on_ended_session_is_409(client, db_session, seeded_session, monkeypatch):
    sid = seeded_session.id
    _resolved_batch(db_session, sid)
    seeded_session.ended_at = datetime.now(timezone.utc)
    db_session.commit()
    monkeypatch.setattr("agent.tutor.run_streaming",
                        _make_fake_run_streaming(db_session, sid))
    r = client.post(f"/api/sessions/{sid}/check/complete", json={"user_id": USER_ID})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "session_ended"


def _resolved_batch_miss(db, sid):
    """Same as _resolved_batch but answers WRONG (selected_index=1, correct=0)."""
    ctx = ToolContext(db=db, session_id=sid, user_id=USER_ID,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    check_question_service.register(db, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=sid, gap="atp",
        items=[{"question": "Q1?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a."}]))
    check_question_service.answer(db, sid, index=0, selected_index=1)


def test_complete_sets_quiz_cooldown_on_miss(client, db_session, seeded_session, monkeypatch):
    sid = seeded_session.id
    _resolved_batch_miss(db_session, sid)
    monkeypatch.setattr("agent.tutor.run_streaming",
                        _make_fake_run_streaming(db_session, sid))
    r = client.post(f"/api/sessions/{sid}/check/complete", json={"user_id": USER_ID})
    assert r.status_code == 200
    cd = check_question_service.get_quiz_cooldown(db_session, sid)
    assert cd is not None
    assert cd["gap"] == "atp"
    assert cd["last_score"] == "0/1"


def test_complete_no_cooldown_on_all_correct(client, db_session, seeded_session, monkeypatch):
    sid = seeded_session.id
    _resolved_batch(db_session, sid)  # answers correctly
    monkeypatch.setattr("agent.tutor.run_streaming",
                        _make_fake_run_streaming(db_session, sid))
    r = client.post(f"/api/sessions/{sid}/check/complete", json={"user_id": USER_ID})
    assert r.status_code == 200
    assert check_question_service.get_quiz_cooldown(db_session, sid) is None


def test_complete_writes_check_batch_to_message(client, db_session, seeded_session, monkeypatch):
    sid = seeded_session.id
    _resolved_batch(db_session, sid)
    m = ChatMessage(session_id=sid, role="assistant", content="")
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    check_question_service.attach_message_id(db_session, sid, m.id)

    monkeypatch.setattr("agent.tutor.run_streaming",
                        _make_fake_run_streaming(db_session, sid))

    r = client.post(f"/api/sessions/{sid}/check/complete", json={"user_id": USER_ID})
    assert r.status_code == 200

    db_session.refresh(m)
    assert m.check_batch_json is not None
    data = json.loads(m.check_batch_json)
    assert data["gap"] == "atp"
    assert data["items"][0]["correct"] is True
    assert check_question_service.get_pending_check(db_session, sid) is None


def test_complete_check_claims_batch_under_row_lock(client, db_session, seeded_session, monkeypatch):
    """B-02: the route must take the session row lock BEFORE reading the
    batch, so a concurrent caller blocks on the winner's clear commit and
    re-reads an empty batch (409). SQLite cannot exercise the real race, so
    this asserts the claim ordering.
    """
    sid = seeded_session.id
    _resolved_batch(db_session, sid)
    monkeypatch.setattr(
        "agent.tutor.run_streaming", _make_fake_run_streaming(db_session, sid)
    )

    events = []
    real_lock = profile_service.lock_session_row

    def lock_spy(db, session_id):
        events.append("lock")
        return real_lock(db, session_id)

    monkeypatch.setattr(profile_service, "lock_session_row", lock_spy)

    real_get = pending_check_store.get_pending_check

    def get_spy(db, session_id):
        events.append("get")
        return real_get(db, session_id)

    monkeypatch.setattr(pending_check_store, "get_pending_check", get_spy)

    resp = client.post(f"/api/sessions/{sid}/check/complete", json={"user_id": USER_ID})
    assert resp.status_code == 200
    assert "lock" in events and "get" in events
    assert events.index("lock") < events.index("get"), (
        f"batch read before row lock -- double-fire window open (events={events})"
    )
