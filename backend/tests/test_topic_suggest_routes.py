"""#354 wiring: session create seeds topic_suggest_state, the transcript
carries the card, and both prompt builders render TOPIC_SUGGEST."""

import json

import pytest

from contracts import TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from routes import chat as chat_route
from routes import sessions as sessions_route
from services import topic_suggest_service

USER_ID = "u_ts_routes"


@pytest.fixture
def user(db_session):
    db_session.add(User(id=USER_ID))
    db_session.commit()


def _state_of(db, sid):
    db.expire_all()
    return db.get(SessionModel, sid).topic_suggest_state


def test_fresh_session_without_level_awaits_level(client, user, db_session):
    r = client.post("/api/sessions", json={"user_id": USER_ID, "topic": "Thermo", "seed_mode": "fresh"})
    assert r.status_code == 201, r.text
    assert _state_of(db_session, r.json()["id"]) == topic_suggest_service.AWAITING_LEVEL


def test_session_created_with_declared_level_never_gets_the_card(client, user, db_session):
    r = client.post("/api/sessions", json={
        "user_id": USER_ID, "topic": "Thermo", "seed_mode": "fresh", "declared_level": "advanced",
    })
    assert r.status_code == 201, r.text
    assert _state_of(db_session, r.json()["id"]) is None


@pytest.mark.parametrize("prior_level,expected", [
    ("beginner", None),
    (None, topic_suggest_service.AWAITING_LEVEL),
])
def test_resumed_session_follows_the_seeded_level(client, user, db_session, prior_level, expected):
    db_session.add(SessionModel(
        id="prior_ts", user_id=USER_ID, topic="Thermo",
        topic_profile_json=TopicProfile(knowledge_level=prior_level).model_dump_json(),
    ))
    db_session.commit()
    r = client.post("/api/sessions", json={
        "user_id": USER_ID, "topic": "Thermo", "seed_mode": "resume", "prior_session_id": "prior_ts",
    })
    assert r.status_code == 201, r.text
    assert _state_of(db_session, r.json()["id"]) == expected


def test_session_detail_returns_topic_suggestions(client, user, db_session):
    db_session.add(SessionModel(id="s_card", user_id=USER_ID, topic="Carnot cycle"))
    db_session.add(ChatMessage(
        session_id="s_card", role="assistant", content="The Carnot cycle is...",
        tool_calls_json=json.dumps([{
            "name": "suggest_topics", "status": "ok", "error": None,
            "args": {"mode": "specific", "topic": "Carnot cycle",
                     "items": [{"label": "Entropy"}, {"label": "Otto cycle", "hint": "real engines"}]},
        }]),
    ))
    db_session.add(ChatMessage(session_id="s_card", role="user", content="hi"))
    db_session.commit()

    msgs = client.get(f"/api/sessions/s_card?user_id={USER_ID}").json()["messages"]
    assert msgs[0]["topic_suggestions"] == {
        "mode": "specific",
        "topic": "Carnot cycle",
        "items": [{"label": "Entropy", "hint": None}, {"label": "Otto cycle", "hint": "real engines"}],
    }
    assert msgs[1]["topic_suggestions"] is None


def test_chat_prompt_state_carries_topic_suggest_state():
    row = SessionModel(id="x", user_id="u", topic="t", topic_suggest_state="awaiting_level")
    state = chat_route._build_prompt_state(
        session=row, profile=TopicProfile(knowledge_level="beginner"), ingestion_status=None,
        retrieval_required=False, review_gaps=False, pending_check=None, quiz_cooldown=None,
    )
    assert state["topic_suggest_state"] == "awaiting_level"


def test_followup_after_graded_diagnostic_makes_the_card_due(user, db_session):
    row = SessionModel(
        id="s_follow", user_id=USER_ID, topic="Thermo",
        topic_profile_json=TopicProfile(knowledge_level="intermediate").model_dump_json(),
        topic_suggest_state=topic_suggest_service.AWAITING_LEVEL,
    )
    db_session.add(row)
    db_session.commit()
    allowed, _msgs, system_prompt, _ctx = sessions_route._followup_context(
        db_session, row, "s_follow", USER_ID, "[check results] gap=g: 3/3 correct. Set 1 of 1.", None,
    )
    assert allowed
    assert "TOPIC_SUGGEST: DUE" in system_prompt
