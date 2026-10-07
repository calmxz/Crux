"""#464: one error-code list in the spec, one backend registry.

The `x-error-codes` block in docs/api/openapi.yaml is the list's home;
lib/error_codes.py must hold exactly those codes, and no backend source
outside the registry may spell a code as a string literal.
"""

import ast
import functools
import os
from pathlib import Path

import yaml

from lib import error_codes

BACKEND = Path(__file__).parent.parent
SPEC_PATH = BACKEND.parent / "docs" / "api" / "openapi.yaml"
REGISTRY_PATH = BACKEND / "lib" / "error_codes.py"
SKIP_DIRS = {"tests", ".venv", "contracts", "__pycache__"}


@functools.cache
def _spec_codes() -> dict:
    doc = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    return doc["x-error-codes"]


def _registry_values() -> set[str]:
    return {
        value
        for name, value in vars(error_codes).items()
        if not name.startswith("_") and isinstance(value, str)
    }


def test_registry_matches_spec_exactly():
    assert _registry_values() == set(_spec_codes())


def test_every_spec_entry_says_where_and_when():
    for code, entry in _spec_codes().items():
        assert isinstance(entry, dict), code
        assert entry.get("when"), code
        assert "status" in entry or "sse" in entry or "via" in entry, code


def _source_files() -> list[Path]:
    # Prune while walking: rglob would enumerate all of .venv first.
    files = []
    for root, dirs, names in os.walk(BACKEND):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        files.extend(Path(root) / n for n in names if n.endswith(".py"))
    return [f for f in files if f != REGISTRY_PATH]


def _is_str(node) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _violations(tree: ast.AST, registry_values: set[str]) -> list[tuple[int, str]]:
    hits = []
    for node in ast.walk(tree):
        # Position: a literal as the value of a "code" key or a code= keyword.
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if _is_str(key) and key.value == "code" and _is_str(value):
                    hits.append((value.lineno, value.value))
        elif isinstance(node, ast.keyword):
            if node.arg == "code" and _is_str(node.value):
                hits.append((node.value.lineno, node.value.value))
        # Value: a literal equal to a registered code, anywhere. If one ever
        # collides with an unrelated literal, add a commented allowlist here.
        if _is_str(node) and node.value in registry_values:
            hits.append((node.lineno, node.value))
    return sorted(set(hits))


def test_no_inline_error_code_literals():
    registry_values = _registry_values()
    files = _source_files()
    assert len(files) > 50, "scan found too few files; is the path filter broken?"

    found = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for lineno, value in _violations(tree, registry_values):
            found.append(f"{path.relative_to(BACKEND)}:{lineno} {value!r}")
    assert not found, "use a lib/error_codes.py constant:\n" + "\n".join(found)


def test_guard_catches_key_keyword_and_value():
    src = (
        'raise HTTPException(409, detail={"code": "set_closed"})\n'
        'Err(code="other")\n'
        'helper("session_ended")\n'
    )
    hits = _violations(ast.parse(src), {"session_ended"})
    assert [v for _, v in hits] == ["set_closed", "other", "session_ended"]
