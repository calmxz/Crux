from decimal import Decimal

from sqlalchemy import select, text

from db.models import DailyCostLedger, User
from services import cost_meter


def _mk_user(db, uid):
    db.add(User(id=uid))
    db.flush()


def test_check_cap_urgent_tier(db_session, monkeypatch):
    # hard cap $3 -> urgent at $2.70; soft at $2
    user = "u1"
    # below soft
    cost_meter.record_cost(db_session, user, Decimal("1.00"))
    db_session.commit()
    s = cost_meter.check_cap(db_session, user)
    assert (s.soft_breached, s.urgent_breached, s.allowed) == (False, False, True)
    # soft but not urgent
    cost_meter.record_cost(db_session, user, Decimal("1.20"))
    db_session.commit()  # 2.20
    s = cost_meter.check_cap(db_session, user)
    assert (s.soft_breached, s.urgent_breached, s.allowed) == (True, False, True)
    # urgent but not hard
    cost_meter.record_cost(db_session, user, Decimal("0.60"))
    db_session.commit()  # 2.80
    s = cost_meter.check_cap(db_session, user)
    assert (s.soft_breached, s.urgent_breached, s.allowed) == (True, True, True)
    assert s.urgent_cap == Decimal("2.70")
    # hard
    cost_meter.record_cost(db_session, user, Decimal("0.50"))
    db_session.commit()  # 3.30
    s = cost_meter.check_cap(db_session, user)
    assert s.allowed is False


def test_check_cap_from_spend_matches_check_cap_semantics():
    st = cost_meter.check_cap_from_spend(Decimal("0"))
    assert st.allowed and not st.soft_breached and not st.urgent_breached
    st = cost_meter.check_cap_from_spend(Decimal("2.50"))
    assert st.allowed and st.soft_breached
    st = cost_meter.check_cap_from_spend(Decimal("3.00"))
    assert not st.allowed


def test_spend_subquery_returns_todays_spend(db_session):
    cost_meter.record_cost(db_session, "sq-user", Decimal("0.25"))
    used = db_session.execute(
        select(cost_meter.spend_subquery("sq-user"))
    ).scalar_one()
    assert Decimal(str(used or 0)) == Decimal("0.25")


def test_spend_subquery_zero_when_no_ledger_row(db_session):
    used = db_session.execute(
        select(cost_meter.spend_subquery("nobody"))
    ).scalar_one()
    assert Decimal(str(used or 0)) == Decimal("0")


def test_current_spend_reads_through_identity_map(db_session):
    # F-43: db.get returns the identity-map cache without SQL, hiding other
    # sessions' concurrent spend. current_spend must emit a fresh SELECT.
    _mk_user(db_session, "u43")
    cost_meter.record_cost(db_session, "u43", Decimal("0.5"))
    db_session.commit()
    # Prime the identity map the way a long turn does.
    assert cost_meter.current_spend(db_session, "u43") == Decimal("0.5000")
    # Hold a strong reference to the cached row. SQLAlchemy's identity map is
    # a WeakInstanceDict: without this, CPython's GC can reclaim the cached
    # instance between calls and a buggy db.get()-based current_spend would
    # accidentally re-query, letting this test pass even against the old
    # cached-read bug. Keeping `row` alive across the mutation and the final
    # assertion pins the fresh-read behavior deterministically (mirrors the
    # F-17 test below).
    row = db_session.get(DailyCostLedger, ("u43", cost_meter._today_utc()))
    assert row is not None
    # Mutate the row behind the ORM's back (simulates another session's commit).
    db_session.execute(
        text("UPDATE daily_cost_ledger SET cost_usd = 2.0 WHERE user_id = 'u43'")
    )
    assert cost_meter.current_spend(db_session, "u43") == Decimal("2.0000")
    # The cached instance must remain stale (proves `row` was the identity-map
    # hit a cached read would have returned) while current_spend is fresh.
    assert row.cost_usd == Decimal("0.5")


def test_record_cost_is_an_atomic_increment(db_session):
    # F-17: record_cost must not read-modify-write. After the ORM has a stale
    # cached instance, a subsequent record_cost must still add to the DB
    # value, not to the cached one.
    _mk_user(db_session, "u17")
    cost_meter.record_cost(db_session, "u17", Decimal("0.5"))
    db_session.commit()
    row = db_session.get(DailyCostLedger, ("u17", cost_meter._today_utc()))
    assert row is not None  # instance now cached with 0.5
    db_session.execute(
        text("UPDATE daily_cost_ledger SET cost_usd = 1.0 WHERE user_id = 'u17'")
    )
    total = cost_meter.record_cost(db_session, "u17", Decimal("0.25"))
    # Read-modify-write on the cached 0.5 would yield 0.75; atomic SQL yields 1.25.
    assert total == Decimal("1.2500")


def test_reserve_cost_returns_pre_increment_total(db_session):
    # B-05: the gate reads the PRE-increment total so the caller is judged on
    # the spend that existed before its own reservation.
    _mk_user(db_session, "ures")
    cost_meter.record_cost(db_session, "ures", Decimal("0.10"))
    pre = cost_meter.reserve_cost(db_session, "ures", Decimal("0.02"))
    assert pre == Decimal("0.1000")
    assert cost_meter.current_spend(db_session, "ures") == Decimal("0.1200")


def test_reserve_cost_creates_row_when_absent(db_session):
    _mk_user(db_session, "ures2")
    pre = cost_meter.reserve_cost(db_session, "ures2", Decimal("0.02"))
    assert pre == Decimal("0.0000")
    assert cost_meter.current_spend(db_session, "ures2") == Decimal("0.0200")


def test_adjust_cost_allows_negative_delta(db_session):
    _mk_user(db_session, "uadj")
    cost_meter.reserve_cost(db_session, "uadj", Decimal("0.02"))
    total = cost_meter.adjust_cost(db_session, "uadj", Decimal("-0.02"))
    assert total == Decimal("0.0000")
    assert cost_meter.current_spend(db_session, "uadj") == Decimal("0.0000")


def test_adjust_cost_zero_is_a_no_op(db_session):
    _mk_user(db_session, "uadj0")
    cost_meter.record_cost(db_session, "uadj0", Decimal("0.25"))
    assert cost_meter.adjust_cost(db_session, "uadj0", Decimal("0")) == Decimal("0.2500")
    assert cost_meter.current_spend(db_session, "uadj0") == Decimal("0.2500")


def test_sequential_reserves_serialize_at_the_cap(db_session, monkeypatch):
    # B-05: two turns that would each pass a plain read gate at
    # hard_cap - 0.01 must NOT both be admitted: the second reserve's
    # pre-increment total already carries the first's reservation.
    from config import settings

    monkeypatch.setattr(settings, "llm_hard_cap_usd", 3.00)
    _mk_user(db_session, "ucap")
    cost_meter.record_cost(db_session, "ucap", Decimal("2.99"))

    first = cost_meter.reserve_cost(db_session, "ucap", Decimal("0.02"))
    assert cost_meter.check_cap_from_spend(first).allowed is True

    second = cost_meter.reserve_cost(db_session, "ucap", Decimal("0.02"))
    assert second == Decimal("3.0100")
    assert cost_meter.check_cap_from_spend(second).allowed is False


def test_record_cost_returns_running_total_and_quantizes(db_session):
    _mk_user(db_session, "uq")
    assert cost_meter.record_cost(db_session, "uq", 0.00006) == Decimal("0.0001")
    assert cost_meter.record_cost(db_session, "uq", Decimal("0.1")) == Decimal("0.1001")
    # Sub-precision cost quantizes to zero and is a no-op.
    assert cost_meter.record_cost(db_session, "uq", 0.00001) == Decimal("0.1001")
