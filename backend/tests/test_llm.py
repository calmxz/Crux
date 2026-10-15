"""#411: the LLM adapter shell (llm-adapter 2/4).

The provider is the scripted FakeLlmProvider from conftest; the gate, retry
and settlement are the real ones, running against the sqlite test engine.
Isolation from the caller's transaction is asserted on Postgres only, in
test_llm_characterisation_pg.py.
"""

import logging
import threading
from decimal import Decimal

import litellm
import pytest
import sqlalchemy.exc
from sqlalchemy import select

from config import settings
from db.models import DailyCostLedger, LlmCallLog, User
from lib.error_codes import DAILY_COST_CAP_REACHED, GLOBAL_COST_CAP_REACHED
from services import cost_meter, llm

USER_ID = "llm-u1"
SESSION_ID = "llm-s1"
MESSAGES = [{"role": "user", "content": "hi"}]


@pytest.fixture(autouse=True)
def _caps(monkeypatch):
    monkeypatch.setattr(settings, "llm_soft_cap_usd", 2.00)
    monkeypatch.setattr(settings, "llm_hard_cap_usd", 3.00)
    monkeypatch.setattr(settings, "global_daily_cost_cap_usd", None)
    monkeypatch.setattr(settings, "llm_retry_attempts", 2)


@pytest.fixture
def user(db_session):
    db_session.add(User(id=USER_ID))
    db_session.commit()


def _meter(user_id=USER_ID, purpose="summary") -> llm.Meter:
    return llm.Meter(user_id=user_id, session_id=SESSION_ID, purpose=purpose)


def _log_rows(db) -> list[tuple[str, str, Decimal]]:
    rows = db.execute(
        select(LlmCallLog.purpose, LlmCallLog.model, LlmCallLog.cost_usd).order_by(LlmCallLog.id)
    ).all()
    return [(p, m, Decimal(str(c))) for p, m, c in rows]


def _rate_limited():
    return litellm.RateLimitError(message="slow down", llm_provider="gemini", model="m")


def _timeout():
    return litellm.Timeout(message="too slow", model="m", llm_provider="gemini")


async def _complete():
    return await llm.get().complete(MESSAGES, meter=_meter(), temperature=0.2, timeout=5)


# --- happy path ------------------------------------------------------------


async def test_complete_settles_ledger_and_call_log(db_session, user, fake_llm):
    fake_llm.replies = ["hello"]
    fake_llm.cost = Decimal("0.002")

    result = await _complete()

    assert (result.text, result.cost) == ("hello", Decimal("0.002"))
    assert fake_llm.complete_calls == [{"messages": MESSAGES, "temperature": 0.2, "timeout": 5}]
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0020")
    assert _log_rows(db_session) == [("summary", "fake/chat", Decimal("0.0020"))]


def test_embed_settles_under_the_embedding_model(db_session, user, fake_llm):
    fake_llm.cost = Decimal("0.0005")

    result = llm.get().embed(["a", "b"], meter=_meter(purpose="embedding"))

    assert len(result.vectors) == 2
    assert len(result.vectors[0]) == settings.embedding_dim
    assert fake_llm.embed_calls == [["a", "b"]]
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0005")
    assert _log_rows(db_session) == [("embedding", "fake/embedding", Decimal("0.0005"))]


async def test_aembed_settles(db_session, user, fake_llm):
    fake_llm.cost = Decimal("0.0005")

    await llm.get().aembed(["q"], meter=_meter(purpose="embedding"))

    assert fake_llm.aembed_calls == [["q"]]
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0005")


# --- gate --------------------------------------------------------------------


async def test_gate_refuses_over_the_user_cap(db_session, user, fake_llm):
    cost_meter.record_cost(db_session, USER_ID, Decimal("3.00"))
    db_session.commit()

    with pytest.raises(llm.CallRefused) as exc:
        await _complete()

    assert isinstance(exc.value, cost_meter.CostCapExceeded)
    assert exc.value.code == DAILY_COST_CAP_REACHED
    assert fake_llm.complete_calls == []


def test_gate_refuses_over_the_global_ceiling(db_session, user, fake_llm, monkeypatch):
    monkeypatch.setattr(settings, "global_daily_cost_cap_usd", 1.00)
    cost_meter.record_cost(db_session, "someone-else", Decimal("1.00"))
    db_session.commit()

    with pytest.raises(cost_meter.CostCapExceeded) as exc:
        llm.get().embed(["a"], meter=_meter())

    assert exc.value.code == GLOBAL_COST_CAP_REACHED
    assert fake_llm.embed_calls == []


async def test_failing_spend_read_raises_and_never_calls_the_provider(
    db_session, user, fake_llm, monkeypatch
):
    def boom(db, user_id):
        raise RuntimeError("spend read failed")

    monkeypatch.setattr(cost_meter, "current_spend", boom)

    with pytest.raises(RuntimeError, match="spend read failed"):
        await _complete()

    assert fake_llm.complete_calls == []


def test_no_user_skips_gate_and_ledger(db_session, fake_llm, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("gate must not run without a user")

    monkeypatch.setattr(cost_meter, "assert_within_caps", boom)
    fake_llm.cost = Decimal("0.0005")

    result = llm.get().embed(["a"], meter=llm.Meter(user_id=None, session_id=None, purpose="x"))

    assert len(result.vectors) == 1
    assert _log_rows(db_session) == []
    assert cost_meter.global_spend(db_session) == Decimal("0")


# --- settlement --------------------------------------------------------------


async def test_failed_settlement_keeps_the_call_log_and_retries_the_ledger(
    db_session, user, fake_llm, monkeypatch, caplog
):
    real_record_cost = cost_meter.record_cost
    calls = []

    def ledger_busy_once(*args, **kwargs):
        calls.append(args[1:])
        if len(calls) == 1:
            raise RuntimeError("lock timeout")
        return real_record_cost(*args, **kwargs)

    scheduled = []
    monkeypatch.setattr(llm, "_schedule", lambda delay, fn, *a: scheduled.append((delay, fn, a)))
    monkeypatch.setattr(cost_meter, "record_cost", ledger_busy_once)
    fake_llm.replies = ["kept"]
    fake_llm.cost = Decimal("0.002")

    with caplog.at_level(logging.INFO, logger="services.llm"):
        result = await _complete()

        # The request returns at once; the receipt is kept, the ledger deferred.
        assert result.text == "kept"
        assert _log_rows(db_session) == [("summary", "fake/chat", Decimal("0.0020"))]
        assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0")
        [deferred] = [r for r in caplog.records if r.name == "services.llm"]
        # Error level: the record that survives if the retry never runs.
        assert deferred.levelno == logging.ERROR
        assert deferred.getMessage() == "llm settlement deferred: lock timeout"
        assert (deferred.user_id, deferred.cost_usd, deferred.call_logged) == (
            USER_ID,
            "0.002",
            True,
        )

        [(delay, fn, args)] = scheduled
        assert delay == llm.SETTLE_RETRY_DELAY_S
        fn(*args)

    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0020")
    assert len(_log_rows(db_session)) == 1  # the retry adds no second receipt
    assert calls == [(USER_ID, Decimal("0.002"))] * 2
    landed = [r for r in caplog.records if r.name == "services.llm"][-1]
    assert (landed.levelno, landed.getMessage()) == (logging.INFO, "llm deferred settlement landed")


async def test_failed_retry_logs_at_error_with_the_receipt_kept(
    db_session, user, fake_llm, monkeypatch, caplog
):
    def ledger_down(*args, **kwargs):
        raise RuntimeError("ledger down")

    monkeypatch.setattr(cost_meter, "record_cost", ledger_down)
    fake_llm.replies = ["kept"]
    fake_llm.cost = Decimal("0.002")

    with caplog.at_level(logging.ERROR, logger="services.llm"):
        result = await _complete()

    assert result.text == "kept"
    assert _log_rows(db_session) == [("summary", "fake/chat", Decimal("0.0020"))]
    records = [r for r in caplog.records if r.name == "services.llm"]
    assert [r.getMessage() for r in records] == [
        "llm settlement deferred: ledger down",
        "llm settlement failed: ledger down",
    ]
    record = records[-1]
    assert (record.user_id, record.session_id, record.purpose) == (USER_ID, SESSION_ID, "summary")
    assert (record.cost_usd, record.call_logged) == ("0.002", True)


def _ledger_down_once(monkeypatch, exc):
    real = cost_meter.record_cost
    calls = []

    def record_cost(*args, **kwargs):
        calls.append(kwargs.get("date_utc"))
        if len(calls) == 1:
            raise exc
        return real(*args, **kwargs)

    monkeypatch.setattr(cost_meter, "record_cost", record_cost)
    return calls


async def test_full_retry_capacity_logs_the_spend_unsettled(
    db_session, user, fake_llm, monkeypatch, caplog
):
    _ledger_down_once(monkeypatch, RuntimeError("lock timeout"))
    scheduled = []
    monkeypatch.setattr(llm, "_schedule", lambda delay, fn, *a: scheduled.append(fn))
    monkeypatch.setattr(llm, "_retry_slots", threading.BoundedSemaphore(1))
    llm._retry_slots.acquire()  # another retry already waiting
    fake_llm.cost = Decimal("0.002")

    with caplog.at_level(logging.ERROR, logger="services.llm"):
        await _complete()

    assert scheduled == []
    assert _log_rows(db_session) == [("summary", "fake/chat", Decimal("0.0020"))]
    [record] = [r for r in caplog.records if r.name == "services.llm"]
    assert record.getMessage().startswith("llm settlement failed: retry capacity full")
    assert record.cost_usd == "0.002"


async def test_pool_timeout_leaves_the_receipt_to_the_retry(
    db_session, user, fake_llm, monkeypatch
):
    _ledger_down_once(monkeypatch, sqlalchemy.exc.TimeoutError("pool full"))
    scheduled = []
    monkeypatch.setattr(llm, "_schedule", lambda delay, fn, *a: scheduled.append((fn, a)))
    fake_llm.cost = Decimal("0.002")

    await _complete()

    assert _log_rows(db_session) == []  # no second checkout on the request path
    [(fn, args)] = scheduled
    fn(*args)
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0020")
    assert _log_rows(db_session) == [("summary", "fake/chat", Decimal("0.0020"))]


async def test_retry_books_to_the_day_the_call_was_settled(db_session, user, fake_llm, monkeypatch):
    calls = _ledger_down_once(monkeypatch, RuntimeError("lock timeout"))
    scheduled = []
    monkeypatch.setattr(llm, "_schedule", lambda delay, fn, *a: scheduled.append((fn, a)))
    monkeypatch.setattr(cost_meter, "_today_utc", lambda: "2026-10-14")
    fake_llm.cost = Decimal("0.002")

    await _complete()
    monkeypatch.setattr(cost_meter, "_today_utc", lambda: "2026-10-15")  # past midnight
    [(fn, args)] = scheduled
    fn(*args)

    assert calls == [None, "2026-10-14"]
    row = db_session.execute(select(DailyCostLedger)).scalar_one()
    assert (row.date_utc, Decimal(str(row.cost_usd))) == ("2026-10-14", Decimal("0.0020"))


async def test_lost_call_log_row_logs_at_error_and_keeps_the_ledger(
    db_session, user, fake_llm, monkeypatch, caplog
):
    monkeypatch.setattr(cost_meter, "log_call", lambda *a, **k: False)
    fake_llm.cost = Decimal("0.002")

    with caplog.at_level(logging.ERROR, logger="services.llm"):
        await _complete()

    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0020")
    [record] = [r for r in caplog.records if r.name == "services.llm"]
    assert record.getMessage() == "llm call log row lost"
    assert (record.user_id, record.purpose, record.cost_usd) == (USER_ID, "summary", "0.002")


# --- retry and failed-call settlement ---------------------------------------


async def test_retry_on_429_then_success_bills_once(db_session, user, fake_llm):
    fake_llm.replies = [_rate_limited(), "second try"]
    fake_llm.cost = Decimal("0.002")
    fake_llm.timeout_cost = Decimal("0.5")  # must not be charged for a 429

    result = await _complete()

    assert result.text == "second try"
    assert len(fake_llm.complete_calls) == 2
    assert fake_llm.estimates == []
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0020")
    assert _log_rows(db_session) == [("summary", "fake/chat", Decimal("0.0020"))]


async def test_retry_gives_up_after_the_configured_attempts(db_session, user, fake_llm):
    fake_llm.replies = [_rate_limited(), _rate_limited(), _rate_limited(), "never"]

    with pytest.raises(litellm.RateLimitError):
        await _complete()

    assert len(fake_llm.complete_calls) == 3
    assert fake_llm.replies == ["never"]
    assert _log_rows(db_session) == []


async def test_completion_timeout_is_not_retried_and_settles_an_estimate(
    db_session, user, fake_llm
):
    fake_llm.replies = [_timeout(), "never"]
    fake_llm.timeout_cost = Decimal("0.0003")

    with pytest.raises(litellm.Timeout):
        await _complete()

    assert len(fake_llm.complete_calls) == 1
    assert fake_llm.estimates == [("completion", MESSAGES)]
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0003")
    assert _log_rows(db_session) == [("summary", "fake/chat", Decimal("0.0003"))]
    fake_llm.replies.clear()


def test_embedding_timeout_is_retried_and_each_attempt_settles(db_session, user, fake_llm):
    fake_llm.embed_errors = [_timeout()]
    fake_llm.timeout_cost = Decimal("0.0001")
    fake_llm.cost = Decimal("0.0005")

    llm.get().embed(["a"], meter=_meter(purpose="embedding"))

    assert fake_llm.embed_calls == [["a"], ["a"]]
    assert fake_llm.estimates == [("embedding", ["a"])]
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0006")
    assert [cost for _, _, cost in _log_rows(db_session)] == [
        Decimal("0.0001"),
        Decimal("0.0005"),
    ]


async def test_non_transient_error_is_raised_at_once_and_settles_nothing(
    db_session, user, fake_llm
):
    fake_llm.replies = [ValueError("bad request")]
    fake_llm.timeout_cost = Decimal("0.5")

    with pytest.raises(ValueError):
        await _complete()

    assert len(fake_llm.complete_calls) == 1
    assert fake_llm.estimates == []
    assert _log_rows(db_session) == []


# --- provider resolution -----------------------------------------------------


def test_get_resolves_the_provider_per_call(monkeypatch):
    monkeypatch.setattr(llm, "_provider", None)
    assert isinstance(llm.get().provider, llm.LiteLlmProvider)

    fake = object()
    monkeypatch.setattr(llm, "_provider", fake)
    assert llm.get().provider is fake
