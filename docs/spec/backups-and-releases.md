# Backups, environments, and releases

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers backups, the restore log and repairs, the environments, and releases. What runs where and the database are in [`hosting.md`](hosting.md).

## Backups

Supabase Free has no backups, so Crux makes its own ([#716]).

- **Daily dump:** a `pg_dump` of live, in the daily job. It drops to weekly once the database passes about 100 MB, so Supabase's 5 GB a month of outgoing transfer is not used up.
- **Before every live migration:** an automatic `pg_dump`.
- **Who can read the data:** the dump runs as its own read-only role. It, the restore's role, which writes for a restore or a repair, and the migration role are the only Crux roles allowed past row-level security, and only the release script uses them. On staging and live, no Crux code connects as `postgres` or `service_role`. The owner uses `postgres` only to create Crux's roles ([#719], [#726], [#735]).
- **Where they go:** a Cloud Storage bucket with soft delete off, readable only by the release script's account.
- **How long:** a lifecycle rule deletes each dump after 7 days, and Google applies it within about a day. The Privacy Policy says "deleted data may remain in a backup for up to 8 days", for every deletion (see [`privacy.md`](privacy.md) and [`terms-and-policy.md`](terms-and-policy.md)).
- **Soft delete** is set to 0 on every Crux bucket, so deleting erases.

### The restore log

A log in its own Cloud Storage bucket, with soft delete off, records what a restore must apply again. The app can only add entries, and only the release script reads them. An entry keeps only IDs, the time and the action, never content, and a lifecycle rule deletes it after 8 days, once the last dump it applies to has expired ([#716], [#719], [#735]). It records:

- every deletion;
- seals and locks, and the "Reported" mark;
- warnings and flags, and a warning or dismissal with its waiting misuse card ([#764]);
- a tap on Continue on a misuse card, and an ended page's first showing, so a restore neither brings the kinds back nor loses a card ([#764]);
- the authorities' answer on a Reported session, a lock lift that decides a flag while a Reported seal stays, and an erase card waiting and a tap on its Continue ([#777]);
- the 30-day erasure of kinds waiting for a misuse card or a first showing ([#776]);
- ticks and quotes withdrawn;
- closures asked for or kept, contests entered or upheld ([#764]), and copies asked for;
- misuse-block entries;
- trial links switched off;
- age-question answers;
- each home erasure, with its moves and writes and any copy's object ID, expiry and scrambled code, and re-marks that change a mark ([#719], [#762]);
- each outage, each date an outage or a notice's acceptance moved, as the new last day per ID, a waiting erasure warning, and each inbox confirmation (see [`dates.md`](dates.md)) ([#772]).
- each refused message's erasure: the text erased, the marker kept, any waiting state cleared, and a session name taken from the refused words reset ([#802]).

A new safety or privacy action joins this list in the same change that adds it, with a test that it survives a restore ([#735]).

**A full restore** applies the log again. Entries that point at something the restore lost are skipped, and applying an entry twice is harmless. New messages and marks since the dump are lost. A copy already made is kept, since the erasure applies again ([#716], [#735]). A logged home erasure is applied again by calling the erasure routine in [`data-model.md`](data-model.md), so its moves and writes happen again before the delete. A replay rewrites a copy's record from the log, and makes and sends nothing ([#719]). Before Crux takes traffic, the release script sets the database endpoint's last-answer time to its last answer before the outage, read from the uptime check's history, which the script's account can read, so the restore counts only the real outage ([#772]). It reads it with Cloud Monitoring's `projects.timeSeries.list` on `uptime_check/check_passed`, and its account holds `monitoring.timeSeries.list`. Cloud Monitoring keeps that history 6 weeks ([#726]). A restore may lose a share tick given, which the learner gives again, and a "Start the window" press, let-in entries and an inbox code not yet used, which the owner redoes ([#719], [#772]).
After a full restore, the release loads the current terms versions and their "What changed" lists into Homes again before Crux takes traffic, so Homes matches the legal pages. An agreement made after the dump is lost with it, so that person is asked again at their next opening ([#769]).

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

- Staging's AI calls are the owner's own tries, the limit tests and the release's guest sitting. They run in the Crux tests workspace and count in its limit ([#726], [#802]). Staging keeps guest mode on ([#726]). Its Supabase pauses after a quiet week, and is restored by hand before a release ([#716]).
- Staging sends no real email, and its daily job runs by hand, so it uses neither Resend's limit nor a Cloud Scheduler job ([#735]).
- The owner-page switches apply to the owner's account on live. Dev, the AI tests and staging have their own settings (see [`live-faults.md`](live-faults.md)) ([#678], [#679]).
- CI starts the local stack, then runs `alembic upgrade head` ([#750]). Dev and CI migrate their throwaway local stack as before; the migration role is for staging and live ([#726]).
- Staging's Worker runs on a subdomain of the domain, in the same Cloudflare account, behind its own copy of the request guards and a gate (see [`security.md`](security.md)). Its address is on Turnstile's hostname list ([#770]).

The tools the code is built with are in [`tools.md`](tools.md) ([#769]).

## Releases

- A release goes to staging first, then to live as a no-traffic revision with a private address, then takes all traffic in one step. Rollback is one step. It sets live's copy of the no-session rule, the burst guard and the hand-block rule to the text committed with the code it restores. Staging's copy stays with staging's code ([#716], [#770], [#781]).
- The release applies the Cloudflare rules with a script on Cloudflare's Rulesets API, updating each rule by its own ID from the committed files in `cloudflare/`: staging's copy at the staging step, the rest at the live step (see [`security.md`](security.md)). Each rule's ID is a fixed reference set in its committed file (Cloudflare's `ref`), so any commit's files find their rules. The first apply creates each rule ([#781]).
- The open-path check runs on staging before live, and on live after each release (see [`security.md`](security.md)) ([#770]).
- **The release's guest sitting:** each release then runs one scripted guest sitting on staging before live, through the gate. It checks only that replies stream back. When the open-path check fails, the sitting does not run. When the sitting fails, the release stops on staging and names the stop reason from Crux's reply, the region message, or no reply ([#726]).
- The release runs from a machine in a country Crux serves ([#726]).
- Migrations are backward-compatible: add first, remove in a later release. A one-step rollback still works ([#716]).
- A live release takes the dump (see [Backups](#backups)), then runs `alembic upgrade head` as the migration role, used only by the release script. Staging's release also migrates as the migration role ([#716], [#726], [#750]).

[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#716]: https://github.com/calmxz/Crux/issues/716
[#719]: https://github.com/calmxz/Crux/issues/719
[#726]: https://github.com/calmxz/Crux/issues/726
[#735]: https://github.com/calmxz/Crux/issues/735
[#750]: https://github.com/calmxz/Crux/issues/750
[#762]: https://github.com/calmxz/Crux/issues/762
[#764]: https://github.com/calmxz/Crux/issues/764
[#769]: https://github.com/calmxz/Crux/issues/769
[#770]: https://github.com/calmxz/Crux/issues/770
[#772]: https://github.com/calmxz/Crux/issues/772
[#776]: https://github.com/calmxz/Crux/issues/776
[#777]: https://github.com/calmxz/Crux/issues/777
[#781]: https://github.com/calmxz/Crux/issues/781
[#802]: https://github.com/calmxz/Crux/issues/802
