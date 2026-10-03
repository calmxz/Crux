"""Spec A5 interaction test: focus set in prior turn, cleared same or later turn.

F-02 (restored, decision Q1): clearing focus_target_gap with
focus_clear_reason="tested_correct" requires a correct LearningEvent for the
(canon-equal) focused gap recorded ANYWHERE in this session -- not scoped to
the current turn. record_learning_event is no longer an LLM tool (a human
click writes the event via record_from_answer), so the LLM cannot fabricate
one; only the gap-label match is policed here.

F-23: clearing focus WITHOUT a focus_clear_reason is not treated as a clear at
all -- it succeeds and leaves focus unchanged (indistinguishable from an
omitted field after JSON parsing).
"""

from datetime import datetime, timedelta, timezone

import pytest

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile, UpdateTopicProfileArgs
from db.models import Session as SessionModel
from db.models import User
from services import check_question_service as cq
from services import learning_event_service, profile_service

SESSION_ID = "sess_a5"
USER_ID = "u_a5"


@pytest.fixture
def session_row(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="algorithms",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    return db_session.get(SessionModel, SESSION_ID)


@pytest.fixture
def ctx(db_session):
    return ToolContext(
        db=db_session,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc),
    )


def test_tested_correct_clear_rejected_with_no_event_at_all(session_row, ctx, db_session):
    """F-02 restored: tested_correct is rejected with zero LearningEvents in
    the session at all -- there is nothing to prove the gap was tested.
    """
    profile = profile_service.load_profile(db_session, SESSION_ID)
    profile.focus_target_gap = "atp"
    profile_service.save_profile(db_session, SESSION_ID, profile)

    res = profile_service.apply_patch(
        db_session,
        ctx,
        UpdateTopicProfileArgs(
            session_id=ctx.session_id,
            focus_target_gap=None,
            focus_clear_reason="tested_correct",
            evidence_type="tested",
        ),
    )
    assert res.ok is False
    assert "tested_correct" in (res.error or "")
    assert profile_service.load_profile(db_session, ctx.session_id).focus_target_gap == "atp"


def test_grade_then_clear_focus_tested_correct_same_turn(session_row, ctx, db_session):
    """A5: focus set + question asked in a prior turn; grade + clear focus in grading turn.

    The F-02 guard is session-scoped, not turn-scoped, so the LearningEvent recorded
    in this same turn still satisfies it. This test confirms the full grading-then-clear
    flow remains valid end-to-end.
    """
    # Focus set in a "prior turn" — apply_patch with focus_target_gap="g"
    set_result = profile_service.apply_patch(
        db_session,
        ctx,
        UpdateTopicProfileArgs(
            session_id=ctx.session_id,
            focus_target_gap="g",
            evidence_type=None,
        ),
    )
    assert set_result.ok is True
    assert profile_service.load_profile(db_session, ctx.session_id).focus_target_gap == "g"

    # Question asked in prior turn (asked_at_turn is before turn_started_at)
    prior_ctx = ToolContext(
        db=db_session,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=ctx.turn_started_at - timedelta(seconds=5),
    )
    cq.register(db_session, prior_ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=SESSION_ID,
        gap="g",
        items=[{"question": "q?", "options": ["a", "b"], "correct_index": 0, "explanation": "a."}],
    ))

    # Grading turn: log a correct LearningEvent via human click / record_from_answer
    rec = learning_event_service.record_from_answer(
        db_session,
        ctx.session_id,
        gap="g",
        question="q?",
        correct=True,
    )
    assert rec.correct is True

    # Clear focus with reason "tested_correct" — succeeds without needing the guard
    clr = profile_service.apply_patch(
        db_session,
        ctx,
        UpdateTopicProfileArgs(
            session_id=ctx.session_id,
            focus_target_gap=None,
            focus_clear_reason="tested_correct",
            evidence_type=None,
        ),
    )
    assert clr.ok is True
    assert profile_service.load_profile(db_session, ctx.session_id).focus_target_gap is None


def test_clear_focus_tested_correct_with_divergent_gap_label(session_row, ctx, db_session):
    """F-02 restored: an explicit tested_correct clear is REJECTED when the only
    correct LearningEvent's gap_tested label does not canon-match focus_target_gap.

    The model can pick the check-question `gap` independently of `focus_target_gap`,
    so the two labels can diverge. The guard is a strict canon-equality match (known
    limit), so a divergent label does not prove the FOCUSED gap was tested; the agent
    must use the same gap label for the check-question as the focus it intends to clear.
    Note: in the common case, record_from_answer's own add_exclusive call already
    auto-clears a canon-equal focus on a correct answer -- this test exercises the
    agent's explicit clear call for a gap that does NOT canon-match.
    """
    focus_gap = "electron transport chain"
    check_gap = "electron transport chain location"

    profile_service.apply_patch(
        db_session,
        ctx,
        UpdateTopicProfileArgs(session_id=ctx.session_id, focus_target_gap=focus_gap),
    )
    prior_ctx = ToolContext(
        db=db_session,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=ctx.turn_started_at - timedelta(seconds=5),
    )
    cq.register(db_session, prior_ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=SESSION_ID,
        gap=check_gap,
        items=[{
            "question": "Where does the ETC occur?",
            "options": ["mitochondria", "cytoplasm"],
            "correct_index": 0,
            "explanation": "mitochondria.",
        }],
    ))
    rec = learning_event_service.record_from_answer(
        db_session,
        ctx.session_id,
        gap=check_gap,
        question="Where does the ETC occur?",
        correct=True,
    )
    assert rec.correct is True

    clr = profile_service.apply_patch(
        db_session,
        ctx,
        UpdateTopicProfileArgs(
            session_id=ctx.session_id,
            focus_target_gap=None,
            focus_clear_reason="tested_correct",
        ),
    )
    assert clr.ok is False
    assert "tested_correct" in (clr.error or "")
    assert profile_service.load_profile(db_session, ctx.session_id).focus_target_gap == focus_gap


def test_clear_focus_without_reason_is_not_a_clear(session_row, ctx, db_session):
    """F-23 (restored): a null focus_target_gap WITHOUT focus_clear_reason is
    indistinguishable from an omitted field, so it does not clear focus --
    focus is left unchanged either way. Under F-20, this second call carries
    no actionable field at all, so it is now rejected as an empty patch
    rather than silently succeeding."""
    set_result = profile_service.apply_patch(
        db_session,
        ctx,
        UpdateTopicProfileArgs(
            session_id=ctx.session_id,
            focus_target_gap="some_gap",
            evidence_type=None,
        ),
    )
    assert set_result.ok is True

    clr = profile_service.apply_patch(
        db_session,
        ctx,
        UpdateTopicProfileArgs(
            session_id=ctx.session_id,
            focus_target_gap=None,
            focus_clear_reason=None,
            evidence_type=None,
        ),
    )
    assert clr.ok is False
    assert clr.status == "failed"
    # Focus must remain set -- this was not treated as a clear.
    assert profile_service.load_profile(db_session, ctx.session_id).focus_target_gap == "some_gap"
