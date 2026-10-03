"""Account-level user state (F-46): onboarding + preferences live on the
users row, not per-browser localStorage. A new device hydrates from here."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from contracts import DataExport, MePatchRequest, MeResponse
from db.database import get_db
from db.models import User
from services import object_store
from services.auth import accepted_terms_from_request, current_user_id
from services.export_service import build_export
from services.supabase_admin import AuthAdminError, admin_configured, delete_auth_user
from services.user_service import delete_user_account, ensure_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def _to_response(user) -> MeResponse:
    return MeResponse(
        display_name=user.display_name,
        # NULL = never set on the server; the effective preference is the
        # default the tutor prompt also falls back to.
        feedback_pref=user.feedback_pref or "hints",
        check_ins=user.check_ins,
        reply_length=user.reply_length,
        onboarding_complete=bool(user.onboarding_complete),
    )


@router.get("/me", response_model=MeResponse)
def get_me(
    request: Request,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    # Steady-state GET is a pure read on the render-blocking boot path; only
    # the first-ever call for a user needs the create + COMMIT round trip.
    user = db.get(User, user_id)
    if user is None:
        user = ensure_user(
            db, user_id, accepted_terms=accepted_terms_from_request(request)
        )
        db.commit()
    return _to_response(user)


@router.patch("/me", response_model=MeResponse)
def patch_me(
    req: MePatchRequest,
    request: Request,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    # Codegen drops the openapi `minProperties: 1` constraint (contracts are
    # generated, not hand-tunable) -- enforce the empty-patch rejection here,
    # same pattern as routes/profile.py's patch_profile empty-patch guard.
    if (
        req.display_name is None
        and req.feedback_pref is None
        and req.check_ins is None
        and req.reply_length is None
        and req.onboarding_complete is None
    ):
        raise HTTPException(status_code=422, detail="empty patch")

    user = ensure_user(
        db, user_id, accepted_terms=accepted_terms_from_request(request)
    )
    if req.display_name is not None:
        user.display_name = req.display_name.strip() or None
    if req.feedback_pref is not None:
        user.feedback_pref = req.feedback_pref
    if req.check_ins is not None:
        user.check_ins = req.check_ins
    if req.reply_length is not None:
        user.reply_length = req.reply_length
    if req.onboarding_complete is not None:
        user.onboarding_complete = req.onboarding_complete
    db.commit()
    db.refresh(user)
    return _to_response(user)


@router.get("/me/export", response_model=DataExport)
def export_me(
    response: Response,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    # #361: pure read -- unlike GET /me this never creates the users row; a
    # caller without one gets a null account and empty lists. The filename
    # takes exported_at's UTC day, the same value the frontend names it by.
    export = build_export(db, user_id)
    stamp = export.exported_at.date().isoformat()
    response.headers["Content-Disposition"] = (
        f'attachment; filename="crux-export-{stamp}.json"'
    )
    return export


@router.delete("/me", status_code=204)
def delete_me(
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    # Checked before any row is touched: without the admin key the auth user
    # could not be removed, so a half-deleted account would be left behind.
    if not admin_configured():
        raise HTTPException(status_code=503, detail="auth admin not configured")

    try:
        keys = delete_user_account(db, user_id)
        db.commit()
    except IntegrityError:
        # A child row (streamed reply, chunk embedding) landed between the
        # child deletes and the sessions/users delete. The transaction rolls
        # back whole, so nothing is half-deleted; the learner retries once
        # that work has settled.
        db.rollback()
        raise HTTPException(
            status_code=409, detail="account changed during deletion; try again"
        ) from None

    # Best-effort blob cleanup after commit, same policy as delete_document.
    for key in keys:
        try:
            object_store.get_store().delete(key)
        except Exception:
            logger.warning("could not delete stored object %s during account deletion", key)

    try:
        delete_auth_user(user_id)
    except AuthAdminError:
        # Strip line breaks so the id cannot forge extra log lines (CodeQL).
        safe_id = user_id.replace("\r", "").replace("\n", "")
        logger.error("account %s: app data deleted; auth user removal failed", safe_id)
        raise HTTPException(
            status_code=503, detail="app data deleted; auth user removal failed"
        ) from None
    return Response(status_code=204)
