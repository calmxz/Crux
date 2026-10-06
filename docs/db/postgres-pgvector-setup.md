# Postgres + pgvector Setup

Phase 7 migrates Crux off SQLite + ChromaDB to Supabase-managed
Postgres with the `pgvector` extension. This doc covers the database side of
that migration: extension enablement, schema layout for embeddings, and
ivfflat tuning notes.

`DATABASE_URL` provisioning and the connection-string format are in
`docs/auth/supabase-setup.md` §3. This doc assumes you already have a
working `DATABASE_URL` and `psql` access.

## 1. Enable the `vector` extension

In Supabase: `SQL Editor → New query`:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

This is idempotent. You should also see `vector` listed under
`Database → Extensions` in the dashboard.

## 2. Apply the Crux baseline migration

The Phase 7 Alembic baseline (`backend/db/alembic/versions/0001_phase7_baseline.py`)
creates every application table — `users`, `sessions`, `chat_messages`,
`usage_counters`, `learning_events`, `documents`, `daily_cost_ledger`. The
follow-up migration (`backend/db/alembic/versions/0002_chunk_embeddings.py`)
enables the `vector` extension and creates the `chunk_embeddings` table that
pgvector backs.

From the `backend/` directory, with `DATABASE_URL` set:

```bash
alembic upgrade head
```

Verify with:

```bash
psql "$DATABASE_URL" -c "\dt"
psql "$DATABASE_URL" -c "\d chunk_embeddings"
```

## 3. `chunk_embeddings` schema

```sql
CREATE TABLE chunk_embeddings (
  id          TEXT PRIMARY KEY,
  session_id  TEXT NOT NULL REFERENCES sessions(id),
  document_id INT  NOT NULL REFERENCES documents(id),
  chunk_index INT  NOT NULL,
  page        INT,
  chunk_text  TEXT NOT NULL,
  embedding   vector(768) NOT NULL,
  created_at  TIMESTAMPTZ
);

CREATE INDEX ix_chunk_embeddings_session_id
  ON chunk_embeddings (session_id);

CREATE INDEX ix_chunk_embeddings_document_id
  ON chunk_embeddings (document_id);

CREATE INDEX ix_chunk_embeddings_embedding
  ON chunk_embeddings
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

Notes:

- `vector(768)` matches `EMBEDDING_DIM` (`config.py` `embedding_dim=768`),
  the output dimension of the configured embedding model
  `gemini/gemini-embedding-2`. If you change `EMBEDDING_DIM` or swap to a model
  with a different output dimension, update the column type and re-embed all
  chunks — pgvector enforces dimensionality.
- `ivfflat` (vs `hnsw`) was chosen because Supabase Postgres 17 ships with
  pgvector 0.8.x which supports both, but `ivfflat` is well-tested, faster
  to build, and adequate for the corpus sizes we expect (<100k chunks per
  user in v1). Revisit `hnsw` if recall/latency profile changes.
- The session-scoped B-tree on `session_id` is what most retrieval queries
  filter on first; the ivfflat index then narrows the cosine search within
  that subset.

## 4. ivfflat tuning notes

- `lists = 100` is a reasonable default for tables in the 1k–1M row range.
  Heuristic: `lists ≈ rows / 1000` for <1M rows, `lists ≈ sqrt(rows)` above.
- Probes (query-time accuracy/speed tradeoff) is set per-session in the
  retrieval service:
  ```sql
  SET LOCAL ivfflat.probes = 10;
  ```
  Higher = better recall, more rows scanned. 10 is a common starting point;
  drop to 1-5 if latency becomes an issue, raise to 20-40 if retrieval
  misses obvious matches.
- ivfflat indexes must be **rebuilt** if the data distribution changes a
  lot (e.g. after bulk imports). `REINDEX INDEX ix_chunk_embeddings_embedding;`
  is the lever.

## 5. Daily cost ledger

`daily_cost_ledger` is plain Postgres, no pgvector needed:

```sql
CREATE TABLE daily_cost_ledger (
  user_id    TEXT NOT NULL REFERENCES users(id),
  date_utc   TEXT NOT NULL,
  cost_usd   NUMERIC(10, 4) NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (user_id, date_utc)
);
```

The composite PK is the upsert target; `backend/services/cost_meter.py`
`record_cost()` writes to `(user_id, today_utc)` on every paid LLM call.
The `daily_cost_cap_reached` envelope and `X-Cost-Warning` header read
straight off this table.

## 6. Test database

For backend pytest against a real Postgres (instead of mocked):

```bash
docker run -d --name crux-test-pg \
  -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=crux_test \
  -p 55432:5432 \
  pgvector/pgvector:pg16

DATABASE_URL=postgresql+psycopg://postgres:test@127.0.0.1:55432/crux_test \
  alembic upgrade head

DATABASE_URL=postgresql+psycopg://postgres:test@127.0.0.1:55432/crux_test \
  pytest
```

The `pgvector/pgvector:pg16` image ships with the extension pre-installed;
the Alembic baseline runs `CREATE EXTENSION IF NOT EXISTS vector` for you.

## 7. Backups

Daily `pg_dump -Fc` snapshots go to Cloudflare R2 via
`.github/workflows/backup.yml` (retention: newest 7). Restore procedure and the
proven restore log live in `docs/deploy/RESTORE.md`. Supabase's built-in daily
backups (free tier: 7-day retention) are the secondary recovery point.

Before any destructive migration, take a manual dump as well:

```bash
pg_dump "$DATABASE_URL" --no-owner --no-acl > backup_$(date +%Y%m%d).sql
```
