"""TDD: run_streaming handles suggest_topics (#354) -- emits topic_suggestions,
ends the turn, and rejects a tool-only call.

The model is the scripted fake provider (conftest fake_llm) behind the real
adapter.
"""

import json
from datetime import datetime, timezone

import pytest

from agent import tutor
from agent.types import ToolContext
from contracts import TopicProfile
from db.models import ChatMessage
from db.models import Session as SessionModel
from db.models import User as UserModel
from services import profile_service, topic_suggest_service
from tests.conftest import tool_call


@pytest.fixture(autouse=True)
def _real_llm_path(fake_llm):
    """Every test runs the real loop against the scripted fake."""


async def _drain(agen):
    return [ev async for ev in agen]


USER_ID = "u1"
SUGGEST = {
    "mode": "broad",
    "topic": "Thermodynamics",
    "items": [
        {"label": "Laws of thermodynamics"},
        {"label": "Heat engines", "hint": "efficiency limits"},
        {"label": "Entropy"},
    ],
}


def _session(db, sid, level=None, state=topic_suggest_service.AWAITING_LEVEL):
    db.add(UserModel(id=USER_ID))
    db.flush()
    db.add(
        SessionModel(
            id=sid,
            user_id=USER_ID,
            topic="Thermodynamics",
            topic_profile_json=TopicProfile(knowledge_level=level).model_dump_json(),
            topic_suggest_state=state,
        )
    )
    db.commit()
    return ToolContext(
        db=db,
        session_id=sid,
        user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc),
    )


def _suggest(id="tc_s"):
    return tool_call("suggest_topics", SUGGEST, id=id)


def _run(ctx):
    return tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx)


@pytest.mark.asyncio
async def test_suggest_topics_emits_card_and_ends_turn(db_session, fake_llm):
    ctx = _session(db_session, "ts1", level="beginner")
    fake_llm.streams = [["Thermodynamics is about energy.", _suggest()], ["SHOULD-NOT-APPEAR"]]

    events = await _drain(_run(ctx))
    types = [e.type for e in events]

    card = next(e for e in events if e.type == "topic_suggestions")
    assert card.data == {
        "mode": "broad",
        "topic": "Thermodynamics",
        "items": [
            {"label": "Laws of thermodynamics", "hint": None},
            {"label": "Heat engines", "hint": "efficiency limits"},
            {"label": "Entropy", "hint": None},
        ],
    }
    assert types[-1] == "done"
    assert types.index("topic_suggestions") < types.index("done")
    assert not any("SHOULD-NOT-APPEAR" in str(e.data) for e in events)

    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == "ts1").one()
    assert msg.status == "complete"
    assert topic_suggest_service.from_tool_calls(msg.tool_calls_json).model_dump() == card.data
    db_session.expire_all()
    assert db_session.get(SessionModel, "ts1").topic_suggest_state == topic_suggest_service.DONE


@pytest.mark.asyncio
async def test_tool_only_suggest_is_rejected_until_prose_is_written(db_session, fake_llm):
    ctx = _session(db_session, "ts2", level="beginner")
    fake_llm.streams = [
        [_suggest(id="tc_bare")],
        ["Here is the overview.", _suggest(id="tc_ok")],
    ]

    events = await _drain(_run(ctx))

    bare = next(e for e in events if e.type == "tool_call_done" and e.data["id"] == "tc_bare")
    assert bare.data["status"] == "error"
    assert "reply" in bare.data["error"]
    assert [e.type for e in events].count("topic_suggestions") == 1
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_declared_level_patch_then_suggest_in_one_turn(db_session, fake_llm):
    # DIAGNOSTIC REQUIRED turn: the learner states a level; the model records
    # it and offers the card in the same response.
    ctx = _session(db_session, "ts3", level=None)
    patch = tool_call(
        "update_topic_profile",
        {"knowledge_level": "intermediate", "evidence_type": "declared"},
        id="tc_lvl",
    )
    fake_llm.streams = [["Intermediate it is.", patch, _suggest()]]

    events = await _drain(_run(ctx))

    assert profile_service.load_profile(db_session, "ts3").knowledge_level == "intermediate"
    assert "topic_suggestions" in [e.type for e in events]
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_ask_and_suggest_bundled_only_the_first_terminal_runs(db_session, fake_llm):
    ctx = _session(db_session, "ts4", level="beginner")
    ask = tool_call(
        "ask_check_questions",
        {
            "gap": "entropy",
            "set_index": 1,
            "set_total": 1,
            "items": [
                {"question": "Q?", "options": ["a", "b"], "correct_index": 0, "explanation": "e."}
            ],
        },
        id="tc_ask",
    )
    fake_llm.streams = [["Quick check:", ask, _suggest()]]

    events = await _drain(_run(ctx))
    types = [e.type for e in events]

    assert "check_question" in types
    assert "topic_suggestions" not in types
    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == "ts4").one()
    assert [tc["name"] for tc in json.loads(msg.tool_calls_json)] == ["ask_check_questions"]
    db_session.expire_all()
    # The card is still owed; the next at-level reply offers it.
    assert (
        db_session.get(SessionModel, "ts4").topic_suggest_state
        == topic_suggest_service.AWAITING_LEVEL
    )
