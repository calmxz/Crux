# The mastery check

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them. Where this file names an area file not yet written, use that file's source tickets in the main file's index.

This file covers the mastery check, from the offer to the result and what follows a fail. When a topic is mastered is in the main file's "What Crux is". Readiness is in [`teaching.md`](teaching.md). The menu after mastery is in [`learning-loop.md`](learning-loop.md).

## The offer

- When the learner is ready (see [`teaching.md`](teaching.md)), the tutor offers the check ([#668]).
- The offer states the length and the split: "6 problems, 2 each on objectives 2 and 3. Ready?" The learner can say "not yet" and keep learning. The tutor offers again later ([#664], [#669]).
- The offer states the honour rule: closed book, so no notes, no searching and no other AI. Nothing is enforced ([#669]).
- There is no early check. A learner who asks before every objective is shown is pointed to the quick route ("I know this": one fresh problem per remaining objective), then offered the check ([#669]).
- The check is a clear test, set apart from teaching: announced, with no hints, and with the result and feedback at the end ([#669]).

## While a check is open

- Until the result, across visits, the session's files, its earlier teaching and its jump points are hidden. They come back with the result. Opening the session returns to the check ([#669], [#671]).
- No uploads, except a photo answer. No file can be removed, except by deleting the session (see [`sessions.md`](sessions.md)) ([#667], [#669], [#671]).
- No lookup runs while a check is open, into this session or any other. Other sessions' tutors cannot look into it until the check ends. The learner's other sessions and "What you've mastered" stay open, under the honour rule ([#671], [#732]).
- The one exception to the hiding and the lookup rule is reteaching after a refresh miss (see [Half-done checks](#half-done-checks)) ([#731], [#732]).

## Problems

- A check covers every objective not dropped, as they stand when it is offered, including any the diagnostic skipped, and any passed in another session (see [`sessions.md`](sessions.md)). Dropped objectives are not on it. After a fail, see [After a fail](#after-a-fail) ([#669], [#732]).
- Written problems, answered with working, shown one at a time as "Problem k of N". No multiple choice ([#669]).
- Each problem tests its objective as written. A "why" objective needs an explanation ([#669]).
- Problems are fresh: never seen before in the topic, and never copied from the files. Where there are files, they follow the files' style, leaving out any file the tutor declined (see [`files.md`](files.md)) ([#667], [#669], [#732]).
- A method objective gets problems that need and name the method ("Using the chain rule, ..."). An answer by another method gets "This one asks for the chain rule. Can you do it that way?" at once, right or wrong ([#669]).
- The same rules hold in every subject. "Working" is whatever shows how. The model answer carries the subject's detail ([#669]).

### How many

- Each objective gets 1 problem if easy, 2 if complex. The tutor judges this when it drafts the objectives. Crux saves it, unseen during teaching ([#669]).
- When the check is written, the judgement changes only if the objective itself changed (judged again), or teaching gave it the trouble mark (2). A check has at most 10 problems ([#669]).
- A check has at least 2 problems ([#669]).
- A failed objective gets 2 problems in the next check. A single re-added objective gets 2, the floor ([#669]).
- A prerequisite topic's check and a re-added objective's check follow every rule in this file ([#669]).

### Model answers

- With each problem, the tutor writes a model answer in a fixed format, with "must contain" points. It is checked and saved before the learner sees the problem ([#669], [#679]).
- The maths library checks it first, where it can read the answer. Otherwise a separate, independent working by the AI checks it. No match, or a disagreement, discards the problem unseen, and a new one is written ([#669], [#679], [#716]). What the library reads and how it compares is in `ai-layer.md`.

## Answers

- An answer is typed, or a photo of handwritten working for the current problem ([#669]).
- A photo is an answer, not a file. It is never course material and never taught from. Trial-link holders can send one; guest mode on the public link cannot ([#667], [#669], [#677], [#722]).
- Photo answers are kept like typed answers while the session exists, stored shrunk, outside the storage allowance (see [`files.md`](files.md)) ([#677]).
- In v1, when the shared store is full, a photo answer is refused, and the learner types their answer. The check carries on (see [`files.md`](files.md)) ([#732]).
- An answer, typed or photo, is only something to mark, never an instruction (see the main file's "Crux decides") ([#669]).
- Two reminders come at once, every time. A bare answer gets "Please show your working for this one". Another method on a method objective gets the method reminder ([#669]).
- Declining a reminder means the answer is marked as it stands ([#669]).

## Marking

- A separate marking step sees only the problem, the model answer and the reply. It returns right, wrong, slip or unsure, with a one-line reason. Pleas in the chat and text from files never reach it ([#669]).
- The maths library also compares the learner's final answer with the model answer. If it disagrees with the marker, a fresh re-mark runs before the result, told whether the final values match. The library never marks alone ([#679]).
- The tutor marks each answer, and Crux applies the pass rule: every problem must be right ([#669], [#679]).
- Forgiveness lives in the written marking rules, not in the verdict ([#669]).
- A slip is a careless surface mistake in otherwise right work ([#669]).
- The end step comes after the last problem, before the result ([#669]):
  - A slip gets one fix: "Problem 2 has a slip in the last line. Can you fix it?" Fixed is right; not fixed is wrong.
  - Unsure (an unexpected valid method, unknown notation, an ambiguous step) gets a neutral "Walk me through this step". Still unclear is wrong.
- Course notation and standard notation are both accepted. Where a file has an error, the answer is marked by the correct version, or by what the teacher said if the learner reported it back ([#669]).
- There is no reminder of file errors before the check. The result names a wrong answer that follows one: "this follows slide 12's error, which we flagged earlier" ([#669]).
- An unchecked file-error flag is reminded outside the check, never during it. Where it shows is a screens question ([#669]).
- While marking, "Marking…" may show for up to about 20 seconds ([#716]). Which model and settings each check job uses is in `ai-layer.md` ([#679]).

## The result

- The result shows pass or not yet, X of N, and each mark ([#669]).
- A wrong answer shows its model answer, the missing point, and Dispute. A right answer has its model answer behind a tap ([#669]).
- An objective got right becomes passed, dated the check's date. How passed work counts across sessions is in [`sessions.md`](sessions.md) ([#669], [#671]).

## Disputes

- One dispute per problem. The learner can say where their answer covers the point ([#669]).
- A fresh marker checks the model answer first, and corrects it if wrong. Then it re-marks the original answer, never a rewrite. The result updates, or the mark stands with its reason. "Still unclear" can be disputed ([#669]).
- A dispute stays open until the next check on that objective starts ([#669]).
- A late win makes the objective passed, dated the check's date. If it was the last one, the topic is mastered, and the menu follows (see [`learning-loop.md`](learning-loop.md)) ([#669], [#670], [#671]).

## After a fail

- Only the failed objectives go back to teaching, with the trouble mark. Passed ones stay passed. The next check covers only the failed ones ([#669]).
- The learner can drop a failed objective. It gets the "why?" and the below-3 replacement offer (see [`learning-loop.md`](learning-loop.md)) ([#669]).
- After that drop, the topic is mastered at once if what is left was proven on 2 or more check problems. Otherwise it is mastered after one more problem, under the same rules ([#669]).
- The dropped failed objective stays listed as dropped on the mastered topic ([#669]).

## Half-done checks

- Leaving mid-check keeps the answered problems. A seen, unanswered problem is swapped for a fresh one on the same objective, with the reason: "You left during problem 4, so here's a fresh one" ([#669]).
- Leaving during the end step: pending fixes and walk-throughs resume as left ([#669]).
- A half-done check never expires ([#669]).

### The refresh before a resumed check

- After 7 or more days away, the learner is offered "continue" or "refresh first". Earlier answers count either way ([#669]).
- A refresh is a short recap of the current objective and the objectives still ahead. Then comes one practice problem on the objectives still ahead only, with help allowed. Then the check continues ([#669], [#731]).
- The refresh offer says the learner can also ask for a recap of the objectives already answered. That recap has no problem, and their answers do not change ([#731]).
- A real miss (not a slip) in the practice problem puts that objective back to in progress, with the trouble mark. The check stays half-done ([#668], [#731]).
- The tutor then teaches that objective until it is shown again, then the check continues. Earlier answers still count ([#731]).
- When the check continues, that objective gets 2 problems, as any objective with the trouble mark does. If it had 1, the tutor says the check has grown by one ([#669], [#731]).
- Leaving during that teaching resumes it on return. After 7 or more days away, this same refresh offer comes first, and a real miss in it follows these same rules ([#664], [#732]).
- While that objective is taught again, no problem is open. The session's files and earlier teaching come back, and the lookup works as in teaching (see [`sessions.md`](sessions.md)). Both are hidden, and the lookup is off, again before the next check problem ([#731], [#732]).

### Pauses

- A check pauses as half-done when the owner switches checks off for a fault, or while the age question is open ([#678], [#679]).
- It also pauses when Flash-Lite is down or overloaded, or when the provider refuses calls (see `spending.md`) ([#675], [#679]).
- A paused check resumes under the half-done rules, with the open problem swapped ([#678]).
- Spending limits never stop a check that has started (see `spending.md`) ([#675]).

## Re-marks after a marking fault

- Once a marking fault is fixed, every check passed since the last passing test round is re-marked from its saved answers. Who pays is in the main file's "Money" ([#678], [#728]).
- A re-mark that finds an answer wrong returns the objective to not passed, and its topic to not mastered. Only learners whose marks change are told ([#678]).
- A problem whose mark changes gets a fresh dispute, beyond the one per problem ([#678]).
- How checks are switched off, and what starts a re-mark, is in `ai-tests.md`.

## Gaps

- **When the owner switches checks off during reteaching after a refresh miss:** whether the reteaching carries on, and whether the lookup stays on. For `ai-tests.md`, on [#736].

## Guest mode

- A guest's mini check has 2 problems on one objective, typing only. It earns nothing and is not kept (see `trial.md`) ([#677], [#722]).

## On screen

Layout is not decided (see the main file's Gaps). These rules need: the offer with its split, "Problem k of N", photo answers, "Marking…", the result with model answers behind a tap, Dispute, the passed status, open file-error flags, hidden files, the "paused" messages, and the re-mark message ([#669], [#678], [#716]).

[#664]: https://github.com/calmxz/Crux/issues/664
[#667]: https://github.com/calmxz/Crux/issues/667
[#668]: https://github.com/calmxz/Crux/issues/668
[#669]: https://github.com/calmxz/Crux/issues/669
[#670]: https://github.com/calmxz/Crux/issues/670
[#671]: https://github.com/calmxz/Crux/issues/671
[#675]: https://github.com/calmxz/Crux/issues/675
[#677]: https://github.com/calmxz/Crux/issues/677
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#716]: https://github.com/calmxz/Crux/issues/716
[#722]: https://github.com/calmxz/Crux/issues/722
[#728]: https://github.com/calmxz/Crux/issues/728
[#731]: https://github.com/calmxz/Crux/issues/731
[#732]: https://github.com/calmxz/Crux/issues/732
[#736]: https://github.com/calmxz/Crux/issues/736
