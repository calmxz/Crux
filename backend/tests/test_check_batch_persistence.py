"""Persistence of resolved check batches onto the asking ChatMessage."""

import json as _json
from datetime import datetime, timezone

import pytest

from agent import tutor
from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, LearningEvent, User
from db.models import Session as SessionModel
from services import check_question_service

USER_ID = "u_batch_1"
SID = "s_batch_1"


@pytest.fixture
def seeded(db_session):
    db_session.add(User(id=USER_ID))
    db_session.add(SessionModel(
        id=SID, user_id=USER_ID, topic="bio",
        topic_profile_json=TopicProfile().model_dump_json(),
    ))
    db_session.commit()
    return db_session


def test_check_batch_json_column_roundtrips(seeded):
    db = seeded
    m = ChatMessage(session_id=SID, role="assistant", content="",
                    check_batch_json='{"gap": "atp"}')
    db.add(m)
    db.commit()
    db.refresh(m)
    assert m.check_batch_json == '{"gap": "atp"}'


def _register_batch(db, gap="atp"):
    ctx = ToolContext(db=db, session_id=SID, user_id=USER_ID,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    check_question_service.register(db, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=SID, gap=gap,
        items=[{"question": "Q1?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a is right."}]))


def test_register_pc_has_null_message_id(seeded):
    db = seeded
    _register_batch(db)
    pc = check_question_service.get_pending_check(db, SID)
    assert pc["message_id"] is None


def test_attach_message_id_stamps_open_pc(seeded):
    db = seeded
    _register_batch(db)
    m = ChatMessage(session_id=SID, role="assistant", content="")
    db.add(m)
    db.commit()
    db.refresh(m)
    check_question_service.attach_message_id(db, SID, m.id)
    pc = check_question_service.get_pending_check(db, SID)
    assert pc["message_id"] == m.id


def test_attach_message_id_noop_when_no_pc(seeded):
    db = seeded
    # No open batch - must not raise.
    check_question_service.attach_message_id(db, SID, 999)
    assert check_question_service.get_pending_check(db, SID) is None


def test_write_check_batch_persists_public_view(seeded):
    db = seeded
    _register_batch(db)
    m = ChatMessage(session_id=SID, role="assistant", content="")
    db.add(m)
    db.commit()
    db.refresh(m)
    check_question_service.attach_message_id(db, SID, m.id)
    check_question_service.answer(db, SID, index=0, selected_index=0)
    pc = check_question_service.get_pending_check(db, SID)
    check_question_service.write_check_batch(db, pc)
    db.refresh(m)
    import json
    data = json.loads(m.check_batch_json)
    assert data["gap"] == "atp"
    assert data["items"][0]["selected_index"] == 0
    assert data["items"][0]["correct"] is True


def test_write_check_batch_noop_without_message_id(seeded):
    db = seeded
    _register_batch(db)
    pc = check_question_service.get_pending_check(db, SID)
    # message_id is None - must be a no-op, no raise.
    check_question_service.write_check_batch(db, pc)


def test_reconstruct_from_tool_calls_and_event(seeded):
    db = seeded
    # Asking message with the ask_check_questions tool call, no check_batch_json.
    m = ChatMessage(
        session_id=SID, role="assistant", content="",
        tool_calls_json=_json.dumps([{
            "name": "ask_check_questions",
            "args": {"session_id": SID, "gap": "atp", "items": [
                {"question": "Q1?", "options": ["a", "b"],
                 "correct_index": 0, "explanation": "a is right."}]},
            "status": "ok", "error": None,
        }]),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    # A graded LearningEvent created AFTER the ask.
    db.add(LearningEvent(session_id=SID, gap_tested="atp",
                         question="Q1?", correct=True, selected_index=0))
    db.commit()

    batch = check_question_service.reconstruct_check_batch(db, m)
    assert batch["gap"] == "atp"
    item = batch["items"][0]
    assert item["status"] == "answered"
    assert item["correct"] is True
    # U-03: the learner's pick is recoverable from the LearningEvent; a None
    # here made the recap card claim "Answer not recorded" for graded items.
    assert item["selected_index"] == 0
    assert item["correct_index"] == 0
    assert item["explanation"] == "a is right."


def test_reconstruct_pre_0013_event_without_selected_index(seeded):
    db = seeded
    m = ChatMessage(
        session_id=SID, role="assistant", content="",
        tool_calls_json=_json.dumps([{
            "name": "ask_check_questions",
            "args": {"session_id": SID, "gap": "atp", "items": [
                {"question": "Q1?", "options": ["a", "b"],
                 "correct_index": 0, "explanation": "a is right."}]},
            "status": "ok", "error": None,
        }]),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    # Event predating migration 0013: selected_index was never stored.
    db.add(LearningEvent(session_id=SID, gap_tested="atp",
                         question="Q1?", correct=False))
    db.commit()

    item = check_question_service.reconstruct_check_batch(db, m)["items"][0]
    assert item["status"] == "answered"
    assert item["selected_index"] is None


def test_reconstruct_skipped_when_no_event(seeded):
    db = seeded
    m = ChatMessage(
        session_id=SID, role="assistant", content="",
        tool_calls_json=_json.dumps([{
            "name": "ask_check_questions",
            "args": {"session_id": SID, "gap": "g", "items": [
                {"question": "Qx?", "options": ["a", "b"],
                 "correct_index": 1, "explanation": "b."}]},
            "status": "ok", "error": None,
        }]),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    batch = check_question_service.reconstruct_check_batch(db, m)
    item = batch["items"][0]
    assert item["status"] == "skipped"
    assert item["correct"] is None
    assert item["selected_index"] is None


def test_reconstruct_none_without_ask_tool_call(seeded):
    db = seeded
    m = ChatMessage(session_id=SID, role="assistant", content="hi",
                    tool_calls_json="[]")
    db.add(m)
    db.commit()
    db.refresh(m)
    assert check_question_service.reconstruct_check_batch(db, m) is None


def test_load_check_batch_prefers_column(seeded):
    db = seeded
    m = ChatMessage(session_id=SID, role="assistant", content="",
                    check_batch_json='{"gap": "stored", "items": []}')
    db.add(m)
    db.commit()
    db.refresh(m)
    assert check_question_service.load_check_batch(db, m)["gap"] == "stored"


def test_reconstruct_none_on_malformed_tool_calls_json(seeded):
    db = seeded
    m = ChatMessage(session_id=SID, role="assistant", content="",
                    tool_calls_json="{not json")
    db.add(m)
    db.commit()
    db.refresh(m)
    assert check_question_service.reconstruct_check_batch(db, m) is None


def test_load_check_batch_falls_through_on_malformed(seeded):
    db = seeded
    m = ChatMessage(session_id=SID, role="assistant", content="",
                    check_batch_json="{not json",
                    tool_calls_json="[]")
    db.add(m)
    db.commit()
    db.refresh(m)
    # Malformed column -> None, no ask tool call -> reconstruct returns None.
    assert check_question_service.load_check_batch(db, m) is None


def test_streaming_ask_attaches_message_id(seeded):
    db = seeded
    ctx = ToolContext(db=db, session_id=SID, user_id=USER_ID,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    check_question_service.register(db, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=SID, gap="atp",
        items=[{"question": "Q1?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a."}]))

    msg_id = tutor._persist_assistant_message(ctx, "", "complete")
    check_question_service.attach_message_id(ctx.db, ctx.session_id, msg_id)

    pc = check_question_service.get_pending_check(db, SID)
    assert pc["message_id"] == msg_id
