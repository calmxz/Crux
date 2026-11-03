# Teaching

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them. Where this file names an area file not yet written, use that file's source tickets in the main file's index.

This file covers how the tutor teaches a topic until the learner is ready for the mastery check. Topics, objectives and changes to them are in [`learning-loop.md`](learning-loop.md). The check is in [`mastery-check.md`](mastery-check.md).

## How the tutor teaches

- The tutor's instruction is built on the LearnLM prompt guide. Its five principles and moves are kept, the parts that clash are rewritten, and Crux's rules are added. For example, it never asks for a topic it already has ([#668]). Models and settings are in `ai-layer.md`.
- Within a topic, the tutor adapts pace, explanation, practice difficulty and examples. It adapts from the learner's answers and from direct asks ("slower", "another way") ([#668]).
- One step per turn. Every turn ends with something for the learner to do: the next step, a prediction, or "why does that work?" ([#668])
- Practice asks for brief working. A bare answer is accepted, but it cannot make an objective shown on its own. On a fresh problem, a bare right answer gets "how did you get that?" ([#668])
- Questions about the material are answered ([#667]).

### Wrong answers

- The tutor reads the working first ([#668]):
  - A bare wrong answer gets "how did you get that?".
  - Two possible causes get a narrow question that tells them apart.
  - A visible cause is named, with a pointed question.
  - "I don't know" goes to the help ladder.
- A misconception is shown where it breaks, then confirmed fixed with a fresh question. The objective gets the trouble mark ([#668]).
- A slip gets a light nudge at the spot. Fixed by the learner, nothing changes, even on a shown objective. Not fixed, it is treated as a misconception or a gap ([#668]).

### The learner's own problem

- The tutor never works the learner's own problem, typed or in any file. It teaches on a twin, then coaches the learner through their own ([#667]).
- The twin is taught faded: the tutor works the early step or steps, and the learner the rest. How many adapts to how they are doing ([#668]).
- On the learner's own problem, step 3 of the help ladder shows the step on the twin and hands the problem back. The tutor never writes the answer. It only confirms a right one ([#668]).

## Objective statuses and readiness

- Every objective shows a status: not started, in progress, shown, passed, or dropped ([#668], [#669]). Crux keeps the statuses and hands them to the tutor (see the main file's "Crux decides").
- **Shown:** the learner solved a fresh problem on the objective with no help. Their working, or their reply when asked, shows the method ([#668]).
- **Fresh problem:** one the tutor writes at that point, not seen before in the topic. It is not the learner's own problem, not a twin they were taken through, and not earlier practice ([#668]). The diagnostic, the quick route and the check use the same rule.
- A real miss (not a slip) on a shown objective puts it back to in progress. This includes a refresh problem after 7 or more days away (see `sessions.md`), and the refresh before a resumed check (see [`mastery-check.md`](mastery-check.md)) ([#668], [#671], [#731]).
- **Trouble mark:** an objective gets it when it goes back to in progress, needs a misconception fixed, or fails a check. It then needs 2 fresh problems in a row, unhelped, to be shown. Using a hint does not give the trouble mark ([#668], [#669]).
- **Ready:** every objective not dropped is shown. The tutor then offers the check. The learner is never pushed into it ([#663], [#668]).
- The learner can jump to any objective. If it needs an earlier one not yet shown, the tutor says so and suggests that one first. The learner decides ([#668]).

## The help ladder

- The ladder is for "I get the idea but can't see the next move". On the same problem ([#668]):
  1. A nudge question.
  2. A more specific hint.
  3. The tutor does the step and explains it.
  4. A fresh similar problem, for the learner alone.
- "Just show me" skips to step 3 ([#668]).
- Not getting the idea at all gets another explanation, not the ladder ([#668]).

## Missing basics

- A missing basic shows on the ladder, when a hint relies on something the learner cannot do. One quick question confirms the gap ([#668]).
- **Detour:** a gap of a single rule. The tutor names it, teaches it in a few turns with one check question, and returns to the same step. The objectives do not change ([#668]).
- **Prerequisite topic offer:** a gap of a whole topic. The tutor offers to teach it first, and the learner decides. A failed detour check, or a second missing basic, becomes this offer. The learner can still ask for a detour ([#668]).
- A prerequisite topic pauses the current topic, with its statuses kept. It has its own objectives and its own check. Once it is mastered, the learner returns to where they left, with no menu ([#668], [#670]).
- The learner can go back to the paused topic before the prerequisite is mastered. The prerequisite stays paused with what was shown, and can be resumed. The tutor suggests finishing it if the gap shows again ([#668]).
- A confirmed gap in something passed in another session gets the same detour or prerequisite offer. The tutor names the pass: "You passed the chain rule back in November, so let's do a quick refresher." The record stays passed ([#671]).

## Never ready

- After 3 missed fresh problems on one objective, the tutor asks what is not clicking and tries a fix aimed at the answer ([#668]).
- If the learner cannot say, or the fix does not help, the tutor names the pattern it sees in the misses. For example: "Your last three answers all forget to multiply by the inside's derivative." ([#731])
- Then it offers a numbered menu ([#668], [#731]):
  1. Learn it a different way, marked as recommended. The tutor asks which way the learner wants, and suggests some: simpler steps, a picture set out in text, a worked example, or an everyday comparison.
  2. Check for a missing basic.
  3. Drop this objective.
  4. Stop for now.
- A drop from the menu happens at once, with no "why?", because the menu is the help offer. If it leaves fewer than 3 objectives, one replacement offer follows (see [`learning-loop.md`](learning-loop.md)) ([#668], [#731]).
- After "different way" or "missing basic", the miss count restarts ([#668]).
- The 3 is a starting value, for the meantime, and can be tuned ([#668]).

## The diagnostic

- After the objectives are set out, at every topic's "go", the learner can say "I know some of this". The tutor gives one fresh problem per objective claimed. A claim alone skips nothing ([#666], [#668], [#670]).
- Right, with working that shows the method: shown, and its teaching is skipped. Bare, wrong working, or wrong: taught as normal, with no penalty. Each problem tests its objective as written ([#668]).
- A skipped objective that the learner later misses gets the trouble mark ([#668]).
- "I know this" mid-teaching works the same way, on the current objective ([#668]).
- A learner who claims and passes every objective is ready at once, and is offered the check ([#668]).
- The diagnostic never grants mastery. Skipped objectives are still on the mastery check ([#664], [#668]).

## Preferences

- A preference is stated by the learner, or noticed by the tutor and confirmed ("use real-world examples"). It carries across sessions. The learner can see and remove it ([#668]). How it is kept is in `sessions.md` ([#671]).
- Nothing the tutor infers about the learner, such as recurring mistakes or strengths, is stored ([#668]).

## Gaps

- Whether the chat can show drawings is not decided (screens and layout). Until it is, the "picture" way is set out in text ([#731]).

## On screen

Layout is not decided (see the main file's Gaps). These rules need: each objective's status, paused topics, the never-ready menu, and the learner's preferences with a way to remove each ([#668]).

[#663]: https://github.com/calmxz/Crux/issues/663
[#664]: https://github.com/calmxz/Crux/issues/664
[#666]: https://github.com/calmxz/Crux/issues/666
[#667]: https://github.com/calmxz/Crux/issues/667
[#668]: https://github.com/calmxz/Crux/issues/668
[#669]: https://github.com/calmxz/Crux/issues/669
[#670]: https://github.com/calmxz/Crux/issues/670
[#671]: https://github.com/calmxz/Crux/issues/671
[#731]: https://github.com/calmxz/Crux/issues/731
