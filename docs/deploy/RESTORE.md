# Restore drill — Postgres from R2

Backups are daily `pg_dump -Fc` snapshots at `crux/pg/YYYY-MM-DD/dump.pgc` in the
R2 bucket, produced by `.github/workflows/backup.yml`. Retention: newest 7.

**Never restore straight over production. Always restore into a scratch DB first.**

`backend/tests/test_backup_workflow.py` reads this file and asserts it still mentions `pg_restore`, `--clean` and a scratch database; keep all three when editing.

## Steps

1. List available dumps (or use the R2 dashboard):
   - Set `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.
   - `cd backend && python -c "from scripts.backup import R2Store; [print(o.key) for o in R2Store.from_env().list('crux/pg/')]"`
2. Download the chosen dump (R2 dashboard or `aws s3 cp --endpoint-url $R2_ENDPOINT`).
3. Restore into a scratch DB (a local Postgres 17 or a throwaway Supabase project):
   - `pg_restore --clean --if-exists -d "$TARGET_DATABASE_URL" dump.pgc`
4. Verify:
   - Row counts on key tables (users, sessions, chunk_embeddings, daily_cost_ledger).
   - A sample query returns expected data.
5. Paste the actual command output below.

## Proven restore log

**Run 2026-08-07 (UTC), dump `crux/pg/2026-08-07/dump.pgc` (450,836 bytes). PASS.**

Scratch target: `pgvector/pgvector:pg17` docker container (PostgreSQL 17.10), local machine.
Mechanical RTO: **2 min 29 s** (11:50:20Z first R2 list -> 11:52:49Z verified vector query).
Realistic RTO estimate ~15-20 min including credential recovery: the original R2 token
secret is not retrievable (GitHub secrets are write-only), so a fresh scoped R2 API token
had to be created in the Cloudflare dashboard first. Keep a restore credential in a
password manager to keep RTO at the low number.

Dump listing (retention working — exactly 7 daily dumps):

```
crux/pg/2026-08-01/dump.pgc  440,694 bytes
...
crux/pg/2026-08-07/dump.pgc  450,836 bytes  2026-08-07 04:49:58+00:00
```

Restore command and verification (real output):

```
$ pg_restore --clean --if-exists -U postgres -d crux_restore /tmp/dump.pgc
pg_restore: warning: errors ignored on restore: 268   (exit code 1)

$ psql -d crux_restore -c "select ... counts ..."
 users             |     2
 sessions          |    34
 documents         |     7
 chunk_embeddings  |     8
 daily_cost_ledger |    21
 learning_events   |    64

$ psql -d crux_restore -c "select version_num from public.alembic_version;"
 0022_documents_session_idx

$ psql -d crux_restore -c "set search_path to public, extensions;
    select id from public.chunk_embeddings
    order by embedding <=> (select embedding from public.chunk_embeddings limit 1) limit 3;"
 7b86c898-bf94-4976-b9f9-4f4058a4b455
 8812f408-a069-479f-94be-ccd4793b75d6
 334744e3-01c3-4c5a-820a-c67170284f3f

$ psql -d crux_restore -c "select count(*) from auth.users;"
 2
```

Findings (read these before the next restore):

1. **Exit code 1 does not mean failure.** All 268 ignored errors are Supabase
   infrastructure the dump carries but a plain Postgres lacks: missing roles
   (`supabase_admin`, `dashboard_user`, `anon`, `service_role`, ...) and the
   `supabase_vault` extension. **Zero errors touched `public.*`.** Judge a restore by
   row counts and queries, never by pg_restore's exit code.
2. **pgvector lands in the `extensions` schema** (Supabase convention preserved by the
   dump). Vector operators resolve only with `set search_path to public, extensions;`
   (Supabase sets this at the database level in production; a scratch DB does not).
3. `auth.users` data restores (2 accounts), so user identities are recoverable, but
   Supabase Auth *service* config (providers, JWT keys) is not in the dump — a full
   production rebuild would also need a new Supabase project + `docs/auth/supabase-setup.md`.
4. Latent restore hazards C-15/C-16/C-18 did **not** fire on this dataset.

## Owed human gates

1. Create the R2 bucket + scoped API token; add the 5 secrets to GitHub Actions
   (`DATABASE_URL`, `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
   `R2_BUCKET`).
2. Trigger the workflow via `workflow_dispatch` and confirm one green run.
3. ~~Run the restore drill above once and paste its output.~~ Done 2026-08-07 — see Proven restore log.
