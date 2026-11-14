# The old code

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file is the comparison against the old code, not product rules. It covers the verdicts, each module's fate, what is copied with its tests, and what is left behind, for the backend and the frontend. No product file links to it: every build ticket names it beside its area files (see [`spec-process.md`](spec-process.md)) ([#750], [#769]). The facts behind it are on [#749] and [#768].

## Terms

- **Rework:** the old file is copied into the new code and changed until it fits ([#750]). Neither verdict uses it ([#769]).
- **Rebuild:** the module is written new, with the old code open as a reference at most ([#750]).
- **Copied:** a piece of old code, smaller than a module, taken into a rebuilt module as code, with its tests ([#750]).
- **Left behind:** old code that is neither copied nor reworked. It stays a reference and goes with the old code ([#750], [#769]).
- **Planted case:** a deliberate bad example, run once to prove a check fails on it ([#750]).

## The verdict

- The backend is a rewrite. A new backend is written against the spec ([#750]).
- Its first migration creates homes with row-level security. The old `users` table and concept lists never exist there ([#750]).
- The frontend is a rewrite. A new React app in TypeScript is written against the spec and the new backend's API. The old Vue code is a reference ([#769]).
- Nothing old is live, so no step has to keep the old app running ([#769]).
- Only the pieces this file lists as copied go in as code ([#750], [#769]).

## Backend modules

The modules are the ones in [`data-model.md`](data-model.md) ([#719]).

| Module | Verdict | Copied as code |
|---|---|---|
| Homes | Rebuild | None |
| Sign-in | Rebuild | None |
| Learning | Rebuild | None |
| Mastery check | Rebuild | None |
| Files | Rebuild | None |
| Tutor AI | Rebuild | None |
| Spending | Rebuild | The pricing piece |
| Safety | New, no old code | None |
| Feedback | New, no old code | None |
| Email | New, no old code | None |
| Operations | Rebuild | `routes/health.py`, `lib/request_id.py`, `lib/body_limit.py` |

All of this comes from [#750].

- **Tutor AI:** the whole `agent/` (tool loop, prompt, tools) is rebuilt. Two things in `services/llm.py` are borrowed as design: the test stub, and no retry once streaming starts ([#750]).
- **Spending:** the pricing piece is the rate table, the dated rate change and `usage_cost` in `services/cost_meter.py`. Its `gemini/...` model names become Agent Platform's, and its rates are re-checked against Agent Platform's price list. A dated rate change takes effect when Google's billing applies it; the build ticket checks Google's notice, and until then the copied date stays in UTC. The limits are written new ([#750]).
- **Operations:** the three copied files change their imports and drop their Render comment. The rebuilt database setup keeps psycopg's `connect_timeout`, which the copied `/ready` probe relies on. Error handling, logging and the backup are written new ([#750]).

## Copied tests and scripts

- Copied code comes with its tests: `test_health.py`, `test_request_id.py`, `test_body_limit.py`, and the pricing cases taken out of `test_cost_meter_estimate.py` and `test_chat_rates.py` ([#750]).
- Each moves onto the throwaway database where it touches one (see [`hosting.md`](hosting.md)) ([#750]).
- `gen_contracts.py` is copied (see [`tools.md`](tools.md)) ([#750]).

## Left behind

- The old schema and its 31 migrations, and every old module's code not listed as copied ([#750]).
- Old code with no module in the spec: the embedding search, the review queue, the data export, the usage summary, `display_name` and onboarding, ending and pinning sessions, `profile_insights.py`, `lib/etag.py`, and the live-model evaluation scripts ([#750]).
- The old `Dockerfile`, `config.py`, `main.py`, `worker.py` and `entrypoint.sh` are written new, with the old ones as a reference. `seed_debug_accounts.py` and `pg_tests.sh` are left behind ([#750]).
- The test suite apart from the copied tests, `conftest.py` included ([#750]).
- From the old CI: semgrep and trivy, the coverage gate and the Codecov upload, gitleaks, and `uv audit` in CI and the nightly `audit.yml`. The checks that stay are in [`quality-bar.md`](quality-bar.md) ([#750]).

## Frontend modules

The modules are the ones in the screen files' Frontend modules tables. Themes and the all-sessions page get their rows on [#779] and [#780] ([#769]).

| Module | Verdict | Old code as reference |
|---|---|---|
| Session screen | Rebuild | `SessionView.vue`, `SessionHeader.vue`, `stores/session.js` |
| Conversation | Rebuild | `MessageList.vue`, `AssistantBubble.vue`, `MarkdownContent.vue`, `CapBanners.vue` |
| Objectives panel | Rebuild | `CueColumn.vue` |
| Mastery check | Rebuild | `CheckQuestion.vue` |
| Result | Rebuild | `CheckRecap.vue` |
| Pictures | New, no old code | None |
| App shell | Rebuild | `App.vue`, `Sidebar.vue`, `SidebarMobileTopStrip.vue` |
| Session list | Rebuild | `SidebarSessionRow.vue`, `SidebarRowMenu.vue`, `useSessionActions.js` |
| Record | Rebuild | `AggregateProfileView.vue` |
| Files | Rebuild | `Composer.vue`'s file button, `uploadApi.js`, `ReferenceStatusBanner.vue`, `useReferencePoll.js` |
| File viewer | New, no old code | None |
| Sign-in | Rebuild | `LoginView.vue`, `RegisterView.vue`, `stores/auth.js` |
| Opening steps | Rebuild | The router guard, `OnboardingView.vue` |
| Settings | Rebuild | `SettingsView.vue`, `AccountView.vue` |
| Feedback | New, no old code | None |
| Landing page | Rebuild | `NotFoundView.vue` |
| Entry ticks, Guest mode, Request access, Trial link | New, no old code | None |
| The eight owner modules | New, no old code | None |
| Legal pages | Rebuild | `LegalView.vue`, for the layout only |
| Copy page | New, no old code | None |
| Themes | Rebuild | `AppearanceTab.vue`, `useTheme.js` |
| All-sessions page | Rebuild | `SessionsLibraryView.vue` |

All of this comes from [#769].

- Every rebuilt module is written from its screen file and, where it has one, its prototype. The shapes the old code shares with the spec are already spec rules ([#769]).
- The one thing borrowed as design is `safeRedirect.js`'s same-site rule: after sign-in, only a path on Crux's own address is followed, never `//host` or a full address ([#769]).
- Each screen's look comes from its prototype. The old "Card Box" design system is left behind as a reference ([#769]).
- The old legal text is not reused ([#769]).

## Copied frontend code

- `markdownRenderer.js` is copied whatever [#771] decides, since every reply needs its Markdown and its DOMPurify cleaning. Its KaTeX part stays only if [#771] keeps LaTeX drawn with KaTeX. Vue's `ref` is replaced ([#769]).
- If [#771] keeps word-by-word streaming, `markdownStreamBuffer.js` and `deltaBatcher.js` are copied too ([#769]).
- Each is converted to TypeScript and comes with its tests: `markdownRenderer.test.js` (3 cases), `markdownIncremental.test.js` (14), `markdownStreamBuffer.test.js` (17) and `deltaBatcher.test.js` (4). The 6 cases in `markdownRendererLazy.test.js` mount the old Vue component, so they are rewritten against the React one ([#769]).
- `sseParser.js` is left behind, since Hey API's client reads the event stream. If the fallback in [`tools.md`](tools.md) drops Hey API, `sseParser.js` and `sseParser.test.js` (7 cases) are copied, since something must read the backend's event stream whatever [#771] decides ([#769]).

## Frontend left behind

- The six small plain files: `safeRedirect.js`, `safeStorage.js`, `idle.js`, `formatDate.js`, `validation.js`, `download.js` ([#769]).
- The API client (`apiClient.js`) and the error files tied to the old API and Supabase; the stores and the router ([#769]).
- Old code against the spec: Supabase called from the browser, money shown to the learner, the name asked at onboarding, passwords, the "Direct answers" preference, Vercel Web Analytics, and the account delete that acts at once ([#769]).
- Old code with no module: Recall (ruled out on [#664]), the data export (ruled out on [#677]), the session profile page, the topic match on start (`StartTopicIntercept.vue`), tool chips and citations, and End, Resume and Continue topic with the gap picker ([#769]).
- `cspPlugin.js`, `vercel.json`, the frontend `Dockerfile` and `nginx.conf`; the Playwright harness (`e2e/run-local.sh`, the test JWKS) as a reference; the local oxlint rules plugin ([#769]).
- Every old test apart from those listed as copied, and the 80% coverage gate ([#769]).
- From the old frontend CI: hadolint on `frontend/Dockerfile`, since there is no frontend container; the trivy image scan; `npm audit` in CI and nightly, since osv-scanner already covers the lockfiles and Dependabot opens the fixes; and the coverage gate with the Codecov upload. The checks that stay are in [`quality-bar.md`](quality-bar.md) ([#769]).

## After v1

Learner statistics, keyboard shortcuts and pinning a session are lines on the map's Out of scope list ([#769]).

## Gaps

- **Streaming and KaTeX:** whether they stay is open on [#771]. Its answer settles which frontend files are copied ([#769]).
- **Where the new code lives, and when the old code goes:** open on [#781] ([#750], [#769]).
- **Bringing the deployment back:** on the map's "Not yet specified" list. The new schema has no path from the old migrations ([#750]).

[#664]: https://github.com/calmxz/Crux/issues/664
[#677]: https://github.com/calmxz/Crux/issues/677
[#719]: https://github.com/calmxz/Crux/issues/719
[#749]: https://github.com/calmxz/Crux/issues/749
[#750]: https://github.com/calmxz/Crux/issues/750
[#768]: https://github.com/calmxz/Crux/issues/768
[#769]: https://github.com/calmxz/Crux/issues/769
[#771]: https://github.com/calmxz/Crux/issues/771
[#779]: https://github.com/calmxz/Crux/issues/779
[#780]: https://github.com/calmxz/Crux/issues/780
[#781]: https://github.com/calmxz/Crux/issues/781
