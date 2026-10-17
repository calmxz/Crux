# Reference

Technical lookup: how things work, gotchas, conventions. Durable "why" (decisions,
tradeoffs) belongs in `docs/decisions.md` instead.

## Backend

### Alembic migrations: live-Postgres safety checklist (C-12)

`backend/db/alembic/env.py` runs every migration inside one transaction, and the
live database is Supabase-managed Postgres serving traffic during `alembic upgrade
head`. Every new file under `backend/db/alembic/versions/` must follow these
patterns (the `migration-reviewer` agent enforces them before commit):

- **Revision ids are at most 32 characters.** `alembic_version.version_num` is
  `varchar(32)`; a longer id passes locally on sqlite and fails CI on Postgres.
- **Index builds on populated or hot tables run CONCURRENTLY**, which cannot run
  inside a transaction: wrap them in `with op.get_context().autocommit_block():`
  and use `op.create_index(..., postgresql_concurrently=True, if_not_exists=True)`
  or `op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ...")`.
- **Drop an INVALID namesake first.** A CONCURRENTLY build that fails part-way
  leaves an invalid index with the same name; `IF NOT EXISTS` matches on name only
  and would no-op, stamping the revision while the planner ignores the index. Probe
  `pg_index.indisvalid` and `DROP INDEX CONCURRENTLY IF EXISTS` when false (see
  `0025_learning_events_created_at.py` for the shape).
- **CHECK constraints on populated tables are two-step:** `ADD CONSTRAINT ... NOT
  VALID`, then `VALIDATE CONSTRAINT` (VALIDATE takes only SHARE UPDATE EXCLUSIVE, so
  reads and writes continue).
- **Unique constraints on populated tables** are built as a CONCURRENT unique index
  and then adopted with `ADD CONSTRAINT ... UNIQUE USING INDEX` (see
  `0023_worker_queue.py`).
- **Any migration touching a hot table** (`sessions`, `chat_messages`,
  `chunk_embeddings`, `documents`) opens with `op.execute("SET lock_timeout =
  '5s'")` so it fails fast instead of queueing behind a long query and then blocking
  everything behind itself.
- **No table rewrites in-transaction:** adding a column is nullable with no default
  (or a constant default, which Postgres 11+ stores in the catalog); type changes
  and volatile defaults rewrite the table under an exclusive lock.
- **Column drops or renames** must not remove anything deployed backend code still
  reads (`backend/db/models.py` and services); ship the code change first.
- **pgvector columns and indexes** keep dimension and distance operator consistent
  with `backend/services/pgvector_store.py`.
- **Linear chain:** `down_revision` points at the current head;
  `backend/tests/test_migration_chain.py` fails on branching heads.
- **Run against the direct connection (port 5432), not the transaction pooler
  (6543)** when a migration needs session-level state (`SET`, CONCURRENTLY,
  advisory locks). `DATABASE_URL` points at the pooler.

### Retrieval transaction tuning (F-10)

`pgvector_store.query_chunks` post-filters the HNSW scan on `documents.status =
'ready'`, so a scan that returns exactly k candidates can yield fewer than k
usable rows. Before the search, on Postgres only, it issues `SET LOCAL
hnsw.ef_search = <HNSW_EF_SEARCH>` (default 100, pgvector default 40) and `SET
LOCAL hnsw.iterative_scan = strict_order` (pgvector 0.8+): the scan re-enters the
graph until k rows survive the filter, preserving exact distance order
(`relaxed_order` would return rows slightly out of order and nothing downstream
tolerates that). Both are transaction-scoped, so they run immediately before the
select in the same transaction; because SET cannot take bind parameters, the
`ef_search` value goes through `set_config(name, value, is_local=true)` (bind-safe
SET LOCAL) after int() validation. Semgrep's `avoid-sqlalchemy-text` rule blocks any
f-string inside `text()`, so use `set_config` for every value-bearing GUC. The pair runs inside a Core-level
SAVEPOINT so an older pgvector that rejects the GUC does not abort the search.

`chunk_embeddings.doc_ready` was deliberately NOT denormalised: the join to
`documents` is needed anyway for `filename`, and the status predicate is a
PK-joined filter per candidate. If the table ever outgrows the HNSW build memory
budget, the next step is LIST-partitioning `chunk_embeddings` by a `session_id`
hash bucket, not a status column.

### Chat cost gate is a reservation, not a read (B-05)

`_prepare_turn_guards` no longer SELECTs today's spend and compares. It calls
`cost_meter.reserve_cost(db, user_id, LLM_TURN_RESERVE_USD)` (default 0.02): an
`INSERT .. ON CONFLICT DO UPDATE .. RETURNING` that adds the reserve and returns
the PRE-increment total. Concurrent turns serialise on the ledger row, so each
sees a distinct total and only those below the hard cap are admitted. The turn
releases the reserve with `adjust_cost(db, user_id, -reserve)` on every exit path
of `chat_stream` (normal, cancel, exception); a rate-limit reject after
`ensure_user` has committed releases explicitly, and a failure between the guards
and the stream start releases in `_prepare_turn`'s `except BaseException` arm.
Consequences: the usage ledger reads `reserve` high for the duration of a turn,
and a process crash mid-turn leaves the reserve on the ledger until UTC midnight.

### LLM adapter (#411, #412, #413)

`backend/services/llm.py` is the one place that calls the model; only it and
`cost_meter`'s pricing helpers import `litellm` (the offline eval script
excepted). `llm.get()` returns the shell around the active provider:
`complete`, `stream`, `embed`, `aembed`, each taking a
`Meter(user_id, session_id, purpose)`. The shell gates on
`cost_meter.assert_within_caps` and settles the ledger row plus the
`LlmCallLog` row in its own short session, so spend survives any caller
rollback. Settlement never raises; a failure is an error-level log line
carrying user, session, purpose, cost and usage. `CallRefused` (base of
`CostCapExceeded` and `LlmUnavailable`) lives in `lib/llm_errors.py` so
`cost_meter` can subclass it without importing the adapter. Catch
`CallRefused` and report its `code`; `cap` is set only on a cost cap.

Stub mode: `llm.get()` is the only reader of `settings.llm_stub_enabled`;
when it is on, `get()` returns `StubProvider` even over a test's installed
provider. Never branch on the flag elsewhere: handle `LlmUnavailable`
instead. The stub streams the deterministic `[STUB:...]` echo
(`agent/_stub.py`, which finds the prior summary by
`prompts.LAST_SESSION_SUMMARY_LABEL`) with no tool calls; `complete`,
`embed` and `aembed` raise `LlmUnavailable` (code `llm_unavailable`). It
never spends, so the shell skips the gate for it. Callers fall back as
without a model: mechanical session and rolling summaries, no retrieval
escalation or prefetch, and stub-mode ingestion fails the document.

Caller rule: never hold an uncommitted ledger write (`record_cost`,
`reserve_cost`, `adjust_cost`) in your session across an adapter call. The
settlement upserts the same row; on Postgres it waits at most
`SETTLE_LOCK_TIMEOUT` (5 s), then defers the ledger write (`_defer_ledger`):

- The LlmCallLog row is committed on its own (it never waits on the ledger
  row), except after a pool timeout, when the retry writes it instead of
  queueing a second checkout on the request path.
- `llm settlement deferred` logs at error level with the reconciliation
  fields (`call_logged`, `date_utc`). It is the record that survives if the
  retry never runs, e.g. a restart within the delay.
- One retry runs on a daemon thread after `SETTLE_RETRY_DELAY_S`, waits up to
  `SETTLE_RETRY_LOCK_TIMEOUT` (30 s), and books to the day the call was
  settled, not the day it runs. It logs `llm deferred settlement landed`
  (info) or `llm settlement failed` (error).
- At most `SETTLE_RETRY_MAX_IN_FLIGHT` (2) retries wait per process, since
  each holds a pooled connection; past that the spend is logged as
  `llm settlement failed: retry capacity full`.
- A connection lost mid-COMMIT can leave the first write committed; the
  retry then counts it twice, the accepted (overcounting) direction.

Reconcile from the logs: a deferral with no matching `landed` line is spend
missing from the ledger. Until a deferred write lands the cap undercounts, so
any ledger write still commits before the next slow step, not just before
adapter calls. The tutor and the `retrieve` tool write no ledger rows
themselves; the chat route's B-05 reservation is the one caller-side write,
published by its admission commit. The adapter's gate and settlement each
take their own pooled connection, so callers commit before the call (the
tutor before each stream, the retrieve tool before its embed) instead of
holding an idle one.

Streams: `async with llm.get().stream(messages, meter=..., tools=...,
tool_choice=..., temperature=..., timeout=...) as s:` gates on enter (a
refusal raises a `CallRefused` before the block runs), then
`async for ev in s` yields `TextDelta`. `s.text` and `s.tool_calls`
(`ToolCall(id, name, arguments)`, arguments the raw JSON string) are complete
once iteration ends; `s.cost` is set when the block exits and stays readable
after a cancel. The exit settles once, synchronously, before any await: the
provider's price on a normal end (token math if pricing fails), an estimate
of the prompt plus the output received (text and tool-call arguments) on
cancel or on the caller's generator closing, and on a provider error the
estimate only if a chunk arrived or it was a `Timeout` ($0 otherwise).
Retry (429, 503, 500, connection) happens only while no chunk has arrived;
a retried attempt costs nothing and its stream, if it opened, is closed
(whether Gemini bills such an attempt is open, #561). The tutor keeps the
stream it is inside in `inflight` until its iteration finishes, so its
cancel event reports what the cut-short call settled, or $0 for a cancel
during tool dispatch or while a finished stream closes.

Tests: the `fake_llm` fixture (conftest) installs `FakeLlmProvider` under the
real shell; script it with `replies` (str or exception per `complete`
attempt), `streams` (per `stream` open: an exception raised on open, or a
list of steps -- str text, `tool_call(name, args, id=)`, an exception raised
there, `BLOCK` to park until cancelled), `embed_errors`, `vector`, `cost`,
`timeout_cost` and `partial_cost` (a cut-short stream). `stream_calls`
copies each sent message, so later pruning cannot rewrite a capture.
`fake_llm` pins stub mode off (the test key `"test"` turns it on); set
`settings.llm_stub = True` after it to get the stub. litellm's chunk parsing is the
provider's and is tested against litellm-shaped chunks in `test_llm.py`.
`db_session` binds `llm.session_factory` (and the chat route's `SessionLocal`, for the
rolling-summary task) to the sqlite test engine. On sqlite that engine
is one shared connection (`StaticPool`), so the adapter's commit also commits
the caller's pending writes, and so does the rolling-summary task's (which on a
due summary also makes a `fake_llm` call); isolation is only provable on
Postgres. A Postgres test must bind `llm.session_factory` to its own
sessionmaker (see `adapter_on_postgres` in `tests/test_llm_characterisation_pg.py`),
and one that streams a chat turn stubs `summary_service.update_rolling_summary`
(or the guard below fails it). An autouse
conftest fixture runs the deferred retry inline (it replaces `llm._schedule`)
and gives each test fresh retry slots; a test that needs to observe the
deferred state captures the scheduled call instead (`test_llm.py`).

### Stream cleanup must be shielded (#421)

Starlette cancels a streaming response's task on client disconnect (and on
shutdown), and anyio's cancel is level-triggered: once the scope is cancelled,
every later `await` in cleanup raises `CancelledError` at once. An unshielded
`await task` also forwards the cancel into the producer, killing the tutor's
cancel arm before it persists the partial reply and its cost. So any cleanup that
must finish (draining the producer, releasing the B-05 reserve) runs inside
`anyio.CancelScope(shield=True)`: `chat_stream`'s finally, the check follow-up
pump in `routes/sessions.py`, and `_prepare_turn`'s release-on-failure. Drain
before release, in one shield, because both touch the same `Session`.

### Proving a row lock in a test (#418)

SQLite ignores `with_for_update`, so a lock is only provable on Postgres
(`backend/tests/test_check_locks_pg.py`, run via `backend/scripts/pg_tests.sh`).
The pattern: the test holds `SELECT ... FOR UPDATE` on the session row on a
connection of its own, fires real routes on worker threads (one `TestClient`
each, a fresh `Session` per request), and polls until the expected number of
request backends show `wait_event_type = 'Lock'` in `pg_stat_activity` before
committing. The test's engine carries an `application_name`, so the poll
counts only this test's backends that are waiting on a lock. The holder never
waits, but any other test-side session that blocks (such as a service call
fired on a worker thread) counts too. Reaching the waiter count proves each request blocked; a live
thread does not, and sleeps prove nothing.

Activity stats are snapshotted once per transaction, and the holder's stays
open, so each poll must run `SELECT pg_stat_clear_snapshot()` first or the
waiters never appear.

### Check module owns its transaction (#420)

`services/check_service.py` is the only code that reads or writes
`pending_check_json`, `current_check_json`, `quiz_cooldown_json` and
`ChatMessage.check_batch_json`; everything else goes through its row reads.
Its actions commit themselves, on early exits and `CheckError` too, and
never release the lock by rollback. An unexpected exception leaves the
transaction to the caller; for `register`, `agent.tools.dispatch` rolls it
back (#569). `abandon_in_caller_transaction` is the exception: it
joins the session end's single commit. So a caller never commits after an
action, and must commit after abandon.

Ending a session takes two transactions. `_claim_end` commits `ended_at`
first. Abandon runs in the second, after the multi-second summary LLM call.
An `ended_at` check made before taking the row lock can pass, and the Set can
still be open, in the window between the two. That is why every Check action,
`register` included, rechecks `ended_at` under the lock.

### Prompt state (#395)

The tutor's dynamic context is rendered from a `PromptState`
(`services/prompt_state.py`), never a dict. Build it in two steps:
`gather_session_inputs(db, row, ...)` reads the session's inputs and
`assemble(session_inputs, TurnInputs(...))` adds the turn's. Every
`PromptState` field is required. Pass `learner_prefs`, `ingestion_status` or
`gap_accuracy` when the caller already has them (chat loads the first two in
its guard SELECTs) or wants them blank; the default `NOT_LOADED` makes gather
query for them. gather reads columns off the
row it is given, so a detached row costs no refresh SELECT. To override one
value, use `dataclasses.replace` on either dataclass (the check follow-up
does this).

The gap-accuracy read is best-effort, and on Postgres a swallowed SQL error
still aborts the request's transaction. So the read runs in a Core-level
SAVEPOINT (`db.connection().begin_nested()`), which rolls back only itself;
`Session.begin_nested()` would flush pending ORM state first (#565). Any
best-effort read on the request session needs the same: wrap it in
`services.savepoint.core_savepoint(db)` and catch outside it (the chat
pre-flight's retrieval reads do, #567). Never put a commit inside one, such
as the embed's connection-releasing commit.

`tests/test_prompt_golden.py` pins the full system prompt of three chat turns
and two check follow-ups (`/check/complete`, `/check/stop`), byte for byte,
against
`tests/fixtures/prompt_golden/`. A deliberate prompt change rewrites them
with `UPDATE_PROMPT_GOLDEN=1`; review the fixture diff as the change. Renderer
tests build state with `tests/prompt_state_factory.make_prompt_state`, whose
defaults are the old renderer fallbacks.

### Liveness vs readiness (G-07)

`/health` and `/healthz` are liveness-only and must keep returning 200 while the
DB is down. `/ready` runs `SELECT 1` on a `READINESS_TIMEOUT_S` budget and returns
503 on failure or timeout; Render's `healthCheckPath` points at it, so a Supabase
outage fails the instance health check. `/ready` is `include_in_schema=False` and
not part of the openapi contract.

### Tool dispatch error surface (G-04)

`agent/tools.dispatch` hands the model a coarse `tool_failed` for unexpected
exceptions; the real exception text is only in the server WARNING log.
`pydantic.ValidationError` is the deliberate exception and passes through: the
model needs the field detail to repair its own call.

Both arms also roll back `ctx.db` (#569): on Postgres a failed statement aborts
the transaction, which would fail the next tool in the batch and the loop's
next commit. Two rules follow for any tool. A write tool commits its own work
before returning, since a later tool's failure rolls back anything left
uncommitted. A tool that swallows its own SQL error (as `retrieve` does,
returning `retrieval_failed`) rolls back itself in that except arm, since
`dispatch` rolls back only on an exception.

### Ingestion error strings (C-11)

`documents.error` is rendered verbatim by the frontend, so it only ever holds a
value from `ingestion_service.INGEST_ERROR_MESSAGES` (or upload.py's fixed
"storage write failed"). The raw exception goes to the log line only.

### CI drift guards

- `backend/tests/test_openapi_status_codes.py` AST-walks `backend/routes/*.py` and
  fails if a handler can raise a non-2xx status code that `docs/api/openapi.yaml`
  does not document under that path+method. It follows same-module helpers one
  level, plus one more for `_`-prefixed helpers; skips `include_in_schema=False`
  routes; never expects 500. Add a new `raise` and add the response block in the
  same commit. It also fails when the yaml documents a path+method with no route.
- Error codes (#464): every `code` the backend sends is listed in the
  `x-error-codes` block of `docs/api/openapi.yaml` and defined once in
  `backend/lib/error_codes.py`. `backend/tests/test_error_codes.py` fails if the
  two differ, or if backend code outside the registry spells a code as a string
  literal (an `ast` guard: a literal under a `"code"` key or `code=` keyword, or
  any literal equal to a registered value). A new code goes into the spec block
  and the registry in the same commit. `frontend/src/lib/errorCodes.js` holds
  only the codes the frontend handles; `errorCodes.test.js` fails if one is not
  in the spec block.
- SSE events (#463): an autouse fixture in `backend/tests/conftest.py` validates
  the `data` of every `StreamEvent` built in the suite against the `x-sse-events`
  block of `docs/api/openapi.yaml` (jsonschema, Draft 2020-12). Every object is
  closed with `additionalProperties: false`, so a new field goes into the block
  in the same commit as its emitter. Test fakes are validated too; a test that
  must build an off-spec event opts out with `@pytest.mark.sse_unchecked("reason")`.
  A clean whole-suite run also fails if any type in the block was never built,
  on-spec, by non-test code, so a new event type needs a test that reaches its
  real emitter. Runs that are narrowed (paths, `-k`, `-m`, `--ignore`, or
  anything that deselects, such as `--lf` or `--sw`), collect-only, or already
  failing skip this check.
- Default engine (#579): no test may connect on `db.database.engine` (a developer's
  real `data/app.db` locally). A `do_connect` hook in `backend/tests/conftest.py`
  refuses every such connection, so the file is never opened, and records it; the
  test that made it fails at teardown, named, even if app code swallowed the
  refusal. Hits outside a test fail the next test, or the run if none follows
  (`tests/test_default_engine_guard.py` pins the hook). App
  code that opens its own session (`SessionLocal()`, `engine.begin()`) needs its
  factory bound to the test engine: `db_session` does this for `llm.session_factory`
  and `routes.chat.SessionLocal`; tests that run the app lifespan stub
  `main.create_tables`.
- `backend/tests/test_deploy_config.py` enforces bidirectional drift between
  `config.Settings`, `.env.example`, and `render.yaml` `envVars`. A new Settings
  field must be documented in `.env.example` (commented default is fine).
- Non-multipart request bodies above `MAX_JSON_BODY_BYTES` (default 64 KiB) are
  rejected with 413 `body_too_large` by `lib/body_limit.BodySizeLimitMiddleware`
  (pure ASGI, registered outermost) before any parsing. Multipart uploads have
  their own gate in `routes/upload.py`.

### Unhandled-error contract (C-14)

`backend/lib/error_handlers.py`. Any exception that escapes a route answers
`500 {"detail": {"code": "internal_error", "message": "Something went wrong.",
"request_id": ...}}`; the exception text never reaches the body. It is a pure
ASGI middleware registered between BodySizeLimit and CORS so the 500 carries
CORS headers (the C-03 trap) and does not buffer SSE. A plain `ValueError`
(exact type only) answers `422 invalid_value` with its message; subclasses
such as pydantic `ValidationError` and `json.JSONDecodeError` fall through to
the 500 because they usually mean corrupt stored data, not bad input.
Route-level `except ValueError` blocks still take precedence.

### Cross-session insights module (G-14)

`services/profile_insights.py` owns `aggregate_for_user` and the weekly
insights; it imports from `services/profile_service.py`, never the reverse
(a test walks the AST to keep it that way).

### Access-token revocation window (A-01)

`backend/services/auth.py` verifies JWT signature, `exp`, `aud` and `iss`
only; there is no revocation primitive. See `docs/decisions.md`, 2026-09-21
Wave 4 entry, for the residual-window tradeoff and the TTL value.

### Cost cap tiers (B-08)

| Tier | Formula | Local/dev default (`backend/config.py`) | Render blueprint (`render.yaml`) |
|---|---|---|---|
| Soft | `LLM_SOFT_CAP_USD` | 2.00 | 0.50 |
| Urgent | `hard_cap * 0.9` (`cost_meter.py:216`) | 2.70 | 0.90 |
| Hard | `LLM_HARD_CAP_USD` | 3.00 | 1.00 |

The Render blueprint values are what `render.yaml` pins for the Render
deploy target: blueprint values, not confirmed deployed. Local dev
(native uvicorn, docker compose) and tests use `backend/config.py` defaults
unless `.env` overrides them.

## Frontend

### `--control-edge` token (D-20)

The resting border of a text control. WCAG 1.4.11 needs 3:1 for the boundary of
a component the user has to find; `--card-edge` is card chrome at 1.50:1 light /
1.19:1 dark on `--card`. `--control-edge` is `#767c86` light (4.20:1 on
`#ffffff`) and `#6e7584` dark (3.32:1 on `#22252b`), declared in all three token
blocks of `frontend/src/assets/base.css`. Use it on inputs and textareas at rest
(the composer shell today); leave card, rail and row chrome and disabled controls
on `--card-edge`. `frontend/src/__tests__/tokenContrast.test.js` asserts >= 3:1
in every block.

### Reference polling (F-12 / E-07)

`composables/useReferencePoll.js` is the only ingestion poller. `SessionView`
owns one instance per session id and passes `status` / `documents` / `failed`
into `ReferenceStatusBanner.vue` (now presentational, emits `refresh`).
Backoff `POLL_DELAYS_MS = [2000, 4000, 8000, 15000]`, capped at 15 s while any
document is pending, reset on success. A thrown poll with no status, status 0 or
a 5xx (including the first, when `status` is still null) sets `failed`, keeps the
last-known list so delete buttons stay reachable, and keeps retrying on the same
schedule. A **4xx** is terminal instead: an unknown or foreign session id 404s
forever, so the loop stops, `failed` stays false and `status` stays null (banner
hidden) and any pending watcher settles `{ unavailable: true }`. The upload
chip is driven by `watch(documentId, filename)` outcomes; `WATCH_CEILING_MS =
90000` and `schedule()` clamps the next delay to the earliest watcher deadline
so "still processing" fires at exactly 90 s. Polls use `{ fresh: true, silent:
true }`.

### apiClient GET retry and cache (F-18, client side -- server half below)

`request()` retries **GET only**: 3 attempts, 300 ms / 900 ms with +/-20%
jitter, on `TypeError` (network failure) and 502/503/504. A `TimeoutError` is
deliberately **not** retried: each attempt carries its own 30 s
`AbortSignal.timeout`, so retrying a hung server would take ~91 s to surface.
`reportApiError` fires once after the last failure; the 401 refresh-once path
is separate and unchanged. `chatStreamService` uses raw `fetch` and is not
retried.

GET cache: 5 s TTL, in-memory `Map`, key = url **+ access token** (a token
mismatch is a miss; `_onAuthExpired()` clears the map). `{ fresh: true }`
bypasses the read but still writes. Failures and non-GETs never populate it.
Invalidation after any non-GET settles (success or failure): every cached GET
under the write's **resource root** (first path segment, query stripped) is
dropped, so `POST /sessions/abc/end` drops `GET /sessions/abc` and also the
sibling lists `GET /sessions/library` and `GET /sessions?..`, which the
bidirectional prefix rule alone would have missed. Roots whose GETs read each
other's data are linked in `LINKED_ROOTS`. A write under `/sessions` or
`/profile` drops both of those roots and `/review`. Every profile derives from
sessions, `GET /sessions/:id` embeds the topic profile, and the review queue
joins both. Without the link, a new session was missing from the combined
profile for up to 5 s (#518). A new root derived from another one must be added there.
A write under `/sessions` still leaves `/me` or `/documents` entries alone.
Coarse on purpose: a 5 s cache
gains nothing from finer rules and a stale list is a visible bug.
Two writers bypass `request()` and call the exported `invalidateGetCache(path)`
themselves once they settle, success or failure: `chatStreamService`
(`streamChat`, `streamCheckComplete`) and `uploadApi.uploadDocument`, both on
`/sessions/:id`. Every invalidation also bumps an epoch; a GET that was already
in flight when the epoch moved does not write its (possibly pre-write) body
into the cache. `getSession` and `getSessionProfile` always pass `fresh: true`
(server-side tutor writes are invisible to path invalidation, the session body
carries ingestion and pending-check state, and the profile body carries the
`If-Match` ETag).
`_resetApiCache()` is the test hook; call it in `beforeEach` of any test that
mocks `fetch` for GETs.

Cache entries also keep the response `ETag` (`{ at, value, token, etag }`). A
read against an expired entry -- or any read with `fresh: true`, even inside
the TTL -- under the same token sends `If-None-Match` when an `etag` was
stored, instead of dropping the entry outright. A `304` response returns the
cached body and refreshes the TTL, unless an invalidation landed while the
revalidation was in flight, in which case the cached body is still returned
but the TTL is left alone (the entry was already dropped by the
invalidation). Writes still drop the entry on any non-GET, so the next GET is
always unconditional. Entries under a different token are never used for
conditional requests -- they are dropped on sight, same as before.

### HTTP ETag on hot GETs (F-18, backend half, #331)

`backend/lib/etag.py` -- `ETagMiddleware`, pure ASGI (never
`BaseHTTPMiddleware`, which would buffer SSE). It acts only on **GET/HEAD**
under four segment-wise prefixes: `/api/sessions`, `/api/profile`,
`/api/review/queue`, `/api/usage/summary` (`/api/sessionsx` does not match).
Everything else -- every POST, including the two SSE routes under
`/api/sessions` -- gets `send` handed through untouched.
A matching 200 is buffered, hashed, and stamped `ETag: "<sha256 hex>"` (strong,
quoted) plus `cache-control: no-cache`, which means "revalidate", not "do not
store": without it a body carrying an ETag and no freshness headers is reused
heuristically and the client never sends the conditional request. A route that
set its own `Cache-Control` keeps it. `If-None-Match` is parsed per RFC 9110:
repeated headers and comma-separated lists both work, a `W/` prefix is stripped
before comparing, `*` matches anything. On a hit the reply is **304** with the
same `etag`/`cache-control` and no `content-length`/`content-type`; non-200
responses (404s included) are forwarded untagged.
CORS: `If-None-Match` is in `allow_headers` and `ETag` in `expose_headers` --
neither is safelisted, so the cross-origin dev setup (5173 -> 8000) would
otherwise never see the header.
Registered between `BodySizeLimitMiddleware` and `UnhandledErrorMiddleware`, so
it sits **inside** both `UnhandledErrorMiddleware` (a bug here answers a coded
500) and `CORSMiddleware` (a 304 carries `access-control-allow-origin`).
Not the same thing as the `etag` field in the **body** of `GET
/api/profile/{id}` (`profile_service.profile_etag`): that is an `If-Match`
optimistic-concurrency token for profile writes.

### Auth error copy (E-13)

`lib/authErrors.js` maps Supabase `AuthError` to owned copy: `code` first
(`invalid_credentials`, `email_not_confirmed`, `user_already_exists`,
`email_exists`, `weak_password`, `same_password`, `otp_expired`,
`over_email_send_rate_limit`, `over_request_rate_limit`,
`email_address_invalid`, `session_expired`), then `status` (429 throttled, >=500
generic), then the caller's fallback. SDK prose is never rendered.
`isEmailNotConfirmed(e)` drives the resend-confirmation affordance. Do not route
auth errors through `friendlyError()`: it keys on HTTP status and would clobber
this copy.

### Streaming markdown render cache (F-15)

`renderMarkdownIncremental(text, cache)` in `lib/markdownRenderer.js` keeps the
rendered HTML of a stable head and renders only the tail. A head is only
reusable when its last block close is safe; `UNSAFE_CLOSE` =
`bullet_list_close`, `ordered_list_close`, `code_block`, because markdown-it
would re-open a list or indented code across the cut. A trailing **unclosed**
`fence` is unsafe too: markdown-it renders it as a complete `<pre>`, so the head
would look closed while the tail got parsed as markdown. `scanBlocks()` applies
the CommonMark fence rule (a run of 3+ backticks or tildes closes only on the
same character, at least as long, nothing but whitespace after), so an inner
` ``` ` line inside a ` ```` ` or `~~~` fence no longer flips the scanner out of
the block and turns the next blank line into a cut candidate inside code.
`MarkdownContent.vue`
holds one `createRenderCache()` per instance and resets it when `streaming`
flips false (final full render) or the lazy asset version changes. ~4 kB
streamed in 40-char chunks goes from ~214 k chars through markdown-it to ~15 k.

### Message window (F-16)

`stores/session.js` `MAX_RETAINED_MESSAGES = 200`, enforced in `_appendMessage`
only. Eviction drops from the top until the head carries a server id and sets
`hasMoreMessages = true`; `loadEarlierMessages` uses the oldest retained server
id as its `before` cursor. Manual prepends are not capped.

### Optimistic chat row identity (F-21)

The optimistic user row and locally-cancelled assistant rows carry a
`client_id` (`c-<uuid>`); `message_id` is only ever a server id or the
literal `'pending'`. `MessageList` keys on a real `message_id`, then
`client_id`, then index. Never write a client value into `message_id`:
`_hasServerId` and the `before` pagination cursor read it.

### Reset epoch (#414)

`stores/session.js` `reset()` (sign-out) aborts the live stream first, then
bumps `_resetEpoch`, clears `_inflight` and `_listReplays`, and nulls
`_latestRequestedId`. Any
async action must call `const live = _epochGuard()` before its first `await`
and gate every later state write on `live()`: data writes, `finally` flag
clears, and the error write (`_setError(e, live)`, or
`_setError(e, live, listError)` for the sidebar list, #537). Return or rethrow to the
caller unchanged. Without the gate, a request in flight at sign-out writes the
previous account's data into the next one's store. Streams use the separate
`ABANDONED` sentinel on `_streamSid` instead (`_streamSuperseded()`).
Shared-promise dedupe goes through `_shareInflight`, which deletes an entry
only if it is still the same promise.

### Sidebar session window (#522, #524, #528, #533, #534, #544)

`stores/session.js` `sessions` is a window (40 active + 40 ended), not the
corpus, and a mutation never refetches it. Four exceptions, below: the
#528 and #533 re-lists after a status-change race, the #534 re-list when
the tab becomes visible again, and the #544 re-list after a create made
while the first list has failed.
`listSessions()` replaces
it; actions patch rows in place. `createSession` / `continueTopic` insert the
created session locally via `_addCreated` -> `_insertCreated` (list-item
shape, after the pinned active rows), counting it in `activeTotal` only if
the row was not already there. "Has the window loaded?" is `sessionsLoaded`,
never `sessions.length`: a create makes the window non-empty without loading
it.

A list snapshot can predate a local change, so every window change is
recorded in `_listReplays` and re-applied onto the incoming rows and totals
before the list writes them:
- Create, end, reopen and continueTopic's prior-end are recorded on success,
  only while a list is in flight. A create inserts only if the snapshot lacks
  the row. An end/reopen applies only to a row in the snapshot that is still in
  the prior state, and then moves the totals. A row already in the target state
  was counted by the snapshot. A row outside the snapshot gives no evidence
  either way, so its replay flags the list for a re-list (below).
- Pin and rename are recorded from their optimistic start, because a list that
  started before the write committed can land while it is still pending. A
  failed write drops its entry and also rolls back any landed row it patched,
  unless a later write has already changed that row.
- Settled entries clear when the in-flight list settles, success or failure.
  `reset()` clears them all. A new action that changes window rows locally must
  record a replay, or an in-flight list will revert it.

Re-list (#528): when a list lands and an end/reopen/prior-end replay found no
row, or the same id is in both the active and the ended page (a change
committed between the two parallel page reads), the snapshot's totals may be
off by one. The list still writes its result, drops `listLoading` (when
the no-race path would; only the list and `reset()` write that flag, #532), clears its
settled replays, and runs one more fetch inside the same shared `'list'`
promise, so `_listPending` and replay tracking cover it too. The follow-up's
own race result is ignored (capped at one), its failure is swallowed (the
first result stays, no `error`), and the epoch guard drops it after `reset()`.
Creates and pin/rename never trigger it: their replays are exact. Residual
races it cannot see are listed in `docs/decisions.md` (2026-10-14).

Late reply (#533): end/reopen/continueTopic call `_statusChangeGuard()` when
their request starts (it notes `_listsLanded`, bumped each time a list writes
the window). On the reply, before patching, its judge returns `'move'`,
`'skip'` or `'relist'`. With no list landed since, it is the shared totals
rule. Once a list has landed: the landed window row alone decides when there
is one (the open detail or the caller's row can be a stale separate copy),
even with a later list in flight. Copies all in the target state skip.
Otherwise `_relist()` calls `listSessions()` instead of moving the totals, or,
with a list in flight, the totals move and that list's replay decides (#528).
Observed copies are always patched. `_relist()` runs after
`_trackStatusChange`, or the re-list would record that replay against itself
and re-list again, and it waits out a list whose `_inflight` entry outlives
`_listPending`, so it never joins a finished fetch.

Visibility re-list (#534): `composables/useVisibilityRelist.js`, called by
`Sidebar.vue`, holds one `visibilitychange` listener on `document` for all
mounted sidebars (module-scoped count; added on the first mount, removed on
the last unmount). When the document turns visible and the user is signed in,
it calls the store's `relistIfStale()`. That calls `listSessions()` unless the
window has not loaded this sign-in (`sessionsLoaded`), or a list wrote the
window (`_listLandedAt`, set by every landing) or a throttled re-list was
attempted (`_relistTriedAt`, so offline returns are throttled too) under 30
seconds ago (`_claimRelistSlot`). `reset()` clears both; a negative age from
a clock moved back counts as stale. A list still in flight is joined through
`_inflight`. The event runs as its own task, never in the microtasks between
a list's `finally` and its `_inflight` removal, so it cannot join a finished
fetch.

Failed first list (#544): until a list has loaded this sign-in, a failed one
(the store's `firstListFailed`, `!sessionsLoaded && listError`) is the only
state where the window vouches for nothing, and the only state any surface
reports a list failure in: Home's boot error reads the same computed (#546).
One surface reports it at a time (#549): `SidebarListError` while the
sidebar's body is on screen (`useSidebar().isExpanded`: `expanded`,
`drawer-open`), Home's boot error otherwise (`collapsed`, `drawer-closed`,
where the sidebar renders no list at all). Both say `LIST_FAILED_COPY`
(`lib/errors.js`); a start-attempt error on Home is separate and wins over
the boot error in every mode. The sidebar shows `SidebarListError` (message +
silent Retry) on both tabs, in place of an empty hint, under rows a create
inserted, or above search results, and hides every
total-derived surface (View all links, the Ended tab count) while that list
has failed or a retry of it runs: the totals then count only local creates. A
new surface that renders `activeTotal`, `endedTotal` or an empty state reads
the same gate. `_addCreated` re-lists in this state through `_relist()`,
sharing the #534 throttle via `_claimRelistSlot`. Retry and mount-time lists
are not throttled attempts. After a load, a failed list stays silent and
keeps the window (#534), on Home as in the sidebar, including an account that
loaded with zero sessions.

Ordering matrix. A change to the totals or replay logic is checked against
each row, for a session inside and outside the window. In a store test, seed
the session with `seedSession` (in `sessionStore.test.js`), which puts it in
the window, the open detail and the search results as separate objects, like
the app holds them:

| # | Ordering, relative to an action's request and reply |
|---|---|
| 1 | No list starts or lands between request and reply |
| 2 | A list is in flight at the reply (replay recorded; #528 may re-list) |
| 3 | A list lands between request and reply, none in flight at the reply |
| 4 | A list lands, then a later list is in flight at the reply, and that list succeeds or fails |
| 5 | The reply arrives during a #528 follow-up |
| 6 | `reset()` between the request and the reply, or during a re-list |
| 7 | The reply resumes in the microtasks while a list settles (between its write, its `finally`, and its `_inflight` removal) |

Row 7 has no stable ordering to set up by hand. Release the reply after 0..N
microtasks with `it.each` (the #533 sweep test in `sessionStore.test.js`), and
check the sweep goes red when the guarded branch is removed.

### E2E sign-in against the real backend (#518)

Specs that call the e2e backend sign in with `signIn(page)` from
`frontend/e2e/support/auth.js`. It stubs GoTrue (`auth/v1/settings|token|user`)
and signs in through the real `/login` form, but the access token it returns is
a real RS256 JWT for a fresh random user id. So every test starts on an empty,
not-yet-onboarded account. `node e2e/support/gen-auth-keys.js` writes a throwaway key
pair to `frontend/e2e/.auth/` (gitignored). The e2e job serves only `jwks/`
over `http.server` on 8787 and boots the backend with
`SUPABASE_URL=http://e2e-auth.invalid` and
`SUPABASE_JWKS_URL_OVERRIDE=http://127.0.0.1:8787/jwks.json`. The backend has
no test branch: it verifies through the normal JWKS path, and
`backend/tests/test_auth_served_jwks.py` pins that a foreign key is still a 401.
Gotchas:
- `ISSUER_ORIGIN` in `auth-keys.js` must equal the job's `SUPABASE_URL`.
- Never pair `signIn` with an `addInitScript` storage wipe. It re-runs on every
  navigation and drops the supabase-js session.
- `VITE_SUPABASE_URL` stays unset in CI, so the client uses its placeholder
  host, which the `**/auth/v1/**` routes still match.

Local run steps are in the `playwright.config.js` header.

### Card look spec (#453)

`frontend/e2e/card-look.spec.js` pins the computed box (background, border
colours and widths, corner radii, box-shadow, padding) of every card surface,
in the light theme at 1366px, plus the 390px surfaces whose media queries
change a card. It runs offline: GoTrue and every `/api` call are stubbed, so
only the Vite dev server is needed (`npx playwright test e2e/card-look.spec.js`
from `frontend/`). The expected values are literals recorded from the browser,
never derived from the CSS. After a deliberate visual change, re-record:
`CARD_LOOK_RECORD=1 npx playwright test e2e/card-look.spec.js` prints each
surface's values (once two reads agree) instead of asserting. Fold them back
into `LOOK`, keeping the shared shapes (`CARD`, `JOINED`, `LEARNER`, `strip`,
`bare`) where they still match. A surface the refactor only moves must pass
unchanged without re-recording. Zero-width borders read as colour `none`, so
an unseen side colour never fails a move.
Gotchas:
- The session page focuses the composer after the session loads. Reading
  before that focus lands races it and pins the `:focus-within` border; wait
  for the focus, then blur.
- Park the mouse after the form sign-in. Otherwise whatever lands under the
  submit button's old spot reads in `:hover`.
- `:focus-visible` needs real `Tab` presses; script `focus()` may not match it.

### Favicon generation

`frontend/scripts/gen-favicon.py` regenerates `frontend/public/favicon.ico` from the
Logo mark geometry, drawn directly with Pillow's `ImageDraw` (rounded rect, tab, two
round-capped lines) at 512px supersample, downscaled with LANCZOS to 16/32/48 and
saved as a single multi-size `.ico`. Pillow cannot rasterise SVG and cairosvg needs a
cairo DLL absent on Windows, so there is no SVG-to-ico path here.

Run: `python frontend/scripts/gen-favicon.py` (installs nothing itself; `pip install
pillow` first if missing).

`frontend/public/favicon.svg` is hand-maintained separately and is not generated by
this script. Its geometry must stay in sync with the mark in
`frontend/src/components/Logo.vue` whenever one changes.

### Anti-slop Oxlint plugin

Vendored at `frontend/.oxlint/anti-slop/` and registered via `jsPlugins` in
`frontend/.oxlintrc.json`; provenance in its `UPSTREAM.md`. Gotchas:

- The rule source is `.ts`, loaded through Node's built-in type stripping. That needs
  Node 22.18+ (CI resolves 22.23); older Node in the `engines` range cannot load it.
- `@oxlint/plugins` must stay exactly equal to `oxlint`; both are in the dependabot
  `oxlint` group.
- `oxlint --fix` for `require-readable-spacing` splits one-line multi-statement blocks
  (`{ a(); return }`) into broken layout. Rewrite such blocks by hand, then re-lint.
- A Prettier rewrap can turn one statement into several and create new spacing findings;
  the edit hook's Prettier+oxlint pass catches this. Re-run `npx oxlint . --fix` after
  formatting.
