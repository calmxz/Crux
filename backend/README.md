# Crux Backend

FastAPI + Supabase Postgres (pgvector). Python 3.14+.

## Setup

From `backend/`:

```bash
uv sync --locked --extra dev
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
```

Installs the committed `uv.lock`, the same versions CI and the Docker image use.

## Environment

Create `.env` at the **repo root** (not `backend/`):

```
GEMINI_API_KEY=your-key-here
MODEL=gemini/gemini-3.8-flash
EMBEDDING_MODEL=gemini/gemini-embedding-2
DAILY_CAP=50
```

Optional overrides: `EMBEDDING_MODEL`, `DATABASE_URL`, `EMBEDDING_DIM` (768), `UPLOADS_PATH`, `CORS_ORIGINS`, `ENV`.

`DATABASE_URL` defaults to a local SQLite file (`sqlite:///.../data/app.db`) for local dev. Tests never touch it: each runs on its own in-memory engine, and connecting on the default one fails the test. **Production requires a Supabase-managed Postgres URL** — pgvector needs Postgres. Supabase env vars: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, `SUPABASE_JWKS_URL_OVERRIDE`. LLM spend caps (per user, per UTC day): `LLM_SOFT_CAP_USD` (2.00, emits `X-Cost-Warning`), `LLM_HARD_CAP_USD` (3.00, returns 429).

Paths in `config.py` are anchored to the repo root, so the server runs correctly from any working directory. `data/uploads/` is auto-created on first boot; `data/app.db` is created only when running the local SQLite default.

## Run

From `backend/`:

```bash
uvicorn main:app --reload
```

From repo root:

```bash
uvicorn main:app --reload --app-dir backend
```

Server: `http://127.0.0.1:8000`. Health check: `GET /health`.

## Tests

From `backend/`:

```bash
pytest -v
pytest tests/test_foo.py::test_bar   # single test
```

Tests use in-memory SQLite — no filesystem dependency.

## Docker

Local dev does **not** use Docker for app infra. `docker-compose.yml` is a no-op anchor (`services: {}`) — `docker compose up` brings up nothing. Postgres + pgvector and Auth are Supabase-managed (external cloud), so there is no local DB or vector-store container.

### Local dev (native)

- `.env` at repo root with `GEMINI_API_KEY` populated. Read directly by `config.py`.

Backend (from `backend/`):

```bash
uvicorn main:app --reload
```

Frontend (from `frontend/`):

```bash
npm run dev
```

### Volumes

`./data/uploads/` (uploaded PDFs) is the only real local volume. The database and vectors live in Supabase. `./data/app.db` exists only when running the local SQLite default.

### Deploy / public-demo stack

`docker-compose.prod.yml` is the actual deploy stack (nginx-served frontend + uvicorn backend). From repo root:

```bash
docker compose -f docker-compose.prod.yml --env-file .env up --build
```

Frontend is served on host port 80. Expose a public URL via:

```bash
ngrok http 80
```

## Contracts

Pydantic models in `contracts/` are generated from `docs/api/openapi.yaml`. Edit the YAML, then regenerate:

```bash
python backend/scripts/gen_contracts.py
```

CI fails on drift.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: fastapi` | venv not active | activate `.venv` or call `.venv\Scripts\python.exe -m uvicorn ...` directly |
| `sqlite3.OperationalError: unable to open database file` | stale `config.py` with cwd-relative paths | pull latest; paths now anchored to repo root |
| `GEMINI_API_KEY` empty at runtime | `.env` missing or in `backend/` | move `.env` to repo root |
