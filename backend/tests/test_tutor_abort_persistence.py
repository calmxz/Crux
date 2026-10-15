"""F-14: max_iters / mid-turn-cap aborts persist already-streamed text as a
'partial' assistant message; the F-01 error arm attaches an open batch."""

import asyncio

from sqlalchemy import select

from agent import tutor
from agent.types import ToolContext
from db.models import ChatMessage
from db.models import Session as SessionModel
from tests.conftest import tool_call


def _mk_session(db):
    s = SessionModel(id="s1", user_id="u1", topic="t")
    db.add(s)
    db.commit()
    return s


def _ctx(db, s):
    from datetime import datetime, timezone

    return ToolContext(
        db=db, session_id=s.id, user_id="u1", turn_started_at=datetime.now(timezone.utc)
    )


def test_max_iters_persists_partial(db_session, monkeypatch, fake_llm):
    s = _mk_session(db_session)
    monkeypatch.setattr(tutor.settings, "llm_stub", False)
    monkeypatch.setattr(tutor.settings, "gemini_api_key", "real")
    # One text token then one tool call: never a final answer, so the loop
    # exhausts max_iters.
    patch = {"add_confirmed_gap": "x", "evidence_type": "declared"}
    fake_llm.streams = [
        ["draft ", tool_call("update_topic_profile", patch, id=f"tc{i}")] for i in range(2)
    ]

    async def run():
        events = []
        async for ev in tutor.run_streaming(
            [{"role": "user", "content": "hi"}],
            "sys",
            _ctx(db_session, s),
            max_iters=2,
        ):
            events.append(ev)
        return events

    events = asyncio.run(run())
    assert events[-1].type == "error"
    assert events[-1].data["code"] == "max_iters_reached"
    row = db_session.execute(
        select(ChatMessage).where(ChatMessage.session_id == s.id, ChatMessage.role == "assistant")
    ).scalar_one()
    assert row.status == "partial"
    assert "draft" in row.content
