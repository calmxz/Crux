"""#641: a test that registers rates leaves litellm's price state as it found it.

The tests run in pairs, in file order by design: the first registers through
the production path (cost_meter.register_rates), the second checks that the
conftest fixture put everything back before it started.
"""

from decimal import Decimal

import litellm
import litellm.utils
import pytest
from litellm import ModelResponse, Usage

from config import settings
from services import cost_meter, llm

FLASH = "gemini/gemini-3.8-flash"
MADE_UP = "openai/crux-made-up-641"
# Rates no price map ships, so seeing them proves the registration landed.
SENTINEL = {"input_per_1k": Decimal("0.004000"), "output_per_1k": Decimal("0.020000")}

# What the registering test saw before it registered, for its partner to check.
_before: dict[str, object] = {}


def _resp() -> ModelResponse:
    return ModelResponse(
        model=FLASH.split("/", 1)[-1],
        usage=Usage(prompt_tokens=1000, completion_tokens=200, total_tokens=1200),
        choices=[{"message": {"role": "assistant", "content": "hi"}}],
    )


def _runtime_registrations() -> dict:
    return {k: dict(v) for k, v in litellm.utils._runtime_registered_model_cost.items()}


def _register_sentinel(monkeypatch) -> None:
    monkeypatch.setattr(settings, "model", FLASH)
    monkeypatch.setitem(cost_meter.MODEL_RATES, FLASH, SENTINEL)
    monkeypatch.setitem(cost_meter.SCHEDULED_RATES, FLASH, [])
    _before["model_cost"] = dict(litellm.model_cost[FLASH])
    _before["runtime"] = _runtime_registrations()
    _before["registered"] = dict(cost_meter._registered)
    llm.LiteLlmProvider()._completion_cost(_resp(), [], "hi")
    assert litellm.model_cost[FLASH]["input_cost_per_token"] == pytest.approx(4e-06)


def _assert_restored() -> None:
    assert litellm.model_cost[FLASH] == _before["model_cost"]
    assert _runtime_registrations() == _before["runtime"]
    assert cost_meter._registered == _before["registered"]
    # The symptom itself: litellm prices the model at its own map's rates
    # again, not the sentinel (priced directly, so nothing re-registers).
    cost = litellm.completion_cost(completion_response=_resp(), model=FLASH)
    expected = (
        1000 * _before["model_cost"]["input_cost_per_token"]  # type: ignore[index]
        + 200 * _before["model_cost"]["output_cost_per_token"]  # type: ignore[index]
    )
    assert cost == pytest.approx(expected)


def test_registers_sentinel_rates(monkeypatch):
    _register_sentinel(monkeypatch)


def test_sentinel_rates_are_gone_after_a_passing_test():
    _assert_restored()


@pytest.mark.xfail(strict=True, reason="#641: teardown must restore after a failure")
def test_registers_sentinel_rates_then_fails(monkeypatch):
    _register_sentinel(monkeypatch)
    pytest.fail("fails after registering")


def test_sentinel_rates_are_gone_after_a_failing_test():
    _assert_restored()


def test_registers_a_model_litellm_does_not_know(monkeypatch):
    assert MADE_UP not in litellm.model_cost
    assert MADE_UP not in litellm.open_ai_chat_completion_models
    monkeypatch.setitem(cost_meter.MODEL_RATES, MADE_UP, SENTINEL)
    assert cost_meter.register_rates(MADE_UP) is True
    assert MADE_UP in litellm.model_cost
    assert MADE_UP in litellm.open_ai_chat_completion_models


def test_unknown_model_leaves_no_key_and_no_provider_name():
    assert MADE_UP not in litellm.model_cost
    assert MADE_UP not in litellm.open_ai_chat_completion_models
    assert MADE_UP not in litellm.utils._runtime_registered_model_cost
    assert MADE_UP not in cost_meter._registered
