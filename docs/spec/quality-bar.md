# The quality bar

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what "solid" means, the ordinary tests, the real-phone tests, what is measured before it counts, the repo, and what each stage needs before it starts. AI tests are in [`ai-tests.md`](ai-tests.md). How a stage's list is ticked is in [`spec-process.md`](spec-process.md).

## Who "solid" is for

Two bars, both met before sharing: the app (what learners, and recruiters trying it, experience) and the repo (what technical interviewers read). When time runs short, the app comes first ([#678]).

## The first click

The rule is in the main file's "Speed". It is checked by hand on the owner's phone, after an hour with no use, on 3 different days ([#678]). What Crux tries if it fails is in [`hosting.md`](hosting.md) ([#716]).

## Ordinary tests

An ordinary test needs no AI judgement. Ordinary tests run on every push, in CI on a throwaway database, and a change merges only when they pass. There is no coverage target ([#678], [#716]). The rule report in [`spec-process.md`](spec-process.md) asks for a proof of each rule a build ticket names ([#680]).

These are the tests the closed tickets sent here, by area.

**Isolation and the owner page** ([#676], [#678], [#734])

- On every page and request, another learner's, guest's or trial link's session, file or Record gives "not found".
- The owner page turns away every other account, test addresses included, and anyone signed out, including at its direct address, with "Page not found" ([#755]).
- Feedback text shows there as plain text.

**Sign-up and sign-in** ([#674], [#678], [#717], [#733])

- Start stays off until both ticks. No account exists before Start. The same email by Google and by code opens one account. A returning learner never sees the step.
- A session ends after 30 days without a visit.
- Codes stop at 5 tries, 10 minutes, 3 an hour and 10 a day. Code requests from one network stop at 20 an hour.
- The sender-out message, and its owner-page count, each address once per day.
- Google returns only the email, and nothing else is stored.
- The region message comes before any code. The let-in list beats the misuse block.
- The landing page's 18+, and an unticked box refused.

**Age** ([#679], [#681], [#728], [#733], [#734])

- A tap on Yes closes the account, erases its data, takes its steps off the counts in the window each was counted in, and adds 1 to the dated count. A judged window keeps its verdict, and the budget counts do not change.
- A tap on No resumes teaching where it was.
- An open question holds every session and browser. A tap on Yes clears the entry ticks on that browser.
- A guest's Yes and a trial link's Yes do what [`age.md`](age.md) says, including a trial link's feedback words and quote permissions removed.

**Sessions and the lookup** ([#671], [#678], [#732], [#735])

- The refresh offer comes at 7 days.
- No lookup runs while a check problem is open, and none of a session's teaching is reachable then. The lookup runs during reteaching after a refresh miss, even with checks switched off, and is off during the refresh, the end step and any paused check.
- Deleting a session removes its entries from "What you've mastered".
- A sealed session is unreachable by lookup, share, background answer or re-mark.

**Files** ([#670], [#677], [#716], [#722], [#732])

- Text in a file cannot reorder the menu.
- A removed file and a deleted session are gone at once.
- The harmful-file hold. A failed file erased. A removed whole-request file.
- Uploads stop at the 20 GB store total.
- A guest's upload attempt shows the trial-link line and stores nothing.

**The mastery check** ([#678], [#679], [#735])

- The menu order, and the maths library's checks.
- A blocked mark swaps the problem, and the check pauses after 2 swaps.

**Spending** ([#675], [#679], [#717], [#728], [#734])

- The daily ceiling stops replies and restarts at midnight.
- A check started at 90% of a learner's limit runs to the end, and so does a half-done one resumed on a ceiling day.
- A tap on "Start the check" at a full limit. A typed "yes" at a full limit is kept. Reteaching stopped at a limit.
- The pop-up at 75%, once each for the day and the week, never inside a check. The cap's "full" message.
- A provider refusal shows the month's message, and keeps a check half-done.
- A kept message is answered on opening, oldest first, with the open session ahead.
- A background answer is not a sitting, opens no check problem, and does not restart the 7 days.
- A filling read's fixed line shows only for a usable file.
- A guest's mini check stops at the guest caps, the ceiling and the month, even when an older saved state is resent ([#719]).
- Re-marks pause at the owner's share. A re-run's ceiling is a quarter of its budget.
- The owner's pushes and daily email: the ceiling's push at most once a day; the Gemini-cap push with Crux's count beside Google's cap; the other pushes in [`operations.md`](operations.md); and the day's turned-away count in the next morning's email.

**Counts and feedback** ([#676], [#678], [#734])

- The counts match worked scenarios: several masteries counted once, a deleted session, the owner's account left out, the re-share window, and a sitting needing something sent.
- A test account behaves as the owner's for limits and counts.
- The first-mastery notice shows once, never during a check. The Feedback link is hidden during a check.
- A "yes" from a learner with no mastery does not count.
- The budget-caused miss: 7 days is budget-caused, and 6 a normal miss. One learner at their own cap on 7 days is not budget-caused. One re-run in the effort.
- After a re-mark, a learner stays counted as mastered only if another topic was mastered inside the same window.
- The window button's guards, and its same-day undo. Feedback limits. A locked or closing account can untick but not send. A published quote after an under-18 ending.

**Closing and retention** ([#677], [#733], [#735])

- A closing waits 7 days, is cancelled by "Keep my account", and erases on day 8. A day-8 copy through the copy page: each opening gets a link that works its full 15 minutes and opens nothing outside the copies bucket, and the page refuses the code after 7 days plus any days down ([#762]).
- The idle warnings.
- The terms and "Keep my account" steps on a live sign-in.
- A notice clock starts at Resend's acceptance. Dates gain the days lost in a pause.
- Spend lines past the week are reduced to nameless totals. "Email me" lists are erased.
- The copy's zip, with a declined file packed unread. A quote untick reaches the daily email.
- The share tick's two choices, and its untick.

**Misuse** ([#677], [#733], [#735], [#743])

- 3 declines in 7 days flag a session. A threat against a real person flags at once, with a push.
- A decline saves its date, kind and place, and no words.
- The flag table: warn, dismiss and close, by whether a warning is on record. The count resets. One open flag.
- A flag opens only sessions with a decline. No file shows on any flag. A flag dies with its account. A trial link's flag has no warning.
- A sealed flag locks at once, and the owner sees only the date and the kind.
- A lock is read-only. A contest holds the erasure. A misuse closure erases on day 8, and blocks the email for 12 months.
- A blocked reply counts as a decline, tested with a made-up block result. A second prohibited-content block locks the account.
- A sealed session marked "Reported" stays past its account's erasure, and an unmarked one goes. The erasure tests in [`data-model.md`](data-model.md) pass ([#719]).

**The trial** ([#677], [#717], [#722], [#733])

- The entry ticks, once per browser. The region message on the public link.
- The guest 10-reply limit and its message. The guest cap switching to the video.
- The key leaves the address bar. A switched-off link fails, and its files, pages and photo answers are gone at once. A network is refused after 10 wrong links. A link on a fourth browser is flagged.
- A request is declined at 30 days and at trial end, with the email.
- Arrivals count once per tab and by tag.
- The trial's end button and its notice. Ending the trial erases every link's sessions and files.

**Switches and re-marks** ([#678], [#736])

- Each switch does what [`live-faults.md`](live-faults.md) says, and is undone by switching back on.
- A message sent while the whole tutor is off is kept, gets the distress check, and is answered on a refresh, a tap, another send or the next opening.
- A read under way when files go off is dropped, with no try used and no charge.
- A re-mark covers every mark from the faulty period, in both directions, and gives what a correct marker would have given then. A wrong or unsure result undoes a pass, and the objective stays shown. Several checks on one objective: any right one passes it. Checks stay off until the re-marks finish.
- An answer sent to an open check problem while the whole tutor is off is not kept, and the problem is swapped.

**Hosting and operations** ([#716], [#717], [#735], [#750])

- Crux's own logs never write a network address or a request header. Logged paths are route patterns, with a trial key never logged.
- The tasks service refuses calls from the internet.
- An error carrying learner text is reported without it.
- The restore log, one test per listed action. Sender shares. The 26-hour uptime check.
- Push protection, Betterleaks and osv-scanner each fail on a planted case.
- Before the trial, hadolint, the image scan and CodeQL each fail on a planted case: a Dockerfile running as root, an image with a known-vulnerable package, and a query built from strings.

## Real-phone tests

These run on the owner's Android phone ([#678]). iPhone is untested: a known gap from the trial on, since link holders and Request access reach Crux from phone apps. A failed request can be tried again in the phone's browser, and the invite link works again from the email ([#678], [#717], [#736]).

- **Before the trial:** Turnstile passes inside LinkedIn's and Facebook's apps on the Request access form. A trial link opened from the Gmail and Outlook apps lands signed in and stays so ([#717]).
- **Before opening, and whenever sign-in changes:** the Google button inside those two apps jumps to the phone's browser or shows Crux's note, never Google's error page. The code works inside them, including switching to the mail app and back ([#674], [#678]). This also settles whether LinkedIn's jump works on Android ([#678]).

## Security

- GitHub push protection refuses known key formats at GitHub. Betterleaks stops a secret at commit on the owner's computer, and fails in CI ([#717]).
- osv-scanner fails on any known hole in the libraries Crux uses, unless a written exception gives a reason and an expiry date. Dependabot opens fix pull requests ([#717]).
- osv-scanner also scans the built backend image, under the same rule. hadolint checks the backend Dockerfile ([#750]).
- CodeQL on the backend blocks a merge on a finding of high or above, until it is fixed or dismissed with GitHub's reason. Medium and low findings show and do not block. CodeQL also runs weekly; a finding there on unchanged code is an alert, fixed by its own pull request ([#750]).
- Before opening, the owner works through the OWASP Top 10 ([#678]).

## Knowing when something is wrong

The tools are in [`operations.md`](operations.md) ([#717]).

- Phone notifications come within minutes: errors from Crux, and the outside check ([#678], [#717]). Error Reporting goes quiet for 6 hours after 20 notifications in an hour, and the uptime check is separate ([#717]).
- The services' security emails go straight to the owner's own email ([#717]).
- A one-page breach plan is written before the trial. It has the National Privacy Commission notice and the learner email already drafted, so the 72 hours from knowing are spent filling in and sending ([#678]). For link holders, it drafts the on-screen notice in [`trial.md`](trial.md) ([#733]).

## Measured before it counts

**Before the trial, on the owner's own sittings** ([#678]):

- A week of Crux's spend count against Google's bill. More than 10% apart tightens the limits by the gap.
- The cost per reply of the note at 40 mastered topics, and the cost of a lookup reply. If either is too costly, the owner decides then, as a recorded change ([#732]).

**During the trial, from trial-link users** ([#678], [#679], [#717]):

- Sittings per mastery. More than 3 means the tutoring limits and the learner cap are revisited before opening.

The age question's reliability on the chosen model is what the high-risk age tests measure ([#678]).

## Build checks

These settle how Google's services behave, while that part is built:

- that `OFF` holds on Agent Platform for the pinned models; how a block arrives mid-stream; whether a blocked attempt is charged ([#735]);
- whether Gemini reads each listed image format ([#732]);
- whether Gemini can read a topic's pages straight from the bucket on the global address ([#716]);
- the smoke test: the model-call-only role is enough for the service accounts, after which the Express API keys are deleted ([#716]).

## The repo

- **The README:** what Crux is, the live link, how to run it locally, an architecture section with a diagram, the key decisions with their reasons, and how Crux tests its AI: the tiers, the grader, and what blocks a release ([#678]). The decisions link the closed tickets and `spec-change` issues ([#680]).
- **CI:** tests, style checks and type checks ([#678]).

## What each stage needs

- A test runs before the first stage where someone other than the owner can reach its feature. A feature only accounts have is tested before opening ([#678], [#736]).
- Each item says who ticks it: **check** (an agent, with proof) or **owner** ([#680]).
- Items done by hand on live, such as the phone tests and the alerts, are done before the stage starts, and read no learner's data ([#736]).

### Before the trial

| Item | Who |
|---|---|
| Every AI test passes, including those on files and photo answers ([#678], [#722]) | check |
| The tutor's instructions frozen, and the test cap raised first if the deep round will not fit ([#736]) | owner |
| A deep round, on the version that starts the trial ([#678]) | check |
| The grader judges its example list correctly ([#678]) | check |
| Every ordinary test for what guests and trial links can reach passes, including the isolation test ([#678], [#736]) | check |
| The first-click speed, on 3 days ([#678]) | owner |
| The real-phone tests for the trial ([#717]) | owner |
| The spend, note and lookup measures ([#678]) | owner |
| The fidelity test on real decks: Word equations, SmartArt, speaker notes ([#716], [#722]) | check |
| The build checks, and the smoke test with the Express keys deleted ([#716], [#732], [#735]) | check |
| A deliberate error reaches the owner's phone within minutes, which also proves the request-log filter keeps Crux's own logs ([#717]) | owner |
| An uptime alert and a new-request push reach the phone, and so do two requests 2 minutes apart. The Google Cloud app receives a push ([#717], [#735], [#762]) | owner |
| The breach plan, with how the NPC takes breach notices confirmed ([#678], [#762]) | owner |
| A test restore of a dump that replays the log ([#716], [#735]) | check |
| The Trial Terms and Trial Privacy Notice published ([#677], [#717]) | owner |
| The spend caps set: the Crux and Crux tests projects, and Cloud Run on live and staging ([#679], [#716]) | owner |
| The domain bought and verified with Resend, and Email Routing to the Crux Gmail ([#717]) | owner |
| The billing export on, before the first Gemini call in the Crux project ([#717]) | owner |
| Essential Contacts set ([#717]) | owner |
| Push protection on ([#717]) | check |
| The processor terms of Google Cloud, Cloudflare, Supabase and Resend accepted ([#717]) | owner |
| Two-step sign-in on the Resend account ([#717]) | owner |
| The crisis line's number and link verified, and the directory's terms read ([#735]) | owner |

### Before opening

Done before anyone but the owner signs up, even privately to one friend ([#677]).

| Item | Who |
|---|---|
| Every ordinary test for what only accounts reach passes: sign-up and sign-in, the code limits, account closing and the idle warnings, the age tick-box, and the rest ([#678], [#717], [#736]) | check |
| The real-phone tests for opening ([#678]) | owner |
| The tutor's instructions frozen, and the test cap raised first if the deep round will not fit ([#736]) | owner |
| A deep round, on the version that opens ([#678]) | check |
| The OWASP self-review ([#678]) | owner |
| The README ([#678]) | check |
| Sittings per mastery reviewed ([#678]) | owner |
| The advisory letter sent, at least a month before opening ([#677]) | owner |
| The Terms and Privacy Policy published, with the officer's contact ([#677]) | owner |
| The reworded consent tick and the EU/UK check in sign-up ([#677]) | check |
| The Crux email's switch: Zoho if its agreement covers the free plan, otherwise Workspace, with trial mail moved or deleted ([#717]) | owner |
| The Sentry judgement, with its address settings if added ([#717]) | owner |
| Google's sign-in screen moved to production, with the Privacy Policy on the domain ([#717]) | owner |
| The crisis line's number and link verified again, and the directory's terms read ([#735]) | owner |

## Gaps

- **Whether warm-on-open meets the 5 seconds off-peak.** Example: Ana sends her first message 3 seconds after opening at 6 am, before the backend is up ([#716]).
- **How the owner meets the 72-hour rule when nobody is watching.** The breach plan covers the writing. Example: the host emails on a Friday night that its database was exposed ([#677]).

[#670]: https://github.com/calmxz/Crux/issues/670
[#671]: https://github.com/calmxz/Crux/issues/671
[#674]: https://github.com/calmxz/Crux/issues/674
[#675]: https://github.com/calmxz/Crux/issues/675
[#676]: https://github.com/calmxz/Crux/issues/676
[#677]: https://github.com/calmxz/Crux/issues/677
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#680]: https://github.com/calmxz/Crux/issues/680
[#681]: https://github.com/calmxz/Crux/issues/681
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#722]: https://github.com/calmxz/Crux/issues/722
[#728]: https://github.com/calmxz/Crux/issues/728
[#732]: https://github.com/calmxz/Crux/issues/732
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#736]: https://github.com/calmxz/Crux/issues/736
[#743]: https://github.com/calmxz/Crux/issues/743
[#750]: https://github.com/calmxz/Crux/issues/750
[#762]: https://github.com/calmxz/Crux/issues/762
[#755]: https://github.com/calmxz/Crux/issues/755
