"""F-18: semantic_fallback_required is async (aembedding); tools.dispatch runs
in a worker thread from the agent loop."""

import asyncio
import inspect

from services import retrieval_service


def test_semantic_fallback_is_async():
    assert inspect.iscoroutinefunction(retrieval_service.semantic_fallback_required)


def test_fallback_uses_aembedding(monkeypatch, db_session, fake_llm):
    """Drives the fallback all the way to the embedding call (mirrors the
    has_ready_document / _session_centroid monkeypatch pattern used by the
    fallback tests in test_retrieval_service.py) so the recorded call actually
    proves the async embed was invoked, not just that the early-return path
    short-circuited before reaching it."""
    fake_llm.vector = [0.0] * 768
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    monkeypatch.setattr(
        "services.retrieval_service._session_centroid",
        lambda db, sid: [0.0] * 768,
    )
    result, vec = asyncio.run(
        retrieval_service.semantic_fallback_required(db_session, "nosuch", "q")
    )
    assert fake_llm.aembed_calls == [["q"]]
    assert fake_llm.embed_calls == []
    # Zero query vector vs zero centroid -> cosine similarity is 0.0 (the
    # zero-norm guard), which is below the fallback threshold -> False.
    assert result is False
    assert vec == [0.0] * 768
