"""TDD: services.documents_service aggregate status + ready gate."""

import json

import pytest

from config import settings
from contracts import TopicProfile
from db.models import ChunkEmbedding, Document, User
from db.models import Session as SessionModel
from services import documents_service

SID = "sess_docs"
UID = "u_docs"


def _seed_session(db):
    db.add(User(id=UID))
    db.flush()
    db.add(
        SessionModel(
            id=SID,
            user_id=UID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db.commit()


def _add_doc(db, status):
    doc = Document(session_id=SID, filename=f"{status}.pdf", status=status)
    db.add(doc)
    db.commit()


def test_status_none_when_no_documents(db_session):
    _seed_session(db_session)
    assert documents_service.session_ingestion_status(db_session, SID) is None
    assert documents_service.has_ready_document(db_session, SID) is False


def test_status_pending_when_any_pending(db_session):
    _seed_session(db_session)
    _add_doc(db_session, "ready")
    _add_doc(db_session, "pending")
    assert documents_service.session_ingestion_status(db_session, SID) == "pending"


def test_status_ready_when_any_ready_and_none_pending(db_session):
    _seed_session(db_session)
    _add_doc(db_session, "ready")
    _add_doc(db_session, "failed")
    assert documents_service.session_ingestion_status(db_session, SID) == "ready"
    assert documents_service.has_ready_document(db_session, SID) is True


def test_status_failed_when_all_failed(db_session):
    _seed_session(db_session)
    _add_doc(db_session, "failed")
    _add_doc(db_session, "failed")
    assert documents_service.session_ingestion_status(db_session, SID) == "failed"
    assert documents_service.has_ready_document(db_session, SID) is False


def test_list_document_statuses_orders_oldest_first(db_session):
    _seed_session(db_session)
    _add_doc(db_session, "ready")
    _add_doc(db_session, "pending")
    docs = documents_service.list_document_statuses(db_session, SID)
    assert [d.status for d in docs] == ["ready", "pending"]


def test_retrieval_gate_uses_any_ready_not_latest(db_session, monkeypatch):
    """Regression: a newer pending doc must NOT mask an older ready doc."""
    from agent.types import ToolContext
    from contracts import RetrieveChunksArgs
    from services import retrieval_service

    _seed_session(db_session)
    _add_doc(db_session, "ready")    # older
    _add_doc(db_session, "pending")  # newer - previously masked the ready one

    captured = {}

    def fake_embedding(model, input, **_):
        from types import SimpleNamespace
        data_item = {"embedding": [0.1] * 8}
        return SimpleNamespace(data=[data_item])

    def fake_query_chunks(db, *, session_id, query_embedding, k):
        captured["called"] = True
        return []

    monkeypatch.setattr("services.retrieval_service.litellm.embedding", fake_embedding)
    monkeypatch.setattr(
        "services.retrieval_service.pgvector_store.query_chunks", fake_query_chunks
    )

    ctx = ToolContext(
        db=db_session,
        session_id=SID,
        user_id=UID,
        turn_started_at=None,
    )
    result = retrieval_service.retrieve(
        db_session, ctx, RetrieveChunksArgs(session_id=SID, query="indexes", k=5)
    )
    assert captured.get("called") is True, "gate should pass when an older doc is ready"
    # The fake query_chunks returns [] so status is "no_results", but the gate
    # passed: ok is True with no ingestion error. Under the old latest-doc logic
    # the newer pending doc masked the ready one -> error="ingestion_status=pending".
    assert result.ok is True
    assert result.error is None


def _seed_doc(db, *, user_id="u1", session_id="s1", filename="notes.pdf"):
    db.add(User(id=user_id))
    db.flush()
    db.add(SessionModel(id=session_id, user_id=user_id, topic="t", topic_profile_json="{}"))
    db.flush()
    doc = Document(session_id=session_id, filename=filename, status="ready")
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


USER_ID = "u1"


@pytest.fixture
def seeded_doc_with_chunks(db_session):
    """doc + real ChunkEmbedding rows. sqlite tolerates the pgvector column via
    its generic UserDefinedType bind/result processors, but pgvector's own
    Vector._to_db still enforces the declared dimension client-side, so the
    embedding must be settings.embedding_dim long even here."""
    from db.models import ChunkEmbedding

    doc = _seed_doc(db_session)
    for i in range(3):
        db_session.add(
            ChunkEmbedding(
                session_id=doc.session_id,
                document_id=doc.id,
                chunk_index=i,
                page=1,
                chunk_text=f"chunk {i}",
                embedding=[0.0] * settings.embedding_dim,
            )
        )
    db_session.commit()
    db_session.refresh(doc)
    return doc


def test_delete_is_atomic_rollback_keeps_chunks(db_session, monkeypatch, seeded_doc_with_chunks):
    # seeded_doc_with_chunks: doc + real ChunkEmbedding rows.
    from db.models import ChunkEmbedding

    def boom(obj):
        raise RuntimeError("crash between chunk and row delete")

    monkeypatch.setattr(db_session, "delete", boom)
    with pytest.raises(RuntimeError):
        documents_service.delete_document(db_session, seeded_doc_with_chunks.id, USER_ID)
    db_session.rollback()
    # F-28: the chunk delete must not have been committed on its own.
    assert (
        db_session.query(ChunkEmbedding)
        .filter_by(document_id=seeded_doc_with_chunks.id)
        .count()
        > 0
    )


def test_delete_removes_blob_from_store(db_session, monkeypatch, seeded_doc_with_chunks):
    deleted_keys = []

    class RecordingStore:
        def delete(self, key):
            deleted_keys.append(key)

    monkeypatch.setattr(
        "services.documents_service.object_store.get_store", lambda: RecordingStore()
    )
    documents_service.delete_document(db_session, seeded_doc_with_chunks.id, USER_ID)
    assert deleted_keys == [f"{seeded_doc_with_chunks.id}_{seeded_doc_with_chunks.filename}"]


def test_delete_document_removes_row_chunks_and_file(db_session, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "services.documents_service.pgvector_store.delete_document_chunks",
        lambda db, document_id: calls.append(document_id) or 3,
    )
    monkeypatch.setattr("services.object_store.settings.uploads_path", str(tmp_path))

    doc = _seed_doc(db_session)
    disk = tmp_path / f"{doc.id}_{doc.filename}"
    disk.write_bytes(b"%PDF-fake")

    documents_service.delete_document(db_session, document_id=doc.id, user_id="u1")

    assert calls == [doc.id]
    assert db_session.get(Document, doc.id) is None
    assert not disk.exists()


def test_delete_document_missing_raises_not_found(db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "services.documents_service.pgvector_store.delete_document_chunks",
        lambda db, document_id: 0,
    )
    monkeypatch.setattr("services.object_store.settings.uploads_path", str(tmp_path))
    with pytest.raises(documents_service.DocumentNotFound):
        documents_service.delete_document(db_session, document_id=999, user_id="u1")


def test_delete_document_other_user_raises_not_found(db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "services.documents_service.pgvector_store.delete_document_chunks",
        lambda db, document_id: 0,
    )
    monkeypatch.setattr("services.object_store.settings.uploads_path", str(tmp_path))
    doc = _seed_doc(db_session, user_id="owner", session_id="s_owner")
    with pytest.raises(documents_service.DocumentNotFound):
        documents_service.delete_document(db_session, document_id=doc.id, user_id="intruder")
    # Row must remain intact.
    assert db_session.get(Document, doc.id) is not None


def test_delete_document_tolerates_missing_file(db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "services.documents_service.pgvector_store.delete_document_chunks",
        lambda db, document_id: 0,
    )
    monkeypatch.setattr("services.object_store.settings.uploads_path", str(tmp_path))
    doc = _seed_doc(db_session)
    # No file on disk.
    documents_service.delete_document(db_session, document_id=doc.id, user_id="u1")
    assert db_session.get(Document, doc.id) is None


def test_delete_document_filename_traversal_is_contained(db_session, monkeypatch, tmp_path):
    """A filename with an embedded ../ must not unlink a file outside uploads_path."""
    monkeypatch.setattr(
        "services.documents_service.pgvector_store.delete_document_chunks",
        lambda db, document_id: 0,
    )
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr("services.object_store.settings.uploads_path", str(uploads))

    # A file one level above the uploads dir that a traversal filename would target.
    outside = tmp_path / "secret.txt"
    outside.write_text("keep me")

    doc = _seed_doc(db_session, filename="x/../../secret.txt")
    documents_service.delete_document(db_session, document_id=doc.id, user_id="u1")

    assert outside.exists(), "traversal escaped the uploads directory"
    assert db_session.get(Document, doc.id) is None


def test_delete_document_tolerates_unlink_oserror(db_session, monkeypatch, tmp_path):
    """A locked/undeletable file (OSError on unlink) must not 500: the DB row and
    chunks are still deleted and the call returns normally."""
    monkeypatch.setattr(
        "services.documents_service.pgvector_store.delete_document_chunks",
        lambda db, document_id: 0,
    )
    monkeypatch.setattr("services.object_store.settings.uploads_path", str(tmp_path))

    doc = _seed_doc(db_session)
    disk = tmp_path / f"{doc.id}_{doc.filename}"
    disk.write_bytes(b"%PDF-fake")

    import pathlib

    def _raise(self, *a, **k):
        raise PermissionError("locked")

    monkeypatch.setattr(pathlib.Path, "unlink", _raise)

    # Must not raise.
    documents_service.delete_document(db_session, document_id=doc.id, user_id="u1")
    assert db_session.get(Document, doc.id) is None


@pytest.mark.parametrize(
    "total,pending,ready,expected",
    [
        (0, 0, 0, None),
        (2, 1, 1, "pending"),
        (2, 0, 1, "ready"),
        (2, 0, 0, "failed"),
    ],
)
def test_status_from_counts_mirrors_aggregate_status(total, pending, ready, expected):
    assert documents_service.status_from_counts(total, pending, ready) == expected


def test_aggregate_status_treats_processing_as_in_flight():
    assert documents_service.aggregate_status(["processing"]) == "pending"
    assert documents_service.aggregate_status(["ready", "processing"]) == "pending"


@pytest.mark.parametrize(
    "total,pending,ready,processing,expected",
    [
        (1, 0, 0, 1, "pending"),
        (2, 0, 1, 1, "pending"),
    ],
)
def test_status_from_counts_treats_processing_as_in_flight(
    total, pending, ready, processing, expected
):
    assert (
        documents_service.status_from_counts(total, pending, ready, processing)
        == expected
    )


def test_delete_document_invalidates_session_chunk_centroid(db_session, monkeypatch, tmp_path):
    """F-05: removing a document changes the session's mean embedding, so the
    materialised centroid must be dropped in the same transaction."""
    monkeypatch.setattr(
        "services.documents_service.pgvector_store.delete_document_chunks",
        lambda db, document_id: 0,
    )
    monkeypatch.setattr("services.object_store.settings.uploads_path", str(tmp_path))

    doc = _seed_doc(db_session)
    sess = db_session.get(SessionModel, doc.session_id)
    sess.chunk_centroid = [0.4] * settings.embedding_dim
    db_session.commit()

    documents_service.delete_document(db_session, document_id=doc.id, user_id="u1")

    db_session.expire_all()
    assert db_session.get(SessionModel, "s1").chunk_centroid is None


def _add_doc_with_text(db, session_id, filename, texts, status="ready"):
    doc = Document(session_id=session_id, filename=filename, status=status)
    db.add(doc)
    db.flush()
    for i, text in enumerate(texts):
        db.add(
            ChunkEmbedding(
                session_id=session_id,
                document_id=doc.id,
                chunk_index=i,
                page=1,
                chunk_text=text,
                embedding=[0.0] * settings.embedding_dim,
            )
        )
    db.commit()
    db.refresh(doc)
    return doc


def _kw_index(db, session_id):
    db.expire_all()
    return json.loads(db.get(SessionModel, session_id).kw_index_json or "[]")


def test_delete_document_rebuilds_keyword_index_from_survivors(
    db_session, monkeypatch, tmp_path
):
    """#430: a deleted file's stems must leave the session keyword index, or
    chat's lexical gate keeps forcing retrieval for a file that is gone."""
    from lib import keyword_index

    monkeypatch.setattr("services.object_store.settings.uploads_path", str(tmp_path))
    db_session.add(User(id="u1"))
    db_session.flush()
    db_session.add(SessionModel(id="s1", user_id="u1", topic="t", topic_profile_json="{}"))
    db_session.commit()
    photo = _add_doc_with_text(
        db_session, "s1", "bio.pdf", ["photosynthesis chlorophyll", "mitochondria"]
    )
    tcp = _add_doc_with_text(db_session, "s1", "net.pdf", ["router packets"])
    # A non-ready document's chunks are not part of the index.
    _add_doc_with_text(db_session, "s1", "wip.pdf", ["volcano"], status="pending")
    sess = db_session.get(SessionModel, "s1")
    sess.kw_index_json = json.dumps(
        sorted(keyword_index.build_from_text("photosynthesis chlorophyll mitochondria router packets"))
    )
    db_session.commit()

    documents_service.delete_document(db_session, photo.id, "u1")
    assert _kw_index(db_session, "s1") == sorted(keyword_index.build_from_text("router packets"))

    documents_service.delete_document(db_session, tcp.id, "u1")
    assert _kw_index(db_session, "s1") == []


def test_delete_document_locks_session_before_touching_chunks(
    db_session, monkeypatch, seeded_doc_with_chunks
):
    """#430: the session row lock is taken before chunks are deleted or read,
    so a concurrently finishing ingestion's merge unions onto the rebuilt set."""
    calls = []
    real_lock = documents_service.profile_service.lock_session_row
    real_delete = documents_service.pgvector_store.delete_document_chunks

    def spy_lock(db, session_id):
        calls.append("lock")
        return real_lock(db, session_id)

    def spy_delete(db, document_id):
        calls.append("delete_chunks")
        return real_delete(db, document_id)

    monkeypatch.setattr(documents_service.profile_service, "lock_session_row", spy_lock)
    monkeypatch.setattr(documents_service.pgvector_store, "delete_document_chunks", spy_delete)

    documents_service.delete_document(db_session, seeded_doc_with_chunks.id, USER_ID)
    assert calls == ["lock", "delete_chunks"]
