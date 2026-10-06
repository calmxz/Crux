"""TDD: services.ingestion_service.run pipeline.

Pipeline: pypdf -> chunk -> embed -> pgvector_store.insert_chunks -> kw_index.
Tests mock the embed + storage layers so they run against in-memory SQLite.
"""

import json
from types import SimpleNamespace

import pytest

from contracts import TopicProfile
from db.models import Document, User
from db.models import Session as SessionModel
from lib import chunking

SESSION_ID = "sess_ing"
USER_ID = "u_ing"


@pytest.fixture
def setup_doc(db_session, monkeypatch):
    """Seed user, session, document; patch SessionLocal to reuse the test db session."""
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
    db_session.flush()
    doc = Document(session_id=SESSION_ID, filename="x.pdf", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    # ingestion_service opens its own SessionLocal; redirect it to the in-memory test db
    test_bind = db_session.get_bind()
    from sqlalchemy.orm import sessionmaker

    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=test_bind),
    )
    return doc.id


@pytest.fixture
def insert_capture(monkeypatch):
    """Capture pgvector_store.insert_chunks calls instead of writing rows.

    SQLite has no `vector` type or cosine-distance operator, so the test
    DB can't accept ChunkEmbedding inserts. Capturing the call lets us
    assert the ingestion service hands the right payload to the storage
    layer; live row insertion is covered in test_pgvector_retrieval.py.
    """
    calls: list[dict] = []

    def fake(db, *, session_id, document_id, rows):
        calls.append(
            {
                "session_id": session_id,
                "document_id": document_id,
                "rows": list(rows),
            }
        )
        return len(rows)

    monkeypatch.setattr("services.ingestion_service.pgvector_store.insert_chunks", fake)
    return calls


@pytest.fixture
def mock_pdf(monkeypatch):
    """Return a pypdf.PdfReader stub with two pages of text."""

    class FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class FakeReader:
        def __init__(self, _path):
            self.pages = [
                FakePage("Indexes accelerate database queries."),
                FakePage("Joins combine rows from multiple tables."),
            ]

    monkeypatch.setattr("services.ingestion_service.PdfReader", FakeReader)


@pytest.fixture
def mock_embed(monkeypatch):
    def fake_embedding(model, input, **_):
        if isinstance(input, str):
            input = [input]
        return SimpleNamespace(data=[{"embedding": [0.1] * 8} for _ in input])

    monkeypatch.setattr(
        "services.ingestion_service.litellm.embedding", fake_embedding
    )


def _write_blob_stub(monkeypatch, tmp_path, doc_id, filename, content=b"stub blob bytes"):
    """Point uploads_path at tmp_path and write a dummy blob under the store's
    doc-id-prefixed key. Extractors in these tests are separately mocked, so
    the content doesn't matter -- _load_blob just needs the key to exist."""
    monkeypatch.setattr("services.ingestion_service.settings.uploads_path", str(tmp_path))
    (tmp_path / f"{doc_id}_{filename}").write_bytes(content)


def test_embed_and_store_requests_configured_dimension(db_session, setup_doc, monkeypatch):
    """Embeddings must be requested at settings.embedding_dim so they match the
    chunk_embeddings.embedding column. Without an explicit dimensions argument
    the model emits its native size (e.g. gemini-embedding-2 -> 3072), which the
    768-dim pgvector column rejects, failing ingestion for every document."""
    from config import settings
    from services import ingestion_service

    doc = db_session.get(Document, setup_doc)
    captured = {}

    def fake_embedding(model, input, **kw):
        captured["dimensions"] = kw.get("dimensions")
        return SimpleNamespace(
            data=[{"embedding": [0.1] * settings.embedding_dim} for _ in input]
        )

    monkeypatch.setattr(
        "services.ingestion_service.litellm.embedding", fake_embedding
    )
    monkeypatch.setattr(
        "services.ingestion_service.pgvector_store.insert_chunks",
        lambda db, **kw: len(kw["rows"]),
    )
    chunks = [chunking.Chunk(text="hello world", page=1, chunk_idx=0)]
    ingestion_service._embed_and_store(db_session, doc, chunks, user_id=None)
    expected_dim = settings.embedding_dim  # local int: keep secrets out of failure repr
    assert captured["dimensions"] == expected_dim


def test_embed_and_store_retries_once_on_transient_provider_error(
    db_session, setup_doc, monkeypatch
):
    """A single APIConnectionError from the provider must not fail the batch;
    the retry helper re-issues the call and the chunks are stored."""
    import litellm

    from config import settings
    from services import ingestion_service

    doc = db_session.get(Document, setup_doc)
    calls = {"n": 0}

    def flaky_embedding(model, input, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise litellm.APIConnectionError(message="blip", llm_provider="gemini", model=model)
        return SimpleNamespace(
            data=[{"embedding": [0.1] * settings.embedding_dim} for _ in input]
        )

    stored = []
    monkeypatch.setattr("services.ingestion_service.litellm.embedding", flaky_embedding)
    monkeypatch.setattr(
        "services.ingestion_service.pgvector_store.insert_chunks",
        lambda db, **kw: stored.append(kw["rows"]) or len(kw["rows"]),
    )
    monkeypatch.setattr("services.ingestion_service.llm_retry.time.sleep", lambda _s: None)

    chunks = [chunking.Chunk(text="hello world", page=1, chunk_idx=0)]
    ingestion_service._embed_and_store(db_session, doc, chunks, user_id=None)

    assert calls["n"] == 2
    assert len(stored) == 1 and len(stored[0]) == 1


def test_success_path(
    setup_doc, insert_capture, mock_pdf, mock_embed, db_session, monkeypatch, tmp_path
):
    _write_blob_stub(monkeypatch, tmp_path, setup_doc, "x.pdf")
    from services import ingestion_service

    ingestion_service.run(setup_doc)

    db_session.expire_all()
    doc = db_session.get(Document, setup_doc)
    assert doc.status == "ready"
    assert doc.error is None
    assert doc.page_count == 2

    assert len(insert_capture) == 1
    call = insert_capture[0]
    assert call["session_id"] == SESSION_ID
    assert call["document_id"] == setup_doc
    assert len(call["rows"]) >= 1
    chunk_idx, page, text, embedding = call["rows"][0]
    assert isinstance(chunk_idx, int)
    assert isinstance(text, str) and text
    assert isinstance(embedding, list) and len(embedding) == 8

    session = db_session.get(SessionModel, SESSION_ID)
    stems = set(json.loads(session.kw_index_json))
    assert len(stems) > 0


def test_pypdf_failure_marks_failed(
    setup_doc, insert_capture, mock_embed, db_session, monkeypatch, tmp_path
):
    _write_blob_stub(monkeypatch, tmp_path, setup_doc, "x.pdf")

    def boom(_path):
        raise RuntimeError("corrupt pdf")

    monkeypatch.setattr("services.ingestion_service.PdfReader", boom)
    from services import ingestion_service

    ingestion_service.run(setup_doc)
    db_session.expire_all()
    doc = db_session.get(Document, setup_doc)
    assert doc.status == "failed"
    # C-11: the exception text stays in the log; the persisted string is a
    # fixed, enumerated, user-facing message.
    assert doc.error == ingestion_service.ERR_EXTRACTION_FAILED
    assert insert_capture == []


def test_embedding_failure_marks_failed(
    setup_doc, insert_capture, mock_pdf, db_session, monkeypatch, tmp_path
):
    _write_blob_stub(monkeypatch, tmp_path, setup_doc, "x.pdf")

    def boom(model, input, **_):
        raise RuntimeError("embedding api down")

    monkeypatch.setattr("services.ingestion_service.litellm.embedding", boom)
    from services import ingestion_service

    ingestion_service.run(setup_doc)
    db_session.expire_all()
    doc = db_session.get(Document, setup_doc)
    assert doc.status == "failed"
    assert doc.error == ingestion_service.ERR_EMBEDDING_FAILED
    assert insert_capture == []


def test_pgvector_insert_failure_marks_failed(
    setup_doc, mock_pdf, mock_embed, db_session, monkeypatch, tmp_path
):
    _write_blob_stub(monkeypatch, tmp_path, setup_doc, "x.pdf")

    def boom(*a, **k):
        raise RuntimeError("pgvector insert failed")

    monkeypatch.setattr("services.ingestion_service.pgvector_store.insert_chunks", boom)
    from services import ingestion_service

    ingestion_service.run(setup_doc)
    db_session.expire_all()
    doc = db_session.get(Document, setup_doc)
    assert doc.status == "failed"
    # The insert happens inside _embed_and_store, so it is the embed stage.
    assert doc.error == ingestion_service.ERR_EMBEDDING_FAILED


def test_run_fails_over_chunk_cap_before_embedding(db_session, monkeypatch, tmp_path):
    """F-03 enforcement: documents whose chunk count exceeds settings.max_chunks
    must fail before any embedding call -- no vendor spend for an oversized doc."""
    from sqlalchemy.orm import sessionmaker

    from services import ingestion_service

    db_session.add(User(id="u_cap"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_cap",
            user_id="u_cap",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_cap", filename="big.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )
    monkeypatch.setattr("services.ingestion_service.settings.max_chunks", 1)

    # chunk=500 tokens, stride 450 -- 4000 words yields well over 1 chunk.
    _write_blob_stub(
        monkeypatch, tmp_path, doc.id, doc.filename, content=b"word " * 4000
    )

    embed_calls: list[object] = []

    def boom_if_called(model, input, **_):
        embed_calls.append((model, input))
        raise AssertionError("embedding must not be called over the chunk cap")

    monkeypatch.setattr("services.ingestion_service.litellm.embedding", boom_if_called)

    inserted: list[dict] = []

    def fake_insert(db, *, session_id, document_id, rows):
        inserted.append({"session_id": session_id, "document_id": document_id, "rows": list(rows)})
        return len(rows)

    monkeypatch.setattr("services.ingestion_service.pgvector_store.insert_chunks", fake_insert)

    ingestion_service.run(doc.id)

    db_session.expire_all()
    refreshed = db_session.get(Document, doc.id)
    assert refreshed.status == "failed"
    assert "chunk limit" in refreshed.error
    assert embed_calls == []
    assert inserted == []


def test_merge_failure_keeps_already_committed_chunks(db_session, monkeypatch, tmp_path):
    """F-02/F-03/B-02: _embed_and_store commits each batch (embed+insert+meter)
    as it goes, so chunks are durable before run() ever reaches the
    keyword-merge step. A later failure in merge_into_session must still roll
    back its own uncommitted work (page_count etc.) and mark the document
    failed, but it must NOT undo the already-committed, already-paid-for
    chunk rows -- that's the whole point of per-batch commits (a retry can
    resume instead of re-embedding from scratch)."""
    from sqlalchemy.orm import sessionmaker

    from config import settings
    from db.models import ChunkEmbedding
    from services import ingestion_service

    db_session.add(User(id="u_merge_boom"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_merge_boom",
            user_id="u_merge_boom",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_merge_boom", filename="ref.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr("services.ingestion_service.settings.uploads_path", str(tmp_path))
    (tmp_path / f"{doc.id}_ref.txt").write_text(
        "Indexes accelerate database queries. " * 20, encoding="utf-8"
    )
    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )

    def fake_embedding(model, input, **_):
        if isinstance(input, str):
            input = [input]
        return SimpleNamespace(
            data=[{"embedding": [0.1] * settings.embedding_dim} for _ in input]
        )

    monkeypatch.setattr("services.ingestion_service.litellm.embedding", fake_embedding)

    def boom(db, session_id, stems):
        raise RuntimeError("kw merge exploded")

    monkeypatch.setattr("services.ingestion_service.keyword_index.merge_into_session", boom)

    ingestion_service.run(doc.id)
    db_session.expire_all()
    doc = db_session.get(Document, doc.id)
    assert doc.status == "failed"
    assert doc.error == ingestion_service.ERR_INGESTION_FAILED
    assert db_session.query(ChunkEmbedding).filter_by(document_id=doc.id).count() > 0


def test_rerun_after_partial_failure_skips_already_paid_chunks(
    db_session, monkeypatch, tmp_path
):
    """F-02 resume contract, exercised through run() (not just the
    _embed_and_store unit tests) with the real _existing_chunk_indexes query:
    a first run that embeds+stores all chunks but then fails at the
    keyword-merge step leaves those chunks committed. Re-running the same
    document must not re-embed any of them -- litellm.embedding must not be
    called again -- and must reach status=ready this time."""
    from sqlalchemy.orm import sessionmaker

    from config import settings
    from db.models import ChunkEmbedding
    from services import ingestion_service

    db_session.add(User(id="u_resume"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_resume",
            user_id="u_resume",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_resume", filename="ref.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr("services.ingestion_service.settings.uploads_path", str(tmp_path))
    (tmp_path / f"{doc.id}_ref.txt").write_text(
        "Indexes accelerate database queries. " * 20, encoding="utf-8"
    )
    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )

    embed_calls = []

    def fake_embedding(model, input, **_):
        embed_calls.append(list(input))
        return SimpleNamespace(
            data=[{"embedding": [0.1] * settings.embedding_dim} for _ in input]
        )

    monkeypatch.setattr("services.ingestion_service.litellm.embedding", fake_embedding)
    monkeypatch.setattr(
        "services.ingestion_service.keyword_index.merge_into_session",
        lambda db, session_id, stems: (_ for _ in ()).throw(RuntimeError("kw merge exploded")),
    )

    ingestion_service.run(doc.id)
    db_session.expire_all()
    doc = db_session.get(Document, doc.id)
    assert doc.status == "failed"
    committed_before = db_session.query(ChunkEmbedding).filter_by(document_id=doc.id).count()
    assert committed_before > 0
    calls_before_rerun = len(embed_calls)

    # Second attempt: keyword merge now succeeds; embedding must not be
    # re-invoked for any chunk index already committed by the first attempt.
    monkeypatch.setattr(
        "services.ingestion_service.keyword_index.merge_into_session",
        lambda db, session_id, stems: None,
    )
    ingestion_service.run(doc.id)
    db_session.expire_all()
    doc = db_session.get(Document, doc.id)
    assert doc.status == "ready"
    assert len(embed_calls) == calls_before_rerun  # no new embedding calls
    assert (
        db_session.query(ChunkEmbedding).filter_by(document_id=doc.id).count()
        == committed_before
    )


def test_merge_failure_still_records_embedding_spend_after_rollback(
    db_session, monkeypatch, tmp_path
):
    """F-02/F-03/B-02: metering now commits per batch inside _embed_and_store,
    before run() ever reaches the keyword-merge step. So the embedding
    vendor's real spend lands on the daily cost ledger as a durable part of
    each batch's own commit -- not via a post-rollback re-record -- even
    though the doc ends up 'failed' from a later merge_into_session error."""
    from decimal import Decimal

    from sqlalchemy.orm import sessionmaker

    from config import settings
    from db.models import ChunkEmbedding
    from services import cost_meter, ingestion_service

    db_session.add(User(id="u_merge_boom2"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_merge_boom2",
            user_id="u_merge_boom2",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_merge_boom2", filename="ref.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr("services.ingestion_service.settings.uploads_path", str(tmp_path))
    (tmp_path / f"{doc.id}_ref.txt").write_text(
        "Indexes accelerate database queries. " * 20, encoding="utf-8"
    )
    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )

    def fake_embedding(model, input, **_):
        if isinstance(input, str):
            input = [input]
        return SimpleNamespace(
            data=[{"embedding": [0.1] * settings.embedding_dim} for _ in input]
        )

    monkeypatch.setattr("services.ingestion_service.litellm.embedding", fake_embedding)
    monkeypatch.setattr(
        "services.ingestion_service.cost_meter.litellm.completion_cost",
        lambda **kw: 0.004,
    )

    def boom(db, session_id, stems):
        raise RuntimeError("kw merge exploded")

    monkeypatch.setattr("services.ingestion_service.keyword_index.merge_into_session", boom)

    ingestion_service.run(doc.id)
    db_session.expire_all()
    refreshed = db_session.get(Document, doc.id)
    assert refreshed.status == "failed"
    assert db_session.query(ChunkEmbedding).filter_by(document_id=doc.id).count() > 0
    assert cost_meter.current_spend(db_session, "u_merge_boom2") == Decimal("0.0040")


def test_extract_plaintext_txt_and_md():
    from services import ingestion_service

    assert ingestion_service._extract(
        b"Plain text reference content.", "notes.txt"
    ) == [(None, "Plain text reference content.")]

    assert ingestion_service._extract(b"# Heading\n\nBody.", "notes.md") == [
        (None, "# Heading\n\nBody.")
    ]

    assert ingestion_service._extract(b"Long-form note.", "notes.markdown") == [
        (None, "Long-form note.")
    ]


def test_extract_unknown_extension_raises():
    from services import ingestion_service

    with pytest.raises(ValueError):
        ingestion_service._extract(b"\x00\x01", "data.bin")


def test_extract_slides_uses_python_pptx(monkeypatch):
    from services import ingestion_service

    class FakeTextFrame:
        def __init__(self, text):
            self.text = text

    class FakeShape:
        def __init__(self, text):
            self.has_text_frame = True
            self.has_table = False
            self.text_frame = FakeTextFrame(text)

    class FakeSlide:
        def __init__(self, texts):
            self.shapes = [FakeShape(t) for t in texts]

    class FakePresentation:
        def __init__(self, _path):
            self.slides = [
                FakeSlide(["Title one", "Bullet a"]),
                FakeSlide(["Title two"]),
            ]

    monkeypatch.setattr("services.ingestion_service.Presentation", FakePresentation)
    pages = ingestion_service._extract(b"stub pptx bytes", "x.pptx")
    assert pages[0][0] == 1 and "Title one" in pages[0][1] and "Bullet a" in pages[0][1]
    assert pages[1][0] == 2 and "Title two" in pages[1][1]


def test_extract_slides_includes_table_cell_text(monkeypatch):
    from services import ingestion_service

    class FakeCell:
        def __init__(self, text):
            self.text = text

    class FakeRow:
        def __init__(self, cells):
            self.cells = [FakeCell(c) for c in cells]

    class FakeTable:
        def __init__(self, rows):
            self.rows = [FakeRow(r) for r in rows]

    class FakeTableShape:
        def __init__(self, rows):
            self.has_text_frame = False
            self.has_table = True
            self.table = FakeTable(rows)

    class FakeSlide:
        def __init__(self, shapes):
            self.shapes = shapes

    class FakePresentation:
        def __init__(self, _path):
            self.slides = [
                FakeSlide([FakeTableShape([["r1c1", "r1c2"], ["r2c1", "r2c2"]])])
            ]

    monkeypatch.setattr("services.ingestion_service.Presentation", FakePresentation)
    pages = ingestion_service._extract(b"stub pptx bytes", "x.pptx")
    assert pages[0][0] == 1
    assert "r1c1 r1c2" in pages[0][1]
    assert "r2c1 r2c2" in pages[0][1]


def test_ingestion_meters_embedding_spend(
    db_session, insert_capture, mock_embed, monkeypatch, tmp_path
):
    """F-19: ingestion is the largest embedding spender; its litellm.embedding
    calls must land on the same daily_cost_ledger as chat/retrieval spend."""
    from decimal import Decimal

    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker

    from services import cost_meter, ingestion_service

    db_session.add(User(id="u_meter"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_meter",
            user_id="u_meter",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_meter", filename="ref.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr("services.ingestion_service.settings.uploads_path", str(tmp_path))
    (tmp_path / f"{doc.id}_ref.txt").write_text(
        "Indexes accelerate database queries. " * 20, encoding="utf-8"
    )
    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )
    monkeypatch.setattr(
        "services.ingestion_service.cost_meter.litellm.completion_cost",
        lambda **kw: 0.004,
    )

    ingestion_service.run(doc.id)

    user_id = db_session.execute(
        select(SessionModel.user_id).where(SessionModel.id == doc.session_id)
    ).scalar_one()
    assert cost_meter.current_spend(db_session, user_id) == Decimal("0.0040")


def test_embed_and_store_stops_at_cap_between_batches(db_session, monkeypatch):
    """B-01: _embed_and_store must consult the daily cost cap at the TOP of
    each per-batch loop iteration, before spending on litellm.embedding -- a
    user already over cap must not trigger another paid call."""
    from decimal import Decimal

    from services import cost_meter as cm
    from services import ingestion_service

    monkeypatch.setattr("services.cost_meter.settings.llm_hard_cap_usd", 0.10)
    db_session.add(User(id="u_capped"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_cap",
            user_id="u_capped",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_cap", filename="x.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    cm.record_cost(db_session, "u_capped", Decimal("0.2000"))
    db_session.commit()
    called = []
    monkeypatch.setattr(
        "services.ingestion_service.litellm.embedding",
        lambda **kw: called.append(1),
    )
    chunks = [chunking.Chunk(text="text", page=None, chunk_idx=0)]
    with pytest.raises(cm.CostCapExceeded):
        ingestion_service._embed_and_store(
            db_session, doc, chunks, user_id="u_capped"
        )
    assert called == []


def test_run_fails_over_cost_cap_and_keeps_prior_spend(db_session, monkeypatch, tmp_path):
    """B-01: a cap breach discovered mid-ingestion must fail the document
    with a friendly error, distinct from the generic embedding-failure
    message, and must not lose spend already paid for by earlier batches
    (Finding 1 pattern -- the cost-cap branch also re-records
    embed_cost_holder like the broad except arm does)."""
    from decimal import Decimal

    from sqlalchemy.orm import sessionmaker

    from services import cost_meter as cm
    from services import ingestion_service

    db_session.add(User(id="u_cap_run"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_cap_run",
            user_id="u_cap_run",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_cap_run", filename="ref.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr("services.ingestion_service.settings.uploads_path", str(tmp_path))
    (tmp_path / f"{doc.id}_ref.txt").write_text(
        "Indexes accelerate database queries. " * 20, encoding="utf-8"
    )
    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )

    # Over cap before ingestion even starts, so the very first batch trips it.
    monkeypatch.setattr("services.cost_meter.settings.llm_hard_cap_usd", 0.10)
    cm.record_cost(db_session, "u_cap_run", Decimal("0.2000"))
    db_session.commit()

    embed_calls: list[object] = []

    def boom_if_called(model, input, **_):
        embed_calls.append((model, input))
        raise AssertionError("embedding must not be called once the cap is exceeded")

    monkeypatch.setattr("services.ingestion_service.litellm.embedding", boom_if_called)

    ingestion_service.run(doc.id)

    db_session.expire_all()
    refreshed = db_session.get(Document, doc.id)
    assert refreshed.status == "failed"
    assert refreshed.error == "daily cost cap reached; ingestion stopped"
    assert embed_calls == []
    # Spend already on the ledger before ingestion ran must survive intact
    # (nothing new was spent since the very first batch was blocked).
    assert cm.current_spend(db_session, "u_cap_run") == Decimal("0.2000")


def test_missing_blob_marks_failed(setup_doc, db_session, monkeypatch, tmp_path):
    """F-15: if the blob isn't in the object store (and no legacy bare-filename
    fallback exists either), ingestion must fail the document, not crash."""
    monkeypatch.setattr("services.ingestion_service.settings.uploads_path", str(tmp_path))
    from services import ingestion_service

    ingestion_service.run(setup_doc)
    db_session.expire_all()
    doc = db_session.get(Document, setup_doc)
    assert doc.status == "failed"
    assert doc.error


def test_extract_plaintext_from_bytes():
    from services import ingestion_service

    assert ingestion_service._extract(b"hello world", "notes.txt") == [(None, "hello world")]


def test_legacy_bare_filename_fallback(db_session, insert_capture, mock_embed, monkeypatch, tmp_path):
    """Pre-F-15 files were stored under the bare filename (no doc-id prefix).
    _load_blob must fall back to that layout so old uploads keep ingesting."""
    from sqlalchemy.orm import sessionmaker

    from services import ingestion_service

    db_session.add(User(id="u_legacy"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_legacy",
            user_id="u_legacy",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_legacy", filename="ref.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr("services.ingestion_service.settings.uploads_path", str(tmp_path))
    (tmp_path / doc.filename).write_bytes(b"legacy content")
    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )

    ingestion_service.run(doc.id)
    db_session.expire_all()
    refreshed = db_session.get(Document, doc.id)
    assert refreshed.status == "ready"


def test_run_txt_success(db_session, insert_capture, mock_embed, monkeypatch, tmp_path):
    from sqlalchemy.orm import sessionmaker

    from contracts import TopicProfile
    from db.models import Document, User
    from db.models import Session as SessionModel
    from services import ingestion_service

    db_session.add(User(id="u_txt"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_txt",
            user_id="u_txt",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_txt", filename="ref.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr("services.ingestion_service.settings.uploads_path", str(tmp_path))
    (tmp_path / f"{doc.id}_ref.txt").write_text(
        "Indexes accelerate database queries. " * 20, encoding="utf-8"
    )
    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )

    ingestion_service.run(doc.id)
    db_session.expire_all()
    refreshed = db_session.get(Document, doc.id)
    assert refreshed.status == "ready"
    assert refreshed.page_count is None
    assert len(insert_capture) == 1
    assert len(insert_capture[0]["rows"]) >= 1


def test_run_logs_carry_document_and_session_ids(
    db_session, insert_capture, mock_embed, monkeypatch, tmp_path, caplog
):
    """G-06: ingestion start/done log lines must carry document_id and
    session_id so a failure can be correlated back to the upload without
    logging any message/document content (PII rule, logging_config.py)."""
    import logging

    from sqlalchemy.orm import sessionmaker

    from contracts import TopicProfile
    from db.models import Document, User
    from db.models import Session as SessionModel
    from services import ingestion_service

    db_session.add(User(id="u_log"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_log",
            user_id="u_log",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_log", filename="ref.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr("services.ingestion_service.settings.uploads_path", str(tmp_path))
    (tmp_path / f"{doc.id}_ref.txt").write_text(
        "Indexes accelerate database queries. " * 20, encoding="utf-8"
    )
    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )

    with caplog.at_level(logging.INFO, logger="services.ingestion_service"):
        ingestion_service.run(doc.id)

    joined = " ".join(r.getMessage() for r in caplog.records)
    assert f"document_id={doc.id}" in joined
    assert f"session_id={doc.session_id}" in joined


# --- F-02/F-03/B-02: streaming per-batch embed-insert-meter-commit --------


def _fake_embedding_factory(fail_on_call: int | None = None):
    """Returns (stub, calls) where stub mimics litellm.embedding and
    optionally raises on the Nth call (1-based)."""
    calls = []

    def stub(*, model, input, dimensions, timeout):
        calls.append(list(input))
        if fail_on_call is not None and len(calls) == fail_on_call:
            raise RuntimeError("embedding api down")
        return SimpleNamespace(
            data=[{"embedding": [0.1] * 8} for _ in input]
        )

    return stub, calls


def test_batches_commit_incrementally_and_resume_skips_paid_batches(
    db_session, setup_doc, monkeypatch
):
    doc = db_session.get(Document, setup_doc)
    monkeypatch.setattr("services.ingestion_service.EMBED_BATCH", 2)
    chunks = [
        chunking.Chunk(text=f"c{i}", page=1, chunk_idx=i) for i in range(5)
    ]
    stored_rows = []

    def fake_insert(db, *, session_id, document_id, rows):
        fresh = [r for r in rows if r[0] not in {x[0] for x in stored_rows}]
        stored_rows.extend(fresh)
        return len(fresh)

    monkeypatch.setattr(
        "services.ingestion_service.pgvector_store.insert_chunks", fake_insert
    )
    # Expose the persisted indexes to the skip-set query:
    monkeypatch.setattr(
        "services.ingestion_service._existing_chunk_indexes",
        lambda db, doc_id: {r[0] for r in stored_rows},
        raising=False,
    )
    stub, calls = _fake_embedding_factory(fail_on_call=2)
    monkeypatch.setattr("services.ingestion_service.litellm.embedding", stub)

    from services import ingestion_service

    with pytest.raises(RuntimeError):
        ingestion_service._embed_and_store(
            db_session, doc, chunks, user_id=None
        )
    assert [r[0] for r in stored_rows] == [0, 1]  # batch 1 survived

    stub2, calls2 = _fake_embedding_factory()
    monkeypatch.setattr("services.ingestion_service.litellm.embedding", stub2)
    n = ingestion_service._embed_and_store(
        db_session, doc, chunks, user_id=None
    )
    assert n == 3  # only the unpaid chunks were embedded and stored
    assert sorted(r[0] for r in stored_rows) == [0, 1, 2, 3, 4]
    assert all(len(c) <= 2 for c in calls2)  # still batched


def test_metering_commits_per_batch(db_session, setup_doc, monkeypatch):
    doc = db_session.get(Document, setup_doc)
    monkeypatch.setattr("services.ingestion_service.EMBED_BATCH", 1)
    chunks = [
        chunking.Chunk(text=f"c{i}", page=1, chunk_idx=i) for i in range(2)
    ]
    monkeypatch.setattr(
        "services.ingestion_service.pgvector_store.insert_chunks",
        lambda db, **kw: len(kw["rows"]),
    )
    metered = []
    monkeypatch.setattr(
        "services.ingestion_service.cost_meter.meter_embedding_response",
        lambda db, resp, **kw: metered.append(len(kw["texts"])),
    )
    ledger_seen_at_call = []
    stub, calls = _fake_embedding_factory()

    def spying_stub(**kw):
        ledger_seen_at_call.append(len(metered))
        return stub(**kw)

    monkeypatch.setattr(
        "services.ingestion_service.litellm.embedding", spying_stub
    )

    from services import ingestion_service

    ingestion_service._embed_and_store(db_session, doc, chunks, user_id=None)
    # Before batch 2's embedding call, batch 1 was already metered:
    assert ledger_seen_at_call == [0, 1]


def test_run_holds_no_db_transaction_during_blob_load_and_extract(
    db_session, insert_capture, mock_embed, monkeypatch, tmp_path
):
    """F-02: blob load, extraction and chunking are the slow, memory-heavy part
    of ingestion. Holding a pooled DB connection across them starves the pool
    under concurrent uploads, so run() must close its session first and
    re-acquire one only for the embed/persist phase."""
    from sqlalchemy.orm import sessionmaker

    from services import ingestion_service

    db_session.add(User(id="u_notx"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_notx",
            user_id="u_notx",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_notx", filename="notes.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    created: list = []
    real_factory = sessionmaker(
        autocommit=False, autoflush=False, bind=db_session.get_bind()
    )

    def recording_factory():
        s = real_factory()
        created.append(s)
        return s

    monkeypatch.setattr("services.ingestion_service.SessionLocal", recording_factory)
    _write_blob_stub(monkeypatch, tmp_path, doc.id, doc.filename, content=b"hello there")

    # Recorded, not asserted, inside the fakes: run() catches Exception (and
    # therefore AssertionError) and would swallow a failed assertion.
    in_tx: list[bool] = []

    real_load = ingestion_service._load_blob
    real_extract = ingestion_service._extract
    real_chunk = ingestion_service.chunking.chunk_text

    def spy_load(*a, **kw):
        in_tx.append(created[-1].in_transaction())
        return real_load(*a, **kw)

    def spy_extract(*a, **kw):
        in_tx.append(created[-1].in_transaction())
        return real_extract(*a, **kw)

    def spy_chunk(*a, **kw):
        in_tx.append(created[-1].in_transaction())
        return real_chunk(*a, **kw)

    monkeypatch.setattr("services.ingestion_service._load_blob", spy_load)
    monkeypatch.setattr("services.ingestion_service._extract", spy_extract)
    monkeypatch.setattr("services.ingestion_service.chunking.chunk_text", spy_chunk)

    ingestion_service.run(doc.id)

    db_session.expire_all()
    refreshed = db_session.get(Document, doc.id)
    assert refreshed.status == "ready", refreshed.error
    assert in_tx == [False, False, False]


def test_run_marks_failed_when_extract_raises_outside_session(
    db_session, insert_capture, mock_embed, monkeypatch, tmp_path
):
    """F-02 regression: the failure arms run after the session was closed, so
    they must re-fetch the Document by id rather than touch a detached
    instance."""
    from sqlalchemy.orm import sessionmaker

    from services import ingestion_service

    db_session.add(User(id="u_notx2"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_notx2",
            user_id="u_notx2",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_notx2", filename="notes.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )
    _write_blob_stub(monkeypatch, tmp_path, doc.id, doc.filename, content=b"hello there")

    def boom(*a, **kw):
        raise RuntimeError("extract exploded")

    monkeypatch.setattr("services.ingestion_service._extract", boom)

    ingestion_service.run(doc.id)

    db_session.expire_all()
    refreshed = db_session.get(Document, doc.id)
    assert refreshed.status == "failed"
    assert refreshed.error == ingestion_service.ERR_EXTRACTION_FAILED


def test_run_invalidates_session_chunk_centroid(
    db_session, insert_capture, mock_embed, monkeypatch, tmp_path
):
    """F-05: new chunks move the session's mean embedding, so the materialised
    centroid must be dropped; the next chat turn recomputes it once."""
    from sqlalchemy.orm import sessionmaker

    from config import settings
    from services import ingestion_service

    db_session.add(User(id="u_cinv"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_cinv",
            user_id="u_cinv",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
            chunk_centroid=[0.3] * settings.embedding_dim,
        )
    )
    db_session.flush()
    doc = Document(session_id="s_cinv", filename="notes.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )
    _write_blob_stub(monkeypatch, tmp_path, doc.id, doc.filename, content=b"hello there")

    ingestion_service.run(doc.id)

    db_session.expire_all()
    assert db_session.get(Document, doc.id).status == "ready"
    assert db_session.get(SessionModel, "s_cinv").chunk_centroid is None


def test_run_passes_max_chunks_and_fails_on_early_abort(
    db_session, insert_capture, mock_embed, monkeypatch, tmp_path
):
    """F-03: the cap is enforced inside the chunker (early abort), not by
    counting a fully materialised chunk list afterwards."""
    from sqlalchemy.orm import sessionmaker

    from config import settings
    from services import ingestion_service

    db_session.add(User(id="u_cap2"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_cap2",
            user_id="u_cap2",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    doc = Document(session_id="s_cap2", filename="big.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )
    _write_blob_stub(monkeypatch, tmp_path, doc.id, doc.filename, content=b"word " * 50)

    seen: dict = {}

    def fake_chunk_text(pages, **kw):
        seen.update(kw)
        raise chunking.ChunkLimitExceeded(kw["max_chunks"])

    monkeypatch.setattr("services.ingestion_service.chunking.chunk_text", fake_chunk_text)

    ingestion_service.run(doc.id)

    assert seen["max_chunks"] == settings.max_chunks
    db_session.expire_all()
    refreshed = db_session.get(Document, doc.id)
    assert refreshed.status == "failed"
    assert refreshed.error == "document too large to ingest (chunk limit)"
    assert insert_capture == []


def test_partial_ingest_failure_still_invalidates_centroid(
    db_session, mock_embed, monkeypatch, tmp_path
):
    """F-05: _embed_and_store commits per batch, so a failure mid-document
    leaves durable new chunks. The centroid must already be NULL by then --
    otherwise a stale mean survives with nothing left to refresh it."""
    from sqlalchemy.orm import sessionmaker

    from config import settings
    from services import ingestion_service

    db_session.add(User(id="u_cinv2"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s_cinv2",
            user_id="u_cinv2",
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
            chunk_centroid=[0.3] * settings.embedding_dim,
        )
    )
    db_session.flush()
    doc = Document(session_id="s_cinv2", filename="notes.txt", status="pending")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    monkeypatch.setattr(
        "services.ingestion_service.SessionLocal",
        sessionmaker(autocommit=False, autoflush=False, bind=db_session.get_bind()),
    )
    monkeypatch.setattr("services.ingestion_service.EMBED_BATCH", 1)
    _write_blob_stub(
        monkeypatch, tmp_path, doc.id, doc.filename, content=b"word " * 1200
    )

    calls = {"n": 0}

    def fail_on_second_batch(db, *, session_id, document_id, rows):
        calls["n"] += 1
        if calls["n"] > 1:
            raise RuntimeError("pgvector insert failed on batch 2")
        return len(rows)

    monkeypatch.setattr(
        "services.ingestion_service.pgvector_store.insert_chunks", fail_on_second_batch
    )

    ingestion_service.run(doc.id)

    db_session.expire_all()
    assert calls["n"] > 1
    assert db_session.get(Document, doc.id).status == "failed"
    assert db_session.get(SessionModel, "s_cinv2").chunk_centroid is None


# --- C-11: documents.error is an enumerated, leak-free string -------------


def test_extraction_failure_hides_exception_text_but_logs_it(
    setup_doc, insert_capture, mock_embed, db_session, monkeypatch, tmp_path, caplog
):
    """C-11: documents.error is rendered verbatim by the frontend, so a raw
    exception message would leak server paths to the browser. The persisted
    string must be one of the enumerated constants; the original text must
    still reach the log for operators."""
    import logging

    _write_blob_stub(monkeypatch, tmp_path, setup_doc, "x.pdf")

    def boom(_blob, _filename):
        raise RuntimeError("/srv/secret/path: boom")

    monkeypatch.setattr("services.ingestion_service._extract", boom)
    from services import ingestion_service

    with caplog.at_level(logging.ERROR, logger="services.ingestion_service"):
        ingestion_service.run(setup_doc)

    db_session.expire_all()
    doc = db_session.get(Document, setup_doc)
    assert doc.status == "failed"
    assert doc.error == ingestion_service.ERR_EXTRACTION_FAILED
    assert "secret" not in doc.error
    assert "/srv/secret/path: boom" in " ".join(
        r.getMessage() for r in caplog.records
    )


def test_generic_stage_failure_uses_the_catch_all_message(
    setup_doc, insert_capture, mock_pdf, mock_embed, db_session, monkeypatch, tmp_path
):
    """A failure outside extract/embed (here: the keyword merge) maps to the
    generic constant, never to str(e)."""
    _write_blob_stub(monkeypatch, tmp_path, setup_doc, "x.pdf")

    def boom(db, session_id, stems):
        raise RuntimeError("kw merge exploded")

    monkeypatch.setattr(
        "services.ingestion_service.keyword_index.merge_into_session", boom
    )
    from services import ingestion_service

    ingestion_service.run(setup_doc)
    db_session.expire_all()
    doc = db_session.get(Document, setup_doc)
    assert doc.status == "failed"
    assert doc.error == ingestion_service.ERR_INGESTION_FAILED


def test_every_assigned_document_error_is_enumerated():
    """C-11 guard rail: no future edit may assign a free-form string (or an
    f-string / str(e)) to doc.error in this module."""
    import inspect
    import re

    from services import ingestion_service

    src = inspect.getsource(ingestion_service)
    assigned = re.findall(r"\.error\s*=\s*(.+)", src)
    assert assigned, "expected at least one doc.error assignment"
    namespace = vars(ingestion_service)
    for expr in assigned:
        expr = expr.split("#")[0].strip()
        if expr == "None":
            continue
        assert "str(" not in expr and not expr.startswith(("f'", 'f"')), (
            f"doc.error must not carry exception text, got {expr!r}"
        )
        # Every remaining form must resolve into the enumerated set, for
        # every stage the generic arm can classify. eval() is safe here: the
        # expression comes from this repo's own module source read via
        # inspect.getsource, never from user input or a network payload.
        for stage in ingestion_service._STAGE_ERRORS:
            value = eval(expr, dict(namespace), {"stage": stage})
            assert value in ingestion_service.INGEST_ERROR_MESSAGES, (
                f"{expr!r} -> {value!r} is not an enumerated message"
            )


def test_ingest_error_messages_covers_the_upload_route_string():
    """upload.py writes its own failure string onto the same column; the
    frozenset is the single inventory of everything the frontend can render."""
    from services import ingestion_service

    assert (
        ingestion_service.ERR_STORAGE_WRITE
        in ingestion_service.INGEST_ERROR_MESSAGES
    )
    assert len(ingestion_service.INGEST_ERROR_MESSAGES) == 6
