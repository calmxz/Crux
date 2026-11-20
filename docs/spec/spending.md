# Spending limits

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what Crux counts, the tutoring limits, Google's caps, and what the owner page changes. What happens at a limit, and how started checks finish, are in [`at-a-limit.md`](at-a-limit.md). The amounts are in the main file's "Money". The learner cap's sign-up step and the let-in list are in [`accounts.md`](accounts.md). Guest mode's cap is in [`trial.md`](trial.md).

## What is counted

- Every limit counts money: what each tutor reply, file read, lookup and mastery-check call actually costs. A check's calls are writing a problem, checking its model answer, marking, re-marking and the walk-through ([#675]).
- Crux counts spend at list price from each reply's own token counts (input, cached, output, thinking), the moment the reply arrives, whether credits or the card pay ([#679]). A broken attempt counts the same way, from what Crux sent and received (see [`ai-layer.md`](ai-layer.md)) ([#771]).
- Crux's own count is what enforces the limits. Google's bill only checks it (see [Google's caps](#googles-caps)) ([#717]).
- A learner never sees money. Their tutoring limit is shown as a bar ([#675]).

When a learner sends a reply, a request or a file, Crux checks in this order: the month's budget, the daily ceiling, then the learner's own tutoring limit. If all have room, the tutor answers, and the cost is added to the month, today, and the learner's day and week ([#675]).

## The budget and the ceiling

- The month is a calendar month and resets on the 1st ([#675]).
- Money unspent on a quiet day stays in the month. It does not raise a later day's ceiling. The worst case is four ceiling days in a row, which empties the month ([#675]).
- The budget and the ceiling count guests and trial links. They do not count the owner's own use or re-marks (see the main file's "Money") ([#677], [#679], [#728] Answer 1).
- A re-run's bigger budget is in [`feedback.md`](feedback.md). During a re-run, the ceiling becomes a quarter of the bigger budget, even if the owner had set it by hand, and the owner can still change it. The tutoring limits do not change. The bigger budget and its ceiling start when the owner presses "Start the window" (see [`feedback.md`](feedback.md)), after raising Google's cap, and that press sends the "it's back" emails. They last to the end of the calendar month the re-run ends in. On the 1st, both return to what they were, and the owner lowers Google's cap ([#734]).

## Each learner's tutoring limit

- **2 sittings' worth a day and 4 a week,** whichever runs out first ([#675], [#679]).
- A sitting's worth is an amount of money: the cost of the cost research's typical sitting, about 15 learner replies, on the model that teaches. That is about USD 0.045 on 3.5 Flash-Lite (see [Gaps](#gaps)) ([#675], [#679]).
- A week runs Monday to Sunday ([#675]).
- A short sitting uses less than a sitting's worth, so a learner can come back several times a day ([#675]).
- A learner can use at most about 17 sittings' worth a month ([#675]).
- Reading a file counts like any reply. That is what caps how often a learner uploads ([#667], [#675]).
- The limit is per account, and one email is one account. A learner who makes extra accounts gets a limit per account. The ceiling and the month are the backstop ([#674], [#675]).
- A trial link has the same limit as an account, shared across its browsers ([#677]).

### Seeing the limit

- The bar is always visible on a settings page: "Today's tutoring: 70% used", with the week's total under it ([#675]).
- In the session, a pop-up appears once 75% of today's or the week's limit is used ([#675]). It shows once for the day and once for the week, and not inside a check ([#734]).

## The messages

| What ran out | What the learner sees |
|---|---|
| Their day | "You've used today's tutoring. Back tomorrow." |
| Their week | "You've used this week's tutoring. Back Monday." |
| The ceiling | "Crux is full for today. Back tomorrow." No email is offered. |
| The month, or Google's cap | "Crux has used this month's tutoring budget. Back on 1 Dec.", with a tick-box, "Email me when it's back" |

- Reset times are in the learner's own clock (see the main file's "Money") ([#675]).
- Each ticked learner gets one email when Crux reopens: on the 1st, when a re-run's bigger budget starts, or when an owner's raise reopens it ([#675], [#734]). Where these stand against the sender's limits is in [`email.md`](email.md) ([#735]).
- A trial link has no tick-box, since Crux keeps no email for it ([#722]).
- A guest sees the stop in [`trial.md`](trial.md) ([#734]).
- Anything that costs no AI keeps working: past sessions, "What you've mastered", files, settings and feedback ([#675]).

## The owner's share

- At the share, Crux stops only the owner's account, re-marks and the distress check. The owner sees "You've used your owner share this month" ([#679], [#734]).
- The owner raises it on the owner page, which asks them to raise Google's cap first and tick "I raised Google's cap" ([#679], [#755]).
- Re-marks and the distress check's pot spend from the share ([#728] Answer 1, [#734]). At the share, re-marks pause. They resume when the share refills on the 1st, or sooner if the owner raises it. A pass stands until it is re-marked. The owner's own check pauses as half-done at the share, and resumes the same way ([#734]).
- Google's cap covers the share too, so when it trips the owner is stopped as well ([#679]).

## Google's caps

- Agent Platform has no prepaid credit. Google's spend cap is the backstop, set a little above Crux's own stop so Crux stops first ([#675], [#679]).
- The Crux project's cap is about USD 11.50: the learners' USD 8, the owner's USD 3 and a margin of about USD 0.50 ([#679]).
- The cap is not instant, and an overage is billed to the card ([#679]).
- When Google refuses calls, learners see the month's message, and a check it stops is kept as half-done ([#675], [#679]).
- Before any raise in the money (the budget, a re-run's budget, the owner's share), the owner page names the cap to set, and the raise waits for the tick "I raised Google's cap" ([#679], [#755]).
- Once a day, Crux compares its own total with Google's billing report. A gap over 10% goes in the owner's daily email, with where it is ([#679], [#717]).
- Tests' cap is in the main file's "Money". The Cloud Run cap is in [`hosting.md`](hosting.md) ([#678], [#716]).

## The owner page

### What the owner can change

- At any time: the ceiling, the tutoring limits, the learner cap, the daily and monthly guest caps, the owner's share, the distress check's pot and the let-in list ([#675], [#679], [#734]).
- The budget changes only as the main file's "Money" says ([#675], [#679]).
- The switches for each part are in [`live-faults.md`](live-faults.md) ([#678]).

### What it shows

- The budget used and left, by Crux's own count ([#675]).
- Crux's count beside Google's billed figure, compared daily. The owner checks the credits left in Google Cloud, since Crux cannot read them ([#679]).
- While the cap is full: "Learner cap full (25 of 25). Raise it before you re-share." With let-in learners, "25 + N let in" ([#675], [#679]).
- Learners stopped by their own limit, each once per day ([#675], [#676]).
- Emails told "Crux is full for now", each once per day: "Told Crux is full: 30, 12 ticked email". A full cap with money left is a normal miss, so this does not count toward a budget-caused miss ([#675]).
- Days the ceiling, the month or Google's cap turned a learner away: see [`feedback.md`](feedback.md) ([#675], [#676], [#679]).
- The owner is never counted as turned away ([#675]).

### What the owner is told

How each message reaches the owner is in [`operations.md`](operations.md) ([#717]).

- **A push:** when the month's budget runs out; when the ceiling is hit, saying when, at most once a day; when Google's Gemini cap is reached, with Crux's count beside Google's cap; and when the owner's share reaches 100% ([#717], [#728] Answer 8).
- **The daily email:** the budget at 50% and 80%; the learner cap filled; the owner's share at 80%; a billing gap over 10%; and how many learners were turned away the day before ([#717], [#728] Answer 8).
- **During the trial,** that last line counts trial links, each once per day, and guests as a plain number of stops, tied to no browser ID: "3 trial links turned away. Guest mode stopped 5 times." Guest-cap stops are included ([#734]).

## Records

How long per-account spend and the "email me" addresses are kept is in [`privacy.md`](privacy.md) ([#677]).

## Gaps

- **What a sitting costs on Agent Platform:** its cache savings are unmeasured. Open on [#675]. With no cache hits, USD 8 gives about 133 sittings a month, not 176 ([#679]).
- **Measures that can change the limits:** a week of Crux's count against Google's bill, and sittings per mastery in the trial. See [`quality-bar.md`](quality-bar.md) ([#678]).

## On screen

The session screen is in [`learning-screen.md`](learning-screen.md): the near-limit pop-up as a pinned line, and the day, week, ceiling and month messages with their tick-box, the fixed lines after a filling reply and after a file, the waiting mark on a kept message, and the care and crisis lines in the thread ([#751]). The rest of the layout is not decided (see the main file's Gaps). The tutoring bar on the Settings page is in [`account-screens.md`](account-screens.md) ([#753]). The owner page's settings, cap line, counts, and share with its raise are in [`owner-screens.md`](owner-screens.md) ([#755]).

[#667]: https://github.com/calmxz/Crux/issues/667
[#674]: https://github.com/calmxz/Crux/issues/674
[#675]: https://github.com/calmxz/Crux/issues/675
[#676]: https://github.com/calmxz/Crux/issues/676
[#677]: https://github.com/calmxz/Crux/issues/677
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#722]: https://github.com/calmxz/Crux/issues/722
[#728]: https://github.com/calmxz/Crux/issues/728
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#751]: https://github.com/calmxz/Crux/issues/751
[#753]: https://github.com/calmxz/Crux/issues/753
[#755]: https://github.com/calmxz/Crux/issues/755
[#771]: https://github.com/calmxz/Crux/issues/771
