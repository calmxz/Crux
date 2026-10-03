"""pgvector-backed embedding store. Replaces ChromaDB (Phase 7 T4).

Thin wrapper around the `chunk_embeddings` table so tests can monkeypatch
`insert_chunks` / `query_chunks` without standing up a real Postgres.

Cosine-distance search uses pgvector's `<=>` operator via the ORM's
`embedding.cosine_distance(...)` builder. On non-pgvector dialects (e.g.
SQLite in unit tests) the query is never executed because tests patch this
module.
"""

import functools
import logging
from dataclasses import dataclass
from typing import Sequence
from uuid import uuid4

from sqlalchemy import delete as _delete
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from config import settings
from db.models import ChunkEmbedding, Document
from services.sql_dialect import dialect_insert

log = logging.getLogger(__name__)


# Cached so it warns at most once per process if the server rejects the HNSW GUCs.
@functools.cache
def _warn_hnsw_tuning_rejected() -> None:
    log.warning(
        "hnsw search tuning rejected by the server; "
        "falling back to pgvector defaults (needs pgvector >= 0.8)"
    )


@dataclass(frozen=True)
class RetrievedChunk:
    doc_id: int
    chunk_text: str
    page: int | None
    score: float | None
    doc_name: str | None = None


def insert_chunks(
    db: Session,
    session_id: str,
    document_id: int,
    rows: Sequence[tuple[int, int | None, str, list[float]]],
) -> int:
    """Bulk insert chunk embeddings. `rows` is `(chunk_index, page, text, embedding)`.
    Returns the number of rows inserted. Does NOT commit — the caller owns the
    transaction (F-27: ingestion commits chunks, keyword index, and status
    together, atomically).

    Idempotent: `(document_id, chunk_index)` is unique (migration 0023), and
    conflicting rows are skipped via ON CONFLICT DO NOTHING rather than
    raising — a retried ingestion attempt (e.g. after a crash between the
    chunk insert and the status commit) must not fail on rows it already
    wrote."""
    if not rows:
        return 0
    values = [
        {
            "id": str(uuid4()),
            "session_id": session_id,
            "document_id": document_id,
            "chunk_index": chunk_index,
            "page": page,
            "chunk_text": text,
            "embedding": embedding,
        }
        for (chunk_index, page, text, embedding) in rows
    ]
    ins = dialect_insert(db)(ChunkEmbedding).values(values)
    stmt = ins.on_conflict_do_nothing(
        index_elements=["document_id", "chunk_index"]
    ).returning(ChunkEmbedding.id)
    result = db.execute(stmt)
    inserted = len(result.fetchall())
    db.flush()
    return inserted


def delete_document_chunks(db: Session, document_id: int) -> int:
    """Delete all chunk embeddings for a document. Returns rows deleted.
    Does NOT commit — the caller owns the transaction (F-28: chunk delete and
    document-row delete must land atomically). The FK also carries
    ON DELETE CASCADE (migration 0018) as a schema-level backstop."""
    result = db.execute(
        _delete(ChunkEmbedding).where(ChunkEmbedding.document_id == document_id)
    )
    return result.rowcount or 0


def _apply_hnsw_tuning(db: Session) -> None:
    """F-10: widen the HNSW candidate list for the search transaction.

    The search post-filters on `documents.status = 'ready'`, so an HNSW scan
    that returns exactly k candidates can yield fewer than k usable rows.
    `hnsw.ef_search` enlarges the per-scan candidate list, and pgvector 0.8's
    `hnsw.iterative_scan = strict_order` re-scans deeper until k rows survive
    the filter while preserving exact distance ordering (`relaxed_order` would
    return rows slightly out of order).

    Both are `SET LOCAL`, i.e. transaction-scoped, so they must be issued in
    the same transaction as the search, immediately before it. SET cannot take
    bind parameters, so `ef_search` goes through `set_config(name, value,
    is_local=true)` (the bind-safe equivalent of SET LOCAL); int() is the
    validation. The pair runs inside a SAVEPOINT: on a pgvector < 0.8 server
    `iterative_scan` is an unknown GUC and raises, which would otherwise abort
    the whole transaction and take the search down with it.

    The savepoint is taken at Core level (`db.connection().begin_nested()`)
    rather than via `Session.begin_nested()`, which unconditionally flushes
    pending ORM state regardless of autoflush. This session runs with
    autoflush=False by design, and retrieval is invoked mid-turn with
    profile/event rows potentially pending; forcing a flush here would
    surface an unrelated write error as a retrieval failure.
    """
    if db.get_bind().dialect.name != "postgresql":
        return
    ef_search = int(settings.hnsw_ef_search)
    try:
        with db.connection().begin_nested():
            db.execute(
                text("SELECT set_config('hnsw.ef_search', :v, true)"),
                {"v": str(ef_search)},
            )
            db.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))
    except ProgrammingError:
        _warn_hnsw_tuning_rejected()


def query_chunks(
    db: Session,
    session_id: str,
    query_embedding: list[float],
    k: int,
) -> list[RetrievedChunk]:
    """Return top-k chunks for the session, ordered by cosine distance asc."""
    _apply_hnsw_tuning(db)
    distance = ChunkEmbedding.embedding.cosine_distance(query_embedding)
    stmt = (
        select(ChunkEmbedding, distance.label("score"), Document.filename)
        .join(Document, ChunkEmbedding.document_id == Document.id)
        .where(
            ChunkEmbedding.session_id == session_id,
            # F-27: never serve chunks from a doc that is not fully ingested.
            # A failed merge can leave committed chunks on a "failed" doc
            # (pre-F-27 data), and a mid-ingestion doc must not leak partials.
            Document.status == "ready",
        )
        .order_by(distance)
        .limit(k)
    )
    rows = db.execute(stmt).all()
    return [
        RetrievedChunk(
            doc_id=row[0].document_id,
            chunk_text=row[0].chunk_text,
            page=row[0].page,
            score=float(row[1]) if row[1] is not None else None,
            doc_name=row[2],
        )
        for row in rows
    ]
