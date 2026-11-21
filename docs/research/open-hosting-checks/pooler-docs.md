# Item 1 from the docs: row-level security through Supabase's pooler (#726)

The hands-on test that checks this is in [`pooler-test.md`](pooler-test.md).

Every claim below comes from an official docs, pricing, terms or source-code page, all read on **2026-11-02**. Numbers in square brackets point to the source list at the end, numbered as in the first version of this note. Where a page was silent, this note says so.

The ticket's case: Ana's and Ben's requests share one pooled connection. Ben's query must not see Ana's rows.

### What clears a transaction-local setting

- `set_config(name, value, true)` applies "only during the current transaction" [1].
- `SET LOCAL` effects "last only till the end of the current transaction, whether committed or not" [2].
- A rollback to an earlier savepoint also cancels `SET` and `SET LOCAL` [2].
- So Ana's setting cannot stay behind. Postgres drops it at commit or rollback.
- In transaction mode the pooler hands the connection on only after a transaction ends [3]. Ben's transaction therefore starts with no learner set.

### What Supavisor does between clients

- Supavisor runs `DISCARD ALL` only on session-mode connections, before it returns them to the pool [4].
- In transaction mode it does not reset anything. Its own source says leftover session state "leaks across clients" [5].
- The leaking statements include session-level `SET`, `set_config` with `is_local` false, and `DISCARD` [5].
- Supavisor names `SET LOCAL` and `SET TRANSACTION` as "safe and never flagged" [5].
- Its leak check, `txn_mode_leak_action`, defaults to `ignore`. It can also log a warning or reject the statement [4][5].
- Supabase's own value for that setting on its hosted pooler is not stated in any page read.
- Supabase's connect page says session-level state "is lost between transactions" [3]. Supavisor's source adds that another client can receive it [5].

### Failure modes

- **A plain session-level `SET`, or `set_config(..., false)`.** It survives the commit and reaches the next client on that connection [2][5].
- **`SET LOCAL` outside a transaction block.** Postgres "emits a warning and otherwise has no effect" [2].
- **Autocommit drivers.** A `set_config(..., true)` in its own statement ends with that statement. The next query runs unset [1].
- **Prepared statements.** The shared pooler does not support them in transaction mode [3][6].
- Turn them off in the driver. Psycopg: `prepare_threshold=None`. asyncpg: `statement_cache_size=0` [3][6].
- **Query pipelining.** Transaction mode can hand a connection on while queued queries remain. This "can hang queries or return mismatched rows" [3].
- **Wrong role.** Superusers and `BYPASSRLS` roles always skip the rules [7].
- Table owners skip them too, unless the table has `FORCE ROW LEVEL SECURITY` [7][8].
- **Views.** Supabase warns that views made by `postgres` bypass row-level security by default [9].
- **Security-definer functions.** They run as their creator, so one made by `postgres` bypasses the rules [9].

### Which role the backend connects as

- Supabase's `postgres` role "has admin privileges" [10]. The page does not say whether it has `BYPASSRLS`.
- Tables made from the dashboard or by migrations as `postgres` are owned by `postgres`. The owner skip applies either way [7].
- `service_role` has the bypass, so the backend must not use it [9][10].
- Use a custom login role with `NOBYPASSRLS`, the Postgres default [11]. Grant it only the table rights it needs.
- Keep `postgres` as the table owner, or add `FORCE ROW LEVEL SECURITY` on every learner table [7][8].
- Through the shared pooler, a custom role's username is `[ROLE].[PROJECT-REF]` [3].

### The safe pattern

1. Connect as the custom role on the transaction-mode port 6543, with prepared statements and pipelining off [3][6].
2. Open one explicit transaction for each unit of work.
3. Run `select set_config('app.learner_id', '<id>', true)` as its first statement [1].
4. Run every data query for that learner inside the same transaction.
5. Commit or roll back. Postgres clears the setting either way [2].
6. Write each policy to return no rows when the setting is missing or empty.

Read the setting with `current_setting('app.learner_id', true)`, which returns NULL when it is missing [1].

Whether an unset custom setting reads as NULL or as an empty string on a reused connection is not stated in the docs read. The hands-on test answers it: NULL on a new backend, an empty string on a reused one. So each policy needs `nullif(..., '')` before its cast (see [`pooler-test.md`](pooler-test.md)).

### Answer

- The #716 rule holds on Supabase Free, under the conditions above. No connection rule changes.
- #719 records the role: a custom role without the bypass, not the table owner, or `FORCE ROW LEVEL SECURITY` on every table.

## Sources (all read 2026-11-02)

1. PostgreSQL 17, configuration settings functions (`set_config`, `current_setting`): https://www.postgresql.org/docs/17/functions-admin.html
2. PostgreSQL 17, SET: https://www.postgresql.org/docs/17/sql-set.html
3. Supabase, Connect to your database (transaction mode limitations, pooler usernames): https://supabase.com/docs/guides/database/connecting-to-postgres
4. Supavisor, tenant configuration (`server_reset_query`, `txn_mode_leak_action`), main branch at commit c89d880: https://github.com/supabase/supavisor/blob/main/docs/configuration/tenants.md
5. Supavisor source, `SessionLeaks` module, main branch at commit c89d880: https://github.com/supabase/supavisor/blob/main/lib/supavisor/protocol/session_leaks.ex
6. Supabase, Disabling prepared statements: https://supabase.com/docs/guides/troubleshooting/disabling-prepared-statements-qL8lEL
7. PostgreSQL 17, Row Security Policies: https://www.postgresql.org/docs/17/ddl-rowsecurity.html
8. PostgreSQL 17, ALTER TABLE (`FORCE ROW LEVEL SECURITY`): https://www.postgresql.org/docs/17/sql-altertable.html
9. Supabase, Row Level Security (views, security definer, `service_role`): https://supabase.com/docs/guides/database/postgres/row-level-security
10. Supabase, Postgres Roles: https://supabase.com/docs/guides/database/postgres/roles
11. PostgreSQL 17, CREATE ROLE (`BYPASSRLS`): https://www.postgresql.org/docs/17/sql-createrole.html
