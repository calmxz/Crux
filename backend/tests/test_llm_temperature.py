"""D2.1: explicit temperature on every LLM call, config-driven."""

import asyncio
from datetime import datetime, timezone

import pytest

from agent.types import ToolContext
from config import settings
from contracts import TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from services import summary_service


def test_temperature_defaults():
    assert settings.llm_temperature == 0.3
    assert settings.summary_temperature == 0.0


def _ctx(db_session, session_id="s1"):
    return ToolContext(
        db=db_session,
        session_id=session_id,
        user_id="u1",
        turn_started_at=datetime.now(timezone.utc),
    )


def _disable_stub(monkeypatch):
    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")


async def _drain(agen):
    return [ev async for ev in agen]


@pytest.mark.asyncio
async def test_tutor_stream_gets_llm_temperature(db_session, monkeypatch, fake_llm):
    _disable_stub(monkeypatch)

    from agent import tutor

    fake_llm.streams = [["hi"]]

    ctx = _ctx(db_session, session_id="s1")
    events = await _drain(tutor.run_streaming([{"role": "user", "content": "explain"}], "sys", ctx))

    assert events[-1].type == "done"
    assert fake_llm.stream_calls[0]["temperature"] == settings.llm_temperature


USER_ID = "u_temp"
SESSION_ID = "s_temp"


@pytest.fixture
def session_with_messages(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    session = SessionModel(
        id=SESSION_ID,
        user_id=USER_ID,
        topic="sql",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(session)
    db_session.flush()
    for i in range(3):
        db_session.add(ChatMessage(session_id=SESSION_ID, role="user", content=f"msg {i}"))
        db_session.add(ChatMessage(session_id=SESSION_ID, role="assistant", content=f"resp {i}"))
    db_session.commit()
    return session


def test_summary_call_gets_summary_temperature(session_with_messages, db_session, fake_llm):
    fake_llm.replies = ["a summary"]

    summary = asyncio.run(summary_service.generate_and_persist(db_session, session_with_messages))
    assert summary == "a summary"
    assert fake_llm.complete_calls[0]["temperature"] == settings.summary_temperature


@pytest.mark.asyncio
async def test_rolling_summary_call_gets_summary_temperature(db_session, monkeypatch, fake_llm):
    # Mirror backend/tests/test_rolling_summary.py's session_with_messages
    # factory and update_rolling_summary drive; the fake provider records the call.
    db_session.add(User(id="u_roll_temp"))
    db_session.flush()
    session = SessionModel(
        id="s_roll_temp",
        user_id="u_roll_temp",
        topic="sql",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(session)
    db_session.flush()
    for i in range(30):
        role = "user" if i % 2 == 0 else "assistant"
        db_session.add(ChatMessage(session_id="s_roll_temp", role=role, content=f"msg {i}"))
    db_session.commit()

    monkeypatch.setattr(summary_service.settings, "llm_stub", False)
    fake_llm.replies = ["a rolling summary"]

    result = await summary_service.update_rolling_summary(db_session, "s_roll_temp")
    assert result == "a rolling summary"
    assert fake_llm.complete_calls[0]["temperature"] == settings.summary_temperature
