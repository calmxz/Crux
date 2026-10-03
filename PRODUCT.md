# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: a student studying alone from their own course PDFs. Evening or library desk, laptop, long focused sessions, returning to the same topics over weeks (confirmed 2026-09-10). Self-learners working through a textbook share the same job.

Secondary (README, not a design priority): educators and EdTech researchers evaluating tool-augmented LLM tutors with verifiable state. Portfolio evaluators see the app, but the learner's task comes first.

## Product Purpose

Crux is an adaptive AI study companion. The learner picks a topic, optionally drops in reference files (PDF, PPTX, TXT, MD), and holds an ongoing conversation with a tutor agent. Every turn the agent updates a structured profile of what the learner knows, and the next question is conditioned on that profile rather than a blank slate.

Success: the learner leaves a session knowing what they mastered and what the one gap worth working on is, and comes back over weeks because the tutor remembers.

## Positioning

The tutor's memory is structured and verifiable, not a chat transcript. Mastery is only recorded when declared or tested; the server grades check questions deterministically and writes learning events; the agent cannot silently clear its focus gap. No hallucinated mastery, no silent context loss, no fabricated citations. A generic chatbot cannot truthfully claim this.

## Operating Context

- **Sessions** are per topic. Active sessions resume with the profile carried forward; ended sessions get an LLM summary and become read-only until resumed.
- **Per-topic profile:** knowledge level, confirmed gaps, mastered concepts, one focus target gap, per-subtopic levels, evidence provenance (declared vs tested).
- **Check questions:** the tutor registers a batch of 1 to 5 multiple-choice items; the learner answers in the chat; the server grades; a recap card shows score, the learner's answer, the correct answer, and explanations. Correct answers promote a gap to mastered; an incorrect retest demotes.
- **Retrieval:** uploaded files are chunked and embedded; answers cite page and document name. An ingestion status banner shows processing state.
- **Streaming:** tutor replies stream token by token with a stop control. Math renders via KaTeX; code via highlight.js.
- **Recall:** spaced-repetition queue across sessions with streaks.
- **Insights:** aggregate profile across sessions (mastered, gaps, subtopic levels), usage and spend.
- **Onboarding:** display name and feedback style (hints vs explain outright). A diagnostic consent card inside the first session asks for a self-assessed level.
- **Limits:** per-user daily LLM cost cap surfaces as banners and toasts.
- **Legal:** terms of service and privacy policy pages, consent at registration.

## Capabilities and Constraints

- Vue 3 + Vite, Pinia, vue-router, PrimeVue 4 (InputText, Toast, ConfirmDialog, dialogs, teleported overlays), PrimeIcons, markdown-it + KaTeX + highlight.js. FastAPI backend; the API contract is `docs/api/openapi.yaml` and is not a design variable.
- Function, copy semantics, routes, store contracts, `data-testid` hooks (216 unique) and aria attributes are load-bearing: 870 vitest unit tests and Playwright e2e suites assert them. A redesign replaces look and layout, not behavior or test hooks.
- Dark and light themes both exist today via `data-theme` and are user-selectable in Settings. Whether both survive is open (user declared everything visual open on 2026-09-10); dropping one is a product decision to surface, not to take silently.
- Accessibility is already engineered (skip link, roving tabindex, live regions, inert drawers, AA-corrected accent text); the redesign must not regress it.
- Mobile web at 390px is a supported viewport (sidebar becomes a top strip and drawer).
- ASCII only in script output; no emojis in code or comments.

## Brand Commitments

None binding. The product name is Crux. The current four-point star mark, coral accent, Bricolage Grotesque / Inter / IBM Plex Mono faces, and slate-and-paper palette are the incumbent look and are explicitly open for replacement (user, 2026-09-10).

## Evidence on Hand

- Real product copy across all routes (`frontend/src/views`, `frontend/src/components`).
- Real learner-profile data shapes in `backend/db/schemas.py` and `docs/api/openapi.yaml`.
- Legal texts in `frontend/src/legal/`.
- No testimonials, customer logos, benchmarks, or pricing exist. Do not invent them.

## Product Principles

1. The learner's task outranks expression: reading a tutor reply, answering a check, seeing what changed in the profile.
2. The profile is the product. What the tutor knows about you should be legible as a designed artifact, not a row of chips.
3. Honesty over flattery: mastery appears only when earned; ended sessions read as completion, not restriction.
4. Long sessions must stay comfortable for hours on a laptop; every state (streaming, grading, ingesting, capped, ended) is visible without being loud.
5. Nothing the backend cannot verify gets a visual claim.

## Accessibility & Inclusion

WCAG AA contrast on all text in both themes (enforced by a vitest contrast assertion on tokens). Keyboard-complete: composer shortcuts, roving tabindex rails, focus-visible rings, screen-reader status announcements for streaming and grading.
