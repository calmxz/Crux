"""#340 "early stop = skip", via the Stop button.

POST /sessions/{id}/check/stop ends the check in progress: the open set's
remaining items are graded as skipped, a diagnostic is graded from what was
answered, and the tutor's reaction streams like /check/complete's. A chat
message never stops a check: the set stays open while the learner asks about
the question.
"""

from datetime import datetime, timezone

import pytest

from agent.stream_events import StreamEvent
from agent.types import ToolContext
from config import settings
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from services import check_question_service as cq
from services import pending_check_store as pcs
from services import profile_service, rate_limit

USER_ID = "u_check_stop"
SESSION_ID = "s_check_stop"
AUTH_HEADERS = {"Authorization": f"Bearer test-{USER_ID}"}
LEARNER_TEXT = "what does option B mean?"


@pytest.fixture(autouse=True)
def seed_session(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(SessionModel(
        id=SESSION_ID, user_id=USER_ID, topic="biology",
        topic_profile_json=TopicProfile(knowledge_level="beginner").model_dump_json(),
    ))
    db_session.commit()


def _ctx(db, suppress=False, diagnostic=False):
    return ToolContext(
        db=db, session_id=SESSION_ID, user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc), suppress_check=suppress,
        diagnostic_required=diagnostic,
    )


def _register(db, set_index, set_total, gap, ctx=None):
    res = cq.register(db, ctx or _ctx(db), AskCheckQuestionsArgs(
        session_id=SESSION_ID, gap=gap, set_index=set_index, set_total=set_total,
        items=[
            {"question": f"{gap} Q{n}?", "options": ["a", "b"],
             "correct_index": 0, "explanation": "e."}
            for n in range(2)
        ],
    ))
    assert res.ok, res.error


def _fake_tutor(monkeypatch):
    captured = {}

    async def fake(messages, system_prompt, ctx):
        captured.update(messages=messages, system_prompt=system_prompt, ctx=ctx)
        msg = ChatMessage(session_id=SESSION_ID, role="assistant", content="Why stop?")
        ctx.db.add(msg)
        ctx.db.commit()
        yield StreamEvent("done", {"message_id": str(msg.id)})

    monkeypatch.setattr("agent.tutor.run_streaming", fake)
    return captured


def _stream(client, method_path, json=None):
    with client.stream("POST", method_path, json=json, headers=AUTH_HEADERS) as resp:
        body = "".join(resp.iter_text())
        return resp.status_code, body


def _stop(client):
    return _stream(client, f"/api/sessions/{SESSION_ID}/check/stop")


def test_stop_mid_set_grades_remaining_as_skipped_and_reacts(client, db_session, monkeypatch):
    _register(db_session, 1, 2, "glycolysis")
    cq.answer(db_session, SESSION_ID, 0, 0)
    captured = _fake_tutor(monkeypatch)

    status, _body = _stop(client)

    assert status == 200
    last = captured["messages"][-1]
    assert last["role"] == "user"
    assert last["content"].startswith(
        "[check results] gap=glycolysis: 1/1 correct. learner stopped at set 1 of 2."
    )
    assert "  Q2 skipped." in last["content"]
    assert captured["ctx"].suppress_check is True
    db_session.expire_all()
    assert cq.get_pending_check(db_session, SESSION_ID) is None
    assert pcs.get_current_check(db_session, SESSION_ID) is None
    assert cq.get_quiz_cooldown(db_session, SESSION_ID)["gap"] == "glycolysis"
    # The synthetic summary is never persisted as a user turn.
    assert db_session.query(ChatMessage).filter_by(
        session_id=SESSION_ID, role="user"
    ).count() == 0


def test_stop_between_sets_records_where_the_learner_stopped(client, db_session, monkeypatch):
    _register(db_session, 1, 3, "glycolysis")
    cq.answer(db_session, SESSION_ID, 0, 0)
    cq.answer(db_session, SESSION_ID, 1, 0)
    cq.close_set(db_session, SESSION_ID, cq.get_pending_check(db_session, SESSION_ID))
    captured = _fake_tutor(monkeypatch)

    status, _body = _stop(client)

    assert status == 200
    assert captured["messages"][-1]["content"] == (
        "[check results] learner stopped at set 1 of 3."
    )
    db_session.expire_all()
    assert pcs.get_current_check(db_session, SESSION_ID) is None


def test_stop_mid_diagnostic_prompts_from_the_graded_profile(client, db_session, monkeypatch):
    row = db_session.get(SessionModel, SESSION_ID)
    row.topic_profile_json = TopicProfile().model_dump_json()
    db_session.commit()
    _register(db_session, 1, 3, "glycolysis", ctx=_ctx(db_session, diagnostic=True))
    cq.answer(db_session, SESSION_ID, 0, 0)
    captured = _fake_tutor(monkeypatch)

    status, _body = _stop(client)

    assert status == 200
    db_session.expire_all()
    # 1 right of 2 posed -> beginner, graded before the follow-up turn.
    assert profile_service.load_profile(db_session, SESSION_ID).knowledge_level == "beginner"
    assert captured["ctx"].diagnostic_required is False


def test_stop_with_no_check_in_progress_409s(client, monkeypatch):
    _fake_tutor(monkeypatch)
    status, body = _stop(client)
    assert status == 409
    assert "no_open_check" in body


def test_stop_on_a_fully_answered_set_409s(client, db_session, monkeypatch):
    """The set is /check/complete's to close; stopping it would race that call."""
    _register(db_session, 1, 1, "glycolysis")
    cq.answer(db_session, SESSION_ID, 0, 0)
    cq.answer(db_session, SESSION_ID, 1, 0)
    _fake_tutor(monkeypatch)
    status, body = _stop(client)
    assert status == 409
    assert "no_open_check" in body


def test_stop_at_daily_cap_still_stops_but_skips_the_reaction(client, db_session, monkeypatch):
    _register(db_session, 1, 1, "glycolysis")
    for _ in range(settings.daily_cap):
        rate_limit.check_and_increment(db_session, USER_ID)
    _fake_tutor(monkeypatch)

    status, body = _stop(client)

    assert status == 200
    assert "followup_skipped" in body
    db_session.expire_all()
    assert cq.get_pending_check(db_session, SESSION_ID) is None


def test_chat_message_mid_set_leaves_the_set_open(client, db_session, monkeypatch):
    _register(db_session, 1, 2, "glycolysis")
    cq.answer(db_session, SESSION_ID, 0, 0)
    captured = _fake_tutor(monkeypatch)

    status, _body = _stream(
        client, "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": LEARNER_TEXT},
    )

    assert status == 200
    assert captured["messages"][-1] == {"role": "user", "content": LEARNER_TEXT}
    assert '"current_question": {"question": "glycolysis Q1?"' in captured["system_prompt"]
    db_session.expire_all()
    pc = cq.get_pending_check(db_session, SESSION_ID)
    assert pc is not None and pc["current_index"] == 1
    assert pcs.get_current_check(db_session, SESSION_ID)["last_set_index"] == 1


def test_chat_between_sets_tells_the_tutor_to_pose_the_next_set(client, db_session, monkeypatch):
    _register(db_session, 1, 3, "glycolysis")
    cq.answer(db_session, SESSION_ID, 0, 0)
    cq.answer(db_session, SESSION_ID, 1, 0)
    cq.close_set(db_session, SESSION_ID, cq.get_pending_check(db_session, SESSION_ID))
    captured = _fake_tutor(monkeypatch)

    _stream(client, "/api/chat/stream", json={"session_id": SESSION_ID, "message": "ok"})

    assert (
        'PENDING_CHECK: {"between_sets": true, "last_set_index": 1, "set_total": 3}'
        in captured["system_prompt"]
    )
