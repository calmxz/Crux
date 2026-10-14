#!/usr/bin/env bash
# Run the Playwright e2e suite locally against the real e2e backend, the way
# .github/workflows/e2e.yml does: throwaway pgvector Postgres, migrated; a
# throwaway JWKS for e2e/support/auth.js; the backend with LLM_STUB=1. Every
# service it starts is stopped on exit, pass or fail.
#
# Usage, from anywhere:
#   frontend/e2e/run-local.sh                                   # whole suite
#   frontend/e2e/run-local.sh e2e/resume-carries-profile.spec.js
# Extra arguments go to `playwright test` unchanged (paths are relative to
# frontend/). E2E_PG_PORT overrides the Postgres host port (default 55432).
# Service logs land in frontend/test-results/e2e-local/ (gitignored).
set -euo pipefail

FRONTEND="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$FRONTEND/../backend"

if [ -x "$BACKEND/.venv/Scripts/python.exe" ]; then
  PY="$BACKEND/.venv/Scripts/python.exe"
elif [ -x "$BACKEND/.venv/bin/python" ]; then
  PY="$BACKEND/.venv/bin/python"
else
  echo "[ERROR] backend/.venv not found; run: uv sync --extra dev --inexact" >&2
  exit 1
fi

PG_PORT="${E2E_PG_PORT:-55432}"
NAME="crux-e2e-$$"
LOGS="$FRONTEND/test-results/e2e-local"
JWKS_PID=""
API_PID=""

port_open() {
  "$PY" -c "import socket,sys; s=socket.socket(); s.settimeout(0.5); sys.exit(0 if s.connect_ex(('127.0.0.1', int(sys.argv[1]))) == 0 else 1)" "$1"
}

url_ok() {
  "$PY" -c "import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=2)" "$1" >/dev/null 2>&1
}

cleanup() {
  [ -n "$API_PID" ] && kill "$API_PID" >/dev/null 2>&1 || true
  [ -n "$JWKS_PID" ] && kill "$JWKS_PID" >/dev/null 2>&1 || true
  docker rm -f "$NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Fail fast on a busy port. 5173 matters too: off CI, Playwright reuses an
# existing dev server, which may point at a different API base URL.
for p in "$PG_PORT" 8787 8000 5173; do
  if port_open "$p"; then
    echo "[ERROR] port $p is already in use; stop whatever holds it and rerun" >&2
    exit 1
  fi
done

mkdir -p "$LOGS"

docker run -d --rm --name "$NAME" \
  -e POSTGRES_USER=crux -e POSTGRES_PASSWORD=crux -e POSTGRES_DB=crux_e2e \
  -p "${PG_PORT}:5432" pgvector/pgvector:pg17 >/dev/null

export DATABASE_URL="postgresql://crux:crux@localhost:${PG_PORT}/crux_e2e"
export CRUX_SKIP_DOTENV=1
export LLM_STUB=1
# Fake issuer origin; must match ISSUER_ORIGIN in e2e/support/auth-keys.js.
export SUPABASE_URL="http://e2e-auth.invalid"
export SUPABASE_JWKS_URL_OVERRIDE="http://127.0.0.1:8787/jwks.json"

# pg_isready goes green before the host port forward accepts connections, so
# the migration is retried as well.
migrated=0
for _ in $(seq 1 30); do
  if (cd "$BACKEND" && "$PY" -m alembic upgrade head) >"$LOGS/alembic.log" 2>&1; then
    migrated=1
    break
  fi
  sleep 1
done
if [ "$migrated" -ne 1 ]; then
  echo "[ERROR] alembic upgrade head failed; see $LOGS/alembic.log" >&2
  exit 1
fi
echo "[OK] Postgres on port ${PG_PORT} migrated to head"

(cd "$FRONTEND" && node e2e/support/gen-auth-keys.js) >/dev/null
"$PY" -m http.server 8787 --bind 127.0.0.1 --directory "$FRONTEND/e2e/.auth/jwks" \
  >"$LOGS/jwks.log" 2>&1 &
JWKS_PID=$!

(cd "$BACKEND" && exec "$PY" -m uvicorn main:app --port 8000 --host 127.0.0.1) \
  >"$LOGS/backend.log" 2>&1 &
API_PID=$!

# /ready probes the database; /health is liveness only.
ready=0
for _ in $(seq 1 30); do
  if url_ok http://127.0.0.1:8787/jwks.json && url_ok http://127.0.0.1:8000/ready; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "[ERROR] JWKS or backend did not come up; see $LOGS/" >&2
  exit 1
fi
echo "[OK] JWKS and backend ready"

cd "$FRONTEND"
VITE_API_BASE_URL="http://localhost:8000/api" npx playwright test "$@"
