from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from contracts import ReviewQueueItem, ReviewQueuePage
from db.database import get_db
from db.models import LearningEvent
from db.models import Session as SessionModel
from services import profile_service
from services.auth import current_user_id
from services.review_queue_service import (
    REVIEW_WINDOW_DAYS,
    EventRow,
    compute_schedule,
)
from services.session_enrichment import aware_utc

router = APIRouter(prefix="/api")


@router.get("/review/queue", response_model=ReviewQueuePage)
def get_review_queue(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    # F-07: bound the scan. Without this the queue reads every learning event
    # the user has ever produced on each sidebar boot. See
    # review_queue_service.REVIEW_WINDOW_DAYS for why the window is safe.
    window_start = now - timedelta(days=REVIEW_WINDOW_DAYS)
    rows = db.execute(
        select(LearningEvent, SessionModel.topic)
        .join(SessionModel, LearningEvent.session_id == SessionModel.id)
        .where(SessionModel.user_id == user_id)
        .where(LearningEvent.created_at >= window_start)
        .where(
            or_(
                LearningEvent.purpose.is_(None),
                LearningEvent.purpose != "diagnostic",
            )
        )
        .order_by(LearningEvent.created_at.asc(), LearningEvent.id.asc())
    ).all()
    events = [
        EventRow(
            concept=ev.gap_tested,
            correct=ev.correct,
            created_at=aware_utc(ev.created_at),
            session_id=ev.session_id,
            topic=topic,
        )
        for ev, topic in rows
    ]
    evidence_map: dict[str, str | None] = {}
    # One batched fetch instead of a profile load per distinct session; this
    # runs on every sidebar boot, so it must not be O(sessions) round trips.
    sids = {e.session_id for e in events}
    session_rows = (
        db.execute(select(SessionModel).where(SessionModel.id.in_(sids)))
        .scalars()
        .all()
        if sids
        else []
    )
    for row in session_rows:
        prof = profile_service.profile_from_row(row)
        for entry in (prof.mastered_concepts or []) + (prof.confirmed_gaps or []):
            key = profile_service.canon(entry.name)
            # tested wins across sessions; otherwise last writer is fine
            if evidence_map.get(key) != "tested":
                evidence_map[key] = entry.evidence_type
    due = compute_schedule(events, now=now, evidence_map=evidence_map)
    return ReviewQueuePage(
        items=[
            ReviewQueueItem(
                concept=e.concept,
                source_session_id=e.source_session_id,
                source_topic=e.source_topic,
                last_tested_at=e.last_tested_at,
                streak=e.streak,
                due_at=e.due_at,
            )
            for e in due[offset : offset + limit]
        ],
        total=len(due),
        limit=limit,
        offset=offset,
    )
