"""Cross-session profile insights: the /api/profile/aggregate dashboard.

G-14: split out of `profile_service`, which had grown two unrelated halves --
the per-session topic-profile patch rules (spec 3.4) and this read-only
cross-user rollup. They share only the stored-profile parser.

Dependency direction is one-way and must stay that way: this module imports
from `profile_service`; `profile_service` must never import this one. There is
deliberately no re-export shim on the old names, so a missed caller fails
loudly at import time instead of silently keeping the old coupling.

Pure SQL + Python. No LLM calls.
"""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from contracts import (
    AggregateConceptCount,
    AggregateProfileResponse,
    ConceptAccuracy,
    KnowledgeLevelDistribution,
    RecentSessionSummary,
    WeeklyMasteryPoint,
)
from db.models import LearningEvent
from db.models import Session as SessionModel
from services.profile_service import _parse_profile
from services.session_enrichment import aware_utc, compute_enrichment

log = logging.getLogger(__name__)


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _learning_insights(
    db: Session, session_ids: list[str], now: datetime
) -> tuple[list[ConceptAccuracy], list[WeeklyMasteryPoint]]:
    """Per-concept accuracy + weekly mastery buckets from learning_events.
    Diagnostic probes excluded (NULL purpose kept). Pure SQL + Python."""
    this_monday = _monday(now.date())
    weeks = [this_monday - timedelta(weeks=i) for i in range(11, -1, -1)]
    week_counts: dict[date, int] = {w: 0 for w in weeks}

    if not session_ids:
        return [], [
            WeeklyMasteryPoint(week_start=w, count=0) for w in weeks
        ]

    rows = db.execute(
        select(LearningEvent)
        .where(LearningEvent.session_id.in_(session_ids))
        .where(
            or_(
                LearningEvent.purpose.is_(None),
                LearningEvent.purpose != "diagnostic",
            )
        )
        .order_by(LearningEvent.created_at.asc(), LearningEvent.id.asc())
    ).scalars().all()

    per: dict[str, dict] = {}
    first_correct: dict[str, datetime] = {}
    for ev in rows:
        entry = per.setdefault(
            ev.gap_tested,
            {"correct": 0, "total": 0, "results": [], "first_session": ev.session_id},
        )
        entry["total"] += 1
        entry["results"].append(ev.correct)
        if ev.correct:
            entry["correct"] += 1
            first_correct.setdefault(ev.gap_tested, aware_utc(ev.created_at))

    for ts in first_correct.values():
        w = _monday(ts.date())
        if w in week_counts:
            week_counts[w] += 1

    concept_accuracy = sorted(
        (
            ConceptAccuracy(
                concept=name,
                correct_count=v["correct"],
                total_count=v["total"],
                accuracy=round(v["correct"] / v["total"], 4),
                last_results=v["results"][-5:],
                first_seen_session_id=v["first_session"],
            )
            for name, v in per.items()
        ),
        key=lambda x: (x.accuracy, x.concept),
    )
    weekly = [WeeklyMasteryPoint(week_start=w, count=week_counts[w]) for w in weeks]
    return concept_accuracy, weekly


def aggregate_for_user(
    db: Session, user_id: str, now: datetime | None = None
) -> AggregateProfileResponse:
    """Cross-session aggregate. Pure SQL + Python, no LLM calls.

    F-08: this scans every session the user owns, so it projects only the
    five columns the aggregate actually reads. Loading whole ORM rows also
    dragged kw_index_json, pending_check_json, quiz_cooldown_json and the
    rolling summary of every session into memory (plus an identity-map entry
    each) for a response that never mentions them.

    The per-row profile parse stays in Python deliberately (plan deviation,
    recorded here on purpose). _parse_profile's failure mode is all-or-
    nothing per row: ConceptEntry and TopicProfile are both extra="forbid"
    and evidence_type is a Literal, so one stale key or one retired
    evidence_type on a single list element fails both validation attempts and
    the ENTIRE row collapses to an empty profile -- contributing no concepts
    and no knowledge_level. A jsonb aggregation in SQL would happily count
    that row's other elements, so the two paths cannot be made equal, and the
    disagreement would land on exactly the legacy rows the tolerant parser
    exists for. Revisit if the aggregate moves to a materialised column or
    the stored profile shape is version-stamped.
    """
    sessions = db.execute(
        select(
            SessionModel.id,
            SessionModel.topic,
            SessionModel.created_at,
            SessionModel.ended_at,
            SessionModel.topic_profile_json,
        )
        .where(SessionModel.user_id == user_id)
        .order_by(SessionModel.created_at.asc())
    ).all()

    total = len(sessions)
    active = sum(1 for s in sessions if s.ended_at is None)
    ended = total - active

    mastered_counts: dict[str, dict] = {}
    gap_counts: dict[str, dict] = {}
    level_dist = {"beginner": 0, "intermediate": 0, "advanced": 0, "unknown": 0}
    last_active_at = None

    for s in sessions:
        profile = _parse_profile(s.topic_profile_json)

        level_key = profile.knowledge_level or "unknown"
        level_dist[level_key] = level_dist.get(level_key, 0) + 1

        for concept in profile.mastered_concepts or []:
            entry = mastered_counts.setdefault(
                concept.name, {"count": 0, "first_seen_session_id": s.id}
            )
            entry["count"] += 1

        for gap in profile.confirmed_gaps or []:
            entry = gap_counts.setdefault(
                gap.name, {"count": 0, "first_seen_session_id": s.id}
            )
            entry["count"] += 1

        candidate = s.ended_at or s.created_at
        if candidate is not None and (
            last_active_at is None or candidate > last_active_at
        ):
            last_active_at = candidate

    def _to_sorted_list(d: dict[str, dict]) -> list[AggregateConceptCount]:
        return sorted(
            (
                AggregateConceptCount(
                    concept=name,
                    count=v["count"],
                    first_seen_session_id=v["first_seen_session_id"],
                )
                for name, v in d.items()
            ),
            key=lambda x: (-x.count, x.concept),
        )

    session_ids = [s.id for s in sessions]

    # Issue #288: a concept must never surface as both mastered and a confirmed
    # gap. Most-recent-event-wins: the newest LearningEvent for the concept
    # across this user's sessions decides. Correct -> mastered only, incorrect
    # -> gap only. No event (or nothing decisive) -> gap only, the conservative
    # reading. One query covers every conflicting concept.
    conflicts = set(mastered_counts) & set(gap_counts)
    if conflicts and session_ids:
        rows = db.execute(
            select(LearningEvent.gap_tested, LearningEvent.correct)
            .where(
                LearningEvent.session_id.in_(session_ids),
                LearningEvent.gap_tested.in_(conflicts),
            )
            .order_by(LearningEvent.created_at.desc(), LearningEvent.id.desc())
        ).all()
        newest: dict[str, bool] = {}
        for name, correct in rows:
            if name not in newest:
                newest[name] = bool(correct)
    else:
        newest = {}
    for name in conflicts:
        if newest.get(name) is True:
            gap_counts.pop(name, None)
        else:
            mastered_counts.pop(name, None)

    concept_accuracy, weekly_mastery = _learning_insights(
        db, session_ids, now or datetime.now(timezone.utc)
    )
    if session_ids:
        total_events = db.execute(
            select(func.count(LearningEvent.id)).where(
                LearningEvent.session_id.in_(session_ids)
            )
        ).scalar_one()
    else:
        total_events = 0

    # `sessions` already ordered by created_at asc; last 5 reversed = newest first.
    recent = list(reversed(sessions[-5:]))
    recent_enr = compute_enrichment(db, recent)
    recent_topics = [
        RecentSessionSummary(
            id=s.id,
            topic=s.topic or "",
            created_at=s.created_at,
            ended_at=s.ended_at,
            last_session_summary=recent_enr[s.id].last_session_summary,
            message_count=recent_enr[s.id].message_count,
            last_activity_at=recent_enr[s.id].last_activity_at,
            last_message_preview=recent_enr[s.id].last_message_preview,
            progress=recent_enr[s.id].progress,
        )
        for s in recent
    ]

    return AggregateProfileResponse(
        total_sessions=total,
        active_sessions=active,
        ended_sessions=ended,
        total_learning_events=int(total_events or 0),
        last_active_at=last_active_at,
        combined_mastered_concepts=_to_sorted_list(mastered_counts),
        combined_confirmed_gaps=_to_sorted_list(gap_counts),
        knowledge_level_distribution=KnowledgeLevelDistribution(**level_dist),
        recent_topics=recent_topics,
        concept_accuracy=concept_accuracy,
        weekly_mastery=weekly_mastery,
    )
