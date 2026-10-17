"""TDD: services.retrieval_service.retrieve (pgvector backend, Phase 7 T4).

Unit tests mock services.pgvector_store.query_chunks so they run against
the in-memory SQLite fixture. End-to-end cosine-distance behavior is
covered in tests/test_pgvector_retrieval.py against a live Postgres.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import litellm
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

    # The retrieve tool still calls litellm directly until #412.
    monkeypatch.setattr(litellm, "embedding", fake_embedding)


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
        return SimpleNamespace(data=[{"embedding": [0.1] * settings.embedding_dim} for _ in input])

    monkeypatch.setattr(litellm, "embedding", fake_embedding)
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
    # llm_stub_enabled, and the stub provider refuses the fallback's embed.
    # Pin it off for this module (the stub-mode tests re-enable it).
    from config import settings

    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "")


def _fake_embedding_resp(vec):
    from types import SimpleNamespace

    return SimpleNamespace(data=[{"embedding": vec}])


def test_semantic_fallback_true_above_threshold(db_session, monkeypatch, fake_llm):
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [1.0, 0.0, 0.0],
    )

    fake_llm.vector = [1.0, 0.0, 0.0]  # sim = 1.0
    result, vec = asyncio.run(retrieval_service.semantic_fallback_required(db_session, "s1", "q"))
    assert result is True
    assert vec == [1.0, 0.0, 0.0]


def test_semantic_fallback_false_below_threshold(db_session, monkeypatch, fake_llm):
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [1.0, 0.0, 0.0],
    )

    fake_llm.vector = [0.0, 1.0, 0.0]  # sim = 0.0
    result, vec = asyncio.run(retrieval_service.semantic_fallback_required(db_session, "s1", "q"))
    assert result is False
    assert vec == [0.0, 1.0, 0.0]


def test_semantic_fallback_false_without_ready_docs(db_session, monkeypatch):
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: False,
    )
    result, vec = asyncio.run(retrieval_service.semantic_fallback_required(db_session, "s1", "q"))
    assert result is False
    assert vec is None


def test_semantic_fallback_false_on_sqlite_centroid_guard(db_session, monkeypatch):
    # Real _session_centroid on the sqlite test db must return None.
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    assert retrieval_service._session_centroid(db_session, "s1") is None
    result, vec = asyncio.run(retrieval_service.semantic_fallback_required(db_session, "s1", "q"))
    assert result is False
    assert vec is None


def test_semantic_fallback_false_on_embedding_error(db_session, monkeypatch, fake_llm):
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [1.0, 0.0, 0.0],
    )

    fake_llm.embed_errors = [RuntimeError("embedding down")]
    result, vec = asyncio.run(retrieval_service.semantic_fallback_required(db_session, "s1", "q"))
    assert result is False
    assert vec is None


def test_semantic_fallback_false_in_stub_mode(db_session, monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "llm_stub", True)
    result, vec = asyncio.run(retrieval_service.semantic_fallback_required(db_session, "s1", "q"))
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
    monkeypatch.setattr(litellm, "completion_cost", lambda **kw: 0.0005)
    retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="query", k=5)
    )
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0005")
    row = db_session.execute(select(LlmCallLog).where(LlmCallLog.user_id == USER_ID)).scalar_one()
    assert row.purpose == "embedding"


def test_retrieve_commits_its_metering_before_querying(
    session, ctx, mock_embed, db_session, monkeypatch
):
    # _embed_query commits before the network call so the pooled connection
    # is not held idle across the embedding and its retries; nothing reopens
    # a transaction before the query.
    _seed_ready_doc(db_session)
    open_at_query: list[bool] = []

    def query(db, **_kw):
        open_at_query.append(db.in_transaction())
        return []

    monkeypatch.setattr("services.retrieval_service.pgvector_store.query_chunks", query)
    monkeypatch.setattr(litellm, "completion_cost", lambda **kw: 0.0005)
    retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="query", k=5)
    )
    assert open_at_query == [False]


def test_retrieve_rolls_back_the_error_it_swallows(
    session, ctx, mock_embed, db_session, monkeypatch
):
    """#569: retrieve returns `retrieval_failed` instead of raising, so
    dispatch never rolls back; on Postgres the aborted transaction would fail
    the next tool in the batch. The except arm covers every statement in it,
    the embed's commit included."""
    _seed_ready_doc(db_session)
    rollbacks: list[bool] = []
    real_rollback = db_session.rollback

    def rollback():
        rollbacks.append(True)
        real_rollback()

    def query(db, **_kw):
        raise RuntimeError("vector query failed")

    monkeypatch.setattr(db_session, "rollback", rollback)
    monkeypatch.setattr("services.retrieval_service.pgvector_store.query_chunks", query)
    monkeypatch.setattr(litellm, "completion_cost", lambda **kw: 0.0005)
    result = retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="query", k=5)
    )
    assert (result.ok, result.error) == (False, "retrieval_failed")
    assert rollbacks == [True]


def test_semantic_fallback_meters_when_user_id_given(db_session, monkeypatch, fake_llm):
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

    fake_llm.vector = [1.0, 0.0, 0.0]  # sim = 1.0
    fake_llm.cost = Decimal("0.0005")
    asyncio.run(
        retrieval_service.semantic_fallback_required(db_session, "s1", "q", user_id="u_fallback")
    )
    assert cost_meter.current_spend(db_session, "u_fallback") == Decimal("0.0005")


def test_semantic_fallback_does_not_meter_without_user_id(db_session, monkeypatch, fake_llm):
    # Existing positional callers (no user_id) keep working, unmetered.
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [1.0, 0.0, 0.0],
    )

    fake_llm.vector = [1.0, 0.0, 0.0]
    fake_llm.cost = Decimal("0.0005")
    result, vec = asyncio.run(retrieval_service.semantic_fallback_required(db_session, "s1", "q"))
    assert result is True
    assert vec == [1.0, 0.0, 0.0]
    assert cost_meter.global_spend(db_session) == Decimal("0")
    assert db_session.execute(select(LlmCallLog)).first() is None


def test_embedding_calls_pass_timeout(session, ctx, db_session, monkeypatch):
    from config import settings

    _seed_ready_doc(db_session)
    _stub_query(monkeypatch, [])
    captured = {}

    def _fake_embedding(**kw):
        captured.update(kw)
        return SimpleNamespace(data=[{"embedding": [0.1] * 8}])

    monkeypatch.setattr(litellm, "embedding", _fake_embedding)
    monkeypatch.setattr(litellm, "completion_cost", lambda **kw: 0.0)
    retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="query", k=5)
    )
    assert captured["timeout"] == settings.embedding_timeout_s


# --- F-56: server force-retrieve prefetch ---------------------------------


def test_prefetch_for_prompt_returns_chunks_and_meters(session, db_session, monkeypatch, fake_llm):
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

    fake_llm.cost = Decimal("0.0005")

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
    row = db_session.execute(select(LlmCallLog).where(LlmCallLog.user_id == USER_ID)).scalar_one()
    assert row.purpose == "embedding"


def test_prefetch_for_prompt_empty_hits_returns_none(session, db_session, monkeypatch, fake_llm):
    _seed_ready_doc(db_session)
    _stub_query(monkeypatch, [])

    result = asyncio.run(
        retrieval_service.prefetch_for_prompt(db_session, SESSION_ID, USER_ID, "query")
    )
    assert result is None


def test_prefetch_for_prompt_no_ready_document_returns_none(db_session, fake_llm):
    result = asyncio.run(
        retrieval_service.prefetch_for_prompt(db_session, "no-doc-session", "u1", "query")
    )
    assert result is None
    assert fake_llm.aembed_calls == []  # short-circuits before embedding when no ready doc


def test_prefetch_cost_cap_refusal_is_no_retrieval(session, db_session, monkeypatch, fake_llm):
    """A capped user gets no prefetch: the adapter refuses before embedding."""
    from config import settings

    _seed_ready_doc(db_session)
    _stub_query(monkeypatch, [])
    cost_meter.record_cost(db_session, USER_ID, Decimal(str(settings.llm_hard_cap_usd)))
    db_session.commit()

    result = asyncio.run(
        retrieval_service.prefetch_for_prompt(db_session, SESSION_ID, USER_ID, "query")
    )
    assert result is None
    assert fake_llm.aembed_calls == []


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

    # Through the real LiteLlmProvider: the timeout kwarg is the provider's job.
    monkeypatch.setattr(litellm, "aembedding", _fake_aembedding)
    asyncio.run(retrieval_service.semantic_fallback_required(db_session, "s1", "q"))
    assert captured["timeout"] == settings.embedding_timeout_s


# --- B-09: fallback query vector reused by prefetch (embed once per turn) --


def test_fallback_vector_prevents_second_embedding(session, db_session, monkeypatch, fake_llm):
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

    fake_llm.vector = [1.0, 0.0, 0.0]
    fake_llm.cost = Decimal("0.0005")

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
    assert fake_llm.aembed_calls == [["query"]]


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
    write must not commit -- _prepare_turn owns that transaction."""
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
    monkeypatch.setattr("services.retrieval_service._compute_centroid", lambda db, sid: computed)

    commits: list[int] = []
    monkeypatch.setattr(type(db_session), "commit", lambda self: commits.append(1))

    assert retrieval_service._session_centroid(db_session, "s_cent2") == computed
    assert commits == []

    row = db_session.get(SessionModel, "s_cent2")
    db_session.refresh(row)
    assert list(row.chunk_centroid) == computed


def test_prefetch_holds_no_db_transaction_during_the_embedding(
    session, db_session, monkeypatch, fake_llm
):
    """#411: has_ready_document opens a transaction; it is committed before
    the adapter checks out its own connection for the gate and settlement."""
    _seed_ready_doc(db_session)
    _stub_query(monkeypatch, [])
    seen = []
    real_aembed = fake_llm.aembed

    async def spy(texts):
        seen.append(db_session.in_transaction())
        return await real_aembed(texts)

    fake_llm.aembed = spy
    asyncio.run(retrieval_service.prefetch_for_prompt(db_session, SESSION_ID, USER_ID, "q"))
    assert seen == [False]


# --- stub mode (#413): a refused embedding keeps today's no-model output ------


@pytest.fixture
def stub_on(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "llm_stub", True)

    def refuse(**_kw):
        raise AssertionError("stub mode called litellm")

    monkeypatch.setattr(litellm, "embedding", refuse)
    monkeypatch.setattr(litellm, "aembedding", refuse)


def test_stub_mode_semantic_fallback_with_ready_doc_stays_optional(
    session, db_session, monkeypatch, caplog, stub_on
):
    _seed_ready_doc(db_session)
    monkeypatch.setattr(retrieval_service, "_session_centroid", lambda db, sid: [1.0, 0.0])
    with caplog.at_level("WARNING"):
        result = asyncio.run(
            retrieval_service.semantic_fallback_required(
                db_session, SESSION_ID, "q", user_id=USER_ID
            )
        )
    assert result == (False, None)
    assert "semantic fallback check failed" not in caplog.text


def test_stub_mode_prefetch_with_ready_doc_returns_none(session, db_session, caplog, stub_on):
    _seed_ready_doc(db_session)
    with caplog.at_level("WARNING"):
        result = asyncio.run(
            retrieval_service.prefetch_for_prompt(db_session, SESSION_ID, USER_ID, "q")
        )
    assert result is None
    assert "prefetch_for_prompt failed" not in caplog.text


def test_stub_mode_retrieve_reports_the_refusal_code(session, ctx, db_session, stub_on):
    from lib.error_codes import LLM_UNAVAILABLE

    _seed_ready_doc(db_session)
    result = retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SESSION_ID, query="q", k=5)
    )
    assert (result.ok, result.status, result.error) == (False, "failed", LLM_UNAVAILABLE)
