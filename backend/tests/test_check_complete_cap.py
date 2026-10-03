"""S2: the hidden follow-up turn after a resolved batch must count against
the daily message cap, and cap exhaustion must never block grading."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from agent.stream_events import StreamEvent
from agent.types import ToolContext
from config import settings
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, UsageCounter, User
from db.models import Session as SessionModel
from services import check_question_service, rate_limit

USER_ID = "u_cap_1"


@pytest.fixture
def resolved_batch_session(db_session):
    """Session with a fully-answered (resolved) pending check batch.

    Answered incorrectly so a quiz cooldown is always written on resolution
    (see check_question_service.build_quiz_cooldown) -- lets the cap test
    assert the cooldown persists even when the follow-up turn is skipped.
    """
    db_session.add(User(id=USER_ID))
    session = SessionModel(
        id="s_cap_resolved", user_id=USER_ID, topic="bio",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(session)
    db_session.commit()
    ctx = ToolContext(db=db_session, session_id=session.id, user_id=USER_ID,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    check_question_service.register(db_session, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=session.id, gap="atp",
        items=[{"question": "Q1?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a."}]))
    check_question_service.answer(db_session, session.id, index=0, selected_index=1)
    return session.id, USER_ID


@pytest.fixture
def open_batch_session(db_session):
    """Session with a still-open (not fully answered) pending check batch."""
    db_session.add(User(id=USER_ID))
    session = SessionModel(
        id="s_cap_open", user_id=USER_ID, topic="bio",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(session)
    db_session.commit()
    ctx = ToolContext(db=db_session, session_id=session.id, user_id=USER_ID,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    check_question_service.register(db_session, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=session.id, gap="atp",
        items=[{"question": "Q1?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a."},
               {"question": "Q2?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a."}]))
    return session.id, USER_ID


def _exhaust_cap(db, user_id):
    for _ in range(settings.daily_cap):
        allowed, _n = rate_limit.check_and_increment(db, user_id)
        assert allowed


def _rate_limit_count(db, user_id):
    date_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = db.execute(
        select(UsageCounter).where(
            UsageCounter.user_id == user_id,
            UsageCounter.date_utc == date_utc,
        )
    ).scalar_one_or_none()
    return row.count if row else 0


def _make_fake_run_streaming(session_id):
    """Fake run_streaming: persists one assistant message (owns persistence like
    the real tutor) and yields a done event. Mirrors test_check_complete_route.py."""
    async def fake(messages, system_prompt, ctx):
        msg = ChatMessage(session_id=session_id, role="assistant", content="Great job!")
        ctx.db.add(msg)
        ctx.db.commit()
        yield StreamEvent("assistant_delta", {"text": "Great job!"})
        yield StreamEvent("done", {"message_id": str(msg.id)})
    return fake


def test_followup_increments_daily_counter(client, db_session, resolved_batch_session, monkeypatch):
    sid, user_id = resolved_batch_session
    monkeypatch.setattr("agent.tutor.run_streaming", _make_fake_run_streaming(sid))
    before = _rate_limit_count(db_session, user_id)
    r = client.post(f"/api/sessions/{sid}/check/complete", json={"user_id": user_id})
    assert r.status_code == 200
    assert _rate_limit_count(db_session, user_id) == before + 1


def test_cap_hit_skips_followup_but_batch_still_clears(client, db_session, resolved_batch_session, monkeypatch):
    sid, user_id = resolved_batch_session
    monkeypatch.setattr("agent.tutor.run_streaming", _make_fake_run_streaming(sid))
    _exhaust_cap(db_session, user_id)
    r = client.post(f"/api/sessions/{sid}/check/complete", json={"user_id": user_id})
    assert r.status_code == 200
    body = r.text
    assert "event: followup_skipped" in body
    assert '"reason": "daily_cap"' in body
    assert "assistant_delta" not in body  # no LLM turn ran
    # batch cleared and cooldown written despite the cap
    assert check_question_service.get_pending_check(db_session, sid) is None
    assert check_question_service.get_quiz_cooldown(db_session, sid) is not None


def test_answer_and_skip_do_not_touch_counter(client, db_session, open_batch_session):
    sid, user_id = open_batch_session
    before = _rate_limit_count(db_session, user_id)
    r = client.post(
        f"/api/sessions/{sid}/check/answer",
        json={"index": 0, "selected_index": 0, "user_id": user_id},
    )
    assert r.status_code == 200
    assert _rate_limit_count(db_session, user_id) == before
