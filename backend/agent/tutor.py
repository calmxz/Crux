"""Streaming tutor agent loop. Calls LiteLLM (stream=True) with the
registered tools and dispatches tool calls until the model returns a final
text answer or max_iters is exhausted, yielding StreamEvent objects live.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncIterator

import litellm

from agent import context_budget, tools
from agent._stub import stub_response
from agent.excerpt import wrap_chunk
from agent.stream_events import StreamEvent
from agent.types import ToolContext
from config import settings
from contracts import Citation, ToolCallRecord, ToolResult
from db.models import ChatMessage
from lib.citations import chunks_to_citations
from services import check_question_service, cost_meter, topic_suggest_service

log = logging.getLogger(__name__)

MAX_ITERS = 8

# Turn-terminating tools: each hands the learner a card and ends the turn, so
# at most one of them runs per response (see the reduce in run_streaming).
_TERMINAL_TOOLS = ("ask_check_questions", topic_suggest_service.TOOL_NAME)

# #354: the topic card sits under the tutor's reply, never alone. A call made
# before any reply text fails so the model writes the reply and calls again.
_SUGGEST_NEEDS_PROSE = (
    "write your reply to the learner first, then call suggest_topics"
)


def _persist_assistant_message(
    ctx, content, status, cancelled_at=None, tool_calls=None, citations=None
):
    # run_streaming OWNS persistence of the streaming assistant message on BOTH
    # normal completion and cancel: a cancelled stream cannot be persisted from
    # the route after the client disconnects, so the agent does it.
    # tool_calls_json / citations_json are serialized here so a resumed session
    # renders streamed messages (including partial ones on cancel) with their
    # tool calls and citations.
    m = ChatMessage(
        session_id=ctx.session_id,
        role="assistant",
        content=content,
        status=status,
        cancelled_at=cancelled_at,
        tool_calls_json=json.dumps([tc.model_dump() for tc in (tool_calls or [])]),
        citations_json=json.dumps([c.model_dump() for c in (citations or [])]),
    )
    ctx.db.add(m)
    ctx.db.commit()
    return m.id


def _persist_partial_on_abort(ctx, accumulated_text, tool_calls, citations, asked_check):
    """F-14: an aborted turn (max_iters, mid-turn cap) must not vanish text
    the learner watched stream. Persist it as 'partial'; if a check batch was
    registered this turn, attach it so it renders with its asking message
    instead of dangling."""
    if not accumulated_text and not asked_check:
        return None
    try:
        msg_id = _persist_assistant_message(
            ctx, accumulated_text, "partial",
            tool_calls=tool_calls, citations=citations,
        )
        if asked_check:
            check_question_service.attach_message_id(ctx.db, ctx.session_id, msg_id)
        return msg_id
    except Exception:
        log.exception(
            "failed to persist partial assistant message on abort "
            "session_id=%s user_id=%s",
            ctx.session_id, ctx.user_id,
        )
        return None


def _summarize(name: str, result) -> str:
    if name == "retrieve_chunks":
        return f"Found {len((result.data or {}).get('chunks', []))} passages"
    if name == "update_topic_profile":
        if result.status == "ignored":
            return "Profile change ignored (inferred evidence)"
        return "Profile updated"
    if name == "ask_check_questions":
        return "Questions asked"
    if name == topic_suggest_service.TOOL_NAME:
        return "Topics suggested"
    return "ok"


def _record_partial_cost(ctx, snapshots: list[list[dict]], text: str, purpose: str) -> Decimal:
    """Estimate and record spend for iterations whose acompletion started but
    was never metered (cancelled or crashed mid-stream). Token-math estimate,
    same shape as the cancellation arm always used. Never raises."""
    prompt_tokens_total = 0
    for snapshot in snapshots:
        try:
            prompt_tokens_total += litellm.token_counter(
                model=settings.model, messages=snapshot
            )
        except Exception as e:
            # Local tokenization only; no credential in the exception.
            log.warning("token_counter failed: %s", e)  # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
    try:
        cost = cost_meter.estimate_cancelled_cost(
            settings.model, text, prompt_tokens_total
        )
    except Exception as e:
        log.warning("estimate_cancelled_cost failed: %s", e)
        cost = Decimal("0")
    try:
        cost_meter.record_cost(ctx.db, ctx.user_id, cost)
    except Exception as e:
        log.warning("cost_meter.record_cost (partial) failed: %s", e)
    cost_meter.log_call(
        ctx.db, user_id=ctx.user_id, session_id=ctx.session_id,
        purpose=purpose, model=settings.model, cost_usd=cost,
    )
    return cost


def _chunk_text(text: str, parts: int = 3) -> list[str]:
    """Split text into ~`parts` word-boundary chunks for stub streaming."""
    words = text.split(" ")
    if len(words) <= 1:
        return [text]
    parts = max(1, min(parts, len(words)))
    size = -(-len(words) // parts)  # ceil division
    out: list[str] = []
    for i in range(0, len(words), size):
        group = words[i : i + size]
        sep = " " if (i + size) < len(words) else ""
        out.append(" ".join(group) + sep)
    return out


async def run_streaming(
    messages: list[dict],
    system_prompt: str,
    ctx: ToolContext,
    max_iters: int = MAX_ITERS,
) -> AsyncIterator[StreamEvent]:
    """The tutor agent loop. Yields StreamEvent objects live.

    Real token streaming via litellm.acompletion(stream=True) each iteration.
    Owns persistence of the assistant ChatMessage (complete or cancelled) and
    records an estimated cost on cancellation.
    """
    # Stub mode: deterministic, no LLM, no tools, no cost. Chunked so the UI
    # still exercises the delta path.
    if settings.llm_stub_enabled:
        text = stub_response(messages, system_prompt)
        accumulated_text = ""
        for piece in _chunk_text(text):
            accumulated_text += piece
            yield StreamEvent("assistant_delta", {"text": piece})
        msg_id = _persist_assistant_message(ctx, accumulated_text, "complete")
        yield StreamEvent("done", {"message_id": str(msg_id)})
        return

    full: list[dict] = [{"role": "system", "content": system_prompt}] + list(messages)
    accumulated_text = ""
    iter_prompt_snapshots: list[list[dict]] = []  # shallow-copied prefix at each iteration start; used only on cancel/error
    billed_iters = 0  # iterations whose cost was metered (real or fallback)
    billed_chars = 0  # accumulated_text length at the last metering point
    tool_calls_record: list[ToolCallRecord] = []
    citations: list[Citation] = list(ctx.prefetched_citations or [])
    asked_check = False  # hoisted so the except asyncio.CancelledError: branch can read it
    dispatch_task: asyncio.Task | None = None  # in-flight tools.dispatch thread (see cancel arm)

    if citations:
        # F-56: server-prefetched excerpts -- emit their citations up front so
        # the FE renders sources even though no retrieve_chunks call happens.
        yield StreamEvent("citations", [c.model_dump() for c in citations])

    try:
        for _i in range(max_iters):
            cap = cost_meter.check_cap(ctx.db, ctx.user_id)
            if not cap.allowed:
                log.warning(
                    "hard cost cap reached mid-turn (stream) "
                    "session_id=%s user_id=%s used=%s",
                    ctx.session_id, ctx.user_id, cap.used,
                )
                _persist_partial_on_abort(
                    ctx, accumulated_text, tool_calls_record, citations, asked_check
                )
                yield StreamEvent(
                    "error",
                    {
                        "code": "daily_cost_cap_reached",
                        "used_usd": str(cap.used),
                        "soft_cap_usd": str(cap.soft_cap),
                        "hard_cap_usd": str(cap.hard_cap),
                    },
                )
                return

            # Shallow-copy each message dict: prune_superseded_excerpts (P2)
            # mutates a tool message's "content" VALUE on the shared dict
            # later in the loop, but a copied dict keeps its own reference to
            # the original (unmutated) string, so this prefix stays exact
            # even if a later iteration's prune stubs an earlier round.
            iter_prompt_snapshots.append([dict(m) for m in full])

            # B-10 (structural): close the transaction the loop-top check_cap
            # SELECT opened so the pooled connection (and, on the Supabase
            # transaction pooler, its pinned backend) returns to the pool for
            # the 10-60 s stream. Commit, not rollback: any flushed ledger
            # increments from earlier this turn are real spend and must
            # survive. Post-stream code reopens a transaction on first use.
            ctx.db.commit()

            resp = await litellm.acompletion(
                model=settings.model,
                temperature=settings.llm_temperature,
                messages=full,
                tools=tools.TOOLS,
                tool_choice="auto",
                stream=True,
                timeout=settings.llm_timeout_s,
            )

            content_buf = ""
            tool_frags: dict[int, dict] = {}
            chunks: list = []

            async for chunk in resp:
                chunks.append(chunk)
                delta = chunk.choices[0].delta

                token = getattr(delta, "content", None)
                if token:
                    content_buf += token
                    accumulated_text += token
                    yield StreamEvent("assistant_delta", {"text": token})

                tcs = getattr(delta, "tool_calls", None)
                if tcs:
                    for tcd in tcs:
                        idx = getattr(tcd, "index", 0)
                        slot = tool_frags.setdefault(
                            idx, {"id": None, "name": None, "args": ""}
                        )
                        tcd_id = getattr(tcd, "id", None)
                        if tcd_id:
                            slot["id"] = tcd_id
                        fn = getattr(tcd, "function", None)
                        if fn is not None:
                            fn_name = getattr(fn, "name", None)
                            if fn_name:
                                slot["name"] = fn_name
                            fn_args = getattr(fn, "arguments", None)
                            if fn_args:
                                slot["args"] += fn_args

            # Record this iteration's cost BEFORE branching on tool_frags. Every
            # acompletion above is billed, so tool-dispatch iterations must count
            # toward the daily cap too -- otherwise a multi-tool turn could evade
            # the hard cost cap by only ever billing its final text iteration.
            built = None
            try:
                built = litellm.stream_chunk_builder(chunks, messages=full)
                cost = litellm.completion_cost(completion_response=built) or 0.0
            except Exception as e:
                log.warning("stream completion_cost failed: %s", e)
                # F-19: a pricing-table gap must not register the turn as $0 --
                # fall back to token math so the cap still sees real spend.
                try:
                    pt = litellm.token_counter(model=settings.model, messages=full)
                    cost = cost_meter.estimate_cancelled_cost(
                        settings.model, content_buf, pt
                    )
                except Exception as e2:  # noqa: BLE001
                    # Local tokenization/cost-estimation only; no credential in the exception.
                    log.warning("stream cost token-math fallback failed: %s", e2)  # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
                    cost = 0.0
            if cost > 0:
                try:
                    cost_meter.record_cost(ctx.db, ctx.user_id, cost)
                except Exception as e:
                    log.warning("cost_meter.record_cost failed: %s", e)
                cost_meter.log_call(
                    ctx.db,
                    user_id=ctx.user_id,
                    session_id=ctx.session_id,
                    purpose="followup" if getattr(ctx, "suppress_check", False) else "chat",
                    model=settings.model,
                    cost_usd=cost,
                    **cost_meter.extract_usage(built),
                )
            billed_iters = len(iter_prompt_snapshots)
            billed_chars = len(accumulated_text)

            # No tool calls assembled -> the streamed content was the final answer.
            if not tool_frags:
                # Soft-cap warning: SSE flushes its headers before the LLM runs,
                # so a response header cannot carry the 90%-of-cap signal; it is
                # emitted as a dedicated event instead and routed through the
                # costBus -> toast on the client.
                post = cost_meter.check_cap(ctx.db, ctx.user_id)
                if post.soft_breached:
                    yield StreamEvent(
                        "cost_warning",
                        {
                            "level": "urgent" if post.urgent_breached else "soft",
                            "used_usd": str(post.used),
                            "soft_cap_usd": str(post.soft_cap),
                            "urgent_cap_usd": str(post.urgent_cap),
                            "hard_cap_usd": str(post.hard_cap),
                        },
                    )
                msg_id = _persist_assistant_message(
                    ctx,
                    accumulated_text,
                    "complete",
                    tool_calls=tool_calls_record,
                    citations=citations,
                )
                yield StreamEvent("done", {"message_id": str(msg_id)})
                return

            # Tool calls present: append the assistant turn, then dispatch each.
            ordered = [tool_frags[k] for k in sorted(tool_frags)]
            # ask_check_questions and suggest_topics are turn-terminating and
            # must be the LAST call of the turn. F-10: bundled non-terminal
            # calls (profile patches, retrieval) are legitimate and are
            # dispatched first in their original order; only ADDITIONAL
            # terminal calls (e.g. a second ask, or a topic card next to a
            # check) are dropped, and the first one streamed wins. Reduce
            # BEFORE building the assistant message so the persisted tool
            # calls and `full` stay consistent.
            terminal_slots = [s for s in ordered if s["name"] in _TERMINAL_TOOLS]
            if terminal_slots:
                non_terminal = [s for s in ordered if s["name"] not in _TERMINAL_TOOLS]
                ordered = non_terminal + terminal_slots[:1]
            full.append(
                {
                    "role": "assistant",
                    "content": content_buf or None,
                    "tool_calls": [
                        {
                            "id": slot["id"],
                            "type": "function",
                            "function": {
                                "name": slot["name"],
                                "arguments": slot["args"],
                            },
                        }
                        for slot in ordered
                    ],
                }
            )

            asked_check = False
            suggested_topics = False
            for slot in ordered:
                name = slot["name"]
                call_id = slot["id"]

                try:
                    args = json.loads(slot["args"]) if slot["args"] else {}
                except json.JSONDecodeError as e:
                    # F-20: a truncated/garbled streamed argument blob must
                    # fail loudly. Dispatching {} would validate (session_id
                    # is injected) and report "Profile updated" for a no-op.
                    log.warning("invalid tool args json (stream): %s", e)
                    result = ToolResult(
                        ok=False, status="failed",
                        error="malformed tool arguments (invalid JSON); retry the call",
                    )
                    tool_calls_record.append(
                        ToolCallRecord(name=name, args={}, status=result.status, error=result.error)
                    )
                    yield StreamEvent(
                        "tool_call_start", {"id": call_id, "name": name, "args": {}}
                    )
                    yield StreamEvent(
                        "tool_call_done",
                        {"id": call_id, "status": "error", "error": result.error},
                    )
                    full.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": name,
                            "content": json.dumps(result.model_dump()),
                        }
                    )
                    continue

                yield StreamEvent(
                    "tool_call_start",
                    {"id": call_id, "name": name, "args": args},
                )

                # asyncio.to_thread cannot be interrupted: cancelling the task
                # while it awaits the thread would leave tools.dispatch running
                # detached, still writing/committing on ctx.db (profile
                # patches, check registration, retrieval embeddings).
                # asyncio.shield keeps dispatch_task running to completion even
                # if this await is cancelled, so the cancel arm below can drain
                # it before touching ctx.db from the main thread (SQLAlchemy
                # Session is not thread-safe).
                if name == topic_suggest_service.TOOL_NAME and not accumulated_text.strip():
                    result = ToolResult(ok=False, status="failed", error=_SUGGEST_NEEDS_PROSE)
                else:
                    dispatch_task = asyncio.ensure_future(
                        asyncio.to_thread(tools.dispatch, name, args, ctx)
                    )
                    result = await asyncio.shield(dispatch_task)
                tool_calls_record.append(
                    ToolCallRecord(
                        name=name, args=args, status=result.status, error=result.error
                    )
                )

                if result.ok:
                    yield StreamEvent(
                        "tool_call_done",
                        {"id": call_id, "status": "ok", "summary": _summarize(name, result)},
                    )
                else:
                    yield StreamEvent(
                        "tool_call_done",
                        {"id": call_id, "status": "error", "error": result.error},
                    )

                if name == "ask_check_questions" and result.ok:
                    data = result.data or {}
                    yield StreamEvent(
                        "check_question",
                        {
                            "gap": data.get("gap"),
                            "items": data.get("items", []),
                            "total": data.get("total", 0),
                            "set_index": data.get("set_index"),
                            "set_total": data.get("set_total"),
                        },
                    )
                    asked_check = True

                if name == topic_suggest_service.TOOL_NAME and result.ok:
                    # The card data is the validated args; on reload it is
                    # read back from this call in tool_calls_json.
                    yield StreamEvent("topic_suggestions", result.data or {})
                    suggested_topics = True

                if name == "retrieve_chunks" and result.ok:
                    raw_chunks = (result.data or {}).get("chunks", [])
                    # G-11: the similarity floor applies to what the user is
                    # shown as a source; raw_chunks itself (what the model
                    # sees) is deliberately unfiltered.
                    new_cites = chunks_to_citations(raw_chunks)
                    # F-56: dedup against citations already present (a server
                    # prefetch, or an earlier retrieve_chunks call this turn)
                    # by (doc_id, text) identity, so overlapping chunks don't
                    # duplicate in citations_json. Yield the FULL merged list:
                    # the FE's citations handler (session.js setCitations)
                    # REPLACES its list on each "citations" event, so a
                    # partial (new-only) yield would drop earlier entries from
                    # the live view -- they'd only reappear on reload.
                    seen = {(c.doc_id, c.text) for c in citations}
                    added_any = False
                    for c in new_cites:
                        key = (c.doc_id, c.text)
                        if key in seen:
                            continue
                        seen.add(key)
                        citations.append(c)
                        added_any = True
                    if added_any:
                        yield StreamEvent(
                            "citations", [c.model_dump() for c in citations]
                        )
                    wrapped_chunks = [
                        {**ch, "text": wrap_chunk(ch)}
                        for ch in raw_chunks
                    ]
                    tool_payload = result.model_copy(
                        update={"data": {**(result.data or {}), "chunks": wrapped_chunks}}
                    )
                    tool_content = json.dumps(tool_payload.model_dump())
                else:
                    tool_content = json.dumps(result.model_dump())

                full.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": tool_content,
                    }
                )

            # P2: earlier same-turn retrieval payloads are superseded once a
            # newer one exists; stub them so they stop re-billing every
            # remaining iteration.
            context_budget.prune_superseded_excerpts(full)

            if asked_check or suggested_topics:
                # Turn-terminating: a check or topic card handed to the learner.
                # Persist and stop. Grading happens on the next turn, not this one.
                # Cost for this LLM call was already recorded above (before the
                # tool-dispatch section), so no extra metering needed here.
                # Soft-cap warning is intentionally skipped here: the card is
                # the active UI element; the next regular reply surfaces the warning.
                msg_id = _persist_assistant_message(
                    ctx,
                    accumulated_text,
                    "complete",
                    tool_calls=tool_calls_record,
                    citations=citations,
                )
                if asked_check:
                    check_question_service.attach_message_id(ctx.db, ctx.session_id, msg_id)
                yield StreamEvent("done", {"message_id": str(msg_id)})
                return

        # max_iters exhausted without a final answer.
        _persist_partial_on_abort(
            ctx, accumulated_text, tool_calls_record, citations, asked_check
        )
        yield StreamEvent("error", {"code": "max_iters_reached"})
        return

    except asyncio.CancelledError:
        # The shielded dispatch (see above) keeps running after this arm is
        # entered. Drain it FIRST, before any ctx.db use below: the worker
        # thread may still be mid-commit (profile_service.apply_patch,
        # check_question_service.register, retrieval_service.retrieve), and
        # SQLAlchemy's Session is not thread-safe.
        if dispatch_task is not None and not dispatch_task.done():
            try:
                await dispatch_task
            except Exception:
                log.warning(
                    "in-flight tool dispatch raised while draining on cancel "
                    "session_id=%s user_id=%s",
                    ctx.session_id, ctx.user_id,
                    exc_info=True,
                )

        # Bill only iterations not yet metered -- completed iterations already
        # recorded real cost above.
        cost = _record_partial_cost(
            ctx,
            iter_prompt_snapshots[billed_iters:],
            accumulated_text[billed_chars:],
            "followup" if getattr(ctx, "suppress_check", False) else "chat",
        )

        # F-01-style guard: a persistence failure here must not replace the
        # CancelledError being propagated below.
        msg_id = None
        try:
            msg_id = _persist_assistant_message(
                ctx,
                accumulated_text,
                "cancelled",
                cancelled_at=datetime.now(timezone.utc),
                tool_calls=tool_calls_record,
                citations=citations,
            )
            if asked_check:
                check_question_service.attach_message_id(ctx.db, ctx.session_id, msg_id)
        except Exception:
            log.exception(
                "failed to persist assistant message on cancel "
                "session_id=%s user_id=%s",
                ctx.session_id, ctx.user_id,
            )

        yield StreamEvent(
            "cancelled",
            {
                "message_id": str(msg_id) if msg_id is not None else None,
                "partial_content_chars": len(accumulated_text),
                "estimated_cost_usd": str(cost),
            },
        )
        raise

    except Exception:
        # F-01: a provider 429/timeout, malformed stream chunk, or tool crash
        # must surface as an error SSE, not a silent stream end that leaves the
        # client stuck in 'streaming'. Persist whatever text already streamed.
        log.exception(
            "agent loop failed (stream); emitting error event "
            "session_id=%s user_id=%s",
            ctx.session_id, ctx.user_id,
        )
        try:
            ctx.db.rollback()  # the session may hold a failed transaction
        except Exception as rb_err:
            log.warning(
                "rollback after agent-loop failure failed: %s "
                "session_id=%s user_id=%s",
                rb_err, ctx.session_id, ctx.user_id,
            )
        # F-03/B-10: re-estimate the WHOLE turn (all snapshots), not just the
        # unbilled tail. Because of B-10's loop-top commit before each
        # acompletion, completed iterations' real costs already survived the
        # rollback above, so on an errored multi-iteration turn this
        # double-counts them -- kept deliberately, since overcounting only
        # shortens the user's own daily budget (no card billing) and is safer
        # than the alternative undercount. It also doesn't account for
        # in-turn retrieval-embedding spend discarded by the rollback (only
        # chat prompt snapshots are re-tokenized), a known negligible
        # undercount (~$0.0005/query) in the opposite direction.
        _record_partial_cost(
            ctx,
            iter_prompt_snapshots,
            accumulated_text,
            "followup" if getattr(ctx, "suppress_check", False) else "chat",
        )
        try:
            msg_id = _persist_assistant_message(
                ctx,
                accumulated_text,
                "error",
                tool_calls=tool_calls_record,
                citations=citations,
            )
            if asked_check:
                check_question_service.attach_message_id(ctx.db, ctx.session_id, msg_id)
        except Exception:
            log.exception(
                "failed to persist assistant message after agent-loop failure "
                "session_id=%s user_id=%s",
                ctx.session_id, ctx.user_id,
            )
        yield StreamEvent(
            "error",
            {
                "code": "llm_failed",
                "message": "The tutor could not finish responding. Please try again.",
            },
        )
        return
