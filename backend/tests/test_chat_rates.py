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
    usd = (
        Decimal(prompt - cached) * rates["input_per_1k"]
        + Decimal(completion) * rates["output_per_1k"]
    )
    if cached:
        usd += Decimal(cached) * rates["cache_read_per_1k"]
    return (usd / Decimal(1000)).quantize(Decimal("0.000001"))


def _priced(resp) -> Decimal:
    cost = llm.LiteLlmProvider()._completion_cost(resp, [], "hi")
    return cost.quantize(Decimal("0.000001"))


# Rates no price map ships, so a match proves they came from MODEL_RATES.
SENTINEL = {
    "input_per_1k": Decimal("0.004000"),
    "output_per_1k": Decimal("0.020000"),
    "cache_read_per_1k": Decimal("0.000400"),
}


@pytest.fixture
def on_date(monkeypatch):
    def set_today(day: str) -> None:
        monkeypatch.setattr(cost_meter, "_today_utc", lambda: day)

    return set_today


def test_completion_cost_equals_usage_x_model_rates(monkeypatch):
    monkeypatch.setitem(cost_meter.MODEL_RATES, settings.model, SENTINEL)
    monkeypatch.setitem(cost_meter.SCHEDULED_RATES, settings.model, [])
    assert _priced(_resp(1000, 200)) == _usage_x_rates(SENTINEL, 1000, 200)


def test_cached_prompt_tokens_price_at_the_cache_rate(monkeypatch):
    monkeypatch.setitem(cost_meter.MODEL_RATES, settings.model, SENTINEL)
    monkeypatch.setitem(cost_meter.SCHEDULED_RATES, settings.model, [])
    assert _priced(_resp(1000, 200, cached=400)) == _usage_x_rates(SENTINEL, 1000, 200, cached=400)


def test_configured_model_has_a_cache_rate():
    rates = cost_meter.rates_for(settings.model)
    assert rates is not None and "cache_read_per_1k" in rates


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


def test_cancelled_flash_stream_prices_at_the_rates_in_effect(monkeypatch, on_date):
    """#602: the cancelled-stream estimate for 3.8 Flash is pinned, not derived."""
    monkeypatch.setattr(litellm, "token_counter", lambda model, text: 10)
    on_date("2026-12-31")
    # (1000 x 0.00075 + 10 x 0.00375) / 1000
    assert cost_meter.estimate_cancelled_cost(FLASH, "partial", 1000) == Decimal("0.0007875")
    on_date("2027-01-01")
    assert cost_meter.estimate_cancelled_cost(FLASH, "partial", 1000) == Decimal("0.001575")


def test_unscheduled_model_keeps_its_model_rates():
    assert (
        cost_meter.rates_for("gemini/gemini-3.5-flash-lite")
        == (cost_meter.MODEL_RATES["gemini/gemini-3.5-flash-lite"])
    )
    assert cost_meter.rates_for("some/unknown-model") is None


def test_registration_failure_never_raises(monkeypatch, expect_app_log):
    expect_app_log("could not register rates")
    calls = []

    def boom(*args, **kwargs):
        calls.append(args)
        raise ValueError("bad map")

    monkeypatch.setattr(litellm, "register_model", boom)

    assert cost_meter.register_rates(FLASH) is False
    assert len(calls) == 1
    assert FLASH not in cost_meter._registered  # retried on the next call


def test_failed_registration_prices_usage_at_our_rates(monkeypatch, on_date, expect_app_log):
    """A map litellm never updated must not meter 2027 turns at the old price."""
    expect_app_log("could not register rates")
    monkeypatch.setattr(settings, "model", FLASH)
    monkeypatch.setattr(
        litellm, "register_model", lambda *a, **k: (_ for _ in ()).throw(ValueError("bad map"))
    )
    on_date("2027-01-01")

    # (600 x 0.0015 + 400 x 0.00015 + 200 x 0.0075) / 1000
    assert _priced(_resp(1000, 200, cached=400)) == Decimal("0.002460")


def test_pricing_gap_bills_usage_not_the_visible_text(monkeypatch, expect_app_log):
    """completion_tokens carries thinking and tool-call tokens; token math over
    the reply text would drop them."""
    expect_app_log("completion_cost failed")
    monkeypatch.setattr(settings, "model", FLASH)
    monkeypatch.setitem(cost_meter.SCHEDULED_RATES, FLASH, [])

    def no_price(**kwargs):
        raise ValueError("unknown model")

    monkeypatch.setattr(litellm, "completion_cost", no_price)

    # (1000 x 0.00075 + 2300 x 0.00375) / 1000
    assert _priced(_resp(1000, 2300)) == Decimal("0.009375")


def test_schedule_order_in_the_list_does_not_matter(monkeypatch, on_date):
    early, late = {**SENTINEL}, {**SENTINEL, "input_per_1k": Decimal("1")}
    monkeypatch.setitem(
        cost_meter.SCHEDULED_RATES, FLASH, [("2027-06-01", late), ("2027-01-01", early)]
    )
    on_date("2027-07-01")
    assert cost_meter.rates_for(FLASH) == late
