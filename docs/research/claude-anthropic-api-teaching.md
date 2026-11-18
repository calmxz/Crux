# Claude through Anthropic's API: teaching (Part 2)

Part 2 of #727, measured on **2026-11-18** through Anthropic's API with the owner's key, `anthropic` Python SDK 2.10.0. Index: `claude-anthropic-api.md`. Prices are USD. Source IDs like [S21] are in the index's source list.

## Answer

- **Teaching holds on Haiku 5.5 at `low`.** On a Crux-style prompt it kept one step per turn, warmth and a twin for the learner's own problem, and its maths was correct in 6 of 6 sittings.
- **The weak point is reporting.** Haiku's `record_problem_result` calls were imperfect in 6 of 6 sittings: 2 missed records, and wrong `helped` flags, objective numbers or duplicates. Sonnet 5.5's were right in 3 of 3.
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

## What this changes

- **#679:** Haiku 5.5 at `low` can take the teaching job, with a strict tool schema. Its tool-reporting reliability needs the same AI test that `ai-layer.md` plans for Flash-Lite. Sonnet 5.5 reported cleanly at about 14 times the cost.
- **#679:** the test confirms the "what the tutor reports" tool set works on Claude, including #751's graph, diagram and file-mistake outputs.
- **#678:** the 12 grades cost USD 0.37 through the Batch API at half price, about 0.031 a transcript, on Opus 5.5 at `medium`.
