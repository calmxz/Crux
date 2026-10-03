"""F-11: async handlers must not run their synchronous DB work on the event
loop.

`create_session`, `end_session`, `complete_check` and `chat_stream`
(_prepare_turn) stay `async` -- they await LLM/summary/stream work -- so every
synchronous DB segment inside them has to go through
`starlette.concurrency.run_in_threadpool`. These tests spy on the module-level
`run_in_threadpool` name in each route module (the name bound by
`from starlette.concurrency import run_in_threadpool`) and assert each handler
actually hands work to a worker thread, while still running it for real so the
surrounding behaviour assertions stay honest.
"""

from datetime import datetime, timezone

import pytest
import starlette.concurrency as _sc

from agent.stream_events import StreamEvent
from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from services import check_question_service

USER_ID = "u_tp_1"
SESSION_ID = "s_tp_1"
AUTH_HEADERS = {"Authorization": f"Bearer test-{USER_ID}"}


@pytest.fixture
def spy(monkeypatch):
    """Patch run_in_threadpool in both route modules with a pass-through spy."""
    calls: list[str] = []
    real = _sc.run_in_threadpool

    async def spied(func, *args, **kwargs):
        calls.append(getattr(func, "__name__", repr(func)))
        return await real(func, *args, **kwargs)

    for module in ("routes.sessions", "routes.chat"):
        monkeypatch.setattr(f"{module}.run_in_threadpool", spied)
    return calls


@pytest.fixture
def seeded_session(db_session):
    db_session.add(User(id=USER_ID))
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="bio",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()


def test_create_session_uses_threadpool(client, db_session, spy):
    db_session.add(User(id=USER_ID))
    db_session.commit()
    r = client.post(
        "/api/sessions",
        json={"user_id": USER_ID, "topic": "sql joins", "seed_mode": "fresh"},
    )
    assert r.status_code == 201, r.text
    assert calls_nonempty(spy)


def test_end_session_uses_threadpool(
    client, db_session, seeded_session, spy, mock_litellm, llm_text, monkeypatch
):
    async def fake_acompletion(**kwargs):
        return llm_text("wrapped up")

    monkeypatch.setattr(
        "services.summary_service.litellm.acompletion", fake_acompletion
    )
    r = client.post(f"/api/sessions/{SESSION_ID}/end?user_id={USER_ID}")
    assert r.status_code == 200, r.text
    assert calls_nonempty(spy)


def test_complete_check_uses_threadpool(
    client, db_session, seeded_session, spy, monkeypatch
):
    ctx = ToolContext(
        db=db_session,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    check_question_service.register(
        db_session,
        ctx,
        AskCheckQuestionsArgs(
            set_index=1, set_total=1,
            session_id=SESSION_ID,
            gap="atp",
            items=[
                {
                    "question": "Q1?",
                    "options": ["a", "b"],
                    "correct_index": 0,
                    "explanation": "a.",
                }
            ],
        ),
    )
    check_question_service.answer(db_session, SESSION_ID, index=0, selected_index=0)

    async def fake_run_streaming(messages, system_prompt, tool_ctx):
        msg = ChatMessage(
            session_id=SESSION_ID, role="assistant", content="Nice work"
        )
        tool_ctx.db.add(msg)
        tool_ctx.db.commit()
        yield StreamEvent("done", {"message_id": str(msg.id)})

    monkeypatch.setattr("routes.sessions.tutor.run_streaming", fake_run_streaming)

    r = client.post(f"/api/sessions/{SESSION_ID}/check/complete?user_id={USER_ID}")
    assert r.status_code == 200, r.text
    assert calls_nonempty(spy)


def test_chat_stream_prepare_uses_threadpool(
    client, db_session, seeded_session, spy, monkeypatch
):
    async def fake_run_streaming(messages, system_prompt, tool_ctx):
        yield StreamEvent("done", {"message_id": "1"})

    monkeypatch.setattr("routes.chat.tutor.run_streaming", fake_run_streaming)

    r = client.post(
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "hi"},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 200, r.text
    assert calls_nonempty(spy)


def calls_nonempty(calls):
    """Readable failure message listing what (if anything) was threadpooled."""
    assert calls, "handler ran all of its synchronous DB work on the event loop"
    return True
