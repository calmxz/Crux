# Claude through Anthropic's API: teaching (Part 2)

Part 2 of #727, measured on **2026-11-18** through Anthropic's API with the owner's key, `anthropic` Python SDK 2.10.0. Index: `claude-anthropic-api.md`. Prices are USD. Source IDs like [S21] are in the index's source list.

## Answer

- **Teaching holds on Haiku 5.5 at `low`.** On a Crux-style prompt it kept one step per turn, warmth and a twin for the learner's own problem, and its maths was correct in 6 of 6 sittings.
- **The weak point is reporting.** Haiku's `record_problem_result` calls were imperfect in 6 of 6 sittings: 2 missed records, and wrong `helped` flags, objective numbers or duplicates. Sonnet 5.5's were right in 3 of 3.
- **A revised reporting prompt helped but did not pass.** In a follow-up, it removed the missed and duplicate records, but 5 of 43 records had a wrong value, and 2 of 6 sittings were clean. Two sittings also stated a maths step wrongly. See [Follow-up](#follow-up-a-revised-reporting-prompt).
- **Pictures and file mistakes work** on both models: graphs and flowcharts came through the tools, and both reported the lesson file's planted mistake.
- **A sitting costs about USD 0.006 on Haiku** with caching, and about 0.08 on Sonnet. The costs and the budget are in `claude-anthropic-api-budget.md`.

## How it was measured

- **Tutor prompt.** A Crux-style instruction written from `docs/spec/teaching.md`, `ai-layer.md` ("The prompt", "What the tutor reports") and `mastery-check.md` ("The offer"). It covers the LearnLM principles, Crux's rules (topic given, brief working, twins, the help ladder, readiness), pictures, LaTeX and fenced file content.
- **Tools.** Ten strict tools matching "What the tutor reports": problem result, graph, diagram, file mistake, page request, lookup, related topics, decline, age question and check offer. A small stand-in for Crux kept the objective statuses and answered each call.
- **Lesson file.** An 8-page outline of a linear-equations lesson, fenced as data, with a planted mistake on page 6: "3x - 4 = 11. Add 4: 3x = 7".
- **Prompt start.** About 4,600 tokens of instructions, tools and file, growing to about 12,600 by turn 15. The state message came after the first learner message, so the history stayed append-only.
- **Settings.** `output_config.effort` `low` on every tutor call, adaptive thinking (the default), top-level automatic caching, `max_tokens` 3,000.
- **Learners.** The three #684 learners: A, who gets it; B, who is stuck; and C, with the sign misconception. Their opening lines were verbatim from #684, B's next two lines were scripted, and Haiku 5.5 at `low` played the rest in under 50 words.
- **Sittings.** 15 learner turns each, rebuilt from #688's method because #688's scripts were no longer on disk. Haiku: A, B and C twice each, 6 sittings. Sonnet 5.5 at `low`: A, B and C once, 3 sittings.
- **Like-for-like row.** Haiku 5.5 at `low` on #684's verbatim LearnLM prompt, with no tools or file, for 3 chats of 6 turns.
- **Grading.** Opus 5.5 at `medium` graded each transcript through the Batch API against #684's 5 checks and 7 Crux checks. It answered yes, no, partly or n/a, with the turn and a quote as evidence.
- **Pictures and the file.** The simulated learners never asked for a picture, so scripted 3-turn chats ran on both models: a graph request, a flowchart request, and "Can we go through page 6 of my file?"
- **Scripts.** The scripts, transcripts and per-call usage are kept locally in `%TEMP%\crux727`, not committed, as for #688.

## Results against #684

#684's baseline: on Gemini, all three models passed checks 1 to 5, and Flash-Lite needed `low`, not `minimal`.

| Check | Haiku 5.5, #684's prompt (3 chats) | Haiku 5.5, Crux prompt (6 sittings) | Sonnet 5.5, Crux prompt (3 sittings) |
|---|---|---|---|
| 1. One step per turn | 3 yes | 5 yes, 1 partly | 3 yes |
| 2. B: a nudge, not the answer | yes | 2 partly (see below) | 1 partly (see below) |
| 3. C: finds the sign mistake by a question | yes | 1 yes, 1 partly | yes |
| 4. Summarizes and offers to continue | 3 yes | 5 yes, 1 partly | 3 yes |
| 5. A warm coach throughout | 3 yes | 6 yes | 3 yes |
| The maths it states is correct | 2 yes, 1 no | 6 yes | 1 yes, 2 partly |

- **Check 2's "partly" is Crux's rule working.** After "just tell me the answer", every B sitting did the step on the twin and gave a fresh problem. No tutor wrote the answer to the learner's own problem, 2x - 7 = 9. That is step 3 of Crux's help ladder, where "just show me" skips to the tutor doing the step on the twin. #684's wording asks for a nudge instead, so the grader marked it partly.
- **The one "no":** on #684's prompt, Haiku told learner C "Your first step was subtracting 3 from both sides, and that's right. You got 4x = 22". But 19 - 3 is 16.
- **Sonnet's two "partly" verdicts** were misleading phrasing, not wrong results. In one, it said "The 7 is added first here" about 7 + 4x.

## Crux's own checks

| Check | Haiku 5.5 (6 sittings) | Sonnet 5.5 (3 sittings) |
|---|---|---|
| Every turn ends with something to do | 2 yes, 4 partly | 2 yes, 1 partly |
| Never asks for a topic it already has | 6 yes | 3 yes |
| Teaches the learner's own problem on a twin (B and C) | 3 yes, 1 partly | 2 yes |
| Reports each answered problem correctly | 6 partly | 3 yes |

- **The reporting misses.** Two sittings each skipped one `record_problem_result`: one at the last turn, where the tutor asked for a check first, and one mid-sitting. The others had wrong values:
  - `helped: false` where a hint had been given;
  - a two-step equation filed under the brackets objective;
  - the learner's own problem recorded three times with conflicting results.
- This is the gap `ai-layer.md` already lists for Flash-Lite at `low`: "a tutor that forgets to report a solved problem leaves an objective unshown". It is measured here for Haiku, not closed.
- **The "partly" on twins** was one C sitting that coached the learner straight through their own problem. It never solved the problem for them.
- **No sitting reached a bare right answer** on a fresh problem, so the "how did you get that?" check was not tested.

## Pictures and the file mistake

Scripted chats, one per model and request:

| Request | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|
| "Show me 3x + 5 = 20 as a graph" | `show_graph`, both turns | `show_graph`, both turns |
| "Draw the steps as a flowchart", then for brackets | `show_diagram`, `flowchart`, both turns | `show_diagram`, `flowchart`, both turns |
| "Go through page 6 of my file" | Taught a twin first, then `report_file_mistake` on turn 2 | `report_file_mistake` on turn 1 |

- Every diagram was a `flowchart` with no styles or classes, so it would pass the parse check in `ai-layer.md`.
- On the graph request, Sonnet drew a twin, y = 2x + 1, and left the learner's own equation to them. That follows the twin rule.
- Both flagged page 6 with the file's step (3x - 4 = 11 to 3x = 7) and the correction (3x = 15, x = 5).
- When the learner said "My teacher said the file is right", neither model filled `teacher_said`. Both sent the learner to check by substitution.

## Refusals and limits

- **No refusals** in 264 tutor calls: 172 on Haiku and 92 on Sonnet, all on algebra.
- No tutor reply reached `max_tokens`.
- Three simulated-learner replies reached their own 400-token cap. That does not affect the tutor.

## Follow-up: a revised reporting prompt

Run on 2026-11-19, after #727 closed. Only the reporting part of the tutor prompt changed.

- **The change.** The prompt's one line on `record_problem_result` became a "Reporting results" section:
  - report in the turn a problem ends, before the reply, including a turn that offers the check;
  - one record a problem, with a whole twin counted as one problem;
  - the objective from the problem's form: the unknown on both sides is 3, otherwise brackets is 2, otherwise 1;
  - `helped` is true after any nudge, hint, worked step or similar example;
  - `result` is the most serious thing that happened: misconception, wrong, slip not fixed, slip fixed, bare right, right.
- **These rules are a test choice, not Crux's.** `ai-layer.md` doesn't say how to report a problem that took several attempts. The rules were written to agree with the test's stand-in for Crux, and the owner has not chosen them.
- **The same run otherwise:** Haiku 5.5 at `low`, learners A, B and C twice each, 15 turns, and the same Opus grader.
- **Scoring by hand.** Each record was checked against its transcript under the rules above. A problem counts when the learner was asked to solve it. A "what would you do first?" question doesn't count.
- **The pass mark:** every answered problem recorded once with the right values, in all 6 sittings.

| | First prompt (6 sittings) | Revised prompt (6 sittings) |
|---|---|---|
| Records | 47 | 43 |
| Missed records | 2 | 0 |
| Problems recorded more than once | 1, three times | 0 |
| Records with a wrong value | at least 2 | 5 |
| Sittings with every record right | 0 | 2 (A2 and C1) |

The first prompt's column comes from the grader and the notes above, not from this hand check.

- **The 5 wrong values:**
  - **C2:** the learner's sign misconception was filed as `wrong`. That drops the trouble mark, so objective 1 was shown after one fresh problem, not two.
  - **B2:** the tutor gave the steps for 4x + 3 = 23 before the learner started ("undo the +4 first, then undo the x 4"), but filed it with `helped: false`. That made objective 1 shown, so all 3 of B2's check offers came too early.
  - **A1:** 2(x + 4) = 3(x - 1) has the unknown on both sides, but it was filed under brackets (2), not 3.
  - **B1 and B2:** the learner's own problem, 2x - 7 = 9, came after a twin but was filed with `helped: false`. An own problem never makes an objective shown, so no status changed.
  - C2 and B2 are the two errors that changed a status.
- **Judgement calls,** counted as right above:
  - A "which would you do first?" question that the learner solved in full was recorded in B1 but not in C2.
  - A confirmation between steps, such as "Your first step is right", was filed as help in A2 and B1 but not in C1. Counting it as help would put C1 among the failures.
  - A2 filed the file's page-5 example as `own`. The prompt says a problem from the learner's file is their own.
- **Also seen:**
  - B1 called `offer_mastery_check` while objective 3 was in progress, and its reply said so.
  - In both B sittings, the learner gave up on the twin, and it was filed as `wrong`. The result list has no value for giving up.
  - C2's note on 2(x - 3) = -x + 9 says "subtracted 6", but the learner added 6. Crux doesn't act on the note.
  - The grader's one verdict per sitting passed A1 and B1 and missed C2's misconception. A reporting test needs a check per record.
- **What neither run tested.** The simulated learners made few mistakes: 2 sign misconceptions (C) and 2 give-ups (B). B never made its scripted slip or bracket mistake, and no learner gave a bare answer. So no slip, slip fix or bare answer was ever reported.

The teaching checks, from the grader:

| Check | First prompt | Revised prompt |
|---|---|---|
| One step per turn | 5 yes, 1 partly | 6 yes |
| Summarizes and offers to continue | 5 yes, 1 partly | 2 yes, 4 partly |
| Every turn ends with something to do | 2 yes, 4 partly | 4 partly, 2 no |
| The maths it states is correct | 6 yes | 4 yes, 2 no |
| Reports each answered problem | 6 partly | 3 yes, 3 partly |

The other checks didn't change: warmth, the topic, twins, B's nudge and C's sign question. One learner, A2, asked for a graph this time, and `show_graph` drew it.

- **Two maths errors:**
  - **C2,** right after the sign lesson: "Subtracting 2 first, then dividing by 5, is the method" for 5x - 2 = 13. The learner had added 2, which is right.
  - **B2:** "undo the +4 first" for 4x + 3 = 23.
- **Turn endings.** Most of the turns without a task end on the check offer, or are send-offs after the learner chose to start the check. The revised sittings offered the check 11 times, against 7.
- **Cause unknown.** The new text says nothing about maths or turn endings, and 6 sittings can't separate the change from run-to-run variation.
- **Cost:** 0.0069 a sitting with a 1-hour cache (0.0042 to 0.0087), against 0.0063. That's about 23 calls and 204,000 input tokens a sitting. There were no refusals in 137 tutor calls, and no reply reached `max_tokens`. The 6 grades cost 0.21.

## What this changes

- **#802:** Haiku teaching has not passed its reporting test. A further prompt is a new test with its own count. Its learners should be scripted to make each kind of mistake. The reporting rules need the owner's choice before any pass counts.
- **#679:** Haiku 5.5 at `low` can take the teaching job, with a strict tool schema. Its tool-reporting reliability needs the same AI test that `ai-layer.md` plans for Flash-Lite. Sonnet 5.5 reported cleanly at about 14 times the cost.
- **#679:** the test confirms the "what the tutor reports" tool set works on Claude, including #751's graph, diagram and file-mistake outputs.
- **#678:** the 12 grades cost USD 0.37 through the Batch API at half price, about 0.031 a transcript, on Opus 5.5 at `medium`.
