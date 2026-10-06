"""TDD: POST /sessions/{id}/check/answer over a batch."""

import json
from datetime import datetime, timezone

import pytest

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from services import check_question_service, profile_service

USER_ID = "u_ans_1"


@pytest.fixture
def seeded_session(db_session):
    # knowledge_level set so register() tags this batch "check" (not
    # "diagnostic"), matching this file's intent: exercising the check-answer
    # route's mastery mutation, not the diagnostic bypass.
    db_session.add(User(id=USER_ID))
    session = SessionModel(
        id="s_ans_1", user_id=USER_ID, topic="biology",
        topic_profile_json=TopicProfile(knowledge_level="intermediate").model_dump_json(),
    )
    db_session.add(session)
    db_session.commit()
    return session


def _open_batch(db, session_id):
    ctx = ToolContext(db=db, session_id=session_id, user_id=USER_ID,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    check_question_service.register(db, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=session_id, gap="atp",
        items=[
            {"question": "Q1?", "options": ["2 ATP", "36 ATP"],
             "correct_index": 0, "explanation": "Net 2 ATP."},
            {"question": "Q2?", "options": ["a", "b"],
             "correct_index": 1, "explanation": "b."},
        ]))


def test_answer_first_item_advances(client, db_session, seeded_session):
    sid = seeded_session.id
    _open_batch(db_session, sid)
    r = client.post(f"/api/sessions/{sid}/check/answer",
                    json={"index": 0, "selected_index": 0, "user_id": USER_ID})
    assert r.status_code == 200
    body = r.json()
    assert body["correct"] is True
    assert body["current_index"] == 1
    assert body["has_next"] is True
    assert body["done"] is False
    assert check_question_service.get_pending_check(db_session, sid) is not None
    assert "atp" in profile_service.concept_names(
        profile_service.load_profile(db_session, sid).mastered_concepts
    )


def test_answer_last_item_done(client, db_session, seeded_session):
    sid = seeded_session.id
    _open_batch(db_session, sid)
    client.post(f"/api/sessions/{sid}/check/answer",
                json={"index": 0, "selected_index": 0, "user_id": USER_ID})
    r = client.post(f"/api/sessions/{sid}/check/answer",
                    json={"index": 1, "selected_index": 1, "user_id": USER_ID})
    assert r.json()["done"] is True


def test_answer_later_item_first(client, db_session, seeded_session):
    # #348: free navigation, any pending item may be answered first.
    sid = seeded_session.id
    _open_batch(db_session, sid)
    r = client.post(f"/api/sessions/{sid}/check/answer",
                    json={"index": 1, "selected_index": 0, "user_id": USER_ID})
    assert r.status_code == 200
    assert r.json()["current_index"] == 0
    assert r.json()["done"] is False


def test_answer_resolved_item_is_409(client, db_session, seeded_session):
    sid = seeded_session.id
    _open_batch(db_session, sid)
    client.post(f"/api/sessions/{sid}/check/answer",
                json={"index": 1, "selected_index": 0, "user_id": USER_ID})
    r = client.post(f"/api/sessions/{sid}/check/answer",
                    json={"index": 1, "selected_index": 0, "user_id": USER_ID})
    assert r.status_code == 409


def test_answer_no_batch_is_409(client, db_session, seeded_session):
    sid = seeded_session.id
    r = client.post(f"/api/sessions/{sid}/check/answer",
                    json={"index": 0, "selected_index": 0, "user_id": USER_ID})
    assert r.status_code == 409


def test_answer_foreign_session_is_404(client, db_session):
    db_session.add(User(id=USER_ID))
    db_session.commit()
    r = client.post("/api/sessions/nope/check/answer",
                    json={"index": 0, "selected_index": 0, "user_id": USER_ID})
    assert r.status_code == 404


def test_answer_on_ended_session_is_409(client, db_session, seeded_session):
    sid = seeded_session.id
    _open_batch(db_session, sid)
    seeded_session.ended_at = datetime.now(timezone.utc)
    db_session.commit()
    r = client.post(f"/api/sessions/{sid}/check/answer",
                    json={"index": 0, "selected_index": 0, "user_id": USER_ID})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "session_ended"


def test_answer_writes_check_batch_to_message(client, db_session, seeded_session):
    sid = seeded_session.id
    _open_batch(db_session, sid)
    m = ChatMessage(session_id=sid, role="assistant", content="")
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    check_question_service.attach_message_id(db_session, sid, m.id)
    r = client.post(f"/api/sessions/{sid}/check/answer",
                    json={"index": 0, "selected_index": 0, "user_id": USER_ID})
    assert r.status_code == 200
    db_session.refresh(m)
    assert m.check_batch_json is not None
    data = json.loads(m.check_batch_json)
    assert data["items"][0]["status"] == "answered"
    assert data["items"][0]["selected_index"] == 0


@pytest.fixture
def seeded_session_with_open_check(db_session):
    # No Authorization header is sent by the test below, so the auth shim's
    # default identity ("test-user") must own this session.
    owner_id = "test-user"
    db_session.add(User(id=owner_id))
    session = SessionModel(
        id="s_ans_open_check", user_id=owner_id, topic="biology",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(session)
    db_session.commit()
    _open_batch(db_session, session.id)
    return session.id


def test_answer_check_has_no_add_lesson_suggestion(client, seeded_session_with_open_check):
    sid = seeded_session_with_open_check
    r = client.post(f"/api/sessions/{sid}/check/answer", json={"index": 0, "selected_index": 0})
    assert r.status_code == 200
    assert "add_lesson_suggestion" not in r.json()
