"""Tests for the streaming tutor agent loop (tutor.run_streaming).

run_streaming yields StreamEvent objects live, streams each iteration through
the LLM adapter, and owns persistence of the assistant ChatMessage (on both
normal completion and cancel). Spend is the adapter's: each call settles once
on its own exit.

The model is the scripted fake provider (conftest fake_llm) behind the real
adapter shell, so the gate and settlement run for real. A script is a list of
steps: a str is a text token, tool_call(...) an assembled tool call, an
exception is raised at that point and BLOCK parks until cancelled. litellm's
chunk parsing is the provider's and is tested in test_llm.py.
"""

import asyncio
import json
import threading
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from agent import tutor
from agent.types import ToolContext
from config import settings
from contracts import Citation, ToolResult, TopicProfile
from db.models import ChatMessage, LlmCallLog, User
from db.models import Session as SessionModel
from services import cost_meter
from services.cost_meter import CapStatus
from tests.conftest import BLOCK, tool_call

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(db_session, session_id="s1"):
    return ToolContext(
        db=db_session,
        session_id=session_id,
        user_id="u1",
        turn_started_at=datetime.now(timezone.utc),
    )


@pytest.fixture(autouse=True)
def _real_loop(monkeypatch, fake_llm):
    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")


@pytest.fixture
def user(db_session):
    db_session.add(User(id="u1"))
    db_session.commit()


def _cap(**overrides) -> CapStatus:
    fields = {
        "allowed": True,
        "used": Decimal("0.0"),
        "soft_breached": False,
        "urgent_breached": False,
        "soft_cap": Decimal("2.0"),
        "urgent_cap": Decimal("2.70"),
        "hard_cap": Decimal("3.0"),
    }
    return CapStatus(**(fields | overrides))


async def _drain(agen):
    return [ev async for ev in agen]


async def _run_and_cancel(ctx, after_text="partial "):
    """Run a turn, cancel it once `after_text` has streamed (the stream then
    parks on BLOCK), and return the events received."""
    received = []
    reached = asyncio.Event()

    async def _consume():
        async for ev in tutor.run_streaming([{"role": "user", "content": "go"}], "sys", ctx):
            received.append(ev)
            if ev.type == "assistant_delta" and ev.data["text"] == after_text:
                reached.set()

    task = asyncio.create_task(_consume())
    try:
        await asyncio.wait_for(reached.wait(), timeout=5)
    except TimeoutError:
        # Reap the task so it cannot outlive the test (and db_session).
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise AssertionError("stream never reached its parked chunk") from None
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.gather(task)
    return received


def _retrieve(call_id, query):
    return tool_call("retrieve_chunks", {"query": query}, id=call_id)


def _retrieval_dispatch(name, args, ctx):
    first = args.get("query") == "a"
    chunk = {
        "doc_id": "d1" if first else "d2",
        "doc_name": "notes.pdf" if first else "slides.pdf",
        "text": "old material" if first else "new material",
    }
    return ToolResult(ok=True, status="ok", error=None, data={"chunks": [chunk]})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_streaming_yields_tool_then_delta_then_done(db_session, fake_llm, monkeypatch):
    fake_llm.streams = [
        [tool_call("retrieve_chunks", '{"query":"photosynthesis"}', id="tc_1")],
        ["Hello ", "world"],
    ]
    result = ToolResult(
        ok=True,
        status="ok",
        error=None,
        data={"chunks": [{"doc_id": "d1", "text": "leaves convert light"}]},
    )
    monkeypatch.setattr("agent.tutor.tools.dispatch", MagicMock(return_value=result))

    ctx = _ctx(db_session, session_id="s1")
    events = await _drain(tutor.run_streaming([{"role": "user", "content": "explain"}], "sys", ctx))

    types = [e.type for e in events]
    assert "tool_call_start" in types
    assert "tool_call_done" in types
    assert "citations" in types
    assert types.count("assistant_delta") == 2
    assert types[-1] == "done"

    deltas = [e.data["text"] for e in events if e.type == "assistant_delta"]
    assert deltas == ["Hello ", "world"]

    start = next(e for e in events if e.type == "tool_call_start")
    assert start.data["name"] == "retrieve_chunks"
    assert start.data["args"] == {"query": "photosynthesis"}

    cites = next(e for e in events if e.type == "citations")
    assert cites.data == [
        {"doc_id": "d1", "text": "leaves convert light", "page": None, "doc_name": None}
    ]

    # Persisted assistant message.
    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == "s1").one()
    assert msg.status == "complete"
    assert msg.content == "Hello world"
    assert msg.role == "assistant"

    # The persisted row carries the tool calls and citations so a resumed
    # session renders them (agent owns persistence).
    assert json.loads(msg.citations_json) == [
        {"doc_id": "d1", "text": "leaves convert light", "page": None, "doc_name": None}
    ]
    persisted_tcs = json.loads(msg.tool_calls_json)
    assert len(persisted_tcs) == 1
    assert persisted_tcs[0]["name"] == "retrieve_chunks"
    assert persisted_tcs[0]["status"] == "ok"

    # The tool turn is replayed to the model as the assistant message plus
    # the tool result.
    replay = fake_llm.stream_calls[1]["messages"]
    assert replay[-2]["tool_calls"] == [
        {
            "id": "tc_1",
            "type": "function",
            "function": {"name": "retrieve_chunks", "arguments": '{"query":"photosynthesis"}'},
        }
    ]
    assert replay[-1]["role"] == "tool"


@pytest.mark.asyncio
async def test_prefetched_citations_yielded_up_front(db_session, fake_llm):
    """F-56: ctx.prefetched_citations (server force-retrieve, Task 11) must be
    yielded as a citations event BEFORE the LLM loop runs, so the FE renders
    sources even when the model answers directly without calling
    retrieve_chunks this turn -- and the persisted message carries them too."""
    fake_llm.streams = [["answer"]]

    ctx = ToolContext(
        db=db_session,
        session_id="s_prefetch",
        user_id="u1",
        turn_started_at=datetime.now(timezone.utc),
        prefetched_citations=[
            Citation(doc_id="d1", text="prefetched excerpt", page=3, doc_name="notes.pdf")
        ],
    )

    events = await _drain(tutor.run_streaming([{"role": "user", "content": "explain"}], "sys", ctx))

    # The citations event fires up front -- before the first assistant_delta.
    first_relevant = next(e for e in events if e.type in ("citations", "assistant_delta"))
    assert first_relevant.type == "citations"
    assert first_relevant.data == [
        {"doc_id": "d1", "text": "prefetched excerpt", "page": 3, "doc_name": "notes.pdf"}
    ]
    assert [e.type for e in events].count("citations") == 1

    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == "s_prefetch").one()
    assert json.loads(msg.citations_json) == [
        {"doc_id": "d1", "text": "prefetched excerpt", "page": 3, "doc_name": "notes.pdf"}
    ]


@pytest.mark.asyncio
async def test_retrieve_chunks_dedupes_against_prefetched_citations(
    db_session, fake_llm, monkeypatch
):
    """F-56 fix: a same-turn retrieve_chunks call that overlaps with the
    server-prefetched citations must not duplicate the persisted/streamed
    citation list (identity: doc_id + text), and the citations event it
    emits must carry the FULL merged set -- the FE's setCitations REPLACES
    its list on each "citations" event (session.js), so a partial (new-only)
    yield would drop the prefetched entry from the live view."""
    fake_llm.streams = [[_retrieve("tc_1", "x")], ["final"]]
    result = ToolResult(
        ok=True,
        status="ok",
        error=None,
        data={
            "chunks": [
                {"doc_id": "d1", "text": "leaves convert light"},  # overlaps the prefetch
                {"doc_id": "d2", "text": "chlorophyll absorbs red and blue light"},
            ]
        },
    )
    monkeypatch.setattr("agent.tutor.tools.dispatch", MagicMock(return_value=result))

    ctx = ToolContext(
        db=db_session,
        session_id="s_dedup",
        user_id="u1",
        turn_started_at=datetime.now(timezone.utc),
        prefetched_citations=[Citation(doc_id="d1", text="leaves convert light")],
    )

    events = await _drain(tutor.run_streaming([{"role": "user", "content": "explain"}], "sys", ctx))

    citation_events = [e for e in events if e.type == "citations"]
    # One up-front (prefetch seed) + one from the tool-path merge.
    assert len(citation_events) == 2
    assert citation_events[0].data == [
        {"doc_id": "d1", "text": "leaves convert light", "page": None, "doc_name": None}
    ]
    # d1 is not duplicated; d2 is appended. The second event carries the
    # FULL set (not just d2) so the FE's replace-on-event semantics work.
    assert citation_events[1].data == [
        {"doc_id": "d1", "text": "leaves convert light", "page": None, "doc_name": None},
        {
            "doc_id": "d2",
            "text": "chlorophyll absorbs red and blue light",
            "page": None,
            "doc_name": None,
        },
    ]

    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == "s_dedup").one()
    persisted = json.loads(msg.citations_json)
    assert [c["doc_id"] for c in persisted] == ["d1", "d2"]


@pytest.mark.asyncio
async def test_run_streaming_persists_cancelled_on_cancel(db_session, user, fake_llm):
    """A cancel mid-stream persists the partial text as cancelled and reports
    the estimate the cut-short call settled."""
    fake_llm.streams = [["partial ", BLOCK]]
    fake_llm.partial_cost = Decimal("0.0007")

    received = await _run_and_cancel(_ctx(db_session, session_id="s2"))

    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == "s2").one()
    assert msg.status == "cancelled"
    assert "partial" in msg.content
    assert msg.cancelled_at is not None

    cancelled = next(e for e in received if e.type == "cancelled")
    assert cancelled.data["message_id"] == str(msg.id)
    assert cancelled.data["partial_content_chars"] == len("partial ")
    assert Decimal(cancelled.data["estimated_cost_usd"]) == Decimal("0.0007")
    # The estimate covers the cut-short call's own prompt and text, once.
    assert [(kind, text) for kind, _messages, text in fake_llm.estimates] == [
        ("stream", "partial ")
    ]
    assert cost_meter.current_spend(db_session, "u1") == Decimal("0.0007")


@pytest.mark.asyncio
async def test_cancel_during_tool_dispatch_reports_no_inflight_cost(
    db_session, user, fake_llm, monkeypatch
):
    """A cancel between calls cuts no call short: the finished call already
    settled its real price, and the cancelled event reports $0 in flight."""
    fake_llm.streams = [["Looking. ", _retrieve("tc_1", "a")]]
    fake_llm.cost = Decimal("0.0020")
    fake_llm.partial_cost = Decimal("0.5")
    started = threading.Event()
    release = threading.Event()

    def _slow_dispatch(name, args, ctx):
        started.set()
        release.wait(timeout=5)
        return ToolResult(ok=True, status="ok", error=None, data={"chunks": []})

    monkeypatch.setattr("agent.tutor.tools.dispatch", _slow_dispatch)
    received = []

    async def _consume():
        async for ev in tutor.run_streaming(
            [{"role": "user", "content": "go"}], "sys", _ctx(db_session, "s_mid")
        ):
            received.append(ev)

    task = asyncio.create_task(_consume())
    await asyncio.to_thread(started.wait, 5)
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.gather(task)

    cancelled = next(e for e in received if e.type == "cancelled")
    assert Decimal(cancelled.data["estimated_cost_usd"]) == Decimal("0")
    assert fake_llm.estimates == []
    assert cost_meter.current_spend(db_session, "u1") == Decimal("0.0020")


@pytest.mark.asyncio
async def test_malformed_tool_args_yield_error_not_dispatch(db_session, fake_llm, monkeypatch):
    """F-20a: a truncated/garbled streamed tool-args blob must fail loudly
    instead of dispatching {} (which would validate -- session_id is
    injected -- and silently report a no-op patch as ok)."""
    fake_llm.streams = [
        # Turn 1: a tool call whose accumulated arguments are truncated JSON.
        [tool_call("update_topic_profile", '{"session_id": "s1", "add_confirm', id="tc_1")],
        # Turn 2: plain text so the loop terminates.
        ["done"],
    ]
    dispatched = []
    monkeypatch.setattr(
        "agent.tutor.tools.dispatch",
        MagicMock(side_effect=lambda name, args, ctx: dispatched.append(name)),
    )

    ctx = _ctx(db_session, session_id="s1")
    events = await _drain(
        tutor.run_streaming([{"role": "user", "content": "update my profile"}], "sys", ctx)
    )

    done_events = [e for e in events if e.type == "tool_call_done"]
    assert done_events and done_events[0].data["status"] == "error"
    assert "malformed" in done_events[0].data["error"]
    assert dispatched == []
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_no_estimate_on_happy_path(db_session, fake_llm):
    """P3.2: an estimate (tokenization) is needed only for a call cut short.
    A finished call is priced from the provider's response instead."""
    fake_llm.streams = [["final answer"]]

    ctx = _ctx(db_session, session_id="s_no_token_counter")
    events = await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    assert events[-1].type == "done"
    assert fake_llm.estimates == []


@pytest.mark.asyncio
async def test_run_streaming_emits_error_on_cost_cap(db_session, user, fake_llm):
    """At the cap, the adapter gate refuses the first call: an error event
    with the cap fields, and the provider is never called."""
    cost_meter.record_cost(db_session, "u1", Decimal("3.10"))
    db_session.commit()

    ctx = _ctx(db_session, session_id="s3")
    events = await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    assert events[-1].type == "error"
    assert events[-1].data == {
        "code": "daily_cost_cap_reached",
        "used_usd": "3.1000",
        "soft_cap_usd": str(cost_meter.check_cap(db_session, "u1").soft_cap),
        "hard_cap_usd": str(cost_meter.check_cap(db_session, "u1").hard_cap),
    }
    assert fake_llm.stream_calls == []
    # Nothing streamed, so nothing is persisted.
    assert db_session.query(ChatMessage).filter(ChatMessage.session_id == "s3").count() == 0


@pytest.mark.asyncio
async def test_run_streaming_emits_cost_warning_when_soft_breached(
    db_session, fake_llm, monkeypatch
):
    """When the cost soft cap (90%) is breached after the final iteration, the
    stream emits a `cost_warning` event before `done` -- parity with the
    non-streaming X-Cost-Warning header path (which SSE cannot use, since its
    headers flush before the LLM runs and the spend is known).
    """
    cap = _cap(used=Decimal("1.95"), soft_breached=True)
    monkeypatch.setattr("agent.tutor.cost_meter.check_cap", MagicMock(return_value=cap))
    fake_llm.streams = [["final answer"]]

    ctx = _ctx(db_session, session_id="s_softcap")
    events = await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    types = [e.type for e in events]
    assert "cost_warning" in types
    assert types.index("cost_warning") < types.index("done")
    assert types[-1] == "done"

    cw = next(e for e in events if e.type == "cost_warning")
    assert cw.data == {
        "level": "soft",
        "used_usd": "1.95",
        "soft_cap_usd": "2.0",
        "urgent_cap_usd": "2.70",
        "hard_cap_usd": "3.0",
    }


@pytest.mark.asyncio
async def test_run_streaming_cost_warning_marks_urgent_level(db_session, fake_llm, monkeypatch):
    """When spend is in the urgent band (>= urgent_cap), the cost_warning
    event's level must be "urgent" instead of "soft"."""
    cap = _cap(used=Decimal("2.80"), soft_breached=True, urgent_breached=True)
    monkeypatch.setattr("agent.tutor.cost_meter.check_cap", MagicMock(return_value=cap))
    fake_llm.streams = [["final answer"]]

    ctx = _ctx(db_session, session_id="s_urgentcap")
    events = await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    cw = next(e for e in events if e.type == "cost_warning")
    assert cw.data["level"] == "urgent"


@pytest.mark.asyncio
async def test_run_streaming_no_cost_warning_when_under_soft_cap(db_session, fake_llm):
    """No cost_warning when the soft cap is not breached (default happy path)."""
    fake_llm.streams = [["ok"]]

    ctx = _ctx(db_session, session_id="s_nosoft")
    events = await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    assert "cost_warning" not in [e.type for e in events]
    assert events[-1].type == "done"


@pytest.mark.asyncio
async def test_run_streaming_stub_mode_chunks(db_session, fake_llm, monkeypatch):
    from agent._stub import stub_response

    monkeypatch.setattr(settings, "llm_stub", True)

    messages = [{"role": "user", "content": "hello there friend"}]
    ctx = _ctx(db_session, session_id="s4")
    events = await _drain(tutor.run_streaming(messages, "sys", ctx))

    deltas = [e for e in events if e.type == "assistant_delta"]
    assert len(deltas) >= 1
    assert events[-1].type == "done"

    joined = "".join(e.data["text"] for e in deltas)
    assert joined == stub_response(messages, "sys")

    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == "s4").one()
    assert msg.status == "complete"
    assert msg.content == stub_response(messages, "sys")
    assert fake_llm.stream_calls == []


@pytest.mark.asyncio
async def test_run_streaming_records_cost_on_tool_iterations(
    db_session, user, fake_llm, monkeypatch
):
    """Regression (review #1): cost must be recorded on EVERY billed iteration,
    including tool-dispatch iterations -- not only on the final text iteration,
    or tool-heavy turns could evade the daily cost cap."""
    fake_llm.streams = [[_retrieve("tc_1", "x")], ["done"]]
    fake_llm.cost = Decimal("0.01")
    monkeypatch.setattr(
        "agent.tutor.tools.dispatch",
        MagicMock(return_value=ToolResult(ok=True, status="ok", error=None, data={"chunks": []})),
    )

    ctx = _ctx(db_session, session_id="s_cost_iter")
    await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    assert cost_meter.current_spend(db_session, "u1") == Decimal("0.0200")
    assert db_session.query(LlmCallLog).filter(LlmCallLog.session_id == "s_cost_iter").count() == 2


@pytest.mark.asyncio
async def test_no_transaction_open_when_a_tool_starts(db_session, user, fake_llm, monkeypatch):
    """A tool can run for tens of seconds; the tutor's session must not hold
    an open transaction (and so a pooled connection, or a row lock) across
    it. Settlement happens in the adapter's own session, never ctx.db."""
    fake_llm.streams = [[_retrieve("tc_1", "x")], ["done"]]
    fake_llm.cost = Decimal("0.01")
    open_at_dispatch: list[bool] = []

    def dispatch(*_a, **_k):
        open_at_dispatch.append(db_session.in_transaction())
        return ToolResult(ok=True, status="ok", error=None, data={"chunks": []})

    monkeypatch.setattr("agent.tutor.tools.dispatch", dispatch)

    ctx = _ctx(db_session, session_id="s_cost_commit")
    await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    assert open_at_dispatch == [False]


@pytest.mark.asyncio
async def test_run_streaming_ask_check_question_dispatches_sibling_first(
    db_session, fake_llm, monkeypatch
):
    """ask_check_questions is turn-terminating and must be the LAST call
    dispatched. F-10: a sibling non-ask tool call streamed in the same
    response (e.g. a bundled record_learning_event) is legitimate and IS
    dispatched -- before the ask, not dropped."""
    fake_llm.streams = [
        [
            tool_call(
                "record_learning_event",
                {"session_id": "s1", "gap_tested": "x", "question": "q?", "correct": True},
                id="tc_0",
            ),
            tool_call(
                "ask_check_questions",
                {
                    "session_id": "s1",
                    "gap": "x",
                    "items": [
                        {
                            "question": "What is x?",
                            "options": ["yes", "no"],
                            "correct_index": 0,
                            "explanation": "Yes.",
                        }
                    ],
                },
                id="tc_1",
            ),
        ]
    ]
    dispatch = MagicMock(
        return_value=ToolResult(
            ok=True,
            status="ok",
            error=None,
            data={
                "gap": "x",
                "total": 1,
                "set_index": 1,
                "set_total": 1,
                "items": [{"question": "What is x?", "options": ["yes", "no"]}],
            },
        )
    )
    monkeypatch.setattr("agent.tutor.tools.dispatch", dispatch)

    # Seed user and session row for stamp_message_id lock to succeed
    db_session.add(User(id="u1"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_ask_skip",
            user_id="u1",
            topic="test",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()

    ctx = _ctx(db_session, session_id="s_ask_skip")
    events = await _drain(tutor.run_streaming([{"role": "user", "content": "quiz me"}], "sys", ctx))

    # F-10: the bundled non-ask call is dispatched first, then the ask last.
    dispatched = [c.args[0] for c in dispatch.call_args_list]
    assert dispatched == ["record_learning_event", "ask_check_questions"]

    types = [e.type for e in events]
    assert "check_question" in types
    assert types[-1] == "done"


@pytest.mark.asyncio
async def test_run_streaming_writes_llm_call_log_row(db_session, user, fake_llm):
    """After a streamed turn with nonzero cost, LlmCallLog gains a row with
    purpose == "chat" (suppress_check is unset, so it is not "followup")."""
    fake_llm.streams = [["hi there"]]
    fake_llm.cost = Decimal("0.0032")

    ctx = _ctx(db_session, session_id="s_call_log")
    await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    row = db_session.query(LlmCallLog).filter(LlmCallLog.session_id == "s_call_log").one()
    assert row.purpose == "chat"
    assert row.user_id == "u1"


@pytest.mark.asyncio
async def test_llm_exception_yields_error_event_and_persists_partial(db_session, fake_llm):
    """F-01: a non-cancel exception (provider 429/timeout, malformed chunk, tool
    crash) must surface as exactly one error SSE event -- not escape the
    generator and leave the client stuck in 'streaming' forever -- and the
    partial assistant text must be persisted with status='error'."""
    fake_llm.streams = [RuntimeError("provider blew up")]

    ctx = _ctx(db_session, session_id="s_llm_exception")
    events = await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    error_events = [e for e in events if e.type == "error"]
    assert len(error_events) == 1
    assert error_events[0].data["code"] == "llm_failed"

    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == "s_llm_exception").one()
    assert msg.status == "error"


@pytest.mark.asyncio
async def test_prune_superseded_excerpts_wired_into_loop(db_session, fake_llm, monkeypatch):
    """Integration (Task 7): prune_superseded_excerpts runs after each
    tool-dispatch iteration. Two same-turn retrieve_chunks calls (iterations 1
    and 2) followed by a final text iteration (3) must arrive at the third
    call with the FIRST retrieval's tool message stubbed and the SECOND
    (newest) retrieval's document_excerpt intact. The fake provider copies
    each message as it is sent, so a later prune cannot rewrite an earlier
    capture."""
    fake_llm.streams = [[_retrieve("tc_1", "a")], [_retrieve("tc_2", "b")], ["final answer"]]
    monkeypatch.setattr("agent.tutor.tools.dispatch", MagicMock(side_effect=_retrieval_dispatch))

    ctx = _ctx(db_session, session_id="s_prune")
    await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    assert len(fake_llm.stream_calls) == 3
    third_call_msgs = fake_llm.stream_calls[2]["messages"]
    tool_msgs = [
        m for m in third_call_msgs if m.get("role") == "tool" and m.get("name") == "retrieve_chunks"
    ]
    assert len(tool_msgs) == 2
    assert tool_msgs[0]["content"].startswith("[superseded retrieval:")
    assert "<document_excerpt" in tool_msgs[1]["content"]


@pytest.mark.asyncio
async def test_cancel_estimates_only_the_cut_short_call_as_sent(
    db_session, user, fake_llm, monkeypatch
):
    """Two retrieval rounds finish (each settled at its real price), then the
    third call is cancelled mid-stream. Only that call is estimated, once,
    from the prompt it was sent -- which already carries iteration 2's prune
    of round 1's excerpt -- plus only its own streamed text."""
    fake_llm.streams = [
        [_retrieve("tc_1", "a")],
        [_retrieve("tc_2", "b")],
        ["partial ", BLOCK],
    ]
    fake_llm.cost = Decimal("0.0010")
    fake_llm.partial_cost = Decimal("0.0007")
    monkeypatch.setattr("agent.tutor.tools.dispatch", MagicMock(side_effect=_retrieval_dispatch))

    await _run_and_cancel(_ctx(db_session, session_id="s_cancel_prune"))

    assert len(fake_llm.estimates) == 1
    kind, messages, text = fake_llm.estimates[0]
    assert (kind, text) == ("stream", "partial ")
    assert messages == fake_llm.stream_calls[2]["messages"]
    tc1 = next(m for m in messages if m.get("tool_call_id") == "tc_1")
    assert tc1["content"].startswith("[superseded retrieval:")
    assert cost_meter.current_spend(db_session, "u1") == Decimal("0.0027")


@pytest.mark.asyncio
async def test_error_mid_stream_bills_the_failed_call_once(db_session, user, fake_llm):
    """F-03/F-06, changed by #412: a mid-stream provider crash bills the
    started call once, an estimate of its prompt plus the text it streamed.
    The error arm no longer re-estimates the whole turn on top."""
    fake_llm.streams = [["partial ", RuntimeError("provider blew up mid-stream")]]
    fake_llm.partial_cost = Decimal("0.0009")

    ctx = _ctx(db_session, session_id="s_error_bill")
    events = await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    assert events[-1].type == "error"
    assert [(kind, text) for kind, _m, text in fake_llm.estimates] == [("stream", "partial ")]
    assert cost_meter.current_spend(db_session, "u1") == Decimal("0.0009")
    rows = db_session.query(LlmCallLog).filter(LlmCallLog.session_id == "s_error_bill").all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_stream_receives_tools_and_timeout(db_session, fake_llm):
    """F-06: a stuck provider connection must not hang the turn forever -- the
    call carries the configured LLM timeout, plus the tool list."""
    fake_llm.streams = [["hello world"]]

    ctx = _ctx(db_session, session_id="s_timeout")
    await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    call = fake_llm.stream_calls[0]
    assert call["timeout"] == settings.llm_timeout_s
    assert call["tools"] == tutor.tools.TOOLS
    assert call["tool_choice"] == "auto"


def test_summarize_labels_ignored_profile_patch():
    from agent.tutor import _summarize

    result = ToolResult(ok=True, status="ignored", data={"notes": ["inferred mastery ignored"]})
    assert "ignored" in _summarize("update_topic_profile", result).lower()


@pytest.mark.asyncio
async def test_no_open_transaction_during_llm_stream(db_session, fake_llm, monkeypatch):
    """B-10 (structural): the pooled DB connection must be released before the
    LLM stream begins. A read earlier in the turn autobegins a transaction on
    ctx.db; it must be committed before the stream opens, so the connection
    returns to the pool for the 10-60 s stream (Supabase transaction pooler
    ceiling)."""
    captured = {}
    open_stream = fake_llm.stream

    async def _spy_stream(*args, **kwargs):
        captured["open_txn"] = db_session.in_transaction()
        return await open_stream(*args, **kwargs)

    monkeypatch.setattr(fake_llm, "stream", _spy_stream)
    fake_llm.streams = [["hi"]]

    db_session.query(ChatMessage).count()  # autobegins, as the route's reads do
    assert db_session.in_transaction()

    ctx = _ctx(db_session, session_id="s_no_open_txn")
    await _drain(tutor.run_streaming([{"role": "user", "content": "hi"}], "sys", ctx))

    assert captured["open_txn"] is False


@pytest.mark.asyncio
async def test_cancel_mid_dispatch_drains_inflight_thread_before_persisting(
    db_session, fake_llm, monkeypatch
):
    """asyncio.to_thread cannot be interrupted. Cancelling the streaming task
    while a tool dispatch is running in its worker thread must NOT let the
    cancel arm touch ctx.db (persist the cancelled message) until that worker
    thread has actually finished -- otherwise the main thread and the
    still-running dispatch thread would both use the same (non-thread-safe)
    SQLAlchemy Session concurrently.

    The dispatch genuinely blocks a separate OS thread (threading.Event). The
    blocked thread is released only once the cancel arm has entered the
    drain, so no wall-clock sleep decides the order; the ordering list then
    proves the drain finished before the persist. If the drain is removed,
    the cancel arm never enters it and the test fails."""
    fake_llm.streams = [[tool_call("update_topic_profile", '{"session_id": "s1"}', id="tc_1")]]

    started = threading.Event()
    release = threading.Event()
    order: list[str] = []

    def _slow_dispatch(name, args, ctx):
        started.set()
        release.wait(timeout=5)
        order.append("dispatch_done")
        return ToolResult(ok=True, status="ok", error=None, data={})

    monkeypatch.setattr("agent.tutor.tools.dispatch", _slow_dispatch)

    drain_entered = asyncio.Event()
    orig_drain = tutor._drain_dispatch

    async def _spy_drain(dispatch_task, ctx):
        assert dispatch_task is not None and not dispatch_task.done()
        drain_entered.set()
        await orig_drain(dispatch_task, ctx)

    monkeypatch.setattr("agent.tutor._drain_dispatch", _spy_drain)

    orig_persist = tutor._persist_assistant_message

    def _spy_persist(*a, **k):
        order.append("persist_called")
        return orig_persist(*a, **k)

    monkeypatch.setattr("agent.tutor._persist_assistant_message", _spy_persist)

    ctx = _ctx(db_session, session_id="s1")
    received = []

    async def _consume():
        async for ev in tutor.run_streaming([{"role": "user", "content": "go"}], "sys", ctx):
            received.append(ev)

    task = asyncio.create_task(_consume())

    # Wait (off the event loop thread) until the dispatch thread has actually
    # started, so cancellation lands mid-dispatch, not before it.
    await asyncio.to_thread(started.wait, 5)
    assert started.is_set(), "dispatch never started"

    task.cancel()
    try:
        await asyncio.wait_for(drain_entered.wait(), timeout=5)
    finally:
        # Never leave the worker thread (or the task) behind on failure.
        release.set()
    assert order == [], "cancel arm must not run ahead of the in-flight dispatch"

    with pytest.raises(asyncio.CancelledError):
        await asyncio.gather(task)

    # The dispatch thread must have fully finished BEFORE the cancel arm
    # persisted the cancelled message.
    assert order == ["dispatch_done", "persist_called"]
    assert any(e.type == "cancelled" for e in received)

    msg = db_session.query(ChatMessage).filter(ChatMessage.session_id == "s1").one()
    assert msg.status == "cancelled"
