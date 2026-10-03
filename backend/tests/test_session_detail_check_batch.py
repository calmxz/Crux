"""GET /sessions/{id} returns check_batch per message; open batch suppressed."""

import json
from datetime import datetime, timezone

import pytest

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, LearningEvent, User
from db.models import Session as SessionModel
from services import check_question_service

USER_ID = "u_detail_1"
SID = "s_detail_1"


@pytest.fixture
def seeded(db_session):
    db_session.add(User(id=USER_ID))
    db_session.add(SessionModel(
        id=SID, user_id=USER_ID, topic="bio",
        topic_profile_json=TopicProfile().model_dump_json(),
    ))
    db_session.commit()
    return db_session


def _msg(db, content="", **kw):
    m = ChatMessage(session_id=SID, role="assistant", content=content, **kw)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def test_check_batch_returned_from_column(client, seeded):
    db = seeded
    _msg(db, check_batch_json=json.dumps({
        "gap": "atp", "current_index": 1, "total": 1,
        "items": [{"question": "Q1?", "options": ["a", "b"], "status": "answered",
                   "selected_index": 0, "correct_index": 0, "correct": True,
                   "explanation": "a."}],
    }))
    r = client.get(f"/api/sessions/{SID}?user_id={USER_ID}")
    assert r.status_code == 200
    msgs = r.json()["messages"]
    assert msgs[0]["check_batch"]["gap"] == "atp"
    assert msgs[0]["check_batch"]["items"][0]["selected_index"] == 0


def test_open_batch_message_suppressed(client, seeded):
    db = seeded
    ctx = ToolContext(db=db, session_id=SID, user_id=USER_ID,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    check_question_service.register(db, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=SID, gap="atp",
        items=[{"question": "Q1?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a."}]))
    m = _msg(db)
    check_question_service.attach_message_id(db, SID, m.id)
    # Answer one item -> per-answer write stamps check_batch_json while OPEN.
    check_question_service.answer(db, SID, index=0, selected_index=0)
    check_question_service.write_check_batch(
        db, check_question_service.get_pending_check(db, SID))

    r = client.get(f"/api/sessions/{SID}?user_id={USER_ID}")
    msg = next(x for x in r.json()["messages"] if x["id"] == m.id)
    # Batch still open (pending_check present) -> recap suppressed; live card owns it.
    assert msg["check_batch"] is None


def test_backfill_when_no_column(client, seeded):
    db = seeded
    m = _msg(db, tool_calls_json=json.dumps([{
        "name": "ask_check_questions",
        "args": {"session_id": SID, "gap": "g", "items": [
            {"question": "Qb?", "options": ["a", "b"],
             "correct_index": 1, "explanation": "b."}]},
        "status": "ok", "error": None,
    }]))
    db.add(LearningEvent(session_id=SID, gap_tested="g",
                         question="Qb?", correct=False))
    db.commit()
    r = client.get(f"/api/sessions/{SID}?user_id={USER_ID}")
    cb = next(x for x in r.json()["messages"] if x["id"] == m.id)["check_batch"]
    assert cb["items"][0]["status"] == "answered"
    assert cb["items"][0]["correct"] is False
    assert cb["items"][0]["selected_index"] is None


def test_plain_message_has_null_check_batch(client, seeded):
    db = seeded
    m = _msg(db, content="hello", tool_calls_json="[]")
    r = client.get(f"/api/sessions/{SID}?user_id={USER_ID}")
    cb = next(x for x in r.json()["messages"] if x["id"] == m.id)["check_batch"]
    assert cb is None
