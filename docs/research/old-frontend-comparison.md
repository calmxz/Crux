# Research: how far the old frontend is from the spec's modules (#768)

Question: for each module in the "Frontend modules" tables of the five screen files, what old code does the same job, and how much of it already matches the spec?

The old code is `frontend/` and `.github/workflows/` at `901ec1a`, read on 2026-11-12 and not run. The spec is `docs/spec/` at the same commit, cited as file and section. The old product docs (`DESIGN.md`, `PRODUCT.md`, `docs/reference.md`) are read from `e68424e`. This note sizes gaps only. Keep, rework, rebuild or delete is for [#769](https://github.com/calmxz/Crux/issues/769). The backend's twin is [#749](https://github.com/calmxz/Crux/issues/749).

**Size key.** Small: the old code does the job, with local changes. Medium: the old code holds a working core, and the spec adds real parts. Large: nothing exists, or the old model differs at its core.

**Sizing rule.** Each module is sized on the job it does against the spec. The framework is left out of the size, because it differs the same way for every module: the old frontend is Vue, and the spec's is React (see [Shared ground](#shared-ground)). Each module's Stack line names the old pieces it leans on.

## Short answer

Twenty-two of the 28 modules have a large gap, and six a medium one. None is small. Fifteen modules have no old code at all: the owner's eight, four of the landing screens, Pictures, the file viewer and Feedback. The old app has no page for a visitor without an account, and no owner page. Where old code exists, the screens' shapes come closest: the sidebar and drawer, the session screen's grid with a right-hand panel that is a strip on a phone, messages streamed with Stop, and a result card in the thread. Their contents follow the old model: concept lists, multiple-choice checks, passwords through Supabase in the browser, and money shown to the learner.

Each section file holds the per-module detail: old code, what matches, what differs, what is missing, the stack and the size.

### The learning screen ([detail](old-frontend-comparison/learning-screen.md))

| Module | Old code | Gap | Size |
|---|---|---|---|
| Session screen | `SessionView.vue`, `SessionHeader.vue`, `stores/session.js` | No switch into the check; other top bar actions | Medium: the layout fits, the check switch and top bar change |
| Conversation | `MessageList.vue`, `AssistantBubble.vue`, `MarkdownContent.vue`, `CapBanners.vue`, SSE stream | No Crux's own lines by kind, waiting marks or pinned lines; limits shown in dollars | Medium: messages and streaming work, Crux's lines are new |
| Objectives panel | `CueColumn.vue` | Focus, Gaps, Mastered and Level, not objectives with statuses | Large: the rail and strip fit, every item differs |
| Mastery check | `CheckQuestion.vue` | Multiple choice in a card, not written answers under a check bar | Large: the check model differs |
| Result | `CheckRecap.vue` | Chosen and correct options; no sheet or Dispute | Medium: the card fits, the sheet and Dispute are new |
| Pictures | None | No Mermaid, no graphs | Large: nothing exists, though the module is small |

### The app shell ([detail](old-frontend-comparison/app-shell.md))

| Module | Old code | Gap | Size |
|---|---|---|---|
| App shell | `App.vue`, `Sidebar.vue`, `SidebarMobileTopStrip.vue` | Opens on the start page; no sealed, guest or trial states | Medium: the sidebar, drawer and main area fit |
| Session list | `SidebarSessionRow.vue`, `SidebarRowMenu.vue`, `useSessionActions.js` | One-row lines, no badges, End and Pin instead of Delete | Medium: the list, menu and rename fit |
| Record | `AggregateProfileView.vue` | A stats page, not dated mastered topics and passed objectives | Large: a different page |
| Files | `Composer.vue` file button, `uploadApi.js`, `ReferenceStatusBanner.vue`, `useReferencePoll.js` | Upload through the backend, 25 MB, no dialogs or pinned lines | Medium: picking, states and removal exist |
| File viewer | None | No page can be opened | Large: nothing exists |

### The account screens ([detail](old-frontend-comparison/account-screens.md))

| Module | Old code | Gap | Size |
|---|---|---|---|
| Sign-in | `LoginView.vue`, `RegisterView.vue`, password reset views, `stores/auth.js` | Passwords through Supabase in the browser, not Google and codes | Large: the way in is replaced |
| Opening steps | Router guard, `OnboardingView.vue` | Onboarding asks a name; no lock, keep, terms or under-18 pages | Large: only the routing pattern exists |
| Settings | `SettingsView.vue` tabs, `AccountView.vue` | Dollars, fixed preferences, delete at once; no files or feedback parts | Large: two parts missing, two differ |
| Feedback | None | No page | Large: nothing exists |

### The landing screens ([detail](old-frontend-comparison/landing-screens.md))

| Module | Old code | Gap | Size |
|---|---|---|---|
| Landing page | `NotFoundView.vue` only | No start box, chips, video or states | Large: only the not-found page exists |
| Entry ticks | None | No ticks | Large: nothing exists |
| Guest mode | None | No guest app | Large: nothing exists |
| Request access | None | No page | Large: nothing exists |
| Trial link | None | No link entry, notices or ended pages | Large: nothing exists |

### The owner screens ([detail](old-frontend-comparison/owner-screens.md))

| Module | Old code | Gap | Size |
|---|---|---|---|
| Owner shell | None | No owner page, address or role check | Large: nothing exists |
| Owner today | None | All missing | Large: nothing exists |
| Owner trial | None | All missing | Large: nothing exists |
| Owner safety | None | All missing | Large: nothing exists |
| Owner feedback | None | All missing | Large: nothing exists |
| Owner counts | None | All missing | Large: nothing exists |
| Owner money | None | All missing | Large: nothing exists |
| Owner switches | None | All missing | Large: nothing exists |

## Old code with no module

Old paths are under `frontend/src/`.

| Old code | Job | Spec ruling |
|---|---|---|
| `views/RecallView.vue`, `services/reviewApi.js`, `utils/recallQueue.js` | Spaced review | Retesting later is out of scope, ruled out in [Prototype: the learning loop as a flow diagram](https://github.com/calmxz/Crux/issues/664) |
| "Export your data" in `views/AccountView.vue`, `lib/download.js` | Data download | "Download my data" is out of scope, ruled out in [Decide: privacy, terms, and what happens when sharing ends](https://github.com/calmxz/Crux/issues/677). The spec's emailed copy is another job ([`account-screens.md`](../spec/account-screens.md), Closing an account) |
| `views/SessionsLibraryView.vue`, `components/SessionChips.vue`, the sidebar's search | A page of all sessions, searched by topic, filtered and sorted | No ruling. The spec's search is the tutor's lookup ([`sessions.md`](../spec/sessions.md), The lookup) |
| End, Resume, Continue topic and Pin; `SessionEndedBanner.vue`, `GapPickerDialog.vue` | Ending, reopening and pinning sessions | No spec home. Archiving was ruled out in [Decide: what Crux remembers between visits](https://github.com/calmxz/Crux/issues/671) |
| `views/ProfileView.vue` | A session's profile page, where the learner removes concept list items | No ruling. "Nothing the tutor infers about the learner ... is stored" ([`teaching.md`](../spec/teaching.md), Preferences) |
| Check accuracy and mastered-by-week in `views/AggregateProfileView.vue` | Learner statistics | No ruling |
| `components/profile/UsagePanel.vue`, `components/settings/UsageTab.vue`, the dollar line in `CapBanners.vue` | Spend shown to the learner | Against "A learner never sees money" ([`spending.md`](../spec/spending.md), What is counted) |
| `views/OnboardingView.vue`, display name in `AccountView.vue`, the initial in `SidebarUserMenu.vue` | Name and onboarding | Against "No name is asked or kept" ([`accounts.md`](../spec/accounts.md)) |
| Password change, `ForgotPasswordView.vue`, `ResetPasswordView.vue` | Passwords | Against "There is no password" ([`accounts.md`](../spec/accounts.md), Ways in) |
| `components/start/StartTopicIntercept.vue` | Offers an existing session when a new topic matches one | No ruling. A topic mastered elsewhere is a tutor message ([`sessions.md`](../spec/sessions.md), A topic mastered in another session) |
| `components/settings/AppearanceTab.vue`, `composables/useTheme.js` | Light and dark themes | No ruling |
| `Analytics` in `App.vue`, `lib/analytics.js` | Vercel Web Analytics page views, on Vercel builds | Against "no click or time-on-screen analytics" ([`feedback.md`](../spec/feedback.md)) |
| `ToolCallChip.vue`, `CitationsList.vue` | Tool activity and page citations under a reply | No ruling. A pointer opens the file viewer ([`app-shell.md`](../spec/app-shell.md), Reading a file) |
| `views/LegalView.vue`, `legal/` | Terms of Service and Privacy Policy pages | The spec names Terms, Privacy Policy, Trial Terms, Privacy Notice and "What changed" pages, but no Frontend modules table holds them |
| Ctrl+B and Ctrl+. in `App.vue` | Keyboard shortcuts that fold the sidebar and the panel | No ruling |

## Shared ground

**The framework.** The old frontend is Vue 3 with Pinia (3 stores), vue-router 5 and PrimeVue 4 (`Dialog`, `Toast`, `ConfirmDialog`), themed by an Aura preset. The spec's is a React single-page app with TanStack Router and TanStack Query ([`hosting.md`](../spec/hosting.md), What runs where). [Decide: the app stack and hosting](https://github.com/calmxz/Crux/issues/716) rejected Vue: "the owner chose React". The 56 `.vue` files hold 17,102 lines of templates, scripts and scoped styles. None of them runs under React as written.

**Code with no framework in it.** Of the 50 plain JavaScript files (5,764 lines), these import no Vue, Pinia, PrimeVue or Supabase, directly or through another file, and call no old route: `lib/sseParser.js`, `lib/markdownStreamBuffer.js`, `lib/deltaBatcher.js`, `utils/formatDate.js`, `utils/safeStorage.js`, `utils/safeRedirect.js`, `utils/validation.js`, `utils/idle.js` and `lib/download.js`, 427 lines together. `lib/markdownRenderer.js` (451 lines: markdown-it, DOMPurify, KaTeX and highlight.js loaded on first use) imports only Vue's `ref`. The error files (`errors.js`, `errorCodes.js`, `capErrors.js`, `authErrors.js`) are tied to the old API's error codes and to Supabase's.

**The API client.** `services/apiClient.js` is hand-written `fetch` with a 30-second timeout, three tries on 502, 503 and 504 for reads, a 5-second read cache with ETag checks, and one token refresh on 401. That is the job the spec gives TanStack Query. It sends the Supabase token as a bearer header, against a sign-in cookie the backend checks ([`accounts.md`](../spec/accounts.md), Staying signed in). It calls 27 old routes by hand, by method and path, from the old `docs/api/openapi.yaml`. No types are generated from the contract; five unit tests read the YAML to check a few enums and limits. The spec writes a new contract and generates the backend's models from it ([`hosting.md`](../spec/hosting.md), The backend's tools); it says nothing about the frontend's side.

**Types.** Plain JavaScript. `jsconfig.json` holds one path alias, and no script checks types. The spec asks CI for "tests, style checks and type checks" ([`quality-bar.md`](../spec/quality-bar.md), The repo) and does not name TypeScript for the frontend.

**The build and the host.** Vite 8, with a plugin that writes the content security policy from the API's address (`cspPlugin.js`). Lint is oxlint (with a local rules plugin) and ESLint; Prettier checks format. Two deploy paths exist: `vercel.json` (rewrites and security headers) and a `Dockerfile` that builds the bundle and serves it from nginx as a non-root user, proxying `/api`. The spec serves static files from Cloudflare, with a Worker passing `/api` to Cloud Run ([`hosting.md`](../spec/hosting.md), What runs where). The default API address is `http://localhost:8000/api`; the Docker image sets `/api`, the same-origin shape the Worker gives.

**Where data goes from the browser.** The browser calls Supabase Auth directly (`services/supabase.js`), against "Supabase never sees the browser" ([`hosting.md`](../spec/hosting.md), The database). Vercel Web Analytics runs on Vercel builds (see the table above). Browser errors are not reported anywhere, against `/api/client-error` ([`operations.md`](../spec/operations.md), Errors). Fonts are served from the app's own files.

**The unit tests.** 103 vitest files with about 1,535 test cases, by a count of `it(` and `test(` lines. They run in jsdom with `@vue/test-utils`. By file name, 32 files (about 320 cases) test plumbing: the API client, the SSE parser, markdown, errors, the router, the theme, and checks on landmarks, tap sizes, reduced motion and colour contrast. The other 71 test the old screens. `vitest.config.js` enforces 80% line coverage, against "There is no coverage target" ([`quality-bar.md`](../spec/quality-bar.md), Ordinary tests).

**The end-to-end tests.** 8 Playwright specs with 55 tests, Chromium only, against the old backend with a stubbed model, a throwaway pgvector Postgres and a test JWKS (`e2e/run-local.sh`). The CI job is advisory, "not a required branch-protection check on main" (`e2e.yml`). The spec names no browser tests.

**The CI checks.** The old frontend job runs lint, the format check, vitest with coverage and a Codecov upload, and the build. `npm audit` runs in CI and nightly. hadolint already checks `frontend/Dockerfile`, trivy scans the frontend image, and CodeQL already runs on `javascript-typescript` on each pull request and weekly. In the spec, hadolint is named for the backend's Dockerfile only, and CodeQL for the backend only ([`quality-bar.md`](../spec/quality-bar.md), Security). The spec's frontend is static files on Cloudflare, and no spec file names a frontend container.

**Shapes close to the spec.** File-state polling backs off from 2 to 15 seconds and stops at 90 (`useReferencePoll.js`), and the session list reloads when the tab comes back on screen (`useVisibilityRelist.js`). The spec's open app asks for finished answers "only while its tab is on screen, and less often the longer it waits" ([`hosting.md`](../spec/hosting.md), Background answers). The old app does not call the backend as soon as it loads, which is the spec's warm-on-open (The 5-second first reply); it only opens the connection early.

**Accessibility and look.** The old app has a skip link, focus moved to the main area on each route change, live regions for the stream, 44-pixel tap targets, a reduced-motion mode and a colour-contrast test over its design tokens. Its look is the "Card Box" design system in the old `DESIGN.md`. The spec has no ruling on accessibility or themes; its look comes from the prototypes each screen file names.

## Could not determine

- **The look against the prototypes:** the prototypes are on throwaway branches, and this note does not compare their look with the old design system.
- **Maths and streaming in replies:** no screen file says whether tutor text streams word by word, or how maths in a message is drawn. The old app does both (KaTeX).
- **Old tests per module:** sorted by file name, not read one by one.
