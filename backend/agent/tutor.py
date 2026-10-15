"""Streaming tutor agent loop. Streams each iteration through the LLM adapter
(services/llm.py) with the registered tools and dispatches tool calls until
the model returns a final text answer or max_iters is exhausted, yielding
StreamEvent objects live. The adapter gates, retries and settles each call.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncIterator

from agent import context_budget, tools
from agent.excerpt import wrap_chunk
from agent.stream_events import StreamEvent
from agent.types import ToolContext
from config import settings
from contracts import Citation, ToolCallRecord, ToolResult
from db.models import ChatMessage
from lib.citations import chunks_to_citations
from lib.error_codes import LLM_FAILED, MAX_ITERS_REACHED
from services import check_service, cost_meter, llm, topic_suggest_service

log = logging.getLogger(__name__)

MAX_ITERS = 8

# Turn-terminating tools: each hands the learner a card and ends the turn, so
# at most one of them runs per response (see the reduce in run_streaming).
_TERMINAL_TOOLS = ("ask_check_questions", topic_suggest_service.TOOL_NAME)

# #354: the topic card sits under the tutor's reply, never alone. A call made
# before any reply text fails so the model writes the reply and calls again.
_SUGGEST_NEEDS_PROSE = "write your reply to the learner first, then call suggest_topics"


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
            ctx,
            accumulated_text,
            "partial",
            tool_calls=tool_calls,
            citations=citations,
        )
        if asked_check:
            check_service.stamp_message_id(ctx.db, ctx.session_id, msg_id)
        return msg_id
    except Exception:
        log.exception(
            "failed to persist partial assistant message on abort session_id=%s user_id=%s",
            ctx.session_id,
            ctx.user_id,
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


async def _drain_dispatch(dispatch_task: asyncio.Task | None, ctx) -> None:
    """Wait for an in-flight tools.dispatch thread to finish. Never raises."""
    if dispatch_task is None or dispatch_task.done():
        return
    try:
        await dispatch_task
    except Exception:
        log.warning(
            "in-flight tool dispatch raised while draining on cancel session_id=%s user_id=%s",
            ctx.session_id,
            ctx.user_id,
            exc_info=True,
        )


async def run_streaming(
    messages: list[dict],
    system_prompt: str,
    ctx: ToolContext,
    max_iters: int = MAX_ITERS,
) -> AsyncIterator[StreamEvent]:
    """The tutor agent loop. Yields StreamEvent objects live.

    Real token streaming through llm.get().stream() each iteration. Owns
    persistence of the assistant ChatMessage (complete or cancelled). Spend is
    the adapter's: each call settles once on its own exit, so no path here
    records cost.
    """
    full: list[dict] = [{"role": "system", "content": system_prompt}] + list(messages)
    accumulated_text = ""
    meter = llm.Meter(
        ctx.user_id,
        ctx.session_id,
        "followup" if getattr(ctx, "suppress_check", False) else "chat",
    )
    tool_calls_record: list[ToolCallRecord] = []
    citations: list[Citation] = list(ctx.prefetched_citations or [])
    asked_check = False  # hoisted so the except asyncio.CancelledError: branch can read it
    dispatch_task: asyncio.Task | None = None  # in-flight tools.dispatch thread (see cancel arm)
    inflight: llm.LlmStream | None = None  # the call a cancel cut short, if any

    if citations:
        # F-56: server-prefetched excerpts -- emit their citations up front so
        # the FE renders sources even though no retrieve_chunks call happens.
        yield StreamEvent("citations", [c.model_dump() for c in citations])

    try:
        for _ in range(max_iters):
            # B-10 (structural): close the transaction this turn's earlier
            # reads opened so the pooled connection (and, on the Supabase
            # transaction pooler, its pinned backend) returns to the pool for
            # the 10-60 s stream. Post-stream code reopens one on first use.
            ctx.db.commit()

            stream = llm.get().stream(
                full,
                meter=meter,
                tools=tools.TOOLS,
                tool_choice="auto",
                temperature=settings.llm_temperature,
                timeout=settings.llm_timeout_s,
            )
            try:
                async with stream:
                    inflight = stream
                    async for ev in stream:
                        accumulated_text += ev.text
                        yield StreamEvent("assistant_delta", {"text": ev.text})
                    # Finished, so a cancel landing in the exit's close cut
                    # nothing short (the exit settles its real price).
                    inflight = None
            except llm.CallRefused as refused:
                # The adapter refused this call (user cap, global ceiling, or
                # no provider can serve it); the model was not called.
                log.warning(
                    "llm call refused mid-turn (stream) code=%s session_id=%s user_id=%s",
                    refused.code,
                    ctx.session_id,
                    ctx.user_id,
                )
                _persist_partial_on_abort(
                    ctx, accumulated_text, tool_calls_record, citations, asked_check
                )
                payload = {"code": refused.code}
                if refused.cap is not None:
                    payload |= {
                        "used_usd": str(refused.cap.used),
                        "soft_cap_usd": str(refused.cap.soft_cap),
                        "hard_cap_usd": str(refused.cap.hard_cap),
                    }
                yield StreamEvent("error", payload)
                return
            content_buf = stream.text

            # No tool calls -> the streamed content was the final answer.
            if not stream.tool_calls:
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
            ordered = stream.tool_calls
            # ask_check_questions and suggest_topics are turn-terminating and
            # must be the LAST call of the turn. F-10: bundled non-terminal
            # calls (profile patches, retrieval) are legitimate and are
            # dispatched first in their original order; only ADDITIONAL
            # terminal calls (e.g. a second ask, or a topic card next to a
            # check) are dropped, and the first one streamed wins. Reduce
            # BEFORE building the assistant message so the persisted tool
            # calls and `full` stay consistent.
            terminal_calls = [tc for tc in ordered if tc.name in _TERMINAL_TOOLS]
            if terminal_calls:
                non_terminal = [tc for tc in ordered if tc.name not in _TERMINAL_TOOLS]
                ordered = non_terminal + terminal_calls[:1]
            full.append(
                {
                    "role": "assistant",
                    "content": content_buf or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": tc.arguments},
                        }
                        for tc in ordered
                    ],
                }
            )

            asked_check = False
            suggested_topics = False
            for tc in ordered:
                name = tc.name
                call_id = tc.id

                try:
                    args = json.loads(tc.arguments) if tc.arguments else {}
                except json.JSONDecodeError as e:
                    # F-20: a truncated/garbled streamed argument blob must
                    # fail loudly. Dispatching {} would validate (session_id
                    # is injected) and report "Profile updated" for a no-op.
                    log.warning("invalid tool args json (stream): %s", e)
                    result = ToolResult(
                        ok=False,
                        status="failed",
                        error="malformed tool arguments (invalid JSON); retry the call",
                    )
                    tool_calls_record.append(
                        ToolCallRecord(name=name, args={}, status=result.status, error=result.error)
                    )
                    yield StreamEvent("tool_call_start", {"id": call_id, "name": name, "args": {}})
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
                    ToolCallRecord(name=name, args=args, status=result.status, error=result.error)
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
                        yield StreamEvent("citations", [c.model_dump() for c in citations])
                    wrapped_chunks = [{**ch, "text": wrap_chunk(ch)} for ch in raw_chunks]
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
                    check_service.stamp_message_id(ctx.db, ctx.session_id, msg_id)
                yield StreamEvent("done", {"message_id": str(msg_id)})
                return

        # max_iters exhausted without a final answer.
        _persist_partial_on_abort(ctx, accumulated_text, tool_calls_record, citations, asked_check)
        yield StreamEvent("error", {"code": MAX_ITERS_REACHED})
        return

    except asyncio.CancelledError:
        # The shielded dispatch (see above) keeps running after this arm is
        # entered. Drain it FIRST, before any ctx.db use below: the worker
        # thread may still be mid-commit (profile_service.apply_patch,
        # check_service.register, retrieval_service.retrieve), and
        # SQLAlchemy's Session is not thread-safe.
        await _drain_dispatch(dispatch_task, ctx)

        # The call this cancel cut short settled its own estimate as it
        # exited; a cancel between calls (during tool dispatch) cut none.
        cost = Decimal("0")
        if inflight is not None and inflight.cost is not None:
            cost = inflight.cost

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
                check_service.stamp_message_id(ctx.db, ctx.session_id, msg_id)
        except Exception:
            log.exception(
                "failed to persist assistant message on cancel session_id=%s user_id=%s",
                ctx.session_id,
                ctx.user_id,
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
            "agent loop failed (stream); emitting error event session_id=%s user_id=%s",
            ctx.session_id,
            ctx.user_id,
        )
        try:
            ctx.db.rollback()  # the session may hold a failed transaction
        except Exception as rb_err:
            log.warning(
                "rollback after agent-loop failure failed: %s session_id=%s user_id=%s",
                rb_err,
                ctx.session_id,
                ctx.user_id,
            )
        # No re-estimate: every call settled once in the adapter's own
        # transaction as it exited, so the rollback above erased no spend.
        try:
            msg_id = _persist_assistant_message(
                ctx,
                accumulated_text,
                "error",
                tool_calls=tool_calls_record,
                citations=citations,
            )
            if asked_check:
                check_service.stamp_message_id(ctx.db, ctx.session_id, msg_id)
        except Exception:
            log.exception(
                "failed to persist assistant message after agent-loop failure "
                "session_id=%s user_id=%s",
                ctx.session_id,
                ctx.user_id,
            )
        yield StreamEvent(
            "error",
            {
                "code": LLM_FAILED,
                "message": "The tutor could not finish responding. Please try again.",
            },
        )
        return
