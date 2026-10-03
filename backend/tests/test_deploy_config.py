import json
import re
from pathlib import Path

import yaml

from config import Settings

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RENDER = REPO_ROOT / "render.yaml"
VERCEL = REPO_ROOT / "frontend" / "vercel.json"
COMPOSE_FILES = (REPO_ROOT / "docker-compose.yml", REPO_ROOT / "docker-compose.prod.yml")
BACKUP_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "backup.yml"
ENV_EXAMPLE = REPO_ROOT / ".env.example"

# G-12: names that may appear in .env.example without being a Settings field.
# Empty on purpose -- a template var the app never reads is dead config.
ENV_TEMPLATE_ONLY = set()

_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _env_example_names() -> set:
    """Every NAME mentioned as `NAME=` in .env.example, commented or not."""
    names = set()
    for raw in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lstrip("#").strip()
        if "=" not in line:
            continue
        name = line.split("=", 1)[0].strip()
        if _NAME_RE.match(name):
            names.add(name)
    return names


def _settings_env_names() -> set:
    return {f.upper() for f in Settings.model_fields}


def _load(path):
    p = Path(path)
    if not p.is_absolute():
        p = REPO_ROOT / p
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def test_render_yaml_parses():
    data = yaml.safe_load(RENDER.read_text(encoding="utf-8"))
    assert "services" in data


def test_render_service_shape():
    data = yaml.safe_load(RENDER.read_text(encoding="utf-8"))
    svc = data["services"][0]
    assert svc["type"] == "web"
    assert svc["runtime"] == "docker"
    # G-07: deliberately /ready, not /health -- the check must fail when the
    # database is unreachable so Render restarts the instance.
    assert svc["healthCheckPath"] == "/ready"
    assert svc["plan"] == "free"
    assert svc["dockerfilePath"] == "./backend/Dockerfile"


def test_render_secrets_not_inlined():
    data = yaml.safe_load(RENDER.read_text(encoding="utf-8"))
    env_vars = {e["key"]: e for e in data["services"][0]["envVars"]}
    for secret in (
        "GEMINI_API_KEY",
        "DATABASE_URL",
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
        "SUPABASE_SECRET_KEY",
        "CORS_ORIGINS",
    ):
        assert env_vars[secret].get("sync") is False
        assert "value" not in env_vars[secret]


def test_vercel_json_parses():
    json.loads(VERCEL.read_text(encoding="utf-8"))


def test_vercel_spa_rewrite():
    data = json.loads(VERCEL.read_text(encoding="utf-8"))
    dests = [r["destination"] for r in data["rewrites"]]
    assert "/index.html" in dests


def test_vercel_has_security_headers_but_not_csp():
    # P3 I-06: Content-Security-Policy is deliberately NOT a vercel.json header.
    # It is injected at build time as a <meta http-equiv="Content-Security-Policy">
    # tag by frontend/cspPlugin.js (behavior covered by
    # frontend/src/__tests__/cspPlugin.test.js), because the header value needs
    # to interpolate VITE_API_BASE_URL, which vercel.json cannot do. Do not
    # "restore" a Content-Security-Policy header here.
    data = json.loads(VERCEL.read_text(encoding="utf-8"))
    headers = data["headers"][0]["headers"]
    keys = {h["key"] for h in headers}
    assert "Content-Security-Policy" not in keys
    assert "X-Content-Type-Options" in keys
    assert "X-Frame-Options" in keys
    assert "Referrer-Policy" in keys


def test_compose_files_do_not_define_worker_service():
    """2026-08-12 worker-deferral spec: ingestion runs in-process in the
    web service (INGEST_IN_PROCESS, default on). Re-adding a worker
    service here means the scale-out path was taken deliberately --
    revisit the flag on the web service and the spec before deleting
    this test (spec removed from the tree; see git history for
    docs/superpowers/specs/2026-08-12-defer-render-worker-design.md)."""
    for path in ("docker-compose.yml", "docker-compose.prod.yml"):
        cfg = _load(path)
        assert "worker" not in cfg["services"]


def test_env_example_documents_every_setting():
    """G-12: a Settings field absent from .env.example is invisible to whoever
    configures a deploy -- they get the default and never know it existed."""
    missing = sorted(_settings_env_names() - _env_example_names())
    assert not missing, f".env.example is missing: {missing}"


def test_env_example_has_no_dead_vars():
    """The other direction: a template var no Settings field reads is config
    the app silently ignores."""
    extra = sorted(_env_example_names() - _settings_env_names() - ENV_TEMPLATE_ONLY)
    assert not extra, f".env.example documents unknown vars: {extra}"


def test_render_env_vars_are_known_settings():
    data = yaml.safe_load(RENDER.read_text(encoding="utf-8"))
    known = _settings_env_names()
    for svc in data["services"]:
        unknown = sorted({e["key"] for e in svc.get("envVars", [])} - known)
        assert not unknown, f"{svc['name']} sets unknown vars: {unknown}"


def test_backup_job_is_bounded():
    """G-10: a hung pg_dump or R2 upload otherwise burns the full 6h runner
    limit and the next night's run overlaps it."""
    data = yaml.safe_load(BACKUP_WORKFLOW.read_text(encoding="utf-8"))
    assert data["jobs"]["backup"]["timeout-minutes"] == 15


def test_backup_workflow_can_open_issues():
    data = yaml.safe_load(BACKUP_WORKFLOW.read_text(encoding="utf-8"))
    assert data["permissions"]["contents"] == "read"
    assert data["permissions"]["issues"] == "write"


def test_backup_workflow_alerts_on_failure():
    """A silently failing nightly backup is indistinguishable from a working
    one until a restore is needed."""
    data = yaml.safe_load(BACKUP_WORKFLOW.read_text(encoding="utf-8"))
    steps = data["jobs"]["backup"]["steps"]
    # A timeout-minutes kill marks the job cancelled, not failed, so the
    # alert condition must cover both or the hang case never alerts.
    failure_steps = [
        s for s in steps
        if "failure()" in str(s.get("if", "")) and "cancelled()" in str(s.get("if", ""))
    ]
    assert failure_steps, "no `if: failure() || cancelled()` alert step in the backup job"
    assert any("gh issue" in str(s.get("run", "")) for s in failure_steps)


def test_render_does_not_define_worker_service():
    """See test_compose_files_do_not_define_worker_service."""
    cfg = _load("render.yaml")
    names = {s["name"] for s in cfg["services"]}
    assert "crux-worker" not in names
    assert {s["type"] for s in cfg["services"]} == {"web"}
