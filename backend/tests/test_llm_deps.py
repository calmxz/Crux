"""Dependency contract for the LiteLLM tool-calling path.

litellm.completion() imports its MCP handler whenever `tools` is passed, and that
chain pulls litellm.proxy.* -> orjson. orjson ships with litellm's [proxy] extra,
not with the base package, so a base install raises
ModuleNotFoundError: No module named 'orjson' on every tutor turn while the whole
stubbed test suite stays green. Since 1.106 the handler also imports `mcp`, which
litellm declares only under extras: [mcp], or [proxy] with the whole proxy server.
Pin every half here.
"""

import importlib
import re
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
_REQ = re.compile(r"\s*([A-Za-z0-9._-]+)\s*(?:\[([^\]]*)\])?")


def _canon(name: str) -> str:
    # PEP 503 / PEP 685 normalization, so equivalent spellings compare equal
    return re.sub(r"[-_.]+", "-", name).lower()


def test_litellm_tools_path_importable():
    # Exactly what litellm/main.py imports under `if not skip_mcp_handler and tools:`
    importlib.import_module("litellm.responses.mcp.chat_completions_handler")


def _declared() -> dict[str, list[set[str]]]:
    # name -> extras of each entry (marker-split entries each count), whatever
    # the version operator
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    out: dict[str, list[set[str]]] = {}
    for d in data["project"]["dependencies"]:
        m = _REQ.match(d)
        assert m, f"unparseable dependency: {d!r}"
        extras = {_canon(e.strip()) for e in (m.group(2) or "").split(",") if e.strip()}
        out.setdefault(_canon(m.group(1)), []).append(extras)
    return out


def test_orjson_declared_as_dependency():
    assert "orjson" in _declared(), (
        "orjson must stay an explicit dependency: litellm's tool-calling path "
        "imports it transitively but does not declare it outside the [proxy] extra"
    )


def test_litellm_declared_with_mcp_extra():
    entries = _declared().get("litellm", [])
    assert entries and all("mcp" in extras for extras in entries), (
        "litellm must be declared as litellm[mcp]: litellm >= 1.106 imports mcp on "
        "the tool-calling path but declares it only under extras ([mcp], or the "
        "whole proxy server via [proxy])"
    )
