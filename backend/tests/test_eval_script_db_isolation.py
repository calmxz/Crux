"""#596: the live eval scripts run every session, the LLM adapter's included,
on the script's own in-memory database."""

import importlib
import uuid

import pytest

from db.database import SessionLocal
from db.database import engine as default_engine
from db.models import User
from services.cost_meter import assert_within_caps


@pytest.mark.parametrize("script", ["eval_subtopic_levels", "reliability_focus_clear"])
def test_adapter_sessions_reach_the_seeded_database(script, monkeypatch):
    # The script hard-assigns DATABASE_URL on import; setenv first so
    # monkeypatch restores the caller's value at teardown.
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    module = importlib.import_module(f"scripts.{script}")

    # The script binds SessionLocal itself, so bind_session_local cannot wrap
    # it; hold the same one-binding rule and restore the default engine.
    assert SessionLocal.kw["bind"] is default_engine
    try:
        factory = module._make_session_factory()
        user_id = f"u-{uuid.uuid4().hex[:8]}"
        with factory() as db:
            db.add(User(id=user_id))
            db.commit()
            seeded_engine = db.get_bind()

        with SessionLocal() as db:
            assert db.get_bind() is seeded_engine
            assert_within_caps(db, user_id)
    finally:
        script_engine = SessionLocal.kw["bind"]
        SessionLocal.configure(bind=default_engine)
        if script_engine is not default_engine:
            script_engine.dispose()
