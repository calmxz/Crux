# What thinking tokens add to a sitting's cost on Gemini

Research for issue #688 (child of #661). Measured on **2026-10-21** through the Gemini Developer API on a paid Tier 1 project, with `google-genai` 2.32.0. Prices are USD per 1M tokens, Standard tier. Source IDs like [S1] point to the list at the end.

A **sitting** here is what the cost notes call a "typical session": one visit of 15 learner turns, then the mastery check and a progress update, 18 model calls in all [S5]. A glossary Session is a learning thread that can span several sittings.

## Answer

| Setup | Thinking per reply: median / mean / max | Thinking per sitting: mean (range over 6) | Sittings per $5, cached: none -> with thinking | Uncached: none -> with thinking |
|---|---|---|---|---|
| 3.5 Flash-Lite at `low` | 13 / 60 / 311 | 896 (93 to 1,616) | 152 -> **141** | 93 -> **83** |
| 3.8 Flash at `low`, to 2026-12-31 | 94 / 110 / 495 | 1,645 (0 to 3,419) | 76 -> **67** | 42 -> **35** |
| 3.8 Flash at `low`, from 2027-01-01 | same | same | 38 -> **33** | 21 -> **17** |
| 3.8 Flash at `medium`, to 2026-12-31 | 268 / 282 / 901 | 4,232 (3,200 to 5,831) | 76 -> **55** | 42 -> **29** |
| 3.8 Flash at `medium`, from 2027-01-01 | same | same | 38 -> **27** | 21 -> **14** |

1. **Thinking is lighter than the +500-per-call sensitivity in the cost note assumed** [S5]. Flash-Lite at `low` averages about 60 thinking tokens a reply and loses about 7% of its sittings (152 to 141), not the 41% that sensitivity gave (90). 3.8 Flash at `medium`, its default, averages about 280 and loses about 28% (76 to 55).
2. **The ranking holds.** With caching, Flash-Lite at `low` gets about 2.1x the sittings of 3.8 Flash at `low` before 2027-01-01 and 4.3x after. Against 3.8 Flash at `medium` it gets 2.6x and 5.2x.
3. **Thinking bills twice.** It bills as output once [S2]. Then the thought signature that comes back with the reply is sent back on the next call. It adds input tokens equal to the thinking tokens (measured 1.000 per thinking token, plus about 1 token per turn), and it stays in the history for every later call. Google says only that signatures "will increase the input tokens you are charged when sent back" [S2]; no page gives the size. With caching this costs little, because history reads at a tenth of the input price. Without caching, it costs 5 sittings per $5 on Flash-Lite and up to 7 on 3.8 Flash at `medium`. Leaving signatures out is allowed for plain chat, but Google warns that "omitting signatures will degrade the model's reasoning and answer quality" [S3]. So it is not a free saving.
4. **No implicit cache hit happened in 270 tutor calls.** That includes 32 calls on 3.8 Flash with prompts of 4,096 tokens or more, the documented minimum [S4], on a paid project. Implicit caching comes with "no cost saving guarantee" [S4]. Google says the Interactions API's stateful mode "allows the system to more easily utilize implicit caching for the conversation history" [S7]; that was not tested here. Until Crux's own prompts are seen to hit the cache, the uncached column is the safer budget figure.
5. **Sittings vary widely.** One 3.8 Flash `low` sitting thought on no turn at all, and another thought 3,419 tokens. If every sitting thought like the heaviest measured one, the cached figures would be 131 on Flash-Lite `low`, 58 / 29 on 3.8 Flash `low`, and 51 / 25 on `medium`.

## How it was measured

- **Tutor.** The LearnLM guide's math-coach system instruction, verbatim, as in #684 [S6], at temperature 1.0, through the SDK's chat. The SDK sends thought signatures back automatically [S2]. Every reply carried one.
- **Setups.** `gemini-3.5-flash-lite` at `low`; `gemini-3.8-flash` at `low` and at `medium` (its default) [S2]. `minimal` on 3.8 Flash returns HTTP 400, "Thinking level MINIMAL is not supported for this model", so `low` is its floor.
- **Learner.** 3.5 Flash-Lite at `minimal` played the three #684 learners: the one who gets it, the stuck one, and the one with the sign misconception. Their opening lines were verbatim from #684, and the rest were kept under 50 words. When the tutor wrapped up, the learner took a harder equation, so every sitting ran 15 learner turns. Each learner ran twice per setup: 6 sittings and 90 replies per setup.
- **Read per reply** from `usage_metadata`: `prompt_token_count`, `cached_content_token_count`, `candidates_token_count`, `thoughts_token_count` [S2].
- **Signature input.** Measured as the prompt's growth from one call to the next, minus the previous visible reply and the new learner message (`count_tokens`). Fitted against the previous reply's thinking tokens, it was 1.0 + 1.000 x thinking on Flash-Lite `low` and 3.8 Flash `low`, and 1.1 + 1.000 x on 3.8 Flash `medium` (84 turn pairs each).
- **Spend.** $0.69 at paid prices ($0.59 tutor, $0.10 simulated learner).
- **Scripts and per-call data** (with transcripts) are kept locally in `%TEMP%\crux-688`, not committed.

## Details per setup

| | 3.5 Flash-Lite `low` | 3.8 Flash `low` | 3.8 Flash `medium` |
|---|---|---|---|
| Replies with no thinking | 35 of 90 | 39 of 90 | 0 of 90 |
| p90 thinking per reply | 188 | 244 | 417 |
| Mean thinking on turn 1 (the most of any turn) | 186 | 185 | 349 |
| Visible reply: median / mean / max | 66 / 75 / 271 | 83 / 102 / 274 | 83 / 102 / 295 |
| Largest prompt reached | 2,984 | 5,309 | 7,816 |
| Calls at 4,096 prompt tokens or more / with cache hits | 0 / 0 | 6 / 0 | 26 / 0 |
| Cost of a measured sitting itself (short instruction, no retrieval, no check) | $0.0113 | $0.0330 | $0.0543 |

**Visible replies were far shorter than the cost shape assumes** (median 66 to 83 tokens against 350), because this instruction asks for one step per turn. The re-cost keeps 350, as the ticket asked. Crux's own instruction will set the real length.

## Re-cost arithmetic

The typical shape from the cost note is unchanged [S5]: 2,000-token system prompt, 60-token learner messages, 350-token replies, 1,500 retrieved tokens per chat call, then question-writing, grading and progress calls. Caching applies once the shared prefix reaches 4,096 tokens. Changes:

- Chat call *k* bills its thinking as output, using the mean measured thinking on turn *k* across the setup's 6 sittings.
- The next call's new input grows by that thinking x 1.000 (the signature), which then stays in the history and joins the cached prefix.
- **The three non-chat calls were not measured.** They are given the setup's mean thinking per chat reply, the cautious choice. Giving them none instead adds 1 to 3 sittings per $5.
- With thinking set to zero, the arithmetic reproduces the cost note's 152 / 76 / 38 cached and 93 / 42 / 21 uncached exactly.

Sittings per $5 under each variant:

| Setup and price | Cached, as measured | Cached, non-chat calls unthinking | Cached, signatures not sent back | Uncached | Uncached, signatures not sent back |
|---|---|---|---|---|---|
| 3.5 Flash-Lite `low` | 141 | 143 | 140 | 83 | 88 |
| 3.8 Flash `low`, to 2026-12-31 | 67 | 69 | 68 | 35 | 39 |
| 3.8 Flash `low`, from 2027-01-01 | 33 | 34 | 34 | 17 | 19 |
| 3.8 Flash `medium`, to 2026-12-31 | 55 | 58 | 59 | 29 | 36 |
| 3.8 Flash `medium`, from 2027-01-01 | 27 | 29 | 29 | 14 | 18 |

The "signatures not sent back" columns assume thinking stays the same without them, which was not measured, and Google warns that answer quality drops [S3]. With caching, dropping them moves the figure by 1 to 4 sittings at most, and on Flash-Lite by 1 the wrong way: the smaller history reaches the 4,096 minimum later, which offsets the saving.

## Not verified

- **Crux's own instruction** will be longer than the guide's and may draw more or less thinking. These figures are for the guide's instruction.
- **One subject, simulated learners.** All sittings were linear-equation algebra with a model playing the learner. Real learners and other subjects may draw different thinking.
- **Six sittings per setup.** The spread between sittings is wide (finding 5). The means are rough.
- **Why the cache never hit** was not investigated, and neither was the Interactions API's stateful mode [S7].
- **3.8 Flash's default level.** The thinking guide's table gives `medium` [S2]. Google's Gemini 3 page says "If thinking_level is not specified, Gemini 3 will default to high" [S3]. These runs set the level explicitly, so the figures stand. Which level the #684 AI Studio run used is not certain.
- **Flash-Lite's caching minimum** is still not listed on the caching page [S4]. Its prompts here never reached 4,096 anyway.
- **Teaching at 3.8 Flash `low`** is still untested. Transcripts exist but were not scored; this note is cost only.
- **Dropping signatures:** its effect on thinking and on teaching was not measured.
- **The checkpoint split** (a stronger model writing and grading the mastery check) is left out, as the ticket says.

## Sources (all read 2026-10-21)

- [S1] Gemini Developer API pricing, https://ai.google.dev/gemini-api/docs/pricing ("Last updated 2026-10-19 UTC"). Unchanged since #672: 3.5 Flash-Lite $0.30 in / $0.03 cached / $2.50 out; 3.8 Flash $0.75 / $0.075 / $3.75 "through December 31, 2026", then $1.50 / $0.15 / $7.50 "starting January 1, 2027"; both output prices "including thinking tokens".
- [S2] Gemini API thinking (generateContent), https://ai.google.dev/gemini-api/docs/generate-content/thinking ("Last updated 2026-10-14 UTC"): pricing note, `thoughts_token_count`, thinking-level table.
- [S3] Gemini API thought signatures, https://ai.google.dev/gemini-api/docs/generate-content/thought-signatures ("Last updated 2026-10-13 UTC"), and Gemini 3 guide, https://ai.google.dev/gemini-api/docs/generate-content/gemini-3 ("Last updated 2026-10-19 UTC"). The old `/docs/thought-signatures` URL now says "This page has moved".
- [S4] Gemini API context caching, https://ai.google.dev/gemini-api/docs/generate-content/caching ("Last updated 2026-10-13 UTC")
- [S5] "What a tutoring session costs on candidate AI models", `docs/research/llm-session-cost.md` (#672)
- [S6] "Task: check whether LearnLM's teaching holds on the cheaper Gemini models", https://github.com/calmxz/Crux/issues/684
- [S7] Gemini Interactions API overview, https://ai.google.dev/gemini-api/docs/interactions-overview ("Last updated 2026-10-15 UTC")
