"""TDD: DELETE /api/documents/{document_id}."""

import pytest

from contracts import TopicProfile
from db.models import Document, User
from db.models import Session as SessionModel

OWNER = "owner1"
SESSION_ID = "sess_del"


@pytest.fixture
def seeded(db_session):
    db_session.add(User(id=OWNER))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=OWNER,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    doc = Document(session_id=SESSION_ID, filename="notes.pdf", status="ready")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


@pytest.fixture(autouse=True)
def stub_chunk_delete(monkeypatch):
    """SQLite can't hold ChunkEmbedding rows; stub the vector delete."""
    monkeypatch.setattr(
        "services.documents_service.pgvector_store.delete_document_chunks",
        lambda db, document_id: 0,
    )


@pytest.fixture(autouse=True)
def stub_filesystem(monkeypatch, tmp_path):
    monkeypatch.setattr("services.object_store.settings.uploads_path", str(tmp_path))


def test_delete_returns_204_and_removes_row(client, seeded, db_session):
    r = client.delete(f"/api/documents/{seeded.id}", params={"user_id": OWNER})
    assert r.status_code == 204, r.text
    assert db_session.get(Document, seeded.id) is None


def test_delete_other_users_document_404(client, seeded, db_session):
    r = client.delete(f"/api/documents/{seeded.id}", params={"user_id": "intruder"})
    assert r.status_code == 404
    assert db_session.get(Document, seeded.id) is not None


def test_delete_missing_document_404(client, seeded):
    r = client.delete("/api/documents/999999", params={"user_id": OWNER})
    assert r.status_code == 404
