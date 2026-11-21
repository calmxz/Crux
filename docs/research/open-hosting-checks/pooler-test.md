# Item 1 hands-on test: row-level security through Supavisor in transaction mode (#726)

This is the hands-on test that `open-hosting-checks.md` lists under "Still to do" for item 1. It ran on a local Supabase stack on **2026-11-21**.

Every figure below points to a line in a log in [`pooler-test/`](pooler-test/). `run:57` means line 57 of `run-2026-11-21.log`. `leak:81` means line 81 of `leak-action-2026-11-21.log`.

## Short answer

- **The invariant holds with the safe pattern.** Each request opens one explicit transaction, sets the home with `set_config('app.home_id', <id>, true)` or `SET LOCAL`, and runs its queries in it. Ben then never sees Ana's rows after a commit, a rollback, or a mid-transaction error.
- **41 of 41 checks passed, 0 failed (`run:186`).** Every check has an expected value, and the script exits non-zero on any failure.
- **The test can fail: the positive controls showed the leak.** A session-level `SET` or `set_config(..., false)` by Ana leaked her home and her 3 rows to Ben on the same backend.
- **A leftover does not beat the safe pattern.** With Ana's session-level value still on the backend, Ben's own transaction saw only his 2 rows. A bare read with no home set saw Ana's 3 rows.
- **An unset home reads as NULL on a new backend and as an empty string on a reused one.** The policy needs `nullif(..., '')`. Without it, the empty string makes every query on that table fail with a uuid cast error.
- **The local pooler's leak check is `ignore`.** Set to `error`, it rejected both leaking forms and let the safe pattern through. This test cannot show the hosted pooler's value.

## What was run

| Part | Version | Log line |
|---|---|---|
| Supabase CLI (`npx -y supabase@latest`) | 3.2.0 | `run:4`, `versions-2026-11-21.log` |
| Postgres image | `public.ecr.aws/supabase/postgres:17.12.0.000` | `run:7` |
| Postgres server | PostgreSQL 17.12 | `run:9` |
| Supavisor image | `public.ecr.aws/supabase/supavisor:2.10.1` | `run:6` |
| Driver | psycopg 3.3.4, `prepare_threshold=None`, `autocommit=True` | `run:5` |
| Docker | 29.8.2 | `versions-2026-11-21.log` |

Setup:

- The stack ran only the database and the pooler. All other services were excluded.
- The pooler block in `supabase/config.toml` had `enabled = true`, `pool_mode = "transaction"`, and `default_pool_size = 1`. See `pooler-test/config-pooler-block.toml`.
- The local tenant is `pooler-dev`, with pool size 1, `txn_mode_leak_action = 'ignore'`, and `server_reset_query = 'DISCARD ALL'` (`run:11`).
- The `DISCARD ALL` reset did not run between transaction-mode clients in this run. Steps 5a and 5b show the session state surviving.
- Both clients log in as `crux_app.pooler-dev` on port 54329, the local transaction port. The hosted form is `crux_app.<project-ref>`.
- The tenant has `require_user = False` (`run:11`), so Supavisor looks up each role's password with an auth query. The container's tenant script sets it to `pgbouncer.get_auth`. No extra pooler user was needed for `crux_app`.
- Ana's home is `aaaaaaaa-...-0001`, with 3 sessions. Ben's is `bbbbbbbb-...-0002`, with 2. A leak therefore shows as a count of 3 where 0 or 2 is expected.

The files:

- `pooler-test/schema.sql` creates the role, the tables, the policies, and the seed rows.
- `pooler-test/pooler_rls_test.py` runs steps 2 to 7 and 8a. It has 41 checks, each with an expected value. It exits non-zero if any check fails.
- `pooler-test/leak_action_probe.py` runs step 8b.
- `pooler-test/run.sh` rebuilds the commands from the session in the order they ran. It was written after the run and has not been run itself. Its `sed` pattern and health wait differ slightly from the commands typed.
- The kept `run-2026-11-21.log` is the second run. The first run's table-owner query also matched Supabase's `auth.sessions` table. The query now filters on the `public` schema. No result changed.

### How the same-backend check works

- A probe reads `pg_backend_pid()`, the setting, and the row count in one statement. The pid therefore vouches for the data printed with it.
- Each step asserts that every pid A and B saw is the same.
- Between groups of steps, the script ends the `crux_app` server connection from the direct port with `pg_terminate_backend`. The pool then opens a new one, so each control starts clean.
- Every one of the 10 pid checks passed, for example `[642, 642]` (`run:58`) and `[651, 651, 651]` (`run:181`).
- The direct port showed one `crux_app` server connection at a time (`run:62`).

## Steps and results

### Step 2: roles, owners, and grants

- `crux_app`: `rolbypassrls = false`, `rolsuper = false` (`run:17`).
- `postgres`: `rolbypassrls = true`, `rolsuper = false` (`run:18`). So locally, Supabase's `postgres` role skips row-level security. The backend must not connect as it.
- `homes`, `sessions`, and `sessions_no_nullif` are owned by `postgres`, with row-level security on and not forced (`run:21` to `run:23`).
- `crux_app` holds only `SELECT` and `INSERT` on those tables (`run:25` to `run:27`).
- The policy text is `home_id = (NULLIF(current_setting('app.home_id', true), ''))::uuid` (`run:30`).

### Step 5: positive controls (session-level setting)

**5a. Session-level `SET`.** On a new backend, A ran `set app.home_id = '<ana>'` in autocommit. B then ran the probe.

- B read Ana's id and 3 rows, all Ana's titles (`run:57`).
- Pids: `[642, 642]` (`run:58`).
- Result: the leak is real. The test can detect it.

**5b. `set_config(..., false)`.** On another new backend, A ran `select set_config('app.home_id', '<ana>', false)`.

- B read Ana's id and 3 rows (`run:71`).
- Pids: `[650, 650]` (`run:72`).
- Result: the same leak.

**5c. A leftover on purpose, then the safe pattern.** The backend still held Ana's session-level value from 5b.

- With no home of its own, B read Ana's id and 3 rows (`run:79`).
- In its own transaction with `set_config('app.home_id', '<ben>', true)`, B read Ben's id and 2 rows, only Ben's titles (`run:83`).
- After B committed, the backend read Ana's id and 3 rows again (`run:85`).
- Pids: `[650, 650, 650]` (`run:86`).
- Result: a transaction-local value overrides a leftover only for its own transaction. Any query that runs without first setting the home inherits the leftover.

### Step 6: the safe pattern

All of step 6 ran on one new backend, pid 651.

| Case | A in its transaction | B afterwards | Log |
|---|---|---|---|
| 6a. `set_config(..., true)`, commit | Ana, 3 rows | `''`, 0 rows | `run:102`, `run:104` |
| 6b. Same, rollback | Ana, 3 rows | `''`, 0 rows | `run:115`, `run:117` |
| 6c. Same, `select 1/0` mid-transaction | Ana, 3 rows, then `DivisionByZero` | `''`, 0 rows | `run:127`, `run:130` |
| 6d. `SET LOCAL`, commit | Ana, 3 rows | `''`, 0 rows | `run:139`, `run:141` |
| 6e. B sets Ben the same way | B: Ben, 2 rows | A afterwards: `''`, 0 rows | `run:150`, `run:152` |

Two driver mistakes were also checked:

- **6f.** `set_config(..., true)` sent as its own autocommit statement ends with that statement. The next statement read `''` and 0 rows (`run:161`). The rule fails closed.
- **6g.** `SET LOCAL` outside a transaction block did nothing. The server sent `WARNING: SET LOCAL can only be used in transaction blocks`, and the next statement read 0 rows (`run:166`, `run:167`).

### Step 7: what an unset home reads as

| Backend state | `current_setting('app.home_id', true)` | Policy with `nullif` | Policy without `nullif` | Log |
|---|---|---|---|---|
| (a) New, never saw the setting | `None` (NULL) | 0 rows | 0 rows, no error | `run:39`, `run:41` |
| (b) Reused, after transaction-local sets | `''` (empty string) | 0 rows | Error: `invalid input syntax for type uuid: ""` | `run:173`, `run:176` |

- In this run, a backend that had never seen the setting read NULL (7a). After one committed transaction-local set, the same backend read `''`, not NULL (6a, `run:104`). It stayed `''` through 6b to 6g and 7b.
- On the shared pool, almost every backend is reused. So `''` is the normal case, not an edge case.
- Without `nullif`, the cast `''::uuid` raises an error. That fails closed, but it breaks every query on the table whenever no home is set. With `nullif`, the same query returns 0 rows.
- Use `nullif(current_setting('app.home_id', true), '')::uuid` in every policy.

### Step 8: Supavisor's leak check (`txn_mode_leak_action`)

**8a. Local value during the main run.** The tenant row reads `ignore` (`run:11`).

- During 5a to 5c, the pooler logged nothing about the session-level `SET`. Of 4 log lines, the only one matching leak, SET, warn, or error was the expected notice that the test ended a server connection (`run:92`, `run:93`).
- The unfiltered pooler log under `ignore` in step 8b shows the same: connection notices only (`leak:27` to `leak:31`).

**8b. Each value in turn (extra).** The script changed the local tenant row, restarted the pooler, and ran `leak_action_probe.py`. This probe logs pids but does not assert them. After the restart into `log`, the first two connects failed while the pooler started, and the third worked (`leak:40`, `leak:41`).

| Value | Session-level `SET` | `set_config(..., false)` | Safe pattern | Log |
|---|---|---|---|---|
| `ignore` | Runs. B reads Ana, 3 rows. Nothing logged. | Runs. B reads Ana, 3 rows. | A: Ben, 2 rows. B: `''`, 0 rows. | `leak:7` to `leak:30` |
| `log` | Runs. B reads Ana, 3 rows. Logs `[warning] received session-level SET statement in transaction mode`. | Runs. B reads Ana, 3 rows. Logs a matching warning. | Same as above. | `leak:39` to `leak:66` |
| `error` | Rejected: `(ESESSIONLEAK) session-level SET statement is not allowed in transaction mode`. The pooler closes A's connection. B reads NULL, 0 rows. | Rejected the same way. | Same as above. Not flagged. | `leak:75` to `leak:108` |

- Only `error` stops the leak. `log` warns but still lets B read Ana's rows.
- Under `error`, the safe pattern ran unchanged, so the setting does not get in its way.

## Answer to the invariant

Ben's query never sees Ana's rows when all of the following are true:

1. The backend connects as a role without `BYPASSRLS` that does not own the tables (`run:17`, `run:21`).
2. Every request runs its queries inside one explicit transaction.
3. The first statement in that transaction sets the home with `set_config('app.home_id', <id>, true)` or `SET LOCAL`.
4. Every policy reads the home as `nullif(current_setting('app.home_id', true), '')::uuid`.
5. No code anywhere runs a session-level `SET` or `set_config(..., false)` on the app role.

Condition 5 matters because the pooler does not clean up between clients on this local stack. Step 5c shows a leftover reaching any query that does not set its own home first.

On the hosted pooler, an `error` leak action would enforce condition 5. Whether Supabase sets it, or lets a project set it, is not shown here.

This confirms the docs-only finding in `open-hosting-checks.md`, section 1. It adds three points:

- The `nullif` is required, not optional.
- Local `postgres` has `BYPASSRLS`.
- The safe pattern protects only queries that set their own home.

## What this test cannot show

- **The hosted pooler's leak setting.** This test read and changed the local tenant row only. Supabase's value for `txn_mode_leak_action` on its shared pooler is not shown. Neither is whether a project can change it.
- **The hosted Supavisor version.** The local image is 2.10.1. The hosted pooler may run another version, with other leak detection or none.
- **Whether hosted `postgres` has `BYPASSRLS`.** Local `postgres` does (`run:18`). The hosted role is likely the same, but this test did not check it.
- **Pipelining.** Both clients sent one statement at a time and waited for the reply. The test did not cover queued queries, which Supabase warns can return mismatched rows in transaction mode.
- **Prepared statements and other drivers.** Only psycopg 3 with `prepare_threshold=None` was tested. asyncpg, SQLAlchemy pools, and named prepared statements were not.
- **Other ways to write the leaking call.** Step 8b tried a literal `SET` and a literal `set_config(..., false)` only. A call whose `is_local` argument is a bound parameter, or one inside a function, was not tried against the `error` check.
- **Load and timing.** Pool size 1 forced both clients onto one backend, one at a time. Many clients at once on a larger pool were not tested.
- **The pooler's session mode and the dedicated pooler.** Only the shared-pooler transaction mode on the local stack was tested.
