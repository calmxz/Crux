"""Learning event recording + automatic demotion of mastered concepts.

Demotion rule (Spec §3.3, §3.4): if correct=False AND gap_tested is currently
in mastered_concepts, remove it from mastered_concepts.

record_learning_event is no longer an LLM tool; recording happens server-side
via record_from_answer when the learner clicks a check-question answer.
"""

import json
from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from db.models import LearningEvent
from services import profile_service


def record_from_answer(
    db: Session,
    session_id: str,
    *,
    gap: str,
    question: str,
    correct: bool,
    selected_index: int | None = None,
    correct_index: int | None = None,
    options: list[str] | None = None,
    purpose: str = "check",
    apply_profile_effects: bool = True,
) -> LearningEvent:
    """Record a learner's clicked check-question answer (deterministic path).

    Never commits and never touches Check state: it joins the caller's
    transaction (check_service.answer commits once for the whole click).

    No turn-barrier applies here: a human click is not the LLM,
    and record_learning_event is no longer a tool, so the ask-and-self-grade
    exploit the barrier guarded against is impossible.

    Applies the deterministic profile effects, because the click is silent and
    the agent's only next-turn signal is the profile state:
    - correct  -> add gap to mastered_concepts (tested mastery) and remove it
      from confirmed_gaps (exclusivity, F-13); a focus pointing at that gap
      is cleared
    - incorrect-> remove gap from mastered_concepts if present (demotion), and add
      gap to confirmed_gaps if not already present (an incorrect retest is
      confirmed-gap evidence, so the demoted concept is a valid review target)

    apply_profile_effects=False (used by the knowledge diagnostic) still writes
    the LearningEvent but skips the mastered_concepts mutation entirely, so a
    correct diagnostic answer cannot pollute the profile with a fake "tested
    mastery" promotion.
    """
    event = LearningEvent(
        session_id=session_id,
        gap_tested=gap,
        question=question,
        correct=correct,
        selected_index=selected_index,
        correct_index=correct_index,
        options_json=json.dumps(options) if options is not None else None,
        purpose=purpose,
    )
    db.add(event)
    db.flush()

    if apply_profile_effects:
        # Lock before the load-mutate-save span; if the caller
        # (check_service.answer) already holds the lock in this same
        # transaction, the re-lock is a no-op (F-12).
        profile_service.lock_session_row(db, session_id)
        profile = profile_service.load_profile(db, session_id)
        stamp = datetime.now(timezone.utc)
        if correct:
            # F-13 (decision Q2): full promote through the single exclusivity
            # choke point -- removes the gap from confirmed_gaps and clears a
            # canon-equal dangling focus. Reversible: a later wrong retest
            # demotes and re-adds the gap below.
            profile_service.add_exclusive(
                profile,
                "mastered_concepts",
                gap,
                evidence_type="tested",
                stamp=stamp,
            )
        else:
            # Demotion + confirmed-gap evidence via the same choke point.
            profile_service.add_exclusive(
                profile,
                "confirmed_gaps",
                gap,
                evidence_type="tested",
                stamp=stamp,
            )
        profile_service.save_profile(db, session_id, profile, commit=False)
    return event


def gap_accuracy(db: Session, session_id: str) -> dict[str, dict]:
    """Per-gap attempts and correct counts for one session (D1.2).

    Session-scoped by design: cross-session accuracy is R2's review-queue
    concern and will be queried at user level there.
    """
    rows = db.execute(
        select(
            LearningEvent.gap_tested,
            func.count().label("attempts"),
            func.sum(case((LearningEvent.correct, 1), else_=0)).label("correct"),
        )
        .where(LearningEvent.session_id == session_id)
        .group_by(LearningEvent.gap_tested)
    ).all()
    return {
        r.gap_tested: {"attempts": int(r.attempts), "correct": int(r.correct or 0)} for r in rows
    }
