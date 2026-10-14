"""cost_meter.extract_usage: tolerant token-usage reader (roadmap P1 AC1).

Instrumentation only -- must return the three-key dict on ANY input and
never raise, because it runs inside the billed turn path.
"""

from types import SimpleNamespace

from services import cost_meter


def test_extract_usage_reads_openai_style_cached_tokens():
    resp = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=1500,
            completion_tokens=200,
            prompt_tokens_details=SimpleNamespace(cached_tokens=1100),
        )
    )
    assert cost_meter.extract_usage(resp) == {
        "prompt_tokens": 1500,
        "completion_tokens": 200,
        "cached_tokens": 1100,
    }


def test_extract_usage_reads_gemini_field_name():
    resp = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=1500,
            completion_tokens=200,
            prompt_tokens_details=SimpleNamespace(cached_content_token_count=800),
        )
    )
    assert cost_meter.extract_usage(resp)["cached_tokens"] == 800


def test_extract_usage_missing_pieces_yield_nones():
    assert cost_meter.extract_usage(None) == {
        "prompt_tokens": None,
        "completion_tokens": None,
        "cached_tokens": None,
    }
    assert cost_meter.extract_usage(SimpleNamespace()) == {
        "prompt_tokens": None,
        "completion_tokens": None,
        "cached_tokens": None,
    }
    no_details = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=2))
    out = cost_meter.extract_usage(no_details)
    assert out["prompt_tokens"] == 10
    assert out["cached_tokens"] is None
