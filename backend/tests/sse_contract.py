"""Validator for SSE event payloads against the x-sse-events block (#463).

The block in docs/api/openapi.yaml is the one description of what the chat
stream carries. Codegen ignores it, so conftest.py validates every
StreamEvent built during the suite through validate_event.
"""

from functools import cache
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

SPEC_PATH = Path(__file__).parent.parent.parent / "docs" / "api" / "openapi.yaml"


class SseContractError(AssertionError):
    pass


@cache
def sse_event_schemas() -> dict[str, dict]:
    """The x-sse-events block: event type -> {data: <JSON Schema>}."""
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))["x-sse-events"]


@cache
def _validators() -> dict[str, Draft202012Validator]:
    out = {}
    for name, ev in sse_event_schemas().items():
        Draft202012Validator.check_schema(ev["data"])
        out[name] = Draft202012Validator(ev["data"])
    return out


def validate_event(event_type: str, data) -> None:
    """Raise SseContractError naming the event and field if data is off-spec."""
    validators = _validators()
    if event_type not in validators:
        raise SseContractError(f"SSE event type {event_type!r} is not in x-sse-events")
    errors = sorted(validators[event_type].iter_errors(data), key=lambda e: list(e.path))
    if errors:
        lines = [
            f"  at {'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
        ]
        raise SseContractError(
            f"SSE event {event_type!r} does not match x-sse-events:\n" + "\n".join(lines)
        )
