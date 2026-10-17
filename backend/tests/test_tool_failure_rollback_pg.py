"""#569: a failed tool cannot poison the rest of the turn on Postgres.

On Postgres a failed statement aborts the transaction. Unless it is rolled
back, a valid write later in the same batch fails with
InFailedSqlTransaction, and a failed flush makes the next iteration's
commit() raise PendingRollbackError, which ends the whole turn with
`llm_failed`. A tool fails either by raising (tools.dispatch turns that into
`tool_failed`) or by swallowing the error itself (retrieve_chunks returns
`retrieval_failed`). Here scripted-model turns run through
tutor.run_streaming with patched code that fails inside Postgres on the
turn's own session.

**Opt-in**: skipped unless `TEST_DATABASE_URL` is set. Run locally with
`scripts/pg_tests.sh tests/test_tool_failure_rollback_pg.py --no-cov`. Never
point it at a production database.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import object_session

from agent import tutor
from agent.types import ToolContext
from contracts import TopicProfile
from db.models import ChatMessage, Document, User
from db.models import Session as SessionModel
from lib import error_codes
from services import check_service, pgvector_store, profile_service, retrieval_service
from tests.conftest import tool_call

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB,
    reason="TEST_DATABASE_URL not set - skipping live Postgres tool-failure test",
)

GAP = "outer joins"


@pytest.fixture
def seeded(pg_seed, fake_llm, monkeypatch):
    """A unique user + session, with the adapter's gate and settlement on the
    same Postgres. Removed by the shared teardown (conftest pg_seed)."""
    from services import llm

    monkeypatch.setattr(llm, "session_factory", pg_seed.Session)
    return pg_seed("tool-pg", topic="sql", topic_profile_json=TopicProfile().model_dump_json())


def _failing(calls: list):
    """A stand-in that fails inside Postgres on the caller's session."""

    def _fail(db, *a, **kw):
        calls.append(True)
        db.execute(text("SELECT 1 / 0"))

    return _fail


async def _run_turn(Session, uid, sid):
    with Session() as db:
        ctx = ToolContext(
            db=db, session_id=sid, user_id=uid, turn_started_at=datetime.now(timezone.utc)
        )
        return [
            ev
            async for ev in tutor.run_streaming(
                [{"role": "user", "content": "explain joins"}], "sys", ctx
            )
        ]


def _done_by_id(events) -> dict[str, dict]:
    return {ev.data["id"]: ev.data for ev in events if ev.type == "tool_call_done"}


def _tool_result_seen_by_model(fake_llm, call_id: str) -> dict:
    """The tool message the second model call received for `call_id`."""
    [msg] = [
        m
        for m in fake_llm.stream_calls[1]["messages"]
        if m.get("role") == "tool" and m.get("tool_call_id") == call_id
    ]
    return json.loads(msg["content"])


def _assistant_status(Session, sid) -> str:
    with Session() as db:
        return db.execute(
            select(ChatMessage.status).where(
                ChatMessage.session_id == sid, ChatMessage.role == "assistant"
            )
        ).scalar_one()


def _confirmed_gaps(Session, sid) -> list[str]:
    with Session() as db:
        profile = profile_service.load_profile(db, sid)
    return profile_service.concept_names(profile.confirmed_gaps)


def _retrieve_then_patch_batch():
    return [
        [
            tool_call("retrieve_chunks", {"query": "joins"}, id="c_ret"),
            tool_call("update_topic_profile", {"add_confirmed_gap": GAP}, id="c_prof"),
        ],
        ["Noted."],
    ]


async def test_raising_read_does_not_fail_a_later_write_in_the_same_batch(
    seeded, fake_llm, monkeypatch, caplog
):
    """Case A: the profile patch after a retrieval that raises still lands."""
    Session, uid, sid = seeded
    calls: list = []
    monkeypatch.setattr(retrieval_service, "retrieve", _failing(calls))
    fake_llm.streams = _retrieve_then_patch_batch()

    events = await _run_turn(Session, uid, sid)

    assert calls == [True]
    done = _done_by_id(events)
    assert done["c_ret"]["status"] == "error"
    assert done["c_prof"]["status"] == "ok"
    assert events[-1].type == "done"
    assert _assistant_status(Session, sid) == "complete"
    assert _tool_result_seen_by_model(fake_llm, "c_ret")["error"] == error_codes.TOOL_FAILED
    assert _confirmed_gaps(Session, sid) == [GAP]
    assert "tool dispatch failed" in caplog.text


async def test_swallowed_retrieval_error_does_not_fail_a_later_write(
    seeded, fake_llm, monkeypatch, caplog
):
    """Case A through the real retrieve: it catches its own vector-query
    failure and returns `retrieval_failed`, so dispatch never sees it."""
    Session, uid, sid = seeded
    with Session() as db:
        db.add(Document(session_id=sid, filename="ref.txt", status="ready"))
        db.commit()
    calls: list = []
    monkeypatch.setattr(pgvector_store, "query_chunks", _failing(calls))
    fake_llm.streams = _retrieve_then_patch_batch()

    events = await _run_turn(Session, uid, sid)

    assert calls == [True]
    done = _done_by_id(events)
    assert (done["c_ret"]["status"], done["c_ret"]["error"]) == ("error", "retrieval_failed")
    assert done["c_prof"]["status"] == "ok"
    assert events[-1].type == "done"
    assert _assistant_status(Session, sid) == "complete"
    assert _tool_result_seen_by_model(fake_llm, "c_ret")["error"] == "retrieval_failed"
    assert _confirmed_gaps(Session, sid) == [GAP]
    assert "retrieval failed" in caplog.text


async def test_failed_flush_does_not_end_the_turn_in_error(seeded, fake_llm, monkeypatch, caplog):
    """Case B: a write tool's flush error is a tool failure, not a turn failure."""
    Session, uid, sid = seeded
    calls: list = []

    def duplicate_pk_patch(db, ctx, args):
        calls.append(args.add_confirmed_gap)
        db.add(User(id=ctx.user_id))
        db.flush()

    monkeypatch.setattr(profile_service, "apply_patch", duplicate_pk_patch)
    fake_llm.streams = [
        [tool_call("update_topic_profile", {"add_confirmed_gap": GAP}, id="c_prof")],
        ["Noted."],
    ]

    events = await _run_turn(Session, uid, sid)

    assert calls == [GAP]
    done = _done_by_id(events)
    assert (done["c_prof"]["status"], done["c_prof"]["error"]) == (
        "error",
        error_codes.TOOL_FAILED,
    )
    assert events[-1].type == "done"
    assert _assistant_status(Session, sid) == "complete"
    assert _tool_result_seen_by_model(fake_llm, "c_prof")["error"] == error_codes.TOOL_FAILED
    assert "tool dispatch failed" in caplog.text


async def test_check_register_failing_under_the_row_lock_does_not_end_the_turn_in_error(
    seeded, fake_llm, monkeypatch, caplog
):
    """register raises a non-CheckError while it holds the session row lock;
    _locked leaves that transaction to the caller, and dispatch rolls it back
    (the check module's docstring relies on this)."""
    Session, uid, sid = seeded
    calls: list = []

    def duplicate_pk_write(row, pc):
        calls.append(pc["gap"])
        db = object_session(row)
        db.add(User(id=row.user_id))
        db.flush()

    monkeypatch.setattr(check_service, "_write_open_set", duplicate_pk_write)
    ask = {
        "set_index": 1,
        "set_total": 1,
        "gap": GAP,
        "items": [
            {
                "question": "Which join keeps unmatched left rows?",
                "options": ["LEFT JOIN", "INNER JOIN"],
                "correct_index": 0,
                "explanation": "LEFT JOIN keeps every left row.",
            }
        ],
    }
    fake_llm.streams = [
        [tool_call("ask_check_questions", ask, id="c_ask")],
        ["Let us keep going."],
    ]

    events = await _run_turn(Session, uid, sid)

    assert calls == [GAP]
    # Postgres rejected the INSERT, so the server-side transaction aborted.
    assert any("UniqueViolation" in r.getMessage() for r in caplog.records)
    done = _done_by_id(events)
    assert (done["c_ask"]["status"], done["c_ask"]["error"]) == (
        "error",
        error_codes.TOOL_FAILED,
    )
    assert not [ev for ev in events if ev.type == "check_question"]
    assert events[-1].type == "done"
    assert _assistant_status(Session, sid) == "complete"
    assert _tool_result_seen_by_model(fake_llm, "c_ask")["error"] == error_codes.TOOL_FAILED
    with Session() as db:
        row = db.get(SessionModel, sid)
        # register writes the Check pointer before the open Set; neither lands.
        assert (row.current_check_json, row.pending_check_json) == (None, None)


async def test_lone_failed_read_still_ends_done(seeded, fake_llm, monkeypatch, caplog):
    """Case C, already correct before #569 and pinned so it stays so: a
    failed read alone in its batch ends the turn `done` (the loop's next
    commit ends the aborted transaction)."""
    Session, uid, sid = seeded
    calls: list = []
    monkeypatch.setattr(retrieval_service, "retrieve", _failing(calls))
    fake_llm.streams = [
        [tool_call("retrieve_chunks", {"query": "joins"}, id="c_ret")],
        ["No sources."],
    ]

    events = await _run_turn(Session, uid, sid)

    assert calls == [True]
    assert events[-1].type == "done"
    assert _assistant_status(Session, sid) == "complete"
    assert _tool_result_seen_by_model(fake_llm, "c_ret")["error"] == error_codes.TOOL_FAILED
    assert "tool dispatch failed" in caplog.text
