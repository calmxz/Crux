# Operations

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers knowing when something is wrong and how the owner is told. Email sending, copies of data, and emailed requests are in [`email.md`](email.md). When dates take effect and the one daily job are in [`dates.md`](dates.md). What runs where is in [`hosting.md`](hosting.md).

## Errors

- Google Cloud Error Reporting reads the backend's logs on Cloud Run ([#717]).
- Browser errors are posted to `/api/client-error` and logged there. A tiny handler catches most load failures ([#717]). It is its own file from Crux's address, loaded first ([#769]). The build ticket loads it as a plain blocking script before the module, not cached. A hash for an inline handler is the alternative ([#769]).
- Each release keeps private source maps, and a local command turns a minified browser trace into file and line ([#717]).
- New kinds of error push to the Google Cloud app, at most 20 an hour per project, then quiet for 6 hours. The uptime check is separate ([#717]).
- Errors carry no learner text: the type, the place in the code and the request number. Any message that could hold learner text is replaced, for example "[answer, 58 characters]" ([#717]).
- Errors carry no theme choice, and nor does Sentry if it is added (see [`themes.md`](themes.md)) ([#779]).
- **At opening:** if only browser errors were hard to fix in the trial, Sentry is added for the browser. If Error Reporting failed more broadly, Sentry replaces it for both, with Error Reporting's notifications off. Either way Sentry collects no network addresses: its browser setting off, "Prevent Storing of IP Addresses" on, and a rule removing the location it derives ([#717]). Addresses can still reach Sentry through request headers such as `X-Forwarded-For`, cookies and query parameters, so the SDK's deny lists cover all three, and the backend SDK's user info is off ([#762]). The Worker's country and address headers join those deny lists. If added, Sentry is bundled and sends through Crux's own address (see [`security.md`](security.md)) ([#769]).

## The outside check

- Google Cloud Monitoring uptime checks open the public link and, through the Worker, an endpoint that runs one tiny database query and answers "ok" ([#716], [#717]).
- A third check calls an endpoint that fails if the daily job has not finished in 26 hours, so a missed run pushes at no cost ([#735]).
- The database endpoint also stores when it last answered, which measures outages (see [`dates.md`](dates.md)) ([#772]).
- They run every 5 minutes, from 3 or more checker places outside the EU and UK. Alerts push to the Google Cloud app ([#717]).
- This also keeps the backend warm and Supabase from pausing ([#716]).
- About 78,000 checks a month (3 checks x 3 places x 12 an hour x 24 x 30), of the 1 million free ([#717], [#735]).

## How the owner is told

### A push to the Google Cloud app

A push comes from a marked log line and an alert rule ([#717]). It goes:

- when the month's budget runs out;
- when the day's ceiling is hit, saying when, at most once a day ([#675], [#728] Answer 8);
- when a workspace limit or the credit stops Crux, the urgent push ([#728] Answer 8, [#802]);
- when the accounts' or the guests' distress pot runs out, at most once a day each ([#802]);
- when the tutor's report ends a guest session for content involving minors, at most once a day (see [`landing-screens.md`](landing-screens.md)) ([#802]);
- when the 20 GB store is full;
- when the owner's share reaches 100%;
- for each new access request;
- for a misuse flag raised at once ([#733]);
- when an AI test round fails (see [`ai-tests.md`](ai-tests.md)) ([#736]);
- when one of Crux's own notices has waited 30 days, or an emailed request needs confirming from the Crux inbox (see [`dates.md`](dates.md)) ([#772]);
- when Resend is down, or the email day or month is full, at most once a day each: "Resend is down: 12 emails waiting". The daily email may not get through then ([#763]).

New kinds of error and uptime alerts push too (see above). That covers the Cloud Run cap and a missed daily job, since no log line can be written then ([#735]).

There are two alert rules: one for access requests, and one for everything else. Each rule can send at most 20 notifications a day, so a flood of requests cannot silence an urgent message. Anything past 20 still shows on the owner page and in the daily email ([#735]). Beside them, two metric alerts on Crux's logs push when `/api` calls run high. The owner is also told when a hand block's lift fails, a block outlives 36 hours, or the list holds anything but single addresses (see [`security.md`](security.md)) ([#770]).

### The daily email

One email through Resend, at 8:05 am Philippine time from the daily job, first in Resend's new day, on days with something in it ([#717], [#763]):

- the budget at 50% and 80%;
- the learner cap filled;
- the owner's share at 80%;
- how many learners were turned away the day before ([#728] Answer 8). For the trial's wording, see [`spending.md`](spending.md) ([#734]);
- code requests refused because the sender's share ran out ([#735]);
- new feedback as a count, and withdrawn quotes (see [`feedback.md`](feedback.md));
- requests still waiting (see [`trial.md`](trial.md));
- misuse flags (see [`misuse.md`](misuse.md)), each by its number, whose it is and the date: "Flag 4821 · An account · 10 Mar · Open ›", or "Flag 4812 on Link K7Q-4MP · 10 Mar · Open ›". No kind and no email. The kind, the record line, the sessions and the actions are in the owner page's Safety area ([#733], [#764]);
- from the first run after a misuse closure's last day until it is erased, unless a contest is entered: "1 closed account's contest time has ended. It's erased on 12 Nov: check the Crux inbox for a contest.", its date updated if an outage delays the run, also kept in the owner page's Today area ([#753], [#772]);
- a copy asked for by email, still to be sent (see [Copies and requests](email.md#copies-and-requests)) ([#735]);
- an erasure warning waiting: "1 erasure warning ends on 15 Mar: check the Crux inbox for a reply.", then from the first run after that date, "1 erasure warning has ended. Its session is erased on 17 Mar: check the Crux inbox for a reply.", its date updated if an outage delays the run, also kept in the Today area ([#755], [#772]);
- dates an outage moved: "Crux was down 40 minutes on 10 Nov: 3 dates moved by a day." ([#772]);
- a request asked for by email whose email is still not accepted, and from 7 days after the owner entered it, the prompt to confirm it from the Crux inbox (see [`dates.md`](dates.md)) ([#772]);
- a required email still unsent, a check paused by repeated refusals, a refused re-mark, and a refusal category Crux doesn't know, by name ([#735], [#802]);
- Resend's month full, by Crux's count or a refusal ([#763]);
- a monthly AI test round that did not run, and a full test cap ([#736]).

### The services' own emails

Emails from Google Cloud, Cloudflare, Supabase, Resend, GitHub, and later Workspace go to the owner's own email, the one on the owner's phone. Google Cloud's Essential Contacts for Security, Billing, Suspension and Technical point there on the Crux projects ([#717]).

## Checking the bill

There is no daily bill comparison, since an individual Anthropic account has no Admin API. The owner compares Crux's count with the Console's Usage page by hand at each monthly test round. Crux's own count stays what enforces the limits ([#717], [#802]).

## Gaps

- **Whether alerting starts to cost:** Google may charge from no sooner than 1 September 2027. Google's pricing bills a log-based rule as a metric reference, about USD 0.35 a month. The two rules and the two metric alerts are about USD 1.40, plus about USD 0.10 for the points the alerts return, so about USD 1.50 a month ([#717], [#762], [#770]).

## On screen

The daily email's layout and the owner page are in [`owner-screens.md`](owner-screens.md) ([#755]). The rest of the layout is not decided (see the main file's Gaps).

[#675]: https://github.com/calmxz/Crux/issues/675
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#728]: https://github.com/calmxz/Crux/issues/728
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#736]: https://github.com/calmxz/Crux/issues/736
[#753]: https://github.com/calmxz/Crux/issues/753
[#755]: https://github.com/calmxz/Crux/issues/755
[#762]: https://github.com/calmxz/Crux/issues/762
[#763]: https://github.com/calmxz/Crux/issues/763
[#764]: https://github.com/calmxz/Crux/issues/764
[#769]: https://github.com/calmxz/Crux/issues/769
[#770]: https://github.com/calmxz/Crux/issues/770
[#772]: https://github.com/calmxz/Crux/issues/772
[#779]: https://github.com/calmxz/Crux/issues/779
[#802]: https://github.com/calmxz/Crux/issues/802
