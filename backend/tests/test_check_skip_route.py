"""TDD: POST /sessions/{id}/check/skip over a batch."""

import json
from datetime import datetime, timezone

import pytest

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from services import check_question_service

USER_ID = "u_skip_1"


@pytest.fixture
def seeded_session(db_session):
    db_session.add(User(id=USER_ID))
    session = SessionModel(
        id="s_skip_1", user_id=USER_ID, topic="bio",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(session)
    db_session.commit()
    return session


def _open_batch(db, session_id):
    ctx = ToolContext(db=db, session_id=session_id, user_id=USER_ID,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    check_question_service.register(db, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=session_id, gap="g",
        items=[{"question": "Q1?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a."},
               {"question": "Q2?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a."}]))


def test_skip_advances(client, db_session, seeded_session):
    sid = seeded_session.id
    _open_batch(db_session, sid)
    r = client.post(f"/api/sessions/{sid}/check/skip",
                    json={"index": 0, "user_id": USER_ID})
    assert r.status_code == 200
    body = r.json()
    assert body["current_index"] == 1
    assert body["done"] is False


def test_skip_later_item_first(client, db_session, seeded_session):
    # #348: free navigation, any pending item may be skipped first.
    sid = seeded_session.id
    _open_batch(db_session, sid)
    r = client.post(f"/api/sessions/{sid}/check/skip",
                    json={"index": 1, "user_id": USER_ID})
    assert r.status_code == 200
    assert r.json()["current_index"] == 0


def test_skip_resolved_item_is_409(client, db_session, seeded_session):
    sid = seeded_session.id
    _open_batch(db_session, sid)
    client.post(f"/api/sessions/{sid}/check/skip",
                json={"index": 0, "user_id": USER_ID})
    r = client.post(f"/api/sessions/{sid}/check/skip",
                    json={"index": 0, "user_id": USER_ID})
    assert r.status_code == 409


def test_skip_no_batch_is_409(client, db_session, seeded_session):
    sid = seeded_session.id
    r = client.post(f"/api/sessions/{sid}/check/skip",
                    json={"index": 0, "user_id": USER_ID})
    assert r.status_code == 409


def test_skip_foreign_session_is_404(client, db_session):
    db_session.add(User(id=USER_ID))
    db_session.commit()
    r = client.post("/api/sessions/nope/check/skip",
                    json={"index": 0, "user_id": USER_ID})
    assert r.status_code == 404


def test_skip_on_ended_session_is_409(client, db_session, seeded_session):
    sid = seeded_session.id
    _open_batch(db_session, sid)
    seeded_session.ended_at = datetime.now(timezone.utc)
    db_session.commit()
    r = client.post(f"/api/sessions/{sid}/check/skip",
                    json={"index": 0, "user_id": USER_ID})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "session_ended"


def test_skip_writes_check_batch_to_message(client, db_session, seeded_session):
    sid = seeded_session.id
    _open_batch(db_session, sid)
    m = ChatMessage(session_id=sid, role="assistant", content="")
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    check_question_service.attach_message_id(db_session, sid, m.id)
    r = client.post(f"/api/sessions/{sid}/check/skip",
                    json={"index": 0, "user_id": USER_ID})
    assert r.status_code == 200
    db_session.refresh(m)
    assert m.check_batch_json is not None
    data = json.loads(m.check_batch_json)
    assert data["items"][0]["status"] == "skipped"
    assert data["items"][0]["selected_index"] is None
