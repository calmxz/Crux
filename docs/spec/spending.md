# Spending limits

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what Crux counts, the tutoring limits, what happens at a limit, Google's caps, and what the owner page changes. The amounts are in the main file's "Money". The learner cap's sign-up step and the let-in list are in [`accounts.md`](accounts.md). Guest mode's cap is in [`trial.md`](trial.md).

## What is counted

- Every limit counts money: what each tutor reply, file read, lookup and mastery-check call actually costs. A check's calls are writing a problem, checking its model answer, marking, re-marking and the walk-through ([#675]).
- Crux counts spend at list price from each reply's own token counts (input, cached, output, thinking), the moment the reply arrives, whether credits or the card pay ([#679]).
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

## At a limit

### The reply that fills the bar

- Teaching stops at the reply that fills the learner's bar. No reply is cut off, except one Google blocks (see [`ai-layer.md`](ai-layer.md)) ([#675], [#678], [#735]).
- Crux knows the cost only when the reply arrives, so it adds its own fixed line after that reply: "That's today's tutoring. Answer whenever you like, and the tutor will pick up here tomorrow." It names the reset that applies, such as "on Monday". This costs no AI ([#734]).
- When the ceiling or the month runs out between replies, the learner's next reply gets the "full" message ([#675]).

### What a stopped message keeps

- A learner is **turned away** when they send something and a limit stops Crux answering it ([#675]).
- A message stopped by any limit is kept. It stays in the conversation, marked as waiting. After the reset, opening the app answers every kept message and starts every kept file's read, oldest session first, several in one session together. The cost comes off the new limit ([#675], [#734]).
- If the limit fills while answering, the rest stay waiting. They also stay waiting on any visit when tutoring cannot run, such as a full limit, an open age question or a lock ([#734]).
- An owner's raise counts as a reset. If a block clears while the app is open, the answers run then, without reopening, and only once across browsers. Blocks are a tap on the age question, "Keep my account", agreeing to terms, removing a held file, lifting a seal or a lock, a raise, or midnight passing ([#734], [#736]). A message the whole-tutor switch stopped is answered as [`live-faults.md`](live-faults.md) says ([#736]).
- The session the learner is in goes first, so a new message there still starts within the main file's 5 seconds ([#734]).
- A background answer never opens a check problem. After reteaching in a half-done check, the next problem waits until the learner opens that session ([#734]).
- A background answer is not a sitting, and it does not restart the 7-day clock (see [`feedback.md`](feedback.md) and [`sessions.md`](sessions.md)) ([#734]).
- A session that needs a step from the learner first, such as the "continue" or "refresh first" offer, waits until they open it. The offer comes first, then the answer ([#734]).
- In a session held by a harmful file (see [`files.md`](files.md)), a kept message stays waiting until the file is gone. An age statement in it waits too ([#734]).
- Deleting a session erases its waiting messages ([#671], [#734]).

### Files at a limit

- A file sent before the limit is read in full ([#675]).
- When that read fills the limit, the read finishes and Crux shows a fixed line saying the file uploaded successfully, then the limit message. The tutor answers after the reset ([#734]).
- The fixed line shows only for a usable file. If the read finds a harmful file or fails, Crux shows that message at once, in place of the line (see [`files.md`](files.md)) ([#734]).
- A file sent when a limit is already full is stored, converted and split into pages at once, since that costs no AI. A file that fails shows the "Couldn't read this file" line then (see [`files.md`](files.md)) ([#734]).
- Only its AI read waits. Crux says so, naming the reset that applies: "Your file is saved. It'll be read when you're back tomorrow." After the reset, opening the app starts the read, and it comes off the new limit. The file counts toward the allowance while it waits, and the learner can remove it ([#734]).
- Once a read fills the limit, other kept files wait for the next reset. While the owner has files switched off, kept files' reads wait too ([#734]).
- A typed message sent with that file is answered after its read ([#734]).

### A learner in distress

A limit stops a message before the tutor reads it. So Crux sends only that message to the model and asks one yes-or-no question: is this person in distress? ([#734])

- **Yes:** Crux adds a care line and, on its own line, the crisis line the tutor points to (see [`misuse.md`](misuse.md)). Both are fixed text.
- **No:** the person sees only the limit message, or the switch's paused line. A check that fails or is blocked counts as no (see [`ai-layer.md`](ai-layer.md)) ([#735]).
- The limit message shows at once, and any care line follows it ([#735]).
- This applies to learners, trial links and guests. It also runs on a typed reply while an age question is open, since the tutor is not reading then (see [`age.md`](age.md)). It also runs on a message the whole-tutor or guest-mode switch stopped (see [`live-faults.md`](live-faults.md)) ([#736]).
- These checks have a pot of USD 0.05 a day, paid from the owner's share. It is outside the budget and the ceiling, and inside Google's cap as it stands. The owner can change the amount on the owner page ([#734]).
- When the pot runs out, the share runs out, or Google's cap stops Crux, no check runs ([#734]).
- The tutor still reads a kept message after the reset. A guest's message is never read later ([#734]).

## Started checks finish

- A mastery check that has started runs to the end, with its result and the after-mastery menu, past the learner's limit, the ceiling and the month ([#675]).
- This covers a half-done check resumed on a later day, its "refresh first" step, and disputes on it ([#675]).
- The offer has "Start the check" and "Not yet" buttons, and the "continue" or "refresh first" offer has buttons too. They need no AI to read (see [`mastery-check.md`](mastery-check.md)) ([#734]).
- A check starts when the learner accepts it with room left, by a tap or a typed reply the tutor reads. At 99% of the limit it starts, and runs past the limit ([#734]).
- A tap on "Start the check" when a limit is already full does not start it. The learner sees the limit message and "Your check is ready when you're back". No problem has been seen, and the objectives stay shown. The tutor offers the check again on return ([#734]).
- A typed "yes" at a full limit is kept like any message, since nothing reads it, and the tutor offers the check again ([#734]).
- **Reteaching stops at the limits.** After a real miss in the refresh, the objective is taught as usual (see [`mastery-check.md`](mastery-check.md)). A limit stops that teaching like any teaching, and the check stays half-done. Earlier answers still count. The problems that follow run past the limits ([#731], [#734]).
- A check does not finish when the owner switches checks off for a fault, or when Google refuses calls. It pauses as half-done (see [`mastery-check.md`](mastery-check.md)) ([#675], [#678]).
- A guest's mini check stops at the guest caps, the ceiling and the month like any guest reply, since a guest can resend an older saved state (see [`data-model.md`](data-model.md)) ([#719]). A started check on a trial link or an account finishes past them ([#733], [#734]).

## The messages

| What ran out | What the learner sees |
|---|---|
| Their day | "You've used today's tutoring. Back tomorrow." |
| Their week | "You've used this week's tutoring. Back Monday." |
| The ceiling | "Crux is full for today. Back tomorrow." No email is offered. |
| The month, or Google's cap | "Crux has used this month's tutoring budget. Back on 1 Dec.", with a tick-box, "Email me when it's back" |

- Reset times are in the learner's own clock (see the main file's "Money") ([#675]).
- Each ticked learner gets one email when Crux reopens: on the 1st, when a re-run's bigger budget starts, or when an owner's raise reopens it ([#675], [#734]). Where these stand against the sender's limits is in [`operations.md`](operations.md) ([#735]).
- A trial link has no tick-box, since Crux keeps no email for it ([#722]).
- A guest sees the stop in [`trial.md`](trial.md) ([#734]).
- Anything that costs no AI keeps working: past sessions, "What you've mastered", files, settings and feedback ([#675]).

## The owner's share

- At the share, Crux stops only the owner's account, re-marks and the distress check. The owner sees "You've used your owner share this month" ([#679], [#734]).
- The owner raises it on the owner page, which reminds them to raise Google's cap first ([#679]).
- Re-marks and the distress check's pot spend from the share ([#728] Answer 1, [#734]). At the share, re-marks pause. They resume when the share refills on the 1st, or sooner if the owner raises it. A pass stands until it is re-marked. The owner's own check pauses as half-done at the share, and resumes the same way ([#734]).
- Google's cap covers the share too, so when it trips the owner is stopped as well ([#679]).

## Google's caps

- Agent Platform has no prepaid credit. Google's spend cap is the backstop, set a little above Crux's own stop so Crux stops first ([#675], [#679]).
- The Crux project's cap is about USD 11.50: the learners' USD 8, the owner's USD 3 and a margin of about USD 0.50 ([#679]).
- The cap is not instant, and an overage is billed to the card ([#679]).
- When Google refuses calls, learners see the month's message, and a check it stops is kept as half-done ([#675], [#679]).
- Before any raise in the money (the budget, a re-run's budget, the owner's share), the owner page reminds the owner to raise Google's cap first ([#679]).
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

Layout is not decided (see the main file's Gaps). These rules need: the tutoring bar on the settings page, the near-limit pop-up, the day, week, ceiling and month messages with their tick-box, the fixed lines after a filling reply and after a file, the waiting mark on a kept message, the care and crisis lines, and the owner page's settings, cap line, counts, and share with its raise ([#675], [#679], [#734]).

[#667]: https://github.com/calmxz/Crux/issues/667
[#671]: https://github.com/calmxz/Crux/issues/671
[#674]: https://github.com/calmxz/Crux/issues/674
[#675]: https://github.com/calmxz/Crux/issues/675
[#676]: https://github.com/calmxz/Crux/issues/676
[#677]: https://github.com/calmxz/Crux/issues/677
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#722]: https://github.com/calmxz/Crux/issues/722
[#728]: https://github.com/calmxz/Crux/issues/728
[#731]: https://github.com/calmxz/Crux/issues/731
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#736]: https://github.com/calmxz/Crux/issues/736
