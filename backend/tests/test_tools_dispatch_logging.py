"""TDD: dispatch logs a WARNING when a tool raises an exception, and rolls
back what the tool left on the session (#569)."""

import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from agent import tools
from agent.types import ToolContext
from contracts import ToolResult, TopicProfile
from db.models import Session as SessionModel
from db.models import User

SESSION_ID = "sess_dispatch_log"
USER_ID = "u_dispatch_log"


@pytest.fixture
def session_row(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="math",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()


@pytest.fixture
def ctx(db_session):
    return ToolContext(
        db=db_session,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc),
    )


def test_dispatch_logs_validation_error(caplog, db_session, session_row, ctx):
    # Missing required gap/items -> ValidationError caught in dispatch.
    bad_args = {"session_id": ctx.session_id}
    with caplog.at_level(logging.WARNING, logger="agent.tools"):
        result = tools.dispatch("ask_check_questions", bad_args, ctx)
    assert result.ok is False
    assert any("ask_check_questions" in r.message for r in caplog.records)


def test_validation_error_message_still_reaches_the_model(db_session, session_row, ctx, caplog):
    """G-04: the coarse error code must NOT swallow ValidationError text --
    the model needs the field-level detail to repair its own tool call."""
    result = tools.dispatch("ask_check_questions", {"session_id": ctx.session_id}, ctx)
    assert result.ok is False
    assert result.error != "tool_failed"
    assert "gap" in result.error
    assert "tool dispatch failed" in caplog.text


def test_unexpected_exception_returns_coarse_code_and_logs_detail(
    caplog, monkeypatch, db_session, session_row, ctx
):
    """G-04: internal exception text (ids, SQL, paths) is server-side detail.
    The model gets a coarse `tool_failed`; the operator gets the real message
    in the WARNING log."""

    def boom(*_args, **_kwargs):
        raise ValueError("session mismatch for sess-123")

    monkeypatch.setattr(tools.profile_service, "apply_patch", boom)

    with caplog.at_level(logging.WARNING, logger="agent.tools"):
        result = tools.dispatch("update_topic_profile", {"focus_target_gap": "glycolysis"}, ctx)

    assert result.ok is False
    assert result.status == "failed"
    assert result.error == "tool_failed"
    assert any("sess-123" in r.getMessage() for r in caplog.records)
    assert any("update_topic_profile" in r.getMessage() for r in caplog.records)


def _ctx_on(db) -> ToolContext:
    return ToolContext(
        db=db, session_id=SESSION_ID, user_id=USER_ID, turn_started_at=datetime.now(timezone.utc)
    )


@pytest.mark.parametrize(
    ("args", "error"),
    [
        # The ValidationError arm: model-authored args keep their detail.
        ({"focus_target_gap": 5}, "focus_target_gap"),
        # The generic arm: the coarse code.
        ({"focus_target_gap": "glycolysis"}, "tool_failed"),
    ],
)
def test_failed_tool_still_returns_its_result_when_the_rollback_raises(
    caplog, monkeypatch, args, error
):
    """#569: dispatch rolls back after a failed tool; a rollback that itself
    raises is logged, and the model still gets the same ToolResult."""

    def boom(*_args, **_kwargs):
        raise ValueError("internal detail")

    monkeypatch.setattr(tools.profile_service, "apply_patch", boom)
    db = MagicMock()
    db.rollback.side_effect = RuntimeError("connection gone")

    with caplog.at_level(logging.WARNING, logger="agent.tools"):
        result = tools.dispatch("update_topic_profile", args, _ctx_on(db))

    db.rollback.assert_called_once_with()
    assert (result.ok, result.status) == (False, "failed")
    assert error in result.error
    assert any("connection gone" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize(
    "returned",
    [
        ToolResult(ok=True, status="ok"),
        ToolResult(ok=False, status="failed", error="empty patch: no fields provided"),
    ],
)
def test_a_tool_that_returns_is_not_rolled_back(monkeypatch, returned):
    """#569: only an exception rolls back; ok and refused returns leave the
    transaction exactly as the tool left it."""
    monkeypatch.setattr(tools.profile_service, "apply_patch", lambda *_a: returned)
    db = MagicMock()

    result = tools.dispatch("update_topic_profile", {"focus_target_gap": "x"}, _ctx_on(db))

    assert result is returned
    db.rollback.assert_not_called()
