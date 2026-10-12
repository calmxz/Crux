#!/usr/bin/env bash
# Run backend tests against a throwaway pgvector Postgres, the way CI does.
#
# Postgres-only test files skip (and still show green) without
# TEST_DATABASE_URL. This starts pgvector/pgvector:pg17 in Docker, migrates
# it with `alembic upgrade head`, runs pytest with TEST_DATABASE_URL set, and
# removes the container on exit.
#
# Usage, from backend/:
#   scripts/pg_tests.sh                                     # whole suite
#   scripts/pg_tests.sh tests/test_llm_characterisation_pg.py --no-cov
# Extra arguments go to pytest unchanged. PG_TESTS_PORT overrides the host
# port (default 55432).
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -x .venv/Scripts/python.exe ]; then
  PY=.venv/Scripts/python.exe
elif [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
else
  echo "[ERROR] backend/.venv not found; run: uv sync --extra dev --inexact" >&2
  exit 1
fi

PORT="${PG_TESTS_PORT:-55432}"
NAME="crux-pg-tests-$$"
URL="postgresql://crux:crux@localhost:${PORT}/crux_test"

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker run -d --rm --name "$NAME" \
  -e POSTGRES_USER=crux -e POSTGRES_PASSWORD=crux -e POSTGRES_DB=crux_test \
  -p "${PORT}:5432" pgvector/pgvector:pg17 >/dev/null

# pg_isready inside the container goes green before the host port forward
# accepts connections, so the migration is retried briefly as well.
for _ in $(seq 1 30); do
  docker exec "$NAME" pg_isready -U crux -d crux_test >/dev/null 2>&1 && break
  sleep 1
done

migrated=0
for _ in $(seq 1 10); do
  if DATABASE_URL="$URL" CRUX_SKIP_DOTENV=1 "$PY" -m alembic upgrade head >/dev/null 2>&1; then
    migrated=1
    break
  fi
  sleep 1
done
if [ "$migrated" -ne 1 ]; then
  echo "[ERROR] alembic upgrade head failed against $URL" >&2
  DATABASE_URL="$URL" CRUX_SKIP_DOTENV=1 "$PY" -m alembic upgrade head
  exit 1
fi
echo "[OK] Postgres on port ${PORT} migrated to head"

TEST_DATABASE_URL="$URL" "$PY" -m pytest "$@"
