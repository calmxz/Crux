# Research: how far the old backend is from the spec's modules (#749)

Question: for each of the 11 backend modules in [`data-model.md`](../spec/data-model.md) (Modules), what old code does the same job, and how much of it already matches the spec?

The old code is `backend/` and `.github/workflows/` at `f0a52c0`, read on 2026-11-08 and not run. The spec is `docs/spec/` at the same commit, cited as file and section. This note sizes gaps only. Keep, rework, rebuild or delete is for [#750](https://github.com/calmxz/Crux/issues/750).

**Size key.** Small: the old code does the job, with local changes. Medium: the old code holds a working core, and the spec adds real parts. Large: nothing exists, or the old model differs at its core.

## Short answer

Nine modules have a large gap and two a medium one. The old schema has no home: learner tables key on a Supabase Auth user ID, with no row-level security and almost no delete with parent. The old domain model is concept lists and multiple-choice sets, not objectives with statuses and written problems with a separate marker. Safety, Feedback and Email have no old code. The model-call adapter and the spend counter come closest: their shape follows the spec, but the provider and limits under them differ.

| Module | Old code | Gap | Size |
|---|---|---|---|
| Homes | `users`, `user_service.py`, `routes/me.py` | No trial links, stubs, undo, copies or erasure routine | Large: one users row, no home |
| Sign-in | `services/auth.py` | Supabase JWT check, not Crux's own OAuth and codes | Large: the way in is replaced |
| Learning | `routes/sessions.py`, `chat.py`, `profile_service.py`, `summary_service.py` | Concept lists, not topics and objectives; AI-written summaries; no waiting messages | Large: the domain model differs |
| Mastery check | `check_service.py`, `learning_events` | Multiple choice graded by index, not written problems and a marker | Large: the check model differs |
| Files | `routes/upload.py`, `ingestion_service.py`, `worker.py` | Text chunks and embeddings, not outlines and page slices | Large: storage and reading differ |
| Tutor AI | `services/llm.py`, `agent/` | One-module shell fits; LiteLLM on an API key, other tools and prompt | Medium: shell fits, contents change |
| Spending | `cost_meter.py`, `daily_cost_ledger` | List-price counting fits; limits are USD per user per UTC day | Medium: counter fits, limits change |
| Safety | None | Declines, flags, seals, locks, age outcomes all missing | Large: nothing exists |
| Feedback | None | Page, counts, marks, window, arrivals all missing | Large: nothing exists |
| Email | None | No sending of any kind | Large: nothing exists, though the module is small |
| Operations | `routes/health.py`, `lib/`, `backup.yml` | Health probe and dumps exist; no daily job, switches or restore log | Large: most duties missing |

## Homes

- **Old code:** the `users` table (`db/models.py`), keyed on the Supabase user ID and made on first call by `user_service.ensure_user`. `user_service.delete_user_account` deletes child rows first, by hand, since only `chunk_embeddings.document_id` cascades (migration `0018`). `DELETE /me` erases at once, then deletes the Supabase user. `lib/terms.py` holds one terms version, stored with its date.
- **Matches:** erasure runs in one transaction, and bucket objects go after it commits ([`data-model.md`](../spec/data-model.md), Erasing a home).
- **Differs:** no 7-day undo ([`privacy.md`](../spec/privacy.md), Closing an account). Bucket deletes are best-effort, with no list for the daily job to retry, and spend rows are deleted, not added to nameless totals (Erasing a home).
- **Missing:** trial links and stubs ([`trial.md`](../spec/trial.md), Trial links); the one erasure routine with its moves; copies; idle erasure ([`privacy.md`](../spec/privacy.md), Idle accounts); the sign-up ticks; the "What changed" list; the time zone.
- **Stack:** the Supabase Auth admin API (`supabase_admin.py`). The spec has no sign-in service ([`accounts.md`](../spec/accounts.md), Ways in).

## Sign-in

- **Old code:** `services/auth.py` checks a Supabase JWT against cached JWKS and returns its `sub`. Terms acceptance arrives as JWT metadata. Sign-in itself happens in the browser through Supabase Auth.
- **Matches:** a credential checked on each call, and little else.
- **Differs:** a bearer JWT, not a sign-in cookie the backend issues ([`accounts.md`](../spec/accounts.md), Staying signed in). Supabase sees the browser, against "Supabase never sees the browser" (Ways in).
- **Missing:** the `openid email` OAuth redirect; scrambled 6-digit codes with limits per email and per network address; Turnstile; the region check; "One more thing"; the learner cap, let-in list and misuse block ([`accounts.md`](../spec/accounts.md)); Request access and wrong-link counts ([`trial.md`](../spec/trial.md)).
- **Stack:** `pyjwt` and Supabase Auth.

## Learning

- **Old code:** `routes/sessions.py`, `routes/chat.py` (the SSE turn), `routes/profile.py` and `profile_service.py` (the `topic_profile_json` blob), `topic_suggest_service.py` (a topic card), `summary_service.py`, `prompt_state.py`, and the `users` preference columns.
- **Matches:** resumable sessions with a name and history; a row lock on profile writes; untrusted text fenced before the prompt ([`ai-layer.md`](../spec/ai-layer.md), Text that is never an instruction).
- **Differs:**
  - A session is one topic that ends and reopens, against topics queued, paused and replaced inside one session ([`learning-loop.md`](../spec/learning-loop.md), Topics and learning objectives).
  - The profile holds knowledge levels, `confirmed_gaps` and `mastered_concepts`, against 3 to 5 objectives with five statuses and a trouble mark ([`teaching.md`](../spec/teaching.md), Objective statuses and readiness).
  - The model asserts mastery through `update_topic_profile`. In the spec, Crux applies the pass rule ([`README.md`](../spec/README.md), Crux decides, the model does not).
  - The model writes an end summary and a rolling summary past the last 20 messages. The spec's note is built from records, and "No AI writes it" ([`sessions.md`](../spec/sessions.md), What the tutor re-reads).
  - Preferences are fixed enums, including `feedback_pref: direct_answers`, against stated, free-form preferences ([`teaching.md`](../spec/teaching.md), Preferences) and "Crux gives no bare answers" ([`learning-loop.md`](../spec/learning-loop.md), A single problem).
  - `GET /sessions/lookup` matches a topic name exactly, and the library uses `LIKE`. The spec's lookup is full-text search over the conversation, written by the tutor ([`sessions.md`](../spec/sessions.md), How it searches).
- **Missing:** narrowing state, the diagnostic by claim, the never-ready menu, the after-mastery menu, dropped objectives and their offer, passed work across sessions, the 7-day refresh, waiting messages and their claims ([`hosting.md`](../spec/hosting.md), Background answers), a per-turn idempotency key ([`ai-layer.md`](../spec/ai-layer.md), What the tutor reports), and deleting a session, which has no route ([`sessions.md`](../spec/sessions.md), Deleting a session).
- **Stack:** FastAPI SSE, SQLAlchemy, JSON blobs in `Text` columns.

## Mastery check

- **Old code:** `check_service.py` runs 1 to 3 sets of 1 to 5 multiple-choice items from the `ask_check_questions` tool. The tool call carries each item's `correct_index`, and the server grades the tap against it. `learning_event_service.py` writes each answer to `learning_events`. The same sets serve a level diagnostic.
- **Matches:** check state held by the server under a row lock, with idempotent grading.
- **Differs:** "No multiple choice" ([`mastery-check.md`](../spec/mastery-check.md), Problems). The model that writes an item also sets its answer, against a checked model answer and a separate marker that sees only the problem, the model answer and the reply (Model answers, Marking). A wrong answer demotes a mastered concept, against "Mastery does not fade in v1" ([`sessions.md`](../spec/sessions.md), Kept between visits).
- **Missing:** the offer and split, counts by complexity, the maths library ([`ai-layer.md`](../spec/ai-layer.md), The maths library), slip and unsure with the end step, disputes, half-done checks, swaps, photo answers, pauses, and re-marks ([`live-faults.md`](../spec/live-faults.md), Re-marks after a marking fault).
- **Stack:** no SymPy.

## Files

- **Old code:** `routes/upload.py` takes `.pdf`, `.pptx`, `.txt` and `.md` up to 25 MB through the backend, checks magic bytes and a 400-page ceiling, and deduplicates by SHA-256. `worker.py` claims `documents` rows with `FOR UPDATE SKIP LOCKED` and resets stuck ones. `ingestion_service.py` extracts text with `pypdf` and `python-pptx`, chunks it and embeds it into `chunk_embeddings`. `object_store.py` writes to local disk or Cloudflare R2.
- **Matches:** a job state per file close to "Reading…" with retries ([`files.md`](../spec/files.md), Storing and reading a file); another learner's file gives "not found".
- **Differs:** uploads pass through the backend, not straight to the bucket by one-time link ([`hosting.md`](../spec/hosting.md), Cloud Run). The tutor gets retrieved chunks, not each file's outline and its topic slice of whole pages ([`files.md`](../spec/files.md), Pages sent to the tutor). Limits are 25 MB and 400 pages, against 50 MB and 100 (Types and limits). Ingestion runs in a thread in the web process, not on the tasks service.
- **Missing:** images, `.docx`, speaker notes, Gotenberg conversion, the outline read, added page ranges, the nothing-learnable, unreadable and harmful outcomes with the hold, the 200 MB allowance and 20 GB store, and erasing a file after its last failed try.
- **Stack:** `pypdf`, `python-pptx`, `tiktoken`, `pgvector`, `boto3` for R2, against Cloud Storage in Singapore.

## Tutor AI

- **Old code:** `services/llm.py` is one adapter for every model call: it gates spend, retries before the first chunk only, settles each attempt's cost, and swaps in a stub for tests. `agent/tutor.py` runs the streamed tool loop, `agent/prompts.py` builds the prompt, and `agent/tools.py` defines `update_topic_profile`, `retrieve_chunks`, `ask_check_questions` and `suggest_topics`.
- **Matches:** one module for every call, and no retry once streaming starts ([`ai-layer.md`](../spec/ai-layer.md), Route and projects, When a call fails). The stub keeps ordinary tests off the network.
- **Differs:**
  - LiteLLM with `GEMINI_API_KEY`, against the GenAI SDK on Agent Platform with no stored key (Signing in to Google).
  - OpenAI-style messages, against Crux's own format with thought blocks kept.
  - One model for every job, default `gemini-3.8-flash`, and teaching sets no thinking level, against 3.5 Flash-Lite with the level set on every call (Models by job).
  - Retries cover 429, 503, 500 and connection errors at 0.5 s and 1 s with no jitter, against 429 and 503 with jitter (When a call fails).
  - The adapter writes the spend ledger itself. The spec's Tutor AI owns no learner items and calls no module ([`data-model.md`](../spec/data-model.md), Modules).
- **Missing:** the spec's tools (a problem's result, the age question, a page request, a lookup, tagged related topics, a decline); filters set to `OFF`; reading block results; the "busy" line; the cache-friendly prompt order; the LearnLM-based instruction ([`teaching.md`](../spec/teaching.md)); the distress check's call.
- **Stack:** `litellm`, against the Google GenAI SDK.

## Spending

- **Old code:** `cost_meter.py` prices each call at list price from its token counts, cached and thinking included, from `MODEL_RATES` for both pinned models with the 2027 rate change. It upserts `daily_cost_ledger` (per user, per UTC day), reserves a per-turn amount, and enforces soft and hard caps per user and an optional global daily cap. `rate_limit.py` counts 50 messages a day, `velocity_limit.py` is a per-minute limit in memory, and `llm_call_log` keeps each call's cost.
- **Matches:** money counted at list price from each reply's tokens ([`spending.md`](../spec/spending.md), What is counted); an all-user ceiling, though optional.
- **Differs:**
  - UTC days, against the owner's time zone ([`README.md`](../spec/README.md), Money).
  - USD 2 and 3 a day per user, against 2 sittings' worth a day and 4 a week ([`spending.md`](../spec/spending.md), Each learner's tutoring limit).
  - The hard cap refuses before the call, while the spec lets the filling reply finish (The reply that fills the bar).
  - `GET /usage/summary` shows money, against "A learner never sees money" (What is counted).
  - `llm_call_log` keeps per-user cost with no end, against current day and week only ([`privacy.md`](../spec/privacy.md), How long things stay).
- **Missing:** the month's budget and check order, guest caps, the owner's share, the distress pot, stop records, turned-away counts, started checks running past limits, and the daily bill comparison.
- **Stack:** Postgres upserts. The spec's burst guard runs at Cloudflare's edge ([`hosting.md`](../spec/hosting.md), Logs).

## Safety

- **Old code:** none. The prompt has no harm line, crisis line or age rule.
- **Missing:** all of [`misuse.md`](../spec/misuse.md) (declines, flags, closures, seals, locks, the reported hold) and the outcomes in [`age.md`](../spec/age.md).

## Feedback

- **Old code:** none. `profile_insights.py` is a learner dashboard, not owner counts.
- **Missing:** all of [`feedback.md`](../spec/feedback.md): the page and its limits, quote and share ticks, path counts and marks, the window, arrivals, and the dated under-18 count.

## Email

- **Old code:** none, and no sender library is a dependency.
- **Missing:** the queue with its three shares, sender counts, and acceptance times that start notice periods ([`operations.md`](../spec/operations.md), Email sending). The spec uses Resend.

## Operations

- **Old code:** `routes/health.py` (`/health`, and `/ready` with a bounded query); `lib/request_id.py`, `error_handlers.py`, `body_limit.py`, `logging_config.py`; `scripts/backup.py` with `backup.yml`, a nightly `pg_dump` to R2 from GitHub Actions.
- **Matches:** an endpoint that runs one tiny query and answers "ok" ([`operations.md`](../spec/operations.md), The outside check); request numbers in logs; a daily dump.
- **Differs:** dumps go to R2 from GitHub, against a Cloud Storage bucket from the daily job under a read-only role ([`hosting.md`](../spec/hosting.md), Backups). `uvicorn.access` still logs, and its default format holds the client address and full path. That likely breaks "No network address or request header is logged" ([`README.md`](../spec/README.md), Where data lives) and route-pattern logging ([`hosting.md`](../spec/hosting.md), Logs).
- **Missing:** the daily job ([`operations.md`](../spec/operations.md), The daily job), the switches ([`live-faults.md`](../spec/live-faults.md), What each switch does), the restore log ([`hosting.md`](../spec/hosting.md), The restore log), the 26-hour check, `/api/client-error`, stripping learner text from errors, pushes, the daily email, and the billing export read.
- **Stack:** GitHub Actions cron, against Cloud Scheduler, Cloud Tasks and the tasks service.

## Old code with no module

| Old code | Job | Spec ruling |
|---|---|---|
| `pgvector_store.py`, `retrieval_service.py`, `lib/keyword_index.py`, `lib/citations.py`, `chunk_embeddings` | Embedding search over file chunks | Replaced by outlines and page slices ([`files.md`](../spec/files.md), Pages sent to the tutor). Vector search for the lookup is looked at only later ([`sessions.md`](../spec/sessions.md), How it searches) |
| `review_queue_service.py`, `routes/review.py` | Spaced review | Retesting later is out of scope, ruled out in [#664](https://github.com/calmxz/Crux/issues/664) |
| `export_service.py`, `GET /me/export` | Data download | "Download my data" is out of scope, ruled out in [#677](https://github.com/calmxz/Crux/issues/677) |
| End, reopen, `pinned` | Ending and pinning sessions | No spec home. Archiving was ruled out in [#671](https://github.com/calmxz/Crux/issues/671) |
| `profile_insights.py` | Learner dashboard | No ruling. "Nothing the tutor infers about the learner ... is stored" ([`teaching.md`](../spec/teaching.md), Preferences) |
| `routes/usage.py`, `usage_service.py` | Spend shown to the learner | Against "A learner never sees money" ([`spending.md`](../spec/spending.md)) |
| `display_name`, `onboarding_complete` | Name and onboarding | Against "No name is asked or kept" ([`accounts.md`](../spec/accounts.md)) |
| `lib/etag.py` | ETags on hot GETs | No ruling |
| `scripts/eval_subtopic_levels.py` and similar | Live-model evaluation | No ruling; see [`ai-tests.md`](../spec/ai-tests.md) |

## Shared ground

**The schema against the homes.** The old schema has 9 tables, and the spec lists about 60 stored items ([`data-model.md`](../spec/data-model.md), Stored items). Learner rows hang off `users.id`, with no trial link as a second kind of home. Only one link deletes with its parent, while the spec requires it on every learner table, with an erasure test for each item that outlives a home (Erasing a home). Much state sits in JSON blobs (`topic_profile_json`, `pending_check_json`, `current_check_json`), while the spec gives each item one owning module (Modules). The 31 Alembic migrations form one chain, and later ones use `IF NOT EXISTS` and `CONCURRENTLY`, close to "add first, remove in a later release" ([`hosting.md`](../spec/hosting.md), Releases).

**Row-level security.** None: no policy in any migration. The backend connects as one role and sets no home per transaction, and isolation is a `user_id` filter in each query. The spec requires row-level security on every learner table, a role without the bypass, and named read rules ([`hosting.md`](../spec/hosting.md), The database).

**Model calls.** Old: the tutor stream, two summaries, and embeddings. Spec: teaching, the check's calls, the outline read, the distress check, and test grading ([`ai-layer.md`](../spec/ai-layer.md), Models by job). Only teaching is in both.

**The test suite.** 140 test files, about 33,400 lines with helpers. They run on in-memory SQLite, and Postgres-only tests skip unless CI's `pgvector/pgvector:pg17` service is set. `pyproject.toml` enforces 75% coverage. The spec uses a throwaway database from the Supabase CLI's local stack, with no coverage target ([`hosting.md`](../spec/hosting.md), Environments; [`quality-bar.md`](../spec/quality-bar.md), Ordinary tests). By file name, about 57 test plumbing (config, auth, adapter, ledger, middleware, worker), and the rest the old domain model.

**The build and CI.** `ci.yml` runs `ruff`, `basedpyright`, the OpenAPI validator, a contracts drift check, migrations and `pytest`, plus gitleaks, `uv audit`, semgrep, hadolint and trivy. CodeQL and Dependabot also run. The spec names push protection, Betterleaks and osv-scanner ([`quality-bar.md`](../spec/quality-bar.md), Security). No deploy workflow exists. Deploy files target Render, Vercel and Docker Compose, against Cloudflare, Cloud Run and Cloud Storage with staging first ([`hosting.md`](../spec/hosting.md), Releases).

**Work outside a request.** The ingestion thread and the post-reply rolling summary break "No work runs outside a request" ([`hosting.md`](../spec/hosting.md), Cloud Run). The worker's claim with recovery is shaped like the spec's expiring claims on waiting messages.

## Could not determine

- **Access-log content:** whether the deployed `uvicorn` logged client addresses depends on its run flags and proxy.
- **How much of the old prompt survives:** `agent/prompts.py` was not judged line by line against the teaching rules. That needs the AI tests in [`ai-tests.md`](../spec/ai-tests.md).
- **Old tests per module:** sorted by file name, not read one by one.
