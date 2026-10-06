"""End-to-end pgvector retrieval test (Phase 7 T9).

Exercises real cosine-distance ordering against a live Postgres with the
`vector` extension installed. The unit tests in `test_retrieval_service.py`
mock `pgvector_store.query_chunks`, so the SQL operator (`<=>`) is never
actually executed there — this test fills that gap.

**Opt-in**: skipped unless `TEST_DATABASE_URL` is set. CI provides one via
the `postgres` service container in .github/workflows/ci.yml
(pgvector/pgvector:pg17) and runs `alembic upgrade head` against it first.
Locally: docker run -e POSTGRES_PASSWORD=crux -p 5432:5432 pgvector/pgvector:pg17
Never run this against a production / Supabase database: it inserts and
immediately deletes rows, but you should not be poking prod with tests.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import settings
from db.database import _normalized_url
from db.models import Document, User
from db.models import Session as SessionModel
from services import pgvector_store

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB,
    reason="TEST_DATABASE_URL not set — skipping live pgvector integration test",
)


@pytest.fixture(scope="module")
def engine():
    """One engine per module. prepare_threshold=None matches prod (Supabase pooler)."""
    eng = create_engine(
        _normalized_url(TEST_DB),
        connect_args={"prepare_threshold": None},
    )
    # Ensure the extension + tables exist. Caller is expected to have run
    # `alembic upgrade head` against the test DB; this is a belt-and-braces
    # check so the failure mode is a useful message, not a SQL error.
    with eng.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    s = Session()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


def _vec(slot: int) -> list[float]:
    """Build a one-hot-ish unit vector of length EMBEDDING_DIM with weight at `slot`.

    Cosine distance between these is 1.0 across different slots and 0.0 to itself,
    so ordering is unambiguous and assertions are robust to floating-point noise.
    """
    v = [0.0] * settings.embedding_dim
    v[slot] = 1.0
    return v


@pytest.fixture
def seeded_session(db):
    """Seed a unique user/session/document/chunks tuple. Cleans up on teardown
    so successive test runs don't accumulate rows in shared test DBs."""
    user_id = f"u-{uuid.uuid4().hex[:8]}"
    session_id = f"s-{uuid.uuid4().hex[:8]}"

    db.add(User(id=user_id))
    db.flush()
    db.add(
        SessionModel(
            id=session_id,
            user_id=user_id,
            topic="vector-test",
            topic_profile_json="{}",
        )
    )
    db.flush()
    doc = Document(session_id=session_id, filename="t.pdf", status="ready")
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 3 chunks with orthogonal embeddings. Query for slot-1 should put
    # the "joins" chunk first, then the others tied at distance 1.0.
    pgvector_store.insert_chunks(
        db,
        session_id=session_id,
        document_id=doc.id,
        rows=[
            (0, 1, "indexes accelerate lookups", _vec(0)),
            (1, 2, "joins combine rows from two tables", _vec(1)),
            (2, 3, "transactions group statements atomically", _vec(2)),
        ],
    )
    db.commit()

    yield {"session_id": session_id, "doc_id": doc.id, "user_id": user_id}

    # Teardown: delete in FK order. Wrapped in try/except so a partial seed
    # doesn't leave the test in error state on cleanup failure.
    try:
        db.execute(
            text("DELETE FROM chunk_embeddings WHERE session_id = :sid"),
            {"sid": session_id},
        )
        db.execute(text("DELETE FROM documents WHERE session_id = :sid"), {"sid": session_id})
        db.execute(text("DELETE FROM sessions WHERE id = :sid"), {"sid": session_id})
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})
        db.commit()
    except Exception:
        db.rollback()


def test_cosine_query_returns_nearest_first(db, seeded_session):
    """Slot-1 query → 'joins' chunk first (cosine distance 0)."""
    hits = pgvector_store.query_chunks(
        db,
        session_id=seeded_session["session_id"],
        query_embedding=_vec(1),
        k=3,
    )
    assert len(hits) == 3, f"expected 3 hits, got {len(hits)}"
    assert "joins" in hits[0].chunk_text
    # The matching chunk should have distance ~0; the others ~1.
    assert hits[0].score is not None and hits[0].score < 0.01
    for h in hits[1:]:
        assert h.score is not None and h.score > 0.5


def test_query_respects_session_isolation(db, seeded_session):
    """A different session_id returns zero hits even when embeddings match."""
    hits = pgvector_store.query_chunks(
        db,
        session_id="nonexistent-session",
        query_embedding=_vec(1),
        k=5,
    )
    assert hits == []


def test_query_respects_k_limit(db, seeded_session):
    """k=1 returns exactly one result, ordered by distance."""
    hits = pgvector_store.query_chunks(
        db,
        session_id=seeded_session["session_id"],
        query_embedding=_vec(0),
        k=1,
    )
    assert len(hits) == 1
    assert "indexes" in hits[0].chunk_text


def test_insert_then_count_matches(db, seeded_session):
    """Sanity: the rows we inserted are visible to a raw count query."""
    n = db.execute(
        text(
            "SELECT COUNT(*) FROM chunk_embeddings WHERE session_id = :sid"
        ),
        {"sid": seeded_session["session_id"]},
    ).scalar()
    assert n == 3


def test_delete_document_chunks_removes_only_that_document(db, seeded_session):
    """delete_document_chunks deletes the target doc's chunks (returns count) and
    leaves a second document's chunks in the same session intact."""
    sid = seeded_session["session_id"]
    doc_id = seeded_session["doc_id"]

    # Add a second document with one chunk in the SAME session.
    other = Document(session_id=sid, filename="keep.pdf", status="ready")
    db.add(other)
    db.commit()
    db.refresh(other)
    pgvector_store.insert_chunks(
        db, session_id=sid, document_id=other.id,
        rows=[(0, 1, "survivor chunk", _vec(4))],
    )
    db.commit()

    # seeded_session inserts 3 chunks for doc_id.
    deleted = pgvector_store.delete_document_chunks(db, document_id=doc_id)
    assert deleted == 3

    # Target's chunks gone; the other document's chunk survives.
    survivors = pgvector_store.query_chunks(
        db, session_id=sid, query_embedding=_vec(4), k=10
    )
    assert [c.doc_id for c in survivors] == [other.id]

    # Teardown for the extra doc (seeded_session only cleans its own rows).
    db.execute(
        text("DELETE FROM chunk_embeddings WHERE document_id = :d"), {"d": other.id}
    )
    db.execute(text("DELETE FROM documents WHERE id = :d"), {"d": other.id})
    db.commit()
