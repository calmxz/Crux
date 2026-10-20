"""An xfail mark names the exception it expects.

Without raises=, any failure counts as the expected one: a broken setup step
or a precondition assert reads as xfailed, and the run stays green (#641).
"""

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def _xfails_without_raises(source: str) -> list[int]:
    """Lines of pytest.mark.xfail marks, bare or called, with no raises=."""
    nodes = list(ast.walk(ast.parse(source)))
    calls = {id(n.func): n for n in nodes if isinstance(n, ast.Call)}
    lines = []
    for node in nodes:
        if not _is_xfail_mark(node):
            continue
        call = calls.get(id(node))
        if call is None or not any(k.arg == "raises" for k in call.keywords):
            lines.append(node.lineno)
    return sorted(lines)


def _is_xfail_mark(node: ast.AST) -> bool:
    # pytest.mark.xfail
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "xfail"
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
    )


def test_the_scan_finds_bare_and_called_xfails_without_raises():
    source = (
        "import pytest\n"
        "@pytest.mark.xfail\n"
        "def a(): ...\n"
        "@pytest.mark.xfail(strict=True, reason='r')\n"
        "def b(): ...\n"
        "@pytest.mark.xfail(strict=True, raises=ValueError)\n"
        "def c(): ...\n"
        "P = pytest.param(1, marks=pytest.mark.xfail(reason='r'))\n"
        "pytest.xfail('imperative: the test raises it itself')\n"
    )
    assert _xfails_without_raises(source) == [2, 4, 8]


def test_every_xfail_in_the_suite_names_its_exception():
    hits = [
        f"{path.relative_to(BACKEND)}:{line}"
        for path in sorted((BACKEND / "tests").rglob("*.py"))
        for line in _xfails_without_raises(path.read_text(encoding="utf-8"))
    ]

    assert hits == [], "give each xfail mark raises=<the exception the test expects>"
