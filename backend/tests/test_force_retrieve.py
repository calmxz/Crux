"""F-56: REQUIRED + ready docs -> excerpts injected server-side."""

import asyncio

from agent import prompts
from tests.prompt_state_factory import make_prompt_state


def test_prompt_renders_provided_block():
    out = prompts.build_dynamic_context(
        make_prompt_state(
            retrieval_required=True,
            prefetched_excerpts=["<document_excerpt doc_id='d1'>text</document_excerpt>"],
        )
    )
    assert "RETRIEVAL: PROVIDED" in out
    assert "PREFETCHED_EXCERPTS:" in out
    assert "document_excerpt" in out


def test_prompt_without_prefetch_keeps_required_label():
    out = prompts.build_dynamic_context(make_prompt_state(retrieval_required=True))
    assert "RETRIEVAL: REQUIRED" in out


def test_prefetch_returns_none_on_failure(db_session, monkeypatch, fake_llm):
    from services import retrieval_service

    fake_llm.embed_errors = [RuntimeError("embed down")]
    monkeypatch.setattr(
        "services.retrieval_service.documents_service.has_ready_document",
        lambda db, sid: True,
    )
    result = asyncio.run(retrieval_service.prefetch_for_prompt(db_session, "s1", "u1", "query"))
    assert result is None
