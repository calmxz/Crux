"""Verify deterministic LLM stub used by e2e."""

from agent._stub import stub_response
from config import settings


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
