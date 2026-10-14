from decimal import Decimal

import pytest

from db.models import User
from lib.error_codes import DAILY_COST_CAP_REACHED, GLOBAL_COST_CAP_REACHED
from services import cost_meter

USER = "u_guard"


@pytest.fixture
def seeded(db_session):
    db_session.add(User(id=USER))
    db_session.commit()


def test_global_spend_sums_todays_ledger(db_session, seeded):
    assert cost_meter.global_spend(db_session) == Decimal("0.0000")
    cost_meter.record_cost(db_session, USER, Decimal("0.5000"))
    db_session.commit()
    assert cost_meter.global_spend(db_session) == Decimal("0.5000")


def test_assert_within_caps_passes_under_caps(db_session, seeded):
    cost_meter.assert_within_caps(db_session, USER)  # no raise


def test_assert_within_caps_raises_on_user_hard_cap(db_session, seeded, monkeypatch):
    monkeypatch.setattr("services.cost_meter.settings.llm_hard_cap_usd", 0.10)
    cost_meter.record_cost(db_session, USER, Decimal("0.2000"))
    db_session.commit()
    with pytest.raises(cost_meter.CostCapExceeded) as exc:
        cost_meter.assert_within_caps(db_session, USER)
    assert exc.value.code == DAILY_COST_CAP_REACHED


def test_assert_within_caps_raises_on_global_ceiling(db_session, seeded, monkeypatch):
    monkeypatch.setattr("services.cost_meter.settings.global_daily_cost_cap_usd", 0.10)
    cost_meter.record_cost(db_session, USER, Decimal("0.2000"))
    db_session.commit()
    with pytest.raises(cost_meter.CostCapExceeded) as exc:
        cost_meter.assert_within_caps(db_session, USER)
    assert exc.value.code == GLOBAL_COST_CAP_REACHED


def test_global_ceiling_disabled_when_unset(db_session, seeded):
    cost_meter.record_cost(db_session, USER, Decimal("1.0000"))
    db_session.commit()
    cost_meter.assert_within_caps(db_session, USER)  # no raise
