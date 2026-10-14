# Coding Standards

Judgement calls for the reviewer. Mechanical rules (formatting, lint, banned patterns) live in oxlint, ruff, prettier, and CI, not here. Each rule below was flagged by a reviewer on a real PR.

## Comments track the code

When a diff renames, moves, or changes the behaviour of a symbol, every comment that names or describes it is updated in the same diff. Check comments near the change and comments elsewhere that mention the old name. (Stale comments reached review on #400, #443, #459.)

## One idiom per concern

A concern that already has a helper or documented pattern uses it; a diff adds no second way. Before accepting a hand-rolled guard, check `docs/reference.md` for an existing pattern. Example: async actions in `stores/session.js` gate writes with `_epochGuard()` / `live()` and report errors through `_setError(e, live)` (see "Reset epoch (#414)"), never with an inline epoch comparison.

When a diff repeats the same guard by hand in three or more places, flag it as a candidate for a shared helper rather than blocking the PR.

## Fakes prove what ran

A test fake records each call, and the test asserts on that record. A fake that only raises on an unexpected call proves nothing when the code under test catches broad exceptions: the tutor, the summaries and the metering paths turn the raise into a fallback, and the test stays green. Where a test claims to pin which input was used (which text was billed, which prompt was sent), the fake's return depends on that input; a constant return cannot tell two inputs apart. (Both reached review on #410.)

## New writers check every reader

When a diff adds a writer to existing shared state (a store ref, a module-level variable), find every reader of that state and confirm each reader's assumption still holds: "non-empty means loaded", "this total mirrors these rows", "only X ever sets this". A reader that infers something from the state's shape breaks silently when a new writer changes that shape. (#522: a create that inserted sidebar rows broke a `sessions.length` "loaded" check and an `activeTotal` count; both reached review.)

## New patterns get a reference entry

A diff that introduces a convention other code must follow (a guard, a sentinel, a dedupe rule) adds or updates its section in `docs/reference.md` in the same PR.
