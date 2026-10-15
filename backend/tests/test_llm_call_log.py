"""TDD: cost_meter.log_call + LlmCallLog model (migration 0014).

llm_call_log is an analytics-only, per-call cost attribution table. It is
additive to the daily cost ledger (record_cost) -- never a replacement, and
cap gating stays on the daily ledger. log_call must never raise: a failed
log write must not fail the user's turn.
"""

from decimal import Decimal
from unittest.mock import patch

from db.models import LlmCallLog
from services import cost_meter


def test_log_call_writes_row(db_session):
    written = cost_meter.log_call(
        db_session,
        user_id="u1",
        session_id="s1",
        purpose="chat",
        model="gemini/gemini-3.5-flash-lite",
        cost_usd=Decimal("0.0032"),
    )
    assert written is True
    row = db_session.query(LlmCallLog).one()
    assert row.purpose == "chat" and row.session_id == "s1"
    assert row.cost_usd == Decimal("0.0032")


def test_log_call_zero_cost_skipped(db_session):
    cost_meter.log_call(
        db_session,
        user_id="u1",
        session_id=None,
        purpose="summary",
        model="m",
        cost_usd=0,
    )
    assert db_session.query(LlmCallLog).count() == 0


def test_log_call_failure_is_isolated(db_session):
    with patch.object(db_session, "add", side_effect=RuntimeError("boom")):
        written = cost_meter.log_call(
            db_session,
            user_id="u1",
            session_id="s1",
            purpose="chat",
            model="m",
            cost_usd=Decimal("0.01"),
        )  # must not raise
    assert written is False  # the adapter error-logs a lost row on False


def test_log_call_flush_failure_does_not_break_session(db_session):
    """Stronger isolation check: a failure during flush (not just db.add)
    must not leave the session in SQLAlchemy's rollback-required state --
    otherwise the caller's next unguarded db.commit() (e.g. persisting the
    assistant message) would raise and fail the user's turn."""
    with patch.object(db_session, "flush", side_effect=RuntimeError("boom")):
        written = cost_meter.log_call(
            db_session,
            user_id="u1",
            session_id="s1",
            purpose="chat",
            model="m",
            cost_usd=Decimal("0.01"),
        )  # must not raise
    assert written is False  # the adapter error-logs a lost row on False

    # Session must still be usable: no row was committed (savepoint rolled
    # back), and further work on the session must not raise.
    assert db_session.query(LlmCallLog).count() == 0
    db_session.add(
        LlmCallLog(
            user_id="u2",
            session_id=None,
            purpose="chat",
            model="m",
            cost_usd=Decimal("0.02"),
        )
    )
    db_session.commit()
    assert db_session.query(LlmCallLog).count() == 1


def test_log_call_persists_token_counts(db_session):
    cost_meter.log_call(
        db_session,
        user_id="u1",
        session_id=None,
        purpose="chat",
        model="m",
        cost_usd="0.0100",
        prompt_tokens=1200,
        completion_tokens=340,
        cached_tokens=900,
    )
    row = db_session.query(LlmCallLog).one()
    assert row.prompt_tokens == 1200
    assert row.completion_tokens == 340
    assert row.cached_tokens == 900


def test_log_call_token_kwargs_default_null(db_session):
    cost_meter.log_call(
        db_session,
        user_id="u1",
        session_id=None,
        purpose="chat",
        model="m",
        cost_usd="0.0100",
    )
    row = db_session.query(LlmCallLog).one()
    assert row.prompt_tokens is None
    assert row.completion_tokens is None
    assert row.cached_tokens is None
