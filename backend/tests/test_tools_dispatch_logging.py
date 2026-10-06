"""TDD: dispatch logs a WARNING when a tool raises an exception."""

import logging
from datetime import datetime, timezone

import pytest

from agent import tools
from agent.types import ToolContext
from contracts import TopicProfile
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


def test_validation_error_message_still_reaches_the_model(db_session, session_row, ctx):
    """G-04: the coarse error code must NOT swallow ValidationError text --
    the model needs the field-level detail to repair its own tool call."""
    result = tools.dispatch("ask_check_questions", {"session_id": ctx.session_id}, ctx)
    assert result.ok is False
    assert result.error != "tool_failed"
    assert "gap" in result.error


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
        result = tools.dispatch(
            "update_topic_profile", {"focus_target_gap": "glycolysis"}, ctx
        )

    assert result.ok is False
    assert result.status == "failed"
    assert result.error == "tool_failed"
    assert any("sess-123" in r.getMessage() for r in caplog.records)
    assert any("update_topic_profile" in r.getMessage() for r in caplog.records)
