# Operations

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers email, knowing when something is wrong, how the owner is told, and the one daily job. What runs where is in [`hosting.md`](hosting.md).

## Email sending

- Resend Free sends Crux's email from the domain: 100 a day and 3,000 a month, from Tokyo's sending region. The account has two-step sign-in ([#717]).
- It carries trial invites and declines, sign-in codes, the account emails, and the owner's daily email ([#717]).
- Sent emails stay in Resend's log for 30 days, and in its backups for up to 7 days after (see [`privacy.md`](privacy.md)) ([#717], [#762]).
- What a learner sees when codes cannot be sent is in [`accounts.md`](accounts.md) ([#674]).

### Who gets the day's emails

Crux keeps shares of Resend's limits, counted on all email sent that day or month, so a flood of one kind cannot take away another ([#735]).

- **The day** is Resend's: a UTC calendar day, 8 am to 8 am Philippine time, as Resend Free counts its 100. Other limits keep the owner's days (see the main file's "Money") ([#763]).
- **The totals** are Resend's own used figures for the day and the month, carried on its replies (`x-resend-daily-quota`, `x-resend-monthly-quota`), plus Crux's sends since that reply. The day restarts at 8 am. The month restarts when Resend's figure drops, since Resend states no Free month start ([#763]).
- A full month, by Crux's count or a refusal, counts as something for the daily email. The 8:05 am run sends it to Resend even though it does not fit, and the answer shows whether Resend's month has restarted. That refusal is expected, so it is not logged as an error ([#763]).
- Resend counts received email and each To, CC and BCC address. So Crux never turns on Resend's receiving, and each email has one address ([#763]).

| Kind | What it covers | Stops when the day's total reaches | Stops when the month's total reaches |
|---|---|---|---|
| Bulk | "It's back" and "spots open" | 40 | 1,200 |
| Codes | Sign-in codes | 80 | 2,400 |
| Required | Closure and misuse emails, contest decisions, erasure warnings, breach notices, re-mark emails, idle warnings, terms changes, copies of data, trial invites and declines, and the owner's daily email | 100 | 3,000 |

- An email over its share waits for the next day, oldest first. A sign-in code is refused instead, as [`accounts.md`](accounts.md) says ([#674], [#735]). Email waiting for room goes, when room comes back, with the daily email first in a new day, then oldest by when it was first due ([#763]).
- A change to the shares is a recorded change ([#735]).
- To meet the 72 hours, a breach notice may use the whole day's room, up to 100, so sign-in codes are refused once the day's total reaches 80 while it sends. Anything past the day's room goes the next day. On that day it gets at most 99, after the daily email, since email sent before 8:05 am, email waiting from before the notice, and codes until the day reaches 80 take room too ([#763]). Its addresses: every account, then waiting requests, invites and declines waiting to send, the let-in list, the "email me" ticks and copies still waiting, each once. The reported hold's email is left out ([#755]).
- A trial request is never kept past its 30 days. One still unsent then is erased without an email (see [`trial.md`](trial.md)) ([#717]).
- **"It's back" emails** go when Crux reopens, as [`spending.md`](spending.md) says. After Google's cap, they wait until a model call succeeds, since Google's month may reset later than Crux's. The daily job tries one small call on the 1st, spent from the owner's share, then hourly until one succeeds ([#675], [#734], [#735]).

### When a required email is late

- A notice period starts when Resend accepts the email, not on its planned date. This covers the idle warnings' 30 and 7 days, the 7 days to contest a misuse closure, the terms' 14 days, and the 2 days after an erasure warning ([#735], [#755]).
- Erasure waits for its notice, for at most 30 days. After that it goes ahead, and the owner is told. The daily email lists any required email still unsent ([#735]).
- A trial request's 30 days do not wait, as above ([#717]).

### When Resend refuses or is down

Resend neither queues nor retries an email it refuses, so Crux does ([#763]):

- A sign-in code is refused with the sender-out message in [`accounts.md`](accounts.md). Over Resend's 10 requests a second, Crux waits the seconds Resend names and sends the code.
- Any other email is retried by reason. Resend down: hourly. Over 10 requests a second: after the seconds Resend names. A quota refusal (`daily_quota_exceeded` or `monthly_quota_exceeded`): the day or the month is marked full, and the email waits for the next room. A code refused on quota marks it full too, and is refused, as above.
- A quota refusal Crux did not expect means its count was wrong, so it is also logged as an error.
- A retry never outlasts how long the spec keeps the email's address, such as a trial request's 30 days. A deadline to send, such as a breach notice's 72 hours, does not end it.
- Retries are Cloud Tasks set for their time (see "The daily job"). A retry task holds only the email's queue ID.
- Accepted does not mean read. A learner who has lost the inbox cannot act on the email, and the data goes at the deadline (see [`privacy.md`](privacy.md)) ([#677]).

### Sending a copy of a learner's data

What a copy holds, and when one is made, is in [`privacy.md`](privacy.md).

- The copy stays in a private Cloud Storage bucket, and never reaches the owner's computer ([#735]).
- **A copy asked for while closing:** the daily job makes it on day 8, and sends the link itself, as a required email ([#735]). The copy, its address and this email are written outside the account before it is erased (see [`data-model.md`](data-model.md)) ([#719]).
- **A copy asked for by email:** the daily email reminds the owner, who checks the request is really the learner's and makes it with the owner page's button ([#735], [#755]).
- The email links to the copy page, with a long random code. Each opening while the link is live signs a download link that works for 15 minutes and sends the learner to it, so a delayed email cannot use it up. The link is live for 7 days from sending, plus the days Crux was down ([#735], [#762]).
- The backend signs as a separate service account that can read only the copies bucket, so a copy link can never open anything else. No Google key is stored (see [`hosting.md`](hosting.md)) ([#762]).
- The code is stored scrambled. A network that tries 10 wrong codes in an hour is refused for the rest of the hour ([#762]).
- Once the link has expired, the page refuses the code. An unknown code gets the same page (see [`account-screens.md`](account-screens.md)) ([#762]).
- The email says when the link expires, and to keep it private ([#735]).
- Once the link has expired, the daily job erases the copy, its address and its code ([#735], [#762]).

### The Crux email

The address is privacy@ the domain (see [`privacy.md`](privacy.md)) ([#717]).

- **In the trial:** Cloudflare Email Routing forwards it to a dedicated Crux Gmail, and replies come from that Gmail. It has no processor agreement, which the owner accepted for the trial.
- **From opening:** Zoho Mail's free plan if Zoho offers it to Crux (it is available only in some data centers) and Zoho's processor agreement covers it, otherwise Google Workspace Business Starter, about USD 84 a year ([#762]). Trial mail in the Gmail is moved or deleted at the switch.
- Crux's emails that ask for a reply carry privacy@ as their reply address: the warning, dismissal and closure emails, the contest decisions, the erasure warning and the closing email. Invites, copy links and sign-in codes carry none, so a reply can't bring a link into the inbox ([#755]).

## Errors

- Google Cloud Error Reporting reads the backend's logs on Cloud Run ([#717]).
- Browser errors are posted to `/api/client-error` and logged there. A tiny handler catches most load failures ([#717]). It is its own file from Crux's address, loaded first ([#769]). The build ticket loads it as a plain blocking script before the module, not cached. A hash for an inline handler is the alternative ([#769]).
- Each release keeps private source maps, and a local command turns a minified browser trace into file and line ([#717]).
- New kinds of error push to the Google Cloud app, at most 20 an hour per project, then quiet for 6 hours. The uptime check is separate ([#717]).
- Errors carry no learner text: the type, the place in the code and the request number. Any message that could hold learner text is replaced, for example "[answer, 58 characters]" ([#717]).
- **At opening:** if only browser errors were hard to fix in the trial, Sentry is added for the browser. If Error Reporting failed more broadly, Sentry replaces it for both, with Error Reporting's notifications off. Either way Sentry collects no network addresses: its browser setting off, "Prevent Storing of IP Addresses" on, and a rule removing the location it derives ([#717]). Addresses can still reach Sentry through request headers such as `X-Forwarded-For`, cookies and query parameters, so the SDK's deny lists cover all three, and the backend SDK's user info is off ([#762]). The Worker's country and address headers join those deny lists. If added, Sentry is bundled and sends through Crux's own address (see [`security.md`](security.md)) ([#769]).

## The outside check

- Google Cloud Monitoring uptime checks open the public link and, through the Worker, an endpoint that runs one tiny database query and answers only "ok" ([#716], [#717]).
- A third check calls an endpoint that fails if the daily job has not finished in 26 hours, so a missed run pushes at no cost ([#735]).
- They run every 5 minutes, from 3 or more checker places outside the EU and UK. Alerts push to the Google Cloud app ([#717]).
- This also keeps the backend warm and Supabase from pausing ([#716]).
- About 78,000 checks a month (3 checks x 3 places x 12 an hour x 24 x 30), of the 1 million free ([#717], [#735]).

## How the owner is told

### A push to the Google Cloud app

A push comes from a marked log line and an alert rule ([#717]). It goes:

- when the month's budget runs out;
- when the day's ceiling is hit, saying when, at most once a day ([#675], [#728] Answer 8);
- when Google's Gemini cap is reached, with Crux's count beside Google's cap ([#728] Answer 8);
- when the 20 GB store is full;
- when the owner's share reaches 100%;
- for each new access request;
- for a misuse flag raised at once ([#733]);
- when an AI test round fails (see [`ai-tests.md`](ai-tests.md)) ([#736]);
- when Resend is down, or the email day or month is full, at most once a day each: "Resend is down: 12 emails waiting". The daily email may not get through then ([#763]).

New kinds of error and uptime alerts push too (see above). That covers the Cloud Run cap and a missed daily job, since no log line can be written then ([#735]).

There are two alert rules: one for access requests, and one for everything else. Each rule can send at most 20 notifications a day, so a flood of requests cannot silence an urgent message. Anything past 20 still shows on the owner page and in the daily email ([#735]).

### The daily email

One email through Resend, at 8:05 am Philippine time from the daily job, first in Resend's new day, on days with something in it ([#717], [#763]):

- the budget at 50% and 80%;
- the learner cap filled;
- the owner's share at 80%;
- Crux's count against Google's bill, when the gap is over 10%, with where it is;
- how many learners were turned away the day before ([#728] Answer 8). For the trial's wording, see [`spending.md`](spending.md) ([#734]);
- code requests refused because the sender's share ran out ([#735]);
- new feedback as a count, and withdrawn quotes (see [`feedback.md`](feedback.md));
- requests still waiting (see [`trial.md`](trial.md));
- misuse flags (see [`misuse.md`](misuse.md)), each by its number, whose it is and the date: "Flag 4821 · An account · 10 Mar · Open ›", or "Flag 4812 on Link K7Q-4MP · 10 Mar · Open ›". No kind and no email. The kind, the record line, the sessions and the actions are in the owner page's Safety area ([#733], [#764]);
- the day before a misuse closure is erased: "1 closed account is erased tomorrow. Check the Crux inbox for a contest." ([#753]);
- a copy asked for by email, still to be sent (see [`privacy.md`](privacy.md)) ([#735]);
- an erasure waiting for its date: "1 erasure on 15 Mar: check the inbox for a reply." ([#755]);
- a required email still unsent, and a check paused by repeated blocks ([#735]);
- Resend's month full, by Crux's count or a refusal ([#763]);
- a monthly AI test round that did not run, and a full test cap ([#736]).

### The services' own emails

Emails from Google Cloud, Cloudflare, Supabase, Resend, GitHub, and later Zoho or Workspace go to the owner's own email, the one on the owner's phone. Google Cloud's Essential Contacts for Security, Billing, Suspension and Technical point there on the Crux projects ([#717]).

## Reading Google's bill

- Google's billing export goes to a BigQuery dataset in Singapore, read by the daily job through a read-only role. It is turned on before the first Gemini call, since it has no backfill ([#717]).
- The job reads the last complete day, per model and token type, with credits on their own lines, and compares it with Crux's own count ([#717]).
- A gap over 10% goes in the daily email, for example "Google +35%: 3.5 Flash-Lite output tokens +USD 0.10" ([#717]).
- This is free at this size. Crux's own count stays what enforces the limits ([#717]).

## The daily job

All scheduled work runs in one job: Cloud Scheduler calling the tasks service, at 8:05 am Philippine time, 5 minutes after Resend's day restarts ([#763]). Cloud Scheduler is free for up to 3 jobs per billing account, and 2 go to the peak schedule if the fallback in [`hosting.md`](hosting.md) is ever used ([#716], [#728] Answer 7).

The job acts on every date that has passed, so a missed run catches up on the next one. Dates that give someone a chance to act (the undo, the contest period, notice periods, the trial's notice, a copy link's 7 days) first gain the days Crux was down, worked out from the gap between runs ([#735], [#762]). It does:

**Backups and reports**

- the daily database dump ([#716], [#728] Answer 7);
- the bill comparison and the daily email ([#717]);

**Email due**

- "it's back" emails on the 1st, and any email waiting for its share ([#675], [#735]);
- idle accounts' warnings at 30 and 7 days ([#677]);
- the 30-day request declines ([#717], [#728] Answer 7);

**Erasure**

- accounts past their 7-day undo, making and sending any copy asked for first ([#677], [#728] Answer 7, [#733], [#735]);
- misuse closures on day 8, unless a contest holds them ([#733]);
- idle accounts at 12 months, once their warnings have run ([#677], [#735]);
- a copy and its address when the link expires ([#735]);
- "email me if spots open" addresses at 3 months, and the misuse block's scrambled email at 12 months ([#677]);
- a decline's saved details once it drops out of the 7 days with no flag, never kinds waiting for a misuse card (see [`misuse.md`](misuse.md)) ([#733], [#764]);
- a withdrawn quote's words at 14 days, if its account has gone ([#677], [#735]);
- a dead trial link's stub, at the trial's end or 12 months after the link died, whichever comes first ([#719]);
- a dead trial link's feedback answers and quote permissions (not after a Yes or its holder's erasing, which remove them at once), 6 months after the trial ends or 12 months after the link died, whichever comes first, unless published ([#719]);
- any scrambled "told Crux is full" email or listed bucket object that its Cloud Tasks job or the erasure missed, and any copy object with no record ([#719]);
- per-account spend, rolled into totals with no account ([#677]);

**Ending things**

- let-in entries older than 7 days, not used or kept. Sign-up also ignores an expired entry ([#679], [#728] Answer 7);
- the trial, on its date ([#733]).

**The exceptions:** records with a shorter life than a day cannot wait for this job. Network addresses in the code limits and wrong-link counts, and the code limits' email addresses, are each deleted by a Cloud Tasks job set for when they expire ([#717], [#735]). Sign-in codes expire by checking their time when used. The daily job sweeps anything these missed, such as during a pause, and an unused code's email ([#735]). Email retries are Cloud Tasks set for their time too, so they need no Cloud Scheduler job (see "When Resend refuses or is down") ([#763]).

Some things happen by the date alone, with no job: a re-run's budget returning on the 1st, and the go-public bar judged at the end of its last day ([#676], [#734], [#735]).

## Gaps

- **Whether alerting starts to cost:** Google may charge from no sooner than 1 September 2027. Google's pricing bills a log-based rule as a metric reference, about USD 0.35 a month, so about USD 0.70 a month for the two rules ([#717], [#762]).
- **Zoho's free plan:** whether Zoho offers it to Crux, and whether its processor agreement covers it. Open on [#726] ([#717], [#762]).
- **Resend's figures on every reply:** Resend's page says only that "the API returns headers that track your email sending quotas". Checked at the build's first real send, a refusal included. If they are missing, how Crux counts comes back as a recorded change ([#763]).
- **Retry mechanics, a build check:** how retries avoid double sends, including after a restore; stale dates in a retried email; email that can never be sent; and a daily email still waiting when the next is due, with the stop records it covers ([#763]).

## On screen

The copy's email with its link is in [`account-screens.md`](account-screens.md) ([#753]). The daily email's layout and the owner page are in [`owner-screens.md`](owner-screens.md) ([#755]). The rest of the layout is not decided (see the main file's Gaps).

[#674]: https://github.com/calmxz/Crux/issues/674
[#675]: https://github.com/calmxz/Crux/issues/675
[#676]: https://github.com/calmxz/Crux/issues/676
[#677]: https://github.com/calmxz/Crux/issues/677
[#679]: https://github.com/calmxz/Crux/issues/679
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#726]: https://github.com/calmxz/Crux/issues/726
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
