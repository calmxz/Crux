"""Vector retrieval via pgvector (Spec §3.3, §4.2; Phase 7 T4).

retrieve() checks whether any document for the session is ready. If none is
ready, returns status="no_results". Otherwise embeds the query and runs a
cosine-distance search over `chunk_embeddings` scoped to the session.
"""

import logging
import math

from pgvector.sqlalchemy import Vector
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from agent.types import ToolContext
from config import settings
from contracts import RetrieveChunksArgs, ToolResult
from db.models import ChunkEmbedding
from db.models import Session as SessionModel
from services import cost_meter, documents_service, llm, pgvector_store

log = logging.getLogger(__name__)


def _embed_query(db: Session, query: str, *, user_id: str | None, session_id: str) -> list[float]:
    """Sync embed of a single query string through the adapter, which gates,
    retries and settles the spend (F-19). Runs inside the tutor's tool
    dispatch thread.

    Commits `db` first so its pooled connection is not held idle across the
    network call and its retries."""
    db.commit()
    result = llm.get().embed(
        [query], meter=llm.Meter(user_id=user_id, session_id=session_id, purpose="embedding")
    )
    return result.vectors[0]


async def _aembed_query(
    db: Session, query: str, *, user_id: str | None, session_id: str
) -> list[float]:
    """Async embed of a single query string through the adapter, which gates,
    retries and settles the spend (F-19).

    Commits `db` first so the request's pooled connection is not held idle
    across the network call while the adapter checks out its own for the gate
    and the settlement (two per request under load would starve the pool)."""
    await run_in_threadpool(db.commit)
    result = await llm.get().aembed(
        [query], meter=llm.Meter(user_id=user_id, session_id=session_id, purpose="embedding")
    )
    return result.vectors[0]


def retrieve(db: Session, ctx: ToolContext, args: RetrieveChunksArgs) -> ToolResult:
    if args.session_id != ctx.session_id:
        return ToolResult(
            ok=False,
            status="failed",
            error=f"session_id mismatch: args={args.session_id} ctx={ctx.session_id}",
        )

    if not documents_service.has_ready_document(db, ctx.session_id):
        agg = documents_service.session_ingestion_status(db, ctx.session_id)
        return ToolResult(
            ok=True,
            status="no_results",
            error="ingestion_not_ready" if agg is None else f"ingestion_status={agg}",
            data={"chunks": []},
        )

    try:
        query_vec = _embed_query(db, args.query, user_id=ctx.user_id, session_id=ctx.session_id)
        hits = pgvector_store.query_chunks(
            db, session_id=ctx.session_id, query_embedding=query_vec, k=args.k or 5
        )
    except cost_meter.CostCapExceeded as e:
        # A tool result, not an exception: the model sees the refusal, and the
        # tutor's next call is refused by the adapter gate with the cap event.
        return ToolResult(ok=False, status="failed", error=e.code)
    except Exception as e:
        log.error(
            "retrieval failed",
            extra={"err_type": type(e).__name__, "session_id": ctx.session_id},
            exc_info=settings.env != "prod",
        )
        return ToolResult(ok=False, status="failed", error="retrieval_failed")

    chunks = [
        {
            "doc_id": str(h.doc_id),
            "text": h.chunk_text,
            "page": h.page,
            "score": h.score,
            "doc_name": h.doc_name,
        }
        for h in hits
    ]

    if not chunks:
        return ToolResult(ok=True, status="no_results", error=None, data={"chunks": []})
    return ToolResult(ok=True, status="ok", data={"chunks": chunks})


def _is_postgres(db: Session) -> bool:
    return db.get_bind().dialect.name == "postgresql"


def _compute_centroid(db: Session, session_id: str) -> list[float] | None:
    """avg() over every chunk embedding of the session. Postgres-only."""
    centroid = db.execute(
        select(func.avg(ChunkEmbedding.embedding, type_=Vector(settings.embedding_dim))).where(
            ChunkEmbedding.session_id == session_id
        )
    ).scalar()
    if centroid is None:
        return None
    return list(centroid)


def _session_centroid(db: Session, session_id: str) -> list[float] | None:
    """Mean embedding over the session's chunks; None off-Postgres or empty.

    F-05: the avg() aggregation scans every chunk row of the session on every
    OPTIONAL turn. Materialise it on sessions.chunk_centroid and recompute
    only after ingestion or a document delete nulls it.

    The dialect guard stays the first statement so sqlite issues no statement
    at all here (test_chat_prepare_perf counts statements on sqlite).

    The write-back flushes but never commits here; the caller's next commit
    (semantic_fallback_required releases the connection before embedding)
    publishes it. A write-back that is rolled back instead just means the
    next turn recomputes.
    """
    if not _is_postgres(db):
        return None
    stored = db.execute(
        select(SessionModel.chunk_centroid).where(SessionModel.id == session_id)
    ).scalar()
    if stored is not None:
        return list(stored)
    centroid = _compute_centroid(db, session_id)
    if centroid is None:
        return None
    db.execute(
        update(SessionModel).where(SessionModel.id == session_id).values(chunk_centroid=centroid)
    )
    db.flush()
    return centroid


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


async def prefetch_for_prompt(
    db: Session,
    session_id: str,
    user_id: str,
    query: str,
    k: int = 5,
    query_vec: list | None = None,
) -> list[dict] | None:
    """Server-side retrieval for REQUIRED turns, since the REQUIRED flag is
    only advisory -- the model could otherwise answer ungrounded without
    calling retrieve_chunks (F-56). Fetch the chunks ourselves and inject
    them into the prompt instead. Returns chunk dicts (same shape retrieve()
    produces) or None on any failure/no-results, so the caller falls back to
    the advisory flag. Embedding spend is settled by the adapter in its own
    transaction (F-19, B-08), so a caller rollback cannot erase it. A cost
    cap refusal is "no retrieval", like any other failure here.

    query_vec, if given, is the vector already embedded for this same query
    by semantic_fallback_required -- reuse it instead of embedding again,
    since that spend was already metered (B-09).
    """
    try:
        if not documents_service.has_ready_document(db, session_id):
            return None
        if query_vec is None:
            query_vec = await _aembed_query(db, query, user_id=user_id, session_id=session_id)
        hits = pgvector_store.query_chunks(
            db, session_id=session_id, query_embedding=query_vec, k=k
        )
    except Exception as e:
        log.warning("prefetch_for_prompt failed; falling back to advisory flag: %s", e)
        return None
    chunks = [
        {
            "doc_id": str(h.doc_id),
            "text": h.chunk_text,
            "page": h.page,
            "score": h.score,
            "doc_name": h.doc_name,
        }
        for h in hits
    ]
    return chunks or None


async def semantic_fallback_required(
    db: Session,
    session_id: str,
    query: str,
    *,
    user_id: str | None = None,
) -> tuple[bool, list[float] | None]:
    """Escalate the OPTIONAL lexical gate when the query is semantically
    close to the session's uploaded material -- paraphrase/acronym misses
    the stem overlap cannot catch (D2.2). Best-effort by design: any failure
    keeps the gate OPTIONAL, mirroring gap_accuracy in routes/chat.py.

    The adapter gates and settles the embedding call against `user_id`;
    callers that cannot attribute the call to a user may omit it and skip
    the gate and the ledger (F-19). A cost cap refusal keeps the gate
    OPTIONAL. Awaits the embedding on the event loop in _prepare_turn (F-18).

    Also returns the embedded query vector (None whenever the embedding call
    never ran) so a caller that goes on to call prefetch_for_prompt can hand
    it back in and skip a second, identical embed for the same query (B-09).
    """
    if settings.llm_stub_enabled:
        return False, None
    try:
        if not documents_service.has_ready_document(db, session_id):
            return False, None
        # F-05: sync DB work on an async handler's event loop; the centroid
        # read (and the one-off recompute) go to the threadpool.
        centroid = await run_in_threadpool(_session_centroid, db, session_id)
        if centroid is None:
            return False, None
        query_vec = await _aembed_query(db, query, user_id=user_id, session_id=session_id)
        sim = _cosine_similarity(list(query_vec), centroid)
        # B-09: hand the vector back so prefetch_for_prompt can skip its
        # identical embed (2x cost + one extra round-trip on every
        # fallback-required turn otherwise).
        return sim >= settings.retrieval_fallback_threshold, list(query_vec)
    except Exception as e:
        log.warning("semantic fallback check failed; keeping OPTIONAL: %s", e)
        return False, None
