"""DELETE /api/documents/{document_id} — remove an uploaded reference file."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from services import documents_service
from services.auth import current_user_id

router = APIRouter(prefix="/api")


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    try:
        documents_service.delete_document(db, document_id=document_id, user_id=user_id)
    except documents_service.DocumentNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="document_not_found"
        ) from None
