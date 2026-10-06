"""TDD Task 6: GET session/{id} returns tool_calls + pending_check."""

import json

from contracts import TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel

USER_ID = "u1"


def test_get_session_returns_tool_calls(client, db_session):
    db_session.add(User(id=USER_ID))
    db_session.add(
        SessionModel(
            id="s_tc",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.add(
        ChatMessage(
            session_id="s_tc",
            role="assistant",
            content="hi",
            tool_calls_json=json.dumps([
                {
                    "name": "update_topic_profile",
                    "args": {},
                    "status": "failed",
                    "error": "evidence_type must be declared/tested/inferred",
                }
            ]),
        )
    )
    db_session.commit()

    resp = client.get("/api/sessions/s_tc", params={"user_id": USER_ID})
    assert resp.status_code == 200
    body = resp.json()
    msg = [m for m in body["messages"] if m["role"] == "assistant"][0]
    assert msg["tool_calls"][0]["status"] == "failed"
    assert "evidence_type" in msg["tool_calls"][0]["error"]
    assert body["pending_check"] is None
