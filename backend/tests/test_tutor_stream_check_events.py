"""TDD: run_streaming emits check_question event and terminates turn on ask_check_questions.

Mirrors test_tutor_stream.py harness exactly. Helpers are copied from that
module so this file is self-contained.
"""

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import tutor
from agent.types import ToolContext
from config import settings
from db.models import ChatMessage
from db.models import Session as SessionModel
from db.models import User as UserModel
from services import check_question_service, profile_service
from services.cost_meter import CapStatus

# ---------------------------------------------------------------------------
# Streaming chunk builders (copied verbatim from test_tutor_stream.py)
# ---------------------------------------------------------------------------

def _content_chunk(token: str) -> SimpleNamespace:
    """A streamed chunk carrying a single text token."""
    delta = SimpleNamespace(content=token, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _tool_fragment(index: int, id=None, name=None, arguments=None) -> SimpleNamespace:
    """A single tool-call delta fragment.

    `name` is assigned AFTER construction because MagicMock(name=...) is
    reserved and would NOT set a real .name attribute. We use SimpleNamespace
    here which has no such restriction, but build the .function with an
    explicit name attr to mirror the real shape.
    """
    fn = SimpleNamespace()
    fn.name = name
    fn.arguments = arguments
    frag = SimpleNamespace()
    frag.index = index
    frag.id = id
    frag.function = fn
    return frag


def _tool_chunk(*fragments) -> SimpleNamespace:
    """A streamed chunk carrying tool-call fragments and no content."""
    delta = SimpleNamespace(content=None, tool_calls=list(fragments))
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _make_stream(*chunks):
    """Return a fresh async-generator instance yielding the given chunks."""
    async def _gen():
        for c in chunks:
            yield c
    return _gen()


def _ctx(db_session, session_id="s1"):
    return ToolContext(
        db=db_session,
        session_id=session_id,
        user_id="u1",
        turn_started_at=datetime.now(timezone.utc),
    )


def _disable_stub(monkeypatch):
    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")


def _allow_cap(monkeypatch):
    cap = CapStatus(
        allowed=True,
        used=Decimal("0.0"),
        soft_breached=False,
        urgent_breached=False,
        soft_cap=Decimal("2.0"),
        urgent_cap=Decimal("2.70"),
        hard_cap=Decimal("3.0"),
    )
    monkeypatch.setattr("agent.tutor.cost_meter.check_cap", MagicMock(return_value=cap))


async def _drain(agen):
    return [ev async for ev in agen]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SESSION_ID = "sc1"
USER_ID = "u1"


def _insert_session(db_session, session_id=SESSION_ID, user_id=USER_ID):
    """Insert a minimal User + Session row so check_question_service can find the row."""
    # SQLite in-memory: ForeignKey enforcement depends on pragma; insert user first.
    user = UserModel(id=user_id)
    db_session.add(user)
    db_session.flush()
    sess = SessionModel(id=session_id, user_id=user_id)
    db_session.add(sess)
    db_session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stream_emits_check_question_and_breaks(monkeypatch, db_session):
    """ask_check_questions dispatch -> check_question event emitted, turn terminates.

    turn1: LLM calls ask_check_questions tool.
    turn2: supplied but must NEVER be consumed (loop terminates after ask).
    """
    _disable_stub(monkeypatch)
    _allow_cap(monkeypatch)

    _insert_session(db_session, session_id=SESSION_ID)
    ctx = _ctx(db_session, session_id=SESSION_ID)

    turn1 = _make_stream(
        _content_chunk("Question: Inputs?"),
        _tool_chunk(
            _tool_fragment(
                index=0,
                id="tc_1",
                name="ask_check_questions",
                arguments=json.dumps(
                    {
                        "session_id": SESSION_ID,
                        "set_index": 1, "set_total": 1, "gap": "linear_algebra",
                        "items": [
                            {
                                "question": "Inputs?",
                                "options": ["vectors", "scalars"],
                                "correct_index": 0,
                                "explanation": "Vectors are inputs.",
                            }
                        ],
                    }
                ),
            )
        ),
    )
    turn2 = _make_stream(_content_chunk("SHOULD-NOT-APPEAR"))

    monkeypatch.setattr(
        "agent.tutor.litellm.acompletion",
        AsyncMock(side_effect=[turn1, turn2]),
    )

    events = await _drain(
        tutor.run_streaming(
            [{"role": "user", "content": "quiz me"}],
            "sys",
            ctx,
        )
    )

    types = [e.type for e in events]

    assert "check_question" in types, f"check_question missing from events: {types}"
    assert "done" in types, f"done missing from events: {types}"

    cq_event = next(e for e in events if e.type == "check_question")
    assert cq_event.data["gap"] == "linear_algebra"
    assert isinstance(cq_event.data["items"], list)
    assert len(cq_event.data["items"]) == 1
    assert cq_event.data["items"][0]["question"] == "Inputs?"
    assert cq_event.data["items"][0]["options"] == ["vectors", "scalars"]
    assert cq_event.data["total"] == 1
    assert "check_result" not in {e.type for e in events}

    # turn must have terminated before turn2 — SHOULD-NOT-APPEAR never streamed
    for e in events:
        text = e.data.get("text", "") if isinstance(e.data, dict) else ""
        assert "SHOULD-NOT-APPEAR" not in text, (
            f"turn2 content leaked into stream: {e}"
        )

    # assistant message must be persisted with status=complete
    msg = (
        db_session.query(ChatMessage)
        .filter(ChatMessage.session_id == SESSION_ID)
        .one()
    )
    assert msg.status == "complete"
    assert msg.role == "assistant"

    pc = check_question_service.get_pending_check(db_session, SESSION_ID)
    assert pc is not None and pc["message_id"] is not None


@pytest.mark.asyncio
async def test_stream_check_question_event_shape(monkeypatch, db_session):
    """check_question event carries gap, items, and total keys."""
    _disable_stub(monkeypatch)
    _allow_cap(monkeypatch)

    sid = "sc2"
    _insert_session(db_session, session_id=sid)
    ctx = _ctx(db_session, session_id=sid)

    turn1 = _make_stream(
        _tool_chunk(
            _tool_fragment(
                index=0,
                id="tc_2",
                name="ask_check_questions",
                arguments=json.dumps(
                    {
                        "session_id": sid,
                        "set_index": 1, "set_total": 1, "gap": "derivatives",
                        "items": [
                            {
                                "question": "What is d/dx x^2?",
                                "options": ["2x", "x^2"],
                                "correct_index": 0,
                                "explanation": "d/dx x^2 = 2x.",
                            }
                        ],
                    }
                ),
            )
        ),
    )

    monkeypatch.setattr(
        "agent.tutor.litellm.acompletion",
        AsyncMock(side_effect=[turn1]),
    )

    events = await _drain(
        tutor.run_streaming(
            [{"role": "user", "content": "test me on derivatives"}],
            "sys",
            ctx,
        )
    )

    cq = next((e for e in events if e.type == "check_question"), None)
    assert cq is not None, "check_question event not emitted"
    assert cq.data["gap"] == "derivatives"
    assert isinstance(cq.data["items"], list)
    assert len(cq.data["items"]) == 1
    assert cq.data["items"][0]["question"] == "What is d/dx x^2?"
    assert cq.data["items"][0]["options"] == ["2x", "x^2"]
    assert cq.data["total"] == 1
    assert "check_result" not in {e.type for e in events}

    done = next((e for e in events if e.type == "done"), None)
    assert done is not None, "done event not emitted"
    assert "message_id" in done.data


@pytest.mark.asyncio
async def test_cancel_mid_text_stream_does_not_raise_name_error(monkeypatch, db_session):
    """Part B: after hoisting 'asked_check = False' before the try: block in
    run_streaming, a plain-text cancel does not raise NameError for asked_check.

    Without the hoist, 'asked_check' is only defined inside the for-loop (inside
    the try:). The except asyncio.CancelledError: block references asked_check,
    which would raise NameError on Python if the cancel fires before any tool
    dispatch iteration.

    This test cancels a text-only streaming turn (no tool calls) at the first
    assistant_delta yield and verifies that:
      (a) a 'cancelled' event is emitted (except branch completed without NameError)
      (b) a ChatMessage with status='cancelled' is persisted

    NOTE on the ask_check_questions + cancel scenario: when a check-ask turn
    completes normally (asked_check=True), the happy path at the 'if asked_check:'
    block calls _persist_assistant_message + attach_message_id BEFORE yielding
    the 'done' event. If CancelledError is thrown at the 'done' yield, the
    except branch's attach_message_id call is redundant (happy path already ran it).
    There is no yield between asked_check=True and the done yield where
    CancelledError could land without the happy path having already attached.
    So the hoist is a correct defensive measure even if its effect is only
    observable via the NameError guard (this test).
    """
    _disable_stub(monkeypatch)
    _allow_cap(monkeypatch)

    sid = "sc_cancel_text"
    _insert_session(db_session, session_id=sid)
    ctx = _ctx(db_session, session_id=sid)

    monkeypatch.setattr(
        "agent.tutor.cost_meter.estimate_cancelled_cost",
        MagicMock(return_value=0),
    )
    monkeypatch.setattr(
        "agent.tutor.cost_meter.record_cost",
        MagicMock(),
    )
    monkeypatch.setattr(
        "agent.tutor.litellm.stream_chunk_builder",
        MagicMock(return_value=SimpleNamespace()),
    )

    # A text-only stream: no tool calls, so asked_check is never set inside the loop.
    stream = _make_stream(
        _content_chunk("partial text"),
        _content_chunk(" more text"),
    )

    monkeypatch.setattr(
        "agent.tutor.litellm.acompletion",
        AsyncMock(side_effect=[stream]),
    )

    agen = tutor.run_streaming(
        [{"role": "user", "content": "tell me something"}],
        "sys",
        ctx,
    )

    # Consume the first assistant_delta; generator is suspended at that yield.
    first_event = await agen.__anext__()
    assert first_event.type == "assistant_delta"

    # Throw CancelledError: lands in the generator at the first yield.
    # With the fix (asked_check hoisted to False before try:), no NameError.
    # Without the fix, NameError: name 'asked_check' is not defined.
    collected = []
    try:
        event = await agen.athrow(asyncio.CancelledError())
        collected.append(event)
    except (asyncio.CancelledError, StopAsyncIteration):
        # Generator re-raised instead of yielding a final event. That is an
        # acceptable outcome: the cancel branch still persisted the cancelled
        # message before re-raising, which the DB assertion below verifies.
        pass

    # If athrow returned an event, it must be the 'cancelled' StreamEvent; if the
    # generator re-raised instead, nothing was collected. Both are valid.
    event_types = [e.type for e in collected]
    assert event_types in ([], ["cancelled"])
    # Either way, the generator must have persisted a cancelled message.
    msgs = db_session.query(ChatMessage).filter(
        ChatMessage.session_id == sid
    ).all()
    assert any(m.status == "cancelled" for m in msgs), (
        "Expected a ChatMessage with status='cancelled' after the cancel branch ran"
    )


@pytest.mark.asyncio
async def test_bundled_profile_patch_dispatched_before_ask(monkeypatch, db_session):
    """F-10: a response bundling update_topic_profile + ask_check_questions in
    one iteration dispatches BOTH -- the patch first, the ask last -- instead
    of dropping the patch. The ask still terminates the turn.
    """
    _disable_stub(monkeypatch)
    _allow_cap(monkeypatch)

    sid = "sc_bundle"
    _insert_session(db_session, session_id=sid)
    ctx = _ctx(db_session, session_id=sid)

    turn1 = _make_stream(
        _tool_chunk(
            _tool_fragment(
                index=0,
                id="tc_patch",
                name="update_topic_profile",
                arguments=json.dumps(
                    {
                        "session_id": sid,
                        "focus_target_gap": "chain rule",
                    }
                ),
            ),
            _tool_fragment(
                index=1,
                id="tc_ask",
                name="ask_check_questions",
                arguments=json.dumps(
                    {
                        "session_id": sid,
                        "set_index": 1, "set_total": 1, "gap": "chain rule",
                        "items": [
                            {
                                "question": "What is d/dx f(g(x))?",
                                "options": ["f'(g(x))g'(x)", "f'(x)g'(x)"],
                                "correct_index": 0,
                                "explanation": "Chain rule.",
                            }
                        ],
                    }
                ),
            ),
        ),
    )

    monkeypatch.setattr(
        "agent.tutor.litellm.acompletion",
        AsyncMock(side_effect=[turn1]),
    )

    events = await _drain(
        tutor.run_streaming(
            [{"role": "user", "content": "quiz me on chain rule"}],
            "sys",
            ctx,
        )
    )

    types = [e.type for e in events]
    assert "check_question" in types, f"check_question missing from events: {types}"
    assert "done" in types, f"done missing from events: {types}"

    # the profile patch was NOT dropped:
    profile = profile_service.load_profile(db_session, sid)
    assert profile.focus_target_gap == "chain rule", (
        "bundled update_topic_profile patch must be dispatched, not dropped"
    )

    # persisted record lists both calls, patch first:
    msg = (
        db_session.query(ChatMessage)
        .filter(ChatMessage.session_id == sid)
        .one()
    )
    names = [tc["name"] for tc in json.loads(msg.tool_calls_json)]
    assert names == ["update_topic_profile", "ask_check_questions"], names


@pytest.mark.asyncio
async def test_second_bundled_ask_is_dropped(monkeypatch, db_session):
    """Only ONE ask_check_questions may run per turn: if the model streams two
    asks in the same response, the first is dispatched and the second is
    dropped (not two check_question events / two registered batches)."""
    _disable_stub(monkeypatch)
    _allow_cap(monkeypatch)

    sid = "sc_double_ask"
    _insert_session(db_session, session_id=sid)
    ctx = _ctx(db_session, session_id=sid)

    item = {
        "question": "Q?",
        "options": ["a", "b"],
        "correct_index": 0,
        "explanation": "because.",
    }

    turn1 = _make_stream(
        _tool_chunk(
            _tool_fragment(
                index=0,
                id="tc_ask1",
                name="ask_check_questions",
                arguments=json.dumps(
                    {"session_id": sid, "set_index": 1, "set_total": 1, "gap": "first_gap", "items": [item]}
                ),
            ),
            _tool_fragment(
                index=1,
                id="tc_ask2",
                name="ask_check_questions",
                arguments=json.dumps(
                    {"session_id": sid, "set_index": 1, "set_total": 1, "gap": "second_gap", "items": [item]}
                ),
            ),
        ),
    )

    monkeypatch.setattr(
        "agent.tutor.litellm.acompletion",
        AsyncMock(side_effect=[turn1]),
    )

    events = await _drain(
        tutor.run_streaming(
            [{"role": "user", "content": "quiz me"}],
            "sys",
            ctx,
        )
    )

    cq_events = [e for e in events if e.type == "check_question"]
    assert len(cq_events) == 1, f"expected exactly one check_question event: {cq_events}"
    assert cq_events[0].data["gap"] == "first_gap"

    # persisted record lists only the first ask -- the second was dropped
    # before dispatch, so only one batch was ever registered.
    msg = (
        db_session.query(ChatMessage)
        .filter(ChatMessage.session_id == sid)
        .one()
    )
    names = [tc["name"] for tc in json.loads(msg.tool_calls_json)]
    assert names == ["ask_check_questions"], names

    pc = check_question_service.get_pending_check(db_session, sid)
    assert pc is not None and pc.get("gap") == "first_gap"

