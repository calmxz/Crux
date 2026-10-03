"""File ingestion background pipeline (Spec §4.2, §3.1).

run(document_id) is invoked by the worker process (services.worker) after it
claims a pending document from the queue. Opens its own SessionLocal because
no request-scoped DB session exists in the worker.

Pipeline:
  1. Load Document, capture its identifiers as plain locals, then close the
     session (F-02) so steps 2-3 hold no pooled DB connection. Load the blob
     via services.object_store (R2 in prod, local disk in dev), not
     settings.uploads_path directly. The Document is re-fetched by id before
     step 4; every failure arm re-fetches by id too, never touching the
     detached instance.
  2. _extract(blob, filename) -> [(page_num | None, text), ...] by extension.
     - .pdf  : pypdf -> [(page_num, text), ...]
     - .pptx : python-pptx -> [(slide_num, text), ...]
     - .txt / .md / .markdown : [(None, full_text)]
  3. lib.chunking.chunk_text (500 / 50 overlap), streaming with
     max_chunks=settings.max_chunks: an oversized document raises
     ChunkLimitExceeded mid-stream and is marked failed without the
     remaining pages ever being tokenised (F-03).
  4. _embed_and_store: per EMBED_BATCH slice (100 chunks) -- cap-check,
     embed (litellm.embedding), insert (pgvector_store.insert_chunks),
     meter (cost_meter.meter_embedding_response), commit. No DB transaction
     is held open during the litellm.embedding HTTP call (F-02/B-02), and
     nothing accumulates for the whole document in memory at once (F-03) --
     a batch's vectors and raw response are discarded as soon as that
     batch's commit lands.
  5. lib.keyword_index.merge_into_session(stems).
  6. Document.status = ready, page_count populated (None for plaintext).

Because embedding/insert/meter now commit per batch, a crash mid-document
leaves a prefix of chunks durably persisted with their spend already on the
ledger -- nothing to re-record on failure. Resume contract: _embed_and_store
looks up chunk_index values already persisted for the document
(_existing_chunk_indexes) and skips them before making any embedding call,
so re-running ingestion for a partially-ingested document never re-pays for
chunks it already bought and stored.

Steps 5-6 still share one transaction with the final batch's own commit
boundary: merge_into_session only flushes, and the closing db.commit() after
step 6 covers it (F-27 applies only to this tail, not to the already-durable
embedding batches). On exception at any step: db.rollback() first (discards
any unflushed/uncommitted work from this run -- committed batches are
unaffected), then status=failed and a fixed error string, committed alone.

C-11: `documents.error` is rendered verbatim by the frontend, so it never
carries exception text (which can embed server paths, blob keys, or provider
payloads). Every value this module writes is one of the constants collected
in INGEST_ERROR_MESSAGES, selected by the pipeline stage that failed; the
original exception goes to the log line only.
"""

import io
import logging
import os

import litellm
from pptx import Presentation
from pypdf import PdfReader
from sqlalchemy import select, update

from config import settings
from db.database import SessionLocal
from db.models import ChunkEmbedding, Document
from db.models import Session as SessionModel
from lib import chunking, keyword_index, llm_retry
from services import cost_meter, object_store, pgvector_store

log = logging.getLogger(__name__)

EMBED_BATCH = 100

# C-11: the complete inventory of strings that may reach `documents.error`.
# The frontend renders this column verbatim (ReferenceStatusBanner.vue,
# SessionView.vue), so each one is human-readable and free of any detail
# derived from an exception, a path, or a provider response.
ERR_EXTRACTION_FAILED = "text extraction failed"
ERR_EMBEDDING_FAILED = "embedding failed"
ERR_INGESTION_FAILED = "ingestion failed"
ERR_CHUNK_LIMIT = "document too large to ingest (chunk limit)"
ERR_COST_CAP = "daily cost cap reached; ingestion stopped"
# Written by routes/upload.py when the blob write fails; listed here so this
# frozenset stays the single inventory for the whole documents.error column.
ERR_STORAGE_WRITE = "storage write failed"

INGEST_ERROR_MESSAGES: frozenset[str] = frozenset(
    {
        ERR_EXTRACTION_FAILED,
        ERR_EMBEDDING_FAILED,
        ERR_INGESTION_FAILED,
        ERR_CHUNK_LIMIT,
        ERR_COST_CAP,
        ERR_STORAGE_WRITE,
    }
)

# Pipeline stage -> persisted message for the generic failure arm.
_STAGE_ERRORS = {
    "extract": ERR_EXTRACTION_FAILED,
    "embed": ERR_EMBEDDING_FAILED,
    "other": ERR_INGESTION_FAILED,
}


def _load_blob(
    store: "object_store.ObjectStore", document_id: int, filename: str
) -> bytes:
    """F-02: takes plain identifiers, not the ORM instance -- run() closes its
    session before calling this, so `doc` is detached and every attribute read
    would emit a refresh SELECT on a session that holds no connection."""
    try:
        return store.get(object_store.key_for(document_id, filename))
    except object_store.ObjectNotFound:
        # Not under the canonical key - try the legacy layout below.
        log.debug("blob miss on canonical key for doc %s; trying legacy key", document_id)
    # Legacy fallback: pre-F-15 uploads were stored under the bare filename.
    # LocalDiskStore path-containment rejects traversal in filename.
    try:
        return store.get(filename)
    except object_store.ObjectNotFound:
        raise RuntimeError(f"uploaded file not found in object store: {filename}") from None


def _extract_pages(blob: bytes) -> list[tuple[int, str]]:
    reader = PdfReader(io.BytesIO(blob))
    return [(i + 1, (page.extract_text() or "")) for i, page in enumerate(reader.pages)]


def _extract_slides(blob: bytes) -> list[tuple[int, str]]:
    prs = Presentation(io.BytesIO(blob))
    out: list[tuple[int, str]] = []
    for i, slide in enumerate(prs.slides, start=1):
        parts: list[str] = []
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                parts.append(shape.text_frame.text)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    parts.append(" ".join(cell.text for cell in row.cells))
        out.append((i, "\n".join(p for p in parts if p)))
    return out


def _extract_plaintext(blob: bytes) -> list[tuple[None, str]]:
    return [(None, blob.decode("utf-8", errors="replace"))]


def _extract(blob: bytes, filename: str) -> list[tuple[int | None, str]]:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return _extract_pages(blob)
    if ext == ".pptx":
        return _extract_slides(blob)
    if ext in (".txt", ".md", ".markdown"):
        return _extract_plaintext(blob)
    raise ValueError(f"unsupported file type: {ext!r}")


def _existing_chunk_indexes(db, document_id: int) -> set[int]:
    """Chunk indexes already persisted for this document (resume skip-set)."""
    return {
        idx
        for (idx,) in db.execute(
            select(ChunkEmbedding.chunk_index).where(
                ChunkEmbedding.document_id == document_id
            )
        )
    }


def _embed_and_store(db, doc, chunks, *, user_id: str | None) -> int:
    """Embed and persist chunks in EMBED_BATCH slices.

    Per slice: cap-check -> embed (no open transaction during the HTTP
    call) -> insert -> meter -> commit. Skips chunk indexes already
    persisted by a previous attempt, so re-runs never re-pay.
    """
    existing = _existing_chunk_indexes(db, doc.id)
    todo = [c for c in chunks if c.chunk_idx not in existing]
    stored = 0
    for i in range(0, len(todo), EMBED_BATCH):
        batch = todo[i : i + EMBED_BATCH]
        if user_id is not None:
            cost_meter.assert_within_caps(db, user_id)
        db.commit()  # release the connection before the network call
        try:
            resp = llm_retry.retry_sync(
                lambda batch=batch: litellm.embedding(
                    model=settings.embedding_model,
                    input=[c.text for c in batch],
                    dimensions=settings.embedding_dim,
                    timeout=settings.embedding_timeout_s,
                )
            )
        except Exception as e:
            raise RuntimeError(f"embedding api failed: {e}") from e
        rows = [
            (
                c.chunk_idx,
                c.page,
                c.text,
                item["embedding"] if isinstance(item, dict) else item.embedding,
            )
            for c, item in zip(batch, resp.data, strict=True)
        ]
        stored += pgvector_store.insert_chunks(
            db, session_id=doc.session_id, document_id=doc.id, rows=rows
        )
        # F-19: ingestion is the largest embedding spender; meter it. The cap
        # gate itself runs at the top of the loop above, before each batch's
        # litellm.embedding call (audit B-01).
        cost_meter.meter_embedding_response(
            db, resp, user_id=user_id, session_id=doc.session_id,
            texts=[c.text for c in batch],
        )
        db.commit()
    return stored


def run(document_id: int) -> None:
    db = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None:
            log.warning("ingestion run: document %s not found", document_id)
            return

        # Hoisted locals: everything the rest of run() needs about the row,
        # captured while the session is still open. The except arms below read
        # these after db.rollback(), which expires ORM instances -- reading
        # doc.session_id there would trigger an implicit refresh SELECT that
        # can itself raise if the original failure was DB/connection-related,
        # skipping the mark-failed commit and stranding the doc in "pending".
        session_id = doc.session_id
        filename = doc.filename
        owner_id: str | None = db.execute(
            select(SessionModel.user_id).where(SessionModel.id == session_id)
        ).scalar_one_or_none()
        log.info(
            "ingestion start document_id=%s session_id=%s filename=%s",
            document_id, session_id, filename,
        )
        # F-02: release the pooled connection for the slow, memory-heavy part
        # (blob load, extraction, chunking). A SQLAlchemy 2.x Session is
        # reusable after close(); the next statement checks out a fresh
        # connection. `doc` is detached from here until the re-fetch below.
        db.close()
        # C-11: which stage is running decides which enumerated message the
        # generic failure arm persists. Tracked here rather than inside the
        # helpers so a raise from anywhere in the call tree is classified.
        stage = "other"
        try:
            blob = _load_blob(object_store.get_store(), document_id, filename)
            stage = "extract"
            pages = _extract(blob, filename)
            stage = "other"
            # F-03: the cap is enforced inside the chunker so an oversized
            # document aborts mid-stream instead of materialising every chunk
            # first and only then failing the count check.
            chunks = chunking.chunk_text(pages, max_chunks=settings.max_chunks)
            # Count only pages/slides that carry a page number; plaintext yields
            # (None, text) so its sum is 0, which we collapse to None (no page
            # concept). Degenerate inputs (0-slide pptx) likewise store None.
            page_count = sum(1 for p, _ in pages if p is not None) or None
            del blob, pages

            doc = db.get(Document, document_id)
            if doc is None:
                log.warning(
                    "ingestion run: document %s vanished during extraction", document_id
                )
                return
            doc.page_count = page_count

            if not chunks:
                doc.status = "ready"
                db.commit()
                return

            # F-05: new chunks move the session's mean embedding, so drop the
            # materialised centroid; the next chat turn recomputes it once.
            # Before _embed_and_store, not after: that loop commits per batch,
            # so a failure part-way through leaves durable new chunks. Nulling
            # first means the worst case is a stale NULL (recomputed on
            # demand) instead of a stale centroid nothing would ever refresh.
            db.execute(
                update(SessionModel)
                .where(SessionModel.id == session_id)
                .values(chunk_centroid=None)
            )
            stage = "embed"
            _embed_and_store(db, doc, chunks, user_id=owner_id)
            stage = "other"

            stems: set[str] = set()
            for c in chunks:
                stems |= keyword_index.build_from_text(c.text)
            if stems:
                keyword_index.merge_into_session(db, session_id, stems)

            log.info(
                "ingestion done document_id=%s session_id=%s chunks=%s",
                document_id, session_id, len(chunks),
            )
            doc.status = "ready"
            doc.error = None
            db.commit()
        except chunking.ChunkLimitExceeded:
            # F-03: raised from inside chunk_text, i.e. in the no-session
            # window, so re-fetch by id rather than touching the detached row.
            db.rollback()
            log.warning(
                "ingestion stopped: chunk cap reached document_id=%s session_id=%s",
                document_id, session_id,
                extra={"doc_id": document_id},
            )
            doc = db.get(Document, document_id)
            if doc is not None:
                doc.status = "failed"
                doc.error = ERR_CHUNK_LIMIT
                db.commit()
            return
        except cost_meter.CostCapExceeded:
            db.rollback()
            log.warning(
                "ingestion stopped: cost cap reached "
                "document_id=%s session_id=%s error=%s",
                document_id, session_id, "cost_cap_exceeded",
                extra={"doc_id": document_id},
            )
            # Per-batch commits mean any batches embedded before the breach
            # are already durable, with their spend already on the ledger --
            # nothing to re-record here.
            doc = db.get(Document, document_id)
            if doc is not None:
                doc.status = "failed"
                doc.error = ERR_COST_CAP
                db.commit()
            return
        except Exception as e:
            db.rollback()
            log.error(
                "ingestion failed document_id=%s session_id=%s stage=%s error=%s",
                document_id, session_id, stage, e,
                extra={"err_type": type(e).__name__, "doc_id": document_id},
                exc_info=settings.env != "prod",
            )
            # Per-batch commits (F-02/F-03/B-02) mean any chunks embedded,
            # inserted, and metered before this failure are already durable
            # on a prior commit -- db.rollback() above only discards this
            # attempt's uncommitted tail (e.g. page_count, keyword merge),
            # never a paid-for batch. No re-record needed.
            doc = db.get(Document, document_id)
            if doc is not None:
                doc.status = "failed"
                # C-11: never str(e) here -- the frontend renders this value.
                doc.error = _STAGE_ERRORS[stage]
                db.commit()
    finally:
        db.close()
