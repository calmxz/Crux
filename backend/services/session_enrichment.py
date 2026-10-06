"""Shared per-session enrichment: message count, last activity, latest non-empty
preview, and a lightweight progress signal. Consumed by both the sidebar list
(SessionListItem in routes/sessions.py) and the home shelf (RecentSessionSummary
in services/profile_service.py) so the two payloads stay in lockstep.

Two set-based queries total regardless of how many sessions are passed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from contracts import SessionProgress
from db.models import ChatMessage
from db.models import Session as SessionModel

# Preview window tuning (moved verbatim from routes/sessions.py).
PREVIEW_CANDIDATES = 5
PREVIEW_MAX = 120

_VALID_KNOWLEDGE_LEVELS = {"beginner", "intermediate", "advanced"}


def _valid_level(value: object) -> str | None:
    # A corrupt/legacy profile must not 500 the sessions list -- only pass
    # through a recognized KnowledgeLevel enum value, else None.
    return value if value in _VALID_KNOWLEDGE_LEVELS else None


def aware_utc(dt: datetime | None) -> datetime | None:
    # SQLite drops tzinfo on read even when the column is DateTime(timezone=True).
    # Attach UTC explicitly so Pydantic serializes ISO 8601 with offset; otherwise
    # the frontend's `new Date(iso)` parses the naive string as local time.
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class SessionEnrichment:
    message_count: int
    last_activity_at: datetime | None
    last_message_preview: str | None
    last_session_summary: str | None
    progress: SessionProgress


def compute_enrichment(
    db: Session, rows: list[SessionModel]
) -> dict[str, SessionEnrichment]:
    ids = [r.id for r in rows]
    counts: dict[str, int] = {}
    last_act: dict[str, datetime] = {}
    previews: dict[str, str] = {}
    if ids:
        agg = db.execute(
            select(
                ChatMessage.session_id,
                func.count().label("c"),
                func.max(ChatMessage.created_at).label("la"),
            )
            .where(ChatMessage.session_id.in_(ids))
            .group_by(ChatMessage.session_id)
        ).all()
        for sid, c, la in agg:
            counts[sid] = c
            # func.max() over DateTime returns an ISO string on SQLite (not on
            # Postgres); coerce so aware_utc gets a real datetime either way.
            last_act[sid] = la if not isinstance(la, str) else datetime.fromisoformat(la)
        # Latest NON-EMPTY message per session. Rank by recency in SQL (portable
        # window fn), pick the first non-blank in Python because trim() in SQL
        # strips only spaces (not tabs/newlines) on both SQLite and Postgres.
        rn = func.row_number().over(
            partition_by=ChatMessage.session_id,
            order_by=(ChatMessage.created_at.desc(), ChatMessage.id.desc()),
        ).label("rn")
        sub = (
            select(
                ChatMessage.session_id.label("sid"),
                ChatMessage.content.label("content"),
                rn,
            )
            .where(ChatMessage.session_id.in_(ids))
            .subquery()
        )
        for sid, content in db.execute(
            select(sub.c.sid, sub.c.content)
            .where(sub.c.rn <= PREVIEW_CANDIDATES)
            .order_by(sub.c.sid, sub.c.rn)
        ).all():
            if sid in previews:
                continue  # already took the most-recent non-blank for this session
            stripped = (content or "").strip()
            if stripped:
                previews[sid] = stripped[:PREVIEW_MAX]

    out: dict[str, SessionEnrichment] = {}
    for r in rows:
        try:
            prof = json.loads(r.topic_profile_json or "{}")
        except (ValueError, TypeError):
            prof = {}
        out[r.id] = SessionEnrichment(
            message_count=counts.get(r.id, 0),
            last_activity_at=aware_utc(last_act.get(r.id)),
            last_message_preview=previews.get(r.id),
            last_session_summary=prof.get("last_session_summary"),
            progress=SessionProgress(
                focus_target_gap=prof.get("focus_target_gap"),
                level=_valid_level(prof.get("knowledge_level")),
                mastered_count=len(prof.get("mastered_concepts") or []),
            ),
        )
    return out
