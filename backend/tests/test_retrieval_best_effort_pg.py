"""#567: the chat pre-flight's retrieval reads are best-effort on Postgres too.

semantic_fallback_required and prefetch_for_prompt swallow any failure and
return their fallback. On Postgres a swallowed SQL error still aborts the
request's transaction, and the user-message persist that follows then raises
InFailedSqlTransaction (HTTP 500). Here the patched reads issue real failing
SQL on the request's own session, which is what a vector dimension mismatch
or schema drift would do.

**Opt-in**: skipped unless `TEST_DATABASE_URL` is set. Run locally with
`scripts/pg_tests.sh tests/test_retrieval_best_effort_pg.py --no-cov`. Never
point it at a production database.
"""

from __future__ import annotations

import json
import logging
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.orm import sessionmaker

from config import settings
from db.database import _normalized_url, get_db
from db.models import ChatMessage, DailyCostLedger, Document, LlmCallLog, UsageCounter, User
from db.models import Session as SessionModel
from lib import keyword_index
from main import app
from services import summary_service, velocity_limit
from services.auth import current_user_id
from tests.conftest import _fake_current_user_id

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB,
    reason="TEST_DATABASE_URL not set - skipping live Postgres retrieval test",
)

MESSAGE = "explain photosynthesis"


@pytest.fixture(scope="module")
def engine():
    """prepare_threshold=None matches prod (Supabase pooler)."""
    eng = create_engine(_normalized_url(TEST_DB), connect_args={"prepare_threshold": None})
    yield eng
    eng.dispose()


def _seed(engine, kw_stems: list[str]):
    """A unique user + session with one ready document. Every row a turn
    writes is deleted on teardown, children first."""
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    uid = f"ret-pg-{uuid.uuid4().hex[:12]}"
    sid = f"ret-pg-s-{uuid.uuid4().hex[:12]}"
    with Session() as db:
        db.add(User(id=uid))
        db.flush()
        db.add(
            SessionModel(id=sid, user_id=uid, topic="biology", kw_index_json=json.dumps(kw_stems))
        )
        db.flush()
        db.add(Document(session_id=sid, filename="notes.pdf", status="ready"))
        db.commit()

    def cleanup():
        with Session() as db:
            db.execute(delete(LlmCallLog).where(LlmCallLog.user_id == uid))
            db.execute(delete(ChatMessage).where(ChatMessage.session_id == sid))
            db.execute(delete(Document).where(Document.session_id == sid))
            db.execute(delete(DailyCostLedger).where(DailyCostLedger.user_id == uid))
            db.execute(delete(UsageCounter).where(UsageCounter.user_id == uid))
            db.execute(delete(SessionModel).where(SessionModel.id == sid))
            db.execute(delete(User).where(User.id == uid))
            db.commit()

    return Session, uid, sid, cleanup


@pytest.fixture
def lexical_miss(engine):
    """kw index disjoint from MESSAGE: the lexical gate misses, so the
    semantic fallback runs."""
    Session, uid, sid, cleanup = _seed(engine, ["chlorophyl"])
    assert not keyword_index.match_required(MESSAGE, ["chlorophyl"])
    try:
        yield Session, uid, sid
    finally:
        cleanup()


@pytest.fixture
def lexical_hit(engine):
    """kw index built from MESSAGE: the lexical gate hits, so the turn is
    REQUIRED and the prefetch runs."""
    stems = sorted(keyword_index.build_from_text(MESSAGE))
    Session, uid, sid, cleanup = _seed(engine, stems)
    assert keyword_index.match_required(MESSAGE, stems)
    try:
        yield Session, uid, sid
    finally:
        cleanup()


def _failing(calls: list):
    """A stand-in read that fails inside Postgres on the caller's session."""

    def _fail(db, *a, **kw):
        calls.append(True)
        db.execute(text("SELECT 1 / 0"))

    return _fail


def _stream_turn(Session, uid, sid, monkeypatch) -> tuple[int, str]:
    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    # The response's BackgroundTask opens SessionLocal() on the default URL.
    async def no_rolling_summary(db, session_id):
        return None

    monkeypatch.setattr(summary_service, "update_rolling_summary", no_rolling_summary)
    monkeypatch.setattr(settings, "llm_stub", True)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user_id] = _fake_current_user_id
    velocity_limit.reset()
    try:
        with TestClient(app).stream(
            "POST",
            "/api/chat/stream",
            json={"session_id": sid, "message": MESSAGE},
            headers={"Authorization": f"Bearer test-{uid}"},
        ) as resp:
            return resp.status_code, "\n".join(resp.iter_lines())
    finally:
        app.dependency_overrides.clear()
        velocity_limit.reset()


def _assert_turn_completed(Session, sid, status, body):
    assert status == 200, body
    assert "event: done" in body
    with Session() as db:
        roles = (
            db.execute(select(ChatMessage.role).where(ChatMessage.session_id == sid))
            .scalars()
            .all()
        )
    assert sorted(roles) == ["assistant", "user"]


def test_failed_ready_check_in_semantic_fallback(lexical_miss, monkeypatch, caplog):
    Session, uid, sid = lexical_miss
    calls: list = []
    monkeypatch.setattr("services.documents_service.has_ready_document", _failing(calls))

    with caplog.at_level(logging.WARNING, logger="services.retrieval_service"):
        status, body = _stream_turn(Session, uid, sid, monkeypatch)

    assert calls, "the failing read never ran"
    _assert_turn_completed(Session, sid, status, body)
    assert "semantic fallback check failed; keeping OPTIONAL" in caplog.text


def test_failed_centroid_read_in_semantic_fallback(lexical_miss, monkeypatch, caplog):
    Session, uid, sid = lexical_miss
    calls: list = []
    monkeypatch.setattr("services.retrieval_service._compute_centroid", _failing(calls))

    with caplog.at_level(logging.WARNING, logger="services.retrieval_service"):
        status, body = _stream_turn(Session, uid, sid, monkeypatch)

    assert calls, "the failing read never ran"
    _assert_turn_completed(Session, sid, status, body)
    assert "semantic fallback check failed; keeping OPTIONAL" in caplog.text


def test_failed_ready_check_in_prefetch(lexical_hit, monkeypatch, caplog):
    Session, uid, sid = lexical_hit
    calls: list = []
    monkeypatch.setattr("services.documents_service.has_ready_document", _failing(calls))

    with caplog.at_level(logging.WARNING, logger="services.retrieval_service"):
        status, body = _stream_turn(Session, uid, sid, monkeypatch)

    assert calls, "the failing read never ran"
    _assert_turn_completed(Session, sid, status, body)
    assert "prefetch_for_prompt failed; falling back to advisory flag" in caplog.text


def test_failed_chunk_search_in_prefetch(lexical_hit, monkeypatch, caplog):
    Session, uid, sid = lexical_hit
    calls: list = []

    # Stub mode's embed raises LlmUnavailable before the search; hand back a
    # vector so the search runs.
    async def fake_embed(db, query, **kw):
        return [0.1] * settings.embedding_dim

    monkeypatch.setattr("services.retrieval_service._aembed_query", fake_embed)
    monkeypatch.setattr("services.pgvector_store.query_chunks", _failing(calls))

    with caplog.at_level(logging.WARNING, logger="services.retrieval_service"):
        status, body = _stream_turn(Session, uid, sid, monkeypatch)

    assert calls, "the failing read never ran"
    _assert_turn_completed(Session, sid, status, body)
    assert "prefetch_for_prompt failed; falling back to advisory flag" in caplog.text
