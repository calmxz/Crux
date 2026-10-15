# Durable reconciliation of unsettled LLM spend

Crux does not track, in the database, LLM spend that missed the daily cost
ledger, and runs no sweep to add it back later.

## What was asked

When the LLM adapter's settlement can't write `daily_cost_ledger`, it
commits the `llm_call_log` row on its own and retries the ledger write once,
5 s later, on a background timer (`services/llm.py` `_defer_ledger`). If that
retry never runs (a restart inside the window) or fails too, the spend is
missing from the ledger. The request was to close that gap durably: a
`ledger_pending` flag on the call log row, cleared when the ledger write
lands, plus a sweep that adds every pending row's cost to the ledger.

## Why this is out of scope

The ledger is a daily budget, not a bill. It exists to stop a user's
spending at the cap, and it resets at midnight UTC. A missed settlement is
one call's cost (fractions of a cent to a few cents), it only distorts the
cap until midnight, and the overcount-safe direction is already accepted
elsewhere. Actual billing is the vendor's invoice, not this table.

Against that, the guarantee needs a migration on an insert-heavy table, a
new background job with its own locking (`FOR UPDATE SKIP LOCKED`, so two
workers never count a row twice), and a cadence to run and monitor it. That
is a lot of permanent machinery for a bounded, self-healing error.

The gap is also observable without it: every deferral logs
`llm settlement deferred` at error level with the user, amount and day, and
a successful retry logs `llm deferred settlement landed`. A deferral with no
matching `landed` line is the missing spend, and can be fixed by hand if it
ever matters. Deferrals need a ledger row held for over 5 s, which no code
path does today (see `docs/reference.md`, "LLM adapter (#411)").

See `docs/decisions.md`, the 2026-09-27 B3 entry and its 2026-10-15
amendment.

## Prior requests

- #558: "Deferred LLM settlements leave a findable mark and a sweep adds them to the ledger"
