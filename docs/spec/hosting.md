# Hosting

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what runs where, the database, logs, and secrets. Backups, environments, and releases are in [`backups-and-releases.md`](backups-and-releases.md). Email, errors, uptime and owner messages are in [`operations.md`](operations.md) and [`email.md`](email.md), and the daily job in [`dates.md`](dates.md). The visitor's country and address, and the security headers, are in [`security.md`](security.md). The tools are in [`tools.md`](tools.md). The free-hosting rule, the 5-second rule and where data lives are in the main file.

## What runs where

| Part | Where | Notes |
|---|---|---|
| Frontend | Cloudflare, static files, free | A React single-page app with TanStack Router and TanStack Query. It is served apart from the backend, so the landing page shows while the backend wakes |
| Diagrams | Mermaid, drawn by the frontend | See [`learning-screen.md`](learning-screen.md) |
| The Worker | Cloudflare | Passes `/api` calls to Cloud Run, so the site and API share one address |
| Backend | Google Cloud Run, Crux project, Singapore (`asia-southeast1`), request-based billing | Python with FastAPI |
| Tasks service | A second Cloud Run service from the same image | IAM-only. Only Cloud Tasks and Cloud Scheduler call it |
| Converter | Gotenberg, a third, private Cloud Run service | See [The converter](#the-converter) |
| Database | Supabase Free Postgres, Singapore | See [The database](#the-database) |
| Files | A Cloud Storage bucket, Crux project, Singapore | See [`files.md`](files.md) |
| AI | Anthropic's Messages API, `global` inference | See [`ai-layer.md`](ai-layer.md) |

All of this comes from [#716].

## Cloud Run

- The server takes many requests at once, and never runs below 1 CPU, which would force one request at a time ([#716]).
- No work runs outside a request. Anything that outlives a request goes through Cloud Tasks to the tasks service ([#716]).
- Uploads over 32 MiB cannot pass through Cloud Run, so the browser uploads straight to the bucket with a one-time link from Cloud Run ([#716]).
- The tasks service is guarded by Google, not by Crux's code ([#716]).

### Cost

- Cloud Run's free tier is 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests a month, the first two valued at Tier 1 prices (USD 4.32 and 0.90), shared across the billing account. The tests project, staging, the tasks service and the converter draw on it too. In Singapore, read as each part on its own, it covers about 128,571 vCPU-seconds and 257,143 GiB-seconds. The first month's billing report settles that reading ([#716], [#726]).
- The owner's USD 10 monthly Developer Program credit, which covers all of Google Cloud, pays what is left after it ([#716], [#726], [#802]).
- **Spend caps:** USD 10 a month on live, USD 2 on staging. That cap counts "gross" use, read as before the free tier and any credits. The first month's billing report settles that reading ([#716], [#726]).
- Live's Cloud Run cap moves with Crux's workspace limit: whenever the owner page names a change to that limit, it names the cap's too, at about USD 0.31 for each AI dollar added or removed (see [`spending.md`](spending.md)) ([#726]).
- **At full use,** at 512 MiB, estimated ([#726]):
  - Live: the learners' and owner's AI time, the converter and the uptime checks come to about USD 9.26 to 10.58 gross, so live's cap can trip in the month's last days at the highest sitting rate.
  - Staging's USD 2 cap holds while staging's AI use stays under about USD 6.49 to 7.28 a month.
  - Past the free tier, the credit pays about USD 6.30 to 9.55: live's AI time, the converter, Cloud Storage, alerting and up to staging's USD 2. With the planned USD 30 budget, about 7.60 to 11.02. An all-day minimum instance passes the credit. Past the credit, the billing account's payment method pays.
  - Outbound data for file turns is not in these sums (see [Gaps](#gaps)).
- Cloud Storage takes no spend cap. Its cost is bounded by the 20 GB store total in [`files.md`](files.md), about USD 0.40 a month at full, though accepted files may pass it ([#716], [#732]).
- Other hosting costs outside the AI budget are the domain (below), a minimum instance if the fallback is needed (below), alerting (see [`operations.md`](operations.md)), and Workspace once the owner forms a one person corporation (see [`email.md`](email.md)) ([#675], [#716], [#717]).

### When the Cloud Run cap is reached

Google pauses every Cloud Run service in the project, so the tutor, the tasks service and the daily job all stop ([#726]).

- The uptime alert and Google's billing email tell the owner, since paused code writes no log line ([#735]).
- The owner raises the cap within 5 days, after looking at why it tripped. A raise is about USD 1 to 2 for that month. Five days comes before Supabase pauses and the backups expire. Once dumps are weekly, the last one may expire sooner, so the owner raises it the same day ([#735]).
- A second trip is a recorded change to the main file's free-hosting rule ([#735]).

### The 5-second first reply

The rule is in the main file's "Speed". Crux tries these first ([#716]):

1. Warm-on-open: the app calls the backend as soon as it loads.
2. Lazy imports: SymPy loads on first use.
3. Startup CPU boost.
4. A slim image.

Only if the owner's phone test still fails after all four ([#716]):

- One minimum instance at peak hours only, switched on and off by Cloud Scheduler through Cloud Run's service-level setting, so no new revisions. The cap rises by the instance's gross cost: about USD 0.59 a month for each hour of the daily window at 512 MiB, about 0.78 at 1 GiB ([#726]). The peak hours are seen first, from use, before the window is set.
- If off-peak still fails, the minimum instance runs all day, and the cap rises by about USD 14 a month at 512 MiB, about 19 at 1 GiB ([#726]).
- Either one is a recorded change to the main file's free-hosting rule. The recorded change that turns the instance on sets the cap's figure ([#726]).

### Background answers

What a background answer is, and when it runs, is in [`at-a-limit.md`](at-a-limit.md). A new message must still start within the main file's 5 seconds ([#734]).

- They run on the tasks service through Cloud Tasks, so they carry on if the learner leaves ([#735]).
- Opening the app queues the learner's waiting messages and kept files' reads, oldest session first, with the open session ahead of them ([#734]).
- A block clearing queues them too. A tap, or an owner's raise, reaches the backend. The open app calls the backend when midnight passes, each time the learner comes back to the tab while a limit holds, and asks for finished answers while any are waiting, or after a broken reply ([#734], [#735], [#771], [#802]). It asks only while its tab is on screen, and less often the longer it waits ([#736]).
- Crux claims each waiting message in the database before answering it, so a second browser or a second opening does nothing. A claim expires, so a stopped instance cannot hold a message for good ([#734], [#735]).
- One background answer runs at a time per learner, and Crux checks the limits and the region marker before each one (see [`security.md`](security.md)) ([#735], [#802]). A broken reply's new answer does not stop at the learner's own tutoring limit (see [`ai-layer.md`](ai-layer.md)) ([#771]).
- A new message goes through the backend as usual, and does not wait for this queue. If it runs beside a background answer, the limit can pass by at most that one reply ([#735]).
- A new message in a session with waiting messages is answered together with them, except a message waiting for its file's read, which keeps waiting. If one of them is already being answered, the new message follows it, as with any reply under way ([#734], [#735], [#802]).
- A call that fails on overload leaves the message waiting, for the next opening or the next block to clear ([#735]).

## The Worker

- The Worker passes the visitor's country and network address to the backend in Crux's own headers, as [`security.md`](security.md) says ([#769]).
- Cloud Run accepts only calls from the Worker. The Worker adds a secret header, and middleware checks it first with `hmac.compare_digest`. A failure returns a plain 404 ([#716]).
- The secret is at least 32 random bytes, rotatable through a current and next pair, rotated at each release or on any sign of a leak, and never logged ([#716]).
- Only `/api/*` runs the Worker. It turns any answer from Cloud Run not in Crux's error shape into Crux's "can't be reached" code. The request guards in front of it are in [`security.md`](security.md) ([#770]).
- **Nothing blocks the whole site.** Crux checks the country where someone new comes in: sign-up, a code for an email with no account, guest mode and Request access (see the main file's "Who Crux is for"). It also checks it on every request that calls the AI, for accounts, trial links and guests, as [`security.md`](security.md) says. The outside check is not affected ([#733], [#735], [#802]).

### The domain

A domain is bought through Cloudflare's registrar before the trial, about USD 10 to 11 a year for a .com, at cost. The site and Crux's email use it from the trial on. The `workers.dev` address is turned off ([#717]).

## The database

- Supabase Free Postgres in Singapore, reached only by the backend. Supabase never sees the browser ([#716], [#717]).
- Row-level security is on every table holding a learner's data. The backend connects as a role without the bypass and sets the home (the account or trial link, see [`data-model.md`](data-model.md)) for each transaction, or the rules never run ([#716], [#719]). The owner page, the daily job's scans and the sign-in lookups read through rules that name what each may see, not by passing row-level security ([#719]).
- Through Supabase's pooler, each request sets the home with `set_config(..., true)` or `SET LOCAL` inside one explicit transaction. No code runs a session-level `SET` or `set_config(..., false)`. Policies read it as `nullif(current_setting('app.home_id', true), '')`. The setting's name is a draft for the build ([#726]).
- The driver turns prepared statements off and pipelines no queries. Every view is made with `security_invoker`, and no function on a table with row-level security is `SECURITY DEFINER` ([#726]).
- The backend's role owns no table and has no bypass. An ordinary test proves it with a catalog query (see [`ordinary-tests.md`](ordinary-tests.md)). The dump's, restore's and migration roles are the only Crux roles allowed past row-level security. No Crux code connects as `postgres` or `service_role`. The owner uses `postgres` only to create Crux's roles (see [`backups-and-releases.md`](backups-and-releases.md)) ([#726]).
- Every lookup search is limited to the learner's own sessions, in the query and by row-level security (see [`sessions.md`](sessions.md)) ([#716]).
- The outside check keeps Supabase from pausing (see [`operations.md`](operations.md)) ([#716]).
- Another database host is out of scope (see the map's Out of scope list) ([#716]).
- The backend reaches the database through SQLAlchemy 2 with psycopg ([#750]).
- Alembic runs the migrations. Tables and columns come from the SQLAlchemy models. Row-level security policies and grants are written by hand in each revision ([#750]).

## Logs

- Cloud Run's automatic request logs are dropped for everyone by an exclusion filter. The Worker's call logs are off ([#716]).
- Crux writes its own logs: status, path, timing and a request number. They never hold a network address or request headers ([#716]). The main file's "Where data lives" states the rule, and its one exception.
- A logged path is the route's pattern, never the real address, so a trial link's key is never logged. Query strings are not logged, and addresses in browser error reports are stripped the same way. Logs stay 30 days, Google's default ([#735]).
- Cloudflare sees network addresses at its edge, as a processor. Its automatic flood protection, the burst guard and the hand blocks run there (see [`security.md`](security.md), [`privacy.md`](privacy.md) and [`terms-and-policy.md`](terms-and-policy.md)) ([#716], [#770]).
- Logging addresses returns only as a recorded change, with a reason, a short keep time, shortened or scrambled addresses, and the terms-changed notice ([#716]).

## The converter

Gotenberg (LibreOffice) converts PowerPoint and Word to PDF (see [`files.md`](files.md)). Its Cloud Run service is locked down ([#716]):

- It is IAM-only, invoked only by the tasks service's own service account.
- Its own service account has no permissions and no secrets.
- It runs at most 1 instance, with 4 GiB of memory and 1 vCPU, only while converting. 2 GiB held 12 worst-case files in a row, with its peak at the limit ([#726]).
- It has a short timeout.
- Size, uncompressed size and page limits are checked before conversion.
- Gotenberg's version is pinned.

## Secrets

- Google's own services use service accounts, with no stored keys. The Anthropic API key is stored, as [`ai-layer.md`](ai-layer.md) says ([#716], [#802]).
- Copy links are signed as their own service account, which can read only the copies bucket. The backend may ask Google to sign as it, and nothing else uses it (see [`email.md`](email.md)) ([#762]).
- Other secrets live in Google Secret Manager, as Worker secrets, or as GitHub encrypted secrets, never in the repo. These are the Anthropic API key, the Resend key, the Turnstile secret, the database password, the Worker's secret header and the Cloudflare deploy token ([#717], [#802]). The deploy token can also edit the zone's firewall rules ([#770]).
- Staging's gate secret is a GitHub secret, filled into Cloudflare's rule text when the rule is applied ([#770]). The release keeps it in no file or state of its own. Cloudflare's reply to each rule update carries the whole rule set, the secret included, so the release script never prints or saves the replies ([#781]). The daily job's Cloudflare token is in Secret Manager, and can edit only Cloudflare's lists ([#770]).
- How the repo is guarded is in [`quality-bar.md`](quality-bar.md) ([#717]).

## Gaps

- **The UK regulator's guidance on travellers** is unchecked. The EU's is checked: a traveller using a service that doesn't target the EU is outside its law ([#802]).
- **The hosted pooler's leak-check setting,** which Supabase does not state. The rules above do not depend on it ([#726]).
- **Whether hosted Supabase's `postgres` role has the bypass,** as the local stack's does. The three Crux roles past row-level security need `postgres` to grant it ([#726]).
- **Whether the Cloud Run caps count gross or net use,** and Cloud Run's CPU speed and network time: the first month's billing report ([#726]).
- **Where the release script runs.** It must be a machine in a country Crux serves, so a GitHub-hosted job, whose region GitHub does not state, cannot be relied on ([#726]).
- **Outbound data for file turns,** about USD 3.60 a month at full use: see [`files.md`](files.md) ([#726]).
- **Whether warm-on-open meets the 5 seconds off-peak:** a phone test, in [`quality-bar.md`](quality-bar.md) ([#678], [#716]).

## On screen

What the landing page shows while the backend wakes, or when it cannot be reached, is in [`landing-screens.md`](landing-screens.md) ([#716], [#754]).

[#675]: https://github.com/calmxz/Crux/issues/675
[#678]: https://github.com/calmxz/Crux/issues/678
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#726]: https://github.com/calmxz/Crux/issues/726
[#732]: https://github.com/calmxz/Crux/issues/732
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#736]: https://github.com/calmxz/Crux/issues/736
[#750]: https://github.com/calmxz/Crux/issues/750
[#754]: https://github.com/calmxz/Crux/issues/754
[#762]: https://github.com/calmxz/Crux/issues/762
[#769]: https://github.com/calmxz/Crux/issues/769
[#770]: https://github.com/calmxz/Crux/issues/770
[#771]: https://github.com/calmxz/Crux/issues/771
[#781]: https://github.com/calmxz/Crux/issues/781
[#802]: https://github.com/calmxz/Crux/issues/802
