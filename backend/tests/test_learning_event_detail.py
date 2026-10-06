"""TDD: learning_events per-answer detail columns (migration 0013).

record_from_answer gains optional selected_index/correct_index/options/purpose
params; the batch answer() path in check_question_service is the sole caller
and must populate them from the same item dict it already grades from.
"""
from datetime import datetime, timezone

import pytest

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import LearningEvent, User
from db.models import Session as SessionModel
from services import check_question_service, learning_event_service

USER_ID = "u_detail_1"
_T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def db(db_session):
    return db_session


@pytest.fixture
def seeded_session_id(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    row = SessionModel(
        id="s_detail_1", user_id=USER_ID, topic="bio",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(row)
    db_session.commit()
    return row.id


@pytest.fixture
def open_batch_session(db_session):
    """Session with knowledge_level already set -> register() tags the batch
    'check' (not diagnostic)."""
    db_session.add(User(id=USER_ID))
    db_session.flush()
    row = SessionModel(
        id="s_detail_open", user_id=USER_ID, topic="bio",
        topic_profile_json=TopicProfile(knowledge_level="intermediate").model_dump_json(),
    )
    db_session.add(row)
    db_session.commit()
    ctx = ToolContext(db=db_session, session_id=row.id, user_id=USER_ID, turn_started_at=_T0)
    check_question_service.register(db_session, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=row.id, gap="atp",
        items=[{"question": "Q1?", "options": ["Prophase", "Metaphase", "Telophase"],
                "correct_index": 0, "explanation": "e1"},
               {"question": "Q2?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "e2"}]))
    return row.id, USER_ID


@pytest.fixture
def diagnostic_batch_session(db_session):
    """Session with knowledge_level None -> register() tags the batch
    'diagnostic'."""
    db_session.add(User(id=USER_ID))
    db_session.flush()
    row = SessionModel(
        id="s_detail_diag", user_id=USER_ID, topic="bio",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(row)
    db_session.commit()
    ctx = ToolContext(db=db_session, session_id=row.id, user_id=USER_ID, turn_started_at=_T0,
                      diagnostic_required=True)
    check_question_service.register(db_session, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=row.id, gap="warmup",
        items=[{"question": "Q1?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "e1"}]))
    return row.id, USER_ID


def test_record_from_answer_persists_detail(db, seeded_session_id):
    ev = learning_event_service.record_from_answer(
        db, seeded_session_id,
        gap="mitosis", question="Which phase?", correct=False,
        selected_index=2, correct_index=0,
        options=["Prophase", "Metaphase", "Telophase"],
        purpose="check",
    )
    row = db.get(LearningEvent, ev.id)
    assert row.selected_index == 2
    assert row.correct_index == 0
    assert '"Metaphase"' in row.options_json
    assert row.purpose == "check"


def test_record_from_answer_detail_defaults_null(db, seeded_session_id):
    ev = learning_event_service.record_from_answer(
        db, seeded_session_id, gap="g", question="q", correct=True,
    )
    row = db.get(LearningEvent, ev.id)
    assert row.selected_index is None and row.options_json is None
    assert row.purpose == "check"


def test_batch_answer_path_populates_detail(db, open_batch_session):
    sid, _user_id = open_batch_session
    pc = check_question_service.get_pending_check(db, sid)
    item = pc["items"][0]
    check_question_service.answer(db, sid, index=0, selected_index=item["correct_index"])
    row = (
        db.query(LearningEvent)
        .filter(LearningEvent.session_id == sid)
        .order_by(LearningEvent.id.desc())
        .first()
    )
    assert row.selected_index == item["correct_index"]
    assert row.correct_index == item["correct_index"]
    assert row.options_json is not None
    assert row.purpose == "check"


def test_batch_answer_path_marks_diagnostic_purpose(db, diagnostic_batch_session):
    sid, _user_id = diagnostic_batch_session
    pc = check_question_service.get_pending_check(db, sid)
    item = pc["items"][0]
    check_question_service.answer(db, sid, index=0, selected_index=item["correct_index"])
    row = (
        db.query(LearningEvent)
        .filter(LearningEvent.session_id == sid)
        .order_by(LearningEvent.id.desc())
        .first()
    )
    assert row.purpose == "diagnostic"
