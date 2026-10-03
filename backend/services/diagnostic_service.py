"""Deterministic knowledge-level assignment from a diagnostic check batch."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def grade_if_diagnostic(
    db: "Session", session_id: str, force: bool = False, commit: bool = True
) -> None:
    """Grade a diagnostic check into topic_profile.knowledge_level.

    A diagnostic check may run 1..3 sets (#340); the level is graded ONCE
    over every item of every set: the closed sets' running score kept on the
    current-check pointer plus the open set. By default that happens only
    when the open set is the final one and fully resolved (is_done). force=True
    (learner stop, session end) grades whatever was answered so far, with or
    without an open set.

    Safe to call from any route that may resolve an item (answer or skip) -
    re-grading is a no-op because knowledge_level is only ever written from
    None (see the guard below), never overwritten once set.

    Reads the batch through the leaf pending_check_store, never
    check_question_service: check_question_service.stop_open_check calls this
    function, so importing it back would form an import cycle (CodeQL
    cyclic-import).
    """
    from services import pending_check_store, profile_service

    pc = pending_check_store.get_pending_check(db, session_id)
    cc = pending_check_store.get_current_check(db, session_id)
    prior = cc.get("diag") if cc and cc.get("purpose") == "diagnostic" else None
    if pc is not None:
        if pc.get("purpose") != "diagnostic" or not pending_check_store.is_done(pc):
            return
        if not (force or pending_check_store.is_final_set(pc)):
            return
        tally = pending_check_store.diagnostic_tally(pc, prior)
    elif force and prior is not None:
        tally = prior
    else:
        return
    if not tally["answered"]:
        # F-25: an all-skip check is zero evidence. Leave knowledge_level None
        # so diagnostic_required fires again next turn instead of branding the
        # learner "beginner" forever.
        return
    level = level_for_score(tally["correct"], tally["items"])
    profile_service.lock_session_row(db, session_id)
    profile = profile_service.load_profile(db, session_id)
    if profile.knowledge_level is not None:
        # F-39: a user PATCH mid-batch already set the level; the diagnostic
        # must not clobber explicit user intent. This also makes re-grading
        # a resolved batch a no-op.
        return
    profile.knowledge_level = level
    profile_service.save_profile(db, session_id, profile, commit=commit)


def level_for_score(n_correct: int, total: int) -> str:
    """Map a diagnostic score to a coarse knowledge level.

    Tuned for a 3-question set: 0-1 beginner, 2 intermediate, 3 advanced.
    Generalizes by ratio for other totals (a multi-set diagnostic grades over
    all its items)."""
    if total <= 0:
        return "beginner"
    ratio = n_correct / total
    if ratio >= 1.0:
        return "advanced"
    if ratio >= (2 / 3):
        return "intermediate"
    return "beginner"
