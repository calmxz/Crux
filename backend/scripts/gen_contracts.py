"""Regenerate backend/contracts/ from docs/api/openapi.yaml.

Run from anywhere:
    python backend/scripts/gen_contracts.py

Or as a module from backend/:
    python -m scripts.gen_contracts
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_SPEC = REPO_ROOT / "docs" / "api" / "openapi.yaml"
OUTPUT_DIR = REPO_ROOT / "backend" / "contracts"
OUTPUT_FILE = OUTPUT_DIR / "models.py"
INIT_FILE = OUTPUT_DIR / "__init__.py"

INIT_TEMPLATE = '''"""Generated Pydantic contracts. Do not edit by hand.

Source: docs/api/openapi.yaml
Regenerate: python backend/scripts/gen_contracts.py
"""

from .models import *  # noqa: F401,F403
'''


def main() -> int:
    if not OPENAPI_SPEC.exists():
        print(f"error: spec not found at {OPENAPI_SPEC}", file=sys.stderr)
        return 1

    if importlib.util.find_spec("datamodel_code_generator") is None:
        print(
            "error: datamodel_code_generator not installed in this Python. "
            "Install dev deps (from backend/):\n"
            "  uv sync --locked --extra dev",
            file=sys.stderr,
        )
        return 1

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    cmd = [
        sys.executable,
        "-m",
        "datamodel_code_generator",
        "--input",
        str(OPENAPI_SPEC),
        "--input-file-type",
        "openapi",
        "--output",
        str(OUTPUT_FILE),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--use-double-quotes",
        "--use-standard-collections",
        "--use-union-operator",
        "--enum-field-as-literal",
        "all",
        "--target-python-version",
        "3.12",
        "--use-schema-description",
        # No --use-field-description: it turns property descriptions into attribute
        # docstrings, which Pydantic ignores, so they never reach the LLM tool schemas
        # (#617; enforced by tests/test_tool_arg_descriptions.py).
        "--collapse-root-models",
        "--disable-timestamp",
        # datamodel-code-generator >=0.30 defaults date-time fields to AwareDatetime,
        # which rejects the naive datetimes our services and sqlite tests produce.
        "--output-datetime-class",
        "datetime",
    ]
    print("running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    if result.returncode != 0:
        return result.returncode

    INIT_FILE.write_text(INIT_TEMPLATE, encoding="utf-8")

    print(f"ok: contracts written to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
