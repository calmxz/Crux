"""F-34: duplicate-topic detection is server-side, case-insensitive, and
covers create + reopen."""
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from contracts import TopicProfile
from db.models import Session as SessionModel
from db.models import User


def _create(client, topic, uid="dupe-user"):
    return client.post(
        "/api/sessions",
        json={"topic": topic, "seed_mode": "fresh"},
        headers={"Authorization": f"Bearer test-{uid}"},
    )


def test_create_conflicts_with_active_same_topic(client):
    first = _create(client, "Chain Rule")
    assert first.status_code == 201
    dup = _create(client, "chain rule")  # case-insensitive
    assert dup.status_code == 409
    detail = dup.json()["detail"]
    assert detail["code"] == "duplicate_topic"
    assert detail["session_id"] == first.json()["id"]


def test_create_allowed_after_end(client):
    first = _create(client, "Osmosis")
    sid = first.json()["id"]
    ended = client.post(
        f"/api/sessions/{sid}/end",
        headers={"Authorization": "Bearer test-dupe-user"},
    )
    assert ended.status_code == 200
    again = _create(client, "Osmosis")
    assert again.status_code == 201


def test_reopen_conflicts_with_active_same_topic(client):
    first = _create(client, "Mitosis")
    sid = first.json()["id"]
    client.post(f"/api/sessions/{sid}/end",
                headers={"Authorization": "Bearer test-dupe-user"})
    second = _create(client, "Mitosis")
    assert second.status_code == 201
    reopened = client.post(
        f"/api/sessions/{sid}/reopen",
        headers={"Authorization": "Bearer test-dupe-user"},
    )
    assert reopened.status_code == 409
    assert reopened.json()["detail"]["code"] == "duplicate_topic"


def test_other_users_topic_does_not_conflict(client):
    _create(client, "Redox", uid="alice")
    other = _create(client, "Redox", uid="bob")
    assert other.status_code == 201


def test_db_rejects_second_active_session_same_topic_casefold(db_session):
    db_session.add(User(id="u_ix"))
    db_session.flush()
    db_session.add(SessionModel(
        id="s_ix1", user_id="u_ix", topic="Calculus",
        topic_profile_json=TopicProfile().model_dump_json(),
    ))
    db_session.commit()
    db_session.add(SessionModel(
        id="s_ix2", user_id="u_ix", topic="calculus",
        topic_profile_json=TopicProfile().model_dump_json(),
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_db_allows_duplicate_topic_when_first_is_ended(db_session):
    db_session.add(User(id="u_ix2"))
    db_session.flush()
    db_session.add(SessionModel(
        id="s_ix3", user_id="u_ix2", topic="Algebra",
        topic_profile_json=TopicProfile().model_dump_json(),
        ended_at=datetime.now(timezone.utc),
    ))
    db_session.commit()
    db_session.add(SessionModel(
        id="s_ix4", user_id="u_ix2", topic="Algebra",
        topic_profile_json=TopicProfile().model_dump_json(),
    ))
    db_session.commit()  # must not raise


# --- Task A2: route-level duplicate-topic hardening (B-05 mapping, B-06 rename check) ---

_AUTH = {"Authorization": "Bearer test-dupe-user"}


def test_rename_active_session_to_duplicate_topic_409(client):
    session_a = _create(client, "A")
    session_b = _create(client, "B")
    assert session_a.status_code == 201 and session_b.status_code == 201
    session_a_id = session_a.json()["id"]
    session_b_id = session_b.json()["id"]

    resp = client.patch(
        f"/api/sessions/{session_b_id}", json={"topic": "A"}, headers=_AUTH
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "duplicate_topic"
    assert resp.json()["detail"]["session_id"] == session_a_id


def test_rename_ended_session_to_duplicate_topic_ok(client):
    assert _create(client, "A").status_code == 201
    session_c = _create(client, "C")
    session_c_id = session_c.json()["id"]
    ended = client.post(f"/api/sessions/{session_c_id}/end", headers=_AUTH)
    assert ended.status_code == 200

    resp = client.patch(
        f"/api/sessions/{session_c_id}", json={"topic": "A"}, headers=_AUTH
    )
    assert resp.status_code == 200


def _bypass_once(monkeypatch, module, attr_name):
    """Monkeypatch `module.<attr_name>` so its FIRST call returns None
    (simulating a pre-check that ran before a concurrent writer landed a
    conflicting row) while every subsequent call delegates to the real
    implementation. Used to force execution past the route pre-check and
    into the real db.commit(), which then hits the genuine partial unique
    index (uq_sessions_active_topic, Task A1) and raises a real
    IntegrityError -- proving the except-IntegrityError branch, not a
    simulated one."""
    original = getattr(module, attr_name)
    calls = {"n": 0}

    def fake(db, user_id, topic, *, exclude_id=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return original(db, user_id, topic, exclude_id=exclude_id)

    monkeypatch.setattr(module, attr_name, fake)


def test_create_race_maps_integrityerror_to_409(client, monkeypatch):
    import routes.sessions as sessions_route

    first = _create(client, "Thermodynamics")
    assert first.status_code == 201
    first_id = first.json()["id"]

    _bypass_once(monkeypatch, sessions_route, "_active_session_on_topic")

    dup = _create(client, "Thermodynamics")
    assert dup.status_code == 409
    assert dup.json()["detail"]["code"] == "duplicate_topic"
    assert dup.json()["detail"]["session_id"] == first_id


def test_reopen_race_maps_integrityerror_to_409(client, monkeypatch):
    import routes.sessions as sessions_route

    first = _create(client, "Gravity")
    first_id = first.json()["id"]
    ended = client.post(f"/api/sessions/{first_id}/end", headers=_AUTH)
    assert ended.status_code == 200
    second = _create(client, "Gravity")
    assert second.status_code == 201
    second_id = second.json()["id"]

    _bypass_once(monkeypatch, sessions_route, "_active_session_on_topic")

    reopened = client.post(f"/api/sessions/{first_id}/reopen", headers=_AUTH)
    assert reopened.status_code == 409
    assert reopened.json()["detail"]["code"] == "duplicate_topic"
    assert reopened.json()["detail"]["session_id"] == second_id


def test_create_conflicts_with_active_same_topic_untrimmed(client):
    """M2: pre-check normalizes via .strip().lower(), but create used to
    store req.topic raw. The FIRST session is created with untrimmed
    whitespace (" Calc "); if it is stored raw, a later create with the
    trimmed "Calc" fails to match on both the pre-check (compares against
    the raw, unstripped stored value) and the DB unique index (also keyed
    on raw lower(topic)), letting two active sessions on the same logical
    topic coexist. Storing stripped at creation time closes both holes."""
    first = _create(client, " Calc ")
    assert first.status_code == 201
    dup = _create(client, "Calc")
    assert dup.status_code == 409
    detail = dup.json()["detail"]
    assert detail["code"] == "duplicate_topic"
    assert detail["session_id"] == first.json()["id"]


def test_rename_race_maps_integrityerror_to_409(client, monkeypatch):
    import routes.sessions as sessions_route

    a = _create(client, "Force")
    b = _create(client, "Torque")
    assert a.status_code == 201 and b.status_code == 201
    a_id = a.json()["id"]
    b_id = b.json()["id"]

    _bypass_once(monkeypatch, sessions_route, "_active_session_on_topic")

    resp = client.patch(
        f"/api/sessions/{b_id}", json={"topic": "Force"}, headers=_AUTH
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "duplicate_topic"
    assert resp.json()["detail"]["session_id"] == a_id
