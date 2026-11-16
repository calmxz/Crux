# Privacy and deleting

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what the owner may read, deleting and closing, and how long data stays. The Terms of Use and the Privacy Policy are in [`terms-and-policy.md`](terms-and-policy.md). Harm and misuse are in [`misuse.md`](misuse.md). The trial's own notices are in [`trial.md`](trial.md). Where data lives and what is logged are in the main file's "Where data lives".

## When the owner reads a session

The owner reads a conversation only in two cases ([#677]):

- **Shared:** on the feedback page, the learner ticks to share, and picks a named session or "all my sessions". The tick warns: "This shares everything you wrote, including anything personal". The owner reads each one from its start up to the tick. Later messages and later sessions stay closed. Unticking in Settings ends the owner's access (see [`feedback.md`](feedback.md)) ([#677], [#733]).
- **Flagged:** a flag opens only the sessions where the tutor declined something, chat text only. The owner reads each one from its start up to the flag, plus any new declines while the flag waits. Access ends when the owner acts on the flag or, after a closure, when the lock ends ([#677], [#733]).

No flag shows the owner a file or a photo, and a sealed flag shows no session at all (see [`misuse.md`](misuse.md) and [`sealed-sessions.md`](sealed-sessions.md)). The owner page never opens a declined file, even on a share. A copy includes it, packed unread when the copy is made, unless it is sealed ([#733]). Other sessions stay closed. Deleting a session erases it at once, including from the owner's view ([#733]).

Repairs from a backup are done by script, and the owner sees counts, not content ([#716]). The owner page's feedback rules, including who sent an answer, are in [`feedback.md`](feedback.md) ([#677]).

## Deleting and closing

### What erases at once

- Removing a file, or deleting a session, erases it at once ([#677]). A removed file's earlier replies stay in the conversation until the session is deleted (see [`files.md`](files.md)) ([#732]).

### Closing an account

- Closing starts in Settings, in a confirm dialog where the learner types "delete" before Close account works ([#753]). The dialog names what is erased ("your 4 sessions, your files, and your record of 3 mastered topics") and the date the 7 days end, with a "Send me a copy first" button ([#677], [#733]).
- An email follows: "Your Crux account closes at 11:59 pm on 10 Nov, Philippine time. Sign in to keep it." ([#677], [#772])
- During the 7 days, the next time they open Crux, on any browser, they see "Keep my account / Sign out", with the same button. There is no tutoring until they pick. A habitual visit does not cancel by accident ([#677], [#733]).
- Keeping leaves the account as it was. Sign out lets the closing go on ([#677]).
- Otherwise the account and its data are erased on day 9, at the first daily run after the last day (see [`dates.md`](dates.md)). From 12:00 am after the last day, the account opens to a closed card only ([#677], [#728] Answer 7, [#772]).
- **If they asked for a copy:** on day 9, Crux makes the copy itself, erases the account and everything else, and emails a private link to the copy page that works until 11:59 pm on the 7th day after it is sent (see [`email.md`](email.md)). It keeps only the copy, the address and the link's scrambled code until the link expires, or 30 days unsent, and a missed link cannot be made again. Keeping the account cancels the copy ([#733], [#735], [#762], [#772]).
- A request that arrives by email during a closing, including a misuse closure, is entered on the owner page, or Crux cannot know about it ([#733]).
- On day 9, the feedback words leave the owner page. Anonymous counts and yes/no answers stay as tallies. The account's quote permissions are withdrawn too (see [`feedback.md`](feedback.md)) ([#677], [#772]).
- The owner chose the undo for the meantime. Erasing at once is the fallback if the undo causes problems ([#677]).
- An under-18 closure skips the undo, and takes its counts off first (see [`age.md`](age.md)) ([#677], [#681]). A published quote's note stays until the owner removes it (see the table below) ([#734]). A misuse closure has its own 7 days (see [`misuse.md`](misuse.md)) ([#733]).
- A closed account's spot under the cap stays used (see [`accounts.md`](accounts.md)) ([#675], [#677]).

### Idle accounts

An account with no visit for 12 months is closed and erased, after emails 30 days and 7 days before. One visit keeps it: any signed-in request, opening the app included ([#719]). A learner who has lost the inbox cannot act on the emails, and the data goes at the deadline ([#677]). If a warning goes out late, the deadline moves, so the full notice is given (see [`dates.md`](dates.md)). The Privacy Policy says so ([#735]). Past the deadline, the account opens to a closed card only, and is erased at the next daily run ([#772]).

### If Crux closes, or goes paid

- **If Crux closes:** every learner is emailed at least 30 days ahead where possible: "Crux closes at 11:59 pm on 15 Feb, Philippine time. Want a copy of your data? Email us before then." Learning continues normally until then. Every account and its data is then erased, once each copy asked for by then has been sent and its link has ended, and the anonymous tallies stay ([#677], [#772]).
- The closing email goes on a day with few sign-ups, so it fits the sender's daily limit ([#677], [#728]).
- **If the go-public bar is not met:** Crux is not shut down. It stays deployed as a portfolio project, under these same rules ([#676], [#677]).
- **If a paid launch follows:** a v1 account moves only if the learner agrees to the new terms when they next open Crux. Anyone who does not answer is treated as a closing, with the 30 days' notice ([#677]).

## How long things stay

| Data | How long (job-enforced limits run longer only while the job is down) |
|---|---|
| Conversations, files, check answers and their marks | Until the session is deleted or the account is erased ([#671], [#677]) |
| Account marks (dates of steps first reached, latest pay answer) | Until the account is erased. Deleting a session does not remove them ([#676]) |
| Photo answers | Like typed answers, stored shrunk, outside the file allowance ([#677]) |
| Preferences | Stored only after the learner agrees, until removed or the account is erased ([#668], [#671]) |
| Sign-up ticks, with date and terms version | As long as the account exists ([#677]) |
| A published quote, once withdrawn | Where it was published and the remove-by date, until the owner marks it removed. Its words too, for at most 14 days if its account has gone. After an under-18 ending, only where it was published and the date ([#677], [#734], [#735]) |
| A decline's date and kind | As [`misuse.md`](misuse.md) sets out ([#733], [#719]) |
| A waiting erase card: the session's name, its mastered-topic count and the erase's date | Until Continue, or until the account or link is erased ([#777]) |
| A misuse warning, with its date | As long as the account exists ([#733], [#776]) |
| A copy asked for while closing, with any declined kinds in it | Until its 7-day link expires, or 30 days if its email can't be sent ([#733], [#735], [#772], [#776]) |
| A copy asked for by email, with any declined kinds in it | Until its 7-day link expires, or 30 days if its email can't be sent ([#735], [#719], [#772], [#776]) |
| A sealed session marked "Reported", with its account's email | Until the owner lifts or erases it, once the authorities answer. With the answer recorded, it goes with its account or link ([#743], [#719], [#777]) |
| A dead trial link's feedback answers and quote permissions, unless it died by a Yes or its holder erased it | 6 months after the trial ends, or 12 months after the link died, whichever comes first. Those of a published quote stay until the owner removes it ([#719]) |
| A dead trial link's stub: scrambled key and cookie IDs, state, reason | The trial's end, or 12 months after the link died, whichever comes first. A misuse reason's kinds go at its first showing, or 30 days after the owner's decision, whichever comes first (see [`misuse.md`](misuse.md)) ([#719], [#764], [#776]) |
| "Told Crux is full" email, scrambled | That day only ([#719]) |
| The learner's time zone | With the account or trial link ([#719]) |
| Per-account spend | Current day and week only. Older days only as totals with no account ([#677]) |
| "Email me if spots open" email | Until its one email is sent, or 3 months ([#677]) |
| "Email me when it's back" email | Until sent ([#677]) |
| Let-in list email | Up to 7 days, or until the owner removes it, and erased at sign-up ([#679]) |
| Code limits | Email addresses for a day, network addresses for an hour ([#674], [#717]) |
| Wrong-link counts | Network addresses for an hour ([#717]) |
| Copy page wrong-code counts | Network addresses for an hour ([#762], [#770]) |
| Hand blocks, in Cloudflare's settings | Network addresses for 12 to 36 hours, longer only while the daily job is down or a lift fails (see [`security.md`](security.md)) ([#770]) |
| A trial request's email | At most 30 days ([#717]) |
| Uptime endpoint and outage times, not personal | Overwritten; an outage until no open date needs it ([#772]) |
| Date moves, an inbox confirmation's code and mark | With the account, or as [`dates.md`](dates.md) says ([#772]) |
| Sent emails, at Resend | 30 days in its log, and up to 7 days after in its backups ([#717], [#762]) |
| Closed-for-misuse email, scrambled | 12 months ([#677]) |
| Backups | Deleted data may remain in a backup for up to 8 days. A restore re-applies every deletion and listed safety or privacy action made since its dump, from a log that keeps only IDs, times and actions for about 8 days (see [`backups-and-releases.md`](backups-and-releases.md)) ([#716], [#735]) |
| Google's copy | Only prompts its filters flag, up to 90 days, with no opt-out. Google staff may read flagged content, and it is never used for training. A short-term cache of at most 24 hours. Deleting in Crux cannot reach these ([#677], [#679], [#717]) |

## On screen

Layout is not decided (see the main file's Gaps). Close account with its dialog and "Send me a copy first", "Keep my account / Sign out", the terms-changed step and the share tick are in [`account-screens.md`](account-screens.md) ([#753]). The owner page's shared sessions, entered requests and breach form are in [`owner-screens.md`](owner-screens.md) ([#755]).

[#668]: https://github.com/calmxz/Crux/issues/668
[#671]: https://github.com/calmxz/Crux/issues/671
[#674]: https://github.com/calmxz/Crux/issues/674
[#675]: https://github.com/calmxz/Crux/issues/675
[#676]: https://github.com/calmxz/Crux/issues/676
[#677]: https://github.com/calmxz/Crux/issues/677
[#679]: https://github.com/calmxz/Crux/issues/679
[#681]: https://github.com/calmxz/Crux/issues/681
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#728]: https://github.com/calmxz/Crux/issues/728
[#732]: https://github.com/calmxz/Crux/issues/732
[#733]: https://github.com/calmxz/Crux/issues/733
[#735]: https://github.com/calmxz/Crux/issues/735
[#734]: https://github.com/calmxz/Crux/issues/734
[#743]: https://github.com/calmxz/Crux/issues/743
[#753]: https://github.com/calmxz/Crux/issues/753
[#762]: https://github.com/calmxz/Crux/issues/762
[#755]: https://github.com/calmxz/Crux/issues/755
[#764]: https://github.com/calmxz/Crux/issues/764
[#770]: https://github.com/calmxz/Crux/issues/770
[#772]: https://github.com/calmxz/Crux/issues/772
[#776]: https://github.com/calmxz/Crux/issues/776
[#777]: https://github.com/calmxz/Crux/issues/777
