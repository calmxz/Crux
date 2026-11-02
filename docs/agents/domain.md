# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root — the glossary / ubiquitous language for this project.
- **`docs/spec/`** — the Crux v1 spec: the current rules. Read `docs/spec/README.md` (shared rules and the index of area files), then the area files that touch the area you're about to work in. The reasons live in the closed tickets each section links, on the pinned wayfinder map, and later in `spec-change` issues. There is no `docs/decisions.md` for v1.
- **`docs/reference.md`** — technical reference (how things work, gotchas, conventions). Look here for "how", in `docs/spec/` for the rules, and in the linked tickets for "why".

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill adds glossary terms as they get resolved; rules go into `docs/spec/`.

## File structure

Single-context repo:

```
/
├── GLOSSARY.md
├── docs/
│   ├── spec/             <- v1 spec: README.md (shared rules, index) + one file per area
│   └── reference.md      <- technical reference, organized by topic
├── backend/
└── frontend/
```

When a skill says "write an ADR", don't create one. Until the spec is locked, a decision is a ticket on the wayfinder map; after the lock, it is a `spec-change` issue the owner decides. Either way, the resolution edits `docs/spec/`.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag spec conflicts

If your output contradicts a rule in `docs/spec/`, surface it explicitly rather than silently overriding:

> _Contradicts `docs/spec/mastery-check.md`, "Disputes" (from #669) — but worth reopening because…_

Don't invent a missing rule; see `docs/spec/spec-process.md` (until it is written, #680's resolution).
