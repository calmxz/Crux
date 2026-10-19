"""Settings tolerate env vars for settings that no longer exist."""

from config import Settings


def test_settings_load_with_retired_temperature_env_vars(monkeypatch):
    # #637 removed both settings; a deploy that still sets them must boot.
    monkeypatch.setenv("LLM_TEMPERATURE", "0.3")
    monkeypatch.setenv("SUMMARY_TEMPERATURE", "0.0")

    s = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]

    assert not hasattr(s, "llm_temperature")
    assert not hasattr(s, "summary_temperature")
