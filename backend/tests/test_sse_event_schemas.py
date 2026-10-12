"""TDD: x-sse-events block in docs/api/openapi.yaml (Task 14 Part B, #463).

Validates that the OpenAPI spec contains the vendor-extension SSE contract
block, that every event has a valid JSON Schema for its data, and that the
validator conftest.py applies to every StreamEvent accepts and rejects the
right payloads.
"""

import pytest
import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from tests.sse_contract import SPEC_PATH, SseContractError, sse_event_schemas, validate_event


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


def test_each_data_schema_is_valid_json_schema():
    for name, ev in sse_event_schemas().items():
        try:
            Draft202012Validator.check_schema(ev["data"])
        except SchemaError as e:
            pytest.fail(f"{name}: {e.message}")


def test_cancelled_allows_null_message_id():
    validate_event(
        "cancelled",
        {"message_id": None, "partial_content_chars": 0, "estimated_cost_usd": "0"},
    )


def test_done_rejects_total_cost_usd():
    with pytest.raises(SseContractError, match="total_cost_usd"):
        validate_event("done", {"message_id": "m", "total_cost_usd": "0.1"})


def test_check_question_allows_null_set_position():
    validate_event(
        "check_question",
        {"gap": "g", "total": 0, "items": [], "set_index": None, "set_total": None},
    )


def test_tool_call_done_rejects_unlisted_field():
    with pytest.raises(SseContractError, match="extra"):
        validate_event("tool_call_done", {"id": "x", "status": "ok", "summary": "s", "extra": 1})


def test_nested_items_reject_unlisted_field():
    with pytest.raises(SseContractError, match="score"):
        validate_event("citations", [{"doc_id": "d", "text": "t", "score": 0.5}])


def test_wrong_field_type_names_event_and_field():
    with pytest.raises(SseContractError, match=r"'done'[\s\S]*message_id"):
        validate_event("done", {"message_id": 1})


def test_unknown_event_type_fails():
    with pytest.raises(SseContractError, match="not in x-sse-events"):
        validate_event("nope", {})
