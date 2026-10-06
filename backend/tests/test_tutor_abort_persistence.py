"""F-14: max_iters / mid-turn-cap aborts persist already-streamed text as a
'partial' assistant message; the F-01 error arm attaches an open batch."""
import asyncio
import json

from sqlalchemy import select

from agent import tutor
from agent.types import ToolContext
from db.models import ChatMessage
from db.models import Session as SessionModel


def _mk_session(db):
    s = SessionModel(id="s1", user_id="u1", topic="t")
    db.add(s)
    db.commit()
    return s


def _ctx(db, s):
    from datetime import datetime, timezone
    return ToolContext(db=db, session_id=s.id, user_id="u1",
                       turn_started_at=datetime.now(timezone.utc))


class _FakeDelta:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _FakeChunk:
    def __init__(self, delta):
        self.choices = [type("C", (), {"delta": delta})()]


class _FakeStream:
    """Async iterator that streams one text token then one tool-call frag so
    the loop never produces a final answer and exhausts max_iters."""
    def __init__(self):
        self._items = [
            _FakeChunk(_FakeDelta(content="draft ")),
            _FakeChunk(_FakeDelta(tool_calls=[type("T", (), {
                "index": 0, "id": "tc1",
                "function": type("F", (), {
                    "name": "update_topic_profile",
                    "arguments": json.dumps({"add_confirmed_gap": "x",
                                             "evidence_type": "declared"}),
                })(),
            })()])),
        ]

    def __aiter__(self):
        self._i = iter(self._items)
        return self

    async def __anext__(self):
        try:
            return next(self._i)
        except StopIteration:
            raise StopAsyncIteration from None


def test_max_iters_persists_partial(db_session, monkeypatch):
    s = _mk_session(db_session)
    monkeypatch.setattr(tutor.settings, "llm_stub", False)
    monkeypatch.setattr(tutor.settings, "gemini_api_key", "real")

    async def fake_acompletion(**kwargs):
        return _FakeStream()

    monkeypatch.setattr(tutor.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(tutor.litellm, "stream_chunk_builder", lambda *a, **k: None)
    monkeypatch.setattr(tutor.litellm, "completion_cost", lambda **k: 0.0)
    monkeypatch.setattr(tutor.litellm, "token_counter", lambda **k: 1)

    async def run():
        events = []
        async for ev in tutor.run_streaming(
            [{"role": "user", "content": "hi"}], "sys", _ctx(db_session, s),
            max_iters=2,
        ):
            events.append(ev)
        return events

    events = asyncio.run(run())
    assert events[-1].type == "error"
    assert events[-1].data["code"] == "max_iters_reached"
    row = db_session.execute(
        select(ChatMessage).where(
            ChatMessage.session_id == s.id, ChatMessage.role == "assistant"
        )
    ).scalar_one()
    assert row.status == "partial"
    assert "draft" in row.content
