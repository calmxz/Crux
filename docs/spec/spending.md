# Spending limits

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what Crux counts, the limits, the workspaces and the credit, and what the owner page changes. What happens at a limit, and how started checks finish, are in [`at-a-limit.md`](at-a-limit.md). The amounts are in the main file's "Money". The learner cap's sign-up step and the let-in list are in [`accounts.md`](accounts.md). Guest mode's cap is in [`trial.md`](trial.md).

## What is counted

- Every limit counts money, except the check limit, which counts checks started, and the reading limit, which counts pages read ([#675], [#802]). The money is what each tutor reply, file read, lookup and mastery-check call actually costs. A check's calls are writing a problem, checking its model answer, marking, re-marking and the walk-through ([#675]).
- Crux counts spend at list price from each reply's own token counts (input, cache writes and reads, output, thinking), the moment the reply arrives ([#679], [#802]). A broken attempt counts the same way, from what Crux sent and received (see [`ai-layer.md`](ai-layer.md)) ([#771]).
- Crux's own count is what enforces the limits. The Console's Usage page only checks it, by hand (see [Workspaces and the credit](#workspaces-and-the-credit)) ([#717], [#802]).
- A learner never sees money. Their tutoring limit is shown as a bar ([#675]).

When a learner sends a reply, a request or a file, Crux checks in this order: the month's budget, the daily ceiling, then the learner's own limit for that kind of call (the tutoring limit, the check limit for starting a check, or the reading limit for a file's read). If all have room, the call runs, and the cost is added to the month, today, and the learner's day and week ([#675], [#802]). A message accepted before the learner's bar filled is answered past it, as [`at-a-limit.md`](at-a-limit.md) says ([#802]).

## The budget and the ceiling

- The month is a calendar month and resets on the 1st ([#675]).
- Money unspent on a quiet day stays in the month. It does not raise a later day's ceiling. The worst case is four ceiling days in a row, which empties the month ([#675]).
- The budget and the ceiling count guests and trial links. They do not count the owner's own use or re-marks (see the main file's "Money") ([#677], [#679], [#728] Answer 1).
- At every limit for a 31-day month, one learner spends about USD 0.80 with 6-problem worded checks and USD 1.11 with 10-problem ones, every read overrunning. 25 learners plus the guests' USD 2 spend USD 21.88 and USD 29.85. In the second case the month's budget runs out about day 26 ([#726]).
- A re-run's bigger budget is in [`feedback.md`](feedback.md). During a re-run, the ceiling becomes a quarter of the bigger budget, even if the owner had set it by hand, and the owner can still change it. The limits do not change. The bigger budget and its ceiling start when the owner presses "Start the window" (see [`feedback.md`](feedback.md)), after raising Crux's workspace limit, and that press sends the "it's back" emails. They last to the end of the calendar month the re-run ends in. On the 1st, both return to what they were, and the owner lowers the workspace limit and live's Cloud Run cap ([#726], [#734], [#802]).

## Each learner's tutoring limit

- **2 sittings' worth a day and 4 a week,** whichever runs out first ([#675], [#679]).
- A sitting's worth is an amount of money: the cost of a typical sitting, about 15 learner replies, on the model that teaches. That is about USD 0.0093 on Haiku 5.5 at `medium` with the 1-hour cache, teaching only, measured as the mean of 3 sittings with nothing cached, since a learner's sittings are usually more than an hour apart ([#675], [#726], [#802]).
- Teaching from a file costs more per reply, since the topic's pages go with every turn: about USD 0.0007 a page per sitting (measured on a 20-page slice: 2.5 sittings' worth with nothing cached, 1.74 within the hour). A cold sitting on a topic of more than about 13 pages fills a day by itself ([#726]).
- A week runs Monday to Sunday ([#675]).
- A short sitting uses less than a sitting's worth, so a learner can come back several times a day ([#675]).
- A learner can use at most about 17 sittings' worth a month ([#675]).
- Mastery checks and a file's read into its outline don't use the tutoring limit. Teaching from a file does ([#802]).
- The limit is per account, and one email is one account. A learner who makes extra accounts gets a limit per account. The ceiling and the month are the backstop ([#674], [#675]).
- A trial link has the same limits as an account, shared across its browsers: the tutoring limit, 2 checks and 100 pages a week ([#677], [#802]). Guests type only, and their 2-problem mini check runs under the guest caps, so neither the check limit nor the reading limit reaches them ([#802]).

### Seeing the limit

- The bar is always visible on a settings page: "Today's tutoring: 70% used", with the week's total under it ([#675]).
- In the session, a pop-up appears once 75% of today's or the week's limit is used ([#675]). It shows once for the day and once for the week, and not inside a check ([#734]).

## The check limit

- Each learner can start 2 mastery checks a week, Monday to Sunday. The learner sees "2 checks this week", then "Your next check is ready on Monday" ([#802]).
- Only the check limit, the ceiling and the month can stop a check starting. A full tutoring limit doesn't ([#802]).
- A started check runs past every limit, as [`at-a-limit.md`](at-a-limit.md) says. A resumed half-done check, its refresh and disputes are part of the same check ([#802]).
- The whole check counts in the budget and the ceiling ([#802]).

## The reading limit

- Crux reads up to 100 pages a week of each learner's files into outlines, outside the tutoring limit. The learner sees "Files: 60 of 100 pages read this week" ([#802]).
- Storing, converting and splitting a file count nothing except the 200 MB allowance (see [`files.md`](files.md)) ([#802]).
- Another file counts its own pages. The read's cost still counts in the budget and the ceiling ([#802]).
- A retried read counts once. A read that ends in "Couldn't read this file" gives its pages back. A re-upload after a successful read counts again ([#802]).
- A file whose read starts within the week's 100 pages is read in full, even past 100, and the next file waits ([#802]).
- Past the limit, the counter shows "Files: this week's reading is used. Back on Monday." in place of the numbers. A waiting read shows "Your file is saved. It'll be read when you're back on Monday.", and starts when the learner next opens Crux after the reset ([#802]).

## The messages

| What ran out | What the learner sees |
|---|---|
| Their day | "You've used today's tutoring. Back tomorrow." |
| Their week | "You've used this week's tutoring. Back Monday." |
| Their checks for the week | "Your next check is ready on Monday" |
| Their reading for the week | "Files: this week's reading is used. Back on Monday." |
| The ceiling | "Crux is full for today. Back tomorrow." No email is offered. |
| The month, or a workspace limit | "Crux has used this month's tutoring budget. Back on 1 Dec.", with a tick-box, "Email me when it's back" |
| The credit | The month's message, with the credit's renewal date: "Back on 11 Dec." |
| The Max plan's last credit, with no decision | "Crux is paused for now.", with the "Email me when it's back" tick-box |

- Reset times are in the learner's own clock (see the main file's "Money") ([#675]).
- Each ticked learner gets one email when Crux reopens: on the 1st, when a re-run's bigger budget starts, when an owner's raise reopens it, or when calls come back after a credit stop ([#675], [#734], [#802]). Where these stand against the sender's limits is in [`email.md`](email.md) ([#735]).
- A trial link has no tick-box, since Crux keeps no email for it ([#722]).
- A guest sees the stop in [`trial.md`](trial.md) ([#734]).
- Anything that costs no AI keeps working: past sessions, "What you've mastered", files, settings and feedback ([#675]).

## The owner's share

- At the share, Crux stops only the owner's account, re-marks and the distress checks. The owner sees "You've used your owner share this month", where the chat box was (see [`at-a-limit.md`](at-a-limit.md)) ([#679], [#734], [#802]).
- The owner raises it on the owner page, which asks them to raise Crux's workspace limit in the Console and live's Cloud Run cap first, and tick "I raised the limits" ([#679], [#726], [#755], [#802]).
- Re-marks and the distress pots spend from the share ([#728] Answer 1, [#734], [#802]). If every pot is used up each day, the pots take USD 0.12 a day (0.05 + 0.05 + 0.02), about USD 3.72 of the 8 in a 31-day month, which leaves about USD 4.28 for re-marks and the owner's own use ([#802]).
- At the share, re-marks pause. They resume when the share refills on the 1st, or sooner if the owner raises it. A pass stands until it is re-marked. The owner's own check pauses as half-done at the share, and resumes the same way ([#734]).
- Crux's workspace limit covers the share too, so when it trips the owner is stopped as well ([#679], [#802]).

## Workspaces and the credit

- The AI spend comes from the owner's Max plan API credit, USD 100 a month, arriving about the 11th and expiring at the end of its cycle. Prepaid credit with auto-reload off and no bought credit is the hard stop: requests stop at zero, and no card is charged ([#802]).
- Anthropic workspaces set the hard monthly limits. Crux's workspace has a monthly spend limit of about USD 34: the learners' 25, the owner's share of 8, and a margin of about 1. Crux tests' workspace has USD 20. "Crux research", for research runs and the owner's computer, has a monthly limit the owner sets, about USD 10. Nothing runs in the Default Workspace ([#802]).
- That commits about 64 of the 100 a month. One credit cycle can see two months' limits, since the credit renews about the 11th and the limits reset on the 1st: at worst 2 x 64 = 128 against the 100. Then the credit-stop rules below apply ([#802]).
- The owner sets each limit by hand in the Console. Before any raise in the money (the budget, a re-run's budget, the owner's share), the owner page names the limit to set and live's Cloud Run cap, which moves at about USD 0.31 for each AI dollar (see [`hosting.md`](hosting.md)), and the raise waits for the tick "I raised the limits" ([#679], [#726], [#755], [#802]).
- Crux's month stays on the 1st. The owner enters the credit's renewal day once on the owner page, and updates it if the billing day changes ([#802]).
- **When a workspace limit or the credit stops Crux,** learners see the month's message, with the renewal date when the credit ran out. A started check pauses as half-done, and the owner gets the urgent push ([#675], [#802]).
- After a credit stop, the small call testing whether Anthropic accepts calls again runs hourly from the stop until calls succeed, since a refused call isn't billed. A workspace-limit stop reopens on the 1st or at the owner's raise ([#802]).
- **If the Max plan ends,** the owner decides then, as a recorded change: buy credit, lower the budgets, or let Crux pause. If the last credit is spent with no decision, Crux pauses: "Crux is paused for now.", with the "Email me when it's back" tick-box, and the owner gets the urgent push ([#802]).
- There is no daily bill comparison, since an individual account has no Admin API. The owner compares Crux's count with the Console's Usage page by hand at each monthly test round ([#802]).
- Tests' limit is in the main file's "Money". The Cloud Run cap is in [`hosting.md`](hosting.md) ([#678], [#716]).

## The owner page

### What the owner can change

- At any time: the ceiling, the tutoring limits, the check limit, the reading limit, the learner cap, the daily and monthly guest caps, the owner's share, the three distress pot amounts, the credit's renewal day and the let-in list ([#675], [#679], [#734], [#802]).
- The budget changes only as the main file's "Money" says ([#675], [#679]).
- The switches for each part are in [`live-faults.md`](live-faults.md) ([#678]).

### What it shows

- The budget used and left, by Crux's own count ([#675]).
- While the cap is full: "Learner cap full (25 of 25). Raise it before you re-share." With let-in learners, "25 + N let in" ([#675], [#679]).
- **Turned away:** an account or trial link counts once a day when it opens Crux or switches to a session at a limit and finds the limit message where the box was. Reaching a limit alone, or switching back to the tab, doesn't count ([#675], [#676], [#802]).
- Emails told "Crux is full for now", each once per day: "Told Crux is full: 30, 12 ticked email". A full cap with money left is a normal miss, so this does not count toward a budget-caused miss ([#675]).
- Days the ceiling, the month, or a workspace or credit stop turned a learner away, counted the same way: see [`feedback.md`](feedback.md) ([#675], [#676], [#802]).
- The owner is never counted as turned away ([#675]).

### What the owner is told

How each message reaches the owner is in [`operations.md`](operations.md) ([#717]).

- **A push:** when the month's budget runs out; when the ceiling is hit, saying when, at most once a day; when a workspace limit or the credit stops Crux; when the owner's share reaches 100%; and when the accounts' or the guests' distress pot runs out, at most once a day each ([#717], [#728] Answer 8, [#802]).
- **The daily email:** the budget at 50% and 80%; the learner cap filled; the owner's share at 80%; and how many learners were turned away the day before ([#717], [#728] Answer 8, [#802]).
- **During the trial,** that last line counts trial links, each once per day, and guests as a plain number of stops, tied to no browser ID: "3 trial links turned away. Guest mode stopped 5 times." Guest-cap stops are included, one per stop line ([#734], [#802]).

## Records

How long per-account spend, the check and reading counts, and the "email me" addresses are kept is in [`privacy.md`](privacy.md) ([#677], [#802]).

## Gaps

- **A sitting's worth on page-heavy topics:** the 1-hour cache's cost is measured, and so is a sitting's worth on a 20-page slice. The cost per page is a straight-line guess from it ([#726], [#802]).
- **Workspace spend limits on an individual account,** to confirm in the smoke test. If they aren't available, that's a recorded change then ([#802]).
- **Telling a credit stop from a workspace-limit stop** by Anthropic's error, a build check. If Crux can't tell them apart, the build opens a spec change and does not guess ([#802]).
- **Measures that can change the limits:** Crux's count against the Console's Usage page, and sittings per mastery in the trial. See [`quality-bar.md`](quality-bar.md) ([#678], [#802]).

## On screen

The session screen is in [`learning-screen.md`](learning-screen.md): the near-limit pop-up as a pinned line, the check and reading counters, and the day, week, ceiling and month messages with their tick-box in the chat box's place ([#751], [#802]). The rest of the layout is not decided (see the main file's Gaps). The tutoring bar on the Settings page is in [`account-screens.md`](account-screens.md) ([#753]). The owner page's settings, cap line, counts, renewal day, and share with its raise are in [`owner-screens.md`](owner-screens.md) ([#755], [#802]).

[#674]: https://github.com/calmxz/Crux/issues/674
[#675]: https://github.com/calmxz/Crux/issues/675
[#676]: https://github.com/calmxz/Crux/issues/676
[#677]: https://github.com/calmxz/Crux/issues/677
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#722]: https://github.com/calmxz/Crux/issues/722
[#726]: https://github.com/calmxz/Crux/issues/726
[#728]: https://github.com/calmxz/Crux/issues/728
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#751]: https://github.com/calmxz/Crux/issues/751
[#753]: https://github.com/calmxz/Crux/issues/753
[#755]: https://github.com/calmxz/Crux/issues/755
[#771]: https://github.com/calmxz/Crux/issues/771
[#802]: https://github.com/calmxz/Crux/issues/802
