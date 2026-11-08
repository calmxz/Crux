# Hosting

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what runs where, the database, backups, environments and releases, the backend's tools, logs, and secrets. Email, errors, uptime, owner messages and the daily job are in [`operations.md`](operations.md). The free-hosting rule, the 5-second rule and where data lives are in the main file.

## What runs where

| Part | Where | Notes |
|---|---|---|
| Frontend | Cloudflare, static files, free | A React single-page app with TanStack Router and TanStack Query. It is served apart from the backend, so the landing page shows while the backend wakes |
| The Worker | Cloudflare | Passes `/api` calls to Cloud Run, so the site and API share one address |
| Backend | Google Cloud Run, Crux project, Singapore (`asia-southeast1`), request-based billing | Python with FastAPI |
| Tasks service | A second Cloud Run service from the same image | IAM-only. Only Cloud Tasks and Cloud Scheduler call it |
| Converter | Gotenberg, a third, private Cloud Run service | See [The converter](#the-converter) |
| Database | Supabase Free Postgres, Singapore | See [The database](#the-database) |
| Files | A Cloud Storage bucket, Crux project, Singapore | See [`files.md`](files.md) |
| AI | Agent Platform, global address | See [`ai-layer.md`](ai-layer.md) |

All of this comes from [#716].

## Cloud Run

- The server takes many requests at once, and never runs below 1 CPU, which would force one request at a time ([#716]).
- No work runs outside a request. Anything that outlives a request goes through Cloud Tasks to the tasks service ([#716]).
- Uploads over 32 MiB cannot pass through Cloud Run, so the browser uploads straight to the bucket with a one-time link from Cloud Run ([#716]).
- The tasks service is guarded by Google, not by Crux's code ([#716]).

### Cost

- Cloud Run's free tier is a dollar credit valued at Tier 1 prices, about USD 5.22 a month, shared across the billing account. The tests project, staging, the tasks service and the converter draw on it too. In Singapore it covers about 128,000 busy CPU-seconds ([#716]).
- The owner's USD 10 monthly Developer Program credit may pay what is left after it, though Gemini likely uses that credit first ([#716]).
- **Spend caps:** USD 6 a month on live, USD 2 on staging. Google's cap counts "gross" use, read as before the free credit and any credits. The first month's billing report settles that reading ([#716], [#726]).
- Cloud Storage takes no spend cap. Its cost is bounded by the 20 GB store total in [`files.md`](files.md), about USD 0.40 a month at full, though accepted files may pass it ([#716], [#732]).
- Other hosting costs outside the AI budget are the domain (below), a minimum instance if the fallback is needed (below), alerting (see [`operations.md`](operations.md)), and Workspace if Zoho's agreement fails ([#675], [#716], [#717]).

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

- One minimum instance at peak hours only, switched on and off by Cloud Scheduler through Cloud Run's service-level setting, so no new revisions. The cap rises to about USD 8. The peak hours are seen first, from use, before the window is set.
- If off-peak still fails, the minimum instance runs all day, about USD 10 a month after the free credit, with a cap of about USD 16.
- Either one is a recorded change to the main file's free-hosting rule.

### Background answers

What a background answer is, and when it runs, is in [`spending.md`](spending.md). A new message must still start within the main file's 5 seconds ([#734]).

- They run on the tasks service through Cloud Tasks, so they carry on if the learner leaves ([#735]).
- Opening the app queues the learner's waiting messages and kept files' reads, oldest session first, with the open session ahead of them ([#734]).
- A block clearing queues them too. A tap, or an owner's raise, reaches the backend. The open app calls the backend when midnight passes, and asks for finished answers while any are waiting ([#734], [#735]). It asks only while its tab is on screen, and less often the longer it waits ([#736]).
- Crux claims each waiting message in the database before answering it, so a second browser or a second opening does nothing. A claim expires, so a stopped instance cannot hold a message for good ([#734], [#735]).
- One background answer runs at a time per learner, and Crux checks the limits before each one ([#735]).
- A new message goes through the backend as usual, and does not wait for this queue. If it runs beside a background answer, the limit can pass by at most that one reply ([#735]).
- A new message in a session with waiting messages is answered together with them. If one of them is already being answered, the new message follows it, as with any reply under way ([#734], [#735]).
- A call that fails on overload leaves the message waiting, for the next opening or the next block to clear ([#735]).

## The Worker and the country check

- Cloudflare adds the visitor's country to each request (`CF-IPCountry`), and the visitor's network address, which the code limits and wrong-link counts read ([#716], [#717]).
- Cloud Run accepts only calls from the Worker. The Worker adds a secret header, and middleware checks it first with `hmac.compare_digest`. A failure returns a plain 404 ([#716]).
- The secret is at least 32 random bytes, rotatable through a current and next pair, rotated at each release or on any sign of a leak, and never logged ([#716]).
- **Nothing blocks the whole site.** Crux checks the country only where someone new comes in: sign-up, a code for an email with no account, guest mode and Request access (see the main file's "Who Crux is for"). Accounts and trial links work from anywhere, and the outside check is not affected ([#733], [#735]).

### The domain

A domain is bought through Cloudflare's registrar before the trial, about USD 10 to 11 a year for a .com, at cost. The site and Crux's email use it from the trial on. The `workers.dev` address is turned off ([#717]).

## The database

- Supabase Free Postgres in Singapore, reached only by the backend. Supabase never sees the browser ([#716], [#717]).
- Row-level security is on every table holding a learner's data. The backend connects as a role without the bypass and sets the home (the account or trial link, see [`data-model.md`](data-model.md)) for each transaction, or the rules never run ([#716], [#719]). The owner page, the daily job's scans and the sign-in lookups read through rules that name what each may see, not by passing row-level security ([#719]). The safe pattern through Supabase's pooler is a research finding on [#726], for [#719].
- Every lookup search is limited to the learner's own sessions, in the query and by row-level security (see [`sessions.md`](sessions.md)) ([#716]).
- The outside check keeps Supabase from pausing (see [`operations.md`](operations.md)) ([#716]).
- Another database host is out of scope (see the map's Out of scope list) ([#716]).
- The backend reaches the database through SQLAlchemy 2 with psycopg ([#750]).
- Alembic runs the migrations. Tables and columns come from the SQLAlchemy models. Row-level security policies and grants are written by hand in each revision ([#750]).

## Backups

Supabase Free has no backups, so Crux makes its own ([#716]).

- **Daily dump:** a `pg_dump` of live, in the daily job. It drops to weekly once the database passes about 100 MB, so Supabase's 5 GB a month of outgoing transfer is not used up.
- **Before every live migration:** an automatic `pg_dump`.
- **Who can read the data:** the dump runs as its own read-only role. It and the restore's role, which writes for a restore or a repair, are the only roles allowed past row-level security, and only the release script uses them ([#719], [#735]).
- **Where they go:** a Cloud Storage bucket with soft delete off, readable only by the release script's account.
- **How long:** a lifecycle rule deletes each dump after 7 days, and Google applies it within about a day. The Privacy Policy says "deleted data may remain in a backup for up to 8 days", for every deletion (see [`privacy.md`](privacy.md)).
- **Soft delete** is set to 0 on every Crux bucket, so deleting erases.

### The restore log

A log in its own Cloud Storage bucket, with soft delete off, records what a restore must apply again. The app can only add entries, and only the release script reads them. An entry keeps only IDs, the time and the action, never content, and a lifecycle rule deletes it after 8 days, once the last dump it applies to has expired ([#716], [#719], [#735]). It records:

- every deletion;
- seals and locks, and the "Reported" mark;
- warnings and flags;
- ticks and quotes withdrawn;
- closures asked for or kept, contests entered, and copies asked for;
- misuse-block entries;
- trial links switched off;
- age-question answers;
- each home erasure, with its moves and writes and any copy's object ID and expiry, and re-marks that change a mark ([#719]).

A new safety or privacy action joins this list in the same change that adds it, with a test that it survives a restore ([#735]).

**A full restore** applies the log again. Entries that point at something the restore lost are skipped, and applying an entry twice is harmless. New messages and marks since the dump are lost. A copy already made is kept, since the erasure applies again ([#716], [#735]). A logged home erasure is applied again by calling the erasure routine in [`data-model.md`](data-model.md), so its moves and writes happen again before the delete. A replay rewrites a copy's record from the log, and makes and sends nothing ([#719]). A restore may lose a share tick given, which the learner gives again, and a "Start the window" press and let-in entries, which the owner redoes ([#719]).

**A repair** ([#716], [#735]):

- It opens the dump in a temporary area of the live database, deleted afterwards. Once the database passes about 250 MB, it uses a throwaway Cloud Run job's own Postgres in Singapore instead.
- Real learner data never leaves Supabase or Google Cloud for a repair.
- Repairs are done by script, and the owner sees counts, not content. Rows changed after the bug keep their newer value, and the log still applies.

A test restore of a dump is on the before-trial checklist (see [`quality-bar.md`](quality-bar.md)) ([#716]).

## Environments

| Environment | Runs on | Data |
|---|---|---|
| Dev | The owner's computer, with the Supabase CLI's local stack in Docker | Fake data only |
| CI | A throwaway database on GitHub's machines for each run, from the same local stack | Fake data only |
| Staging | The Crux tests project: its own Cloud Run, Supabase Free project, bucket and Worker | Synthetic data only |
| Live | The Crux project | Real learner data |

All of this comes from [#716].

- Staging's AI calls count in the test cap. Its Supabase pauses after a quiet week, and is restored by hand before a release ([#716]).
- Staging sends no real email, and its daily job runs by hand, so it uses neither Resend's limit nor a Cloud Scheduler job ([#735]).
- The owner-page switches apply to the owner's account on live. Dev, the AI tests and staging have their own settings (see [`live-faults.md`](live-faults.md)) ([#678], [#679]).
- CI starts the local stack, then runs `alembic upgrade head` ([#750]).

### The backend's tools

- Python 3.14, uv for dependencies and the lockfile, ruff for style, basedpyright for types ([#750]).
- The API is contract-first. `docs/api/openapi.yaml` is written by hand, `gen_contracts.py` generates the request and response models from it, and CI fails on drift between them ([#750]).

## Releases

- A release goes to staging first, then to live as a no-traffic revision with a private address, then takes all traffic in one step. Rollback is one step ([#716]).
- Migrations are backward-compatible: add first, remove in a later release. A one-step rollback still works ([#716]).
- A live release takes the dump (see [Backups](#backups)), then runs `alembic upgrade head` ([#716], [#750]).

## Logs

- Cloud Run's automatic request logs are dropped for everyone by an exclusion filter. The Worker's call logs are off ([#716]).
- Crux writes its own logs: status, path, timing and a request number. They never hold a network address or request headers ([#716]). The main file's "Where data lives" states the rule, and its one exception.
- A logged path is the route's pattern, never the real address, so a trial link's key is never logged. Query strings are not logged, and addresses in browser error reports are stripped the same way. Logs stay 30 days, Google's default ([#735]).
- Cloudflare sees network addresses at its edge, as a processor. Its automatic flood protection and the burst guard run there (see [`privacy.md`](privacy.md)) ([#716]).
- Logging addresses returns only as a recorded change, with a reason, a short keep time, shortened or scrambled addresses, and the terms-changed notice ([#716]).

## The converter

Gotenberg (LibreOffice) converts PowerPoint and Word to PDF (see [`files.md`](files.md)). Its Cloud Run service is locked down ([#716]):

- It is IAM-only, invoked only by the tasks service's own service account.
- Its own service account has no permissions and no secrets.
- It runs at most 1 instance, with 1 to 2 GiB of memory, only while converting.
- It has a short timeout.
- Size, uncompressed size and page limits are checked before conversion.
- Gotenberg's version is pinned.

## Secrets

- Google's own services use service accounts, with no stored keys (see [`ai-layer.md`](ai-layer.md)) ([#716]).
- Other secrets live in Google Secret Manager, as Worker secrets, or as GitHub encrypted secrets, never in the repo. These are the Resend key, the Turnstile secret, the database password, the Worker's secret header and the Cloudflare deploy token ([#717]).
- How the repo is guarded is in [`quality-bar.md`](quality-bar.md) ([#717]).

## Gaps

- **Open hosting checks on [#726]:** the pooler test, and server time per sitting and per upload. The research reads the Cloud Run cap as gross use, so a month of USD 4.80 could trip staging's USD 2 cap at a bill of 0. The first month's report settles it.
- **Whether the Cloud Run credit holds** with file work in the trial, and how busy a sitting is: open on [#675] ([#716], [#722]).
- **Whether warm-on-open meets the 5 seconds off-peak:** a phone test, in [`quality-bar.md`](quality-bar.md) ([#678], [#716]).

## On screen

Layout is not decided (see the main file's Gaps). These rules need: what the static page shows when the backend cannot be reached ([#716]).

[#675]: https://github.com/calmxz/Crux/issues/675
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#722]: https://github.com/calmxz/Crux/issues/722
[#726]: https://github.com/calmxz/Crux/issues/726
[#732]: https://github.com/calmxz/Crux/issues/732
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#736]: https://github.com/calmxz/Crux/issues/736
[#750]: https://github.com/calmxz/Crux/issues/750
