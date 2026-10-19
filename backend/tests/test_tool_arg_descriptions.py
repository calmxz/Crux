"""Every tool-argument property description in openapi.yaml must reach the LLM (#617).

The tool parameter schemas in agent.tools.TOOLS are built from the generated
*Args models. If codegen emits property descriptions somewhere Pydantic does
not read (attribute docstrings), the guidance silently drops out of what the
model sees. This walks each tool's YAML schema and its parameters schema side
by side, at any depth, following $ref on both sides.

test_tool_schema_evidence.py pins the content of one schema-level sentence;
this pins delivery of every property description.
"""

from pathlib import Path

import pytest
import yaml

from agent.tools import TOOLS

SPEC_PATH = Path(__file__).parent.parent.parent / "docs" / "api" / "openapi.yaml"
_SCHEMAS = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))["components"]["schemas"]


def _args_schema_name(tool_name: str) -> str:
    return "".join(part.capitalize() for part in tool_name.split("_")) + "Args"


def _flat(text: str) -> str:
    # YAML folding changes line breaks, not wording.
    return " ".join(text.split())


def _resolve_yaml(node: dict) -> dict:
    while "$ref" in node:
        node = _SCHEMAS[node["$ref"].rsplit("/", 1)[-1]]
    return node


def _resolve_json(node: dict, root: dict) -> dict:
    while "$ref" in node:
        node = root["$defs"][node["$ref"].rsplit("/", 1)[-1]]
    return node


def _walk(spec: dict, gen: dict, root: dict, path: str, failures: list[str]) -> int:
    """Compare property descriptions under spec/gen; return the number of properties seen."""
    spec = _resolve_yaml(spec)
    gen = _resolve_json(gen, root)
    seen = 0
    for name, spec_prop in spec.get("properties", {}).items():
        prop_path = f"{path}.{name}"
        gen_prop = gen.get("properties", {}).get(name)
        if gen_prop is None:
            failures.append(f"{prop_path}: missing from parameters")
            continue
        seen += 1
        want = spec_prop.get("description")
        got = gen_prop.get("description")
        if want is not None and (got is None or _flat(got) != _flat(want)):
            failures.append(f"{prop_path}: want {_flat(want)!r}, got {got!r}")
        seen += _walk(spec_prop, gen_prop, root, prop_path, failures)
    if "items" in spec and "items" in gen:
        seen += _walk(spec["items"], gen["items"], root, f"{path}[]", failures)
    for key in ("oneOf", "anyOf"):
        spec_branches = spec.get(key, [])
        gen_branches = gen.get("anyOf", gen.get("oneOf", []))
        if spec_branches and len(spec_branches) == len(gen_branches):
            for i, (s, g) in enumerate(zip(spec_branches, gen_branches, strict=True)):
                seen += _walk(s, g, root, f"{path}<{i}>", failures)
    return seen


@pytest.mark.parametrize("tool", TOOLS, ids=lambda t: t["function"]["name"])
def test_every_yaml_property_description_reaches_tool_parameters(tool):
    fn = tool["function"]
    schema_name = _args_schema_name(fn["name"])
    assert schema_name in _SCHEMAS, f"{fn['name']}: no {schema_name} in openapi.yaml"
    params = fn["parameters"]
    failures: list[str] = []
    seen = _walk(_SCHEMAS[schema_name], params, params, fn["name"], failures)
    assert seen, f"{fn['name']}: walked no properties"
    assert not failures, "\n".join(failures)
