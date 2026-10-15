"""#418: characterise the check-set row locks on Postgres (check-set 1/3).

Every other check test runs on in-memory SQLite, where `with_for_update` is a
no-op, so none of them proves a lock. Here each case holds the session row
with `SELECT ... FOR UPDATE` on a connection of its own, fires the real
routes on worker threads, waits until Postgres reports the expected number
of backends blocked on a lock, then releases and asserts the end state.
Reaching the waiter count is what proves each request blocked; no sleeps
order anything.

State is seeded as raw JSON on the session row (shapes documented in
services/check_question_service.py and services/pending_check_store.py), not
through service functions, so this file survives the check-module refactor
(#419, #420). Case 4 is the only call into a service by name.

**Opt-in**: skipped unless `TEST_DATABASE_URL` is set, same as
test_pgvector_retrieval.py (CI sets it and runs `alembic upgrade head`
first). Run locally with `scripts/pg_tests.sh tests/test_check_locks_pg.py
--no-cov`. Never point it at a production database.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.orm import sessionmaker

from config import settings
from contracts import TopicProfile
from db.database import _normalized_url, get_db
from db.models import ChatMessage, DailyCostLedger, LearningEvent, LlmCallLog, UsageCounter, User
from db.models import Session as SessionModel
from lib.error_codes import CHECK_CONFLICT, NO_RESOLVED_BATCH
from main import app
from services import check_question_service, velocity_limit
from services.auth import current_user_id
from tests.conftest import _fake_current_user_id

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB,
    reason="TEST_DATABASE_URL not set - skipping live Postgres lock test",
)

# Request connections carry this name so the waiter poll counts only them.
APP_NAME = "crux-check-locks-pg"
WAIT_TIMEOUT_S = 5.0
JOIN_TIMEOUT_S = 15.0


@pytest.fixture(scope="module")
def engine():
    """prepare_threshold=None matches prod (Supabase pooler)."""
    eng = create_engine(
        _normalized_url(TEST_DB),
        connect_args={"prepare_threshold": None, "application_name": APP_NAME},
    )
    yield eng
    eng.dispose()


@pytest.fixture
def seeded(engine):
    """A unique user + session + asking assistant message per test; every
    row the requests write is deleted on teardown (Postgres enforces the FKs,
    so children go first). Yields (Session factory, uid, sid, message id)."""
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    uid = f"lock-pg-{uuid.uuid4().hex[:12]}"
    sid = f"lock-pg-s-{uuid.uuid4().hex[:12]}"
    with Session() as db:
        db.add(User(id=uid))
        db.flush()
        db.add(
            SessionModel(
                id=sid,
                user_id=uid,
                topic="sql",
                topic_profile_json=TopicProfile().model_dump_json(),
            )
        )
        db.flush()
        msg = ChatMessage(session_id=sid, role="assistant", content="Quick check.")
        db.add(msg)
        db.commit()
        msg_id = msg.id
    try:
        yield Session, uid, sid, msg_id
    finally:
        with Session() as db:
            db.execute(delete(LlmCallLog).where(LlmCallLog.user_id == uid))
            db.execute(delete(LearningEvent).where(LearningEvent.session_id == sid))
            db.execute(delete(ChatMessage).where(ChatMessage.session_id == sid))
            db.execute(delete(DailyCostLedger).where(DailyCostLedger.user_id == uid))
            db.execute(delete(UsageCounter).where(UsageCounter.user_id == uid))
            db.execute(delete(SessionModel).where(SessionModel.id == sid))
            db.execute(delete(User).where(User.id == uid))
            db.commit()


@pytest.fixture
def app_on_postgres(seeded, monkeypatch):
    """The real app with a FRESH Postgres Session per request (a shared one
    could never block on a lock). Yields the seeded tuple."""
    Session = seeded[0]

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(settings, "llm_stub", True)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user_id] = _fake_current_user_id
    velocity_limit.reset()
    try:
        yield seeded
    finally:
        app.dependency_overrides.clear()
        velocity_limit.reset()


def _item(n: int, status: str = "pending", selected: int | None = None) -> dict:
    """Item n has options a/b/c; the right answer is always index 0."""
    return {
        "question": f"Q{n}?",
        "options": ["a", "b", "c"],
        "correct_index": 0,
        "explanation": f"because {n}",
        "status": status,
        "selected_index": selected,
        "correct": (selected == 0) if status == "answered" else None,
    }


def _seed_set(
    Session,
    sid: str,
    items: list[dict],
    *,
    message_id: int | None,
    purpose: str = "check",
) -> None:
    pending = next((n for n, it in enumerate(items) if it["status"] == "pending"), len(items))
    pc = {
        "gap": "joins",
        "set_index": 1,
        "set_total": 1,
        "purpose": purpose,
        "current_index": pending,
        "asked_at_turn": datetime.now(timezone.utc).isoformat(),
        "message_id": message_id,
        "items": items,
    }
    cc = {"set_total": 1, "last_set_index": 1, "gaps": ["joins"], "purpose": purpose}
    with Session() as db:
        row = db.get(SessionModel, sid)
        row.pending_check_json = json.dumps(pc)
        row.current_check_json = json.dumps(cc)
        db.commit()


class _HeldRowLock:
    """Hold the session row with FOR UPDATE on a connection of our own, and
    count request backends blocked on a lock while it is held."""

    def __init__(self, engine, sid: str):
        # The holder shares APP_NAME but never waits, so the poll skips it.
        self._conn = engine.connect()
        self._conn.execute(text("SELECT id FROM sessions WHERE id = :sid FOR UPDATE"), {"sid": sid})

    def _waiters(self) -> int:
        # Activity stats are snapshotted once per transaction, and the
        # holder's transaction stays open; drop the snapshot on every poll.
        self._conn.execute(text("SELECT pg_stat_clear_snapshot()"))
        return self._conn.execute(
            text(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE datname = current_database() AND application_name = :app "
                "AND wait_event_type = 'Lock'"
            ),
            {"app": APP_NAME},
        ).scalar_one()

    def wait_for_waiters(self, expected: int) -> None:
        deadline = time.monotonic() + WAIT_TIMEOUT_S
        seen = self._waiters()
        while seen < expected:
            if time.monotonic() > deadline:
                pytest.fail(f"expected {expected} request(s) blocked on the row lock, saw {seen}")
            time.sleep(0.02)
            seen = self._waiters()
        assert seen == expected

    def release(self) -> None:
        self._conn.commit()
        self._conn.close()

    def close(self) -> None:
        if not self._conn.closed:
            self._conn.rollback()
            self._conn.close()


@pytest.fixture
def pool():
    with ThreadPoolExecutor(max_workers=2) as ex:
        yield ex


@pytest.fixture
def hold(engine, pool):
    """Depends on `pool` so a failed test releases the lock before the pool
    waits on the threads blocked behind it."""
    held: list[_HeldRowLock] = []

    def _hold(sid: str) -> _HeldRowLock:
        lock = _HeldRowLock(engine, sid)
        held.append(lock)
        return lock

    yield _hold
    for lock in held:
        lock.close()


def _post(uid: str, path: str, body: dict | None = None):
    """One TestClient per call: each request runs on its own portal thread.
    Not entered as a context manager, so the lifespan does not run."""
    client = TestClient(app)
    return client.post(path, json=body or {}, headers={"Authorization": f"Bearer test-{uid}"})


def _code(resp) -> str | None:
    return resp.json().get("detail", {}).get("code")


def _row(Session, sid: str) -> tuple[dict | None, dict | None, TopicProfile, datetime | None]:
    with Session() as db:
        row = db.get(SessionModel, sid)
        pc = json.loads(row.pending_check_json) if row.pending_check_json else None
        cc = json.loads(row.current_check_json) if row.current_check_json else None
        profile = TopicProfile.model_validate_json(row.topic_profile_json)
        return pc, cc, profile, row.ended_at


def _recap(Session, msg_id: int) -> dict | None:
    with Session() as db:
        raw = db.get(ChatMessage, msg_id).check_batch_json
        return json.loads(raw) if raw else None


def _events(Session, sid: str) -> list[LearningEvent]:
    with Session() as db:
        return (
            db.execute(
                select(LearningEvent)
                .where(LearningEvent.session_id == sid)
                .order_by(LearningEvent.id)
            )
            .scalars()
            .all()
        )


def test_two_answers_on_one_set_serialize(app_on_postgres, hold, pool):
    Session, uid, sid, msg_id = app_on_postgres
    _seed_set(Session, sid, [_item(0), _item(1), _item(2)], message_id=msg_id)
    path = f"/api/sessions/{sid}/check/answer"

    lock = hold(sid)
    a0 = pool.submit(_post, uid, path, {"index": 0, "selected_index": 0})
    a1 = pool.submit(_post, uid, path, {"index": 1, "selected_index": 2})
    lock.wait_for_waiters(2)
    lock.release()
    r0, r1 = a0.result(JOIN_TIMEOUT_S), a1.result(JOIN_TIMEOUT_S)

    assert (r0.status_code, r1.status_code) == (200, 200)
    pc, _, _, _ = _row(Session, sid)
    assert [it["status"] for it in pc["items"]] == ["answered", "answered", "pending"]
    assert [it["selected_index"] for it in pc["items"][:2]] == [0, 2]
    assert pc["current_index"] == 2
    assert sorted((e.question, e.correct) for e in _events(Session, sid)) == [
        ("Q0?", True),
        ("Q1?", False),
    ]


def test_double_complete_lets_one_follow_up_through(app_on_postgres, hold, pool):
    Session, uid, sid, msg_id = app_on_postgres
    items = [_item(0, "answered", 0), _item(1, "skipped")]
    _seed_set(Session, sid, items, message_id=msg_id)
    path = f"/api/sessions/{sid}/check/complete"

    lock = hold(sid)
    c0 = pool.submit(_post, uid, path)
    c1 = pool.submit(_post, uid, path)
    lock.wait_for_waiters(2)
    lock.release()
    responses = [c0.result(JOIN_TIMEOUT_S), c1.result(JOIN_TIMEOUT_S)]

    winners = [r for r in responses if r.status_code == 200]
    losers = [r for r in responses if r.status_code != 200]
    assert len(winners) == 1 and len(losers) == 1
    assert "event: done" in winners[0].text
    assert losers[0].status_code == 409
    assert _code(losers[0]) == NO_RESOLVED_BATCH

    pc, cc, _, _ = _row(Session, sid)
    assert pc is None and cc is None
    assert [it["status"] for it in _recap(Session, msg_id)["items"]] == ["answered", "skipped"]
    with Session() as db:
        follow_ups = db.execute(
            select(func.count())
            .select_from(ChatMessage)
            .where(
                ChatMessage.session_id == sid,
                ChatMessage.role == "assistant",
                ChatMessage.id > msg_id,
            )
        ).scalar_one()
    assert follow_ups == 1


# Lock bug found here, reported on #418: the answer route writes the Recap
# after its commit, outside the row lock, so a Stop that closes the Set in
# that gap has its frozen Recap overwritten with the pre-Stop "pending" item.
# Roughly half of runs hit it. #419 removes that write and this marker.
@pytest.mark.xfail(
    strict=False,
    raises=AssertionError,
    reason="#419: unlocked Recap write after the answer commit can overwrite Stop's frozen Recap",
)
def test_answer_racing_stop_never_splits_the_set(app_on_postgres, hold, pool):
    Session, uid, sid, msg_id = app_on_postgres
    _seed_set(Session, sid, [_item(0), _item(1)], message_id=msg_id)

    lock = hold(sid)
    answer = pool.submit(
        _post, uid, f"/api/sessions/{sid}/check/answer", {"index": 0, "selected_index": 0}
    )
    lock.wait_for_waiters(1)
    stop = pool.submit(_post, uid, f"/api/sessions/{sid}/check/stop")
    lock.wait_for_waiters(2)
    lock.release()
    ra, rs = answer.result(JOIN_TIMEOUT_S), stop.result(JOIN_TIMEOUT_S)

    # Two items with at most one answered: the set is never done, so Stop
    # always has an open check to close.
    assert rs.status_code == 200
    assert "event: done" in rs.text

    pc, cc, _, _ = _row(Session, sid)
    assert pc is None and cc is None
    recap = _recap(Session, msg_id)
    events = _events(Session, sid)
    if ra.status_code == 200:
        # (a) the answer landed first; Stop skipped the rest.
        assert [it["status"] for it in recap["items"]] == ["answered", "skipped"]
        assert [(e.question, e.correct) for e in events] == [("Q0?", True)]
    else:
        # (b) Stop landed first; the answer found no open set.
        assert ra.status_code == 409
        assert _code(ra) == CHECK_CONFLICT
        assert [it["status"] for it in recap["items"]] == ["skipped", "skipped"]
        assert events == []
    skipped = {it["question"] for it in recap["items"] if it["status"] == "skipped"}
    assert not any(e.question in skipped for e in events)


def test_message_id_stamp_and_answer_both_land(app_on_postgres, hold, pool):
    Session, uid, sid, msg_id = app_on_postgres
    _seed_set(Session, sid, [_item(0), _item(1)], message_id=None)

    def stamp():
        with Session() as db:
            check_question_service.attach_message_id(db, sid, msg_id)

    lock = hold(sid)
    answer = pool.submit(
        _post, uid, f"/api/sessions/{sid}/check/answer", {"index": 0, "selected_index": 1}
    )
    lock.wait_for_waiters(1)
    stamped = pool.submit(stamp)
    lock.wait_for_waiters(2)
    lock.release()
    ra = answer.result(JOIN_TIMEOUT_S)
    stamped.result(JOIN_TIMEOUT_S)

    assert ra.status_code == 200
    pc, _, _, _ = _row(Session, sid)
    assert pc["message_id"] == msg_id
    assert [it["status"] for it in pc["items"]] == ["answered", "pending"]
    assert pc["items"][0]["selected_index"] == 1
    assert [(e.question, e.correct) for e in _events(Session, sid)] == [("Q0?", False)]


def test_session_end_racing_a_diagnostic_answer(app_on_postgres, hold, pool):
    Session, uid, sid, msg_id = app_on_postgres
    items = [_item(0, "answered", 0), _item(1), _item(2)]
    _seed_set(Session, sid, items, message_id=msg_id, purpose="diagnostic")
    # Item 0 was answered before the race; its event is already on file.
    with Session() as db:
        db.add(
            LearningEvent(
                session_id=sid,
                gap_tested="joins",
                question="Q0?",
                correct=True,
                selected_index=0,
                correct_index=0,
                options_json=json.dumps(["a", "b", "c"]),
                purpose="diagnostic",
            )
        )
        db.commit()

    lock = hold(sid)
    end = pool.submit(_post, uid, f"/api/sessions/{sid}/end")
    lock.wait_for_waiters(1)
    answer = pool.submit(
        _post, uid, f"/api/sessions/{sid}/check/answer", {"index": 1, "selected_index": 0}
    )
    lock.wait_for_waiters(2)
    lock.release()
    re_, ra = end.result(JOIN_TIMEOUT_S), answer.result(JOIN_TIMEOUT_S)

    assert re_.status_code == 200
    pc, cc, profile, ended_at = _row(Session, sid)
    assert ended_at is not None
    assert pc is None and cc is None
    assert profile.last_session_summary
    recap = _recap(Session, msg_id)
    assert recap["items"][0]["status"] == "answered"
    assert recap["items"][2]["status"] == "skipped"

    events = _events(Session, sid)
    if ra.status_code == 200:
        # The answer landed: its event exists and the forced grade counts it
        # (2 of 3 correct).
        assert [e.question for e in events] == ["Q0?", "Q1?"]
        assert recap["items"][1]["status"] == "answered"
        assert profile.knowledge_level == "intermediate"
    else:
        assert ra.status_code == 409
        assert [e.question for e in events] == ["Q0?"]
        assert recap["items"][1]["status"] == "skipped"
        assert profile.knowledge_level == "beginner"
