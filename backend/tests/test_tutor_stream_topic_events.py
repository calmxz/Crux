"""TDD: run_streaming handles suggest_topics (#354) -- emits topic_suggestions,
ends the turn, and rejects a tool-only call.

Harness mirrors test_tutor_stream_check_events.py (helpers copied so this
module is self-contained).
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import tutor
from agent.types import ToolContext
from config import settings
from contracts import TopicProfile
from db.models import ChatMessage
from db.models import Session as SessionModel
from db.models import User as UserModel
from services import profile_service, topic_suggest_service
from services.cost_meter import CapStatus


def _content_chunk(token):
    delta = SimpleNamespace(content=token, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _tool_fragment(index, id=None, name=None, arguments=None):
    fn = SimpleNamespace()
    fn.name = name
    fn.arguments = arguments
    frag = SimpleNamespace()
    frag.index = index
    frag.id = id
    frag.function = fn
    return frag


def _tool_chunk(*fragments):
    delta = SimpleNamespace(content=None, tool_calls=list(fragments))
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _make_stream(*chunks):
    async def _gen():
        for c in chunks:
            yield c
    return _gen()


def _allow_cap(monkeypatch):
    cap = CapStatus(
        allowed=True, used=Decimal("0.0"), soft_breached=False, urgent_breached=False,
        soft_cap=Decimal("2.0"), urgent_cap=Decimal("2.70"), hard_cap=Decimal("3.0"),
    )
    monkeypatch.setattr("agent.tutor.cost_meter.check_cap", MagicMock(return_value=cap))


@pytest.fixture(autouse=True)
def _real_llm_path(monkeypatch):
    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")
    _allow_cap(monkeypatch)


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
    db.add(SessionModel(
        id=sid, user_id=USER_ID, topic="Thermodynamics",
        topic_profile_json=TopicProfile(knowledge_level=level).model_dump_json(),
        topic_suggest_state=state,
    ))
    db.commit()
    return ToolContext(
        db=db, session_id=sid, user_id=USER_ID, turn_started_at=datetime.now(timezone.utc),
    )


def _suggest(id="tc_s", index=0):
    return _tool_fragment(index=index, id=id, name="suggest_topics", arguments=json.dumps(SUGGEST))


def _run(ctx):
    return tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx)


@pytest.mark.asyncio
async def test_suggest_topics_emits_card_and_ends_turn(monkeypatch, db_session):
    ctx = _session(db_session, "ts1", level="beginner")
    turn1 = _make_stream(_content_chunk("Thermodynamics is about energy."), _tool_chunk(_suggest()))
    turn2 = _make_stream(_content_chunk("SHOULD-NOT-APPEAR"))
    monkeypatch.setattr("agent.tutor.litellm.acompletion", AsyncMock(side_effect=[turn1, turn2]))

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
async def test_tool_only_suggest_is_rejected_until_prose_is_written(monkeypatch, db_session):
    ctx = _session(db_session, "ts2", level="beginner")
    turn1 = _make_stream(_tool_chunk(_suggest(id="tc_bare")))
    turn2 = _make_stream(_content_chunk("Here is the overview."), _tool_chunk(_suggest(id="tc_ok")))
    monkeypatch.setattr("agent.tutor.litellm.acompletion", AsyncMock(side_effect=[turn1, turn2]))

    events = await _drain(_run(ctx))

    bare = next(e for e in events if e.type == "tool_call_done" and e.data["id"] == "tc_bare")
    assert bare.data["status"] == "error"
    assert "reply" in bare.data["error"]
    assert [e.type for e in events].count("topic_suggestions") == 1
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_declared_level_patch_then_suggest_in_one_turn(monkeypatch, db_session):
    # DIAGNOSTIC REQUIRED turn: the learner states a level; the model records
    # it and offers the card in the same response.
    ctx = _session(db_session, "ts3", level=None)
    patch = _tool_fragment(
        index=0, id="tc_lvl", name="update_topic_profile",
        arguments=json.dumps({"knowledge_level": "intermediate", "evidence_type": "declared"}),
    )
    turn1 = _make_stream(
        _content_chunk("Intermediate it is."), _tool_chunk(patch, _suggest(index=1)),
    )
    monkeypatch.setattr("agent.tutor.litellm.acompletion", AsyncMock(side_effect=[turn1]))

    events = await _drain(_run(ctx))

    assert profile_service.load_profile(db_session, "ts3").knowledge_level == "intermediate"
    assert "topic_suggestions" in [e.type for e in events]
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_ask_and_suggest_bundled_only_the_first_terminal_runs(monkeypatch, db_session):
    ctx = _session(db_session, "ts4", level="beginner")
    ask = _tool_fragment(
        index=0, id="tc_ask", name="ask_check_questions",
        arguments=json.dumps({
            "gap": "entropy", "set_index": 1, "set_total": 1,
            "items": [{"question": "Q?", "options": ["a", "b"], "correct_index": 0, "explanation": "e."}],
        }),
    )
    turn1 = _make_stream(_content_chunk("Quick check:"), _tool_chunk(ask, _suggest(index=1)))
    monkeypatch.setattr("agent.tutor.litellm.acompletion", AsyncMock(side_effect=[turn1]))

    events = await _drain(_run(ctx))
    types = [e.type for e in events]

    assert "check_question" in types
    assert "topic_suggestions" not in types
    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == "ts4").one()
    assert [tc["name"] for tc in json.loads(msg.tool_calls_json)] == ["ask_check_questions"]
    db_session.expire_all()
    # The card is still owed; the next at-level reply offers it.
    assert db_session.get(SessionModel, "ts4").topic_suggest_state == topic_suggest_service.AWAITING_LEVEL
