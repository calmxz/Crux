"""Unit tests for pgvector_store module (SQLite + spy pattern, no real pgvector).

Tests the SQL generation of pgvector_store functions using a spy pattern that
captures the SQLAlchemy statement and compiles it for PostgreSQL, verifying the
query structure without needing a live Postgres + pgvector extension.
"""

from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import Select

from config import settings
from services import pgvector_store


def _pg_bind(db_session, monkeypatch):
    """Make db_session look like a postgresql bind without a real Postgres."""
    monkeypatch.setattr(
        db_session,
        "get_bind",
        lambda *a, **k: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
    )
    # The SETs run inside a Core-level SAVEPOINT (not Session.begin_nested,
    # which would force an ORM flush). The spy replaces execute entirely, so
    # a no-op context is equivalent here; the real savepoint is exercised
    # against live Postgres.
    monkeypatch.setattr(
        db_session,
        "connection",
        lambda *a, **k: SimpleNamespace(begin_nested=nullcontext),
    )


def _spy_execute(db_session, monkeypatch):
    calls = []

    class EmptyResult:
        def all(self):
            return []

    def spy(stmt, *args, **kwargs):
        # Statements executed with bind parameters are recorded as a
        # (stmt, params) pair so tests can assert the value never became SQL.
        calls.append((stmt, args[0]) if args else stmt)
        return EmptyResult()

    monkeypatch.setattr(db_session, "execute", spy)
    return calls


def test_insert_chunks_is_idempotent(db_session):
    """ON CONFLICT DO NOTHING: a re-insert of the same (document_id,
    chunk_index) pairs (e.g. a retried ingestion) must not raise and must
    report 0 newly inserted rows the second time."""
    dim = settings.embedding_dim
    rows = [
        (0, 1, "alpha", [0.1] * dim),
        (1, 1, "beta", [0.2] * dim),
    ]
    n1 = pgvector_store.insert_chunks(
        db_session, session_id="s1", document_id=1, rows=rows
    )
    n2 = pgvector_store.insert_chunks(
        db_session, session_id="s1", document_id=1, rows=rows
    )
    assert n1 == 2
    assert n2 == 0


def test_insert_chunks_partial_conflict_counts_only_new_rows(db_session):
    """Partial overlap: re-inserting existing indexes alongside a new one must
    report only the newly inserted count. Task 20's per-batch resume logic
    reads this return value to decide how much of a batch actually landed."""
    dim = settings.embedding_dim
    pgvector_store.insert_chunks(
        db_session,
        session_id="s1",
        document_id=1,
        rows=[
            (0, 1, "alpha", [0.1] * dim),
            (1, 1, "beta", [0.2] * dim),
        ],
    )
    n2 = pgvector_store.insert_chunks(
        db_session,
        session_id="s1",
        document_id=1,
        rows=[
            (0, 1, "alpha", [0.1] * dim),
            (1, 1, "beta", [0.2] * dim),
            (2, 1, "gamma", [0.3] * dim),
        ],
    )
    assert n2 == 1
    from db.models import ChunkEmbedding

    total = db_session.query(ChunkEmbedding).filter_by(document_id=1).count()
    assert total == 3


def test_query_chunks_filters_to_ready_documents(db_session, monkeypatch):
    """query_chunks must filter to only ready documents — never serve chunks
    from a doc that is failed or mid-ingestion (F-27)."""
    captured = {}

    class EmptyResult:
        def all(self):
            return []

    def spy(stmt, *args, **kwargs):
        captured["stmt"] = stmt
        return EmptyResult()

    monkeypatch.setattr(db_session, "execute", spy)
    pgvector_store.query_chunks(db_session, "s1", [0.0] * 3, k=5)
    sql = str(captured["stmt"].compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": False}))
    assert "documents.status" in sql


# --- F-10: HNSW filtered-scan tuning on the search transaction -------------


def test_query_chunks_sets_hnsw_params_before_select_on_postgres(
    db_session, monkeypatch
):
    """F-10: pgvector's HNSW index under-fetches when a post-filter (doc
    status = ready) discards candidates. `ef_search` widens the candidate
    list and `iterative_scan = strict_order` lets pgvector re-scan until k
    rows survive the filter. Both are SET LOCAL, so they must be issued
    inside the same transaction, immediately before the search."""
    _pg_bind(db_session, monkeypatch)
    calls = _spy_execute(db_session, monkeypatch)

    pgvector_store.query_chunks(db_session, "s1", [0.0] * 3, k=5)

    assert len(calls) == 3
    stmt, params = calls[0]
    assert str(stmt) == "SELECT set_config('hnsw.ef_search', :v, true)"
    assert params == {"v": str(int(settings.hnsw_ef_search))}
    assert str(calls[1]) == "SET LOCAL hnsw.iterative_scan = strict_order"
    assert isinstance(calls[2], Select)


def test_query_chunks_issues_no_set_on_sqlite(db_session, monkeypatch):
    """The unit-test dialect has no hnsw GUCs; issuing them would error."""
    calls = _spy_execute(db_session, monkeypatch)

    pgvector_store.query_chunks(db_session, "s1", [0.0] * 3, k=5)

    assert len(calls) == 1
    assert isinstance(calls[0], Select)


def test_query_chunks_rejects_non_int_ef_search(db_session, monkeypatch):
    """ef_search is passed as a set_config bind parameter, never as SQL text,
    but it must still go through int() so a mis-set value raises here rather
    than reaching the server as a bad GUC value."""
    _pg_bind(db_session, monkeypatch)
    _spy_execute(db_session, monkeypatch)
    monkeypatch.setattr(
        pgvector_store,
        "settings",
        SimpleNamespace(hnsw_ef_search="100; DROP TABLE documents"),
    )

    with pytest.raises(ValueError):
        pgvector_store.query_chunks(db_session, "s1", [0.0] * 3, k=5)
