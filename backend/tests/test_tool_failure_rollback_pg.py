"""#569: a tool that raises cannot poison the rest of the turn on Postgres.

tools.dispatch turns any exception into a `tool_failed` ToolResult. On
Postgres a failed statement aborts the transaction, so without a rollback a
valid write later in the same batch fails with InFailedSqlTransaction, and a
failed flush makes the next iteration's commit() raise PendingRollbackError,
which ends the whole turn with `llm_failed`. Here scripted-model turns run
through tutor.run_streaming with patched tools that fail inside Postgres on
the turn's own session.

**Opt-in**: skipped unless `TEST_DATABASE_URL` is set. Run locally with
`scripts/pg_tests.sh tests/test_tool_failure_rollback_pg.py --no-cov`. Never
point it at a production database.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.orm import sessionmaker

from agent import tutor
from agent.types import ToolContext
from contracts import TopicProfile
from db.database import _normalized_url
from db.models import (
    ChatMessage,
    DailyCostLedger,
    LearningEvent,
    LlmCallLog,
    UsageCounter,
    User,
)
from db.models import Session as SessionModel
from lib import error_codes
from services import profile_service, retrieval_service
from tests.conftest import tool_call

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB,
    reason="TEST_DATABASE_URL not set - skipping live Postgres tool-failure test",
)

GAP = "outer joins"


@pytest.fixture(scope="module")
def engine():
    """prepare_threshold=None matches prod (Supabase pooler)."""
    eng = create_engine(_normalized_url(TEST_DB), connect_args={"prepare_threshold": None})
    yield eng
    eng.dispose()


@pytest.fixture
def seeded(engine, fake_llm, monkeypatch):
    """A unique user + session, with the adapter's gate and settlement on the
    same Postgres. Every row a turn writes is deleted on teardown, children
    first."""
    from services import llm

    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(llm, "session_factory", Session)
    uid = f"tool-pg-{uuid.uuid4().hex[:12]}"
    sid = f"tool-pg-s-{uuid.uuid4().hex[:12]}"
    with Session() as db:
        db.add(User(id=uid))
        db.flush()
        db.add(
            SessionModel(
                id=sid,
                user_id=uid,
                topic="sql",
                topic_profile_json=TopicProfile().model_dump_json(),
            )
        )
        db.commit()
    try:
        yield Session, uid, sid
    finally:
        with Session() as db:
            db.execute(delete(LlmCallLog).where(LlmCallLog.user_id == uid))
            db.execute(delete(LearningEvent).where(LearningEvent.session_id == sid))
            db.execute(delete(ChatMessage).where(ChatMessage.session_id == sid))
            db.execute(delete(DailyCostLedger).where(DailyCostLedger.user_id == uid))
            db.execute(delete(UsageCounter).where(UsageCounter.user_id == uid))
            db.execute(delete(SessionModel).where(SessionModel.id == sid))
            db.execute(delete(User).where(User.id == uid))
            db.commit()


def _failing_retrieve(db, ctx, args):
    """A retrieval that fails inside Postgres on the turn's own session."""
    db.execute(text("SELECT 1 / 0"))


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


async def test_failed_read_does_not_fail_a_later_write_in_the_same_batch(
    seeded, fake_llm, monkeypatch
):
    """Case A: the profile patch after a failed retrieval still lands."""
    Session, uid, sid = seeded
    monkeypatch.setattr(retrieval_service, "retrieve", _failing_retrieve)
    fake_llm.streams = [
        [
            tool_call("retrieve_chunks", {"query": "joins"}, id="c_ret"),
            tool_call("update_topic_profile", {"add_confirmed_gap": GAP}, id="c_prof"),
        ],
        ["Noted."],
    ]

    events = await _run_turn(Session, uid, sid)

    done = _done_by_id(events)
    assert done["c_ret"]["status"] == "error"
    assert done["c_prof"]["status"] == "ok"
    assert events[-1].type == "done"
    assert _assistant_status(Session, sid) == "complete"
    assert _tool_result_seen_by_model(fake_llm, "c_ret")["error"] == error_codes.TOOL_FAILED
    with Session() as db:
        profile = profile_service.load_profile(db, sid)
    assert profile_service.concept_names(profile.confirmed_gaps) == [GAP]


async def test_failed_flush_does_not_end_the_turn_in_error(seeded, fake_llm, monkeypatch):
    """Case B: a write tool's flush error is a tool failure, not a turn failure."""
    Session, uid, sid = seeded

    def duplicate_pk_patch(db, ctx, args):
        db.add(User(id=ctx.user_id))
        db.flush()

    monkeypatch.setattr(profile_service, "apply_patch", duplicate_pk_patch)
    fake_llm.streams = [
        [tool_call("update_topic_profile", {"add_confirmed_gap": GAP}, id="c_prof")],
        ["Noted."],
    ]

    events = await _run_turn(Session, uid, sid)

    done = _done_by_id(events)
    assert (done["c_prof"]["status"], done["c_prof"]["error"]) == (
        "error",
        error_codes.TOOL_FAILED,
    )
    assert events[-1].type == "done"
    assert _assistant_status(Session, sid) == "complete"
    assert _tool_result_seen_by_model(fake_llm, "c_prof")["error"] == error_codes.TOOL_FAILED


async def test_lone_failed_read_still_ends_done(seeded, fake_llm, monkeypatch):
    """Case C: a failed read alone in its batch ends the turn `done`."""
    Session, uid, sid = seeded
    monkeypatch.setattr(retrieval_service, "retrieve", _failing_retrieve)
    fake_llm.streams = [
        [tool_call("retrieve_chunks", {"query": "joins"}, id="c_ret")],
        ["No sources."],
    ]

    events = await _run_turn(Session, uid, sid)

    assert events[-1].type == "done"
    assert _assistant_status(Session, sid) == "complete"
    assert _tool_result_seen_by_model(fake_llm, "c_ret")["error"] == error_codes.TOOL_FAILED
