"""Session-wide document ingestion status (Spec: reference-files design 2026-06-14).

Replaces the per-call-site "latest document" lookups that previously decided
retrieval readiness and `ingestion_status`. Those keyed on the most-recent
document only, so a newer pending/failed upload masked an older ready one.
These helpers aggregate across all of a session's documents instead.
"""

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from db.models import Document
from db.models import Session as SessionModel
from services import object_store, pgvector_store

logger = logging.getLogger(__name__)

IngestionStatus = Literal["pending", "processing", "ready", "failed"]


def aggregate_status(statuses: Iterable[str]) -> IngestionStatus | None:
    """Aggregate a collection of document statuses into one session-wide status.

    Priority: (pending or processing) > ready > failed > None (no documents).
    `processing` (worker has picked up the document but not finished) counts as
    in-flight exactly like `pending`, so the session-wide aggregate stays
    "pending" until every document is ready or failed. Pure helper so the
    route can derive the aggregate from documents it has already fetched, without
    a second query and without duplicating the priority logic.
    """
    seen = set(statuses)
    if not seen:
        return None
    if "pending" in seen or "processing" in seen:
        return "pending"
    if "ready" in seen:
        return "ready"
    return "failed"


def status_from_counts(
    total: int, pending: int, ready: int, processing: int = 0
) -> IngestionStatus | None:
    """Counts-based twin of aggregate_status ((pending or processing) > ready >
    failed > None). Used by the consolidated prepare-path session SELECT."""
    if total == 0:
        return None
    if pending > 0 or processing > 0:
        return "pending"
    if ready > 0:
        return "ready"
    return "failed"


def session_ingestion_status(db: Session, session_id: str) -> IngestionStatus | None:
    """Return aggregate ingestion status across all documents in the session."""
    return aggregate_status(
        db.execute(
            select(Document.status).where(Document.session_id == session_id)
        ).scalars().all()
    )


def has_ready_document(db: Session, session_id: str) -> bool:
    """Return True if at least one document for the session has status 'ready'."""
    return (
        db.execute(
            select(Document.id)
            .where(Document.session_id == session_id, Document.status == "ready")
            .limit(1)
        ).first()
        is not None
    )


def list_document_statuses(db: Session, session_id: str) -> list[Document]:
    """Return all documents for the session ordered by creation time ascending."""
    return db.execute(
        select(Document)
        .where(Document.session_id == session_id)
        .order_by(Document.created_at.asc(), Document.id.asc())
    ).scalars().all()


class DocumentNotFound(Exception):
    """Raised when a document does not exist or is not owned by the caller."""


def delete_document(db: Session, document_id: int, user_id: str) -> None:
    """Delete a document: its chunk embeddings, on-disk file, and DB row.

    Raises DocumentNotFound if the document does not exist or its session is not
    owned by user_id (callers map this to HTTP 404 so existence is not leaked).
    """
    row = db.execute(
        select(Document, SessionModel.user_id)
        .join(SessionModel, Document.session_id == SessionModel.id)
        .where(Document.id == document_id)
    ).first()
    if row is None:
        raise DocumentNotFound(str(document_id))
    doc, owner_id = row
    if owner_id != user_id:
        raise DocumentNotFound(str(document_id))

    # Capture identity before the row is expired by commit.
    doc_id = doc.id
    filename = doc.filename
    session_id = doc.session_id

    # F-28: chunk delete + row delete in ONE transaction, so a crash between
    # them can no longer leave a "ready" doc with zero chunks or orphaned
    # vectors. (Migration 0018 also adds ON DELETE CASCADE as a backstop.)
    pgvector_store.delete_document_chunks(db, document_id)
    db.delete(doc)
    # F-05: the removed chunks were part of the session's mean embedding.
    # Drop the materialised centroid in the same transaction as the delete.
    db.execute(
        update(SessionModel)
        .where(SessionModel.id == session_id)
        .values(chunk_centroid=None)
    )
    db.commit()

    # Best-effort blob cleanup AFTER the DB commit, so an undeletable object
    # (e.g. Windows file lock on LocalDiskStore) cannot 500 the request with
    # the DB rows already gone. Store implementations swallow absent keys;
    # guard everything else.
    try:
        object_store.get_store().delete(object_store.key_for(doc_id, Path(filename).name))
    except Exception:
        logger.warning("could not delete stored object for document %s", doc_id)
