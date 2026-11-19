# Claude through Anthropic's API: tutor reports and effort levels (#802)

A test for #802 Question 5, run on **2026-11-19** through Anthropic's API with the owner's key. Index: `claude-anthropic-api.md`. Prices are USD. It follows the revised reporting prompt in `claude-anthropic-api-teaching.md` ("Follow-up") and the Haiku writer run in `claude-anthropic-api-check.md`.

## Answer

- **No setup passed.** The bar was "every answered problem recorded once with the right values, in all 6 sittings". The best setups had 4 of 6 sittings clean.
- **Higher effort had fewer wrong values on both models,** but 6 sittings a setup can't rank them:
  - Haiku 5.5: 5, 5 and 2 wrong values at `low`, `medium` and `high`, with 2, 2 and 4 clean sittings.
  - Sonnet 5.5: 8, 6 and 3 wrong values, with 2, 1 and 4 clean sittings.
- **The commonest error was `helped: false` where help was given:** 16 of the 29 wrong values, on 5 of the 6 setups, with none on Haiku at `high`. 13 of the 16 came after the tutor named the method or first move while setting the problem. The test read that as help.
- **Four sittings accepted a wrong answer** after a scripted slip. That is a teaching error, and the report then recorded the wrong answer as right.
- **Cost a sitting rose with effort:** Haiku 0.0064 to 0.0093, Sonnet 0.094 to 0.118.
- **Opus 5.5 gave the same results at all three efforts** in its suggested role. A check that also reads the worked solution caught both wrong worked solutions, with no false flags.
- **Spend:** USD 6.00 for this run, 8.38 in all. That overran the 8.00 stop by 0.38, because the guard only checks before a batch.

## How it was measured

- **Prompt.** A third reporting prompt (v3), built on #802 Questions 3 and 4: one summary report per problem, sent in the turn it ends, and the help list, where a fixed slip counts as an unhelped solve, with a note. It also defines misconception against wrong, picks the objective by the problem's hardest feature, and says a bare answer explained when asked is "right". **The v3 wording is a test choice, not Crux's prompt.**
- **Stand-in for Crux.** A fixed slip on a fresh, unhelped problem counts as a solve and adds a "fixed slip noted" mark to the statuses the tutor sees.
- **Matrix.** Haiku 5.5 and Sonnet 5.5, each at effort `low`, `medium` and `high`. Learners A, B and C twice each, 15 turns, `max_tokens` 8,000, a 5-minute cache. 6 setups x 6 sittings = 36 sittings.
- **Scripted mistakes.** The harness, not the simulated learner, sent 3 mistakes a sitting:

  | Learner | Events, in order | From turns |
  |---|---|---|
  | A | bare answer, slip then fix, steps first | 4, 7, 10 |
  | B | give up, slip then fix, bare answer | 5, 8, 11 |
  | C | misconception, slip then fix, steps first | 5, 8, 11 |

  - Each event fires at the first learner turn from its set turn where a Haiku check finds a newly set equation.
  - The harness builds each message from a solved equation. A bare answer is the final value only. A slip is the right steps with the final value off by one. A misconception uses the same-operation rule in step 1. Steps first and give up are fixed text.
  - The expected record for each event was written into the harness before the counted sittings.
- **Why scripted.** In the second pilot, the simulated learner was told to make each mistake and didn't: 0 of 6 slips and 0 of 2 misconceptions. The first two pilots changed only the harness, and their sittings are not counted. A third pilot sitting is counted (see [Where Haiku `low` C1 came from](#where-haiku-low-c1-came-from)).
- **Grading.** Opus 5.5 at `medium`, through the Batch API, in one batch of 42: the 36 sittings and 6 control transcripts. Per record, it quoted what the tutor said on the problem, then judged each field, under the v3 rules, with short outputs. It also listed missed and duplicate records, judged each scripted event, and answered the #684 and Crux teaching checklist.
- **Scoring.** The run was graded under the v3 test prompt's rules and the bar "every answered problem recorded once with the right values, in all 6 sittings". "Naming the method counts as help" was a test reading. No rescore was done under the owner's later rules.
- **Scripts.** The scripts, transcripts and per-call usage are kept locally, not committed.

## Results per setup

| Setup | Records | Wrong values | Of which moved a status | Missed | Duplicates | Clean sittings | Events happened / right record | Maths stated wrong (sittings) | Tutor cost a sitting |
|---|---|---|---|---|---|---|---|---|---|
| Haiku `low` | 49 | 5 | 4 | 2 | 0 | 2 of 6 | 17 of 18 / 15 | 3 | 0.0064 |
| Haiku `medium` | 51 | 5 | 1 | 1 | 0 | 2 of 6 | 18 / 14 | 1 | 0.0076 |
| Haiku `high` | 52 | 2 | 0 | 0 | 0 | 4 of 6 | 18 / 16 | 1 | 0.0093 |
| Sonnet `low` | 51 | 8 | 7 | 0 | 0 | 2 of 6 | 18 / 14 | 0 | 0.094 |
| Sonnet `medium` | 51 | 6 | 5 | 0 | 0 | 1 of 6 | 17 of 18 / 14 | 1 | 0.099 |
| Sonnet `high` | 52 | 3 | 3 | 1 | 0 | 4 of 6 | 18 / 16 | 0 | 0.118 |

- **Totals:** 49 + 51 + 52 + 51 + 51 + 52 = 306 records, with 5 + 5 + 2 + 8 + 6 + 3 = 29 wrong values and 2 + 1 + 0 + 0 + 0 + 1 = 4 missed records.
- **Events.** All 108 scripted events fired (36 x 3). "Happened" is the grader's view that the event really took place as scripted on a problem. The 2 that didn't were slips the tutor called right.
- **"Moved a status"** is a script heuristic: a wrong record that, as sent, counted a fresh problem as an unhelped solve, or a wrong result touching a miss. Treat it as approximate.
- **Costs** are the tutor's calls only. Learners and grading are excluded.
- **Effort and cost,** from the unrounded means: Haiku `high` costs 0.00933 / 0.00639 = 1.46 times `low`, and Sonnet `high` 0.1178 / 0.0944 = 1.25 times. Sonnet `low` costs 0.0944 / 0.00639 = about 15 times Haiku `low`.
- **No refusals and no `max_tokens` stops** in any sitting.

### Where Haiku `low` C1 came from

The counted Haiku `low` C1 sitting is a third pilot run, kept as counted. It ran at 20:57, on the final harness, which was last changed at 20:56. The other five Haiku `low` sittings ran at 20:58. The expected records were in the harness before it ran, but were saved to their own file 17 seconds after it ended. Without it, Haiku `low` reads:

| Setup | Records | Wrong values | Missed | Clean sittings | Events happened / right record | Maths stated wrong |
|---|---|---|---|---|---|---|
| Haiku `low`, 5 sittings without C1 | 41 | 5 | 2 | 1 of 5 | 14 of 15 / 12 | 2 |

C1 had no wrong value, no missed record, and all 3 events recorded right, so leaving it out makes Haiku `low` look worse, not better. No setup passes either way.

## The errors

- **`helped: false` where help was given.** Most came after the tutor named the method or first move while setting the problem: "solve it with the method you didn't use before: expand the bracket first", "which side has more x, and why would you move the x terms to that side?". Under the test's reading, that is help.

  | Setup | Haiku `low` | Haiku `medium` | Haiku `high` | Sonnet `low` | Sonnet `medium` | Sonnet `high` |
  |---|---|---|---|---|---|---|
  | `helped` among wrong values | 3 of 5 | 2 of 5 | 0 of 2 | 5 of 8 | 3 of 6 | 3 of 3 |
  | Of which, the method named while setting | 3 | 0 | 0 | 4 | 3 | 3 |

  - In all: 3 + 2 + 0 + 5 + 3 + 3 = 16 of 29, and 3 + 0 + 0 + 4 + 3 + 3 = 13 from naming the method.
  - The other 3: steps given on the learner's steps-first request (Haiku `medium` C1 #4, Sonnet `low` C1 #7), and a pointer at the faulty step (Haiku `medium` C1 #2).
  - On Sonnet, naming the method is 10 of the 15 errors that moved a status (4 of 7, 3 of 5 and 3 of 3).
- **A tutor-set problem filed as `own`:** 6 records, 2 on Haiku and 4 on Sonnet.
- **A misconception filed as `wrong`:** 3 records, all Sonnet (`low` C1, `low` C2, `medium` C2).
- **Missed records:** 2 faded twins (Haiku `low` C2), 1 twin (Haiku `medium` C2) and 1 re-attempt (Sonnet `high` B2).
- **Others:** one `bare_right` where the method was shown later (Haiku `medium` B1), one wrong objective (Haiku `high` A2), and two records with the wrong timing: Haiku `medium` A2 #2, a turn late, and C1 #2, before the problem ended.
- **The tutor called a wrong answer right** after the scripted slip in 4 sittings:
  - Haiku `low` A1 and A2: 3(x + 2) = 21, accepted x = 6.
  - Haiku `high` A1: accepted x = 6 for x = 5.
  - Sonnet `medium` B2: accepted x = 5 for x = 4.

  The stand-in then recorded a wrong answer as right. Haiku `low` C1 also told a learner using the wrong rule "Your method is right". These are teaching errors, not report errors.
- **Teaching checklist:** warmth 36 of 36 yes, and never asked for the topic 36 of 36. It is one verdict per sitting, so it is coarse.

## The grader

Calibration ran on the revised run's 6 transcripts (`claude-anthropic-api-teaching.md`, "Follow-up"): 43 records, with 5 known wrong values from its hand score under the v2 rules.

| Grader | Rules | Known wrong values found | Other flags | Missed-record flags | Cost a transcript |
|---|---|---|---|---|---|
| Plain, `low` | v2 | 2 of 5 | 1 | 1 | 0.022 |
| Plain, `medium` | v2 | 2 of 5 | 1 | 1 | 0.026 |
| Plain, `high` | v2 | 2 of 5 | 1 | 1 | 0.030 |
| Evidence-first, `medium` | v2 | 5 of 5 | 2 | 1 | 0.038 |
| Evidence-first, `medium` | v3 | 5 of 5 | 2 | 1 | 0.040 |
| Evidence-first, short outputs, `medium` (the control in the final batch) | v3 | 5 of 5 | 4 | 1 | 0.028 |

- **Effort made no difference** to the plain grader: at every level it found A1 #5 and B1 #3, flagged A2 #4, and flagged a missed record in C2.
- **Evidence-first** means it quotes what the tutor said on the problem before judging it. It found all 5, and became the grader used.
- **The other flags** are counted against the v2 hand key. v3 is stricter, so some may be right under v3; they were not hand-checked. The missed-record flag is the same C2 problem in every row.
- **The final batch used the short-output wording.** Only the control covers that wording: 5 of 5, at 0.16986 / 6 = 0.028 a transcript.

## Opus 5.5 in its role, at `low`, `medium` and `high`

Three tasks, 40 calls at each effort:

- **The independent check, unchanged,** on cases 2 to 7 of the mastery-check hard cases, for two saved sets of model answers: Sonnet 5.5's repeat 5 and Haiku 5.5's repeat 2 (`claude-anthropic-api-check.md`). 12 calls.
- **A new check that also reads the worked solution,** on the same 12 model answers. 12 calls.
- **Re-marks** of the 16 hard-case answers against Sonnet's model answers, told the maths library's result. 16 calls.

| | `low` | `medium` | `high` |
|---|---|---|---|
| Unchanged check: agrees, of 12 | 11 | 11 | 11 |
| New check: real errors caught | 2 of 2 | 2 of 2 | 2 of 2 |
| New check: flags on right answers | 0 of 10 | 0 of 10 | 0 of 10 |
| Re-marks matching the key, of 16 | 13 | 13 | 13 |
| Refusals, of 40 calls | 0 | 0 | 0 |
| Cost a call: check / new check / re-mark | 0.0061 / 0.0067 / 0.0066 | 0.0068 / 0.0080 / 0.0073 | 0.0074 / 0.0094 / 0.0076 |
| Cost of the 40 calls | 0.259 | 0.294 | 0.323 |

- **The unchanged check's one disagreement,** at every level, is Haiku's case 4 worked solution, with its wrong second example. It caught it beyond its instructions, as before. It never flagged case 7.
- **A second wrong worked solution.** Haiku's case 7 says `' OR '1'='1` makes a login query with `AND password = '...'` "always true". AND binds tighter than OR, so the password check still applies, and it is not always true. The new check flagged it at all three levels.
- **Two keys.** The key written before the run had one wrong worked solution, case 4. By it, the new check caught 1 of 1 and flagged 1 of 11 right answers. Case 7 was found wrong when that flag was read after the run. With case 7 counted wrong, it caught 2 of 2 with 0 false flags, as the table shows.
- **Re-marks:** the same 3 strict "wrong" marks at every level:
  - answer 8, a guess-and-check, where the key says right or unsure;
  - 3B, with no interval written;
  - 5A, with the surface area not tied to diffusion.

  Answer 8 and 3B are #727's strict but defensible readings (`claude-anthropic-api-check.md`, "Marking"). 5A is new: Sonnet's own mark on it, against the same model answer, was right.
- **Effort and cost:** from `low` to `high`, a call costs 0.0074 / 0.0061 = 1.21 times as much for the check, 0.0094 / 0.0067 = 1.40 for the new check, and 0.0076 / 0.0066 = 1.15 for a re-mark.

## Spend

| Part | USD |
|---|---|
| Tutor sittings, Haiku, pilots included | 0.19 |
| Tutor sittings, Sonnet | 1.87 |
| Simulated learners and event checks | 0.16 |
| Opus role | 0.88 |
| Grading, calibrations | 0.93 |
| Grading, final batch | 1.97 |
| **This run** | **6.00** |

- **This run:** 0.1863 + 1.8663 + 0.1631 + 0.8762 + 0.9313 + 1.9748 = 5.998, so 6.00. The pilots were 0.065 of it.
- **In all:** 2.3867 before this run + 5.9979 = 8.3846, so 8.38.
- **Over the stop:** 8.38 - 8.00 = 0.38.
- **Why the stop didn't hold.** The guard only checks before a batch is submitted. Spend was 8.3846 - 1.9748 = 6.41 when the final batch went in, under 8.00. The batch's cost is only known when its results come back. It averaged 3,326 output tokens a sitting transcript.

## Limits

- **6 sittings a setup is a small sample.** Differences of one or two records are noise, so don't rank setups on them.
- **The rules are the test's.** The v3 wording is a test choice, not Crux's prompt. "Naming the method counts as help" was a test reading. No rescore was done under the owner's later rules.
- **The bar** is the test's: every answered problem recorded once with the right values, in all 6 sittings.
- **Algebra only,** with simulated learners and scripted mistakes.
- **One grader,** Opus 5.5, checked by a 6-transcript control, not a full hand check.
- **Haiku `low` C1** is a pilot run kept as counted (see [Where Haiku `low` C1 came from](#where-haiku-low-c1-came-from)).
- **"Moved a status"** is a heuristic, and the teaching checklist is one verdict per sitting.
- **The spend overran the 8.00 stop by 0.38,** because the guard only checks before a batch.
