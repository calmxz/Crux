# Research: open hosting checks (#726)

Question: five facts left open by #716, #675, #717 and #722, each able to change a recorded decision. Later tickets added questions from #770 and #772, and #802 moved item 5 to Haiku 5.5.

This file is the index. Each item's detail, sources and logs are in [`open-hosting-checks/`](open-hosting-checks/). Items 1 to 4 were read on 2026-11-02. The hands-on test, item 5, and the #770 and #772 questions were done on 2026-11-21.

## Short answer

| Item | Answer | Goes against the spec? | Detail |
|---|---|---|---|
| 1. Row-level security through the pooler | Safe in transaction mode when each request sets the home with `set_config(..., true)` or `SET LOCAL` inside one explicit transaction. A local test passed 41 of 41 checks, and its controls showed that a session-level `SET` leaks. An unset home reads as an empty string on a reused connection, so policies need `nullif`. | No. #716's rule holds. The role, the `nullif` and the ban on session-level `SET` are not yet in the spec; #719 is where the ticket says the role goes. | [`pooler-docs.md`](open-hosting-checks/pooler-docs.md), [`pooler-test.md`](open-hosting-checks/pooler-test.md) |
| 2. Spend cap and the free tier | The cap counts gross list-price use, before the free tier. The page does not say which services use gross estimates, so Cloud Run being gross is a reading (rechecked 2026-11-21). | Yes, as #716 already reads it. | [`spend-cap.md`](open-hosting-checks/spend-cap.md) |
| 3. Alerting charges | From no sooner than 1 September 2027: USD 0.35 a month per metric reference, log-based rules included. #770's four rules come to about USD 1.49 a month. The log-based metric uses at most about 0.33 MiB of the free 150 MiB. | No change past #770's figure. | [`alerting.md`](open-hosting-checks/alerting.md), [`alerting-and-uptime-history.md`](open-hosting-checks/alerting-and-uptime-history.md) |
| 4. Zoho Mail's free plan | Withdrawn: the Crux email stays the Crux Gmail until a one person corporation runs Crux (#717, #795). | No longer asked. | [`zoho.md`](open-hosting-checks/zoho.md) |
| 5. Server time per sitting and upload | A sitting holds requests open about 68 s; a 100-page outline read 14 to 22 s; a 100-page conversion 6 to 10 s. 180 to 240 sittings use 9.5% to 12.7% of the free tier's CPU part. At full use of the learners' USD 25, the USD 6 gross live cap trips. | Yes, see below. | [`server-time.md`](open-hosting-checks/server-time.md), [`cloud-run-billing.md`](open-hosting-checks/cloud-run-billing.md) |
| #772. Uptime-check history | `projects.timeSeries.list` on `uptime_check/check_passed`. Its permission, `monitoring.timeSeries.list`, is in `roles/monitoring.viewer`; a custom role with only that permission is a reading. Kept 6 weeks; resolution at the check period is a reading. | No. | [`alerting-and-uptime-history.md`](open-hosting-checks/alerting-and-uptime-history.md) |

## Findings that touch recorded decisions

This research reports facts. Each choice belongs to the owner.

| Finding | Recorded decision it touches |
|---|---|
| At full use of the learners' USD 25, the USD 6 gross live cap trips. It trips at about USD 19 to 22 of AI spend through live in a month. If live had the whole free tier, USD 2.21 to 3.00 would be left to pay; the owner's USD 10 Developer Program credit may pay it. | #716's caps, #675's hosting costs, the map's constraints line |
| If all of the tests' USD 20 ran through staging, staging's USD 2 cap would trip. | #716's staging cap, #678's tests |
| The converter needs at least 2 GiB: at 1 GiB, a later conversion in the same instance failed. 2 GiB held 12 in a row, but its high-water mark reached the full 2 GiB. | #716's converter, "1 to 2 GiB" in `hosting.md` |
| The first sitting on a 20-page photo-heavy slice costs 2.77 sittings' worth, so a day's limit ends at reply 9 or 10 of 15. | #675's tutoring limit, #802's sitting's worth |
| A plain sitting costs USD 0.00927 with nothing cached and USD 0.00820 with the instructions cached, around the spec's USD 0.0084. | #802's sitting's worth, in `spending.md`'s Gaps |
| At every limit, with 10-problem worded checks, 25 learners would spend USD 27.46 a month, past the USD 25. With 6-problem checks, USD 19.49. | #802's re-cost, #675's limits |
| Policies must read the home with `nullif(current_setting(..., true), '')`, and no code may run a session-level `SET`. | #719, as a build rule |
| Splitting a Gotenberg PDF page by page carries every image in the file into each part, unless each page is pruned first. | A build check for the topic slice and the outline read |

## Still open after this research

- **The hosted pooler's leak check.** Supabase's value for `txn_mode_leak_action` is not stated. The local stack's is `ignore`.
- **Gross or net for Cloud Run's cap.** The first month's spend amount on the budget page shows which.
- **Cloud Run's CPU speed and network time.** The times were measured on the owner's computer. The first month's billing report shows the real figures.
- **Whether AI tests run through staging's Cloud Run** or call Anthropic directly.

## How the items were done

- Items 1 to 4, the #770 and #772 questions, and Cloud Run's prices come from primary sources: Google Cloud, Supabase, PostgreSQL, Supavisor and Zoho pages. Each file lists its sources.
- Item 1's test ran on the Supabase CLI's local stack, with the pooler forced to one connection.
- Item 5's runs used the #802 teaching harness, Haiku 5.5 through the Anthropic API, and Gotenberg 8.40.0 in Docker. They cost USD 0.24.
- A fresh agent checked every figure and quote against its log or page before publication. Two Zoho help-page quotes could only be read through a fetch tool, since the page renders with JavaScript. The copied #802 harness matches its source files, apart from `common.py`'s key path.
