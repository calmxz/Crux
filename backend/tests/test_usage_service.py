from datetime import datetime, timezone
from decimal import Decimal

from db.models import DailyCostLedger, LlmCallLog, User
from db.models import Session as SessionModel
from services.usage_service import usage_summary

NOW = datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc)  # today = 2026-07-10


def _seed_user(db, user_id="test-user"):
    if not db.get(User, user_id):
        db.add(User(id=user_id))
        db.commit()


def _seed_ledger(db, user_id, date_utc, cost):
    db.add(DailyCostLedger(user_id=user_id, date_utc=date_utc, cost_usd=Decimal(cost)))
    db.commit()


def _seed_call(db, user_id, session_id, cost):
    db.add(
        LlmCallLog(
            user_id=user_id,
            session_id=session_id,
            purpose="chat",
            model="m",
            cost_usd=Decimal(cost),
        )
    )
    db.commit()


def _seed_session(db, session_id, user_id="test-user", topic="biology"):
    db.add(SessionModel(id=session_id, user_id=user_id, topic=topic))
    db.commit()


def test_daily_window_zero_filled_oldest_first(db_session):
    _seed_user(db_session)
    _seed_ledger(db_session, "test-user", "2026-07-10", "1.5000")
    _seed_ledger(db_session, "test-user", "2026-07-01", "0.2000")
    _seed_ledger(db_session, "test-user", "2026-06-01", "9.0000")  # outside window
    resp = usage_summary(db_session, "test-user", now=NOW)
    assert len(resp.daily) == 14
    assert resp.daily[0].date_utc.isoformat() == "2026-06-27"
    assert resp.daily[-1].date_utc.isoformat() == "2026-07-10"
    by_date = {d.date_utc.isoformat(): d.cost_usd for d in resp.daily}
    assert by_date["2026-07-10"] == 1.5
    assert by_date["2026-07-01"] == 0.2
    assert by_date["2026-07-05"] == 0.0
    assert "2026-06-01" not in by_date


def test_today_spend_and_caps_from_single_source(db_session):
    from config import settings
    from services.cost_meter import check_cap_from_spend

    _seed_user(db_session)
    _seed_ledger(db_session, "test-user", "2026-07-10", "2.5000")
    resp = usage_summary(db_session, "test-user", now=NOW)
    assert resp.today_spend_usd == 2.5
    assert resp.soft_cap_usd == float(settings.llm_soft_cap_usd)
    assert resp.hard_cap_usd == float(settings.llm_hard_cap_usd)
    # urgent must equal the cost_meter derivation, not an independent literal
    expected_urgent = float(check_cap_from_spend(Decimal("0")).urgent_cap)
    assert resp.urgent_cap_usd == expected_urgent


def test_no_data_returns_zeroes(db_session):
    _seed_user(db_session)
    resp = usage_summary(db_session, "test-user", now=NOW)
    assert resp.today_spend_usd == 0.0
    assert all(d.cost_usd == 0.0 for d in resp.daily)
    assert resp.top_sessions == []


def test_top_sessions_ordering_and_cap_at_three(db_session):
    _seed_user(db_session)
    # Distinct topics per session: all are active (no ended_at) for the same
    # user, and uq_sessions_active_topic forbids two simultaneously-active
    # same-topic sessions per user. s2 keeps the default "biology" topic since
    # its value is asserted below; the others' topics are not asserted.
    for sid, costs, topic in [
        ("s1", ["0.1000"], "s1-topic"),
        ("s2", ["0.5000", "0.5000"], "biology"),  # total 1.0 -> top
        ("s3", ["0.3000"], "s3-topic"),
        ("s4", ["0.2000"], "s4-topic"),
    ]:
        _seed_session(db_session, sid, topic=topic)
        for c in costs:
            _seed_call(db_session, "test-user", sid, c)
    resp = usage_summary(db_session, "test-user", now=NOW)
    assert [t.session_id for t in resp.top_sessions] == ["s2", "s3", "s4"]
    assert resp.top_sessions[0].cost_usd == 1.0
    assert resp.top_sessions[0].topic == "biology"


def test_top_sessions_user_isolation_and_null_session_skipped(db_session):
    _seed_user(db_session)
    _seed_user(db_session, "other-user")
    _seed_session(db_session, "mine", user_id="test-user")
    _seed_session(db_session, "theirs", user_id="other-user")
    _seed_call(db_session, "test-user", "mine", "0.1000")
    _seed_call(db_session, "other-user", "theirs", "5.0000")
    _seed_call(db_session, "test-user", None, "3.0000")  # unattributed: excluded
    resp = usage_summary(db_session, "test-user", now=NOW)
    assert [t.session_id for t in resp.top_sessions] == ["mine"]


def test_usage_service_has_no_tier_literals():
    """Guard: tier thresholds live in config/cost_meter only."""
    import inspect
    import sys

    src = inspect.getsource(sys.modules[usage_summary.__module__])
    for literal in ("2.7", "2.70", "2.0", "2.00", "3.0", "3.00", "0.9"):
        assert literal not in src, f"tier literal {literal} duplicated in usage_service"


def test_resets_at_is_next_utc_midnight(db_session):
    _seed_user(db_session)
    resp = usage_summary(db_session, "test-user", now=NOW)
    assert resp.resets_at == datetime(2026, 7, 11, 0, 0, 0, tzinfo=timezone.utc)


def test_resets_at_agrees_with_429_payload_helper(db_session):
    from services.cost_meter import midnight_utc_iso

    _seed_user(db_session)
    resp = usage_summary(db_session, "test-user", now=NOW)
    assert resp.resets_at == datetime.fromisoformat(midnight_utc_iso(now=NOW))


def test_next_midnight_normalizes_non_utc_clock():
    from datetime import timedelta

    from services.cost_meter import next_midnight_utc

    manila = timezone(timedelta(hours=8))
    # 2026-07-11 07:00 +08:00 is still 2026-07-10 23:00 UTC.
    got = next_midnight_utc(datetime(2026, 7, 11, 7, 0, tzinfo=manila))
    assert got == datetime(2026, 7, 11, 0, 0, tzinfo=timezone.utc)
    assert got.utcoffset() == timedelta(0)
