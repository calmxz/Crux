"""TDD: x-sse-events block in docs/api/openapi.yaml (Task 14 Part B).

Validates that the OpenAPI spec contains the vendor-extension SSE contract
reference block and that every event has a data schema dict.
"""

from pathlib import Path

import yaml

SPEC_PATH = Path(__file__).parent.parent.parent / "docs" / "api" / "openapi.yaml"


def test_openapi_has_x_sse_events():
    doc = yaml.safe_load(SPEC_PATH.read_text())
    assert "x-sse-events" in doc
    expected = {
        "tool_call_start",
        "tool_call_done",
        "assistant_delta",
        "citations",
        "cost_warning",
        "done",
        "cancelled",
        "error",
        "check_question",
        "topic_suggestions",
        "followup_skipped",
    }
    assert set(doc["x-sse-events"].keys()) == expected


def test_each_event_has_data_schema():
    doc = yaml.safe_load(SPEC_PATH.read_text())
    for name, ev in doc["x-sse-events"].items():
        assert "data" in ev, f"{name} missing data schema"
        assert isinstance(ev["data"], dict)
