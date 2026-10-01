# Decisions

Durable "why": decisions, findings, tradeoffs. Newest first. Technical
how-it-works lookup belongs in `docs/reference.md` instead.

## 2026-10-01 - The card is one CSS class (#453, #454, #455, #456, #457, #458)

Architecture review candidate F6. `CONTEXT.md` calls the card the base unit
of the world, and `DESIGN.md` describes one card object, but the code had no
card class. 21 `.vue` files each re-declared the box (stock, 1px `card-edge`,
6px radius, 1px hard drop). Six rules re-declared the notice-strip shape.
`sheet.css` and `profile.css` held private copies for two routes each. The
card was off in two places: the drop is on 22 lines in 21 files, not 22
files; and `CONTEXT.md` lists 8 things built from a card, while `DESIGN.md`
lists 10.

- **One global `.card` class with modifiers, not a `<Card>` component.**
  `card--learner` (blue stock), `card--joined` (`0 6px 6px 6px`) and
  `card--banner` (`0 0 6px 6px`, no drop) live in `assets/card.css`, loaded
  after `base.css`. A class adds no DOM, works on plain elements, and doesn't
  add a new place for the scoped-CSS root leak. A component would wrap every
  card and could not wrap the sidebar row or the auth status slot cleanly.
- **The class is the look only.** It never sets padding or layout. The
  standard padding becomes `--card-pad` (the `DESIGN.md` name), and the 8
  components that typed it use the variable. A class that set padding would
  surprise every new user of it.
- **Members:** full cards and notice strips. Dialogs and toasts stay in
  `dialogs.css`; PrimeVue owns their markup and they use the lift, not the
  drop. Tabs, the cue toggle, the avatar and structural edge lines are not
  cards.
- **Notice strips carry no drop.** `DESIGN.md` contradicted itself: the One
  Drop Rule says every card has one, while the Status Banner spec and all six
  shipped strips have none. The code wins: a strip hangs from the surface
  above it, and on the login page it sits inside a card, where a drop would
  be a second depth layer. The One Drop Rule gets amended to name the
  exception (#458).
- **The login status box is a notice strip.** `DESIGN.md`'s "Auth status
  box" line (full coloured border, 4px) was stale; the code wins (#458).
- **Also shared: `.text-btn` and `.error-line` (#457).** Both are pure
  repeats. `.text-btn` takes `profile.css`'s existing set. The two focus
  rings stay per component: the soft ring on components and the solid ring
  in the sidebar and Settings is designed, and making soft the global
  default would be a visible change. Per-component reduced motion is
  deliberate (`base.css` comment, `reducedMotion.test.js`).
- **Pure moves; no pixel changes.** Each move deletes the copied box lines
  and keeps only a differing property, such as the composer's
  `--control-edge` or the auth cover's lift. Three cascade traps are named
  in the tickets:
  - `base.css`'s `:focus-visible` radius ties with `.card`, so `card.css`
    must load later;
  - `.card` loses to every scoped rule on the same element, so each move
    first checks sibling rules (for example, the sidebar row's `:hover`
    background);
  - Recall's existing local `card` class is renamed before the global one
    lands (#454).
- **Tests.** A computed-style Playwright spec pins every moved surface
  first (#453). It is offline, with `page.route` stubs, and is not a
  screenshot test, because fonts differ between Windows and Linux CI. A guard
  test then fails on a re-pasted drop, full card box or notice strip
  outside `card.css` and `dialogs.css` (#458). The refactor ends with one manual look in both
  themes and at 390px.
- **Order:** safety net (#453) -> class and session page (#454) -> page
  cards (#455), shared-sheet copies (#456), text button and error line
  (#457) in any order -> guard and docs (#458). Independent of F4: F4 moves
  script and tests, and #454 rebases over whichever `SessionView` change
  lands first.

## 2026-10-01 - The session page composes seven modules (#443, #444, #445, #446, #447, #448, #449, #450, #451, #452)

Architecture review candidate F4. `SessionView` (1538 lines) was almost all
orchestration. It wired 33 session store members, held 14 stale-id checks
and 7 module-level `let` flags, and kept the cue tick only to pass one
child's output to another. Its 116 tests mount the whole page, so the level
picker, scroll follow and upload could not be tested alone. The page now
composes seven composables and keeps only the glue. The card was wrong in
three places: 33 store members, not 34; 116 tests, not 107; and the
Diagnostic consent zone has 9 stale-id checks, not 5.

- **The profile loads through F3's `useResource` (#445).** It is the same
  endpoint and the same PATCH as `ProfileView`, so the profile gets one loader
  and F5 one foundation. This is why F4 is blocked by #408: a choice, since
  F3's ADR left the view's guards to F4. Two rules are added to
  `useResource` (F3 amendment below): `set(value)` drops an older in-flight
  fetch, and a `params` change clears `data`. `set()` closes a latent
  same-id overlap. A stream-finish refetch that started before a level save
  and landed after it wrote the old null level back and resurrected the
  picker until the next click.
- **A failed refetch keeps the last good profile.** Deliberate visible
  change. Before, the profile went null: the picker hid, the cue column fell
  back to the store's older copy so this session's cues vanished, and the next
  good fetch re-animated them as new and ticked an unrelated reply. The
  failure toast is unchanged.
- **Seven modules; the view keeps the glue.** The modules are: profile
  (#445), sending (#446), level picker (#447), arrival links and resume
  (#448), scroll follow (#449), reference-file upload (#450), and spend-limit
  notices (#451). The view keeps the `current` discriminator and its derived
  computeds, the optimistic header, the end-summary dialog, the four check
  handlers, the topic card's visibility and the F-18 stream announcements.
- **Each module resets itself on a session change.** Each one takes the
  session id getter, as `useReferencePoll` does. `loadCurrent`'s 9-item reset
  list and the id watcher's upload reset go.
- **A shared "still current?" helper is deferred to F5.** 12 id checks
  survive F4: the picker's 7, upload's 4 `uploadGen` checks, and the page
  load's 1. F5 rewrites the picker's 7 and adds `ProfileView`'s 3
  `idAtWrite` copies, so it owns the decision. If it adds the helper, upload's
  4 convert in that ticket.
- **One `sendTurn`, with error placement per caller (#446).** Six paths
  called the store's send with five error treatments, each on purpose:
  - typing and topic pick show a chip with Retry, and typing stashes the
    draft on `auth_expired` (E-05);
  - the picker's "Quiz me" shows its error on the card (F6);
  - the level declaration is swallowed, since the level is already saved;
  - a review seed or `?quiz` link shows the store's banner.

  One placement for all would undo F6 or E-05. The tick clears when any
  tutor reply starts, not per sender (#443).
- **"Which cues are new" belongs to the profile module (#445).** It moves out
  of CueColumn, so CueColumn and MessageList become plain displays. Tidiness
  only; CueColumn is always mounted, so there was no bug.
- **Modules read stream state through the session store.** F2 keeps its
  helper store-internal (#416).
- **Found while grilling: the cue tick jumped (#443).** Only typing and a
  topic pick cleared it. After the quiz button, the level declaration, a
  review seed, a `?quiz` link or a check follow-up, a reply that landed no cue
  inherited the previous reply's tick. Now it clears on the stream-start
  edge.
- **Deliberate visible changes:** `ProfileView`'s header no longer shows the
  previous session's level while switching (#408); a failed refetch keeps the
  profile (#445); the tick fix (#443).
- **Tests.** The safety net comes first (#444): check-handler errors, cost
  warnings, tick plumbing, and no picker on an ended session (#441 relies on
  that). Each move adds its module's tests while every existing view test
  passes unchanged. The one named edit is CueColumn's diff tests, which move
  to the profile module (#445). #452 then trims the duplicated view tests and
  keeps wiring tests.
- **Order: bug fix, safety net, profile, sending, then the picker and
  arrival links.** Scroll, upload and spend notices go in any order; the trim
  is last. Every move waits for #416, and the profile also for #408.

## 2026-09-30 - The learner profile has one reader and one edit recipe (#436, #437, #438, #439, #440, #441, #442)

Architecture review candidate B6. The learner profile is a JSON blob on the
session row with a tolerant parser. Seven writers hand-wrote the same four
steps (lock, read, change, save); the profile routes locked twice; the
session cards read the raw JSON; the aggregate imported the private parser;
resume copied the blob by hand while `seed_from_prior` had no callers. The
card was wrong in three places: the lock guards the whole session row, not
the profile (4 of its 17 call sites never write the profile, and the check
service holds 5); the two patch paths carry different rules on purpose; and
the two summaries are different things. There are 117 profile tests, not 115.

- **The session lock gets its own module (#438).** `lock_session_row` moves
  to `services/session_lock.py` with #417's flush-then-refresh, and every
  caller uses it through the module so monkeypatch spies still see the
  calls. Rejected: leaving it in `profile_service` (the check, topic-suggest
  and document code would keep importing the profile for a row lock, and a
  profile tidy-up could hide it); B4's guard module (route-facing admission
  that runs before the handler; the lockers are services mid-turn).
- **One edit recipe that never commits (#439).** `edit_profile` locks, reads
  fresh, compares the optional `If-Match` tag (a typed `ProfileChanged` the
  route maps to 412), applies the change, enforces list caps and stages the
  write. The learner and tutor doors commit on every return, refusals
  included (B1's rule). `record_from_answer` and Diagnostic grading join the
  commit of the answer or Close they run in, and session end keeps its one
  commit (F-33). The routes' second lock and `save_profile(commit=...)` go.
  Rejected: keeping the steps hand-written (the order is the rule the #417
  bug broke); a recipe that always commits (breaks the nested writers and
  F-33, and needs the commit switch B1 removed). Intended precedence change:
  a malformed argument with a stale `If-Match` gets 422, not 412.
- **Two doors, not one patch path.** The card's "the two patch paths become
  one" is rejected. The learner and tutor rules differ on purpose: evidence
  for mastery and level, the focus-clear guard (F-02), creating vs only
  updating subtopics, and the error shape. A "who is asking" switch would
  weave the tutor's guard rails into learner code. The shared plumbing is
  the recipe.
- **The profile module is the only reader and writer of the blob (#440).**
  The parser goes public. The session cards read through it (a non-dict blob
  would crash the session list), the aggregate imports the public name, and one
  new-session function replaces resume's hand copy, so a resumed blob is now
  normalized rather than byte-copied. `seed_from_prior` is deleted. Rejected:
  a quick-facts reader for the cards (the aggregate already runs the full
  parser on every session).
- **The two summaries stay where they are.** The end-of-session summary
  (in the profile, learner-visible, carried forward on resume) and the
  running recap (its own column, tutor-only) are different things. Moving the
  first out of the profile needs a migration and gains nothing.
- **The `[auto]` tag goes (#440).** The mechanical fallback summary was
  stored with an `[auto] ` tag that nothing acted on. One server site and
  five browser sites hid it, the tutor prompt never did, and it leaked to a
  learner screen once (F-53). It is now stored plain, the parser cleans old
  rows, and #440 updates the design doc's two "[auto]" lines. Lost: telling
  from stored data whether a summary was the fallback; log it at write time
  if that ever matters.
- **An ended session's profile is read-only (#441).** A deliberate
  divergence from B5, which kept file delete allowed on an ended session.
  Tradeoff: fixing an ended profile takes an extra step (continue the topic,
  or reopen), in exchange for closing the edit-during-summary window
  outright (session end commits `ended_at` before the summary model call)
  instead of relying on #417 alone. `ProfileResponse` gains `ended_at`, and
  the page goes read-only. Until then the profile routes use
  `owned_session` in #423.
- **Found while grilling: one bad entry blanked the whole profile, and the
  next write saved the blank (#436).** Probed: a profile with a level, two
  mastered, a gap and a summary, where one mastered entry carried a retired
  evidence value, loaded as empty. After one learner edit the stored blob held
  only the new gap. Latent: stored entries have allowed only
  `declared`/`tested` since slice 8, and every write validates. The trap
  would spring on the next change that narrows the profile's shape. The
  parser now salvages per field and per element. Also found: a DELETE route
  test that always passed (it compared a string with a list of objects) and
  never checked focus, and untested DELETE guards (both in #437).
- **Deferred.** The running recap's unlocked update (worst case one duplicate
  model call; it writes its own columns, never the profile); the
  `[auto-rolling]` tag (stub mode only); `load_profile` kept (13 callers).
  Whether the tutor should respect the learner's own edits is parked as #442
  until after the refactor, since profile features may be cut or changed
  first.
- **Order: bug fix, safety net, lock move, edit recipe, readers, then the
  ended read-only.** #438 waits for #417. #439 waits for #420 (Diagnostic
  grading moves into the check module) and #423. #441 waits for #408 (the
  profile page's loading).

## 2026-09-30 - Reference files are one module and file formats are one table (#430, #431, #432, #433, #434, #435)

Architecture review candidate B5. Upload had no module: one ~210-line route
did validation, dedupe, the cost gate, the rate slot, three content checks,
row creation and the flush, blob, commit protocol with the worker. File-format
knowledge (page counting, extension lists) lived in both upload and ingestion,
and the two caches derived from a session's files (the centroid and the
keyword index) had no owner. The card's "status computed in four places" was
wrong: every reader already calls `documents_service`. Replaced by
`documents_service` as the reference-files module and one file-format table.

- **The module owns intake, status, delete and both derived caches; the
  worker and the ingestion pipeline stay put.** Rejected: one package holding
  the worker and ingestion too. It would rewrite 171 test references and the
  RUNBOOK's scale-out recipe, and concentrate no rule the module leaves
  scattered. The route keeps the guards (B4's tiers compose around the
  module), and the module never touches money. Ingestion touches the caches
  at two moments (centroid nulled before embedding, F-05; keywords merged in
  the ready commit, F-27), so the module offers small functions, not one.
- **Two status answers, on purpose.** "Learner status" ranks pending above
  ready, so the banner says something is still coming. "Anything
  searchable?" is any ready file. One shared answer would block search over
  an older ready file while a new one processes: the masking bug the old
  latest-document lookups had. Known wrinkle, accepted: the tutor's
  `INGESTION_STATUS` reads `pending` while older files are searchable, and
  two retrieval-policy rules then pull against each other. Prefetch covers
  the common case (with a ready file it always returns hits, and is empty
  only when the embedding call fails), so the wording is left to B2's prompt
  work (note on #395). The session-wide contract enum drops `processing`,
  which the aggregate never sends (#431).
- **One backend file-format table.** Per format: extensions, magic bytes,
  plaintext flag, page counter and extractor. Upload and ingestion both read
  it. The frontend keeps its hand-kept list, and B7 takes it with the other
  mirrors. Rejected: serving accepted types over the API (a contract change
  that could clash with B7's method). `.markdown` is left out of the picker
  hint (`ACCEPT_ATTR`) on purpose; it is not a bug.
- **Found while grilling: fixes first (#430).** A rejected upload used a
  daily slot. The slot, which commits, was taken before three free content
  checks (probed: a fake PDF got 415 and a count of 1). The checks move
  above the cost gate. The slot does not move later instead: its commit
  would publish the flushed row before the blob exists. A 507 storage
  failure still uses a slot, a deliberate deferral: it is an infrastructure
  fault, and a refund would collide with #423's `take_slot`. Delete also left
  the file's keywords behind; it now rebuilds them from the remaining ready
  chunks under the session lock. The banner's "Indexing N" counted every
  file.
- **Delete stays allowed on an ended session.** Upload is refused there;
  delete is not, so a learner can always remove their own file. Pinned by
  #432.
- **Dead code goes before the move.** `GET /api/upload/{document_id}` has no
  caller (#400 removes the frontend wrapper first). The legacy bare-filename
  blob fallback is dead: canonical keys arrived with the store in #120, R2
  came later, and Render's disk is ephemeral. A NULL document status would
  fail the file-list response, but no path writes one; left alone.
- **E2E moves to Postgres (#434), then an upload spec (#435).** On SQLite,
  chunks store but vector search fails (probed), so no browser test could
  see a citation. Moving the required e2e job to the production database
  also exposes SQLite-only assumptions in the 7 existing specs. The upload
  spec ends on the citation list showing the file name. It needs #413's stub
  provider plus deterministic fake vectors. The #425 cost fields are asserted
  at the route, not in e2e. Rejected: a backend-only Postgres test with the
  browser stopping at "ready" (misses the citation UI, leaves e2e on SQLite).
- **Order: bug fix, safety net, contract cleanup, then the move.** #432 pins
  the fixed behaviour, including the dedupe-for-a-capped-learner case #422
  wrongly thought was pinned. The move (#433) waits for #432 and #431, so dead
  code is not moved. The e2e tickets do not gate the move: #433 is
  backend-only and #432 guards it. Split out as features, to be grilled after
  the move: retry a failed file (#427), cancel processing (#428), and process
  several files at once (#429).

## 2026-09-29 - Session guards are three tiers and paid admission owns one commit (#421, #422, #423, #424, #425)

Architecture review candidate B4. "May this user take this action on this
session right now" was a convention restated inline: 15 route-level ownership
404s, 6 `session_ended` 409s, and three paid routes with three guard orders.
The admission commit (the cost reservation (B-05), `ensure_user`, the
rate-limit slot) was hidden inside `rate_limit.check_and_increment`, which
committed on both arms. Replaced by one guard module with three tiers, and
one stream pump shared by chat and the check follow-ups.

- **Three tiers, not one policy call and not FastAPI dependencies.**
  `owned_session` (404), `active_session` (adds `session_ended`) and
  `admit_paid_turn` (caps, `ensure_user`, reserve, slot, one commit, a
  release handle). Two of three paid routes need code between ownership and
  admission (upload's free dedupe, the follow-up's Close); tiers leave it as
  plain code. A policy table would need mid-sequence hooks. Dependencies run
  before the handler body, so a cost gate there would refuse free
  re-uploads, stop capped learners closing a Set, and add statements to
  chat's prepare budget. `velocity_limit` stays a dependency: it needs no
  session row.
- **Ownership before the cost cap, on every route.** Report what is wrong
  with the request's target before what is wrong with the account's budget.
  A 409 flips the UI to the ended state and restores the draft; a 429 on an
  ended session left it looking open until midnight. Chat was the only route
  checking cost first, and its perf budget did not require it: the spend read
  and the session read are two statements either way, only the check order
  moves.
- **The tier owns one explicit commit, and a refusal leaves nothing
  behind.** `rate_limit.take_slot` only flushes. B3's own-transaction
  settlement (#411) needs the admission committed before the first model
  call; that invariant now lives where it is enforced. A refusal rolls back
  the tier's own writes before raising, because session end, resume and the
  follow-ups carry on and commit after a refusal. Left pending, the reserve
  would be published with no handle to release it, and the held ledger row
  lock would make a concurrent turn's settlement time out. Explicit rollback
  with an asserted "no pending writes" precondition, not a savepoint: the
  SQLite test engine lacks the pysqlite begin workaround. Chat's special
  rate-refusal release goes; a release handle exists only after admission.
- **Follow-ups are admitted after the Close and skip with a reason.** The
  Close has already committed, so an HTTP 429 would report a success as a
  failure, and gating before the Close would stop a capped learner closing a
  Set (every Close grades). `followup_skipped` already meant "Close done,
  tutor sat out" at the message cap; the cost caps now use it too
  (`cost_cap`, `global_cost_cap`), and the frontend picks copy by reason and
  shows the cap banner. Rejected: the route sending the tutor's `error` event
  (no contract work, but it calls a succeeded Close an error). A capped
  follow-up also stops consuming a message slot.
- **Session end and resume use soft admission.** A refusal gives the
  mechanical summary, never a 429. With the follow-ups they were the last
  callers of the committing `check_and_increment`, so one admission path
  remains. Upload admits with no reserve: it makes no model call in the
  request, and a reserve belongs to a request spanning several calls and the
  SSE lifecycle (B3 entry).
- **One mapper and typed schemas for cap refusals.** The route still owns the
  429 body (B3): it maps the tier's typed refusal, chat and upload to a 429,
  the follow-ups to `followup_skipped`. Per-user cost bodies are always full
  (upload gains three fields); the global body stays `{code, resets_at}`, so
  service spend is never shown. No wire break: the 429 `detail` already
  allowed extra fields.
- **One shared stream pump.** The follow-up's copy of the pump had drifted
  from chat's: it lacked the shield around cancel, drain and release.
  Rejected: keeping two copies (that drift caused the bug below); moving
  disconnect handling into the tutor (puts HTTP in the agent layer).
- **Found while grilling: a follow-up disconnect lost the partial reply and
  its cost (#421).** Starlette's cancel is level-triggered, so the
  follow-up's unshielded `await task` was itself cancelled and the tutor's
  cancel arm died at its tool-drain await, before saving anything. Probed: 0
  rows saved with a tool call in flight. The same unshielded-cleanup mistake
  let chat's prepare-failure release be skipped ($0.02 held until midnight).
  One fix-first ticket, blocked by nothing.
- **Order: bug fix, Postgres characterisation, the tiers, the pump, then the
  contract change.** #422 reuses #418's held-lock harness. The pump (#424)
  lands before follow-up admission (#425), so the follow-ups hand a release
  handle to one pump instead of editing a copy. Left to other candidates: the
  profile routes' double lock and If-Match (B6), `_to_response` (B7), and
  upload's document 404 (B5).

  **Amended 2026-09-30 (B6):** the profile routes take `owned_session` in
  #423 (no behaviour change); #441 moves their writes to `active_session`
  together with the read-only profile page.

## 2026-09-27 - The check lifecycle is one module that owns its commit (#417, #418, #419, #420)

Architecture review candidate B1. A Check (1-3 Sets) was spread over the
check service, `pending_check_store`, diagnostic grading and sequencing in
the routes. One answer click ran up to three commits, `commit=` sat on nine
functions in four files, and `pending_check_store` existed only to break one
import cycle. Replaced by one check module, `services/check_service.py`. The
terms (Check, Set, Item, Close, Recap, Diagnostic) are now in `CONTEXT.md`.

- **One module, not tighten-in-place, not deferred.** The check code had no
  learner-visible bug; the payoff is locality. Deferring (the G-13 route) was
  the alternative. Rejected because B4 edits the same routes, and the next
  check feature would have to re-learn the three-commit sequencing.
- **The module commits every action itself.** Each action locks the session
  row, commits, and releases the lock on every return, conflicts included
  (commit, then raise). Never by rollback: register and the message-id stamp
  run inside the tutor turn, whose flushed ledger writes must survive. No
  public function takes `commit=`.
- **Session end is the one named exception.** Abandon joins the caller's
  transaction and takes the lock itself, so F-33's single write window in
  `generate_and_persist` stays. Rejected: callers always commit (moves B-02's
  commit-before-stream timing back into the routes); abandon commits too
  (breaks F-33).
- **Recording a graded answer stays in `learning_event_service`.** It loses
  `clear_pending` and `commit`, never commits and never touches check state.
  The mastery and gap rules keep their own direct tests, and a second event
  source (R5, demand-gated) would call it directly.
- **Every Close grades.** Complete, Stop and session end share one Close
  path, and Diagnostic grading runs on each, forced when the learner cuts the
  Check short. This replaces Complete's "crash-window backstop", whose window
  #419 removes; it still grades a session stranded before the change.
- **The Recap freezes only on Close.** The per-click snapshot was never read:
  both session reads suppress the Recap while its Set is open, and every
  Close re-froze it under the lock. Dropping it also drops its unlocked write
  race.
- **One conflict error with a code.** Codes are unchanged and the routes map
  it to 409 (C-14). No API or payload change, so F2 #416's converter is
  unaffected.
- **Found while grilling: the row lock returned a stale row (#417).**
  `lock_session_row` emitted `FOR UPDATE`, but when the row was already
  loaded in the session SQLAlchemy kept the pre-lock attributes. Most write
  paths load before locking (the route guards; session end loads the profile
  before its summary LLM call). So on Postgres the lock waited and the code
  then worked from the old copy: a profile edit during session end was
  overwritten, and a double Complete could run two follow-ups. Fixed in the
  helper: flush, then re-read with `populate_existing`. A bare
  `populate_existing` would drop the caller's own unflushed edits (sessions
  use `autoflush=False`, and Stop and abandon edit the row, then re-lock).
  Filed on its own, not inside B1, because it hits profile edits too.
- **Order: bug fix, Postgres characterisation, behaviour, then the move.**
  #418 runs five held-lock race cases on the CI Postgres service (SQLite
  ignores row locks). #419 makes answer and skip one commit and drops the
  per-click snapshot. #420 merges; it is also blocked by B2 #395, whose
  prompt builder reads check state from the row. B4 (guards) follows #420,
  since both edit the check routes.

## 2026-09-27 - The chat stream is a helper inside the session store (#414, #415, #416)

Architecture review candidate F2. `stores/session.js` (1128 lines, 59
returned members) mixed the session list and detail with live streaming.
The chat send and the check follow-up duplicated their setup, SSE switch and
catch; the check batch mapping was written three times; eleven returned
members had no production use. Replaced by `stores/chatStream.js`, a factory
the session store builds once, and `lib/checkBatch.js`, one converter.

- **A helper, not a second store.** `messages` has two writers (detail loads
  and stream appends) and one retention rule (`MAX_RETAINED_MESSAGES`). Two
  peer stores would put that rule in one while the other also writes, and
  would call each other (append one way, abandon the other). The helper gets
  the refs it writes injected and never imports the store. The store
  re-exports ten members flat, so `SessionView` does not change before F4.
- **Stream functions resolve at call time.** Tests spy on `streamChat` after
  the store exists; a function captured at construction would bypass them.
- **The check batch stays in the store.** It is session data that only
  sometimes arrives through the stream: `loadSession` sets it too, and
  answer and navigation are plain HTTP. The helper writes `pendingCheck` on
  `check_question` through the shared converter. Moving the batch would make
  the store reach into the helper for non-stream work.
- **One turn runner with per-kind hooks.** Send keeps the optimistic row, the
  401 draft stash (E-05) and the 409 `session_ended` arm; the follow-up keeps
  the batch restore and `followup_skipped`. These are real differences and
  stay hook choices. Caps move to the helper because only stream paths set
  them. The shared `error` slot is injected, because `SessionView` renders
  one inline error.
- **Three bugs fixed first, on today's code (#414).** A follow-up network drop
  discarded text the learner had watched stream. The server persists it on
  cancel, so a reload brought it back. It now settles through
  `_settleWithError` like send (E-03's stated intent). `reset()` on sign-out
  nulled the abort handle without aborting, so the unmount hook could not
  stop the stream and the server kept billing. `reset()` now abandons first.
  The dead-stream marker is a sentinel, not `null`, because after `reset()`
  `currentSessionId` is also `null` and `null !== null` would un-supersede
  late events. Also added to #414 after the design review: in-flight loads and
  mutations that resolve after `reset()` wrote the previous account's data
  back (only `loadEarlierMessages` was guarded; `_inflight` and
  `_latestRequestedId` survived reset). `reset()` now bumps an epoch, and
  every async store action drops its writes when the epoch changed.
- **Order: fixes, then safety net, then pure move.** #415 rewrites the 32
  test lines that call internals into fake-stream events, with no production
  change. #416 moves the code, and every existing test must pass unchanged.
  Fixing first means the move is pinned to the fixed behaviour, not the bug.
- **Independent of F1 #403.** #403 rewrites inside `chatStreamService.js`
  and keeps `streamChat({ sessionId, signal, onEvent })`. Either can land
  first. #414's transport-level E-05 test binds whichever lands second. F4
  (session page composition) is blocked by #416.
- **Out of scope.** Unknown SSE events stay ignored (B7 owns the event
  contract). `libraryLoading` and the list/detail `loading` pair belong to
  F3/F4. The `!sawTerminal` branch keeps today's behaviour on both paths.

## 2026-09-27 - LLM calls and their metering are one adapter (#410, #411, #412, #413)

Architecture review candidate B3, reopening G-13 (2026-09-21). Six production
modules imported `litellm` directly. The metering sequence (price, token-math
fallback, record, log) was copied per caller with different failure handling:
46 metering call sites across 8 modules. The cap was checked inline at 7
sites, stub mode was 4 inline checks, and only embeddings retried. Tests
patched 16 module-scoped path strings that all resolved to the same global
module. Replaced by `backend/services/llm.py`: a shell that owns the cap gate,
retry and cost settlement, around a swappable provider (litellm, the stub, or
a test fake).

- **G-13 is reopened on purpose.** G-13 declined to split `run_streaming` for
  readability alone. The payoff now is cost correctness: every new LLM
  feature copied the metering block, a test fixture had gone stale, and a
  rollback could erase real spend. #410 writes the characterisation tests
  G-13 asked for before any production change. They patch the global
  `litellm` module, so they run unmodified through the refactor. (G-13's
  `tutor.py:591-600` reference is stale; the guard it meant is the
  `billed_iters` watermark, which #412 deletes.)
- **Scope is completions and embeddings.** Removing `cost_holder` needs the
  embeddings inside. The offline eval judge script stays on raw `litellm`:
  it has no user to bill.
- **The adapter gates every call and fails closed.** It checks the user cap
  and the global ceiling before each call and raises `CostCapExceeded`;
  callers keep their own reaction (partial persist, mechanical summary, skip).
  If the spend read itself fails, the model is not called, so a database
  outage bounds unrecorded spend to calls already in flight. The route gates
  in chat and upload stay: they refuse before parsing or taking a rate-limit
  slot, and they own the 429 body. New behaviour: the tutor and the summaries
  honour the global ceiling, and retrieval embeddings are gated.
- **The B-05 reservation stays outside the adapter.** A reserve belongs to a
  request that spans two to six or more calls and the SSE lifecycle, not to
  one call. This reverses the review card's "reserve moves into adapter".
  Candidate B4 owns a reserve helper and the follow-up route's missing
  reserve and shield; it depends on B3 only for the gate and
  `CostCapExceeded`.
- **Settlement commits in the adapter's own transaction.** `record_cost`
  flushed into the caller's transaction, so a caller rollback erased real
  spend. `cost_holder`, the B-08 re-record and the lost `LlmCallLog` rows
  all worked around that. Now the ledger row and the log row commit per
  call. Invariant: no caller holds an uncommitted ledger write across a
  call, and the adapter sets `lock_timeout` so a violation fails fast
  instead of hanging. For this reason #411 leaves the `retrieve` tool's
  embedding on the old path until #412 removes the tutor's own ledger
  writes.
- **Settlement never raises.** A failed ledger write is logged at error level
  with user, purpose, cost and usage, and the caller keeps its result. The
  vendor has already charged, so throwing the output away (what the
  summaries did) is the worst outcome. No deferred retry: the ledger is a
  daily budget reset at midnight, and the log holds the amount. An inline
  retry was rejected because a streamed call settles synchronously in its
  exit, where a pause would either block the event loop or need a shield;
  `pool_pre_ping` already absorbs stale connections.
- **A streamed call settles itself exactly once on every exit.**
  `async with stream()` yields typed events. The exit settles the real
  price, or an estimate on cancel (always) and on error (if output arrived or
  it was a timeout). The watermark, the prompt snapshots and
  `_record_partial_cost` go. This supersedes the F-03/B-10 "double-count
  kept deliberately" rationale on the error path: that re-estimate existed
  because a rollback could erase recorded spend, which own-transaction
  settlement ends. An errored turn now bills once.
- **Retry covers completions too.** 429, 503, 500 and connection errors
  retry on every call; streams retry only before the first event reaches the
  user. Completions do not retry timeouts (a 30 s timeout retried twice
  would keep the user waiting 90 s or more); embeddings still do. A failed
  attempt with no output settles $0, except a timeout.
- **One module-level active adapter, one test fake.** `llm.get()` resolves
  per call. Tests install a fake provider under the real shell, so the gate,
  retry and settlement run in every test. Explicit injection was rejected
  for now: it churns signatures across the tutor, the services, the
  background summary and the ingestion loop, inside G-13's regression
  surface, and FastAPI `Depends` cannot reach the background paths. If it is
  wanted later, add an optional `client=` parameter defaulting to
  `llm.get()`, one function at a time.
- **The stub is a provider, and it keeps reading the prompt.** This revises
  the B2 entry's plan to pass the summary as data.
  `resume-carries-profile.spec.js` asserts `[STUB:resumed:` because the stub
  sees the summary in the assembled system prompt, so reading the prompt is
  the e2e oracle, not accidental coupling. The summary label becomes a
  constant shared by `prompts.py` and the stub, with a render-to-stub test.
  `complete` and the embeddings raise `LlmUnavailable`, callers keep today's
  stub-mode output, and stub mode never touches the network. Deterministic
  fake vectors wait for candidate B5's e2e upload test, their first user.
  **Amended 2026-09-30 (B5):** #435 makes the stub's `embed` and `aembed`
  return deterministic fake vectors (cost 0, no network); `complete` still
  raises. Stub-mode ingestion now reaches ready.
- **Tracer-bullet order.** #410 characterisation, then #411 (core plus
  summary, retrieval and ingestion), #412 (streaming and the tutor), #413
  (stub). The core is proven on low-risk callers before `run_streaming` is
  touched. #395 (B2) is a soft ordering only: both edit `routes/chat.py`.

## 2026-09-27 - List and resource loading is one composable module (#406, #407, #408)

Architecture review candidate F3. Six call sites each hand-rolled fetch,
loading, error and retry, using three error types (`false`, `''`, and a
string or null) and two pagination styles. The `const seq = ++X` latest-wins
guard was copied into three loaders, and three had no guard at all. Replaced
by `frontend/src/composables/useResource.js`: a private latest-wins core under
`usePagedList` (Recall, the Sessions library, sidebar search) and
`useResource` (the session profile load, the aggregate profile, the usage tab).

- **Scope stops at page loaders.** The ingestion poller, the start flow,
  profile and settings writes, and the id-snapshot and stream guards in
  `SessionView` and the session store stay as they are. Their lifecycles
  differ (backoff, a state machine, serial writes, session identity). The
  store's guards belong to F2 and the view's to F4. The card's "43 guard
  sites" counted these too. Only three loaders used the loader idiom.
- **Two entry points, one core.** A single composable with a `paged` flag
  would show every single-object caller `items`, `hasMore` and `loadMore`.
  Two small interfaces keep each caller honest, and the guard exists once.
- **The composable watches a `params` getter.** A change restarts from offset
  0 and drops older replies, so "inputs changed, start over, ignore late
  answers" is a single rule rather than a dance each view must remember.
  The Sessions library's failed-reload Retry bug came from getting that dance
  wrong. Debounce stays in the view, because it is input UX, not loading.
  A `null` from the getter means idle: drop the in-flight reply, clear, fetch
  nothing. The sidebar needs this for an empty search box.
- **Errors are the raw thrown value, `null` when clear.** Views choose the
  words (`friendlyError` or fixed copy). The status survives for callers that
  need to tell a 404 from a 503. The composable never decides toasts: the
  fetcher passes `silent` itself, and toast-versus-inline stays with #404.
- **The pager requires a `key` and drops repeated rows.** Offset paging
  shifts when the list changes between pages. The offset advances by raw rows
  received, so dedup never re-requests a range. An empty page ends paging
  even when `total` says more.
- **Pager reloads keep the old rows until the new page lands, and clear
  them on failure.** Keeping them avoids a flash on every keystroke; clearing
  on failure avoids showing one filter's rows under another's label. The
  whole-list failure (`error`, Retry from 0) and the next-page failure
  (`moreError`, keep rows, retry that page) are separate slots, so the wrong
  Retry cannot be wired.
- **`useResource` keeps `data` on failure.** This differs from the pager on
  purpose. All three callers did this already, and their templates rank the
  error branch above the data branch. Clearing would add a visible change
  that nobody asked for.
- **Store-owned rows go in through `into`.** Sidebar search rows stay in the
  store's `searchRows`, because rename, pin and end must patch every visible
  copy of a row (`_observedRows`). The composable writes into that ref and
  keeps no shadow copy of it.
- **Nothing visible changes except loading correctness.** Those changes are:
  no duplicate Library rows, a failed Library reload that clears its rows and
  has a Retry that reloads, and stale guards where there were none. One of
  the new guards closes a latent Recall race, where a reload could append a
  late page onto a fresh list. No current UI path reaches it. The double
  toast-plus-inline error on the three single-object views is left to #404.
- **Tracer-bullet order.** #406 builds the core and the pager with Recall, the
  hardest pager caller (the #385 dedup and failed-next-page tests). #407 adds
  the Library and the sidebar, the users of `into` and `null` idle. #408 adds
  `useResource` last, on a core three lists have already exercised. Existing
  view tests pass unchanged as evidence. The only edits allowed are for the
  deliberate changes above, each named in its PR. There is no ordering
  dependency on F1 (#400-#403), because F3 sits above the service functions,
  whose signatures F1 keeps.

  **Amended 2026-10-01 (F4):** `SessionView`'s per-turn profile load also
  moves onto `useResource` (#445). Two rules are added (comment on #408).
  First, `set(value)` writes `data` and drops any older in-flight fetch.
  Second, a `params` change clears `data` for every caller, so "keeps `data`
  on failure" now means same-params reloads only. Deliberate visible change:
  `ProfileView`'s header no longer shows the previous session's level while
  switching. A per-caller flag and a caller-side id check were rejected:
  clearing in the composable is the only option safe on every page without
  each caller remembering it.

## 2026-09-26 - One HTTP transport core under three thin wrappers (#401, #402, #403)

Architecture review candidate F1. The JSON client (`apiClient.js`), the chat
stream (`chatStreamService.js`) and upload (`uploadApi.js`) each call `fetch`
directly and copy the same auth and error policy (Bearer header, 401
refresh-and-retry, sign-out, `ApiError` mapping, cache invalidation). The
copying already caused a bug: only the JSON path read `X-Cost-Warning`, so
upload cost warnings never reached the user (#398). Replaced by
`services/http.js` `send`, with `services/getCache.js` as a standalone cache
module and the three files as wrappers.

- **The core returns an OK `Response`; wrappers read the body.** Body
  handling is the one thing that differs by kind (cached JSON, an SSE stream
  with an idle timer, multipart JSON). A `responseType` switch would pull the
  stream's parser and timers into the core. An interceptor chain would hide
  the order of the 401 retry and the cache.
- **An optional `prepare(token)` hook, not exported building blocks.** The GET
  cache is keyed on the token to stop one account seeing another's cached data,
  so its lookup must run after the token is known and again after a 401
  refresh. With the hook, the core owns that order once. Exporting
  `withAuth` and `fetchOnce` would make each wrapper assemble the order and
  reintroduce the copying F1 removes. Dropping the token from the cache key
  was rejected: it removes a deliberate guard.
- **Transient retry is an opt-in core option.** The JSON wrapper passes
  `retry: true` for GETs. It stays nested inside the 401 retry, as today;
  putting it in the wrapper would flip the nesting and refresh tokens on
  every network retry.
- **Timeout scope is an option.** JSON and upload bound the whole request;
  the stream bounds only time to headers, because a long answer is legitimate
  (F-06) and its 60s idle timer covers the body. One fixed meaning would
  either cut long streams or let a stalled body hang JSON forever. A caller's
  own abort passes through as `AbortError`, never `ApiError(0)`.
- **The core never toasts.** Only the JSON wrapper calls `reportApiError`
  (unless `silent`). Stream and upload errors render inline today, and
  several comments exist only to prevent double toasts, so toasting stays
  opt-in. Unifying toast versus inline is a UX decision, split out as #404
  together with the 19 `silent: true` sites. F1 changes nothing the user
  sees.
- **The 10 test files that stub `fetch` stay unchanged.** Passing unchanged
  is the evidence the refactor kept behaviour. Moving them to fake `send`
  would drop that net and stop view tests covering the core. Only the three
  tests that call `_onAuthExpired` directly are rewritten, because it
  becomes private to `http.js`.
- **Small fixes land first.** #398 (upload cost warning) and #400 (dead
  `getUploadStatus` and `uploadPdf` exports) merge before #401, so the
  refactor's tests are final before it relies on them. Then one wrapper per
  ticket (#401 core and JSON, #402 upload, #403 stream), so a red suite
  points at one move.

## 2026-09-26 - Prompt state is one typed builder, shipped in three parts (#395, #396, #397)

Architecture review candidate B2. The prompt state was an untyped dict built
in five places (chat, the check follow-up, and eval scripts) with different key
sets, and the renderer's `.get()` defaults turned every missing key into a
silent default. Replaced by `backend/services/prompt_state.py`: frozen
dataclasses with required fields, `gather_session_inputs` (reads the DB) and
a pure `assemble`. The renderer accepts only `PromptState`.

- **Three parts, merged in order.** #395 is a pure refactor with a golden
  test that pins the chat and follow-up prompts byte for byte. #396 changes
  behaviour. #397 removes dead state. Splitting them keeps the risky step
  small, and a golden-test diff in #396 shows exactly what the learner-facing
  change is.
- **Follow-ups change behaviour on purpose (#396).** The `/check/complete`
  and `/check/stop` follow-up turns rendered default learner prefs, no rolling
  summary, no gap accuracy, `DIAGNOSTIC` off and `PENDING_CHECK: none`. The
  last one means a follow-up after set 1 of 3 never sees the `between_sets`
  rules, and no test covered it. These were omissions, not choices, so the
  follow-up gets full parity on session-derived state; only per-message
  inputs (retrieval, prefetch, review target, `diagnostic_accepted`) differ
  from a chat turn. Part 1 passes the omitted values as explicit blanks so
  the refactor itself stays byte-identical.
- **The follow-up's `ToolContext.diagnostic_required` moves in #396, not
  #395.** In part 1 the follow-up's prompt state carries a blanked
  `diagnostic_required = False` to keep the rendered prompt identical (the
  renderer reads it). Pointing the tool context at that value would silently
  turn the diagnostic off for the tool, a behaviour change inside the pure
  refactor, so the live computation stays until #396 fills the real value.
- **Eval scripts migrate in #395.** Removing the dict path breaks the five
  eval scripts that build dicts or import the private
  `routes.chat._build_prompt_state`. Leaving them for a later part would
  break `dev` between merges. Eval prompts may change; the byte-identical
  guarantee covers production paths only.
- **`SEED_MODE` leaves the prompt only (#397).** It has rendered a constant
  since `eac5b91`. The `seed_mode` field on the start-session request is live
  (resume versus fresh start) and stays.
- **`agent/_stub.py` is deferred to B3.** The stub regex-parses the rendered
  `LAST_SESSION_SUMMARY:` line (`_SUMMARY_LINE`), coupling it to the prompt's
  text. Fixing that means passing the summary to `run_streaming` directly: a
  signature change across 14 test files and about 120 references, inside the
  code G-13 (2026-09-21) declined to restructure without characterisation
  tests. B3 (the LLM adapter) writes those tests and rewrites the stub anyway.
  **Revised 2026-09-27:** the stub keeps reading the rendered prompt, through
  a label constant shared with `prompts.py`, because the e2e resume spec
  relies on it. See the B3 entry.

## 2026-09-26 - Review is relabelled Recall; the queue stays off Home (#338, #352)

#338 asked whether to drop the Review page. Resolved: keep the queue and the
page, rename it. Built in #352 (rename) and #363 (redesign).

- **The page stays.** The review queue is the only mechanism that knows when
  a concept is due (SM-2-lite over `LearningEvent`s, computed on read).
  REVIEW-GAPS mode targets profile gaps from request flags and has no decay,
  so it does not replace the queue. A due marker on session rows was
  prototyped (`prototype/due-marker-on-session-rows`) and rejected: one page
  listing everything due across sessions earns its place.
- **"Recall", not "Review".** Review suggests re-reading; the page tests.
  Route `/recall` (name `recall`), `/review` redirects to it, rail
  aria-label "Recall: N concepts due".
- **Frontend-only rename.** `GET /review/queue` keeps its path; no contract
  or codegen churn.
- **The queue stays off Home.** The 2026-07-23 UI polish spec (#158, removed
  from `docs/superpowers/specs/` in 55998aa, recoverable from git) moved the
  queue from a Home card to its own sidebar entry and page. That stands.

## 2026-09-26 - Data export is one JSON file without the PDFs (#361)

The issue allowed "JSON (or zip with uploaded PDFs)", streamed. Built as
`GET /api/me/export`, a plain JSON response with `Content-Disposition:
attachment`, and a "Download my data" section directly above Delete account.

- **JSON only, uploads as metadata.** Filename, status, page count and date
  per upload; the bytes stay out. The learner already has the PDFs they
  uploaded, and a zip would mean reading every blob from the object store
  inside one request. Revisit if a compliance driver appears.
- **Not streamed.** One query per table, assembled in memory and validated
  against the `DataExport` contract. A learner's text data is small next to
  the 30s client timeout; switch to streaming only if real accounts get near
  it.
- **Same tables as delete, minus internal state.** Chunk embeddings, the
  open-check pointers, `rolling_summary`, `kw_index_json` and the per-call
  LLM log are left out: none of it is the learner's own content, and the
  LLM log names internal models. `check_batch_json` is left out too:
  answered checks are already in `check_answers`, and rebuilding a batch
  that was shown but never answered would pull in the transcript's
  `load_check_batch` reconstruction. Usage is exported per day (message count
  plus cost, merged from `usage_counters` and `daily_cost_ledger`).
- **Pure read.** Unlike `GET /me`, the export never creates the users row;
  a caller without one gets `account: null` and empty lists.
- **`format_version: 1`** is bumped when a field is removed or changes
  meaning, so an old export stays interpretable.

## 2026-09-26 - Recall page order is weakest proof first, not most overdue (#363)

The #351 resolution asks for "queue order preserved (most overdue group
first, most overdue card first within it)". Those two halves agree only
when every due concept has the same evidence: the review queue sorts by
`(tested evidence last, due_at)` (R4.2 AC2, `review_queue_service.py`), so a
not-tested concept due 2 hours ago leads a tested one due 9 days ago.

- **Queue order wins** (owner call). The Recall page keeps the backend's
  order for dividers, cards within a divider, and the concept "Check <topic>
  now" starts with. A concept the learner never proved is the more useful
  check, even when its due date is newer.
- **The frontend does not re-sort by `due_at`.** Doing so would silently undo
  R4.2 AC2 on this one page and disagree with every other queue consumer.
  Due dates can therefore read out of order inside a divider; that is
  expected.
- **The 100-item cap stays for this PR.** The page fetches `limit=100` (the
  route's max); anything past 100 is unreachable until pagination lands
  (#385).

## 2026-09-25 - Topic card gating lives on the session row (#354)

Builds the #341 resolution (a `suggest_topics` card under the first at-level
reply).

- **"Level became known this session" is recorded at create, not inferred.**
  The level picker's PATCH leaves no trace, a chat-declared level lands
  mid-turn, and a graded diagnostic lands in the follow-up turn, so no single
  turn can tell. `sessions.topic_suggest_state` (migration 0031) is
  `awaiting_level` only when a session starts without a level and flips to
  `done` when the tool runs. Seeded, resumed-with-level, and
  declared-at-create sessions stay NULL and never get the card; so do rows
  created before the migration.
- **The prompt sees `TOPIC_SUGGEST: DUE | AFTER_LEVEL | OFF`.** AFTER_LEVEL
  lets the model call it in the same turn it records a declared level; the
  handler re-reads the profile and refuses while the level is still unknown.
- **A dismissed level picker does not cancel the card** (owner call). If the
  learner later states a level in chat, the reply that records it carries
  the card. Level wording is mapped to the nearest level ("I know the
  basics" -> intermediate); when the model cannot tell, it records nothing
  and asks one clarifying question, the only case where asking about level
  is allowed.
- **No second column for the card.** The ok `suggest_topics` call already
  persists in the message's `tool_calls_json`; the transcript reads it back
  from there (the `reconstruct_check_batch` precedent).
- **Prose first is enforced, not just prompted.** A call made before any reply
  text fails, so the model writes the reply and calls again. When a check and
  a topic card are bundled, the first terminal tool wins and the card stays
  owed.

## 2026-09-25 - Check items resolve in any order within a set (#348)

Follows the multi-set decision in #339: Skip survives as the explicit "don't
know", a skipped item satisfies Done, free navigation applies within one set,
and sets stay sequential batches.

- **The server dropped its linear guard.** `answer()` / `skip()` accept any
  still-pending index; a resolved or out-of-range index is still a 409, which
  also keeps the F-24 double-submit loser rejected.
- **`current_index` now means "first unresolved item"** (`len(items)` once
  every item is resolved). The response shape is unchanged, so `is_done`,
  Stop, and resume-on-reload keep working; the card counts its set-rule fill
  from item status instead, because the pointer no longer equals the resolved
  count.
- **Card:** Next shows on every item but the last, Back on every item but the
  first, and Done shows on the last item (or any item once all resolve) but
  stays disabled until every item is answered or skipped. A skip lands on the
  next unresolved item, wrapping; skipping the final one still ends the set.

## 2026-09-24 - Session view scrolls the page, not the messages box (#346)

Reverses the app-shell lock from PR #24 (`body.chat-locked`, `.messages` as the
sole scroller), which had no decision record.

- **The document is the scroller.** A body class (`session-page`) now drives
  only a flex-height cascade, so a short transcript still puts the composer at
  the foot of the viewport. The composer is pinned by a sticky `.notes-foot`.
- **Cards scroll with the transcript at every width.** The check batch and the
  level picker (DiagnosticConsentCard) render at the end of `.messages`, never
  in the foot. The width-dependent `isNarrow` split is gone.
- **Profile stays pinned, the header does not.** The cue strip (under 900px)
  and the profile panel (900px and up) stay sticky so the learner's focus and
  gaps stay in view. The session header scrolls away with the page: it is
  page chrome, and pinning it too would cost a third band of a phone screen.
- **Leaving the session resets the scroll.** There is no router
  `scrollBehavior`, so without the reset the next route would open scrolled
  down.
- **`overflow: clip` stays on the narrow sheet** so the expanded profile's
  overlay never grows the page; clip is not a scroll container, so sticky
  still resolves to the viewport. The 390px e2e spec now guards that the page
  height is unchanged when the profile opens.

## 2026-09-24 - Learner preferences reach the tutor prompt (#342, #356)

Supersedes the v1 design spec's "drop interaction_preferences, profile-only"
spike outcome (see also the 2026-05-04 entry below): #342 decided learners
set three preferences, and the tutor honors them.

- **Three enums on the users row.** `feedback_pref` [hints, direct_answers],
  `check_ins` [often, sometimes, only_when_asked], `reply_length` [brief,
  balanced, thorough]; defaults hints / sometimes / balanced. Migration 0030
  coerces pre-enum `feedback_pref` values to `hints`; NULL stays "never set"
  and reads as `hints`.
- **Per-request, not cached.** The `LEARNER PREFERENCES` block sits next to
  `CURRENT TOPIC PROFILE` in the dynamic context, so changing a preference
  never invalidates the cached `IMMUTABLE_RULES` prefix. The prefs ride the
  existing step-1 guard read, so a turn costs no extra statement.
- **only_when_asked is bounded.** DIAGNOSTIC and REVIEW-GAPS still call
  `ask_check_questions` on their own, and finishing a multi-set check the
  learner already started does not count as unprompted.
- **reply_length is guidance only.** No token cap; `thorough` overrides the
  base "Be concise" rule.

## 2026-09-24 - Check-question sets: diagnostic grading and learner stop (#340)

Departs from two points of the #339 resolution, decided while reviewing
PR #366.

- **Diagnostic is 1-3 sets, tutor's choice.** #339 point 5 fixed the
  diagnostic at 3 sets of 3. The tutor now picks `set_total`: 1 for a narrow
  topic, up to 3 when the topic has distinct subtopics worth sampling.
- **Diagnostic level graded once, over every set.** #339 point 4 keeps
  grading per batch. Grading the level from set 1 alone would have placed
  the learner on one subtopic's 3 items, while sets 2-3 ran as ordinary
  checks and wrote mastered/gap entries for subtopics never taught. Now the
  current-check pointer carries `purpose`, so later sets stay diagnostic (no
  mastery effects), and a running `diag` score. The level is written when
  the final set resolves, or when the learner stops or the session ends
  mid-check. Items a stop leaves unreached count as skipped, and skipped items
  stay in the denominator exactly as a Skip click does (#339 point 8, "early
  stop = skip"). An all-skip diagnostic still leaves the
  level unset (F-25).
- **Chat clarifies; the Stop button stops.** #339 point 8 left "the learner
  stops" open. The composer stays enabled and the card stays open while the
  learner chats, so a chat message never ends a check: the tutor sees the
  open question (stem and options, never the answer) and may clarify its
  wording without hinting. A "Stop check" button on the card calls
  POST /sessions/{id}/check/stop, which grades the rest of the open set as
  skipped and streams the results turn like /check/complete. Considered and
  rejected: "any message stops the check" plus an "Ask about this" button,
  which would have killed a check on every clarifying question typed into the
  normal composer.

## 2026-09-23 - Shell, chat and settings redesign

Replaced the broken half-tab sidebar toggle, the identity-less sidebar foot,
the two-stocks thread and the four-tab Settings with the Card Box's rail,
identity row, tutor-on-desk and three-tab Settings. Tickets 01-10, this repo's
`.scratch/shell-settings-redesign/`.

- **Icon rail over full hide.** Folding no longer hides the sidebar to a bare
  strip; it folds to a 3rem icon rail (ChatGPT-style) carrying the drawn
  "sidebar" toggle, New session, Search, Review (with due count), one dot per
  session, then the foot (Settings, identity initial). The old half-tab
  chevron overlapped the centred Crux mark at 3rem with neither cleanly
  clickable; the drawn toggle now sits in the head, above the mark when
  folded, so the two never share space. Ctrl+B, the persisted
  `crux.sidebar.expanded` key, the 60/40 widths and the mobile top strip /
  drawer are unchanged — only the toggle glyphs moved.
- **Identity row and user menu replace Sign out.** The sidebar foot now shows
  a 28px initial circle (card stock, 1px card edge, blue initial at 700)
  plus the display name, opening a lifted user-menu card (name, email,
  Account, Sign out) on click or keyboard. Root cause of the blank-identity
  bug: `stores/user.js` writes the literal string `'Learner'` when the
  learner leaves the display name field blank (`completeOnboarding` and
  `updateProfile`), so the identity row treats that placeholder as unset and
  falls back to the sign-in email. The store still writes the placeholder;
  a follow-up should stop writing it so `'Learner'` isn't baked into
  `display_name` rows that a future surface might render verbatim.
- **Account is its own route, not a Settings tab.** `/account` holds display
  name (with save and saved-flash), read-only email, password change and
  delete-account, styled in the same Settings-sheet grammar
  (`frontend/src/assets/sheet.css`, shared with `SettingsView.vue`) so the
  card shell, `.sec`, `.saved-flash` and `.skel-block` furniture are declared
  once. `/settings/profile` redirects to Learning; `/settings/account`
  redirects to `/account`. The Account page is a single column top to
  bottom (Account, Security, Danger sections stacked); the old Settings
  two-column-from-60rem grid was dropped rather than carried over, since
  password fields and the delete section read better in one line of sight
  than split across columns.
- **Tutor on the desk, not a second card stock.** The "Two Stocks Rule" is
  gone: `AssistantBubble.vue` renders the pencil head line and body flat on
  the desk (no edge, no drop, no stock) at the same 78% measure (92% under
  600px) the tutor card used; the landed tick, tool-activity aside,
  citations and typing dots keep their slots. The learner keeps its blue
  card unchanged. `MessageList.vue` grows the gap to 1.5rem only at a
  change of voice (`speakerChangeAt`), 0.75rem within one voice. Inline
  code chips now sit directly on the desk with no card to frame them; the
  Impeccable pass should confirm whether they read cleanly without a border
  or need one added.
- **Session action bar: 56px, shared handlers.** `SessionHeader.vue` is now
  a 56px bar with a 1px `card-edge` rule below it (was 72px, no rule, no
  actions). Left: topic link, level mark/word, middot, started. Right: 28px
  drawn icon buttons for Rename, Pin, End (Resume when ended), plus an
  8px reference-file status dot. Rename/pin/end/resume were lifted out of
  the sidebar row menu into `composables/useSessionActions.js` so the header
  and the sidebar row call the same implementation; End is disabled while
  `streaming` is true, since `store.endSession` never aborts an in-flight
  reply. The status dot reads the same `useReferencePoll` aggregate as
  `ReferenceStatusBanner`, mapping its `'pending'` value onto the header's
  `'processing'` vocabulary (`'ready'`/`'failed'`/`null` pass through).
- **Usage chart choices.** The today meter's soft/urgent/hard ticks are
  positioned as a fraction of the hard cap (`pctOfHard`), since hard is the
  only cap guaranteed non-zero. The seven-day chart draws past days in a new
  `--chart-bar-past` token (light `#5a78c2` / dark `#5570ad`, both clearing
  3:1 non-text contrast on `--desk-deep`, asserted by `tokenContrast.test.js`)
  and today in `--color-accent`, not `--color-accent-strong` as the spec
  named — in the dark theme `accent-strong` (3.16:1) reads fainter than the
  past-day token, which would make today the least prominent column instead
  of the most. The ledger rows stay the one accessible table; the SVG is
  `aria-hidden`.
- **Learning tab reads the aggregate endpoint.** `LearningTab.vue` calls
  `GET /profile/aggregate` for the per-topic overview, a weekly mastery
  series and a concept accuracy list. The server always returns 12
  zero-filled weekly points (`profile_insights.py`), so the tab gates its
  empty state on `total_sessions === 0`, not on array length, and shows
  "none yet" per section when every point is zero. Concept accuracy shows
  the 3 least- and 3 most-accurate concepts (server-sorted ascending, so
  the two slices are the array's head and tail). Grading ticks and crosses
  on the accuracy rows use `--ink-marker`, the same correctness exemption
  from the tab law that check-card grading already uses.
- **Delete account (`DELETE /api/me`).** 503 before touching any row when
  `admin_configured()` is false (checked against `supabase_secret_key` /
  `supabase_url`, not a new setting — the spec called for "a new
  service-role setting", but the repo already has one under a different
  name: `supabase_secret_key` replaced the legacy `service_role` key
  end-to-end, see `services/supabase_admin.py`). `services/user_service.py
  delete_user_account` deletes in one transaction in explicit FK order —
  chunk embeddings, documents, learning events, chat messages, LLM call
  log, usage counter, daily cost ledger, session rows (topic profiles are a
  JSON column on the session row, not a separate table, so they go with
  it), then the user row — commits, then best-effort deletes the object
  store blobs, then calls the Supabase GoTrue admin API to delete the auth
  user. A failure at the auth step after commit returns 503 naming that
  step (`"app data deleted; auth user removal failed"`); the frontend
  matches that literal string to show a retry-safe message instead of raw
  backend prose, and does not sign the learner out, since the delete is
  idempotent and a retry can finish the job. Known gap: between the app-data
  commit and a successful auth-user delete, the learner's still-valid JWT
  plus `ensure_user`'s lazy row creation could recreate an empty `users`
  row on any authenticated request; mitigated by the client signing out
  immediately on success, but not closed for the failure path until the
  auth step succeeds or the token expires. Object storage keys are per
  document (`object_store.key_for(doc_id, filename)`), not a per-user
  directory, so deletion iterates the user's document keys rather than
  removing one directory.
- **Rejected:** a keyboard shortcut reference card, and an in-app
  reduced-motion toggle (the OS-level `prefers-reduced-motion` media query
  already drives every animation in the build).
- **Process note:** destructive confirm buttons (`.confirm-delete-strong`)
  were painting PrimeVue's default blue inside `crux-dialog` and
  `p-confirmdialog` footers — a `(0,2,0)`-specificity PrimeVue rule beat the
  app's own selector. Fixed once in `frontend/src/assets/dialogs.css` with a
  `(0,5,0)` override covering both dialog contexts, rather than per-caller.

## 2026-09-23 - Archived the executed QA re-triage, the 10x roadmap, and the branch-protection script

Removed from the working tree. Everything is recoverable with
`git show c2ef3db:<path>` (last commit on `dev` before the removal).

| Path | What it was | Why removed |
|---|---|---|
| `docs/planning/2026-09-19-qa-retriage.md` | Re-verification of all 107 findings from the 2026-08-06 QA audit: 30 FIXED, 1 OBSOLETE, 1 ACCEPTED, 75 open (62 STILL + 13 PARTIAL) | All 75 open items were closed via waves 1-4 (issues #320-#326, #330, #331; PRs through #334, 2026-09-19 to 2026-09-21). Per-wave deviations are recorded in the entries below. |
| `docs/superpowers/plans/2026-09-19-qa-wave-{1,2,3,4}.md` | Executor plans for the four waves | Executed and merged. Same precedent as the 2026-07-12 slice-plan removal. |
| `docs/planning/2026-07-06-10x-roadmap.md` | Post-v1 roadmap (tracks R/P/D/S, dead-code audit, sequencing) | Status EXECUTED since 2026-07-12; slices 1-8 merged via PRs #106-#114. Only R5 remained; its acceptance criteria are preserved below so the demand gate survives the removal. |
| `docs/deploy/enable-branch-protection.sh` | W-07 script to apply branch protection + code-scanning default setup | Protection is now live on `dev` and `main` (verified via `gh api` 2026-09-23). Supersedes the 2026-09-19 note "W-07 deferred, not done". |

**Branch protection as actually configured** (diverges from the Phase 6 plan in
`docs/security/CI_INVENTORY.md`, which now records the live state):

- `dev`: required checks `Backend (pytest)`, `Frontend (Vitest + lint)`,
  `Security (SAST + deps + secrets + images)`, `Analyze (javascript-typescript)`;
  1 approving review required (maintainer merges with `--admin`);
  `enforce_admins` off.
- `main`: same checks plus `Analyze (python)`; no review requirement;
  `enforce_admins` off; signed commits required.
- `Playwright (chromium)` is not a required check on either branch (e2e is
  advisory; it runs on push/PR but does not gate merge).
- GitHub code-scanning *default setup* is `not-configured`; the `Analyze (*)`
  checks come from `.github/workflows/codeql.yml` (advanced setup). GitHub does
  not allow both, so enabling default setup would require removing the
  workflow first. The deleted script's default-setup PATCH was never run.

**R5 - Practice exam mode (demand-gated; do not build without user demand).**
Generate a timed, mixed practice exam from a session's uploaded documents plus
its gap list, reusing the existing check-batch machinery (batches of 1-5, MC,
server-graded).
- AC1: "Practice exam" action on sessions with a ready document: N questions
  (configurable 5-15) drawn to cover confirmed gaps first, then document
  keyword coverage; generated via one agent call using `ask_check_questions`
  batching (multiple sequential batches, no new grading path).
- AC2: Exam summary card: score, per-gap breakdown, wrong answers feed
  `learning_events` exactly like normal checks (so R2/R3 pick them up free).
- AC3: Cost-guard: exam generation respects the hard cap pre-check and shows
  estimated cost before starting.
- AC4: Live-LLM smoke checklist written (paid gate) before merge, matching the
  project's owed-smoke convention.

**Kept on purpose:** `docs/Crux_Spec.md` and `docs/Crux_DevPlan.md` (historical
v2 reference, listed in CLAUDE.md read order), `docs/deploy/ngrok.md` (still the
local public-demo path referenced by `docker-compose.prod.yml` and the READMEs),
`docs/dev/debug-accounts.example.txt` (template consumed by
`backend/scripts/seed_debug_accounts.py`), `docs/security/CI_INVENTORY.md`
(living CI rationale, updated this pass).

## 2026-09-21 - Issue #331: backend ETag (F-18 backend half)

- **Middleware, not per-route logic.** One allowlist of path prefixes
  (`/api/sessions`, `/api/profile`, `/api/review/queue`, `/api/usage/summary`)
  covers every hot GET with zero route churn -- no decorator, no response-model
  change, nothing for a new sibling route under those prefixes to remember. It
  also makes the SSE exemption structural rather than a convention: the layer
  filters on GET/HEAD, so the streaming POSTs (`/api/chat/stream`,
  `/api/sessions/{id}/check/complete`) are forwarded message-by-message and
  cannot be buffered even by mistake.
- **Pure ASGI, not `BaseHTTPMiddleware`.** Same reason as `lib/request_id.py`,
  `lib/body_limit.py` and `lib/error_handlers.py`: `BaseHTTPMiddleware` wraps
  every response in an anyio stream and would break SSE for the whole app.
- **Strong sha256 of the body, not `updated_at`.** Several hot GETs aggregate
  rows the caller never names -- session detail folds in the profile, the
  message page, the pending check and ingestion status; the usage summary folds
  14 days of ledger plus top sessions. A max-`updated_at` tag would need
  per-model plumbing on every one of them and would still miss a derived field.
  Hashing the serialised body is exact by construction and costs one sha256
  over an already-materialised payload. The tag is strong (no `W/`) because it
  is byte-exact; comparison on the request side is weak, per RFC 9110.
- **`cache-control: no-cache` on every tagged 200.** "Revalidate before reuse",
  not "do not store". Without a freshness header the browser heuristically
  reuses an ETag-bearing body without asking, and the `If-None-Match` this
  whole layer exists to answer never gets sent. A route that already set its
  own `Cache-Control` is left alone.
- **Registered between `BodySizeLimit` and `UnhandledError`.** That slot puts
  it inside `UnhandledErrorMiddleware` (a bug in the new layer surfaces as a
  coded 500, not a bare crash) and inside `CORSMiddleware` (a 304 carries
  `access-control-allow-origin`, so the browser can read it). `If-None-Match`
  and `ETag` had to be added to `allow_headers` / `expose_headers` -- neither
  is CORS-safelisted.
- **Not the body `etag` on the profile.** `profile_service.profile_etag` stays
  a body field used for `If-Match` optimistic concurrency on profile writes.
  Deliberately not unified with the HTTP header: they have different lifetimes
  (the body tag covers the profile only, the header covers the whole response)
  and conflating them would make a profile write's 412 depend on unrelated
  fields like `recent_learning_events`.

## 2026-09-21 - QA re-triage Wave 4 (issue #326): triage and deviations

- **A-01**: access tokens are stateless JWTs with no revocation primitive
  (`token_valid_after` / `denylist` / `jti` / `revoke` grep to zero hits in
  `backend/`); `backend/services/auth.py` verifies signature, `exp`, `aud`
  and `iss` only. Logout or a ban therefore takes effect only at the next
  access-token expiry, not immediately. Worst-case residual window = the
  configured access-token TTL, left at the Supabase default of **~1 hour**
  (`docs/auth/supabase-setup.md` section 8: "Leave the access token (JWT)
  expiry at its default (~1hr)"). Refresh tokens ARE revoked server-side by
  Supabase on sign-out, so a stolen refresh token cannot mint new access
  tokens post-logout; only the already-issued access token still works, and
  only until it expires. Accepted as-is: a revocation list is a feature, not
  a Wave 4 docs fix.
- **B-08**: the Render blueprint's cap tiers (soft 0.80 / urgent 0.90 / hard
  1.00; `cost_meter.py:213` derives urgent as `hard_cap * 0.9`) left only
  0.10 USD between soft warning and hard cutoff, too tight to act on. The
  hard cap is untouched (changing user-facing spend behavior is out of scope
  for a docs wave); only the blueprint's `LLM_SOFT_CAP_USD` in `render.yaml`
  drops to `0.50`, making the tiers 0.50 / 0.90 / 1.00. `backend/config.py`
  local/dev defaults (2.00 / 3.00) are unchanged and remain the source of
  truth outside the Render deploy target. See "Cost cap tiers" in
  `docs/reference.md`. These are blueprint values, not confirmed deployed.
- **C-14 deviation**: the recommended fix mapped service-layer `ValueError`
  to 409/422. Shipped 422 only, and only for the exact `ValueError` type;
  subclasses (pydantic `ValidationError`, `json.JSONDecodeError`) fall through
  to the coded 500 because an escaped one is almost always corrupt stored
  data, not a rejected input. 409 stays route-owned (If-Match / conflict paths
  already raise it explicitly).
- **G-13 wontfix**: `run_streaming` is a ~494-line generator with metering,
  partial-persist and tool dispatch interleaved across `yield` points.
  Extracting three seams is a behaviour-neutral refactor with a large
  regression surface (streaming order, abort persistence, cost double-count
  guard at `tutor.py:591-600`) and only a readability payoff. Revisit when a
  feature next touches `run_streaming`; do it then under that feature's
  tests.
- **Triage** (19 items from `docs/planning/2026-09-19-qa-retriage.md`, 17 fixed
  in this PR, 1 already fixed by Wave 1, 1 wontfix): A-01 fix, docs only (above). B-08 fix, docs
  + blueprint soft cap (above). C-14 fix, global exception handlers with
  `X-Request-Id` (Task A). C-15 fix, `documents.status` / `chat_messages.role`
  CHECK constraints (Task B). C-16 fix, `created_at` NOT NULL + server
  default (Task B). C-17 fix, `q` search param length cap and LIKE escaping
  (Task A). C-18 fix, tie-break ordering on `chat_messages` queries (Task A).
  D-21 fix, visually-hidden session `h1` fallback (Task C). D-22 fix, resting
  underline on the topic link (Task D). D-25 fix, composer Skip button
  removed (Task C, with E-20). E-15 fix, stuck "still processing" chip
  cleared on timeout (Task C). E-17 fix, check-question double-submit guard
  (Task C). E-18 fix, `ProfileView` reloads on id change (Task D). E-19 already
  fixed by Wave 1 E-01 (919d3a0: `startQuick` awaits inside try/catch and
  shows the error inline), no change. E-20 fix, dead `checkLocked`
  computed removed (Task C). F-20 fix, `useTheme` media-query listener leak
  (Task D). F-21 fix, optimistic chat row keyed by `client_id` (Task C).
  G-13 wontfix (above). G-14 fix, `profile_insights` split out of
  `profile_service` (Task A).

## 2026-09-20 - QA re-triage Wave 3 (issue #325): deviations from the recommended fixes

- **F-18 split: frontend half only.** The retriage asked for HTTP `ETag` /
  `If-None-Match` on hot GETs plus client retry and cache. The wave is
  frontend-only, so `apiClient.js` got the bounded GET retry (network errors and
  502/503/504 only, never for writes) and a 5 s in-memory GET cache; the server
  `ETag` is issue #331. The cache key is url **plus access token** and is cleared
  on auth expiry, because a sign-out/sign-in inside the TTL would otherwise serve
  account A's `/sessions` to account B. `getSessionProfile` bypasses the cache:
  the tutor writes the profile server-side mid-turn, which path-prefix
  invalidation cannot see, and a stale body ETag would 412 the next write.
- **F-16: cap on live append only.** `MAX_RETAINED_MESSAGES = 200` evicts from
  the top when a new message is appended and re-arms `hasMoreMessages`; a manual
  "load earlier" prepend is exempt, since dropping "the oldest page" there would
  evict what the user just asked for. The load-earlier cursor is the oldest
  retained server id, so eviction and paging line up.
- **D-16: `aria-controls` only on the selected tab**, not all four panels
  rendered hidden. Rendering every panel would defeat the `<KeepAlive>` that E-10
  relies on for refetch-on-reactivate.
- **E-08: writes serialised, not rejected.** The plan said both "ignore
  re-entrant calls" and "chain onto the previous ETag"; the profile view queues
  writes and threads each response's ETag into the next. Buttons are disabled
  while writing; the add-concept input stays enabled so Enter can queue several.
- **F-17 nginx: `map` + server-block `add_header`**, not `expires` inside
  `location /assets/`. An `add_header` in a location block drops every
  server-level header (CSP, HSTS, X-Frame-Options) for that location, which is
  an nginx inheritance trap; the map keeps one `Cache-Control` and all security
  headers. Same value as `vercel.json`: `public, max-age=31536000, immutable`.
- **F-15: list and indented-code closes are never a cache boundary.** markdown-it
  re-opens a list across a cut, so a cached head ending on
  `bullet_list_close` / `ordered_list_close` / `code_block` falls back to a full
  render. Parity with the full render is byte-identical across the fixture set
  and asserted in `markdownIncremental.test.js`.
- **E-12 / E-08 confirm dialogs reuse the file-delete contract**
  (`ReferenceStatusBanner.vue`): neutral text cancel, `confirm-delete-strong`
  accept, no icon.

## 2026-09-20 - QA re-triage Wave 2 (issue #324): deviations from the recommended fixes

- **F-10: no `chunk_embeddings.doc_ready` column.** The recommended
  denormalisation buys little: the join to `documents` stays for `filename`, and
  the status predicate is a PK-joined filter per candidate. pgvector 0.8.0 (live
  on Supabase) fixes the filtered-HNSW under-fetch directly with
  `hnsw.iterative_scan`, so the fix is `SET LOCAL hnsw.ef_search` +
  `iterative_scan = strict_order` on the search transaction. Partitioning stays a
  note in `docs/reference.md`. Owed: live EXPLAIN smoke.
- **F-09: no `learning_events (created_at, id)` composite.** Wave 1's 0025 added
  `(created_at)`; the review query filters `created_at >= window` over
  `session_id IN (...)` and the composite would not change the plan. Only the
  `chat_messages (session_id, id DESC)` index was added (0027).
- **C-11: enumerated human-readable strings, not codes.** `documents.error` is
  rendered verbatim by `ReferenceStatusBanner.vue` and `SessionView.vue`, so the
  value stays readable but is drawn from a fixed frozenset; only the raw
  exception text was removed. No contract or frontend change.
- **B-05: reservation instead of a row lock.** A `SELECT .. FOR UPDATE` in the
  gate releases at the gate's own commit, before the LLM call, so it cannot close
  the burst window. A provisional per-turn charge (`LLM_TURN_RESERVE_USD`, 0.02)
  added atomically at the gate and released at turn end does. Cost: the ledger
  reads 0.02 high during a turn; a crash mid-turn leaves it until midnight.
- **G-07: Render health check repointed to `/ready`.** A Supabase outage now
  fails the instance health check (Render restarts the instance) instead of
  serving 500s while "healthy". Takes effect at the next deploy.
- **F-19: `PyJWKClient(cache_jwk_set=True, lifespan=3600)` pinned** rather than
  inheriting PyJWT's 300 s default, which refetched JWKS 12x per hour behind the
  app's own 1 h cache.
- **Q-03: ruff backlog folded into the wave PR**, not a dedicated PR as the
  retriage suggested: import sorting after the fact would conflict with every
  file the wave touched. Ruleset `E,F,B,I`, ignore `B008` (FastAPI `Depends`
  defaults) and `E501`.
- **Q-05 stays open for the repo owner**: branch protection is a GitHub UI
  action (`docs/deploy/enable-branch-protection.sh`), not code.

## 2026-09-19 — Archived finished reviews, audits, and the Phase 0 spike

Removed from the working tree. Everything is recoverable with
`git show 1d0f4aa:<path>` (last commit on `dev` before the removal).

| Path | What it was | Why removed |
|---|---|---|
| `spike/` | Phase 0 validation spike: scripts, profiles, six committed transcripts, `decision.md` | Gate passed 2026-05-04. Never imported by app code, excluded from Docker, not in CI. Scripts referenced ADK and gemini-2.5, both long gone. Verdict preserved below. |
| `docs/reviews/2026-07-24-security-and-code-review.md` | Full-codebase review, 0 vulns, 1 Important | Only finding (upload-poll race) merged via PR #159. |
| `docs/reviews/2026-07-25-owed-smokes-ledger.md` | Ledger of owed live gates from PRs #106-#159 | Closed gates are evidenced in PR bodies. The PARTIAL items (ENV=prod compose smoke, HNSW re-EXPLAIN) and the still-open audit gates W-03/04/05/08/13 now live in `docs/deploy/RUNBOOK.md` step 7. |
| `docs/reviews/2026-08-06-qa-audit/` | 107-finding QA audit: `qa-report.md`, `_raw/A-G`, `bug-tracker.csv`, `deployment-checklist.md`, `improvements.md`, evidence JPGs | Verdict READY-for-closed-beta 2026-08-07. Remediation landed via PRs #215-#219 and the 2026-09-02 batch. Note: the CSV status column was never re-triaged after remediation, so 106 rows still read "Open" in git history; treat the CSV as the audit-time snapshot, not a live tracker. Deploy-time gate W-15 ported to `docs/deploy/RUNBOOK.md` step 2. |
| `docs/security/SECURITY_REVIEW.md` | 2026-05-23 audit, 12 findings H-1..L-2 | All resolved and re-verified 2026-06-22. H-3 request-size caps are locked by `backend/tests/test_max_length_validation.py`. |
| `docs/security/SECURITY_REVIEW_2026-06-22.md` | Addendum, 6 findings | All fixed by 2026-07-11 (vercel.json headers, JWT `iss`, JWKS fail-fast, S1 delimiter escaping, S2 rate-limit bypass). Live CSP curl verification is a deploy-time gate in RUNBOOK step 7. |
| `docs/screencast/script.md` | 2-3 min walkthrough script | Screencast never recorded (open since Phase 5). README linked a video that never existed. Record from the git-history script if the screencast is ever picked up. |

Kept on purpose: `docs/security/CI_INVENTORY.md` (living "why is this CI job
here"), `docs/deploy/enable-branch-protection.sh` (W-07 deferred, not done),
`docs/deploy/ngrok.md` (still the local public-demo path referenced by
`docker-compose.prod.yml`).

## 2026-05-04 — Phase 0 spike: profile differentiation validated

Question: do two hand-crafted learner profiles produce structurally different
tutor responses on the same topic, at turn 1 and still at turn 8? This was the
blocking gate for the whole premise (design doc section 7, Phase 0).

Method: three A/B pairs over database normalization, each run for 8 turns
through the immutable-rules prompt with a static profile injected.

| Pair | Model | Turn 1 differs | Turn 8 differs | Result |
|---|---|---|---|---|
| Knowledge level (beginner vs advanced) | gemini-2.5-flash | Yes, clear | Yes, clear | PASS |
| Guidance preference (hints vs direct) | gemini-2.5-flash-lite | Marginal | Yes, clear from turn 4 | WEAK PASS |
| Engagement (quiz-as-we-go vs absorb-then-test) | gemini-2.5-flash-lite | No | Subtle | MARGINAL |

Verdict: knowledge-dominant pass. Per the DevPlan matrix this is strictly
"Knowledge only", but pairs 2 and 3 ran on the lite model after the daily
flash quota ran out, so their result is a lower bound.

Decision: proceed to Phase 1 and 2 with `interaction_preferences` retained but
flagged for re-validation on the production model in Phase 3. That
re-validation was never formally recorded; Phase 3 shipped, the field stayed,
and later prompt audits (2026-09-10) treated guidance and engagement steering
as working. Treat the flag as closed by usage, not by measurement.

Side finding: the model attempted `update_topic_profile` calls in plain text
before any tool was registered, which is what justified betting on native
tool-calling for Phase 2.
