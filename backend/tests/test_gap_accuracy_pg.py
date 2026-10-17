"""#565: the gap-accuracy read is best-effort on Postgres too.

On Postgres a failed statement aborts the whole transaction, so a plain
try/except around the read does not keep the failure contained: the next
statement on the same session raises InFailedSqlTransaction. The sqlite
suite cannot show this (test_chat.py's failure test raises before any SQL
runs). Here the patched read issues real failing SQL on the request's own
session, which is what a statement timeout or schema drift would do.

**Opt-in**: skipped unless `TEST_DATABASE_URL` is set. Run locally with
`scripts/pg_tests.sh tests/test_gap_accuracy_pg.py --no-cov`. Never point it
at a production database.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from config import settings
from contracts import TopicProfile
from db.database import get_db
from db.models import ChatMessage
from db.models import Session as SessionModel
from main import app
from services import prompt_state, summary_service, velocity_limit
from services.auth import current_user_id
from tests.conftest import _fake_current_user_id

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB,
    reason="TEST_DATABASE_URL not set - skipping live Postgres gap-accuracy test",
)

GAPS_PROFILE = TopicProfile(confirmed_gaps=[{"name": "joins"}]).model_dump_json()


@pytest.fixture
def seeded(pg_seed):
    """A unique user + session with a confirmed gap, so the gap-accuracy read
    runs. Removed by the shared teardown (conftest pg_seed)."""
    return pg_seed("gap-pg", topic="sql", topic_profile_json=GAPS_PROFILE)


@pytest.fixture
def failing_read(monkeypatch):
    """Replace the aggregate with one that fails inside Postgres on the
    caller's session. Returns the list of calls, to prove the read ran."""
    calls = []

    def _fail(db, session_id):
        calls.append(session_id)
        db.execute(text("SELECT 1 / 0"))
        return {}

    monkeypatch.setattr("services.learning_event_service.gap_accuracy", _fail)
    return calls


def test_failed_read_leaves_the_session_usable(seeded, failing_read):
    Session, _, sid = seeded
    with Session() as db:
        session = db.get(SessionModel, sid)
        inputs = prompt_state.gather_session_inputs(
            db, session, learner_prefs={}, ingestion_status=None
        )
        assert failing_read == [sid]
        assert inputs.gap_accuracy == {}
        # The next statement on the same transaction must not hit
        # InFailedSqlTransaction.
        assert db.execute(text("SELECT 1")).scalar_one() == 1


def test_failed_read_does_not_kill_the_chat_turn(seeded, failing_read, monkeypatch):
    """End-to-end acceptance. This one passed before #565 too: the only
    statement after the read in _prepare_turn_context is db.commit(), which
    Postgres answers on an aborted transaction with a silent ROLLBACK of that
    read-only segment. The test above is the one that proves the savepoint;
    this one guards the turn once statements are added after the read."""
    Session, uid, sid = seeded

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    # The response's BackgroundTask opens SessionLocal() on the default URL.
    async def no_rolling_summary(db, session_id):
        return None

    monkeypatch.setattr(summary_service, "update_rolling_summary", no_rolling_summary)
    monkeypatch.setattr(settings, "llm_stub", True)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user_id] = _fake_current_user_id
    velocity_limit.reset()
    try:
        with TestClient(app).stream(
            "POST",
            "/api/chat/stream",
            json={"session_id": sid, "message": "hello"},
            headers={"Authorization": f"Bearer test-{uid}"},
        ) as resp:
            status = resp.status_code
            body = "\n".join(resp.iter_lines())
    finally:
        app.dependency_overrides.clear()
        velocity_limit.reset()

    assert failing_read == [sid]
    assert status == 200, body
    assert "event: done" in body
    with Session() as db:
        roles = (
            db.execute(select(ChatMessage.role).where(ChatMessage.session_id == sid))
            .scalars()
            .all()
        )
    assert sorted(roles) == ["assistant", "user"]
