# Feedback and the go-public bar

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers the feedback page, what the owner counts, who sees the owner page, the go-public bar, and a miss caused by the budget. What the owner may read in a session is in [`privacy.md`](privacy.md).

## The feedback page

- Feedback lives on one page, apart from the conversation with the tutor, for signed-in learners and trial-link holders. Guests have no feedback page ([#676], [#677]).
- A "Feedback" link outside the chat opens it at any time, except while the learner is inside a mastery check. A half-done check elsewhere does not hide it ([#676], [#734]).
- After a learner's first mastery, a small notice outside the conversation links to the page: "Tell us what you think, 1 minute". It shows once, never while the learner is inside a check, does not interrupt teaching or the after-mastery menu, and can be dismissed. Once shown, it never returns ([#676]).
- It costs no AI, so it works past every spending limit ([#675]).

### What it asks

1. "Did Crux help you understand your topic?" (yes / somewhat / no), required.
2. "Would you pay for Crux?" (yes / maybe / no), required.
3. "What would make Crux better for you?" (optional, free text).
4. "Anything else?" (optional, free text).

Three optional ticks follow ([#676], [#677], [#733]):

- "Crux may quote this, without my name".
- "You can email me about this". A trial link does not have this tick, since Crux keeps no email for it ([#722]).
- The share tick (below).

There is no question about price. Pricing belongs to the paid-launch effort ([#676]).

### How often

- A learner may send feedback more than once, and each is kept. For the pay count, the latest answer is used ([#676]).
- Each text box holds up to 2,000 characters ([#734]).
- An account or a trial link can send 5 a day, in the owner's time zone. Past that: "You've sent a lot of feedback today. Please try again tomorrow." ([#734])
- A locked account or one in its 7-day closing can untick a quote or a share, but cannot send feedback ([#734]).

### Sharing a session

- The share tick has two choices, a named session or "all my sessions". The page names the session ("Share: Personal essay") with a list to change it, starting on the session the learner came from, or else the one they opened last. With no sessions, there is no share choice ([#733], [#734]).
- It warns: "This shares everything you wrote, including anything personal" ([#677], [#733]).
- What the owner can then read is in [`privacy.md`](privacy.md). The owner reads up to the tick, and later messages and later sessions stay closed ([#733]).
- Unticking in Settings, under "Your feedback", ends the owner's access ([#733]).
- A share from a trial link ends when the link dies ([#733]).

A trial link keeps "Your feedback" and the once-only notice while it is alive, as an account does ([#734]).

### Who sent it, and quoting

- Feedback is anonymous to the owner, unless the learner ticks "You can email me about this". The owner then sees their email with that answer ([#677]).
- The latest pay answer is still kept as a mark on the account. The owner never sees whose it is ([#677]).
- What the owner may do about feedback that says "I'm 16" is in [`age.md`](age.md) ([#677]).
- Feedback may be quoted publicly only with its quote tick, and never with the learner's name ([#676]).
- A learner withdraws a quote by unticking it in Settings, under "Your feedback", which lists their answers with their ticks. Withdrawing is by Settings only ([#677], [#733]).
- When the owner publishes a quote, they mark that answer as published on the owner page and note where ([#677], [#734]).
- When a published quote is withdrawn, the owner removes it within 14 days. Until the owner marks that done, the page shows its words, where it was published, and the date to remove it by. If its account has gone, the words stay for those 14 days at most, and the rest until marked. An under-18 ending is below ([#677], [#734], [#735]).
- An answer never marked as published is erased as usual ([#734]).

### When an account closes or a link dies

- **An account closes:** after the 7-day undo, the feedback words leave the owner page, apart from a published quote still to be removed. Anonymous counts and yes/no answers stay as tallies, so a verdict does not change because someone left. Its quotes are withdrawn ([#677]).
- **An under-18 closure** first takes its counts off (see [Taking counts back](#taking-counts-back)) ([#681]). Its words go at once. As for a link, only a published quote's note and remove-by date stay ([#734]).
- **A trial link dies after a tap on Yes to the age question:** the link's feedback words and quote permissions are removed at once. For a published quote, only the note of where it was published and the remove-by date stay, until the owner marks it done ([#734]).
- **A trial link dies in any other way:** its anonymous feedback answers and quote permissions stay. The holder can untick until the link dies, and the trial's end notice reminds them. The Trial Terms say a tick can't be undone once the link has ended ([#677], [#734]).

## What the owner counts

### The path

Counts of learners, each with a date ([#676]):

- **Signed up:** an account is made, at Start on the new-learner step ([#674]).
- **Started a topic:** the learner says "go" after the objectives, and teaching begins ([#734]).
- **Reached a mastery check:** the tutor offers the check, whether or not the learner accepts ([#734]).
- **Mastered a topic:** any way a topic becomes mastered counts, including a dispute won after the result and a prerequisite topic ([#676]).
- **Came back:** had a sitting on a later day than their first ([#676]).
- **Came back after mastering:** had a sitting on a later day after their first mastery ([#676]).
- **Mastered a second topic:** a different topic. The same topic mastered again in another session does not count ([#676]).

"A later day" is a later calendar day in the learner's own time zone: mastered at 23:50, back at 00:10, counts. Sending feedback is not a sitting ([#676]). A sitting needs something the learner sends to the tutor. Opening the app, reading, or a background answer is not one ([#734]).

### How counting works

- Each count adds 1, with the date, the first time a learner reaches that step in a window. Marks are kept per window ([#676], [#734]).
- To know who has been counted, the account keeps a few marks: the date of each step first reached, the latest pay answer, and that the first-mastery notice was shown. The counts hold no name or content ([#676]).
- Deleting a session removes neither the counts nor the marks. The marks go when the account closes ([#676]).
- Learners let in past a full cap count like any learner ([#679]).
- The owner's own account and any test accounts are left out of every count. A test account is an address on the owner's own email list (see [`accounts.md`](accounts.md)). It behaves as the owner's account for limits and counts, so limits are tested on staging ([#676], [#734]).
- Nothing in the trial counts (see [`trial.md`](trial.md)) ([#677]).
- There are no cookies for counting, and no click or time-on-screen analytics. The sign-in cookie is never used for counting ([#674], [#676]).

### Taking counts back

- **An under-18 closure:** before the account and its marks go, Crux takes 1 off each path and bar count that learner added, in the window each was counted in ([#681]).
- **A pass removed by a re-mark:** it drops from the counts in the window it was counted in ([#678]). A learner stays counted as mastered only if another topic was mastered inside the same window ([#734]).
- **A pass a re-mark adds:** it counts like a dispute won ([#736]).
- A window already judged keeps its verdict ([#678], [#681]).
- The budget counts are not changed ([#681]).

### Other counts

- **Visits:** see [Visits](#visits) ([#717]).
- **Turned away:** learners stopped by their own limit, and emails told "Crux is full for now", are in [`spending.md`](spending.md) ([#675]).
- **Refused sign-in codes:** in [`accounts.md`](accounts.md) ([#674], [#728] Answer 6).
- **Under-18 endings:** in [`age.md`](age.md) ([#681], [#728]).

### Visits

- Crux counts visits itself. The app's first call carries the source: the `?src=` tag on the shared link, otherwise the site the visitor came from, otherwise "direct" ([#717]).
- Sources map to a fixed list: linkedin, facebook, other sites, direct ([#717]).
- The backend adds 1 to today's count for that source, once per browser tab. Nothing per person is kept, and the owner's own visits are left out ([#717]).
- The owner page shows visits by source for today, the last 7 days, and since the first post ([#717]).

## The go-public bar

### The window

- The bar is fixed before sharing ([#676]).
- The window starts on the day of the first public post ([#676], [#677]). The owner starts it with a "Start the window" button on the owner page, pressed on the day of the post. A re-share or a re-run starts the same way ([#734]).
- The button works only once sign-up is open and while no window is running, so it is greyed out during the trial ([#734]).
- The press can be undone the same day. That day's counts and marks are removed, and a re-run's budget and ceiling go back. Emails already sent can't be recalled ([#734]).
- No past date can be entered, and the start cannot be changed later. A late press loses the days before it ([#734]).
- The window runs 56 days, the last day included ([#676]).
- The bar is judged once, at the end of the last day ([#676]).

### Every window

Anything that happens inside a window counts, by any learner, including accounts made before it. A "yes" counts if that learner masters a topic inside the window, using their latest answer, even one given before it. A return sitting inside the window counts as "came back after mastering", even when the mastery came earlier ([#676], [#734]).

### What it needs

**Go** needs all three inside the window ([#676]):

- 20 learners mastered a topic.
- 8 learners came back after mastering.
- 8 learners who have mastered a topic gave "yes" as their latest pay answer. "Maybe" does not count. A "yes" from a learner who has not mastered a topic does not count.

Go starts the paid-launch effort, which is separate from this spec ([#676]).

### A miss

- The owner fixes the weakest step that the path and the feedback point to, re-shares, and runs one more 8-week window with the same bar, counted from zero ([#676]).
- Nothing between the end of the first window and the re-share counts toward either. The fix has no time limit ([#676]).
- **In the re-share window,** the rule in [Every window](#every-window) covers learners from the first window too ([#676]).
- A second miss means stop. There is no paid launch, and Crux stays deployed as a portfolio project, under these same rules ([#676], [#677]).

### A miss caused by the budget

- A miss is **caused by the budget** when the ceiling, the month's budget or Google's cap turned a learner away on at least 7 of the window's 56 days ([#675], [#676], [#679]).
- A day counts only when one of those turned a learner away. A learner stopped by their own limit does not count, however often. Nor does a full learner cap ([#675], [#676]).
- A budget-caused miss does not use up the one retry. The window is re-run: the same bar, counted from zero, for 8 weeks, on a bigger budget the owner fixes before it starts. Only the budget changes, and other fixes wait for the normal retry ([#676]).
- What a re-run does to the ceiling, and how long its budget lasts, is in [`spending.md`](spending.md) ([#734]).
- There is at most one budget re-run in the whole effort, in either window. A second budget-caused miss counts as a normal miss ([#676]).
- Before a re-run, the owner raises the budget and Google's cap ([#675], [#679]).
- On the current budget, Flash-Lite gives about 176 sittings a month, or about 133 with no cache hits, against the bar's 40 to 60 over the window. The owner raises the learner cap during a window when it fills and people are waiting ([#679]).

## The owner page

- Only the owner's main address can open it. Every other account, test addresses included, and anyone signed out, is turned away, including at its direct address ([#676], [#678], [#734]).
- Feedback text shows there as plain text ([#678]).
- It shows the path, the bar's progress ("14 / 20 mastered"), the feedback answers with unread ones marked, which answers may be quoted, and visits by source ([#676], [#677], [#717]).
- It shows the days the budget turned a learner away ("Limit hit on 9 of 56 days"), apart from learners stopped by their own limit ([#676]).
- Its other parts are in the area file that owns each one: [`spending.md`](spending.md), [`accounts.md`](accounts.md), [`trial.md`](trial.md), [`misuse.md`](misuse.md), and [`live-faults.md`](live-faults.md).
- **The daily email** gives new feedback as a count only, never the words or the sender ("2 new feedback answers"), and any "1 quote permission withdrawn" ([#677], [#717]).

## Gaps

- **Whether the bar is reachable on real costs:** what a sitting costs on Agent Platform, and sittings per mastery, are not measured. See [`spending.md`](spending.md) and [`quality-bar.md`](quality-bar.md) ([#678], [#679]).

## On screen

Layout is not decided (see the main file's Gaps). These rules need: the feedback page and its link, its ticks and the share choices and warning, the after-first-mastery notice, "Your feedback" in Settings, the too-many-sends message, and the owner page's path, bar progress, feedback list with unread marks, limit-hit line and visits by source ([#676], [#677], [#717], [#733], [#734]).

[#674]: https://github.com/calmxz/Crux/issues/674
[#675]: https://github.com/calmxz/Crux/issues/675
[#676]: https://github.com/calmxz/Crux/issues/676
[#677]: https://github.com/calmxz/Crux/issues/677
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#681]: https://github.com/calmxz/Crux/issues/681
[#717]: https://github.com/calmxz/Crux/issues/717
[#722]: https://github.com/calmxz/Crux/issues/722
[#728]: https://github.com/calmxz/Crux/issues/728
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#736]: https://github.com/calmxz/Crux/issues/736
