# Research: open hosting checks, items 1 to 4 (#726)

Question: four facts left open by #716, #675 and #717, each able to change a recorded decision. Item 5 and item 1's hands-on test are not in this note.

Every claim below comes from an official docs, pricing, terms or source-code page, all read on **2026-11-02**. Numbers in square brackets point to the source list at the end. Where a page was silent, this note says so.

## Short answer

| Item | Answer in one line | Goes against the spec? | Recorded decision that changes |
|---|---|---|---|
| 1. Row-level security through the pooler | Safe with `SET LOCAL` or `set_config(..., true)` inside one explicit transaction. A session-level `SET` leaks to the next client. | No | #716's rule holds. #719 records a custom role: no bypass, not the table owner, prepared statements off. |
| 2. Spend cap and the free credit | Yes, the cap counts gross list-price use before credits. The free tier is a credit. | Yes | #716's caps (USD 6 live, USD 2 staging) are gross amounts. #675's hosting costs and the map's constraints line follow. |
| 3. Alerting charges | From no sooner than 1 September 2027: USD 0.35 a month per log-based rule. Uptime and billing alerts stay free. | Yes | #675 gains about USD 2.80 a month for 8 rules. #717 may cut rules or move items to the daily email. |
| 4. Zoho Mail free plan and the DPA | Not stated. Zoho signs a DPA on request per organization, and its legal team may refuse. | Unknown | #717 stays conditional. The owner requests the DPA from a free organization before opening. |

Still to do: item 1's hands-on test, and all of item 5. See "Still to do" at the end.

---

## 1. Row-level security through Supabase's pooler, transaction mode

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

Whether an unset custom setting reads as NULL or as an empty string on a reused connection is not stated in the docs read.

### Answer

- The #716 rule holds on Supabase Free, under the conditions above. No connection rule changes.
- #719 records the role: a custom role without the bypass, not the table owner, or `FORCE ROW LEVEL SECURITY` on every table.

---

## 2. Does the Cloud Run spend cap count use before the free credit?

### What the pages say

- The cap "is enforced when your gross, estimated usage costs exceed 100% of your budget amount" [12].
- Estimated costs use "the list price of services and don't include savings and credits" [12].
- "For spend cap budgets, you can't edit the Savings settings" [12]. No "include credits" choice exists.
- Google's API example of a Cloud Run spend cap shows `creditTypesTreatment: EXCLUDE_ALL_CREDITS` [13].
- The budgets page lists "Free tier credits" as a savings type [14].
- It says "credits are applied to implement the free tier usage" [14]. The billing export lists `FREE_TIER` as a credit type [15].
- Firebase's spend-cap page agrees: the cap "is based on gross costs and do not include savings and credits" [16].
- Each cap covers one project and one eligible service. Cloud Run is eligible [12].
- A triggered cap pauses every Cloud Run service in the project. Services return 5xx errors [17].
- Enforcement is not instant, and any overage is billed as normal [12].

### One ambiguity

- The setup steps say some services get fast gross estimates. The "remaining services" use actual costs "inclusive of all savings" [12].
- The page does not say which services are which.
- This note reads Cloud Run as gross, from the general limitation sentence and the Cloud Run API example [12][13].
- The first month's spend amount on the budget page settles it.

### The ticket's example

- A staging month of USD 4.80 gross trips the USD 2 staging cap, though the credit covers it and the bill is 0.
- Live pauses when live alone reaches USD 6 gross, whatever the shared credit has left.
- The credit is shared across the billing account [18]. Each cap counts only its own project's Cloud Run use.
- The converter and the tasks service share the live cap if they run as Cloud Run services in that project.

### Answer

- Yes, it counts use before the credit. This matches #716's "unconfirmed" reading, so the caps are gross amounts.
- #716's caps (USD 6 live, USD 2 staging) and fallback caps (about USD 8, about USD 16) need sizing on gross list-price use.
- #675's hosting costs and the map's constraints line should state the caps as gross.

---

## 3. Alerting charges from 1 September 2027

### What the page says

- "Starting no sooner than September 1, 2027, Cloud Monitoring will begin charging for alerting" [19].
- USD 0.35 a month for each metric reference in an alerting policy [19].
- USD 0.50 per million points returned by a metric alerting policy's conditions [19].
- In filter-based policies, "each condition counts as 1 metric reference" [19].
- Log-match policies, used for log-based alerts, "can have only a single condition" [19].
- "Log-match conditions return no points," so log-based rules pay no points charge [19].
- Metric policies on Billing, Quota or Uptime metrics are not charged [19].
- Log-based policies for Personalized Service Health logs are not charged [19]. No other log-based exception is listed.
- To stop a charge, modify, delete or disable the policy [19].

### Caveat

- The page defines a metric reference as "a single mention of a metric name" [19]. A log-match condition names no metric.
- This note reads each log-based rule as 1 reference, because the single-condition rule sits under the per-condition charge [19].
- The pricing examples page gives no log-based example [20]. The cost-control page gives none either [21].

### The ticket's example

- About 8 log-based rules come to about USD 2.80 a month, or USD 33.60 a year.
- Uptime checks: the first 1 million executions a month are free [20]. #717's 52,000 a month stay free.
- #717 sends errors through Error Reporting, not an alert rule. The real rule count is #717's to settle.

### Answer

- Log-based rules do cost money from no sooner than 1 September 2027, at about USD 0.35 a month each.
- #675's hosting costs gain about USD 2.80 a month for 8 rules.
- #717 can merge rules, or move less urgent items to the daily email.

---

## 4. Zoho Mail's free plan and Zoho's DPA

### What the pages say

- Zoho's privacy policy says Zoho is "prepared to sign an appropriate Data Processing Addendum (DPA)" [22].
- A customer requests it through a form. Zoho then sends it for signature [22].
- Zoho processes "service data" on the customer's behalf, with no plan named [22].
- The Zoho Accounts help page puts the DPA under the Privacy tab of a Zoho account [23].
- "Only the administrator of an organization can initiate a DPA request" [23].
- "Zoho's legal team reserves the right to reject a DPA request" [23].
- Zoho's GDPR page asks organization administrators to request a copy from legal@zohocorp.com [24].
- Zoho's terms of service do not mention a DPA or limit one to paid plans [25].
- Zoho Mail's Forever Free plan: one domain, up to 5 users, 5 GB each, no IMAP, POP or ActiveSync [26].
- The free plan is "available only in select data centers" [26].

### Answer

- No Zoho page read says the DPA covers the free plan. None excludes it either.
- The DPA text itself sits behind a Zoho sign-in, so its plan terms were not read.
- #717 stays conditional.
- The owner can settle it before opening: create the free organization, initiate the DPA, and see whether Zoho approves.
- If Zoho refuses, Workspace Business Starter (about USD 84 a year) joins #675's hosting costs and the map's constraints.

---

## Still to do

- **Item 1, hands-on test.** Docker and the Supabase CLI are not available here. Run it on the owner's computer or a live project.
- Check `select rolbypassrls from pg_roles where rolname = 'postgres'`.
- Set a learner with a session-level `SET`, then show a second client on the same pooled connection sees it.
- Repeat with `set_config(..., true)` and show the second client sees no learner and no rows.
- Check whether an unset custom setting reads as NULL or an empty string on a reused connection.
- Check whether Supabase's hosted pooler logs or rejects session-level `SET` in transaction mode.
- **Item 5, server time per study block and per upload.** Not started. It needs the owner's decks and the owner's Google login.
- **Item 2's ambiguity.** The first month's spend amount on the staging budget page shows gross or net.

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
12. Google Cloud Billing, Manage spend cap budgets ("Last updated 2026-10-26 UTC"): https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps
13. Google Cloud Billing, Using the Cloud Billing Budget API for spend cap budgets: https://docs.cloud.google.com/billing/docs/how-to/budget-api-spend-cap
14. Google Cloud Billing, Create, edit, or delete budgets and budget alerts (Savings types; "Last updated 2026-10-26 UTC"): https://docs.cloud.google.com/billing/docs/how-to/budgets
15. Google Cloud Billing, standard usage cost export (`credits.type`): https://docs.cloud.google.com/billing/docs/how-to/export-data-bigquery-tables/standard-usage
16. Firebase, spend caps ("Last updated 2026-10-20 UTC"): https://firebase.google.com/docs/projects/billing/spend-caps
17. Cloud Run, Best practices for cost-optimized Cloud Run services ("Last updated 2026-10-30 UTC"): https://docs.cloud.google.com/run/docs/tips/services-cost-optimization
18. Cloud Run pricing: https://cloud.google.com/run/pricing
19. Google Cloud Observability pricing, Pricing for alerting: https://cloud.google.com/stackdriver/pricing
20. Google Cloud Observability pricing examples (alerting policies, uptime checks): https://cloud.google.com/stackdriver/observability-pricing-examples
21. Cloud Monitoring, Manage alerting costs ("Last updated 2026-10-26 UTC"): https://docs.cloud.google.com/monitoring/alerts/cost-control
22. Zoho privacy policy ("Last updated on: 22nd Dec 2025"): https://www.zoho.com/privacy.html
23. Zoho Accounts help, Privacy (DPA): https://help.zoho.com/portal/en/kb/articles/privacy
24. Zoho GDPR page: https://www.zoho.com/gdpr.html
25. Zoho terms of service ("Last updated on: 2nd March 2022"): https://www.zoho.com/terms.html
26. Zoho Mail pricing: https://www.zoho.com/mail/zohomail-pricing.html
