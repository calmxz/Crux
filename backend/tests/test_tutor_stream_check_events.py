"""TDD: run_streaming emits check_question event and terminates turn on ask_check_questions.

The model is the scripted fake provider (conftest fake_llm) behind the real
adapter.
"""

import asyncio
import json
from datetime import datetime, timezone

import pytest

from agent import tutor
from agent.types import ToolContext
from db.models import ChatMessage
from db.models import Session as SessionModel
from db.models import User as UserModel
from services import check_service, profile_service
from tests.conftest import tool_call


def _ctx(db_session, session_id="s1"):
    return ToolContext(
        db=db_session,
        session_id=session_id,
        user_id="u1",
        turn_started_at=datetime.now(timezone.utc),
    )


async def _drain(agen):
    return [ev async for ev in agen]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SESSION_ID = "sc1"
USER_ID = "u1"


def _insert_session(db_session, session_id=SESSION_ID, user_id=USER_ID):
    """Insert a minimal User + Session row so check_service can find the row."""
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
async def test_stream_emits_check_question_and_breaks(monkeypatch, db_session, fake_llm):
    """ask_check_questions dispatch -> check_question event emitted, turn terminates.

    turn1: LLM calls ask_check_questions tool.
    turn2: supplied but must NEVER be consumed (loop terminates after ask).
    """

    _insert_session(db_session, session_id=SESSION_ID)
    ctx = _ctx(db_session, session_id=SESSION_ID)

    turn1 = [
        "Question: Inputs?",
        tool_call(
            "ask_check_questions",
            id="tc_1",
            args={
                "session_id": SESSION_ID,
                "set_index": 1,
                "set_total": 1,
                "gap": "linear_algebra",
                "items": [
                    {
                        "question": "Inputs?",
                        "options": ["vectors", "scalars"],
                        "correct_index": 0,
                        "explanation": "Vectors are inputs.",
                    }
                ],
            },
        ),
    ]
    turn2 = ["SHOULD-NOT-APPEAR"]

    fake_llm.streams = [turn1, turn2]

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
        assert "SHOULD-NOT-APPEAR" not in text, f"turn2 content leaked into stream: {e}"

    # assistant message must be persisted with status=complete
    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == SESSION_ID).one()
    assert msg.status == "complete"
    assert msg.role == "assistant"

    pc = check_service.open_set(db_session.get(SessionModel, SESSION_ID))
    assert pc is not None and pc["message_id"] is not None


@pytest.mark.asyncio
async def test_stream_check_question_event_shape(monkeypatch, db_session, fake_llm):
    """check_question event carries gap, items, and total keys."""

    sid = "sc2"
    _insert_session(db_session, session_id=sid)
    ctx = _ctx(db_session, session_id=sid)

    turn1 = [
        tool_call(
            "ask_check_questions",
            id="tc_2",
            args={
                "session_id": sid,
                "set_index": 1,
                "set_total": 1,
                "gap": "derivatives",
                "items": [
                    {
                        "question": "What is d/dx x^2?",
                        "options": ["2x", "x^2"],
                        "correct_index": 0,
                        "explanation": "d/dx x^2 = 2x.",
                    }
                ],
            },
        )
    ]

    fake_llm.streams = [turn1]

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
async def test_cancel_mid_text_stream_does_not_raise_name_error(monkeypatch, db_session, fake_llm):
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
    block calls _persist_assistant_message + stamp_message_id BEFORE yielding
    the 'done' event. If CancelledError is thrown at the 'done' yield, the
    except branch's stamp_message_id call is redundant (happy path already ran it).
    There is no yield between asked_check=True and the done yield where
    CancelledError could land without the happy path having already attached.
    So the hoist is a correct defensive measure even if its effect is only
    observable via the NameError guard (this test).
    """

    sid = "sc_cancel_text"
    _insert_session(db_session, session_id=sid)
    ctx = _ctx(db_session, session_id=sid)

    # A text-only stream: no tool calls, so asked_check is never set inside the loop.
    fake_llm.streams = [["partial text", " more text"]]

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
    except asyncio.CancelledError, StopAsyncIteration:
        # Generator re-raised instead of yielding a final event. That is an
        # acceptable outcome: the cancel branch still persisted the cancelled
        # message before re-raising, which the DB assertion below verifies.
        pass

    # If athrow returned an event, it must be the 'cancelled' StreamEvent; if the
    # generator re-raised instead, nothing was collected. Both are valid.
    event_types = [e.type for e in collected]
    assert event_types in ([], ["cancelled"])
    # Either way, the generator must have persisted a cancelled message.
    msgs = db_session.query(ChatMessage).filter(ChatMessage.session_id == sid).all()
    assert any(m.status == "cancelled" for m in msgs), (
        "Expected a ChatMessage with status='cancelled' after the cancel branch ran"
    )


@pytest.mark.asyncio
async def test_bundled_profile_patch_dispatched_before_ask(monkeypatch, db_session, fake_llm):
    """F-10: a response bundling update_topic_profile + ask_check_questions in
    one iteration dispatches BOTH -- the patch first, the ask last -- instead
    of dropping the patch. The ask still terminates the turn.
    """

    sid = "sc_bundle"
    _insert_session(db_session, session_id=sid)
    ctx = _ctx(db_session, session_id=sid)

    turn1 = [
        tool_call(
            "update_topic_profile",
            id="tc_patch",
            args={
                "session_id": sid,
                "focus_target_gap": "chain rule",
            },
        ),
        tool_call(
            "ask_check_questions",
            id="tc_ask",
            args={
                "session_id": sid,
                "set_index": 1,
                "set_total": 1,
                "gap": "chain rule",
                "items": [
                    {
                        "question": "What is d/dx f(g(x))?",
                        "options": ["f'(g(x))g'(x)", "f'(x)g'(x)"],
                        "correct_index": 0,
                        "explanation": "Chain rule.",
                    }
                ],
            },
        ),
    ]

    fake_llm.streams = [turn1]

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
    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == sid).one()
    names = [tc["name"] for tc in json.loads(msg.tool_calls_json)]
    assert names == ["update_topic_profile", "ask_check_questions"], names


@pytest.mark.asyncio
async def test_second_bundled_ask_is_dropped(monkeypatch, db_session, fake_llm):
    """Only ONE ask_check_questions may run per turn: if the model streams two
    asks in the same response, the first is dispatched and the second is
    dropped (not two check_question events / two registered batches)."""

    sid = "sc_double_ask"
    _insert_session(db_session, session_id=sid)
    ctx = _ctx(db_session, session_id=sid)

    item = {
        "question": "Q?",
        "options": ["a", "b"],
        "correct_index": 0,
        "explanation": "because.",
    }

    turn1 = [
        tool_call(
            "ask_check_questions",
            id="tc_ask1",
            args={
                "session_id": sid,
                "set_index": 1,
                "set_total": 1,
                "gap": "first_gap",
                "items": [item],
            },
        ),
        tool_call(
            "ask_check_questions",
            id="tc_ask2",
            args={
                "session_id": sid,
                "set_index": 1,
                "set_total": 1,
                "gap": "second_gap",
                "items": [item],
            },
        ),
    ]

    fake_llm.streams = [turn1]

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
    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == sid).one()
    names = [tc["name"] for tc in json.loads(msg.tool_calls_json)]
    assert names == ["ask_check_questions"], names

    pc = check_service.open_set(db_session.get(SessionModel, sid))
    assert pc is not None and pc.get("gap") == "first_gap"
