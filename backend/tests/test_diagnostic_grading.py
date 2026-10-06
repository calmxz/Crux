"""TDD: score->level assignment on diagnostic batch completion."""

from datetime import datetime, timezone

import pytest

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import Session as SessionModel
from db.models import User
from services import check_question_service, diagnostic_service, profile_service
from services.diagnostic_service import level_for_score

# Default auth identity from conftest's _fake_current_user_id when no
# Authorization header (and no user_id in the request body) is sent.
USER_ID = "test-user"

_T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def db(db_session):
    return db_session


@pytest.mark.parametrize(
    "n,expected", [(0, "beginner"), (1, "beginner"), (2, "intermediate"), (3, "advanced")]
)
def test_level_for_score_3q(n, expected):
    assert level_for_score(n, 3) == expected


@pytest.fixture
def fresh_session_with_diagnostic_batch(db_session):
    """Session with knowledge_level None -> register() tags the batch
    'diagnostic'. Returns (session_id, correct_indices) so a test can answer
    every item correctly."""
    db_session.add(User(id=USER_ID))
    db_session.flush()
    row = SessionModel(
        id="s_diag_1",
        user_id=USER_ID,
        topic="biology",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(row)
    db_session.commit()

    ctx = ToolContext(
        db=db_session, session_id=row.id, user_id=USER_ID, turn_started_at=_T0,
        diagnostic_required=True,
    )
    correct_indices = [0, 1, 0]
    check_question_service.register(
        db_session,
        ctx,
        AskCheckQuestionsArgs(
            set_index=1, set_total=1,
            session_id=row.id,
            gap="warmup",
            items=[
                {
                    "question": "Q1?",
                    "options": ["a", "b"],
                    "correct_index": correct_indices[0],
                    "explanation": "e1",
                },
                {
                    "question": "Q2?",
                    "options": ["a", "b"],
                    "correct_index": correct_indices[1],
                    "explanation": "e2",
                },
                {
                    "question": "Q3?",
                    "options": ["a", "b"],
                    "correct_index": correct_indices[2],
                    "explanation": "e3",
                },
            ],
        ),
    )
    return row.id, correct_indices


@pytest.fixture
def session_with_level_and_check_batch(db_session):
    """Session with knowledge_level already set -> register() tags the batch
    'check' (not diagnostic). Returns session_id."""
    db_session.add(User(id=USER_ID))
    db_session.flush()
    row = SessionModel(
        id="s_check_1",
        user_id=USER_ID,
        topic="biology",
        topic_profile_json=TopicProfile(knowledge_level="intermediate").model_dump_json(),
    )
    db_session.add(row)
    db_session.commit()

    ctx = ToolContext(
        db=db_session, session_id=row.id, user_id=USER_ID, turn_started_at=_T0
    )
    check_question_service.register(
        db_session,
        ctx,
        AskCheckQuestionsArgs(
            set_index=1, set_total=1,
            session_id=row.id,
            gap="atp",
            items=[
                {
                    "question": "Q1?",
                    "options": ["a", "b"],
                    "correct_index": 0,
                    "explanation": "e1",
                },
            ],
        ),
    )
    return row.id


@pytest.fixture
def session_with_diagnostic_batch(fresh_session_with_diagnostic_batch):
    """Alias returning just the session id (drops the correct_indices half of
    the tuple) for tests that read correct_index off the persisted items
    themselves via _correct_choice below."""
    sid, _correct_indices = fresh_session_with_diagnostic_batch
    return sid


def _correct_choice(db, session_id, index):
    pc = check_question_service.get_pending_check(db, session_id)
    return pc["items"][index]["correct_index"]


def _wrong_choice(db, session_id, index):
    pc = check_question_service.get_pending_check(db, session_id)
    item = pc["items"][index]
    for i in range(len(item["options"])):
        if i != item["correct_index"]:
            return i
    raise AssertionError("item has no wrong option to choose")


def test_all_skip_diagnostic_leaves_level_none(db, session_with_diagnostic_batch):
    sid = session_with_diagnostic_batch
    for i in range(3):
        check_question_service.skip(db, sid, i)
    diagnostic_service.grade_if_diagnostic(db, sid)
    assert profile_service.load_profile(db, sid).knowledge_level is None


def test_user_set_level_not_clobbered_by_diagnostic(db, session_with_diagnostic_batch):
    # Items 1 and 2 are answered WRONG so the diagnostic-computed score
    # (1/3 correct -> "beginner") diverges from the user's explicit
    # mid-batch PATCH ("advanced") -- a genuine clobber scenario, not a
    # same-value coincidence.
    sid = session_with_diagnostic_batch
    check_question_service.answer(db, sid, 0, _correct_choice(db, sid, 0))
    profile_service.apply_user_patch(db, sid, knowledge_level="advanced")
    check_question_service.answer(db, sid, 1, _wrong_choice(db, sid, 1))
    check_question_service.answer(db, sid, 2, _wrong_choice(db, sid, 2))
    diagnostic_service.grade_if_diagnostic(db, sid)
    assert profile_service.load_profile(db, sid).knowledge_level == "advanced"


def test_answer_check_sets_level_on_diagnostic_completion(
    client, db, fresh_session_with_diagnostic_batch
):
    sid, correct_indices = fresh_session_with_diagnostic_batch  # 3-item diagnostic batch, all correct
    for i, ci in enumerate(correct_indices):
        r = client.post(f"/api/sessions/{sid}/check/answer", json={"index": i, "selected_index": ci})
        assert r.status_code == 200
    assert profile_service.load_profile(db, sid).knowledge_level == "advanced"


def test_answer_check_normal_check_leaves_level(client, db, session_with_level_and_check_batch):
    sid = session_with_level_and_check_batch  # knowledge_level already "intermediate"
    client.post(f"/api/sessions/{sid}/check/answer", json={"index": 0, "selected_index": 0})
    assert profile_service.load_profile(db, sid).knowledge_level == "intermediate"


def test_skip_check_sets_level_when_final_item_resolved_via_skip(
    client, db, fresh_session_with_diagnostic_batch
):
    """Regression: the diagnostic batch's FINAL item is resolved via the SKIP
    route (not answer). Grading must still fire so knowledge_level gets set -
    otherwise the tutor re-issues the diagnostic forever (bug found in final
    whole-branch review)."""
    sid, correct_indices = fresh_session_with_diagnostic_batch  # 3-item diagnostic batch
    # Answer items 0 and 1 correctly, then SKIP the final item (index 2).
    r0 = client.post(f"/api/sessions/{sid}/check/answer", json={"index": 0, "selected_index": correct_indices[0]})
    assert r0.status_code == 200
    r1 = client.post(f"/api/sessions/{sid}/check/answer", json={"index": 1, "selected_index": correct_indices[1]})
    assert r1.status_code == 200
    r2 = client.post(f"/api/sessions/{sid}/check/skip", json={"index": 2})
    assert r2.status_code == 200
    assert r2.json()["done"] is True

    # 2 answered-correct out of 3 items -> ratio 2/3 -> "intermediate" per
    # level_for_score. The key assertion is that it is set at all (not None).
    level = profile_service.load_profile(db, sid).knowledge_level
    assert level is not None
    assert level == "intermediate"
