"""SM-2-lite review scheduler (roadmap R2.1).

Pure functions over learning-event rows: no DB session, no LLM, clock
injected. The route layer maps ORM rows to EventRow so this module stays
free of SQLAlchemy imports.

Interval rule: streak = trailing consecutive correct answers for a concept.
streak == 0 (last answer incorrect) -> due BASE_INTERVAL_DAYS after the last
event; streak >= 1 -> BASE_INTERVAL_DAYS * 2^(streak-1) days, capped at
MAX_INTERVAL_DAYS. A mastered-then-demoted concept re-enters at the reset
interval automatically because the demotion event is an incorrect answer
(roadmap R2.1 AC3).

Concept identity: gap_tested strings are free-text and exact-match across
sessions, so grouping uses a strip().casefold() key; the displayed concept
string and source session come from the group's most recent event.

Ordering: weakest-evidence concepts surface first (roadmap R4.2 AC2). An
optional evidence_map (casefolded concept name -> evidence_type) is joined
in by the route from the caller's profile(s); concepts with "tested"
evidence sort after everything else, and within each evidence tier the
most overdue concept comes first. No map -> pure due_at order.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

BASE_INTERVAL_DAYS = 1
MAX_INTERVAL_DAYS = 60

# F-07: the route loads every in-window event and computes the schedule in
# Python, because `streak` needs the full trailing run of answers per concept
# -- a "latest event per concept" query cannot produce it. Bounding the scan
# to a window keeps that load O(recent activity) instead of O(lifetime
# events). A concept with no event in the window has fallen off the schedule:
# it is neither due nor counted. The window must be at least
# MAX_INTERVAL_DAYS, or a concept scheduled at the cap would be dropped
# before it ever came due.
REVIEW_WINDOW_DAYS = 90

assert REVIEW_WINDOW_DAYS >= MAX_INTERVAL_DAYS, (
    "REVIEW_WINDOW_DAYS must cover the longest scheduling interval"
)


@dataclass(frozen=True)
class EventRow:
    concept: str
    correct: bool
    created_at: datetime  # timezone-aware UTC
    session_id: str
    topic: str


@dataclass(frozen=True)
class ScheduleEntry:
    concept: str
    source_session_id: str
    source_topic: str
    last_tested_at: datetime
    streak: int
    due_at: datetime


def _interval_days(streak: int) -> int:
    if streak <= 0:
        return BASE_INTERVAL_DAYS
    return min(BASE_INTERVAL_DAYS * 2 ** (streak - 1), MAX_INTERVAL_DAYS)


def compute_schedule(
    events: Sequence[EventRow],
    now: datetime,
    evidence_map: dict[str, str | None] | None = None,
) -> list[ScheduleEntry]:
    """Return concepts due for review at `now`. Sorted weakest-evidence first
    (non-"tested" before "tested" per evidence_map, keys casefolded concept
    names), then most overdue first. No map -> pure due_at order."""
    groups: dict[str, list[EventRow]] = {}
    for ev in events:
        key = ev.concept.strip().casefold()
        if not key:
            continue
        groups.setdefault(key, []).append(ev)

    due: list[ScheduleEntry] = []
    for group in groups.values():
        ordered = sorted(group, key=lambda e: e.created_at)
        streak = 0
        for ev in reversed(ordered):
            if not ev.correct:
                break
            streak += 1
        last = ordered[-1]
        due_at = last.created_at + timedelta(days=_interval_days(streak))
        if due_at <= now:
            due.append(
                ScheduleEntry(
                    concept=last.concept,
                    source_session_id=last.session_id,
                    source_topic=last.topic,
                    last_tested_at=last.created_at,
                    streak=streak,
                    due_at=due_at,
                )
            )
    emap = evidence_map or {}

    def _rank(entry: ScheduleEntry) -> int:
        return 1 if emap.get(entry.concept.strip().casefold()) == "tested" else 0

    due.sort(key=lambda e: (_rank(e), e.due_at))
    return due
