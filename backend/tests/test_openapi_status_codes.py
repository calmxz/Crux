"""C-13: every status code a route can raise must be documented for that path.

Walks `backend/routes/*.py` with `ast` -- no imports, no app startup -- and
compares the integer status codes each handler can raise against the codes
documented under `paths[<prefix + path>][<method>].responses` in
`docs/api/openapi.yaml`.

Scope of the walker (deliberately narrow, so a failure means a real gap):
- codes come from `HTTPException(...)`, `JSONResponse(status_code=...)` and
  `Response(status_code=...)` calls, either as an int literal or a
  `status.HTTP_<n>_*` attribute;
- the handler body plus same-module functions it calls by name, one level
  deep, plus one more level when the callee is a `_`-prefixed helper
  (`chat.py` keeps its guards two helpers down);
- 2xx is ignored (success codes are the `status_code=` decorator argument);
- routes with `include_in_schema=False` are skipped (internal probes);
- dependency modules (`services/auth.py`, `services/velocity_limit.py`) are
  not walked at all: 401/429 are documented per path already.

`500` is never documented -- it means unhandled.
"""

import ast
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "docs" / "api" / "openapi.yaml"
ROUTES_DIR = REPO_ROOT / "backend" / "routes"

HTTP_METHODS = ("get", "post", "put", "patch", "delete")

# Calls whose status_code argument is a client- or server-visible response code.
RESPONSE_CALLS = {"HTTPException", "JSONResponse", "Response", "PlainTextResponse"}

# Explicit, reasoned exceptions. Empty is the goal; every entry needs a reason.
# Keyed by "<METHOD> <path>", value is {code: reason}.
KNOWN_GAPS: dict[str, dict[int, str]] = {}


def _status_from_node(node: ast.AST) -> int | None:
    """int literal, or `status.HTTP_404_NOT_FOUND` -> 404."""
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Attribute) and node.attr.startswith("HTTP_"):
        head = node.attr.removeprefix("HTTP_").split("_")[0]
        if head.isdigit():
            return int(head)
    return None


def _call_name(func: ast.AST) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _codes_in_body(fn: ast.AST) -> set[int]:
    codes: set[int] = set()
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node.func) not in RESPONSE_CALLS:
            continue
        arg = None
        for kw in node.keywords:
            if kw.arg == "status_code":
                arg = kw.value
        if arg is None and node.args:
            # HTTPException(422, detail=...) -- first positional is the code.
            arg = node.args[0]
        code = _status_from_node(arg) if arg is not None else None
        if code is not None:
            codes.add(code)
    return codes


def _called_names(fn: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
        # run_in_threadpool(_helper, ...) passes the helper as a value.
        if isinstance(node, ast.Call):
            for arg in list(node.args) + [kw.value for kw in node.keywords]:
                if isinstance(arg, ast.Name):
                    names.add(arg.id)
    return names


def _collect_codes(
    fn: ast.AST,
    module_funcs: dict[str, ast.AST],
    depth: int,
    seen: set[str],
) -> set[int]:
    codes = _codes_in_body(fn)
    for name in sorted(_called_names(fn)):
        if name in seen or name not in module_funcs:
            continue
        next_depth = depth + 1
        # one level for any same-module helper, one extra for `_` helpers.
        if next_depth > 2 or (next_depth == 2 and not name.startswith("_")):
            continue
        codes |= _collect_codes(
            module_funcs[name], module_funcs, next_depth, seen | {name}
        )
    return codes


def _router_prefix(tree: ast.Module) -> str:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "router" for t in node.targets):
            continue
        if isinstance(node.value, ast.Call) and _call_name(node.value.func) == "APIRouter":
            for kw in node.value.keywords:
                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                    return kw.value.value
    return ""


def _routes() -> dict[tuple[str, str], set[int]]:
    """{(METHOD, path): raisable non-2xx codes} across backend/routes/*.py."""
    found: dict[tuple[str, str], set[int]] = {}
    for module_path in sorted(ROUTES_DIR.glob("*.py")):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        prefix = _router_prefix(tree)
        module_funcs = {
            n.name: n
            for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for fn in module_funcs.values():
            for dec in fn.decorator_list:
                if not isinstance(dec, ast.Call):
                    continue
                method = _call_name(dec.func)
                if method not in HTTP_METHODS:
                    continue
                if not (dec.args and isinstance(dec.args[0], ast.Constant)):
                    continue
                hidden = any(
                    kw.arg == "include_in_schema"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is False
                    for kw in dec.keywords
                )
                if hidden:
                    continue
                key = (method.upper(), prefix + dec.args[0].value)
                codes = _collect_codes(fn, module_funcs, 0, {fn.name})
                found.setdefault(key, set())
                found[key] |= {c for c in codes if not 200 <= c < 300}
    return found


def _documented() -> dict[tuple[str, str], set[int]]:
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], set[int]] = {}
    for path, ops in (spec.get("paths") or {}).items():
        for method, op in ops.items():
            if method.lower() not in HTTP_METHODS:
                continue
            codes = set()
            for code in (op.get("responses") or {}):
                # a documented `default` is not a wildcard for this check.
                if str(code).isdigit():
                    codes.add(int(code))
            out[(method.upper(), path)] = codes
    return out


def test_every_raised_status_code_is_documented():
    documented = _documented()
    problems = []
    for key, raised in sorted(_routes().items()):
        method, path = key
        if key not in documented:
            problems.append(f"{method} {path} -> route has no entry in openapi.yaml")
            continue
        allowed = KNOWN_GAPS.get(f"{method} {path}", {})
        missing = {c for c in raised if c not in documented[key] and c not in allowed}
        if missing:
            problems.append(
                f"{method} {path} -> raised but undocumented {sorted(missing)} "
                f"(documented: {sorted(documented[key])})"
            )
    assert not problems, "Undocumented status codes:\n  " + "\n  ".join(problems)


def test_every_documented_path_has_a_route():
    routes = _routes()
    missing = sorted(
        f"{m} {p}" for (m, p) in _documented() if (m, p) not in routes
    )
    assert not missing, "Documented in openapi.yaml but no route raises it:\n  " + "\n  ".join(
        missing
    )


def test_no_path_documents_500():
    offenders = sorted(
        f"{m} {p}" for (m, p), codes in _documented().items() if 500 in codes
    )
    assert not offenders, "500 is unhandled and must never be documented:\n  " + "\n  ".join(
        offenders
    )
