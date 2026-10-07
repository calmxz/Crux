import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, literal, select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from agent import context_budget, prompts, tutor
from agent.excerpt import wrap_chunk
from agent.types import ToolContext
from config import settings
from contracts import ChatRequest
from db.database import SessionLocal, get_db
from db.models import ChatMessage, Document, User
from db.models import Session as SessionModel
from lib import keyword_index
from lib.citations import chunks_to_citations
from lib.error_codes import (
    DAILY_CAP_REACHED,
    DAILY_COST_CAP_REACHED,
    EMPTY_MESSAGE,
    GLOBAL_COST_CAP_REACHED,
    SESSION_ENDED,
)
from services import (
    check_question_service,
    cost_meter,
    documents_service,
    learning_event_service,
    pending_check_store,
    profile_service,
    rate_limit,
    retrieval_service,
    summary_service,
    velocity_limit,
)
from services.auth import accepted_terms_from_request, current_user_id
from services.user_service import ensure_user

router = APIRouter(prefix="/api")
log = logging.getLogger(__name__)


async def _rolling_summary_task(session_id: str) -> None:
    """Post-response: refresh the rolling summary if due. Opens its own DB
    session because the request-scoped session is closed by the time
    background tasks run. Must never raise: a failed rolling summary must
    not break a chat turn (the response has already been sent)."""
    db = SessionLocal()
    try:
        await summary_service.update_rolling_summary(db, session_id)
    except Exception as e:  # noqa: BLE001 - never surface to the client
        log.warning("rolling summary task failed: %s", e)
    finally:
        db.close()


def _build_prompt_state(
    *,
    session: SessionModel,
    profile,
    ingestion_status,
    retrieval_required: bool,
    review_gaps: bool,
    review_gap: str | None = None,
    diagnostic_accepted: bool = False,
    pending_check,
    quiz_cooldown,
    gap_accuracy: dict | None = None,
    prefetched_chunks=None,
    learner_prefs: dict | None = None,
) -> dict:
    """Build the prompt_state dict consumed by prompts.build_system_prompt.

    Pure function (no DB access) so it can be unit-tested directly.
    """
    prompt_state = {
        "topic": session.topic,
        "profile": profile,
        "ingestion_status": ingestion_status,
        "retrieval_required": retrieval_required,
        "diagnostic_required": profile.knowledge_level is None,
        "seed_mode": None,
        "last_session_summary": profile.last_session_summary,
        "rolling_summary": getattr(session, "rolling_summary", None),
        "pending_check": pending_check,
        # #340: lets the prompt tell "between sets" from "no check".
        "current_check": (
            pending_check_store.get_current_check_from_row(session)
            if getattr(session, "current_check_json", None) else None
        ),
        "quiz_cooldown": quiz_cooldown,
        "gap_accuracy": gap_accuracy or {},
        "learner_prefs": learner_prefs or {},
        # #354: gates the once-per-session topic card.
        "topic_suggest_state": getattr(session, "topic_suggest_state", None),
    }
    if diagnostic_accepted and profile.knowledge_level is None:
        prompt_state["diagnostic_accepted"] = True
    if review_gaps:
        gaps = profile_service.concept_names(profile.confirmed_gaps)
        mastered = [
            c
            for c in profile_service.concept_names(profile.mastered_concepts)
            if c not in gaps
        ]
        pool = gaps + mastered
        if pool:
            if review_gap in pool:
                target = review_gap
            else:
                # Requested review_gap isn't in the pool (e.g. resolved/renamed
                # since the queue was fetched): fall back to the first
                # confirmed gap, deliberately preferring gaps over mastered
                # retention concepts as the substitute target.
                target = gaps[0] if gaps else pool[0]
            prompt_state["review_gaps_target"] = target
            prompt_state["review_gaps_retention"] = target in mastered
            prompt_state["diagnostic_required"] = False
            prompt_state["diagnostic_accepted"] = False
    if prefetched_chunks:
        prompt_state["prefetched_excerpts"] = [
            wrap_chunk(ch) for ch in prefetched_chunks
        ]
    return prompt_state


def _turn_reserve() -> Decimal:
    """B-05: the provisional per-turn charge held at the cost gate."""
    return Decimal(str(settings.llm_turn_reserve_usd))


def _cost_cap_error(cost_status) -> HTTPException:
    """The 429 envelope for a breached per-user daily cost cap (unchanged
    payload; shared by the read gate and the B-05 reservation gate)."""
    return HTTPException(
        status_code=429,
        detail={
            "code": DAILY_COST_CAP_REACHED,
            "soft_cap_usd": str(cost_status.soft_cap),
            "hard_cap_usd": str(cost_status.hard_cap),
            "used_usd": str(cost_status.used),
            "resets_at": cost_meter.midnight_utc_iso(),
        },
    )


def _release_reserve(db: Session, user_id: str) -> None:
    """B-05: hand back this turn's provisional reservation. Synchronous; async
    callers run it via run_in_threadpool.

    Rolls back first: after a failed or cancelled turn the shared session can
    be left in rollback-required state, and run_streaming owns its own commits,
    so nothing publishable is discarded here. Never raises -- a failed release
    must not turn a finished turn into an error; the residue expires at UTC
    midnight with the ledger row.
    """
    reserve = _turn_reserve()
    if reserve <= 0:
        return
    try:
        db.rollback()
        cost_meter.adjust_cost(db, user_id, -reserve)
        db.commit()
    except Exception as e:  # noqa: BLE001 - release is best-effort by design
        log.warning("cost reserve release failed: %s", e)
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass


def _prepare_turn_guards(
    req: ChatRequest,
    user_id: str,
    db: Session,
    accepted_terms: bool,
):
    """Synchronous guard segment of _prepare_turn (steps 1-5).

    F-11: split out so the caller can run it via run_in_threadpool instead of
    blocking the event loop on psycopg. The guard ORDER inside this function
    is load-bearing -- see _prepare_turn's docstring -- and must not change.
    Returns (session, ingestion_status, learner_prefs); raises HTTPException on rejection
    (propagates through run_in_threadpool unchanged).
    """
    # 1) Combined guard read: today's spend + user existence + the learner
    # preferences for the prompt (#356), one statement. A missing user reads
    # all-NULL preferences, which the prompt renders as defaults.
    exists_subq = select(literal(True)).where(User.id == user_id).exists()
    pref_cols = (User.feedback_pref, User.check_ins, User.reply_length)
    spend_raw, user_exists, *pref_values = db.execute(
        select(
            cost_meter.spend_subquery(user_id),
            exists_subq,
            *(
                select(col).where(User.id == user_id).scalar_subquery()
                for col in pref_cols
            ),
        )
    ).one()
    learner_prefs = {col.key: value for col, value in zip(pref_cols, pref_values, strict=True)}

    cost_status = cost_meter.check_cap_from_spend(Decimal(str(spend_raw or 0)))
    if not cost_status.allowed:
        raise _cost_cap_error(cost_status)

    if settings.global_daily_cost_cap_usd is not None:
        if cost_meter.global_spend(db) >= Decimal(
            str(settings.global_daily_cost_cap_usd)
        ):
            raise HTTPException(
                status_code=429,
                detail={
                    "code": GLOBAL_COST_CAP_REACHED,
                    "resets_at": cost_meter.midnight_utc_iso(),
                },
            )

    # 2) Session + ingestion counts in one statement. Runs BEFORE the rate
    # limiter so a rejected turn (foreign 404 / ended 409) does not consume
    # a daily slot, and before ensure_user so bogus session ids don't create
    # user rows.
    doc_base = select(func.count()).where(Document.session_id == req.session_id)
    row = db.execute(
        select(
            SessionModel,
            doc_base.scalar_subquery().label("doc_total"),
            doc_base.where(Document.status == "pending").scalar_subquery().label("doc_pending"),
            doc_base.where(Document.status == "processing").scalar_subquery().label("doc_processing"),
            doc_base.where(Document.status == "ready").scalar_subquery().label("doc_ready"),
        ).where(SessionModel.id == req.session_id)
    ).first()
    if row is None or row[0].user_id != user_id:
        raise HTTPException(status_code=404, detail="session not found")
    session = row[0]
    if session.ended_at is not None:
        raise HTTPException(status_code=409, detail={"code": SESSION_ENDED})
    ingestion_status = documents_service.status_from_counts(
        row.doc_total, row.doc_pending, row.doc_ready, row.doc_processing
    )
    # Detach: ensure_user/check_and_increment commit below would otherwise
    # expire this already-fully-loaded row (expire_on_commit), forcing a
    # refresh SELECT the first time a column is read afterwards. All later
    # reads of `session` are plain columns already fetched by the SELECT
    # above, so detaching is safe and keeps the statement count neutral.
    db.expunge(session)

    # 3) First-turn-ever: create the user row BEFORE the usage-counter
    # insert whose FK references it (F-36). check_and_increment's internal
    # commit persists both together.
    if not user_exists:
        ensure_user(db, user_id, accepted_terms=accepted_terms)

    # 3b) B-05: reserve this turn's provisional spend and gate on the
    # PRE-increment total. The read gate in step 1 is an early-out only: N
    # concurrent turns at cap-minus-epsilon all pass it. Routing every turn
    # through the ledger upsert serializes them on the row, so each caller
    # sees a distinct total and only those below the hard cap are admitted.
    #
    # Placement: AFTER ensure_user, because daily_cost_ledger.user_id is
    # FK-bound to users.id -- reserving before that row exists raises
    # IntegrityError on Postgres for a first-turn-ever user. Nothing is
    # committed between ensure_user and here, so the reject arm below leaves
    # nothing behind: get_db closes without committing and the flush is lost.
    reserve = _turn_reserve()
    pre_spend = cost_meter.reserve_cost(db, user_id, reserve)
    reserve_status = cost_meter.check_cap_from_spend(pre_spend)
    if not reserve_status.allowed:
        raise _cost_cap_error(reserve_status)

    # 4-5) Rate limit: 2 statements on the allowed path.
    allowed, used = rate_limit.check_and_increment(db, user_id)
    if not allowed:
        # B-05: check_and_increment's internal commit has just published the
        # reservation, so this is the one reject arm that must give it back
        # explicitly instead of relying on the transaction being discarded.
        _release_reserve(db, user_id)
        raise HTTPException(  # unchanged detail payload
            status_code=429,
            detail={
                "code": DAILY_CAP_REACHED,
                "cap": settings.daily_cap,
                "used": used,
                "resets_at": cost_meter.midnight_utc_iso(),
            },
        )

    return session, ingestion_status, learner_prefs


def _prepare_turn_context(req: ChatRequest, db: Session, session: SessionModel):
    """Synchronous history/profile/lexical-gate segment of _prepare_turn.

    F-11: split out so the caller can run it via run_in_threadpool. Returns
    (messages, profile, gap_accuracy, retrieval_required).
    """
    history = db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == req.session_id)
        # C-18: id DESC breaks created_at ties, so a batched write (or a coarse
        # clock) cannot reorder the prompt history or drop the wrong turn.
        # Matches services/session_enrichment.py and the session library query.
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(20)
    ).scalars().all()
    history = list(reversed(history))

    # P2: cap each history message; the current user message (appended below)
    # and the system prompt are exempt.
    messages = [
        {"role": m.role, "content": context_budget.truncate_message(m.content)}
        for m in history
    ]
    messages.append({"role": "user", "content": req.message})

    profile = profile_service.profile_from_row(session)

    # D1.2: per-gap accuracy, best-effort. Only run when there is something
    # to enrich (confirmed_gaps non-empty) to keep the no-gaps path inside
    # the P3.1 budget; a failure here must never kill the turn.
    gap_accuracy: dict[str, dict] = {}
    if profile.confirmed_gaps:
        try:
            gap_accuracy = learning_event_service.gap_accuracy(db, req.session_id)
        except Exception as e:  # noqa: BLE001 - best-effort prompt enrichment
            log.warning("gap_accuracy failed; continuing without it: %s", e)

    retrieval_required = keyword_index.match_required(
        req.message, json.loads(session.kw_index_json or "[]")
    )
    # F-13: this segment is read-only, and the caller's next two steps are
    # awaited embedding round-trips (semantic_fallback_required /
    # prefetch_for_prompt). Committing here releases the pooled connection for
    # the duration of those awaits instead of holding an idle-in-transaction
    # one. `session` was already expunged by the guards and everything read
    # afterwards is a plain local, so commit-expiry costs no refresh SELECT.
    db.commit()
    return messages, profile, gap_accuracy, retrieval_required


def _persist_user_turn(req: ChatRequest, db: Session) -> None:
    """F-11: synchronous user-message persist segment."""
    db.add(ChatMessage(session_id=req.session_id, role="user", content=req.message))
    db.commit()


def _persist_user_turn_after_failure(
    req: ChatRequest, db: Session, user_id: str, embed_cost_holder: list
) -> None:
    """F-11: synchronous failure-path persist segment.

    Rollback discarded metered embedding spend flushed by the retrieval calls;
    re-record it on the fresh transaction so real vendor cost is never lost.
    The user-message commit publishes both (B-08/F-19).
    """
    db.rollback()
    total_embed = sum(embed_cost_holder, Decimal("0"))
    if total_embed > 0:
        cost_meter.record_cost(db, user_id, total_embed)
    db.add(ChatMessage(session_id=req.session_id, role="user", content=req.message))
    db.commit()


async def _prepare_turn_after_guards(
    req: ChatRequest,
    user_id: str,
    db: Session,
    session: SessionModel,
    ingestion_status,
    learner_prefs: dict,
) -> tuple[list[dict], str, ToolContext]:
    """Steps 6-7 of _prepare_turn: history -> prompt build -> user-message
    persist.

    Split out from _prepare_turn so the caller can release the B-05 cost
    reservation (already committed by the guards) on any failure in here.
    """
    # 6) History through prompt build. An unexpected crash here must not lose
    # the user's message: persist it, then re-raise. Happy path pays no extra
    # statement.
    embed_cost_holder: list = []
    try:
        messages, profile, gap_accuracy, retrieval_required = await run_in_threadpool(
            _prepare_turn_context, req, db, session
        )
        query_vec = None
        if not retrieval_required:
            retrieval_required, query_vec = await retrieval_service.semantic_fallback_required(
                db, req.session_id, req.message, user_id=user_id,
                cost_holder=embed_cost_holder,
            )

        prefetched_chunks = None
        if retrieval_required:
            prefetched_chunks = await retrieval_service.prefetch_for_prompt(
                db, req.session_id, user_id, req.message,
                query_vec=query_vec, cost_holder=embed_cost_holder,
            )

        prompt_state = _build_prompt_state(
            session=session,
            profile=profile,
            ingestion_status=ingestion_status,
            retrieval_required=retrieval_required,
            review_gaps=getattr(req, "review_gaps", False),
            review_gap=getattr(req, "review_gap", None),
            diagnostic_accepted=getattr(req, "diagnostic_accepted", False),
            pending_check=pending_check_store.get_pending_check_from_row(session),
            quiz_cooldown=check_question_service.get_quiz_cooldown_from_row(session),
            gap_accuracy=gap_accuracy,
            prefetched_chunks=prefetched_chunks,
            learner_prefs=learner_prefs,
        )
        system_prompt = prompts.build_system_prompt(prompt_state)
    except Exception:
        await run_in_threadpool(
            _persist_user_turn_after_failure, req, db, user_id, embed_cost_holder
        )
        raise

    # 7) Persist the user turn LAST (still committed before returning, so it
    # survives an early stream end) - after all reads, so commit-expiry does
    # not trigger a refresh SELECT.
    await run_in_threadpool(_persist_user_turn, req, db)

    ctx = ToolContext(
        db=db,
        session_id=req.session_id,
        user_id=user_id,
        turn_started_at=datetime.now(timezone.utc),
        diagnostic_required=bool(prompt_state.get("diagnostic_required", False)),
        # G-11: floor applies to the surfaced citations only; the prefetched
        # chunks themselves already went into the prompt above, unfiltered.
        prefetched_citations=(
            chunks_to_citations(prefetched_chunks) if prefetched_chunks else None
        ),
    )

    return messages, system_prompt, ctx


async def _prepare_turn(
    req: ChatRequest,
    user_id: str,
    db: Session,
    accepted_terms: bool = False,
) -> tuple[list[dict], str, ToolContext]:
    """Pre-flight for /chat/stream.

    Guard order: cost cap -> session 404/409 -> ensure_user -> cost reserve ->
    rate limit. The session guard runs before ensure_user and the rate limiter
    so a rejected turn (unknown/foreign session 404, ended session 409) neither
    creates a user row nor consumes a daily rate-limit slot. ensure_user runs
    before check_and_increment so the FK-bearing usage_counters insert never
    races ahead of the users row it references (F-36); check_and_increment's
    internal commit persists both together, plus the B-05 reservation taken
    between them. Loads history, builds the system prompt, then persists the
    user ChatMessage last (committed before returning so it survives even if
    the stream ends early), and returns (messages, system_prompt, ctx).

    F-11: every synchronous DB segment runs via run_in_threadpool so psycopg
    never blocks the event loop. The segments are sequential awaits, so no two
    threadpool calls ever touch `db` concurrently.
    """
    # C-10: the contract's minLength=1 stops "" but not "   ". Reject
    # whitespace-only input as the very first statement, before any guard side
    # effect (no cost reservation, no rate-limit slot, no persisted message).
    # The stored message itself is never stripped.
    if not req.message.strip():
        raise HTTPException(status_code=422, detail={"code": EMPTY_MESSAGE})

    session, ingestion_status, learner_prefs = await run_in_threadpool(
        _prepare_turn_guards, req, user_id, db, accepted_terms
    )

    # B-05: past the guards the reservation is committed, so any failure
    # between here and the start of the stream must hand it back. Once
    # chat_stream has the context, its event_stream finally owns the release.
    try:
        return await _prepare_turn_after_guards(
            req, user_id, db, session, ingestion_status, learner_prefs
        )
    except BaseException:
        # #421: shielded, or a cancel here cancels the release too (see
        # chat_stream's finally).
        with anyio.CancelScope(shield=True):
            await run_in_threadpool(_release_reserve, db, user_id)
        raise


@router.post("/chat/stream", dependencies=[Depends(velocity_limit.enforce_velocity)])
async def chat_stream(
    req: ChatRequest,
    request: Request,
    user_id: str = Depends(current_user_id),
    db: Session = Depends(get_db),
):
    """Streaming SSE endpoint. Yields StreamEvent payloads as text/event-stream.

    Pre-flight (_prepare_turn) runs synchronously before StreamingResponse is
    returned, so HTTPException(404/429) surfaces as normal JSON error responses.
    run_streaming owns persistence of the assistant ChatMessage on both normal
    completion and cancellation.
    """
    t0 = time.perf_counter()
    messages, system_prompt, ctx = await _prepare_turn(
        req, user_id, db, accepted_terms=accepted_terms_from_request(request)
    )
    prepare_ms = (time.perf_counter() - t0) * 1000.0

    async def event_stream():
        queue: asyncio.Queue = asyncio.Queue()
        first_token_logged = False

        async def produce():
            try:
                async for event in tutor.run_streaming(messages, system_prompt, ctx):
                    await queue.put(event)
            finally:
                await queue.put(None)  # sentinel

        task = asyncio.create_task(produce())
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                if event is None:
                    break
                yield event.to_sse()
                if settings.debug_timing and not first_token_logged:
                    first_token_logged = True
                    log.info(
                        "chat timing prepare_ms=%.1f first_token_ms=%.1f",
                        prepare_ms,
                        (time.perf_counter() - t0) * 1000.0,
                    )
                if event.type in ("done", "error", "cancelled"):
                    break
        finally:
            # B-05: drain the producer, then hand back the per-turn reservation
            # exactly once -- both inside ONE shield.
            #
            # The shield is what makes the ordering real. On a client
            # disconnect the surrounding cancel scope is cancelled
            # level-triggered, so every await here raises CancelledError
            # immediately: an unshielded `await task` returns at once (its
            # CancelledError swallowed below) while the tutor's cancel arm is
            # still mid-unwind -- it has suspension points around
            # _persist_assistant_message / ctx.db.commit(). _release_reserve
            # would then run db.rollback() + upsert + commit on that same
            # Session concurrently, discarding the pending "cancelled"
            # assistant message or raising on two-thread Session use and
            # stranding the reserve. Shielding the release alone also keeps it
            # from being skipped entirely (reserve stranded until UTC
            # midnight), which is why it was shielded to begin with.
            with anyio.CancelScope(shield=True):
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        # Producer cancelled or errored during disconnect
                        # cleanup; suppress.
                        pass
                await run_in_threadpool(_release_reserve, db, user_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
        background=BackgroundTask(_rolling_summary_task, req.session_id),
    )
