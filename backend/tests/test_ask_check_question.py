"""TDD: ask_check_questions tool registers a pending check-question batch."""

from datetime import datetime, timezone

import pytest

from agent import tools
from agent.types import ToolContext
from contracts import TopicProfile
from db.models import Session as SessionModel
from db.models import User
from services import check_question_service as cq
from services import pending_check_store as pcs

SESSION_ID = "sess_acq"
USER_ID = "u_acq"


@pytest.fixture
def session_row(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="biology",
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


def test_ask_sets_pending_check(db_session, session_row, ctx):
    args = {
        "session_id": ctx.session_id,
        "set_index": 1, "set_total": 1, "gap": "calvin_cycle",
        "items": [
            {
                "question": "Inputs?",
                "options": ["CO2 and H2O", "O2 and glucose"],
                "correct_index": 0,
                "explanation": "CO2 is fixed in the Calvin cycle.",
            }
        ],
    }
    result = tools.dispatch("ask_check_questions", args, ctx)
    assert result.ok is True
    pc = cq.get_pending_check(db_session, ctx.session_id)
    assert pc["gap"] == "calvin_cycle"
    assert pcs.parse_asked_at(pc) == ctx.turn_started_at


def test_ask_rejected_when_one_already_open(db_session, session_row, ctx):
    tools.dispatch(
        "ask_check_questions",
        {
            "session_id": ctx.session_id,
            "set_index": 1, "set_total": 1, "gap": "g1",
            "items": [
                {"question": "q1?", "options": ["a", "b"], "correct_index": 0, "explanation": "a."}
            ],
        },
        ctx,
    )
    result = tools.dispatch(
        "ask_check_questions",
        {
            "session_id": ctx.session_id,
            "set_index": 1, "set_total": 1, "gap": "g2",
            "items": [
                {"question": "q2?", "options": ["a", "b"], "correct_index": 0, "explanation": "a."}
            ],
        },
        ctx,
    )
    assert result.ok is False
    assert "already" in (result.error or "").lower()


def test_tool_manifest_drops_record_learning_event_and_requires_options():
    from agent.tools import TOOLS
    names = [t["function"]["name"] for t in TOOLS]
    assert "record_learning_event" not in names
    ask = next(t for t in TOOLS if t["function"]["name"] == "ask_check_questions")
    # In the batch schema, options/correct_index are nested inside items[].
    # Verify the items array is required at top level.
    required = ask["function"]["parameters"]["required"]
    assert "items" in required
    # Verify item sub-schema requires options and correct_index.
    defs = ask["function"]["parameters"].get("$defs", {})
    item_schema = defs.get("Item", {})
    item_required = item_schema.get("required", [])
    assert "options" in item_required and "correct_index" in item_required
