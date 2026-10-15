import litellm
import pytest

from config import settings
from lib import llm_retry


def _conn_err():
    return litellm.APIConnectionError(message="boom", llm_provider="gemini", model="m")


def test_retry_sync_recovers_after_transient_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_retry_attempts", 2)
    calls = {"n": 0}
    slept = []
    monkeypatch.setattr(llm_retry.time, "sleep", slept.append)

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise _conn_err()
        return "ok"

    assert llm_retry.retry_sync(fn) == "ok"
    assert calls["n"] == 3
    assert slept == [0.5, 1.0]  # exponential from base_delay_s


def test_retry_sync_gives_up_after_attempts(monkeypatch):
    monkeypatch.setattr(settings, "llm_retry_attempts", 1)
    monkeypatch.setattr(llm_retry.time, "sleep", lambda _s: None)

    def fn():
        raise _conn_err()

    with pytest.raises(litellm.APIConnectionError):
        llm_retry.retry_sync(fn)


def test_retry_sync_does_not_retry_non_transient(monkeypatch):
    monkeypatch.setattr(settings, "llm_retry_attempts", 3)
    monkeypatch.setattr(llm_retry.time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise ValueError("bad input")

    with pytest.raises(ValueError):
        llm_retry.retry_sync(fn)
    assert calls["n"] == 1


def test_retry_sync_zero_attempts_is_single_call(monkeypatch):
    monkeypatch.setattr(settings, "llm_retry_attempts", 0)
    monkeypatch.setattr(llm_retry.time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise _conn_err()

    with pytest.raises(litellm.APIConnectionError):
        llm_retry.retry_sync(fn)
    assert calls["n"] == 1
