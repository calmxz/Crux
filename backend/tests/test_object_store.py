"""TDD: services/object_store.py (adversarial review F-15, owner decision Q4)."""

import pytest

from services import object_store
from services.object_store import LocalDiskStore, ObjectNotFound


def test_key_for():
    assert object_store.key_for(7, "notes.pdf") == "7_notes.pdf"


def test_local_put_get_roundtrip(tmp_path):
    store = LocalDiskStore(str(tmp_path))
    store.put("1_a.pdf", b"hello")
    assert store.get("1_a.pdf") == b"hello"
    assert (tmp_path / "1_a.pdf").read_bytes() == b"hello"


def test_local_put_creates_root(tmp_path):
    store = LocalDiskStore(str(tmp_path / "uploads"))
    store.put("1_a.pdf", b"x")
    assert store.get("1_a.pdf") == b"x"


def test_local_get_missing_raises(tmp_path):
    store = LocalDiskStore(str(tmp_path))
    with pytest.raises(ObjectNotFound):
        store.get("9_missing.pdf")


def test_local_delete_is_idempotent(tmp_path):
    store = LocalDiskStore(str(tmp_path))
    store.put("1_a.pdf", b"x")
    store.delete("1_a.pdf")
    store.delete("1_a.pdf")  # second call must not raise
    with pytest.raises(ObjectNotFound):
        store.get("1_a.pdf")


def test_local_rejects_traversal_keys(tmp_path):
    store = LocalDiskStore(str(tmp_path))
    with pytest.raises(ValueError):
        store.put("../evil.pdf", b"x")
    with pytest.raises(ValueError):
        store.get("../../etc/passwd")


def test_get_store_defaults_to_local_disk(monkeypatch, tmp_path):
    monkeypatch.setattr("services.object_store.settings.uploads_store", "local")
    monkeypatch.setattr("services.object_store.settings.uploads_path", str(tmp_path))
    store = object_store.get_store()
    assert isinstance(store, LocalDiskStore)


class FakeS3Client:
    """Duck-typed stand-in for boto3's S3 client (records calls, in-memory blobs)."""

    def __init__(self):
        self.blobs = {}

    def put_object(self, Bucket, Key, Body):
        self.blobs[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        try:
            import io

            return {"Body": io.BytesIO(self.blobs[(Bucket, Key)])}
        except KeyError:
            import botocore.exceptions

            raise botocore.exceptions.ClientError(
                {"Error": {"Code": "NoSuchKey"}}, "GetObject"
            ) from None

    def delete_object(self, Bucket, Key):
        self.blobs.pop((Bucket, Key), None)


def _r2(client):
    from services.object_store import R2ObjectStore

    return R2ObjectStore(
        endpoint_url="https://acct.r2.cloudflarestorage.com",
        access_key_id="k",
        secret_access_key="s",
        bucket="crux",
        client=client,
    )


def test_r2_put_get_roundtrip_uses_uploads_prefix():
    fake = FakeS3Client()
    store = _r2(fake)
    store.put("7_a.pdf", b"blob")
    assert ("crux", "uploads/7_a.pdf") in fake.blobs
    assert store.get("7_a.pdf") == b"blob"


def test_r2_get_missing_raises_object_not_found():
    store = _r2(FakeS3Client())
    with pytest.raises(ObjectNotFound):
        store.get("9_missing.pdf")


def test_r2_delete_is_idempotent():
    fake = FakeS3Client()
    store = _r2(fake)
    store.put("7_a.pdf", b"blob")
    store.delete("7_a.pdf")
    store.delete("7_a.pdf")  # must not raise
    assert fake.blobs == {}


def test_get_store_returns_r2_when_configured(monkeypatch):
    monkeypatch.setattr("services.object_store.settings.uploads_store", "r2")
    monkeypatch.setattr("services.object_store.settings.r2_endpoint", "https://e")
    monkeypatch.setattr("services.object_store.settings.r2_access_key_id", "k")
    monkeypatch.setattr("services.object_store.settings.r2_secret_access_key", "s")
    monkeypatch.setattr("services.object_store.settings.r2_bucket", "b")
    from services.object_store import R2ObjectStore

    assert isinstance(object_store.get_store(), R2ObjectStore)
