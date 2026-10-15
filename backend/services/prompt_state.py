"""The tutor prompt state, built in one place (#395).

gather_session_inputs reads what a session contributes to the prompt;
assemble combines it with one turn's inputs into the PromptState that
agent.prompts renders. Every PromptState field is required, so a caller that
forgets one fails at construction instead of rendering a silent default.
"""

import logging
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from agent.excerpt import wrap_chunk
from contracts import TopicProfile
from db.models import Session as SessionModel
from db.models import User
from services import check_service, documents_service, learning_event_service, profile_service

log = logging.getLogger(__name__)


class _NotLoaded:
    def __repr__(self) -> str:
        return "NOT_LOADED"


# Default for the injectable inputs of gather_session_inputs. None cannot play
# this role: an ingestion status of None means the session has no documents.
NOT_LOADED: Final = _NotLoaded()

# #356: the User columns behind LEARNER PREFERENCES. Chat's guard SELECT reads
# them too, so both build the prefs dict with learner_prefs_from.
LEARNER_PREF_COLUMNS = (User.feedback_pref, User.check_ins, User.reply_length)


def learner_prefs_from(values) -> dict[str, Any]:
    """Map LEARNER_PREF_COLUMNS-ordered values to the prefs dict."""
    return {col.key: v for col, v in zip(LEARNER_PREF_COLUMNS, values, strict=True)}


@dataclass(frozen=True)
class SessionPromptInputs:
    """What the session row and its related rows contribute to the prompt."""

    topic: str
    profile: TopicProfile
    ingestion_status: str | None
    learner_prefs: dict[str, Any]
    rolling_summary: str | None
    pending_check: dict | None  # the open Set
    current_check: dict | None  # the Check pointer
    quiz_cooldown: dict | None
    gap_accuracy: dict[str, dict]
    topic_suggest_state: str | None


@dataclass(frozen=True)
class TurnInputs:
    """What this turn's request and retrieval contribute to the prompt."""

    retrieval_required: bool
    review_gaps: bool = False
    review_gap: str | None = None
    diagnostic_accepted: bool = False
    prefetched_chunks: list[dict] | None = None


@dataclass(frozen=True)
class PromptState:
    """Everything agent.prompts.build_dynamic_context renders."""

    topic: str
    profile: TopicProfile
    ingestion_status: str | None
    retrieval_required: bool
    diagnostic_required: bool
    diagnostic_accepted: bool
    seed_mode: str | None
    last_session_summary: str | None
    rolling_summary: str | None
    pending_check: dict | None
    current_check: dict | None
    quiz_cooldown: dict | None
    gap_accuracy: dict[str, dict]
    learner_prefs: dict[str, Any]
    topic_suggest_state: str | None
    review_gaps_target: str | None
    review_gaps_retention: bool
    prefetched_excerpts: list[str]


def gather_session_inputs(
    db: Session,
    session: SessionModel,
    *,
    learner_prefs: dict[str, Any] | _NotLoaded = NOT_LOADED,
    ingestion_status: str | None | _NotLoaded = NOT_LOADED,
    gap_accuracy: dict[str, dict] | _NotLoaded = NOT_LOADED,
) -> SessionPromptInputs:
    """Read the session's prompt inputs. Columns come off `session` (which
    may be detached); only what the caller did not inject is queried."""
    if isinstance(learner_prefs, _NotLoaded):
        row = db.execute(select(*LEARNER_PREF_COLUMNS).where(User.id == session.user_id)).first()
        # A missing user reads all-NULL preferences, rendered as defaults.
        learner_prefs = learner_prefs_from(
            tuple(row) if row is not None else (None,) * len(LEARNER_PREF_COLUMNS)
        )
    if isinstance(ingestion_status, _NotLoaded):
        ingestion_status = documents_service.session_ingestion_status(db, session.id)

    profile = profile_service.profile_from_row(session)

    # D1.2: per-gap accuracy, best-effort. Only run when there is something
    # to enrich (confirmed_gaps non-empty) to keep the no-gaps path inside
    # the P3.1 budget; a failure here must never kill the turn.
    if isinstance(gap_accuracy, _NotLoaded):
        gap_accuracy = {}
        if profile.confirmed_gaps:
            try:
                gap_accuracy = learning_event_service.gap_accuracy(db, session.id)
            except Exception as e:  # noqa: BLE001 - best-effort prompt enrichment
                log.warning("gap_accuracy failed; continuing without it: %s", e)

    return SessionPromptInputs(
        topic=session.topic,
        profile=profile,
        ingestion_status=ingestion_status,
        learner_prefs=learner_prefs,
        rolling_summary=session.rolling_summary,
        pending_check=check_service.open_set(session),
        current_check=check_service.current_check(session),
        quiz_cooldown=check_service.quiz_cooldown(session),
        gap_accuracy=gap_accuracy,
        topic_suggest_state=session.topic_suggest_state,
    )


def assemble(session_inputs: SessionPromptInputs, turn_inputs: TurnInputs) -> PromptState:
    """Combine session and turn inputs into the rendered state. Pure."""
    profile = session_inputs.profile
    diagnostic_required = profile.knowledge_level is None
    diagnostic_accepted = turn_inputs.diagnostic_accepted and diagnostic_required
    review_gaps_target = None
    review_gaps_retention = False
    if turn_inputs.review_gaps:
        gaps = profile_service.concept_names(profile.confirmed_gaps)
        mastered = [
            c for c in profile_service.concept_names(profile.mastered_concepts) if c not in gaps
        ]
        pool = gaps + mastered
        if pool:
            if turn_inputs.review_gap in pool:
                review_gaps_target = turn_inputs.review_gap
            else:
                # Requested review_gap isn't in the pool (e.g. resolved/renamed
                # since the queue was fetched): fall back to the first
                # confirmed gap, deliberately preferring gaps over mastered
                # retention concepts as the substitute target.
                review_gaps_target = gaps[0] if gaps else pool[0]
            review_gaps_retention = review_gaps_target in mastered
            diagnostic_required = False
            diagnostic_accepted = False
    return PromptState(
        topic=session_inputs.topic,
        profile=profile,
        ingestion_status=session_inputs.ingestion_status,
        retrieval_required=turn_inputs.retrieval_required,
        diagnostic_required=diagnostic_required,
        diagnostic_accepted=diagnostic_accepted,
        seed_mode=None,
        last_session_summary=profile.last_session_summary,
        rolling_summary=session_inputs.rolling_summary,
        pending_check=session_inputs.pending_check,
        current_check=session_inputs.current_check,
        quiz_cooldown=session_inputs.quiz_cooldown,
        gap_accuracy=session_inputs.gap_accuracy,
        learner_prefs=session_inputs.learner_prefs,
        # #354: gates the once-per-session topic card.
        topic_suggest_state=session_inputs.topic_suggest_state,
        review_gaps_target=review_gaps_target,
        review_gaps_retention=review_gaps_retention,
        prefetched_excerpts=[wrap_chunk(ch) for ch in turn_inputs.prefetched_chunks or []],
    )
