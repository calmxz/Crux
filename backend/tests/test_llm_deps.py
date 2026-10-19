"""Dependency contract for the LiteLLM tool-calling path.

litellm.completion() imports its MCP handler whenever `tools` is passed, and that
chain pulls litellm.proxy.* -> orjson. orjson ships with litellm's [proxy] extra,
not with the base package, so a base install raises
ModuleNotFoundError: No module named 'orjson' on every tutor turn while the whole
stubbed test suite stays green. Since 1.106 the handler also imports `mcp`, which
litellm declares only under its [mcp] extra. Pin every half here.
"""

import importlib
import re
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"
_REQ = re.compile(r"\s*([A-Za-z0-9._-]+)\s*(?:\[([^\]]*)\])?")


def test_litellm_tools_path_importable():
    # Exactly what litellm/main.py imports under `if not skip_mcp_handler and tools:`
    importlib.import_module("litellm.responses.mcp.chat_completions_handler")


def _declared() -> dict[str, set[str]]:
    # name -> extras, for every [project] dependency, whatever its version operator
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    for d in data["project"]["dependencies"]:
        m = _REQ.match(d)
        assert m, f"unparseable dependency: {d!r}"
        out[m.group(1).lower()] = {e.strip() for e in (m.group(2) or "").split(",") if e.strip()}
    return out


def test_orjson_declared_as_dependency():
    assert "orjson" in _declared(), (
        "orjson must stay an explicit dependency: litellm's tool-calling path "
        "imports it transitively but does not declare it outside the [proxy] extra"
    )


def test_litellm_declared_with_mcp_extra():
    assert "mcp" in _declared().get("litellm", set()), (
        "litellm must be declared as litellm[mcp]: litellm >= 1.106 imports mcp on "
        "the tool-calling path but declares it only under the [mcp] extra"
    )
