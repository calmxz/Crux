"""TDD: services.retrieval_service.retrieve (pgvector backend, Phase 7 T4).

Unit tests mock services.pgvector_store.query_chunks so they run against
the in-memory SQLite fixture. End-to-end cosine-distance behavior is
covered in tests/test_pgvector_retrieval.py against a live Postgres.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from agent.types import ToolContext
from contracts import RetrieveChunksArgs, TopicProfile
from db.models import Document, LlmCallLog, User
from db.models import Session as SessionModel
from services import cost_meter, pgvector_store, retrieval_service

SESSION_ID = "sess_ret"
USER_ID = "u_ret"


@pytest.fixture
def session(db_session):
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


@pytest.fixture
def ctx(db_session):
    return ToolContext(
        db=db_session,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_embed(monkeypatch):
    def fake_embedding(model, input, **_):
        if isinstance(input, str):
            input = [input]
        return SimpleNamespace(data=[{"embedding": [0.1] * 8} for _ in input])

    monkeypatch.setattr(
        "services.retrieval_service.litellm.embedding", fake_embedding
    )


def _stub_query(monkeypatch, hits: list[pgvector_store.RetrievedChunk]):
    def fake(db, *, session_id, query_embedding, k):
        assert session_id == SESSION_ID
        return list(hits)[:k]

    monkeypatch.setattr("services.retrieval_service.pgvector_store.query_chunks", fake)


def _seed_ready_doc(db_session) -> Document:
    doc = Document(session_id=SESSION_ID, filename="x.pdf", status="ready")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


def test_ready_doc_returns_chunks(session, ctx, mock_embed, db_session, monkeypatch):
    doc = _seed_ready_doc(db_session)
    _stub_query(
        monkeypatch,
        [
            pgvector_store.RetrievedChunk(
                doc_id=doc.id,
                chunk_text="Inner joins return matching rows.",
                page=1,
                score=0.12,
            )
        ],
    )
    result = retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="inner join", k=5)
    )
    assert result.ok is True
    assert result.status == "ok"
    chunks = (result.data or {}).get("chunks", [])
    assert len(chunks) == 1
    assert "matching rows" in chunks[0]["text"]
    assert chunks[0]["doc_id"] == str(doc.id)
    assert chunks[0]["page"] == 1


def test_retrieve_requests_configured_dimension(session, ctx, db_session, monkeypatch):
    """The query embedding must use the same configured dimension as the stored
    chunk embeddings, otherwise cosine search is dimension-mismatched. This and
    the ingestion-side counterpart together pin both halves to embedding_dim."""
    from config import settings

    captured = {}

    def fake_embedding(model, input, **kw):
        captured["dimensions"] = kw.get("dimensions")
        if isinstance(input, str):
            input = [input]
        return SimpleNamespace(
            data=[{"embedding": [0.1] * settings.embedding_dim} for _ in input]
        )

    monkeypatch.setattr(
        "services.retrieval_service.litellm.embedding", fake_embedding
    )
    _seed_ready_doc(db_session)
    _stub_query(monkeypatch, [])
    retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="q", k=5)
    )
    expected_dim = settings.embedding_dim  # local int: keep secrets out of failure repr
    assert captured["dimensions"] == expected_dim


def test_pending_doc_returns_no_results(session, ctx, mock_embed, db_session):
    db_session.add(Document(session_id=SESSION_ID, filename="x.pdf", status="pending"))
    db_session.commit()
    result = retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="q", k=5)
    )
    assert result.status == "no_results"
    assert (result.data or {}).get("chunks", []) == []


def test_no_documents_returns_no_results(session, ctx, mock_embed, db_session):
    result = retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="q", k=5)
    )
    assert result.status == "no_results"


def test_empty_hits_returns_no_results(session, ctx, mock_embed, db_session, monkeypatch):
    _seed_ready_doc(db_session)
    _stub_query(monkeypatch, [])
    result = retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="q", k=5)
    )
    assert result.status == "no_results"
    assert (result.data or {}).get("chunks", []) == []


def test_pgvector_exception_returns_failed(session, ctx, mock_embed, db_session, monkeypatch):
    _seed_ready_doc(db_session)

    def boom(*a, **k):
        raise RuntimeError("pgvector down")

    monkeypatch.setattr("services.retrieval_service.pgvector_store.query_chunks", boom)
    result = retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="q", k=5)
    )
    assert result.ok is False
    assert result.status == "failed"
    assert result.error == "retrieval_failed"


def test_pgvector_exception_does_not_leak_internal_message(
    session, ctx, mock_embed, db_session, monkeypatch
):
    """H-5 regression: a future change that reintroduces str(e) into the
    error field would leak server internals (file paths, traceback fragments,
    or attacker-controlled input echoes) into chat tool-call traces. Lock
    the generic literal and assert the sentinel exception text is absent."""
    _seed_ready_doc(db_session)

    sentinel = "SENSITIVE_INTERNAL_PATH_/srv/secret/keys.db"

    def boom(*a, **k):
        raise RuntimeError(sentinel)

    monkeypatch.setattr("services.retrieval_service.pgvector_store.query_chunks", boom)
    result = retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="q", k=5)
    )
    assert result.error == "retrieval_failed"
    serialized = result.model_dump_json()
    assert sentinel not in serialized, "raw exception message leaked into ToolResult"


def test_session_id_mismatch_returns_failed(session, ctx, mock_embed, db_session):
    result = retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id="other_session", query="q", k=5)
    )
    assert result.ok is False
    assert result.status == "failed"
    assert "mismatch" in (result.error or "")


# --- D2.2 semantic fallback ---------------------------------------------


@pytest.fixture(autouse=True)
def _stub_off(monkeypatch):
    # settings loads .env; a developer's gemini_api_key=test would flip
    # llm_stub_enabled and short-circuit the fallback. Pin it off for this
    # module (the stub-mode test re-enables it explicitly).
    from config import settings

    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "")


def _fake_embedding_resp(vec):
    from types import SimpleNamespace

    return SimpleNamespace(data=[{"embedding": vec}])


def test_semantic_fallback_true_above_threshold(db_session, monkeypatch):
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [1.0, 0.0, 0.0],
    )

    async def fake_aembedding(**kw):
        return _fake_embedding_resp([1.0, 0.0, 0.0])  # sim = 1.0

    monkeypatch.setattr(
        "services.retrieval_service.litellm.aembedding", fake_aembedding
    )
    result, vec = asyncio.run(
        retrieval_service.semantic_fallback_required(db_session, "s1", "q")
    )
    assert result is True
    assert vec == [1.0, 0.0, 0.0]


def test_semantic_fallback_false_below_threshold(db_session, monkeypatch):
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [1.0, 0.0, 0.0],
    )

    async def fake_aembedding(**kw):
        return _fake_embedding_resp([0.0, 1.0, 0.0])  # sim = 0.0

    monkeypatch.setattr(
        "services.retrieval_service.litellm.aembedding", fake_aembedding
    )
    result, vec = asyncio.run(
        retrieval_service.semantic_fallback_required(db_session, "s1", "q")
    )
    assert result is False
    assert vec == [0.0, 1.0, 0.0]


def test_semantic_fallback_false_without_ready_docs(db_session, monkeypatch):
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: False,
    )
    result, vec = asyncio.run(
        retrieval_service.semantic_fallback_required(db_session, "s1", "q")
    )
    assert result is False
    assert vec is None


def test_semantic_fallback_false_on_sqlite_centroid_guard(db_session, monkeypatch):
    # Real _session_centroid on the sqlite test db must return None.
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    assert retrieval_service._session_centroid(db_session, "s1") is None
    result, vec = asyncio.run(
        retrieval_service.semantic_fallback_required(db_session, "s1", "q")
    )
    assert result is False
    assert vec is None


def test_semantic_fallback_false_on_embedding_error(db_session, monkeypatch):
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [1.0, 0.0, 0.0],
    )

    async def boom(**kw):
        raise RuntimeError("embedding down")

    monkeypatch.setattr("services.retrieval_service.litellm.aembedding", boom)
    result, vec = asyncio.run(
        retrieval_service.semantic_fallback_required(db_session, "s1", "q")
    )
    assert result is False
    assert vec is None


def test_semantic_fallback_false_in_stub_mode(db_session, monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "llm_stub", True)
    result, vec = asyncio.run(
        retrieval_service.semantic_fallback_required(db_session, "s1", "q")
    )
    assert result is False
    assert vec is None


def test_cosine_similarity_basics():
    assert retrieval_service._cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert retrieval_service._cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert retrieval_service._cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


# --- F-19 / F-06: embedding metering + timeout ---------------------------


def test_retrieve_meters_embedding_spend(session, ctx, mock_embed, db_session, monkeypatch):
    # F-19: every retrieval turn embeds the query; that spend must hit the ledger.
    _seed_ready_doc(db_session)
    _stub_query(monkeypatch, [])
    monkeypatch.setattr(
        retrieval_service.cost_meter.litellm, "completion_cost", lambda **kw: 0.0005
    )
    retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="query", k=5)
    )
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0005")
    row = db_session.execute(
        select(LlmCallLog).where(LlmCallLog.user_id == USER_ID)
    ).scalar_one()
    assert row.purpose == "embedding"


def test_semantic_fallback_meters_when_user_id_given(db_session, monkeypatch):
    db_session.add(User(id="u_fallback"))
    db_session.commit()
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [1.0, 0.0, 0.0],
    )
    async def fake_aembedding(**kw):
        return _fake_embedding_resp([1.0, 0.0, 0.0])  # sim = 1.0

    monkeypatch.setattr(
        "services.retrieval_service.litellm.aembedding", fake_aembedding
    )
    monkeypatch.setattr(
        retrieval_service.cost_meter.litellm, "completion_cost", lambda **kw: 0.0005
    )
    asyncio.run(
        retrieval_service.semantic_fallback_required(
            db_session, "s1", "q", user_id="u_fallback"
        )
    )
    assert cost_meter.current_spend(db_session, "u_fallback") == Decimal("0.0005")


def test_semantic_fallback_does_not_meter_without_user_id(db_session, monkeypatch):
    # Existing positional callers (no user_id) keep working, unmetered.
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [1.0, 0.0, 0.0],
    )
    async def fake_aembedding(**kw):
        return _fake_embedding_resp([1.0, 0.0, 0.0])

    monkeypatch.setattr(
        "services.retrieval_service.litellm.aembedding", fake_aembedding
    )
    called = {"n": 0}

    def _boom_meter(*a, **kw):
        called["n"] += 1
        raise AssertionError("metering must not run without user_id")

    monkeypatch.setattr(retrieval_service.cost_meter, "meter_embedding_response", _boom_meter)
    result, vec = asyncio.run(
        retrieval_service.semantic_fallback_required(db_session, "s1", "q")
    )
    assert result is True
    assert vec == [1.0, 0.0, 0.0]
    assert called["n"] == 0


def test_embedding_calls_pass_timeout(session, ctx, db_session, monkeypatch):
    from config import settings

    _seed_ready_doc(db_session)
    _stub_query(monkeypatch, [])
    captured = {}

    def _fake_embedding(**kw):
        captured.update(kw)
        return SimpleNamespace(data=[{"embedding": [0.1] * 8}])

    monkeypatch.setattr(retrieval_service.litellm, "embedding", _fake_embedding)
    monkeypatch.setattr(
        retrieval_service.cost_meter.litellm, "completion_cost", lambda **kw: 0.0
    )
    retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="query", k=5)
    )
    assert captured["timeout"] == settings.embedding_timeout_s


# --- F-56: server force-retrieve prefetch ---------------------------------


def test_prefetch_for_prompt_returns_chunks_and_meters(session, db_session, monkeypatch):
    """Success path: chunk dict shape matches retrieve()'s, and the embedding
    spend is metered (F-19), mirroring test_retrieve_meters_embedding_spend."""
    doc = _seed_ready_doc(db_session)
    _stub_query(
        monkeypatch,
        [
            pgvector_store.RetrievedChunk(
                doc_id=doc.id,
                chunk_text="Inner joins return matching rows.",
                page=2,
                score=0.09,
                doc_name=doc.filename,
            )
        ],
    )

    async def fake_aembedding(**kw):
        return _fake_embedding_resp([0.1] * 8)

    monkeypatch.setattr(retrieval_service.litellm, "aembedding", fake_aembedding)
    monkeypatch.setattr(
        retrieval_service.cost_meter.litellm, "completion_cost", lambda **kw: 0.0005
    )

    result = asyncio.run(
        retrieval_service.prefetch_for_prompt(db_session, SESSION_ID, USER_ID, "inner join")
    )

    assert result == [
        {
            "doc_id": str(doc.id),
            "text": "Inner joins return matching rows.",
            "page": 2,
            "score": 0.09,
            "doc_name": doc.filename,
        }
    ]
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0005")
    row = db_session.execute(
        select(LlmCallLog).where(LlmCallLog.user_id == USER_ID)
    ).scalar_one()
    assert row.purpose == "embedding"


def test_prefetch_for_prompt_empty_hits_returns_none(session, db_session, monkeypatch):
    _seed_ready_doc(db_session)
    _stub_query(monkeypatch, [])

    async def fake_aembedding(**kw):
        return _fake_embedding_resp([0.1] * 8)

    monkeypatch.setattr(retrieval_service.litellm, "aembedding", fake_aembedding)

    result = asyncio.run(
        retrieval_service.prefetch_for_prompt(db_session, SESSION_ID, USER_ID, "query")
    )
    assert result is None


def test_prefetch_for_prompt_no_ready_document_returns_none(db_session, monkeypatch):
    called = {"n": 0}

    async def fake_aembedding(**kw):
        called["n"] += 1
        return _fake_embedding_resp([0.1] * 8)

    monkeypatch.setattr(retrieval_service.litellm, "aembedding", fake_aembedding)
    result = asyncio.run(
        retrieval_service.prefetch_for_prompt(db_session, "no-doc-session", "u1", "query")
    )
    assert result is None
    assert called["n"] == 0  # short-circuits before embedding when no ready doc


# --- B-08: cost_holder collects metered spend across a retrieval call ----


def test_prefetch_appends_metered_cost_to_holder(session, db_session, monkeypatch):
    """B-08: _prepare_turn re-records embedding spend after a rollback, so
    prefetch_for_prompt must let the caller collect what meter_embedding_response
    actually charged via an out-param, independent of the return value."""
    _seed_ready_doc(db_session)
    _stub_query(monkeypatch, [])

    async def fake_aembedding(**kw):
        return _fake_embedding_resp([0.1] * 8)

    monkeypatch.setattr(retrieval_service.litellm, "aembedding", fake_aembedding)
    monkeypatch.setattr(
        retrieval_service.cost_meter.litellm, "completion_cost", lambda **kw: 0.0005
    )

    holder: list = []
    asyncio.run(
        retrieval_service.prefetch_for_prompt(
            db_session, SESSION_ID, USER_ID, "query", cost_holder=holder
        )
    )
    assert len(holder) == 1 and holder[0] >= 0
    assert holder[0] == Decimal("0.0005")


def test_semantic_fallback_appends_metered_cost_to_holder(db_session, monkeypatch):
    """Same out-param contract for semantic_fallback_required, which only
    meters when user_id is given (F-19)."""
    db_session.add(User(id="u_holder"))
    db_session.commit()
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [1.0, 0.0, 0.0],
    )

    async def fake_aembedding(**kw):
        return _fake_embedding_resp([1.0, 0.0, 0.0])

    monkeypatch.setattr(
        "services.retrieval_service.litellm.aembedding", fake_aembedding
    )
    monkeypatch.setattr(
        retrieval_service.cost_meter.litellm, "completion_cost", lambda **kw: 0.0005
    )

    holder: list = []
    asyncio.run(
        retrieval_service.semantic_fallback_required(
            db_session, "s1", "q", user_id="u_holder", cost_holder=holder
        )
    )
    assert len(holder) == 1 and holder[0] >= 0
    assert holder[0] == Decimal("0.0005")


def test_semantic_fallback_calls_pass_timeout(db_session, monkeypatch):
    from config import settings

    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [1.0, 0.0, 0.0],
    )
    captured = {}

    async def _fake_aembedding(**kw):
        captured.update(kw)
        return _fake_embedding_resp([1.0, 0.0, 0.0])

    monkeypatch.setattr(
        "services.retrieval_service.litellm.aembedding", _fake_aembedding
    )
    asyncio.run(retrieval_service.semantic_fallback_required(db_session, "s1", "q"))
    assert captured["timeout"] == settings.embedding_timeout_s


# --- B-09: fallback query vector reused by prefetch (embed once per turn) --


def test_fallback_vector_prevents_second_embedding(session, db_session, monkeypatch):
    """B-09: when the semantic fallback already embedded the query, the
    prefetch it triggers must reuse that vector instead of embedding again --
    otherwise every fallback-required turn pays for the same embedding twice
    (double cost + one extra round-trip)."""
    _seed_ready_doc(db_session)
    _stub_query(monkeypatch, [])
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [1.0, 0.0, 0.0],
    )

    embed_calls = []

    async def fake_aembedding(**kw):
        embed_calls.append(kw)
        return _fake_embedding_resp([1.0, 0.0, 0.0])

    monkeypatch.setattr(retrieval_service.litellm, "aembedding", fake_aembedding)
    monkeypatch.setattr(
        retrieval_service.cost_meter.litellm, "completion_cost", lambda **kw: 0.0005
    )

    required, vec = asyncio.run(
        retrieval_service.semantic_fallback_required(
            db_session, SESSION_ID, "query", user_id=USER_ID
        )
    )
    assert required is True
    assert vec is not None

    asyncio.run(
        retrieval_service.prefetch_for_prompt(
            db_session, SESSION_ID, USER_ID, "query", query_vec=vec
        )
    )
    assert len(embed_calls) == 1


def test_session_centroid_returns_stored_column_without_querying(db_session, monkeypatch):
    """F-05: once materialised on sessions.chunk_centroid, the centroid is a
    column read -- no avg() aggregation over every chunk of the session."""
    from config import settings

    db_session.add(User(id="u_cent"))
    db_session.flush()
    stored = [0.25] * settings.embedding_dim
    db_session.add(
        SessionModel(
            id="s_cent",
            user_id="u_cent",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
            chunk_centroid=stored,
        )
    )
    db_session.commit()

    # Dialect guard must stay the first statement on sqlite (test_chat_prepare_perf
    # counts statements there), so force the postgres branch explicitly.
    monkeypatch.setattr("services.retrieval_service._is_postgres", lambda db: True)

    def boom(*a, **kw):
        raise AssertionError("no aggregate query may run when the centroid is stored")

    monkeypatch.setattr("services.retrieval_service.func.avg", boom)

    assert retrieval_service._session_centroid(db_session, "s_cent") == stored


def test_session_centroid_materialises_and_does_not_commit(db_session, monkeypatch):
    """F-05: a missing centroid is computed once and written back, but the
    write must not commit -- _prepare_turn owns that transaction (B-08)."""
    from config import settings

    db_session.add(User(id="u_cent2"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_cent2",
            user_id="u_cent2",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()

    computed = [0.5] * settings.embedding_dim
    monkeypatch.setattr("services.retrieval_service._is_postgres", lambda db: True)
    monkeypatch.setattr(
        "services.retrieval_service._compute_centroid", lambda db, sid: computed
    )

    commits: list[int] = []
    monkeypatch.setattr(
        type(db_session), "commit", lambda self: commits.append(1)
    )

    assert retrieval_service._session_centroid(db_session, "s_cent2") == computed
    assert commits == []

    row = db_session.get(SessionModel, "s_cent2")
    db_session.refresh(row)
    assert list(row.chunk_centroid) == computed
