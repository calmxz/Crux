"""Verify deterministic LLM stub used by e2e."""

from decimal import Decimal

import litellm
import pytest

from agent import prompts
from agent._stub import stub_response
from config import settings
from lib import error_codes
from services import llm


def test_stub_fresh_marker_no_summary():
    system_prompt = "rules\n\nLAST_SESSION_SUMMARY: none"
    messages = [{"role": "user", "content": "what is recursion?"}]
    out = stub_response(messages, system_prompt)
    assert out.startswith("[STUB:fresh]")
    assert "what is recursion?" in out


def test_stub_resumed_marker_when_summary_present():
    system_prompt = "rules\n\nLAST_SESSION_SUMMARY: Learner explored base cases and tail recursion."
    messages = [{"role": "user", "content": "continue please"}]
    out = stub_response(messages, system_prompt)
    assert out.startswith("[STUB:resumed:")
    assert "continue please" in out


def test_stub_resumed_marker_is_stable_per_summary():
    system_prompt = "LAST_SESSION_SUMMARY: same text"
    messages = [{"role": "user", "content": "hi"}]
    a = stub_response(messages, system_prompt)
    b = stub_response(messages, system_prompt)
    assert a == b


def test_stub_handles_empty_user_message():
    system_prompt = "LAST_SESSION_SUMMARY: none"
    out = stub_response([], system_prompt)
    assert out.startswith("[STUB:fresh]")
    assert "(empty)" in out


def test_settings_auto_enables_when_gemini_key_is_test(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "test")
    monkeypatch.setattr(settings, "llm_stub", False)
    assert settings.llm_stub_enabled is True


def test_settings_auto_enables_when_llm_stub_flag_set(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")
    monkeypatch.setattr(settings, "llm_stub", True)
    assert settings.llm_stub_enabled is True


def test_settings_disabled_when_neither_set(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")
    monkeypatch.setattr(settings, "llm_stub", False)
    assert settings.llm_stub_enabled is False


# --- StubProvider (#413) ------------------------------------------------------


@pytest.fixture
def no_litellm(monkeypatch):
    """Records any litellm network call; the test's teardown asserts none."""
    calls: list[str] = []

    def record(name):
        def call(*_a, **_k):
            calls.append(name)
            raise AssertionError("stub mode called litellm")

        return call

    for name in ("completion", "acompletion", "embedding", "aembedding"):
        monkeypatch.setattr(litellm, name, record(name))
    yield calls
    assert calls == []


async def _stream_text(system_prompt: str, user: str) -> tuple[str, list[str], object]:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user},
    ]
    ps = await llm.StubProvider().stream(
        messages, tools=[], tool_choice="auto", temperature=0.2, timeout=5
    )
    tokens = [t async for t in ps]
    return "".join(tokens), tokens, ps


async def test_stub_provider_streams_resumed_marker_from_a_rendered_prompt(no_litellm):
    system_prompt = prompts.build_system_prompt({"last_session_summary": "covered joins"})

    text, tokens, ps = await _stream_text(system_prompt, "continue please")

    assert text.startswith("[STUB:resumed:")
    assert text.endswith("] Echo: continue please")
    assert len(tokens) > 1  # chunked, so the UI still exercises the delta path
    assert ps.received is True
    assert ps.text == text
    assert ps.tool_calls == []
    assert ps.priced() == (Decimal("0"), {})
    assert ps.estimate() == Decimal("0")
    await ps.aclose()


async def test_stub_provider_streams_fresh_marker_without_a_summary(no_litellm):
    system_prompt = prompts.build_system_prompt({})

    text, _, _ = await _stream_text(system_prompt, "what is recursion?")

    assert text == "[STUB:fresh] Echo: what is recursion?"


async def test_stub_provider_complete_raises_unavailable(no_litellm):
    with pytest.raises(llm.LlmUnavailable):
        await llm.StubProvider().complete(
            [{"role": "user", "content": "hi"}], temperature=0.2, timeout=5
        )


async def test_stub_provider_embeddings_raise_unavailable(no_litellm):
    provider = llm.StubProvider()
    with pytest.raises(llm.LlmUnavailable):
        provider.embed(["a"])
    with pytest.raises(llm.LlmUnavailable):
        await provider.aembed(["a"])


def test_unavailable_carries_a_non_cap_code():
    assert llm.LlmUnavailable().code == error_codes.LLM_UNAVAILABLE
    assert llm.LlmUnavailable().cap is None


def test_get_returns_the_stub_whenever_stub_mode_is_on(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")
    monkeypatch.setattr(settings, "llm_stub", True)
    monkeypatch.setattr(llm, "_provider", object())
    assert isinstance(llm.get().provider, llm.StubProvider)

    monkeypatch.setattr(settings, "llm_stub", False)
    assert not isinstance(llm.get().provider, llm.StubProvider)


def test_summary_label_renders_the_line_the_stub_reads():
    ctx = prompts.build_dynamic_context({"last_session_summary": "x"})
    assert (
        f"\n{prompts.LAST_SESSION_SUMMARY_LABEL}: <untrusted_summary>x</untrusted_summary>\n" in ctx
    )
    assert prompts.LAST_SESSION_SUMMARY_LABEL == "LAST_SESSION_SUMMARY"


async def test_stub_stream_skips_the_cost_gate(db_session, monkeypatch, no_litellm):
    # The stub never spends, so a capped user's stub turn still echoes and
    # leaves no ledger or call-log row.
    from db.models import LlmCallLog
    from services import cost_meter

    monkeypatch.setattr(settings, "llm_stub", True)
    cost_meter.record_cost(db_session, "u-capped", Decimal(str(settings.llm_hard_cap_usd)))
    db_session.commit()
    meter = llm.Meter("u-capped", "s1", "chat")
    messages = [
        {"role": "system", "content": prompts.build_system_prompt({})},
        {"role": "user", "content": "hi"},
    ]

    async with llm.get().stream(messages, meter=meter, temperature=0.2, timeout=5) as s:
        text = "".join([ev.text async for ev in s])

    assert text == "[STUB:fresh] Echo: hi"
    assert s.cost == Decimal("0")
    assert cost_meter.current_spend(db_session, "u-capped") == Decimal(
        str(settings.llm_hard_cap_usd)
    )
    assert db_session.query(LlmCallLog).count() == 0
