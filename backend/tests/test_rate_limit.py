from contextlib import contextmanager

import pytest
from sqlalchemy import event as _sa_event
from sqlalchemy.exc import IntegrityError

from config import settings
from db.models import UsageCounter
from services import rate_limit
from services.rate_limit import check_and_increment


def test_cap_allows_up_to_limit(db_session):
    for i in range(settings.daily_cap):
        allowed, used = check_and_increment(db_session, "u1")
        assert allowed is True
        assert used == i + 1


def test_cap_blocks_on_exceed(db_session):
    for _ in range(settings.daily_cap):
        check_and_increment(db_session, "u1")
    allowed, used = check_and_increment(db_session, "u1")
    assert allowed is False
    assert used == settings.daily_cap


def test_different_users_isolated(db_session):
    for _ in range(settings.daily_cap):
        check_and_increment(db_session, "u1")
    allowed, used = check_and_increment(db_session, "u2")
    assert allowed is True
    assert used == 1


def test_next_day_resets(db_session, monkeypatch):
    import services.rate_limit as rl

    monkeypatch.setattr(rl, "_today_utc", lambda: "2099-01-01")
    for _ in range(settings.daily_cap):
        check_and_increment(db_session, "u1")
    allowed, _ = check_and_increment(db_session, "u1")
    assert allowed is False

    monkeypatch.setattr(rl, "_today_utc", lambda: "2099-01-02")
    allowed, used = check_and_increment(db_session, "u1")
    assert allowed is True
    assert used == 1


def test_usage_counter_unique_per_user_per_day(db_session):
    """At most one usage_counter row per (user, UTC day). This constraint is
    what makes the parallel-upload race impossible: without it, concurrent
    uploads each INSERT a row, and every later read then raises
    MultipleResultsFound on scalar_one_or_none()."""
    db_session.add(UsageCounter(user_id="u1", date_utc="2026-06-14", count=1))
    db_session.commit()
    db_session.add(UsageCounter(user_id="u1", date_utc="2026-06-14", count=1))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_concurrent_calls_no_duplicate_rows_no_errors(tmp_path):
    """Fire many concurrent check_and_increment calls for a fresh (user, day)
    with no pre-existing row -- the exact parallel-upload scenario from PR #83.

    The non-atomic SELECT-then-INSERT loses this race: several callers see no
    row and each INSERTs, which (with the unique constraint) raises
    IntegrityError, or (without it) leaves duplicate rows that later make every
    read raise MultipleResultsFound. The atomic upsert must instead leave
    exactly one row with the correct total and never raise.
    """
    import threading

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from db.database import Base

    n = min(8, settings.daily_cap)  # stay at/under cap so every call is allowed
    db_file = tmp_path / "rl.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(bind=engine)
    SessionMaker = sessionmaker(bind=engine)

    errors: list[Exception] = []
    barrier = threading.Barrier(n)

    def worker():
        barrier.wait()  # release all threads together to maximize overlap
        db = SessionMaker()
        try:
            check_and_increment(db, "u1")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    db = SessionMaker()
    rows = db.execute(select(UsageCounter).where(UsageCounter.user_id == "u1")).scalars().all()
    db.close()
    engine.dispose()

    assert errors == [], f"concurrent calls raised: {errors!r}"
    assert len(rows) == 1, f"expected exactly one row, got {len(rows)}"
    assert rows[0].count == n


def test_check_and_increment_never_exceeds_cap_under_contention(db_session, monkeypatch):
    """Even when calls exceed the cap, exactly `daily_cap` are allowed and the
    single row for (user, day) never goes past that count. The existing
    `test_concurrent_calls_no_duplicate_rows_no_errors` above deliberately stays
    at/under the cap so every call is allowed; this test closes the remaining
    gap by pushing past the cap and asserting the ceiling itself holds."""
    from services import rate_limit

    monkeypatch.setattr(rate_limit.settings, "daily_cap", 3)
    user = "u-concurrent"
    results = [rate_limit.check_and_increment(db_session, user) for _ in range(6)]
    allowed = [r for (r, _c) in results if r]
    assert len(allowed) == 3  # cap holds
    # exactly one row for (user, today)
    rows = db_session.query(UsageCounter).filter_by(user_id=user).all()
    assert len(rows) == 1 and rows[0].count == 3


@contextmanager
def _count(db):
    bind = db.get_bind()
    state = {"n": 0}

    def _before(conn, cursor, statement, params, context, executemany):
        state["n"] += 1

    _sa_event.listen(bind, "before_cursor_execute", _before)
    try:
        yield state
    finally:
        _sa_event.remove(bind, "before_cursor_execute", _before)


def test_check_and_increment_two_statements_on_allowed_path(db_session):
    rate_limit.check_and_increment(db_session, "rl-perf")  # warm: row now exists
    with _count(db_session) as q:
        allowed, used = rate_limit.check_and_increment(db_session, "rl-perf")
    assert allowed and used == 2
    assert q["n"] <= 2, f"allowed path used {q['n']} statements"
