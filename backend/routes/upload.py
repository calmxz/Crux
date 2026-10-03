import hashlib
import io
import logging
import re
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from pptx import Presentation
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import settings
from contracts import UploadResponse, UploadStatus
from db.database import get_db
from db.models import Document
from db.models import Session as SessionModel
from lib.error_codes import CHUNK_LIMIT_EXCEEDED, DAILY_CAP_REACHED, PAGE_LIMIT_EXCEEDED
from services import cost_meter, object_store, rate_limit, velocity_limit
from services.auth import current_user_id

router = APIRouter(prefix="/api")

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".txt", ".md", ".markdown"}

# F-03: measured plaintext ratios (audit 2026-08-06, live tiktoken run)
_CHARS_PER_TOKEN = 6.38
_CHUNK_STRIDE_TOKENS = 450
_PLAINTEXT_EXTENSIONS = {".txt", ".md", ".markdown"}

# F-55: content sniff for container formats. Extensions with no reliable
# magic bytes (.txt, .md) are exempt -- the extension check already ran.
_MAGIC_BYTES = {
    ".pdf": (b"%PDF",),
    ".pptx": (b"PK\x03\x04",),
}

log = logging.getLogger(__name__)

READ_CHUNK = 1024 * 1024  # 1 MiB



def _page_count(ext: str, data: bytes) -> int | None:
    """Pages in a PDF / slides in a PPTX, or None when it cannot be determined.

    Uses the same libraries as services.ingestion_service._extract_pages /
    _extract_slides. Unparseable files return None and are let through:
    ingestion already reports extraction failures on the document row, and a
    parser disagreement must not turn into a confusing 413.
    """
    try:
        if ext == ".pdf":
            return len(PdfReader(io.BytesIO(data), strict=False).pages)
        if ext == ".pptx":
            return len(Presentation(io.BytesIO(data)).slides)
    except Exception:
        log.info("page-count probe failed for %s upload; skipping the gate", ext)
    return None


def _find_existing_document(db: Session, session_id: str, sha: str) -> Document | None:
    """C-08: the live row (if any) holding these exact bytes for this session.

    Mirrors the partial unique index `uq_documents_session_sha`: failed rows
    are excluded so a retry after a failed ingest always creates a fresh row.
    """
    return db.execute(
        select(Document)
        .where(
            Document.session_id == session_id,
            Document.content_sha256 == sha,
            Document.status != "failed",
        )
        .order_by(Document.id)
        .limit(1)
    ).scalar_one_or_none()


def _read_bounded(fh, max_bytes: int) -> bytes:
    """Read fh incrementally, aborting with 413 as soon as the running total
    exceeds max_bytes (F-40: the Content-Length header is client-controlled,
    so the pre-gate above is advisory only)."""
    data = bytearray()
    while True:
        chunk = fh.read(READ_CHUNK)
        if not chunk:
            return bytes(data)
        data.extend(chunk)
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail={"code": "FILE_TOO_LARGE", "max_bytes": max_bytes},
            )


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(velocity_limit.enforce_velocity)],
)
def upload_file(
    request: Request,
    response: Response,
    session_id: str = Form(...),
    file: UploadFile = File(...),
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail={"code": "FILE_TOO_LARGE", "max_bytes": MAX_UPLOAD_BYTES},
                )
        except ValueError:
            # Malformed header - not a size signal. The real guard is the
            # streamed byte count below, so fall through rather than 400 here.
            log.debug("ignoring non-integer content-length header %r", content_length)

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": "file type not supported; use PDF, PPTX, TXT, or MD",
            },
        )

    sess = db.get(SessionModel, session_id)
    if sess is None or sess.user_id != user_id:
        raise HTTPException(status_code=404, detail="session not found")

    # C-07: an ended session is read-only (same detail shape as routes/chat.py
    # and the sessions routes). Placed immediately after the ownership check so
    # it costs neither a cost-cap evaluation nor a daily rate-limit slot.
    if sess.ended_at is not None:
        raise HTTPException(status_code=409, detail={"code": "session_ended"})

    raw_name = Path(file.filename or "upload.pdf").name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", raw_name)
    if not safe_name or safe_name in {".", ".."}:
        raise HTTPException(status_code=400, detail={"code": "INVALID_FILENAME"})

    data = _read_bounded(file.file, MAX_UPLOAD_BYTES)

    # C-08: the dedupe lookup runs before the cost gate and the rate limiter so
    # a re-upload of bytes we already hold burns neither. It is a pure SELECT:
    # nothing is committed on this path.
    sha = hashlib.sha256(data).hexdigest()
    existing = _find_existing_document(db, session_id, sha)
    if existing is not None:
        warn = cost_meter.cost_warning_header(db, user_id)
        if warn:
            response.headers["X-Cost-Warning"] = warn
        return UploadResponse(
            document_id=existing.id,
            session_id=session_id,
            filename=existing.filename,
            status=existing.status,
        )

    # B-01: cost caps gate before the rate-limit slot is consumed, mirroring
    # the chat turn's guard order (routes/chat.py:141-153) - a capped account
    # must not be able to burn a daily upload slot on a rejected request.
    try:
        cost_meter.assert_within_caps(db, user_id)
    except cost_meter.CostCapExceeded as e:
        raise HTTPException(
            status_code=429,
            detail={
                "code": e.code,
                "resets_at": cost_meter.midnight_utc_iso(),
            },
        ) from e

    # B-07: rate limit only after extension + ownership pass, mirroring
    # _prepare_turn's guard order - a rejected upload must not consume a
    # daily slot. Ownership-before-increment also guarantees the users row
    # exists for the usage_counters FK (owning a session implies it).
    allowed, used = rate_limit.check_and_increment(db, user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "code": DAILY_CAP_REACHED,
                "cap": settings.daily_cap,
                "used": used,
                "resets_at": cost_meter.midnight_utc_iso(),
            },
        )

    if ext in _PLAINTEXT_EXTENSIONS:
        estimated_chunks = len(data) / _CHARS_PER_TOKEN / _CHUNK_STRIDE_TOKENS
        if estimated_chunks > settings.max_chunks:
            raise HTTPException(
                status_code=413,
                detail={
                    "code": CHUNK_LIMIT_EXCEEDED,
                    "max_chunks": settings.max_chunks,
                    "estimated_chunks": int(estimated_chunks),
                },
            )

    expected = _MAGIC_BYTES.get(ext)
    if expected and not any(data.startswith(m) for m in expected):
        raise HTTPException(
            status_code=415,
            detail={
                "code": "CONTENT_TYPE_MISMATCH",
                "message": "file content does not match its extension",
            },
        )

    # F-03: structural page gate. The plaintext estimate above has no
    # equivalent for containers, so a 3000-page PDF would only be caught
    # after a worker had already loaded and tokenised the whole document.
    page_count = _page_count(ext, data)
    if page_count is not None and page_count > settings.max_pages:
        raise HTTPException(
            status_code=413,
            detail={
                "code": PAGE_LIMIT_EXCEEDED,
                "max_pages": settings.max_pages,
                "page_count": page_count,
            },
        )

    # The pending row must not be committed (and therefore claimable by the
    # worker's poll loop, which runs every 2s) before the blob write
    # completes. flush() assigns the PK for the storage key without opening
    # the row up to a concurrent claim; only commit once the blob write has
    # actually succeeded.
    doc = Document(
        session_id=session_id,
        filename=safe_name,
        status="pending",
        content_sha256=sha,
    )
    db.add(doc)
    try:
        db.flush()
    except IntegrityError:
        # C-08 race: a concurrent request for the same bytes committed its row
        # between our lookup and this flush. Adopt the winner instead of 500ing.
        db.rollback()
        winner = _find_existing_document(db, session_id, sha)
        if winner is None:
            raise
        log.info("upload deduped after insert race", extra={"doc_id": winner.id})
        warn = cost_meter.cost_warning_header(db, user_id)
        if warn:
            response.headers["X-Cost-Warning"] = warn
        return UploadResponse(
            document_id=winner.id,
            session_id=session_id,
            filename=winner.filename,
            status=winner.status,
        )

    # F-29: a failed blob write must not strand a permanent "pending" row.
    # Mark the row failed (visible in the UI banner) and report 507.
    # get_store() itself is inside the try: a bad R2 config can raise on
    # construction, before put() is ever called, and that must route
    # through the same mark-failed + 507 path.
    try:
        store = object_store.get_store()
        store.put(object_store.key_for(doc.id, doc.filename), data)
    except Exception as e:
        log.error(
            "upload storage write failed",
            extra={"doc_id": doc.id},
            exc_info=settings.env != "prod",
        )
        # Discard the never-committed pending insert entirely (it was only
        # flushed, not committed, so no other session could ever have seen
        # it) before persisting a fresh row that starts life as "failed".
        db.rollback()
        try:
            failed_doc = Document(
                session_id=session_id,
                filename=safe_name,
                status="failed",
                error="storage write failed",
            )
            db.add(failed_doc)
            db.commit()
        except Exception:
            db.rollback()
            log.error("could not mark upload row failed", extra={"doc_id": doc.id})
        raise HTTPException(
            status_code=507,
            detail={"code": "STORAGE_WRITE_FAILED"},
        ) from e

    db.commit()
    db.refresh(doc)

    warn = cost_meter.cost_warning_header(db, user_id)
    if warn:
        response.headers["X-Cost-Warning"] = warn

    return UploadResponse(
        document_id=doc.id,
        session_id=session_id,
        filename=doc.filename,
        status="pending",
    )


@router.get("/upload/{document_id}", response_model=UploadStatus)
def get_upload_status(
    document_id: int,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    sess = db.get(SessionModel, doc.session_id)
    if sess is None or sess.user_id != user_id:
        raise HTTPException(status_code=404, detail="document not found")
    return UploadStatus(id=doc.id, status=doc.status, error=doc.error)
