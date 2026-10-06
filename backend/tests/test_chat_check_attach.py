"""Check-recap persistence and attach-guard tests (streaming chat path).

Originally these covered the non-streaming /chat route's attach_message_id
fix; when that route was deleted they were migrated:

  - end-to-end recap: ask (via /api/chat/stream) -> wrong answer -> complete
    -> GET /sessions confirms selected_index and correct are preserved in
    check_batch (write_check_batch persists the real pick because message_id
    was attached).
  - attach guard: a FAILED ask_check_questions dispatched inside
    run_streaming must NOT repoint an already-open batch's message_id.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent import tutor
from agent.stream_events import StreamEvent
from agent.types import ToolContext
from config import settings
from contracts import AskCheckQuestionsArgs, ToolCallRecord, TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from services import check_question_service
from services.cost_meter import CapStatus

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

USER_ID = "u_chat_check"
SESSION_ID = "s_chat_check"
AUTH_HEADERS = {"Authorization": f"Bearer test-{USER_ID}"}


# ---------------------------------------------------------------------------
# Fixture: seed a user + session
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def seed_session(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="algebra",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()


# ---------------------------------------------------------------------------
# Fake run_streaming that mirrors the real agent's ask turn: registers a
# check batch, persists the assistant message, attaches message_id, yields
# check_question + done.
# ---------------------------------------------------------------------------

ASK_ITEMS = [
    {
        "question": "What is 2+2?",
        "options": ["3", "4"],
        "correct_index": 1,
        "explanation": "2+2=4",
    }
]


def _make_fake_run_streaming_asking():
    async def fake(messages, system_prompt, ctx):
        result = check_question_service.register(
            ctx.db,
            ctx,
            AskCheckQuestionsArgs(
                set_index=1, set_total=1,
                session_id=ctx.session_id, gap="linear_algebra", items=ASK_ITEMS
            ),
        )
        assert result.ok
        tool_call = ToolCallRecord(
            name="ask_check_questions",
            args={"session_id": ctx.session_id, "gap": "linear_algebra", "items": ASK_ITEMS},
            status="ok",
            error=None,
        )
        msg = ChatMessage(
            session_id=ctx.session_id,
            role="assistant",
            content="What is 2+2?",
            status="complete",
            tool_calls_json=json.dumps([tool_call.model_dump()]),
            citations_json="[]",
        )
        ctx.db.add(msg)
        ctx.db.commit()
        check_question_service.attach_message_id(ctx.db, ctx.session_id, msg.id)
        data = result.data or {}
        yield StreamEvent(
            "check_question",
            {"gap": data.get("gap"), "items": data.get("items", []), "total": data.get("total", 0)},
        )
        yield StreamEvent("done", {"message_id": str(msg.id)})

    return fake


# ---------------------------------------------------------------------------
# End-to-end bug regression - wrong pick persisted in check_batch
# ---------------------------------------------------------------------------


def test_chat_check_wrong_pick_persists_in_recap(client, db_session, monkeypatch):
    """Full flow: ask (via /chat/stream) -> answer wrong -> complete ->
    GET /sessions shows selected_index != None and correct=False.

    With message_id attached to the batch, write_check_batch persists the
    real pick instead of the reconstruct_check_batch fallback (which sets
    selected_index=None).
    """
    # 1. Ask a check question via the streaming chat route.
    monkeypatch.setattr("agent.tutor.run_streaming", _make_fake_run_streaming_asking())

    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "quiz me"},
        headers=AUTH_HEADERS,
    ) as resp:
        assert resp.status_code == 200
        for _ in resp.iter_lines():
            pass

    pc_after_ask = check_question_service.get_pending_check(db_session, SESSION_ID)
    assert pc_after_ask is not None
    asking_msg_id = pc_after_ask["message_id"]
    assert asking_msg_id is not None

    # 2. Answer wrong: correct_index=1, we submit selected_index=0.
    answer_resp = client.post(
        f"/api/sessions/{SESSION_ID}/check/answer",
        json={"index": 0, "selected_index": 0},
        headers=AUTH_HEADERS,
    )
    assert answer_resp.status_code == 200
    answer_data = answer_resp.json()
    assert answer_data["correct"] is False

    # 3. Complete the batch (hidden follow-up stream). Patch run_streaming to
    #    avoid real LLM while still exercising write_check_batch.
    async def fake_run_streaming(messages, system_prompt, ctx):
        msg = ChatMessage(session_id=SESSION_ID, role="assistant", content="Better luck!")
        ctx.db.add(msg)
        ctx.db.commit()
        yield StreamEvent("assistant_delta", {"text": "Better luck!"})
        yield StreamEvent("done", {"message_id": str(msg.id)})

    monkeypatch.setattr("agent.tutor.run_streaming", fake_run_streaming)

    complete_resp = client.post(
        f"/api/sessions/{SESSION_ID}/check/complete",
        headers=AUTH_HEADERS,
    )
    assert complete_resp.status_code == 200

    # 4. GET /sessions/{sid} and check the asking message's check_batch.
    session_resp = client.get(
        f"/api/sessions/{SESSION_ID}",
        headers=AUTH_HEADERS,
    )
    assert session_resp.status_code == 200
    messages = session_resp.json()["messages"]

    # Find the asking assistant message by id.
    asking_msg = next((m for m in messages if m["id"] == asking_msg_id), None)
    assert asking_msg is not None, f"asking message {asking_msg_id} not found in session messages"

    check_batch = asking_msg.get("check_batch")
    assert check_batch is not None, (
        "check_batch must be set on the asking message after the batch resolves"
    )
    items = check_batch.get("items", [])
    assert len(items) == 1
    item = items[0]
    assert item["selected_index"] is not None, (
        "selected_index must be persisted (not None) - if None, write_check_batch "
        "no-oped because message_id was never attached"
    )
    assert item["selected_index"] == 0, (
        f"wrong pick (0) must be stored; got {item['selected_index']}"
    )
    assert item["correct"] is False, (
        f"correct must be False for the wrong answer; got {item['correct']}"
    )


# ---------------------------------------------------------------------------
# Attach guard: failed ask must not clobber a prior open batch's message_id
# ---------------------------------------------------------------------------


def _content_chunk(token):
    delta = SimpleNamespace(content=token, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _tool_chunk_ask(call_id):
    fn = SimpleNamespace()
    fn.name = "ask_check_questions"
    fn.arguments = json.dumps(
        {"session_id": SESSION_ID, "gap": "new_gap", "items": ASK_ITEMS}
    )
    frag = SimpleNamespace()
    frag.index = 0
    frag.id = call_id
    frag.function = fn
    delta = SimpleNamespace(content=None, tool_calls=[frag])
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _make_stream(*chunks):
    async def _gen():
        for c in chunks:
            yield c
    return _gen()


@pytest.mark.asyncio
async def test_failed_ask_does_not_clobber_prior_batch_message_id(
    db_session, monkeypatch
):
    """Gate correctness: a FAILED ask_check_questions must NOT attach the
    current message's id to an already-open pending_check.

    run_streaming only sets asked_check (and thereby calls attach_message_id)
    when the ask dispatch result is ok. A second ask while a batch is open
    fails in check_question_service.register, so the prior batch's message_id
    must stay untouched.
    """
    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")
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
    monkeypatch.setattr(
        "agent.tutor.litellm.stream_chunk_builder", MagicMock(return_value=SimpleNamespace())
    )
    monkeypatch.setattr("agent.tutor.litellm.completion_cost", MagicMock(return_value=0.0))

    # 1. Manually register a batch to simulate a prior open batch, stamped
    #    with a known sentinel message_id.
    prior_ctx = ToolContext(
        db=db_session,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc),
    )
    result = check_question_service.register(
        db_session,
        prior_ctx,
        AskCheckQuestionsArgs(
            set_index=1, set_total=1,
            session_id=SESSION_ID,
            gap="prior_gap",
            items=[
                {
                    "question": "Prior Q?",
                    "options": ["a", "b"],
                    "correct_index": 0,
                    "explanation": "a.",
                }
            ],
        ),
    )
    assert result.ok
    check_question_service.attach_message_id(db_session, SESSION_ID, 99999)

    pc_before = check_question_service.get_pending_check(db_session, SESSION_ID)
    assert pc_before["message_id"] == 99999

    # 2. Stream a turn whose ask fails (batch already open), then finishes
    #    with plain text.
    turn1 = _make_stream(_tool_chunk_ask("tc_fail"))
    turn2 = _make_stream(_content_chunk("Please answer the open question first."))
    monkeypatch.setattr(
        "agent.tutor.litellm.acompletion",
        AsyncMock(side_effect=[turn1, turn2]),
    )

    ctx = ToolContext(
        db=db_session,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc),
    )
    events = [
        ev
        async for ev in tutor.run_streaming(
            [{"role": "user", "content": "quiz me again"}], "sys", ctx
        )
    ]

    # The ask dispatch failed and the turn finished normally.
    done_tool = next(e for e in events if e.type == "tool_call_done")
    assert done_tool.data["status"] == "error"
    assert "check_question" not in [e.type for e in events]
    assert events[-1].type == "done"

    # 3. The prior batch's message_id must still be 99999 (not clobbered).
    pc_after = check_question_service.get_pending_check(db_session, SESSION_ID)
    assert pc_after is not None
    assert pc_after["message_id"] == 99999, (
        f"Failed ask must NOT repoint the prior batch's message_id "
        f"(got {pc_after['message_id']!r}, expected 99999). "
        "attach_message_id must only run when the ask dispatch result is ok."
    )
