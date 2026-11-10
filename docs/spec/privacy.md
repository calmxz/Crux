# Privacy, terms and deleting

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what Crux promises, what the owner may read, and how long data stays. Harm and misuse are in [`misuse.md`](misuse.md). The trial's own notices are in [`trial.md`](trial.md). Where data lives and what is logged are in the main file's "Where data lives".

## The Terms of Use

The terms use plain words throughout, and state the cost and the law from the main file's "Who Crux is for" ([#677]).

- **Age:** "You must be 18 or over, and old enough to agree to these terms where you live." (see [`age.md`](age.md)) ([#677]).
- **Graded work:** "Crux teaches; it won't do your work for you. Don't use it where your course or exam forbids outside help." The tutor's teaching is unchanged (see [`teaching.md`](teaching.md)) ([#677]).
- **Standard lines** ([#677]):
  - "Crux is an AI tutor and can make mistakes. Check anything important against your course material."
  - "Crux is provided as is, without guarantees it will be available or error-free."
  - "As far as the law allows, [owner] isn't liable for losses from using Crux."
  - "Crux may change, and may close with notice (see the Privacy Policy)."
  - "You keep ownership of what you upload. You let Crux use it only to tutor you. Only upload what you have the right to use."

### Harm and misuse

The Terms state the harm line and what misuse leads to. Both are in [`misuse.md`](misuse.md) ([#677]).

### Changes to the terms

- Changes that matter are emailed 14 days ahead. These are changes to what is stored, who sees or processes it, new uses of data, and new rules on what learners may do ([#677]).
- The learner then agrees with a tick: "Crux's terms changed: [what changed]. [Agree] [Close my account]". It shows the next time they open Crux, on any browser, before any tutoring ([#677], [#733]).
- A learner who never comes back sees nothing. The account waits, and the idle rule below applies ([#733]).
- Other changes, such as a typo or a clearer sentence, are dated in a "What changed" list ([#677]).

## When the owner reads a session

The owner reads a conversation only in two cases ([#677]):

- **Shared:** on the feedback page, the learner ticks to share, and picks a named session or "all my sessions". The tick warns: "This shares everything you wrote, including anything personal". The owner reads each one from its start up to the tick. Later messages and later sessions stay closed. Unticking in Settings ends the owner's access (see [`feedback.md`](feedback.md)) ([#677], [#733]).
- **Flagged:** a flag opens only the sessions where the tutor declined something, chat text only. The owner reads each one from its start up to the flag, plus any new declines while the flag waits. Access ends when the owner acts on the flag or, after a closure, when the lock ends ([#677], [#733]).

No flag shows the owner a file or a photo, and a sealed flag shows no session at all (see [`misuse.md`](misuse.md)). The owner page never opens a declined file, even on a share. A copy includes it, packed unread by a script, unless it is sealed ([#733]). Other sessions stay closed. Deleting a session erases it at once, including from the owner's view ([#733]).

Repairs from a backup are done by script, and the owner sees counts, not content ([#716]). The owner page's feedback rules, including who sent an answer, are in [`feedback.md`](feedback.md) ([#677]).

## Deleting and closing

### What erases at once

- Removing a file, or deleting a session, erases it at once ([#677]). A removed file's earlier replies stay in the conversation until the session is deleted (see [`files.md`](files.md)) ([#732]).

### Closing an account

- Closing starts in Settings, in a confirm dialog where the learner types "delete" before Close account works ([#753]). The dialog names what is erased ("your 4 sessions, your files, and your record of 3 mastered topics") and the date the 7 days end, with a "Send me a copy first" button ([#677], [#733]).
- An email follows: "Your Crux account closes on 3 Nov. Sign in to keep it." ([#677])
- During the 7 days, the next time they open Crux, on any browser, they see "Keep my account / Sign out", with the same button. There is no tutoring until they pick. A habitual visit does not cancel by accident ([#677], [#733]).
- Keeping leaves the account as it was. Sign out lets the closing go on ([#677]).
- Otherwise the account and its data are erased on day 8, in the daily housekeeping job ([#677], [#728] Answer 7).
- **If they asked for a copy:** on day 8, Crux makes the copy itself, erases the account and everything else, and emails a private link that works for 7 days from when it is sent (see [`operations.md`](operations.md)). It keeps only the copy and the address until the link expires, and a missed link cannot be made again. Keeping the account cancels the copy ([#733], [#735]).
- A request that arrives by email during a closing, including a misuse closure, is entered on the owner page, or Crux cannot know about it ([#733]).
- On day 8, the feedback words leave the owner page. Anonymous counts and yes/no answers stay as tallies. The account's quote permissions are withdrawn too (see [`feedback.md`](feedback.md)) ([#677]).
- The owner chose the undo for the meantime. Erasing at once is the fallback if the undo causes problems ([#677]).
- An under-18 closure skips the undo, and takes its counts off first (see [`age.md`](age.md)) ([#677], [#681]). A published quote's note stays until the owner removes it (see the table below) ([#734]). A misuse closure has its own 7 days (see [`misuse.md`](misuse.md)) ([#733]).
- A closed account's spot under the cap stays used (see [`accounts.md`](accounts.md)) ([#675], [#677]).

### Idle accounts

An account with no visit for 12 months is closed and erased, after emails 30 days and 7 days before. One visit keeps it: any signed-in request, opening the app included ([#719]). A learner who has lost the inbox cannot act on the emails, and the data goes at the deadline ([#677]). If a warning goes out late, the deadline moves, so the full notice is given (see [`operations.md`](operations.md)). The Privacy Policy says so ([#735]).

### If Crux closes, or goes paid

- **If Crux closes:** every learner is emailed at least 30 days ahead where possible: "Crux closes on 15 Feb. Want a copy of your data? Email us." Learning continues normally until then. Every account and its data is then erased, and the anonymous tallies stay ([#677]).
- The closing email goes on a day with few sign-ups, so it fits the sender's daily limit ([#677], [#728]).
- **If the go-public bar is not met:** Crux is not shut down. It stays deployed as a portfolio project, under these same rules ([#676], [#677]).
- **If a paid launch follows:** a v1 account moves only if the learner agrees to the new terms when they next open Crux. Anyone who does not answer is treated as a closing, with the 30 days' notice ([#677]).

## How long things stay

| Data | How long |
|---|---|
| Conversations, files, check answers and their marks | Until the session is deleted or the account is erased ([#671], [#677]) |
| Account marks (dates of steps first reached, latest pay answer) | Until the account is erased. Deleting a session does not remove them ([#676]) |
| Photo answers | Like typed answers, stored shrunk, outside the file allowance ([#677]) |
| Preferences | Stored only after the learner agrees, until removed or the account is erased ([#668], [#671]) |
| Sign-up ticks, with date and terms version | As long as the account exists ([#677]) |
| A published quote, once withdrawn | Where it was published and the remove-by date, until the owner marks it removed. Its words too, for at most 14 days if its account has gone. After an under-18 ending, only where it was published and the date ([#677], [#734], [#735]) |
| A decline's date and kind | As [`misuse.md`](misuse.md) sets out ([#733], [#719]) |
| A misuse warning | As long as the account exists ([#733]) |
| A copy asked for while closing | Until its 7-day link expires ([#733], [#735]) |
| A copy asked for by email | Until its 7-day link expires, 7 days after sending ([#735], [#719]) |
| A sealed session marked "Reported", with its account's email | Until the owner erases it, once the authorities say what to do ([#743], [#719]) |
| A dead trial link's feedback answers and quote permissions | 6 months after the trial ends, or 12 months after the link died, whichever comes first. Those of a published quote stay until the owner removes it ([#719]) |
| A dead trial link's stub: scrambled key and cookie IDs, state, reason | The trial's end, or 12 months after the link died, whichever comes first ([#719]) |
| "Told Crux is full" email, scrambled | That day only ([#719]) |
| The learner's time zone | With the account or trial link ([#719]) |
| Per-account spend | Current day and week only. Older days only as totals with no account ([#677]) |
| "Email me if spots open" email | Until its one email is sent, or 3 months ([#677]) |
| "Email me when it's back" email | Until sent ([#677]) |
| Let-in list email | Up to 7 days, or until the owner removes it, and erased at sign-up ([#679]) |
| Code limits | Email addresses for a day, network addresses for an hour ([#674], [#717]) |
| Wrong-link counts | Network addresses for an hour ([#717]) |
| A trial request's email | At most 30 days ([#717]) |
| Sent emails, in Resend's log | Up to 30 days ([#717]) |
| Closed-for-misuse email, scrambled | 12 months ([#677]) |
| Backups | Deleted data may remain in a backup for up to 8 days. A restore re-applies every deletion and listed safety or privacy action made since its dump, from a log that keeps only IDs, times and actions for about 8 days (see [`hosting.md`](hosting.md)) ([#716], [#735]) |
| Google's copy | Only prompts its filters flag, up to 90 days, with no opt-out. Google staff may read flagged content, and it is never used for training. A short-term cache of at most 24 hours. Deleting in Crux cannot reach these ([#677], [#679], [#717]) |

## The Privacy Policy

### Who runs Crux

- Crux is run by the owner, named, in the Philippines ([#677]).
- Until the Commission says otherwise, Crux handles learning progress as possibly sensitive information about education, and the 18+ tick as information about age. Learning progress means objectives shown and passed, mastered topics, check answers and photos, and preferences. This is why sign-up asks for specific consent ([#677]).
- Crux follows the same standards wherever its learners are ([#677]).

### Contacts

- The owner is the data protection officer. The site and the Privacy Policy publish "Data Protection Officer, Crux", the owner's home postal address, a dedicated phone number (a prepaid SIM used only for Crux), and the role email ([#677]).
- The owner's actual name and details are filled in when the policy is written ([#677]).
- Data requests (a copy, deletion) go to the Crux email, privacy@ the domain ([#677], [#717]). The owner's LinkedIn or other profiles are a general contact ([#677]).
- Where that inbox sits, in the trial and from opening, is in [`operations.md`](operations.md) ([#717]).

### Copies and requests

- A copy of a learner's data is sent on request to the Crux email, within a month, as for every data request. It holds conversations, record, preferences, check answers and photos (data files plus readable text) and uploaded files, as a zip. A script the owner runs makes it, without the owner reading through it ([#677]). It reaches the learner as a private 7-day link (see [`operations.md`](operations.md)) ([#735]).

### Breaches

If sensitive or sign-in data reaches the wrong hands with a real risk of serious harm, the owner tells the National Privacy Commission and the affected learners within 72 hours. The owner sends the Commission a yearly summary of incidents ([#677]).

### What it covers

The Privacy Policy says ([#677], [#679], [#681], [#716], [#717], [#732], [#733]):

- what is stored and for how long (see above);
- "Deleting a session erases it. Another session may still mention something from it, until you delete that one too.";
- a removed file's earlier replies stay in the conversation until the session is deleted;
- "If you ask for a copy while closing, we keep it until its link expires, 7 days after it's sent, and no longer.";
- a date for erasing data moves if a notice goes out late, or if Crux is down, so nobody loses their chance to act ([#735]);
- the processors below, and where they process data;
- the dated anonymous counts, including the under-18 count, and the cookieless arrivals count;
- the sign-in cookie;
- the human check, the email sender, the code limits and the region check;
- the misuse flag, sealed sessions, and the email of their account, being kept longer only if reported to the authorities, what is saved with each decline, what a flag or a share lets the owner read, and the blocked-email list;
- the guest and trial rules;
- error reports with no learner text;
- the learner's rights: a copy, correction, deletion, withdrawing consent, and complaining to the National Privacy Commission;
- the 72-hour breach rule;
- "If Crux becomes a paid service, nothing moves without your agreement."

### Processors

| Processor | Used for | Agreement and place |
|---|---|---|
| Google Cloud | Cloud Run, Cloud Storage, Agent Platform, Error Reporting, Monitoring, BigQuery | Google Cloud's data processing addendum. Data "may be processed in any country", and Crux's data is stored in Singapore ([#679], [#717]) |
| Cloudflare | Static files, the Worker, DNS, the registrar, Email Routing, Turnstile | Its self-serve agreement. It sees network addresses at its edge. Turnstile reads the network address, browser details and connection fingerprint, and Cloudflare uses those signals partly for its own purposes, outside the agreement ([#716], [#717]) |
| Supabase | The database | Part of its Terms on every plan, with Supabase Pte. Ltd (Singapore). Data stored in Singapore ([#717]) |
| Resend | Crux's email | Covers all plans. Processing mainly in the US, with sent emails in its log up to 30 days ([#717]) |
| The Crux Gmail, in the trial | The Crux email | No agreement, an exception the owner accepted. Zoho or Workspace from opening ([#717]) |

## On screen

Layout is not decided (see the main file's Gaps). Close account with its dialog and "Send me a copy first", "Keep my account / Sign out", the terms-changed step and the share tick are in [`account-screens.md`](account-screens.md) ([#753]). These rules need: "Who runs Crux" with the officer's contact, and the owner page's shared sessions and copy requests ([#677], [#733]).


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
