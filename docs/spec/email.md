# Email

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers how Crux sends email: who gets the day's emails, late and refused emails, copies of data and emailed requests, and the Crux email. Errors, uptime and how the owner is told are in [`operations.md`](operations.md).

## Email sending

- Resend Free sends Crux's email from the domain: 100 a day and 3,000 a month, from Tokyo's sending region. The account has two-step sign-in ([#717]).
- It carries trial invites and declines, sign-in codes, the account emails, and the owner's daily email ([#717]).
- Sent emails stay in Resend's log for 30 days, and in its backups for up to 7 days after (see [`privacy.md`](privacy.md) and [`terms-and-policy.md`](terms-and-policy.md)) ([#717], [#762]).
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

- A notice period starts when Resend accepts the email, not on its planned date. What a screen shows meanwhile, and what happens when it waits 30 days, are in [`dates.md`](dates.md) ([#735], [#755], [#772]).
- The daily email lists any required email still unsent ([#735]).
- A trial request's 30 days do not wait, as above ([#717]).

### When Resend refuses or is down

Resend neither queues nor retries an email it refuses, so Crux does ([#763]):

- A sign-in code is refused with the sender-out message in [`accounts.md`](accounts.md). Over Resend's 10 requests a second, Crux waits the seconds Resend names and sends the code.
- Any other email is retried by reason. Resend down: hourly. Over 10 requests a second: after the seconds Resend names. A quota refusal (`daily_quota_exceeded` or `monthly_quota_exceeded`): the day or the month is marked full, and the email waits for the next room. A code refused on quota marks it full too, and is refused, as above.
- A quota refusal Crux did not expect means its count was wrong, so it is also logged as an error.
- A retry never outlasts how long the spec keeps the email's address, such as a trial request's 30 days. A deadline to send, such as a breach notice's 72 hours, does not end it.
- Retries are Cloud Tasks set for their time (see "The daily job" in [`dates.md`](dates.md)). A retry task holds only the email's queue ID.
- Accepted does not mean read. A learner who has lost the inbox cannot act on the email, and the data goes at the deadline (see [`privacy.md`](privacy.md)) ([#677]).

### Copies and requests

- A copy of a learner's data is sent on request to the Crux email, within a month, as for every data request, unless Crux's email can't go. It holds conversations, record, preferences, check answers and photos (data files plus readable text) and uploaded files, as a zip. Every copy, at closing or at Crux's closing too, also holds the decline records the learner is told about: kinds waiting for a misuse card with their count and decision date, or the count and date alone after the 30 days; a misuse closure's count, kinds and date; and a misuse warning, as "Warned on 4 Mar". It leaves out declines still counting toward a flag, an open flag and a sealed flag's kind, and never names the mark that flags at once. Kinds are named in the harm list's words, or "blocked by Google". A waiting erase card shows as its line and date: "2 May: Crux's owner erased your sealed session "Reaction rates", with its 2 mastered topics." ([#776], [#777]) The owner checks the request came from the account's own address. A button on the owner page then makes it, as the copy at closing is made, without the owner reading through it ([#677], [#755]). It reaches the learner as a private 7-day link (see [Sending a copy](#sending-a-copy-of-a-learners-data)) ([#735]).
- A request by email is entered on the owner page by pasting the sender's address, used only to find the account and never stored ([#755]).
- **Deleting an account by email** starts the same closing as Close account, with its email and 7-day undo. It is not offered for an account already closing or locked by a sealed flag. Its timing, and what happens if its email can't go, is in [`dates.md`](dates.md) ([#755], [#772]).
- **A session or file during a closing** is found by the exact name in the learner's email, leaving out sealed sessions. Crux emails the account's address, "We'll erase 'Thesis statements' (made 2 Mar) after 11:59 pm on 15 Mar, Philippine time. Didn't ask? Reply before then to stop it.", its last day 2 days after Resend accepts it. Unless the owner cancels, it goes as [`dates.md`](dates.md) says, even if the account is restored. A session held for the owner's decision waits for the decision ([#755], [#772]).

### Sending a copy of a learner's data

What a copy holds, and when one is made, is in [Copies and requests](#copies-and-requests).

- The copy stays in a private Cloud Storage bucket, and never reaches the owner's computer ([#735]).
- **A copy asked for while closing:** the daily job makes it on day 9, and sends the link itself, as a required email ([#735], [#772]). The copy, its address and this email are written outside the account before it is erased (see [`data-model.md`](data-model.md)) ([#719]).
- **A copy asked for by email:** the daily email reminds the owner, who checks the request is really the learner's and makes it with the owner page's button ([#735], [#755]).
- The email links to the copy page, with a long random code after a `#` (see [`security.md`](security.md)) ([#770]). Each opening while the link is live signs a download link that works for 15 minutes and sends the learner to it, so a delayed email cannot use it up. The link is live until 11:59 pm on the 7th day after Resend accepts it, plus any outage days (see [`dates.md`](dates.md)) ([#735], [#762], [#772]).
- The backend signs as a separate service account that can read only the copies bucket, so a copy link can never open anything else. No Google key is stored (see [`hosting.md`](hosting.md)) ([#762]).
- The code is stored scrambled. A network that tries 10 wrong codes in an hour is refused for the rest of the hour. Its address is kept only that hour ([#762], [#770]).
- Once the link has expired, the page refuses the code. An unknown code gets the same page (see [`account-screens.md`](account-screens.md)) ([#762]).
- The email says when the link expires, and to keep it private ([#735]).
- Once the link has expired, the daily job erases the copy, its address and its code ([#735], [#762]). A copy whose email is still not accepted 30 days after it was made is erased too, and the owner is told ([#772]).

### The Crux email

The address is privacy@ the domain (see [`terms-and-policy.md`](terms-and-policy.md)) ([#717]).

- **In the trial:** Cloudflare Email Routing forwards it to a dedicated Crux Gmail, and replies come from that Gmail. It has no processor agreement, which the owner accepted for the trial.
- **From opening:** Zoho Mail's free plan if Zoho offers it to Crux (it is available only in some data centers) and Zoho's processor agreement covers it, otherwise Google Workspace Business Starter, about USD 84 a year ([#762]). Trial mail in the Gmail is moved or deleted at the switch.
- Crux's emails that ask for a reply carry privacy@ as their reply address: the warning, dismissal and closure emails, the contest decisions, the erasure warning and the closing email. Invites, copy links and sign-in codes carry none, so a reply can't bring a link into the inbox ([#755]).

## Gaps

- **Zoho's free plan:** whether Zoho offers it to Crux, and whether its processor agreement covers it. Open on [#726] ([#717], [#762]).
- **Resend's figures on every reply:** Resend's page says only that "the API returns headers that track your email sending quotas". Checked at the build's first real send, a refusal included. If they are missing, how Crux counts comes back as a recorded change ([#763]).
- **Retry mechanics, a build check:** how retries avoid double sends, including after a restore; stale dates in a retried email; email that can never be sent; and a daily email still waiting when the next is due, with the stop records it covers ([#763]).

## On screen

The copy's email with its link is in [`account-screens.md`](account-screens.md) ([#753]).

[#674]: https://github.com/calmxz/Crux/issues/674
[#675]: https://github.com/calmxz/Crux/issues/675
[#677]: https://github.com/calmxz/Crux/issues/677
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#726]: https://github.com/calmxz/Crux/issues/726
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#753]: https://github.com/calmxz/Crux/issues/753
[#755]: https://github.com/calmxz/Crux/issues/755
[#762]: https://github.com/calmxz/Crux/issues/762
[#763]: https://github.com/calmxz/Crux/issues/763
[#770]: https://github.com/calmxz/Crux/issues/770
[#772]: https://github.com/calmxz/Crux/issues/772
[#776]: https://github.com/calmxz/Crux/issues/776
[#777]: https://github.com/calmxz/Crux/issues/777
