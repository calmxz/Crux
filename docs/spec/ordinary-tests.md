# Ordinary tests

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers the tests that need no AI judgement: the ordinary tests by area, the component tests and the browser paths. AI tests are in [`ai-tests.md`](ai-tests.md). What each stage needs, and the repo's security checks, are in [`quality-bar.md`](quality-bar.md).

## Terms

This is a test term, so it stays out of the glossary.

- **Browser path:** a Playwright test that drives the app in a real browser, through the Worker, against the local stack with the backend's stub model ([#769]).

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

**Sessions, the lookup and the session search** ([#671], [#678], [#732], [#735], [#780])

- The refresh offer comes at 7 days.
- No lookup runs while a check problem is open, and none of a session's teaching is reachable then. The lookup runs during reteaching after a refresh miss, even with checks switched off, and is off during the refresh, the end step and any paused check.
- Deleting a session removes its entries from "What you've mastered".
- A sealed session is unreachable by lookup, share, background answer or re-mark.
- The session search finds only the learner's own sessions; finds a sealed session by its name only; skips a check's hidden teaching and files, finds them during reteaching, and skips them again before the next problem; skips messages Google blocked and Crux's own lines; and loses a deleted session at once.

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

- A closing waits 7 days, is cancelled by "Keep my account", and erases on day 9. A day-9 copy through the copy page: each opening gets a link that works its full 15 minutes and opens nothing outside the copies bucket, and the page refuses the code after 11:59 pm on its last day plus any outage days ([#762], [#772]).
- The idle warnings.
- The terms and "Keep my account" steps on a live sign-in.
- A notice clock starts at Resend's acceptance, and a shown date only moves later. An emailed request waits for its email, or for the owner's confirmation with the right code; a reply with no code, a wrong one or a refusal confirms nothing, and a confirmation survives a restore ([#772]).
- At 12:00 am after a last day, Keep, a trial link and a copy page stop, and the card past the last day shows. An outage of 15 minutes or more moves an open date by its total, before any run or refusal acts, and a restore keeps the move ([#772]).
- Spend lines past the week are reduced to nameless totals. "Email me" lists are erased.
- The copy's zip, with a declined file packed unread. A quote untick reaches the daily email.
- The share tick's two choices, and its untick.

**Misuse** ([#677], [#733], [#735], [#743])

- 3 declines in 7 days flag a session. A threat against a real person flags at once, with a push.
- A decline saves its date, kind and place, and no words.
- The flag table: warn, dismiss and close, by whether a warning is on record. The count resets. One open flag.
- A flag opens only sessions with a decline. No file shows on any flag. A flag dies with its account. A trial link's flag has no warning.
- A sealed flag locks at once, and the owner sees only the date and the kind.
- A lock is read-only. A contest holds the erasure. A misuse closure erases on day 10, one run after the owner's reminder, and blocks the email for 12 months ([#772]).
- A blocked reply counts as a decline, tested with a made-up block result. A second prohibited-content block locks the account.
- A sealed session marked "Reported" with no answer recorded stays past its account's erasure, and an unmarked or answered one goes ([#777]). The erasure tests in [`data-model.md`](data-model.md) pass ([#719]).

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
- The copy page refuses a network after 10 wrong codes in an hour. A trial link's key and the copy page's code are read from after the `#` and sent in a request body ([#770]).
- A Cloudflare refusal is retried once after 10 seconds, then shows "Crux can't be reached right now. Try again later." with the typed message kept. Crux's own errors are not retried. The Worker turns a Cloud Run answer not in Crux's error shape into its "can't be reached" code ([#770]).
- A missing or lapsed sign-in cookie shows the signed-out view, and a blocked network the unreachable line; neither shows the other. Warm-on-open greys the landing page only after its second refused try, and the greying clears when a try succeeds ([#770]).
- Before the trial, hadolint, the image scan and CodeQL each fail on a planted case: a Dockerfile running as root, an image with a known-vulnerable package, and a query built from strings. CodeQL also fails on a planted case on the frontend: a page that writes text from its address into the page as HTML ([#769]).

## Component tests and browser paths

- Component tests run in Vitest, with no coverage target ([#769]).
- Component tests cover a reply arriving with its maths held back until complete, both kinds of broken reply, a guest's broken reply, and a wide equation breaking or scrolling ([#771]).
- About five browser paths, in Chromium, block a merge: a guest's first reply, a trial link landing signed in, sign-in by code, a mastery check through to its Result, and the owner page turning another account away. The build ticket picks the exact paths ([#769]).
- A sixth opens every route once, and each kind of opening and ended page once, and runs axe on each, leaving out Turnstile's own frame. It runs in both themes, the guest Settings page included, and its stub reply holds one diagram of each of the three Mermaid types, a graph, maths, an equation too wide to fit and maths KaTeX cannot draw. It blocks a merge, like the five ([#769], [#779]).
- The contrast test runs inside the sixth path, in both themes, bringing up every state its parts show in. It blocks a merge too (see [`themes.md`](themes.md)) ([#779]).
- One browser path renders a reply with maths, a diagram and a graph under the real content security policy, with no policy errors. No browser path turns the policy off (see [`security.md`](security.md)) ([#769]).
- The headers' browser path is in [`security.md`](security.md) ([#769]).

### How they run

- The browser paths run the real Worker locally, in wrangler's local runtime, between the browser and the local backend ([#769]).
- They send no real email and pass no real Turnstile challenge. A code-keeping stub sender replaces email in dev, CI and staging. Its codes are read from the stub sender's store, never through an API route ([#769]).
- Turnstile's test keys are used in dev and CI. Live refuses to start with either the stub sender or the test keys ([#769]).
- A test's country comes from the local runtime's own settings, which the deployed Worker does not have, so the region message can be tested ([#769]).
- A browser path checks that a browser-sent country or address, in Cloudflare's header names or Crux's own, is ignored (see [`security.md`](security.md)) ([#769]).

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
[#755]: https://github.com/calmxz/Crux/issues/755
[#762]: https://github.com/calmxz/Crux/issues/762
[#769]: https://github.com/calmxz/Crux/issues/769
[#770]: https://github.com/calmxz/Crux/issues/770
[#771]: https://github.com/calmxz/Crux/issues/771
[#772]: https://github.com/calmxz/Crux/issues/772
[#777]: https://github.com/calmxz/Crux/issues/777
[#780]: https://github.com/calmxz/Crux/issues/780
[#779]: https://github.com/calmxz/Crux/issues/779
