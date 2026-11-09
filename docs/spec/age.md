# The age rule

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what happens when someone says they are under 18. The rule that Crux is for adults only, and the tick at every way in, are in the main file's "Who Crux is for".

## Where the rule is said

- The landing page says Crux is for adults (18+) ([#681]).
- The Terms of Use state the age line (see [`privacy.md`](privacy.md)). The tick stays "I am 18 or over" ([#677]).
- Crux keeps no birth date or age ([#681]). What it keeps with the tick is in [`accounts.md`](accounts.md) ([#677]).
- Share posts on LinkedIn and Facebook carry no age wording ([#681]).
- The rule is about the learner, not the topic. An adult may learn a school-level topic ([#681]).

## What raises the question

- Only the learner's own messages to the tutor count, including one typed in the chat while a mastery check is open ([#681]).
- Text in a file, a mastery-check answer and feedback never raise it ([#681]).
- The tutor acts only on a clear statement about the learner's age now ("I'm only 15") ([#681]).
- A remark about the past ("I first saw this when I was 15") does not raise it. "Grade 10" alone is not enough ([#681]).
- The tutor spots the statement and calls Crux through a tool. It does not ask the question itself ([#679]).
- Noticing a statement is tested as an AI test, in [`ai-tests.md`](ai-tests.md). What the tap does is an ordinary test, in [`quality-bar.md`](quality-bar.md) ([#678], [#679]).

## The question

Crux shows its own fixed question, with Yes and No buttons: "Crux is for people 18 and over. Are you under 18?" ([#679])

- The tap decides. The model never ends anyone's access ([#679], [#728] Answer 2).
- While the question is open, a typed reply gets a short "please tap Yes or No" ([#679]). The distress check in [`spending.md`](spending.md) runs on it ([#734]).
- The question holds the whole account or trial link. It shows in every session and on every browser, and there is no tutoring anywhere until the tap ([#733]).
- It stays open if the session is deleted. Reading past sessions and "What you've mastered" still works ([#733]).
- For a guest, it lasts as long as the tab ([#733]).
- If it comes up during a mastery check, the check pauses as half-done (see [`mastery-check.md`](mastery-check.md)) ([#679]).
- It still works while a session is held for a harmful file (see [`files.md`](files.md)) ([#732]).

**On No:**

- Teaching carries on where it was. A paused check resumes with the open problem swapped, under the half-done rules ([#679]).
- Every new clear statement gets the question again, even after an earlier No. No one's access ends as under 18 without a Yes ([#681]).

## On Yes, for an account

In this order ([#677], [#681]):

1. The learner sees a short message.
2. The account's marks take 1 off each path and bar count that learner added, in the window each was counted in. A window already judged keeps its verdict. The budget counts are not changed (see [`feedback.md`](feedback.md)).
3. The owner page's dated under-18 count adds 1, with nothing about who the person was.
4. The account closes and its data is erased at once. The 7-day undo does not apply (see [`privacy.md`](privacy.md)). Only a published quote's note, with no words, stays until the owner removes it (see [`feedback.md`](feedback.md)) ([#734]). A sealed session marked "Reported" also stays, with the account's email, in the reported hold (see [`data-model.md`](data-model.md)). A copy not yet collected is erased with its link, and the account's feedback answers leave the tallies along with its counts ([#719]).

The learner may sign up again like anyone new, ticking the box again. Crux keeps nothing about them to block it ([#681]).

## On Yes, for a guest or a trial link

Guests and trial-link holders get the same question, buttons and rules above ([#728] Answer 2).

- **A guest:** the guest session ends, and the entry ticks clear on that browser, so they show again ([#677], [#728] Answer 2, [#733]).
- **A trial link:** the link is switched off, and its sessions, files, pages, photo answers and preferences are erased ([#717], [#722], [#728] Answer 2). Crux tells the person why their access ended and that their sessions are erased, just before or just after the erasure. A guest gets no such message ([#728] Answer 2).
- A trial link's ending also removes its feedback words and quote permissions, with the same exception for a published quote's note (see [`feedback.md`](feedback.md)) ([#734]).
- Each ending adds 1 to the owner page's dated under-18 count, as an account closed as under 18 does. The count keeps nothing about who the person was ([#728]).
- The trial counts toward no go-public count (see [`trial.md`](trial.md)) ([#677], [#728]).
- The Trial Privacy Notice says the dated count exists ([#728]).

## Through feedback

- Feedback that says "I'm 16" never raises the question ([#681]).
- If the sender ticked "You can email me about this", the owner may email to ask. A yes closes the account as an under-18 closure. Without the tick, the owner cannot act ([#677]).

## On screen

The age question is a card in the thread with Yes and No, and "please tap Yes or No" a line in the thread (see [`learning-screen.md`](learning-screen.md)) ([#751]). The rest of the layout is not decided (see the main file's Gaps). These rules need: the landing page's 18+ line, the closure message, the trial link's access-ended message, and the owner page's dated under-18 count ([#679], [#681], [#728]).

[#677]: https://github.com/calmxz/Crux/issues/677
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#681]: https://github.com/calmxz/Crux/issues/681
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#722]: https://github.com/calmxz/Crux/issues/722
[#728]: https://github.com/calmxz/Crux/issues/728
[#732]: https://github.com/calmxz/Crux/issues/732
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#751]: https://github.com/calmxz/Crux/issues/751
