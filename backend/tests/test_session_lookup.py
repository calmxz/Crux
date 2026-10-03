"""TDD: GET /api/sessions/lookup — case-insensitive exact topic match."""

from datetime import datetime

from contracts import ConceptEntry, TopicProfile
from db.models import Session as SessionModel
from db.models import User

USER_ID = "u1"
OTHER_ID = "u2"


def _mk_session(db, *, sid, user_id=USER_ID, topic, ended_at=None, profile=None):
    db.add(
        SessionModel(
            id=sid,
            user_id=user_id,
            topic=topic,
            ended_at=ended_at,
            topic_profile_json=(profile or TopicProfile()).model_dump_json(),
        )
    )
    db.commit()


def _lookup(client, topic, user_id=USER_ID):
    return client.get("/api/sessions/lookup", params={"topic": topic, "user_id": user_id})


def test_no_match_returns_empty(client, db_session):
    db_session.add(User(id=USER_ID))
    db_session.commit()
    r = _lookup(client, "totally new topic")
    assert r.status_code == 200, r.text
    assert r.json() == {"active_match": None, "ended_match": None}


def test_active_match_case_and_whitespace_insensitive(client, db_session):
    db_session.add(User(id=USER_ID))
    _mk_session(db_session, sid="s1", topic="Glycolysis")
    r = _lookup(client, "  glycolysis ")
    body = r.json()
    assert body["active_match"]["session_id"] == "s1"
    assert body["active_match"]["title"] == "Glycolysis"
    assert body["active_match"]["ended_at"] is None
    assert body["ended_match"] is None


def test_ended_match_only_when_no_active(client, db_session):
    db_session.add(User(id=USER_ID))
    profile = TopicProfile(
        knowledge_level="intermediate",
        confirmed_gaps=[ConceptEntry(name="ATP yield"), ConceptEntry(name="ETC location")],
    )
    _mk_session(
        db_session, sid="s2", topic="glycolysis",
        ended_at=datetime(2026, 7, 1), profile=profile,
    )
    r = _lookup(client, "Glycolysis")
    body = r.json()
    assert body["active_match"] is None
    assert body["ended_match"]["session_id"] == "s2"
    assert body["ended_match"]["gap_count"] == 2
    assert body["ended_match"]["knowledge_level"] == "intermediate"


def test_active_beats_ended(client, db_session):
    db_session.add(User(id=USER_ID))
    _mk_session(db_session, sid="s3", topic="css", ended_at=datetime(2026, 7, 1))
    _mk_session(db_session, sid="s4", topic="CSS")
    body = _lookup(client, "css").json()
    assert body["active_match"]["session_id"] == "s4"
    assert body["ended_match"] is None


def test_latest_ended_wins(client, db_session):
    db_session.add(User(id=USER_ID))
    _mk_session(db_session, sid="s5", topic="mitosis", ended_at=datetime(2026, 6, 1))
    _mk_session(db_session, sid="s6", topic="Mitosis", ended_at=datetime(2026, 7, 1))
    body = _lookup(client, "mitosis").json()
    assert body["ended_match"]["session_id"] == "s6"


def test_other_user_sessions_invisible(client, db_session):
    db_session.add(User(id=USER_ID))
    db_session.add(User(id=OTHER_ID))
    db_session.commit()
    _mk_session(db_session, sid="s7", user_id=OTHER_ID, topic="recursion")
    body = _lookup(client, "recursion").json()
    assert body == {"active_match": None, "ended_match": None}


def test_blank_topic_returns_empty(client, db_session):
    db_session.add(User(id=USER_ID))
    db_session.commit()
    body = _lookup(client, "   ").json()
    assert body == {"active_match": None, "ended_match": None}


def test_legacy_profile_shape_does_not_500(client, db_session):
    """C-01: lookup must use the tolerant parser. TopicProfile is codegen'd
    with extra="forbid", so a row written under an older schema (retired
    field still present) would 500 every lookup on that topic under a strict
    model_validate_json."""
    db_session.add(User(id=USER_ID))
    db_session.add(
        SessionModel(
            id="s8",
            user_id=USER_ID,
            topic="thermodynamics",
            topic_profile_json=(
                '{"knowledge_level":"beginner","confirmed_gaps":[{"name":"entropy"}],'
                '"mastered_concepts":[],"retired_field":1}'
            ),
        )
    )
    db_session.commit()
    r = _lookup(client, "thermodynamics")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["active_match"]["session_id"] == "s8"
    assert body["active_match"]["gap_count"] == 1
    assert body["active_match"]["knowledge_level"] == "beginner"
