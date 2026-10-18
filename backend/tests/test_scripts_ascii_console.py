"""#607: backend scripts print ASCII only.

The Windows console is cp1252, so a non-ASCII character reaching it raises
UnicodeEncodeError and kills the script, worst when it runs unattended.
Checked with `ast`, not a line regex: a print often spans several lines.
"""

import ast
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

# A call to any of these puts every string inside it on the console. Matched
# against the callee's last name, so `parser.error` and `sys.exit` count.
# The argparse constructors are here because their strings (help, choices,
# metavar, description) all print through `--help` or a usage error.
# Only literals written inside the call are seen: a string bound to a name
# first (`msg = "..."; print(msg)`) is not followed.
_CONSOLE_CALLS = {
    "print",
    "input",
    "error",
    "exit",
    "SystemExit",
    "ArgumentTypeError",
    "ArgumentParser",
    "add_argument",
    "add_argument_group",
    "add_mutually_exclusive_group",
    "add_parser",
    "add_subparsers",
}
# `.write` is console output only on these streams; a file handle's `.write`
# is not.
_CONSOLE_WRITES = ("stdout.write", "stderr.write")


def _dotted(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    return ""


def _is_console_call(call: ast.Call) -> bool:
    name = _dotted(call.func)
    return name.rsplit(".", 1)[-1] in _CONSOLE_CALLS or name.endswith(_CONSOLE_WRITES)


def _non_ascii(text: str) -> bool:
    return any(ord(ch) > 127 for ch in text)


def console_non_ascii(source: str) -> list[tuple[int, str]]:
    """(line, string) for each non-ASCII string the script can print."""
    tree = ast.parse(source)
    found = []
    for call in ast.walk(tree):
        if not (isinstance(call, ast.Call) and _is_console_call(call)):
            continue
        for node in ast.walk(call):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _non_ascii(node.value):
                    found.append((node.lineno, node.value))
            elif isinstance(node, ast.Name) and node.id == "__doc__":
                doc = ast.get_docstring(tree, clean=False) or ""
                if _non_ascii(doc):
                    found.append((tree.body[0].lineno, doc))
    return sorted(set(found))


@pytest.mark.parametrize(
    "source",
    [
        pytest.param('print("a \u2014 b")\n', id="print"),
        pytest.param(
            'print(\n    "first line "\n    "spec \u00a76.3"\n)\n',
            id="multi-line-print-continuation",
        ),
        pytest.param('n = 1\nprint(f"{n} \u2014 done")\n', id="f-string-part"),
        pytest.param('import sys\nprint("a \u2014 b", file=sys.stderr)\n', id="print-file-stderr"),
        pytest.param('import sys\nsys.stderr.write("\u2014\\n")\n', id="stderr-write"),
        pytest.param('import sys\nsys.stdout.write("\u2014\\n")\n', id="stdout-write"),
        pytest.param('answer = input("go \u2014 ")\n', id="input-prompt"),
        pytest.param(
            '"""Tool (spec \u00a76.3)."""\nimport argparse\n'
            "parser = argparse.ArgumentParser(description=__doc__)\n",
            id="description-docstring",
        ),
        pytest.param(
            'import argparse\np = argparse.ArgumentParser()\np.add_argument("--x", help="a \u2014 b")\n',
            id="argparse-help",
        ),
        pytest.param(
            'import argparse\np = argparse.ArgumentParser()\np.error("bad \u2014 input")\n',
            id="parser-error",
        ),
        pytest.param(
            'import argparse\nraise argparse.ArgumentTypeError("\u2014")\n',
            id="argument-type-error",
        ),
        pytest.param('raise SystemExit("\u2014")\n', id="system-exit"),
        pytest.param('import sys\nsys.exit("\u2014")\n', id="sys-exit"),
        pytest.param(
            'import argparse\nargparse.ArgumentParser(epilog="\u2014")\n', id="argparse-epilog"
        ),
        pytest.param(
            'import argparse\np = argparse.ArgumentParser()\np.add_subparsers(title="\u2014")\n',
            id="add-subparsers",
        ),
        pytest.param(
            "import argparse\nsub = argparse.ArgumentParser().add_subparsers()\n"
            'sub.add_parser("up", help="\u2014")\n',
            id="add-parser",
        ),
        pytest.param(
            'import argparse\np = argparse.ArgumentParser()\np.add_argument_group("\u2014")\n',
            id="add-argument-group",
        ),
        pytest.param(
            "import argparse\np = argparse.ArgumentParser()\n"
            'p.add_mutually_exclusive_group(title="\u2014")\n',
            id="add-mutually-exclusive-group",
        ),
    ],
)
def test_console_non_ascii_is_flagged(source):
    assert console_non_ascii(source)


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            'with open("out.md", "w", encoding="utf-8") as f:\n    f.write("a \u2014 b")\n',
            id="file-write",
        ),
        pytest.param('# spec \u00a76.3 \u2014 note\nprint("ok")\n', id="comment"),
        pytest.param('LABEL = "a \u2014 b"\n', id="non-console-string"),
        pytest.param('"""Module (spec \u00a76.3)."""\nprint("ok")\n', id="docstring-not-printed"),
    ],
)
def test_non_console_non_ascii_is_allowed(source):
    assert console_non_ascii(source) == []


@pytest.mark.parametrize(
    "path", sorted(SCRIPTS.rglob("*.py")), ids=lambda p: p.relative_to(SCRIPTS).as_posix()
)
def test_script_console_output_is_ascii(path):
    assert console_non_ascii(path.read_text(encoding="utf-8")) == []
