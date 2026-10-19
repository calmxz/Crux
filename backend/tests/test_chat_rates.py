"""MODEL_RATES is the chat price source; litellm's price map is not.

A rated model's turn costs its usage x the rates in effect today, so a stale
litellm map (or a backend that outlives a price change) cannot under-meter the
spend caps (#622). litellm prices only models without rates, and nothing
writes into its price map (#643).
"""

from decimal import Decimal
from types import SimpleNamespace

import litellm
import pytest
from litellm import ModelResponse, Usage
from litellm.types.utils import PromptTokensDetailsWrapper

from config import settings
from services import cost_meter, llm

FLASH = "gemini/gemini-3.8-flash"
# In litellm's bundled price map, not in MODEL_RATES.
UNRATED = "gemini/gemini-2.5-flash"
MESSAGES = [{"role": "user", "content": "hi"}]


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


@pytest.fixture
def litellm_prices(monkeypatch):
    """Fail the test on any litellm.completion_cost or litellm.register_model
    call. Recorded and checked at teardown, not just raised: pricing catches
    every exception, so a raise alone would fall through to another price."""
    calls: dict[str, list] = {"completion_cost": [], "register_model": []}

    def completion_cost(**kwargs):
        calls["completion_cost"].append(kwargs)
        raise AssertionError("litellm.completion_cost must not price this call")

    def register_model(*args, **kwargs):
        calls["register_model"].append(args)
        raise AssertionError("nothing writes into litellm's price map")

    monkeypatch.setattr(litellm, "completion_cost", completion_cost)
    monkeypatch.setattr(litellm, "register_model", register_model)
    yield calls
    assert calls == {"completion_cost": [], "register_model": []}


@pytest.fixture
def sentinel_rates(monkeypatch):
    monkeypatch.setitem(cost_meter.MODEL_RATES, settings.model, SENTINEL)
    monkeypatch.setitem(cost_meter.SCHEDULED_RATES, settings.model, [])


def test_rated_model_costs_usage_x_model_rates(sentinel_rates, litellm_prices):
    assert _priced(_resp(1000, 200)) == _usage_x_rates(SENTINEL, 1000, 200)


def test_cached_prompt_tokens_price_at_the_cache_rate(sentinel_rates, litellm_prices):
    assert _priced(_resp(1000, 200, cached=400)) == _usage_x_rates(SENTINEL, 1000, 200, cached=400)


async def test_complete_prices_a_rated_turn_from_model_rates(
    sentinel_rates, litellm_prices, monkeypatch
):
    async def acompletion(**kwargs):
        return _resp(1000, 200, cached=400)

    monkeypatch.setattr(litellm, "acompletion", acompletion)

    completion = await llm.LiteLlmProvider().complete(MESSAGES, timeout=5)

    assert completion.cost.quantize(Decimal("0.000001")) == _usage_x_rates(
        SENTINEL, 1000, 200, cached=400
    )


async def test_stream_prices_a_rated_turn_from_model_rates(
    sentinel_rates, litellm_prices, monkeypatch
):
    async def acompletion(**kwargs):
        async def gen():
            delta = SimpleNamespace(content="hi", tool_calls=None)
            yield SimpleNamespace(choices=[SimpleNamespace(delta=delta)])

        return gen()

    monkeypatch.setattr(litellm, "acompletion", acompletion)
    monkeypatch.setattr(
        litellm, "stream_chunk_builder", lambda chunks, **kw: _resp(1000, 200, cached=400)
    )
    ps = await llm.LiteLlmProvider().stream(MESSAGES, tools=None, tool_choice=None, timeout=5)
    _ = [t async for t in ps]

    cost, _usage = ps.priced()

    assert cost.quantize(Decimal("0.000001")) == _usage_x_rates(SENTINEL, 1000, 200, cached=400)


def test_rated_response_without_usage_bills_token_math(
    sentinel_rates, litellm_prices, expect_app_log
):
    """A pricing gap bills the prompt, its tools and the reply at our rates,
    not 0 and not litellm's price."""
    expect_app_log("pricing by token math")
    provider = llm.LiteLlmProvider()
    tools = [{"type": "function", "function": {"name": "ask", "parameters": {}}}]

    cost = provider._completion_cost(SimpleNamespace(usage=None), MESSAGES, "reply", tools)

    assert cost > Decimal("0")
    assert cost == provider._token_math(MESSAGES, "reply", tools)


def test_unrated_model_takes_litellms_price(monkeypatch):
    monkeypatch.setattr(settings, "model", UNRATED)
    priced, registered = [], []

    def completion_cost(**kwargs):
        priced.append(kwargs)
        return 0.0042

    monkeypatch.setattr(litellm, "completion_cost", completion_cost)
    monkeypatch.setattr(litellm, "register_model", lambda *a, **k: registered.append(a))
    resp = _resp(1000, 200)

    assert llm.LiteLlmProvider()._completion_cost(resp, MESSAGES, "hi") == Decimal("0.0042")
    # model= supplies the provider prefix the bare response name lacks.
    assert priced == [{"completion_response": resp, "model": UNRATED}]
    assert registered == []


def test_unrated_model_falls_back_to_token_math(monkeypatch, expect_app_log):
    expect_app_log("completion_cost failed: unknown model")
    monkeypatch.setattr(settings, "model", UNRATED)
    registered = []

    def no_price(**kwargs):
        raise ValueError("unknown model")

    monkeypatch.setattr(litellm, "completion_cost", no_price)
    monkeypatch.setattr(litellm, "register_model", lambda *a, **k: registered.append(a))
    provider = llm.LiteLlmProvider()

    cost = provider._completion_cost(_resp(1000, 200), MESSAGES, "hi")

    assert cost > Decimal("0")
    assert cost == provider._token_math(MESSAGES, "hi")
    assert registered == []


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


def test_a_running_process_picks_up_the_new_rates(monkeypatch, on_date, litellm_prices):
    """A backend alive across 2027-01-01 meters the next turn at the new price."""
    monkeypatch.setattr(settings, "model", FLASH)
    on_date("2026-12-31")
    assert _priced(_resp(1000, 200)) == Decimal("0.001500")
    on_date("2027-01-01")
    assert _priced(_resp(1000, 200)) == Decimal("0.003000")
    # (600 x 0.0015 + 400 x 0.00015 + 200 x 0.0075) / 1000
    assert _priced(_resp(1000, 200, cached=400)) == Decimal("0.002460")


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


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        # (200 x 0.0003 + 800 x 0.00003 + 300 x 0.0025) / 1000
        ("gemini/gemini-3.5-flash-lite", Decimal("0.000834")),
        # (200 x 0.00025 + 800 x 0.000025 + 300 x 0.0015) / 1000
        ("gemini/gemini-3.1-flash-lite", Decimal("0.00052")),
    ],
)
def test_fallback_flash_lite_bills_cached_tokens_at_the_cache_rate(model, expected):
    """#644: implicit caching makes cached_tokens non-zero on most turns, so a
    missing cache rate over-bills them at the input rate."""
    usage = {"prompt_tokens": 1000, "cached_tokens": 800, "completion_tokens": 300}
    assert cost_meter.usage_cost(model, usage) == expected


def test_sonnet_fallback_lists_its_cache_rate():
    """Inert today (no request sets cache_control), recorded for when one does."""
    rates = cost_meter.MODEL_RATES["anthropic/claude-sonnet-5"]
    assert rates["cache_read_per_1k"] == Decimal("0.000200")


def test_usage_bills_thinking_and_tool_call_tokens(monkeypatch, litellm_prices):
    """completion_tokens carries thinking and tool-call tokens; token math over
    the reply text would drop them."""
    monkeypatch.setattr(settings, "model", FLASH)
    monkeypatch.setitem(cost_meter.SCHEDULED_RATES, FLASH, [])

    # (1000 x 0.00075 + 2300 x 0.00375) / 1000
    assert _priced(_resp(1000, 2300)) == Decimal("0.009375")


def test_schedule_order_in_the_list_does_not_matter(monkeypatch, on_date):
    early, late = {**SENTINEL}, {**SENTINEL, "input_per_1k": Decimal("1")}
    monkeypatch.setitem(
        cost_meter.SCHEDULED_RATES, FLASH, [("2027-06-01", late), ("2027-01-01", early)]
    )
    on_date("2027-07-01")
    assert cost_meter.rates_for(FLASH) == late
