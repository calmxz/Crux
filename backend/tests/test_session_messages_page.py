import pytest

from contracts import TopicProfile
from db.models import ChatMessage
from db.models import Session as SessionModel

USER_ID = "u1"


@pytest.fixture()
def seeded_user(db_session):
    from db.models import User

    db_session.add(User(id=USER_ID))
    db_session.commit()


def _seed(db_session, session_id, count):
    db_session.add(
        SessionModel(
            id=session_id,
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    ids = []
    for i in range(count):
        m = ChatMessage(session_id=session_id, role="user", content=f"m{i}")
        db_session.add(m)
        db_session.commit()
        ids.append(m.id)
    return ids


def test_page_returns_older_messages_ascending(client, db_session, seeded_user):
    ids = _seed(db_session, "s_page", 40)
    # Cursor at the 35th message: expect the 30 before it, ascending.
    r = client.get(f"/api/sessions/s_page/messages?before={ids[35]}&limit=30&user_id={USER_ID}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert [m["content"] for m in body["items"]] == [f"m{i}" for i in range(5, 35)]
    assert body["has_more"] is True


def test_page_at_history_start_has_more_false(client, db_session, seeded_user):
    ids = _seed(db_session, "s_start", 10)
    r = client.get(f"/api/sessions/s_start/messages?before={ids[5]}&user_id={USER_ID}")
    body = r.json()
    assert [m["content"] for m in body["items"]] == ["m0", "m1", "m2", "m3", "m4"]
    assert body["has_more"] is False


def test_cursor_older_than_everything_returns_empty(client, db_session, seeded_user):
    ids = _seed(db_session, "s_empty", 3)
    r = client.get(f"/api/sessions/s_empty/messages?before={ids[0]}&user_id={USER_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["has_more"] is False


def test_foreign_session_404(client, db_session, seeded_user):
    _seed(db_session, "s_mine", 2)
    r = client.get("/api/sessions/s_mine/messages?before=999&user_id=other")
    assert r.status_code == 404


def test_unknown_session_404(client, seeded_user):
    r = client.get(f"/api/sessions/nope/messages?before=1&user_id={USER_ID}")
    assert r.status_code == 404


def test_missing_or_bad_cursor_422(client, db_session, seeded_user):
    _seed(db_session, "s_bad", 1)
    assert client.get(f"/api/sessions/s_bad/messages?user_id={USER_ID}").status_code == 422
    assert client.get(f"/api/sessions/s_bad/messages?before=abc&user_id={USER_ID}").status_code == 422


def test_limit_out_of_range_422(client, db_session, seeded_user):
    _seed(db_session, "s_lim", 1)
    assert client.get(f"/api/sessions/s_lim/messages?before=99&limit=0&user_id={USER_ID}").status_code == 422
    assert client.get(f"/api/sessions/s_lim/messages?before=99&limit=101&user_id={USER_ID}").status_code == 422
