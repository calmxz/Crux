"""P3.4: debug_timing flag emits prepare/first-token/end-session timings."""

import logging

import pytest

from config import settings
from contracts import TopicProfile
from db.models import Session as SessionModel
from db.models import User

SESSION_ID = "s_debug_timing"
USER_ID = "u_debug_timing"
AUTH_HEADERS = {"Authorization": f"Bearer test-{USER_ID}"}


@pytest.fixture
def seeded_session_fixture(db_session):
    """Seed a User + Session so /chat/stream and /sessions/{id}/end have a
    valid target. Mirrors the seed_session pattern in test_chat.py."""
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()


def _post_stream(client, session_id=SESSION_ID, message="hello"):
    """POST /api/chat/stream and drain the SSE body. Returns (status, body).
    Copied from test_chat.py's streaming-turn client pattern."""
    lines = []
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": session_id, "message": message},
        headers=AUTH_HEADERS,
    ) as resp:
        status = resp.status_code
        if status == 200:
            for line in resp.iter_lines():
                lines.append(line)
    return status, "\n".join(lines)


def test_debug_timing_defaults_off():
    assert settings.debug_timing is False


def test_chat_stream_logs_timing_when_enabled(client, caplog, monkeypatch, seeded_session_fixture):
    monkeypatch.setattr(settings, "debug_timing", True)
    monkeypatch.setattr(settings, "llm_stub", True)
    with caplog.at_level(logging.INFO, logger="routes.chat"):
        status, body = _post_stream(client, message="hi")
    assert status == 200
    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "prepare_ms=" in joined and "first_token_ms=" in joined


def test_chat_stream_logs_nothing_when_disabled(client, caplog, monkeypatch, seeded_session_fixture):
    monkeypatch.setattr(settings, "llm_stub", True)
    with caplog.at_level(logging.INFO, logger="routes.chat"):
        status, body = _post_stream(client, message="hi")
    assert status == 200
    assert "prepare_ms=" not in " ".join(r.getMessage() for r in caplog.records)


def test_end_session_logs_timing_when_enabled(client, caplog, monkeypatch, seeded_session_fixture):
    monkeypatch.setattr(settings, "debug_timing", True)
    monkeypatch.setattr(settings, "llm_stub", True)
    with caplog.at_level(logging.INFO, logger="routes.sessions"):
        r = client.post(f"/api/sessions/{SESSION_ID}/end", headers=AUTH_HEADERS)
    assert r.status_code == 200, r.text
    joined = " ".join(rec.getMessage() for rec in caplog.records)
    assert "end_session timing total_ms=" in joined


def test_end_session_logs_nothing_when_disabled(client, caplog, monkeypatch, seeded_session_fixture):
    monkeypatch.setattr(settings, "llm_stub", True)
    with caplog.at_level(logging.INFO, logger="routes.sessions"):
        r = client.post(f"/api/sessions/{SESSION_ID}/end", headers=AUTH_HEADERS)
    assert r.status_code == 200, r.text
    joined = " ".join(rec.getMessage() for rec in caplog.records)
    assert "end_session timing total_ms=" not in joined


def test_end_session_logs_timing_on_already_ended(client, caplog, monkeypatch, seeded_session_fixture):
    """The timing log lives in a finally, so the already-ended early return
    still emits it."""
    monkeypatch.setattr(settings, "debug_timing", True)
    monkeypatch.setattr(settings, "llm_stub", True)
    first = client.post(f"/api/sessions/{SESSION_ID}/end", headers=AUTH_HEADERS)
    assert first.status_code == 200, first.text
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="routes.sessions"):
        r = client.post(f"/api/sessions/{SESSION_ID}/end", headers=AUTH_HEADERS)
    assert r.status_code == 200, r.text
    joined = " ".join(rec.getMessage() for rec in caplog.records)
    assert "end_session timing total_ms=" in joined
