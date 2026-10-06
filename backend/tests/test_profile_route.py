"""TDD: GET /api/profile/{session_id}."""

import pytest

from contracts import TopicProfile
from db.models import LearningEvent, User
from db.models import Session as SessionModel

SESSION_ID = "sess_1"
USER_ID = "u1"


@pytest.fixture
def seed_session(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile(
                knowledge_level="beginner",
                confirmed_gaps=[{"name": "joins"}],
                mastered_concepts=[{"name": "select"}],
            ).model_dump_json(),
        )
    )
    db_session.commit()


def test_profile_route_404_when_missing(client):
    r = client.get(f"/api/profile/does_not_exist?user_id={USER_ID}")
    assert r.status_code == 404


def test_profile_route_404_for_wrong_user(client, db_session, seed_session):
    db_session.add(User(id="other"))
    db_session.commit()
    r = client.get(f"/api/profile/{SESSION_ID}?user_id=other")
    assert r.status_code == 404


def test_profile_route_empty_defaults(client, db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(SessionModel(id=SESSION_ID, user_id=USER_ID, topic="sql"))
    db_session.commit()
    r = client.get(f"/api/profile/{SESSION_ID}?user_id={USER_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["profile"]["knowledge_level"] is None
    assert body["profile"]["confirmed_gaps"] == []
    assert body["recent_learning_events"] == []


def test_profile_route_with_events_desc(client, db_session, seed_session):
    for i, correct in enumerate([True, False, True]):
        db_session.add(
            LearningEvent(
                session_id=SESSION_ID,
                gap_tested=f"gap_{i}",
                question=f"q_{i}",
                correct=correct,
            )
        )
    db_session.commit()
    r = client.get(f"/api/profile/{SESSION_ID}?user_id={USER_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["profile"]["knowledge_level"] == "beginner"
    assert [g["name"] for g in body["profile"]["confirmed_gaps"]] == ["joins"]
    assert len(body["recent_learning_events"]) == 3
    # ordered desc by created_at -> latest first
    assert body["recent_learning_events"][0]["gap_tested"] == "gap_2"


def test_get_profile_includes_etag(client, auth_headers, seeded_session_id):
    r = client.get(f"/api/profile/{seeded_session_id}", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json()["etag"], str) and r.json()["etag"]


# --- PATCH / DELETE routes -------------------------------------------------

SEEDED_USER_ID = "u_seeded"
SEEDED_SESSION_ID = "sess_seeded"
OTHER_USER_ID = "u_other"


@pytest.fixture
def seeded_session_id(db_session):
    db_session.add(User(id=SEEDED_USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SEEDED_SESSION_ID,
            user_id=SEEDED_USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    return SEEDED_SESSION_ID


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer test-{SEEDED_USER_ID}"}


@pytest.fixture
def other_auth_headers():
    return {"Authorization": f"Bearer test-{OTHER_USER_ID}"}


def _etag(client, headers, sid):
    return client.get(f"/api/profile/{sid}", headers=headers).json()["etag"]


def test_patch_requires_if_match(client, auth_headers, seeded_session_id):
    r = client.patch(
        f"/api/profile/{seeded_session_id}",
        headers=auth_headers,
        json={"add_mastered": "loops"},
    )
    assert r.status_code == 428


def test_patch_stale_if_match_returns_412(client, auth_headers, seeded_session_id):
    r = client.patch(
        f"/api/profile/{seeded_session_id}",
        headers={**auth_headers, "If-Match": "deadbeef"},
        json={"add_gap": "recursion"},
    )
    assert r.status_code == 412


def test_patch_adds_item_and_returns_new_etag(client, auth_headers, seeded_session_id):
    tag = _etag(client, auth_headers, seeded_session_id)
    r = client.patch(
        f"/api/profile/{seeded_session_id}",
        headers={**auth_headers, "If-Match": tag},
        json={"add_mastered": "loops", "knowledge_level": "advanced"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "loops" in [c["name"] for c in body["profile"]["mastered_concepts"]]
    assert body["profile"]["knowledge_level"] == "advanced"
    assert body["etag"] != tag


def test_patch_empty_body_is_422(client, auth_headers, seeded_session_id):
    tag = _etag(client, auth_headers, seeded_session_id)
    r = client.patch(
        f"/api/profile/{seeded_session_id}",
        headers={**auth_headers, "If-Match": tag},
        json={},
    )
    assert r.status_code == 422


def test_patch_whitespace_only_add_gap_is_422(client, auth_headers, seeded_session_id):
    tag = _etag(client, auth_headers, seeded_session_id)
    r = client.patch(
        f"/api/profile/{seeded_session_id}",
        headers={**auth_headers, "If-Match": tag},
        json={"add_gap": "   "},
    )
    assert r.status_code == 422


def test_patch_empty_body_is_422_before_if_match_guard(client, auth_headers, seeded_session_id):
    """Empty-body 422 must fire before the If-Match 428 guard, even when no
    If-Match header is sent at all."""
    r = client.patch(
        f"/api/profile/{seeded_session_id}",
        headers=auth_headers,
        json={},
    )
    assert r.status_code == 422


def test_delete_gap_with_spaces_and_nulls_focus(client, auth_headers, seeded_session_id):
    from urllib.parse import quote
    tag = _etag(client, auth_headers, seeded_session_id)
    client.patch(
        f"/api/profile/{seeded_session_id}",
        headers={**auth_headers, "If-Match": tag},
        json={"add_gap": "big O notation"},
    )
    tag = _etag(client, auth_headers, seeded_session_id)
    r = client.delete(
        f"/api/profile/{seeded_session_id}/confirmed_gaps/{quote('big O notation')}",
        headers={**auth_headers, "If-Match": tag},
    )
    assert r.status_code == 200
    assert "big O notation" not in r.json()["profile"]["confirmed_gaps"]


def test_delete_missing_item_404(client, auth_headers, seeded_session_id):
    tag = _etag(client, auth_headers, seeded_session_id)
    r = client.delete(
        f"/api/profile/{seeded_session_id}/mastered_concepts/nope",
        headers={**auth_headers, "If-Match": tag},
    )
    assert r.status_code == 404


def test_patch_other_users_session_404(client, other_auth_headers, seeded_session_id):
    r = client.patch(
        f"/api/profile/{seeded_session_id}",
        headers={**other_auth_headers, "If-Match": "x"},
        json={"add_mastered": "loops"},
    )
    assert r.status_code == 404


# --- user subtopic edit + delete (Task 4) ----------------------------------


def test_patch_subtopic_level_updates_existing(client, db_session, auth_headers, seeded_session_id):
    from services import profile_service

    p = profile_service.load_profile(db_session, seeded_session_id)
    p.subtopic_levels = {"chain rule": "beginner"}
    profile_service.save_profile(db_session, seeded_session_id, p)

    tag = _etag(client, auth_headers, seeded_session_id)
    res = client.patch(
        f"/api/profile/{seeded_session_id}",
        json={"subtopic": "Chain Rule", "subtopic_level": "advanced"},
        headers={**auth_headers, "If-Match": tag},
    )
    assert res.status_code == 200
    assert res.json()["profile"]["subtopic_levels"] == {"chain rule": "advanced"}


def test_patch_unknown_subtopic_422(client, auth_headers, seeded_session_id):
    tag = _etag(client, auth_headers, seeded_session_id)
    res = client.patch(
        f"/api/profile/{seeded_session_id}",
        json={"subtopic": "never seen", "subtopic_level": "beginner"},
        headers={**auth_headers, "If-Match": tag},
    )
    assert res.status_code == 422


def test_patch_subtopic_without_level_422(client, db_session, auth_headers, seeded_session_id):
    from services import profile_service

    p = profile_service.load_profile(db_session, seeded_session_id)
    p.subtopic_levels = {"chain rule": "beginner"}
    profile_service.save_profile(db_session, seeded_session_id, p)

    tag = _etag(client, auth_headers, seeded_session_id)
    res = client.patch(
        f"/api/profile/{seeded_session_id}",
        json={"subtopic": "chain rule"},
        headers={**auth_headers, "If-Match": tag},
    )
    assert res.status_code == 422


def test_delete_subtopic_level(client, db_session, auth_headers, seeded_session_id):
    from services import profile_service

    p = profile_service.load_profile(db_session, seeded_session_id)
    p.subtopic_levels = {"chain rule": "beginner"}
    profile_service.save_profile(db_session, seeded_session_id, p)

    tag = _etag(client, auth_headers, seeded_session_id)
    res = client.delete(
        f"/api/profile/{seeded_session_id}/subtopic_levels/chain%20rule",
        headers={**auth_headers, "If-Match": tag},
    )
    assert res.status_code == 200
    assert res.json()["profile"]["subtopic_levels"] == {}

    res2 = client.delete(
        f"/api/profile/{seeded_session_id}/subtopic_levels/nope",
        headers={**auth_headers, "If-Match": res.json()["etag"]},
    )
    assert res2.status_code == 404


def test_patch_subtopic_stale_etag_412(client, db_session, auth_headers, seeded_session_id):
    from services import profile_service

    p = profile_service.load_profile(db_session, seeded_session_id)
    p.subtopic_levels = {"chain rule": "beginner"}
    profile_service.save_profile(db_session, seeded_session_id, p)

    res = client.patch(
        f"/api/profile/{seeded_session_id}",
        json={"subtopic": "chain rule", "subtopic_level": "advanced"},
        headers={**auth_headers, "If-Match": "stale-etag"},
    )
    assert res.status_code == 412
