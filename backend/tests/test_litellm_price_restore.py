"""#641: a test that registers rates leaves litellm's price state as it found it.

The tests run in pairs, in file order by design: the first registers through
the production path (cost_meter.register_rates), the second checks that the
conftest fixture put everything back before it started. Each pair registers
its own rates, so a pair cannot pass on what an earlier pair leaked.
"""

import inspect
import re
from decimal import Decimal

import litellm
import litellm.utils
import pytest
from litellm import ModelResponse, Usage

from config import settings
from services import cost_meter, llm
from tests.conftest import _LITELLM_MODEL_SETS

FLASH = "gemini/gemini-3.8-flash"
MADE_UP = "openai/crux-made-up-641"
# Rates no price map ships, so seeing them proves the registration landed.
PASSING_SENTINEL = {"input_per_1k": Decimal("0.004000"), "output_per_1k": Decimal("0.020000")}
FAILING_SENTINEL = {"input_per_1k": Decimal("0.005000"), "output_per_1k": Decimal("0.030000")}

# pair -> what its registering test saw before it registered.
_before: dict[str, dict] = {}


def _resp() -> ModelResponse:
    return ModelResponse(
        model=FLASH.split("/", 1)[-1],
        usage=Usage(prompt_tokens=1000, completion_tokens=200, total_tokens=1200),
        choices=[{"message": {"role": "assistant", "content": "hi"}}],
    )


def _runtime_registrations() -> dict:
    return {k: dict(v) for k, v in litellm.utils._runtime_registered_model_cost.items()}


def _register_sentinel(monkeypatch, pair: str, rates: dict[str, Decimal]) -> None:
    input_cost = float(rates["input_per_1k"] / 1000)
    assert litellm.model_cost[FLASH]["input_cost_per_token"] != pytest.approx(input_cost)
    monkeypatch.setattr(settings, "model", FLASH)
    monkeypatch.setitem(cost_meter.MODEL_RATES, FLASH, rates)
    monkeypatch.setitem(cost_meter.SCHEDULED_RATES, FLASH, [])
    _before[pair] = {
        "model_cost": dict(litellm.model_cost[FLASH]),
        "runtime": _runtime_registrations(),
        "registered": dict(cost_meter._registered),
    }
    llm.LiteLlmProvider()._completion_cost(_resp(), [], "hi")
    assert litellm.model_cost[FLASH]["input_cost_per_token"] == pytest.approx(input_cost)


def _assert_restored(pair: str) -> None:
    if pair not in _before:
        pytest.skip("runs after its registering test; select the pair together")
    before = _before[pair]
    assert litellm.model_cost[FLASH] == before["model_cost"]
    assert _runtime_registrations() == before["runtime"]
    assert cost_meter._registered == before["registered"]
    # The symptom itself: litellm prices the model at its own map's rates
    # again (priced directly, so nothing re-registers).
    cost = litellm.completion_cost(completion_response=_resp(), model=FLASH)
    expected = (
        1000 * before["model_cost"]["input_cost_per_token"]
        + 200 * before["model_cost"]["output_cost_per_token"]
    )
    assert cost == pytest.approx(expected)


def test_restored_model_sets_are_the_ones_register_model_adds_to():
    """A litellm upgrade that adds a provider branch fails here, not as a leak."""
    source = inspect.getsource(litellm.utils.register_model)
    assert set(re.findall(r"litellm\.(\w+)\.add\(", source)) == set(_LITELLM_MODEL_SETS)


def test_registers_sentinel_rates(monkeypatch):
    _register_sentinel(monkeypatch, "passing", PASSING_SENTINEL)


def test_sentinel_rates_are_gone_after_a_passing_test():
    _assert_restored("passing")


@pytest.mark.xfail(
    strict=True,
    raises=pytest.fail.Exception,
    reason="#641: teardown must restore after a failure",
)
def test_registers_sentinel_rates_then_fails(monkeypatch):
    _register_sentinel(monkeypatch, "failing", FAILING_SENTINEL)
    pytest.fail("fails after registering")


def test_sentinel_rates_are_gone_after_a_failing_test():
    _assert_restored("failing")


def test_registers_a_model_litellm_does_not_know(monkeypatch):
    assert MADE_UP not in litellm.model_cost
    assert MADE_UP not in litellm.open_ai_chat_completion_models
    monkeypatch.setitem(cost_meter.MODEL_RATES, MADE_UP, PASSING_SENTINEL)
    assert cost_meter.register_rates(MADE_UP) is True
    assert MADE_UP in litellm.model_cost
    assert MADE_UP in litellm.open_ai_chat_completion_models
    # Primes litellm's case-insensitive lookup with the new key.
    assert litellm.get_model_info(MADE_UP.upper())["input_cost_per_token"] == pytest.approx(4e-06)
    _before["unknown"] = {}


def test_unknown_model_leaves_no_key_and_no_provider_name():
    if "unknown" not in _before:
        pytest.skip("runs after its registering test; select the pair together")
    assert MADE_UP not in litellm.model_cost
    assert MADE_UP not in litellm.open_ai_chat_completion_models
    assert MADE_UP not in litellm.utils._runtime_registered_model_cost
    assert MADE_UP not in cost_meter._registered
    # A stale case-insensitive lookup would still serve the removed entry.
    with pytest.raises(litellm.ModelNotMappedError):
        litellm.get_model_info(MADE_UP.upper())
