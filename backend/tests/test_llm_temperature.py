"""D2.1: explicit temperature on every LLM call, config-driven."""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.types import ToolContext
from config import settings
from contracts import TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from services import summary_service
from services.cost_meter import CapStatus


def test_temperature_defaults():
    assert settings.llm_temperature == 0.3
    assert settings.summary_temperature == 0.0


def _content_chunk(token):
    delta = SimpleNamespace(content=token, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _make_stream(*chunks):
    async def _gen():
        for c in chunks:
            yield c
    return _gen()


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


def _allow_cap(monkeypatch):
    cap = CapStatus(
        allowed=True,
        used=Decimal("0.0"),
        soft_breached=False,
        urgent_breached=False,
        soft_cap=Decimal("2.0"),
        urgent_cap=Decimal("2.70"),
        hard_cap=Decimal("3.0"),
    )
    monkeypatch.setattr("agent.tutor.cost_meter.check_cap", MagicMock(return_value=cap))


async def _drain(agen):
    return [ev async for ev in agen]


@pytest.mark.asyncio
async def test_tutor_acompletion_gets_llm_temperature(db_session, monkeypatch):
    # Mirror the setup of the first plain-content test in
    # backend/tests/test_tutor_stream.py (ToolContext construction, session
    # seeding, event draining) -- only the assertion below is new.
    _disable_stub(monkeypatch)
    _allow_cap(monkeypatch)

    from agent import tutor

    mock = AsyncMock(side_effect=[_make_stream(_content_chunk("hi"))])
    monkeypatch.setattr("agent.tutor.litellm.acompletion", mock)

    ctx = _ctx(db_session, session_id="s1")
    events = await _drain(
        tutor.run_streaming([{"role": "user", "content": "explain"}], "sys", ctx)
    )

    assert events[-1].type == "done"
    assert mock.call_args.kwargs["temperature"] == settings.llm_temperature


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
        db_session.add(
            ChatMessage(session_id=SESSION_ID, role="user", content=f"msg {i}")
        )
        db_session.add(
            ChatMessage(session_id=SESSION_ID, role="assistant", content=f"resp {i}")
        )
    db_session.commit()
    return session


def test_summary_acompletion_gets_summary_temperature(
    session_with_messages, db_session, monkeypatch
):
    # Mirror backend/tests/test_summary_service.py's fake_acompletion test
    # (session + messages seeding, generate_and_persist call), capturing
    # kwargs on the fake.
    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        msg = SimpleNamespace(content="a summary")
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    monkeypatch.setattr(
        "services.summary_service.litellm.acompletion", fake_acompletion
    )

    summary = asyncio.run(
        summary_service.generate_and_persist(db_session, session_with_messages)
    )
    assert summary == "a summary"
    assert captured["temperature"] == settings.summary_temperature


@pytest.mark.asyncio
async def test_rolling_summary_acompletion_gets_summary_temperature(
    db_session, monkeypatch
):
    # Mirror backend/tests/test_rolling_summary.py's session_with_messages
    # factory and update_rolling_summary drive, capturing kwargs on the fake.
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
        db_session.add(
            ChatMessage(session_id="s_roll_temp", role=role, content=f"msg {i}")
        )
    db_session.commit()

    monkeypatch.setattr(summary_service.settings, "llm_stub", False)

    captured = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        msg = SimpleNamespace(content="a rolling summary")
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    monkeypatch.setattr(summary_service.litellm, "acompletion", fake_acompletion)

    result = await summary_service.update_rolling_summary(db_session, "s_roll_temp")
    assert result == "a rolling summary"
    assert captured["temperature"] == settings.summary_temperature
