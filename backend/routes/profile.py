from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from contracts import (
    AggregateProfileResponse,
    LearningEventResponse,
    ProfileMutationResponse,
    ProfilePatchRequest,
    ProfileResponse,
)
from db.database import get_db
from db.models import LearningEvent
from db.models import Session as SessionModel
from services import profile_insights, profile_service
from services.auth import current_user_id

router = APIRouter(prefix="/api")


@router.get("/profile/aggregate", response_model=AggregateProfileResponse)
def get_aggregate_profile(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    return profile_insights.aggregate_for_user(db, user_id)


@router.get("/profile/{session_id}", response_model=ProfileResponse)
def get_profile(
    session_id: str,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    row = db.get(SessionModel, session_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=404, detail="session not found")

    profile = profile_service.load_profile(db, session_id)
    rows = db.execute(
        select(LearningEvent)
        .where(LearningEvent.session_id == session_id)
        .order_by(LearningEvent.id.desc())
        .limit(20)
    ).scalars().all()
    events = [
        LearningEventResponse(
            id=r.id,
            session_id=r.session_id,
            gap_tested=r.gap_tested,
            question=r.question,
            correct=r.correct,
            created_at=r.created_at,
            selected_index=r.selected_index,
            correct_index=r.correct_index,
            purpose=r.purpose,
        )
        for r in rows
    ]
    return ProfileResponse(
        profile=profile,
        recent_learning_events=events,
        etag=profile_service.profile_etag(profile),
    )


def _owned_session_or_404(db, session_id, user_id):
    row = db.get(SessionModel, session_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=404, detail="session not found")
    return row


def _guard_if_match(db, session_id, if_match):
    if if_match is None:
        raise HTTPException(status_code=428, detail="If-Match header required")
    current = profile_service.profile_etag(profile_service.load_profile(db, session_id))
    if if_match != current:
        raise HTTPException(status_code=412, detail="profile changed; refetch")


@router.patch("/profile/{session_id}", response_model=ProfileMutationResponse)
def patch_profile(
    session_id: str,
    body: ProfilePatchRequest,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    _owned_session_or_404(db, session_id, user_id)
    if (
        body.add_mastered is None
        and body.add_gap is None
        and body.knowledge_level is None
        and body.subtopic is None
        and body.subtopic_level is None
    ):
        raise HTTPException(status_code=422, detail="empty patch")
    # F-12: lock before the If-Match read so compare and write are one atomic span.
    profile_service.lock_session_row(db, session_id)
    _guard_if_match(db, session_id, if_match)
    try:
        profile = profile_service.apply_user_patch(
            db,
            session_id,
            add_mastered=body.add_mastered,
            add_gap=body.add_gap,
            knowledge_level=body.knowledge_level,
            subtopic=body.subtopic,
            subtopic_level=body.subtopic_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return ProfileMutationResponse(profile=profile, etag=profile_service.profile_etag(profile))


def _delete_item(db, session_id, user_id, list_name, item, if_match):
    _owned_session_or_404(db, session_id, user_id)
    # F-12: lock before the If-Match read so compare and write are one atomic span.
    profile_service.lock_session_row(db, session_id)
    _guard_if_match(db, session_id, if_match)
    try:
        profile = profile_service.remove_profile_item(db, session_id, list_name, item)
    except KeyError:
        raise HTTPException(status_code=404, detail="item not found") from None
    return ProfileMutationResponse(profile=profile, etag=profile_service.profile_etag(profile))


@router.delete("/profile/{session_id}/mastered_concepts/{item}", response_model=ProfileMutationResponse)
def delete_mastered(
    session_id: str,
    item: str,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    return _delete_item(db, session_id, user_id, "mastered_concepts", item, if_match)


@router.delete("/profile/{session_id}/confirmed_gaps/{item}", response_model=ProfileMutationResponse)
def delete_gap(
    session_id: str,
    item: str,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    return _delete_item(db, session_id, user_id, "confirmed_gaps", item, if_match)


@router.delete(
    "/profile/{session_id}/subtopic_levels/{item}",
    response_model=ProfileMutationResponse,
)
def delete_subtopic_level(
    session_id: str,
    item: str,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    _owned_session_or_404(db, session_id, user_id)
    # F-12: lock before the If-Match read so compare and write are one atomic span.
    profile_service.lock_session_row(db, session_id)
    _guard_if_match(db, session_id, if_match)
    try:
        profile = profile_service.remove_subtopic(db, session_id, item)
    except KeyError:
        raise HTTPException(status_code=404, detail="item not found") from None
    return ProfileMutationResponse(
        profile=profile, etag=profile_service.profile_etag(profile)
    )
