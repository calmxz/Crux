# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the glossary / ubiquitous language for this project.
- **`docs/decisions.md`** — ADR-lite decision log, one dated section per decision. Read the sections that touch the area you're about to work in. This repo uses a single file, not a `docs/adr/` directory.
- **`docs/reference.md`** — technical reference (how things work, gotchas, conventions). Not a decision log; look here for "how", look in `decisions.md` for "why".

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

## File structure

Single-context repo:

```
/
├── CONTEXT.md
├── docs/
│   ├── decisions.md      <- ADR-lite log (append a dated section per decision)
│   └── reference.md      <- technical reference, organized by topic
├── backend/
└── frontend/
```

When a skill says "write an ADR", append a new section to `docs/decisions.md` in the existing format rather than creating a file under `docs/adr/`.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing decision in `docs/decisions.md`, surface it explicitly rather than silently overriding:

> _Contradicts decision "event-sourced orders" (docs/decisions.md, 2026-05-10) — but worth reopening because…_
