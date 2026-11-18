# The old code

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file is the comparison against the old code, not product rules. It covers the verdicts, each module's fate, what is copied with its tests, and what is left behind, for the backend and the frontend, where the new code lives, when the old code leaves the main branch, and the removal of the old deployment. No product file links to it: every build ticket names it beside its area files (see [`spec-process.md`](spec-process.md)) ([#750], [#769]). The facts behind it are on [#749] and [#768].

## Terms

- **Rework:** the old file is copied into the new code and changed until it fits ([#750]). Neither verdict uses it ([#769]).
- **Rebuild:** the module is written new, with the old code open as a reference at most ([#750]).
- **Copied:** a piece of old code, smaller than a module, taken into a rebuilt module as code, with its tests ([#750]).
- **Left behind:** old code that is neither copied nor reworked. It stays a reference and goes with the old code ([#750], [#769]).
- **Planted case:** a deliberate bad example, run once to prove a check fails on it ([#750]).
- **The old-code tag:** a git tag, `old-code`, on the last commit of `main` that holds the old code. Copies and references in this file are read from it ([#781]).
- **The skeleton ticket:** the first build ticket. It removes the old code and lands the new code's folders and CI ([#781]).
- **The cleanup:** the one-time removal of the old deployment, done after [#797] and before the lock. It is the only step that touches the old deployment, and is tracked on [#799] ([#797]).

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

- **Tutor AI:** the whole `agent/` (tool loop, prompt, tools) is rebuilt. Two things in `services/llm.py` are borrowed as design: the test stub, and no overload retry once streaming starts ([#750], [#771]).
- **Spending:** the pricing piece is the rate table, the dated rate change and `usage_cost` in `services/cost_meter.py`. Its `gemini/...` model names become Agent Platform's, and its rates are re-checked against Agent Platform's price list. A dated rate change takes effect when Google's billing applies it; the build ticket checks Google's notice, and until then the copied date stays in UTC. The limits are written new ([#750]).
- **Operations:** the three copied files change their imports and drop their Render comment. The rebuilt database setup keeps psycopg's `connect_timeout`, which the copied `/ready` probe relies on. Error handling, logging and the backup are written new ([#750]).

## Copied tests and scripts

- Copied code comes with its tests: `test_health.py`, `test_request_id.py`, `test_body_limit.py`, and the pricing cases taken out of `test_cost_meter_estimate.py` and `test_chat_rates.py` ([#750]).
- Each moves onto the throwaway database where it touches one (see [`backups-and-releases.md`](backups-and-releases.md)) ([#750]).
- `gen_contracts.py` is copied (see [`tools.md`](tools.md)) ([#750]).

## Left behind

- The old schema and its 31 migrations, and every old module's code not listed as copied ([#750]).
- Old code with no module in the spec: the embedding search, the review queue, the data export, the usage summary, `display_name` and onboarding, ending and pinning sessions, `profile_insights.py`, `lib/etag.py`, and the live-model evaluation scripts ([#750]).
- The old `Dockerfile`, `config.py`, `main.py`, `worker.py` and `entrypoint.sh` are written new, with the old ones as a reference. `seed_debug_accounts.py` and `pg_tests.sh` are left behind ([#750]).
- The test suite apart from the copied tests, `conftest.py` included ([#750]).
- From the old CI: semgrep and trivy, the coverage gate and the Codecov upload, gitleaks, and `uv audit` in CI and the nightly `audit.yml`. The checks that stay are in [`quality-bar.md`](quality-bar.md) ([#750]).

## Frontend modules

The modules are the ones in the screen files' Frontend modules tables. Themes have their row in [`themes.md`](themes.md#frontend-modules) ([#779]). The all-sessions page has its row in [`app-shell.md`](app-shell.md#frontend-modules) ([#769], [#780]).

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

- `markdownRenderer.js` is copied, since every reply needs its Markdown and its DOMPurify cleaning. Its KaTeX part stays, since maths is drawn with KaTeX. Vue's `ref` is replaced ([#769], [#771]).
- `markdownStreamBuffer.js` and `deltaBatcher.js` are copied too, since a reply shows word by word ([#769], [#771]).
- Each is converted to TypeScript and comes with its tests: `markdownRenderer.test.js` (3 cases), `markdownIncremental.test.js` (14), `markdownStreamBuffer.test.js` (17) and `deltaBatcher.test.js` (4). The 6 cases in `markdownRendererLazy.test.js` mount the old Vue component, so they are rewritten against the React one ([#769]).
- `sseParser.js` is left behind, since Hey API's client reads the event stream. If the fallback in [`tools.md`](tools.md) drops Hey API, `sseParser.js` and `sseParser.test.js` (7 cases) are copied, since something must read the backend's event stream ([#769]).

## Frontend left behind

- The six small plain files: `safeRedirect.js`, `safeStorage.js`, `idle.js`, `formatDate.js`, `validation.js`, `download.js` ([#769]).
- The API client (`apiClient.js`) and the error files tied to the old API and Supabase; the stores and the router ([#769]).
- Old code against the spec: Supabase called from the browser, money shown to the learner, the name asked at onboarding, passwords, the "Direct answers" preference, Vercel Web Analytics, and the account delete that acts at once ([#769]).
- Old code with no module: Recall (ruled out on [#664]), the data export (ruled out on [#677]), the session profile page, the topic match on start (`StartTopicIntercept.vue`), tool chips and citations, and End, Resume and Continue topic with the gap picker ([#769]).
- `cspPlugin.js`, `vercel.json`, the frontend `Dockerfile` and `nginx.conf`; the Playwright harness (`e2e/run-local.sh`, the test JWKS) as a reference; the local oxlint rules plugin ([#769]).
- Every old test apart from those listed as copied, and the 80% coverage gate ([#769]).
- From the old frontend CI: hadolint on `frontend/Dockerfile`, since there is no frontend container; the trivy image scan; `npm audit` in CI and nightly, since osv-scanner already covers the lockfiles and Dependabot opens the fixes; and the coverage gate with the Codecov upload. The checks that stay are in [`quality-bar.md`](quality-bar.md) ([#769]).

## Where the new code lives

- The new code lives in this repo, `calmxz/Crux`, and the spec stays in `docs/spec/`. No repo is renamed, so the spec's issue links and the prototype and research branches stay where they are ([#781]).
- Its top-level folders are in [`tools.md`](tools.md#the-repos-folders) ([#781]).

## When the old code goes

- After the spec is locked, the skeleton ticket removes the old code from `main` and lands the new skeleton with its own CI, in one pull request ([#781]).
- At that pull request's merge, the old backend, frontend and security checks give way to the new ones in the branch rules. The CodeQL and file-size checks stay ([#781]).
- Before the removal, the skeleton ticket tags the last commit that holds the old code as `old-code`. A tag ruleset blocks moving and deleting the tag. Copies and references are read from it: `git show old-code:<path>`, a worktree, or GitHub's tag view ([#781]).
- Until then the old code stays frozen. Dependabot security pull requests on it are closed unmerged ([#781]).

### What leaves the main branch

- **Leaves, kept in the tag:** `backend/`, `frontend/`, the old contract at `docs/api/openapi.yaml` (the new one is written fresh at that path), `docs/auth/`, `docs/db/`, `docs/deploy/`, `docs/dev/`, `docs/security/`, `render.yaml`, both `docker-compose` files, `dev.ps1`, `pyrightconfig.json`, `.env.example`, `data/.gitkeep`, `.git-blame-ignore-revs`, `.out-of-scope/llm-settlement-reconciliation.md`, `e2e.yml`, `audit.yml`, `backup.yml` (turned off by the cleanup), the backend, frontend and security jobs in `ci.yml`, and the old entries in `dependabot.yml`, replaced by entries for the new folders ([#781], [#797]).
- **Stays:** `docs/spec/`, `GLOSSARY.md`, `LICENSE`, `docs/research/` (the notes behind five research tickets), the file-size job in `ci.yml`, `claude.yml` and `claude-code-review.yml` ([#781]).
- **Stays, with its old paths revised by the skeleton ticket:** `CODING_STANDARDS.md`, `codeql.yml` and `.github/codeql/`, `plugins/basedpyright-lsp` and `.claude-plugin/`, `.githooks/`, `.gitattributes`, `.gitignore`, `docs/agents/`, and `README.md`, whose status is rewritten in the same change. The repo's GitHub description, topics and homepage change in the same step ([#781]). The cleanup changes the README, the description and the homepage first, as below ([#797]).

## The old deployment

The old deployment does not come back. The new app's first deployment is the one the spec describes, on the new domain (see [`hosting.md`](hosting.md)) ([#797]).

- The old database holds only the owner's own test accounts and data: two accounts, and one session and one message under no current account. No learner gets a notice. Nothing from it carries into the new database ([#750], [#797]).
- After the cleanup, the old app cannot be run with sign-in or the tutor. The old code is read, not run. The copied pieces' tests still run, since they use in-memory SQLite ([#797]).

### What the cleanup removes

- The nightly backup, `backup.yml`, is turned off with GitHub's "Disable workflow" switch, so it never runs again, by schedule or by hand. The file stays until the skeleton pull request removes it with the old code, so no frozen file changes ([#797]).
- Its 5 GitHub secrets: `DATABASE_URL`, `R2_ACCESS_KEY_ID`, `R2_BUCKET`, `R2_ENDPOINT` and `R2_SECRET_ACCESS_KEY` ([#797]).
- The old Supabase project, deleted, not paused ([#797]).
- In Cloudflare R2: the backup bucket with its 7 copies, and the old app's uploaded files, in whichever bucket holds them ([#797]).
- Every R2 token made for the old app or its backup, revoked, so a leaked old key opens nothing ([#797]).
- The Render service `crux-api` ([#797]).
- The Vercel project and this repo's connection to it, so the failing "Vercel" check leaves pull requests. Its address, `crux-tutor.vercel.app`, then shows Vercel's not-found page. Someone else may later take the name; the owner accepts that ([#797]).
- The 3 GitHub environments: "main - crux-api", "Preview" and "Production" ([#797]).
- The old app's `GEMINI_API_KEY`, revoked in Google ([#797]).

### When and in what order

- Right after [#797], before the lock. The skeleton ticket carries nothing old apart from the code ([#797]).
- First the public text: the cleanup pull request is reviewed and merged, the homepage link is cleared and the description rewritten. Every new line is true from the moment it appears ([#797]).
- Then the nightly job is turned off, so it never fails against a deleted database. Then the owner deletes, in order: the Supabase project, the R2 files, bucket and tokens, the Render service, the Vercel project, and the environments ([#797]).
- The old Gemini key goes last: once [#726] has made its model calls, or straight away if that research uses the owner's Google login. At the latest, it goes when that ticket closes ([#797]).
- The cleanup is its own issue, [#799], not a ticket on the map. The map's Destination is reached only once the cleanup is done, so the spec locks only after it ([#797]).
- The owner's Supabase account has one other project, which takes no free slot by the time live and staging are made. Render's `DATABASE_URL` points at the project the counts above came from ([#797]).

### What the public text says

- The cleanup pull request replaces the README's paragraph on the old code with ``The spec is in [`docs/spec/`](docs/spec/README.md).`` (draft wording). The README no longer mentions the old code ([#797]).
- The cleanup clears the repo's GitHub homepage link ([#797]).
- It replaces the GitHub description with "An adaptive tutor that teaches a topic until you understand it, and calls it mastered only once you've proven it. Being re-specified from scratch." (draft wording) ([#797]).

## After v1

Learner statistics, keyboard shortcuts and pinning a session are lines on the map's Out of scope list ([#769]).

[#664]: https://github.com/calmxz/Crux/issues/664
[#677]: https://github.com/calmxz/Crux/issues/677
[#719]: https://github.com/calmxz/Crux/issues/719
[#726]: https://github.com/calmxz/Crux/issues/726
[#749]: https://github.com/calmxz/Crux/issues/749
[#750]: https://github.com/calmxz/Crux/issues/750
[#768]: https://github.com/calmxz/Crux/issues/768
[#769]: https://github.com/calmxz/Crux/issues/769
[#771]: https://github.com/calmxz/Crux/issues/771
[#779]: https://github.com/calmxz/Crux/issues/779
[#780]: https://github.com/calmxz/Crux/issues/780
[#781]: https://github.com/calmxz/Crux/issues/781
[#797]: https://github.com/calmxz/Crux/issues/797
[#799]: https://github.com/calmxz/Crux/issues/799
