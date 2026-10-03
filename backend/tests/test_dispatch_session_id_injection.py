"""TDD: dispatch trusts ctx.session_id, not the model-supplied one.

The LLM is never told the real session id (it is absent from the system prompt),
so it hallucinates a value like "session_001". Every tool service guards
args.session_id == ctx.session_id and rejects the mismatch, silently breaking
every tool call (this is the real cause of the "Profile update failed" chip).
The route-derived ctx.session_id is authoritative; dispatch must inject it before
validation so a wrong OR omitted model value can never reach the guard.
"""

from datetime import datetime, timezone

import pytest

from agent import tools
from agent.types import ToolContext
from contracts import TopicProfile
from db.models import Session as SessionModel
from db.models import User
from services import profile_service

SESSION_ID = "sess_inject"
USER_ID = "u_inject"


@pytest.fixture
def session_row(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="cellular respiration",
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


def test_dispatch_overrides_wrong_session_id(db_session, session_row, ctx):
    # Model hallucinated "session_001"; a focus-only patch must still succeed.
    args = {"session_id": "session_001", "focus_target_gap": "electron transport chain"}

    result = tools.dispatch("update_topic_profile", args, ctx)

    assert result.ok is True, result.error
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert profile.focus_target_gap == "electron transport chain"


def test_dispatch_injects_omitted_session_id(db_session, session_row, ctx):
    # Model omitted session_id entirely; dispatch must supply ctx's, not raise.
    args = {"focus_target_gap": "glycolysis"}

    result = tools.dispatch("update_topic_profile", args, ctx)

    assert result.ok is True, result.error
