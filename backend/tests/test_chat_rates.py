"""#622: MODEL_RATES is the chat price source; litellm's price map is not.

completion_cost for the configured model must equal usage x the rates in
effect today, so a stale litellm map (or a backend that outlives a price
change) cannot under-meter the spend caps.
"""

from decimal import Decimal

import litellm
import pytest
from litellm import ModelResponse, Usage
from litellm.types.utils import PromptTokensDetailsWrapper

from config import settings
from services import cost_meter, llm

FLASH = "gemini/gemini-3.8-flash"


def _resp(prompt: int, completion: int, cached: int | None = None) -> ModelResponse:
    # The bare model name is what Gemini responses carry; the provider prefix
    # has to come from the caller.
    details = PromptTokensDetailsWrapper(cached_tokens=cached) if cached else None
    return ModelResponse(
        model=settings.model.split("/", 1)[-1],
        usage=Usage(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=prompt + completion,
            prompt_tokens_details=details,
        ),
        choices=[{"message": {"role": "assistant", "content": "hi"}}],
    )


def _usage_x_rates(rates, prompt: int, completion: int, cached: int = 0) -> Decimal:
    cache_rate = rates.get("cache_read_per_1k", rates["input_per_1k"])
    usd = (
        Decimal(prompt - cached) * rates["input_per_1k"]
        + Decimal(cached) * cache_rate
        + Decimal(completion) * rates["output_per_1k"]
    ) / Decimal(1000)
    return usd.quantize(Decimal("0.000001"))


def _priced(resp) -> Decimal:
    cost = llm.LiteLlmProvider()._completion_cost(resp, [], "hi")
    return cost.quantize(Decimal("0.000001"))


@pytest.fixture
def on_date(monkeypatch):
    def set_today(day: str) -> None:
        monkeypatch.setattr(cost_meter, "_today_utc", lambda: day)

    yield set_today
    # Leave litellm's map at today's rates for later tests.
    monkeypatch.undo()
    cost_meter.register_rates(settings.model)


def test_completion_cost_equals_usage_x_model_rates():
    rates = cost_meter.rates_for(settings.model)
    assert rates is not None
    assert _priced(_resp(1000, 200)) == _usage_x_rates(rates, 1000, 200)


def test_cached_prompt_tokens_price_at_the_cache_rate():
    rates = cost_meter.rates_for(settings.model)
    assert rates is not None and "cache_read_per_1k" in rates
    assert _priced(_resp(1000, 200, cached=400)) == _usage_x_rates(rates, 1000, 200, cached=400)


def test_flash_rates_before_2027(on_date):
    on_date("2026-12-31")
    assert cost_meter.rates_for(FLASH) == {
        "input_per_1k": Decimal("0.000750"),
        "output_per_1k": Decimal("0.003750"),
        "cache_read_per_1k": Decimal("0.000075"),
    }


def test_flash_rates_double_on_2027_01_01(on_date):
    on_date("2027-01-01")
    assert cost_meter.rates_for(FLASH) == {
        "input_per_1k": Decimal("0.001500"),
        "output_per_1k": Decimal("0.007500"),
        "cache_read_per_1k": Decimal("0.000150"),
    }


def test_a_running_process_picks_up_the_new_rates(monkeypatch, on_date):
    """A backend alive across 2027-01-01 meters the next turn at the new price."""
    monkeypatch.setattr(settings, "model", FLASH)
    on_date("2026-12-31")
    assert _priced(_resp(1000, 200)) == Decimal("0.001500")
    on_date("2027-01-01")
    assert _priced(_resp(1000, 200)) == Decimal("0.003000")


def test_cancelled_flash_stream_prices_at_the_rates_in_effect(on_date):
    """#602: the cancelled-stream estimate for 3.8 Flash is pinned, not derived."""
    on_date("2026-12-31")
    assert cost_meter.estimate_cancelled_cost(FLASH, "", 1000) == Decimal("0.00075")
    on_date("2027-01-01")
    assert cost_meter.estimate_cancelled_cost(FLASH, "", 1000) == Decimal("0.0015")


def test_unscheduled_model_keeps_its_model_rates():
    assert cost_meter.rates_for("gemini/gemini-3.5-flash-lite") == (
        cost_meter.MODEL_RATES["gemini/gemini-3.5-flash-lite"]
    )
    assert cost_meter.rates_for("some/unknown-model") is None


def test_registration_failure_never_raises(monkeypatch, on_date, expect_app_log):
    expect_app_log("could not register rates")

    def boom(*args, **kwargs):
        raise ValueError("bad map")

    monkeypatch.setattr(litellm, "register_model", boom)
    on_date("2030-01-01")  # a period not registered yet, so registration runs
    cost_meter.register_rates(FLASH)
