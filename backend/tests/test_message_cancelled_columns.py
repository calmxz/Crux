"""Tests for chat_messages.status + cancelled_at columns (Task 10).

Validates model-derived schema via in-memory SQLite — no live DB required.
"""
import uuid  # used for session_id generation

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

import db.models  # noqa: F401 — ensures all models are registered with Base.metadata
from db.database import Base


def _make_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


def _columns() -> dict:
    engine = _make_engine()
    insp = inspect(engine)
    return {c["name"]: c for c in insp.get_columns("chat_messages")}


def test_message_has_status_column():
    cols = _columns()
    assert "status" in cols, "chat_messages.status column is missing"
    assert cols["status"]["nullable"] is False, "status must be NOT NULL"


def test_message_has_cancelled_at_column():
    cols = _columns()
    assert "cancelled_at" in cols, "chat_messages.cancelled_at column is missing"
    assert cols["cancelled_at"]["nullable"] is True, "cancelled_at must be nullable"


def test_status_server_default_is_complete():
    """Inserting a row without an explicit status must default to 'complete'."""
    engine = _make_engine()
    session_id = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO chat_messages"
                " (session_id, role, content, tool_calls_json, citations_json, created_at)"
                " VALUES (:session_id, :role, :content, :tc, :ci, :created_at)"
            ),
            {
                "session_id": session_id,
                "role": "user",
                "content": "hello",
                "tc": "[]",
                "ci": "[]",
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        )
        conn.commit()
        row = conn.execute(
            text("SELECT status FROM chat_messages ORDER BY id DESC LIMIT 1"),
        ).fetchone()
    assert row is not None
    assert row[0] == "complete", f"Expected server_default 'complete', got {row[0]!r}"


def test_status_check_constraint_rejects_invalid():
    """Inserting a row with status='bogus' must raise IntegrityError."""
    engine = _make_engine()
    session_id = str(uuid.uuid4())
    with pytest.raises(IntegrityError):
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO chat_messages"
                    " (session_id, role, content, tool_calls_json, citations_json,"
                    "  created_at, status)"
                    " VALUES (:session_id, :role, :content, :tc, :ci, :created_at, :status)"
                ),
                {
                    "session_id": session_id,
                    "role": "user",
                    "content": "hello",
                    "tc": "[]",
                    "ci": "[]",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "status": "bogus",
                },
            )
            conn.commit()
