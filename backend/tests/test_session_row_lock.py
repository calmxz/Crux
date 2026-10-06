"""#417: lock_session_row must return the row as of the lock, not the
identity-map copy loaded earlier in the same transaction.

Two Sessions on one file-backed SQLite engine stand in for two concurrent
requests (the conftest in-memory engine shares one connection). SQLite
cannot show the FOR UPDATE wait, but the stale read is ORM-level, so it
reproduces here.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from contracts import TopicProfile
from db.database import Base
from db.models import Session as SessionModel
from db.models import User
from services import profile_service

SESSION_ID = "sess_lock"
USER_ID = "u_lock"


@pytest.fixture
def make_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'lock.db'}")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    opened = []

    def _make():
        db = factory()
        opened.append(db)
        return db

    seed = _make()
    seed.add(User(id=USER_ID))
    seed.flush()
    seed.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    seed.commit()
    try:
        yield _make
    finally:
        for db in opened:
            db.close()
        engine.dispose()


def test_locked_read_sees_a_concurrent_commit(make_session):
    a, b = make_session(), make_session()
    loaded = a.get(SessionModel, SESSION_ID)  # keep it in A's identity map

    b.get(SessionModel, SESSION_ID).pending_check_json = '{"from": "b"}'
    b.commit()

    row = profile_service.lock_session_row(a, SESSION_ID)
    assert row is loaded
    assert row.pending_check_json == '{"from": "b"}'


def test_locked_read_keeps_the_callers_own_unflushed_edit(make_session):
    a = make_session()
    a.get(SessionModel, SESSION_ID).pending_check_json = '{"from": "a"}'

    row = profile_service.lock_session_row(a, SESSION_ID)
    assert row.pending_check_json == '{"from": "a"}'


def test_profile_read_after_the_lock_is_fresh(make_session):
    a, b = make_session(), make_session()
    loaded = a.get(SessionModel, SESSION_ID)  # what every route guard does

    changed = TopicProfile(knowledge_level="advanced")
    profile_service.save_profile(b, SESSION_ID, changed)

    assert profile_service.lock_session_row(a, SESSION_ID) is loaded
    fresh = profile_service.load_profile(a, SESSION_ID)
    assert fresh.knowledge_level == "advanced"
    assert profile_service.profile_etag(fresh) == profile_service.profile_etag(changed)
