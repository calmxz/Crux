"""#340: a check is 1..3 sets posed one per turn.

Covers the server-side set rules in check_question_service: the current-check
pointer, set_index / set_total validation, the suppress_check bypass between
sets, the results-summary set line, and the learner-stop path.
"""

import json
from datetime import datetime, timezone

import pytest

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from services import check_question_service as cq
from services import pending_check_store as pcs

SESSION_ID = "sess_sets"
USER_ID = "u_sets"
_T0 = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def db(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(SessionModel(
        id=SESSION_ID, user_id=USER_ID, topic="biology",
        topic_profile_json=TopicProfile(knowledge_level="beginner").model_dump_json(),
    ))
    db_session.commit()
    return db_session


def _ctx(db, suppress: bool = False) -> ToolContext:
    return ToolContext(
        db=db, session_id=SESSION_ID, user_id=USER_ID,
        turn_started_at=_T0, suppress_check=suppress,
    )


def _args(set_index: int, set_total: int, gap: str = "atp", n_items: int = 2):
    return AskCheckQuestionsArgs(
        session_id=SESSION_ID, gap=gap, set_index=set_index, set_total=set_total,
        items=[
            {"question": f"{gap} Q{n}?", "options": ["a", "b"],
             "correct_index": 0, "explanation": "e."}
            for n in range(n_items)
        ],
    )


def _answer_all(db, correct: bool = True):
    pc = cq.get_pending_check(db, SESSION_ID)
    for i in range(len(pc["items"])):
        cq.answer(db, SESSION_ID, i, 0 if correct else 1)


def _run_set(db, set_index, set_total, gap="atp", suppress=False):
    """Register, answer every item, close. The set-2+ registrations run under
    suppress_check, as they do in the real /check/complete follow-up turn."""
    res = cq.register(db, _ctx(db, suppress=suppress), _args(set_index, set_total, gap))
    assert res.ok, res.error
    _answer_all(db)
    return cq.close_set(db, SESSION_ID, cq.get_pending_check(db, SESSION_ID))


def test_valid_three_set_sequence(db):
    _run_set(db, 1, 3, gap="glycolysis")
    assert pcs.get_current_check(db, SESSION_ID) == {
        "set_total": 3, "last_set_index": 1, "gaps": ["glycolysis"],
        "purpose": "check",
    }
    _run_set(db, 2, 3, gap="krebs", suppress=True)
    assert pcs.get_current_check(db, SESSION_ID)["last_set_index"] == 2
    _run_set(db, 3, 3, gap="etc", suppress=True)
    # Final set closed: pointer cleared, nothing pending.
    assert pcs.get_current_check(db, SESSION_ID) is None
    assert cq.get_pending_check(db, SESSION_ID) is None


def test_rejects_mismatched_set_total(db):
    _run_set(db, 1, 3)
    res = cq.register(db, _ctx(db, suppress=True), _args(2, 2))
    assert res.ok is False
    assert "set_total" in res.error
    assert cq.get_pending_check(db, SESSION_ID) is None


def test_rejects_out_of_order_set_index(db):
    _run_set(db, 1, 3)
    res = cq.register(db, _ctx(db, suppress=True), _args(3, 3))
    assert res.ok is False
    assert "set_index" in res.error


def test_rejects_set_index_above_set_total(db):
    res = cq.register(db, _ctx(db), _args(2, 1))
    assert res.ok is False
    assert "set_index" in res.error


def test_rejects_later_set_without_a_current_check(db):
    res = cq.register(db, _ctx(db), _args(2, 3))
    assert res.ok is False
    assert "set_index" in res.error


def test_set_one_starts_a_fresh_check_over_a_stale_pointer(db):
    _run_set(db, 1, 3, gap="old")
    res = cq.register(db, _ctx(db), _args(1, 2, gap="new"))
    assert res.ok
    assert pcs.get_current_check(db, SESSION_ID) == {
        "set_total": 2, "last_set_index": 1, "gaps": ["new"],
        "purpose": "check",
    }


def test_suppress_bypassed_between_sets(db):
    _run_set(db, 1, 2)
    res = cq.register(db, _ctx(db, suppress=True), _args(2, 2))
    assert res.ok, res.error


def test_suppress_still_blocks_after_final_set(db):
    _run_set(db, 1, 1)
    res = cq.register(db, _ctx(db, suppress=True), _args(1, 1))
    assert res.ok is False
    assert res.error == "address the check results before quizzing again"


def test_suppress_still_blocks_a_new_check_between_sets(db):
    """The bypass is only for the NEXT set of the current check."""
    _run_set(db, 1, 3)
    res = cq.register(db, _ctx(db, suppress=True), _args(1, 1))
    assert res.ok is False
    assert res.error == "address the check results before quizzing again"


def test_results_summary_names_the_set(db):
    cq.register(db, _ctx(db), _args(1, 3))
    _answer_all(db)
    summary = cq.build_results_summary(cq.get_pending_check(db, SESSION_ID))
    assert summary.splitlines()[0] == "[check results] gap=atp: 2/2 correct. Set 1 of 3."


def test_results_summary_without_set_fields_is_unchanged():
    pc = {"gap": "g", "items": [{"status": "answered", "correct": True}]}
    assert cq.build_results_summary(pc) == "[check results] gap=g: 1/1 correct."


def test_public_view_exposes_set_position(db):
    cq.register(db, _ctx(db), _args(1, 3))
    view = cq.public_view(cq.get_pending_check(db, SESSION_ID))
    assert (view["set_index"], view["set_total"]) == (1, 3)


def test_reconstruct_check_batch_reads_set_position_from_tool_args(db):
    args = _args(2, 3).model_dump()
    msg = ChatMessage(
        session_id=SESSION_ID, role="assistant", content="Set two:",
        tool_calls_json=json.dumps([{"name": "ask_check_questions", "args": args}]),
    )
    db.add(msg)
    db.commit()
    batch = cq.reconstruct_check_batch(db, msg, events=[])
    assert (batch["set_index"], batch["set_total"]) == (2, 3)


def test_stop_mid_check_grades_remaining_as_skipped_and_reports(db):
    _run_set(db, 1, 3, gap="glycolysis")
    cq.register(db, _ctx(db, suppress=True), _args(2, 3, gap="krebs", n_items=3))
    cq.answer(db, SESSION_ID, 0, 0)

    summary = cq.stop_open_check(db, SESSION_ID)

    lines = summary.splitlines()
    assert lines[0] == (
        "[check results] gap=krebs: 1/1 correct. learner stopped at set 2 of 3."
    )
    assert "  Q2 skipped." in lines and "  Q3 skipped." in lines
    assert cq.get_pending_check(db, SESSION_ID) is None
    assert pcs.get_current_check(db, SESSION_ID) is None
    # Skip semantics: skipped items trigger the cooldown.
    assert cq.get_quiz_cooldown(db, SESSION_ID)["gap"] == "krebs"


def test_stop_between_sets_reports_untested_sets(db):
    _run_set(db, 1, 3, gap="glycolysis")
    summary = cq.stop_open_check(db, SESSION_ID)
    assert summary == "[check results] learner stopped at set 1 of 3."
    assert pcs.get_current_check(db, SESSION_ID) is None


def test_stop_leaves_a_finished_final_set_for_check_complete(db):
    """The last answer is in but /check/complete has not run yet: nothing is
    left to stop, and closing it here would 409 the frontend's complete call."""
    cq.register(db, _ctx(db), _args(1, 1))
    _answer_all(db)
    assert cq.stop_open_check(db, SESSION_ID) is None
    assert cq.is_done(cq.get_pending_check(db, SESSION_ID))


def test_stop_with_no_check_is_a_noop(db):
    assert cq.stop_open_check(db, SESSION_ID) is None


def test_abandon_on_session_end_clears_the_pointer(db):
    _run_set(db, 1, 3)
    cq.register(db, _ctx(db, suppress=True), _args(2, 3))
    assert cq.abandon_open_batch(db, SESSION_ID)
    assert pcs.get_current_check(db, SESSION_ID) is None


# --- diagnostic across sets (#340 follow-up: level graded over every set) ---

from services import diagnostic_service, profile_service  # noqa: E402


@pytest.fixture
def fresh_db(db):
    """Level unknown -> the tutor is running the diagnostic."""
    row = db.get(SessionModel, SESSION_ID)
    row.topic_profile_json = TopicProfile().model_dump_json()
    db.commit()
    return db


def _diag_ctx(db, suppress=False, diagnostic=True):
    ctx = _ctx(db, suppress=suppress)
    ctx.diagnostic_required = diagnostic
    return ctx


def _diag_set(db, set_index, set_total, n_right, n_items=2, gap="g", ctx=None):
    """Register, answer (first n_right correct), grade the way the answer
    route does after each item, then close the way /check/complete does."""
    ctx = ctx or _diag_ctx(db, suppress=set_index > 1)
    assert cq.register(db, ctx, _args(set_index, set_total, gap, n_items)).ok
    for i in range(n_items):
        cq.answer(db, SESSION_ID, i, 0 if i < n_right else 1)
        diagnostic_service.grade_if_diagnostic(db, SESSION_ID)
    pc = cq.get_pending_check(db, SESSION_ID)
    diagnostic_service.grade_if_diagnostic(db, SESSION_ID)
    cq.close_set(db, SESSION_ID, pc)


def _level(db):
    return profile_service.load_profile(db, SESSION_ID).knowledge_level


def test_diagnostic_level_is_graded_over_every_set(fresh_db):
    db = fresh_db
    _diag_set(db, 1, 3, n_right=2, gap="glycolysis")
    assert _level(db) is None  # not graded until the final set
    _diag_set(db, 2, 3, n_right=2, gap="krebs")
    assert _level(db) is None
    _diag_set(db, 3, 3, n_right=0, gap="etc")
    # 4/6 overall -> intermediate (set 1 alone, 2/2, would say advanced).
    assert _level(db) == "intermediate"
    assert pcs.get_current_check(db, SESSION_ID) is None


def test_later_diagnostic_sets_inherit_purpose_and_skip_profile_effects(fresh_db):
    db = fresh_db
    _diag_set(db, 1, 2, n_right=2, gap="glycolysis")
    # The follow-up turn's ctx may not flag the diagnostic; the pointer does.
    ctx = _diag_ctx(db, suppress=True, diagnostic=False)
    assert cq.register(db, ctx, _args(2, 2, "krebs")).ok
    assert cq.get_pending_check(db, SESSION_ID)["purpose"] == "diagnostic"
    cq.answer(db, SESSION_ID, 0, 0)
    assert profile_service.load_profile(db, SESSION_ID).mastered_concepts == []


def test_single_set_diagnostic_grades_on_its_last_answer(fresh_db):
    db = fresh_db
    assert cq.register(db, _diag_ctx(db), _args(1, 1, n_items=3)).ok
    for i in range(3):
        cq.answer(db, SESSION_ID, i, 0)
        diagnostic_service.grade_if_diagnostic(db, SESSION_ID)
    assert _level(db) == "advanced"


def test_stop_between_diagnostic_sets_grades_completed_sets(fresh_db):
    db = fresh_db
    _diag_set(db, 1, 3, n_right=1, gap="glycolysis")
    cq.stop_open_check(db, SESSION_ID)
    assert _level(db) == "beginner"  # 1/2


def test_stop_mid_diagnostic_set_grades_answered_items(fresh_db):
    db = fresh_db
    _diag_set(db, 1, 2, n_right=2, gap="glycolysis")
    assert cq.register(db, _diag_ctx(db, suppress=True), _args(2, 2, "krebs")).ok
    cq.answer(db, SESSION_ID, 0, 0)
    cq.stop_open_check(db, SESSION_ID)
    # 3 right of 4 posed (the skipped item counts in the total) -> intermediate.
    assert _level(db) == "intermediate"


def test_session_end_between_diagnostic_sets_grades_completed_sets(fresh_db):
    db = fresh_db
    _diag_set(db, 1, 3, n_right=2, gap="glycolysis")
    cq.abandon_open_batch(db, SESSION_ID)
    assert _level(db) == "advanced"


def test_all_skipped_diagnostic_stays_ungraded(fresh_db):
    db = fresh_db
    assert cq.register(db, _diag_ctx(db), _args(1, 2)).ok
    cq.stop_open_check(db, SESSION_ID)
    assert _level(db) is None
