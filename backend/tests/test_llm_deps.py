"""Dependency contract for the LiteLLM tool-calling path.

litellm.completion() imports its MCP handler whenever `tools` is passed, and that
chain pulls litellm.proxy.* -> orjson. orjson ships with litellm's [proxy] extra,
not with the base package, so a base install raises
ModuleNotFoundError: No module named 'orjson' on every tutor turn while the whole
stubbed test suite stays green. Since 1.106 the handler also imports `mcp`, which
litellm declares only under its [mcp] extra. Pin every half here.
"""

import importlib
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_litellm_tools_path_importable():
    # Exactly what litellm/main.py imports under `if not skip_mcp_handler and tools:`
    importlib.import_module("litellm.responses.mcp.chat_completions_handler")


def test_orjson_declared_as_dependency():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    deps = data["project"]["dependencies"]
    assert any(d.split(">=")[0].split("[")[0].strip() == "orjson" for d in deps), (
        "orjson must stay an explicit dependency: litellm's tool-calling path "
        "imports it transitively but does not declare it outside the [proxy] extra"
    )


def test_litellm_declared_with_mcp_extra():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    deps = data["project"]["dependencies"]
    litellm = [d for d in deps if d.split(">=")[0].split("[")[0].strip() == "litellm"]
    assert len(litellm) == 1
    name = litellm[0].split(">=")[0]
    extras = name.split("[")[1].split("]")[0] if "[" in name else ""
    assert "mcp" in [e.strip() for e in extras.split(",")], (
        "litellm must be declared as litellm[mcp]: litellm >= 1.106 imports mcp on "
        "the tool-calling path but declares it only under the [mcp] extra"
    )
