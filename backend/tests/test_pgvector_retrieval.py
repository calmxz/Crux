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

import asyncio
import os

import pytest
from sqlalchemy import text

from config import settings
from db.models import Document
from services import pgvector_store, retrieval_service

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB,
    reason="TEST_DATABASE_URL not set — skipping live pgvector integration test",
)


@pytest.fixture(scope="module", autouse=True)
def _vector_extension(pg_engine):
    # Ensure the extension + tables exist. Caller is expected to have run
    # `alembic upgrade head` against the test DB; this is a belt-and-braces
    # check so the failure mode is a useful message, not a SQL error.
    with pg_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()


@pytest.fixture
def db(pg_seed):
    # On pg_seed's factory, so this session closes before the seed teardown.
    s = pg_seed.Session()
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
def seeded_session(db, pg_seed):
    """Seed a unique user/session/document/chunks tuple, removed by the
    shared teardown (conftest pg_seed)."""
    _, user_id, session_id = pg_seed("vec-pg", topic="vector-test", topic_profile_json="{}")
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

    return {"session_id": session_id, "doc_id": doc.id, "user_id": user_id}


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


def test_prefetch_searches_inside_its_savepoint(db, seeded_session):
    """#567: prefetch_for_prompt's search runs in a savepoint, with the HNSW
    tuning's own savepoint nested in it. The search still returns the
    nearest chunk, and the transaction-scoped tuning survives both RELEASEs
    (query_vec is passed in, so nothing commits and no ready check runs, #571)."""
    chunks = asyncio.run(
        retrieval_service.prefetch_for_prompt(
            db,
            seeded_session["session_id"],
            seeded_session["user_id"],
            "joins",
            k=3,
            query_vec=_vec(1),
        )
    )
    assert chunks is not None and "joins" in chunks[0]["text"]
    ef_search = db.execute(text("SELECT current_setting('hnsw.ef_search')")).scalar_one()
    assert ef_search == str(int(settings.hnsw_ef_search))


def test_prefetch_with_vector_skips_document_gone_non_ready(db, seeded_session, caplog):
    """#571: with a query_vec there is no ready check, so the document going
    non-ready after the fallback's check is caught only by the search's
    status filter (F-27). Its chunks are never served, and no failure is
    logged: the None comes from no hits, not from the except path."""
    doc = db.get(Document, seeded_session["doc_id"])
    doc.status = "pending"
    db.commit()

    chunks = asyncio.run(
        retrieval_service.prefetch_for_prompt(
            db,
            seeded_session["session_id"],
            seeded_session["user_id"],
            "joins",
            k=3,
            query_vec=_vec(1),
        )
    )
    assert chunks is None
    assert "prefetch_for_prompt failed" not in caplog.text


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
        text("SELECT COUNT(*) FROM chunk_embeddings WHERE session_id = :sid"),
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
        db,
        session_id=sid,
        document_id=other.id,
        rows=[(0, 1, "survivor chunk", _vec(4))],
    )
    db.commit()

    # seeded_session inserts 3 chunks for doc_id.
    deleted = pgvector_store.delete_document_chunks(db, document_id=doc_id)
    assert deleted == 3

    # Target's chunks gone; the other document's chunk survives.
    survivors = pgvector_store.query_chunks(db, session_id=sid, query_embedding=_vec(4), k=10)
    assert [c.doc_id for c in survivors] == [other.id]
