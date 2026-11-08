# The old code

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file is the comparison against the old code, not product rules. It covers the verdict, each backend module's fate, what is copied with its tests, and what is left behind. No product file links to it: every backend build ticket names it beside its area files (see [`spec-process.md`](spec-process.md)) ([#750]). The facts behind it are on [#749].

## Terms

- **Rework:** the old file is copied into the new backend and changed until it fits ([#750]).
- **Rebuild:** the module is written new, with the old code open as a reference at most ([#750]).
- **Copied:** a piece of old code, smaller than a module, taken into a rebuilt module as code, with its tests ([#750]).
- **Left behind:** old code that is neither copied nor reworked. It stays a reference and goes with the old backend ([#750]).
- **Planted case:** a deliberate bad example, run once to prove a check fails on it ([#750]).

## The verdict

- The backend is a rewrite. A new backend is written against the spec ([#750]).
- Its first migration creates homes with row-level security. The old `users` table and concept lists never exist there ([#750]).
- Only the pieces this file lists as copied go in as code ([#750]).

## Backend modules

The modules are the ones in [`data-model.md`](data-model.md) ([#719]).

| Module | Verdict | Copied as code |
|---|---|---|
| Homes | Rebuild | None |
| Sign-in | Rebuild | None |
| Learning | Rebuild | None |
| Mastery check | Rebuild | None |
| Files | Rebuild | None |
| Tutor AI | Rebuild | None |
| Spending | Rebuild | The pricing piece |
| Safety | New, no old code | None |
| Feedback | New, no old code | None |
| Email | New, no old code | None |
| Operations | Rebuild | `routes/health.py`, `lib/request_id.py`, `lib/body_limit.py` |

All of this comes from [#750].

- **Tutor AI:** the whole `agent/` (tool loop, prompt, tools) is rebuilt. Two things in `services/llm.py` are borrowed as design: the test stub, and no retry once streaming starts ([#750]).
- **Spending:** the pricing piece is the rate table, the dated rate change and `usage_cost` in `services/cost_meter.py`. Its `gemini/...` model names become Agent Platform's, and its rates are re-checked against Agent Platform's price list. A dated rate change takes effect when Google's billing applies it; the build ticket checks Google's notice, and until then the copied date stays in UTC. The limits are written new ([#750]).
- **Operations:** the three copied files change their imports and drop their Render comment. The rebuilt database setup keeps psycopg's `connect_timeout`, which the copied `/ready` probe relies on. Error handling, logging and the backup are written new ([#750]).

## Copied tests and scripts

- Copied code comes with its tests: `test_health.py`, `test_request_id.py`, `test_body_limit.py`, and the pricing cases taken out of `test_cost_meter_estimate.py` and `test_chat_rates.py` ([#750]).
- Each moves onto the throwaway database where it touches one (see [`hosting.md`](hosting.md)) ([#750]).
- `gen_contracts.py` is copied (see [`hosting.md`](hosting.md)) ([#750]).

## Left behind

- The old schema and its 31 migrations, and every old module's code not listed as copied ([#750]).
- Old code with no module in the spec: the embedding search, the review queue, the data export, the usage summary, `display_name` and onboarding, ending and pinning sessions, `profile_insights.py`, `lib/etag.py`, and the live-model evaluation scripts ([#750]).
- The old `Dockerfile`, `config.py`, `main.py`, `worker.py` and `entrypoint.sh` are written new, with the old ones as a reference. `seed_debug_accounts.py` and `pg_tests.sh` are left behind ([#750]).
- The test suite apart from the copied tests, `conftest.py` included ([#750]).
- From the old CI: semgrep and trivy, the coverage gate and the Codecov upload, gitleaks, and `uv audit` in CI and the nightly `audit.yml`. The checks that stay are in [`quality-bar.md`](quality-bar.md) ([#750]).

## Gaps

- **The frontend's comparison:** its modules, its verdict, and its CI checks (hadolint on the frontend Dockerfile, CodeQL on JavaScript) wait for the screen prototypes, on the map's "Not yet specified" list ([#750]).
- **Where the new code lives, and when the old backend goes:** on the map's "Not yet specified" list. It also hangs on the frontend's verdict ([#750]).
- **Bringing the deployment back:** on the map's "Not yet specified" list. The new schema has no path from the old migrations ([#750]).

[#719]: https://github.com/calmxz/Crux/issues/719
[#749]: https://github.com/calmxz/Crux/issues/749
[#750]: https://github.com/calmxz/Crux/issues/750
