# Coding Standards

Judgement calls for the reviewer. Mechanical rules (formatting, lint, banned patterns) live in oxlint, ruff, prettier, and CI, not here. Each rule below was flagged by a reviewer on a real PR.

## The backend is Python 3.14

Judge backend syntax against Python 3.14 (`backend/.python-version`). An unparenthesized `except TypeError, ValueError:` is valid there (PEP 758) and is what `ruff format` writes for the py314 target; it is not a SyntaxError. (#620: a security review flagged 11 reformatted files as unparsable.)

## Comments track the code

When a diff renames, moves, or changes the behaviour of a symbol, every comment that names or describes it is updated in the same diff. Check comments near the change and comments elsewhere that mention the old name. (Stale comments reached review on #400, #443, #459.)

## Invariant comments hold on every exit

A comment that states an invariant ("only X writes this", "true while Y") is checked against every way out of the code it describes: success, failure, early return, and `reset()`. Name the exit that would break it, or confirm none does. A comment copied from an issue's invariant line is held to the code, not to the issue. (#532: "true exactly while a list runs" missed the re-list and `reset()`; its rewrite missed the failure path; each reached a later review.)

## One idiom per concern

A concern that already has a helper or documented pattern uses it; a diff adds no second way. Before accepting a hand-rolled guard, check `docs/reference.md` for an existing pattern. Example: async actions in `stores/session.js` gate writes with `_epochGuard()` / `live()` and report errors through `_setError(e, live)` (see "Reset epoch (#414)"), never with an inline epoch comparison.

When a diff repeats the same guard by hand in three or more places, flag it as a candidate for a shared helper rather than blocking the PR.

## Fakes prove what ran

A test fake records each call, and the test asserts on that record. A fake that only raises on an unexpected call proves nothing when the code under test catches broad exceptions: the tutor, the summaries and the metering paths turn the raise into a fallback, and the test stays green. Where a test claims to pin which input was used (which text was billed, which prompt was sent), the fake's return depends on that input; a constant return cannot tell two inputs apart. (Both reached review on #410.)

## Failures are injected beneath their handler

A test that injects a failure patches the call that fails in production (the SQL statement, the provider call), underneath any handler that catches it, so the handler runs. Patching the function that does the catching replaces the handler too, and a path that swallows the error goes untested. (#569: case A patched `retrieve` wholesale and passed, while the real `retrieve` swallowed its query error and still broke the next tool; the Spec review caught it.)

## Every test can go red

For each test the diff adds or edits, name the product-code line whose breakage would turn it red. A test with no such line is vacuous: it sets state the component never reads, or asserts something true whatever the code does. Fix it or delete it. A rename that touches a test re-asks this, since renaming can leave a test pointing at nothing. (#532: a HomeView test set the sidebar list flag, which HomeView never reads; it passed the two-axis review and the bug-hunt review caught it.)

A test that asserts a printed or returned value seeds its inputs so every value the assertion could match is distinct. When two inputs are equal, the assertion passes whichever one the code reads. (#600: spend was seeded equal to the limit, so `"$0.5000" in out` passed whether the cost-stop message printed the spend or the limit; the two-axis review passed it and the bug-hunt review caught it.)

## A removed guard names its backstop's test

When a diff drops a check because another layer already enforces it, name the test that goes red if that layer's check is removed, and confirm it asserts behaviour: rows in, rows out. A test that inspects generated SQL text or a call's arguments is not a backstop. If no such test exists, the diff adds one. (#571: prefetch dropped its ready check on the strength of `test_query_chunks_filters_to_ready_documents`, which only checks the SQL string contains `documents.status`; the Spec review accepted it and the bug-hunt review caught it.)

## New writers check every reader

When a diff adds a writer to existing shared state (a store ref, a module-level variable), find every reader of that state and confirm each reader's assumption still holds: "non-empty means loaded", "this total mirrors these rows", "only X ever sets this". A reader that infers something from the state's shape breaks silently when a new writer changes that shape. (#522: a create that inserted sidebar rows broke a `sessions.length` "loaded" check and an `activeTotal` count; both reached review.)

## A display rule covers every surface

When a diff decides what the UI may say about a state ("never shows the account as empty until a list loads"), list every surface that renders that state and check each one in every reachable state (after a create, during a retry, after a sign-out): empty hints, rows, counts and totals, View all links, tab labels, alerts. A gate that fixes the hint but leaves the count still tells the learner the wrong thing. (#544: the error line replaced the empty hints, then the "View all N" link and the "Ended (N)" tab count each showed local-only totals; they surfaced in review rounds 3 and 4.)

## A self-removing control says where focus goes

When a control unmounts or is replaced as the result of its own activation (a Retry that turns into a skeleton, a menu item that closes its menu), the diff states where keyboard focus lands on success and on failure, and a test pins it with the element attached to the document. Focus left on the body sends a keyboard user back to the top of the page. (#544: Retry dropped focus to the body; the restore, then its pointer-press guard, took two review rounds.)

## Fixes reach every sibling path

When a diff adds a guard or fixes a case on one path, find the parallel paths that do the same job (the other copies an action patches, the success and failure branches, the replayed and the live write) and confirm each one gets the same treatment or has a stated reason not to. (#524: a rollback guard went onto rows a list had landed but not onto the observed copies one loop above; the bug-hunt review caught it.) A diff that replaces an existing guard with a different one covers every statement the old guard covered; list them before accepting the swap. (#569: a savepoint around one query replaced an except-arm rollback that also covered the commit before it; the next review reverted it.)

## Session totals changes walk the ordering matrix

A diff that changes how `stores/session.js` moves `activeTotal` / `endedTotal`, or what a landing list replays, is checked against every row of the ordering matrix in `docs/reference.md` ("Sidebar session window"). For each row, name the totals once everything settles, or the residue entry in `docs/decisions.md` that accepts them. Its store tests seed sessions with `seedSession`, which holds a session in every copy the store reads. A test that seeds only the window row is testing a state the app never holds. (#533: the brief called the in-window case "already exact" and the test seeded only the window row, so the open session's separate copy double-counted. The first review fix then missed the "landed, then a later list in flight" row. Both reached review.)

## A new await re-checks what follows it

When a diff adds an `await` inside an async store action, everything after it is checked as if a `reset()` or an overlapping action ran during that wait: each state write, the `finally`, and the value returned to the caller (the epoch contract covers returns too). A shared ref written in a `finally` must not clear a value an action started since has set. (#528: a follow-up fetch returned the reset store to its caller, and the list's `finally` cleared `loading` for a newer action; both passed the two-axis review and reached the bug-hunt review.)

## New patterns get a reference entry

A diff that introduces a convention other code must follow (a guard, a sentinel, a dedupe rule) adds or updates its section in `docs/reference.md` in the same PR.
