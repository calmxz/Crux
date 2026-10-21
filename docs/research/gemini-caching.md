# Do Crux's sittings get Gemini cache hits, and through which API?

Research for issue #689 (child of #661). Measured on **2026-10-21** through the Gemini Developer API on a paid Tier 1 project, with `google-genai` 2.32.0. It follows "What thinking tokens add to a sitting's cost on Gemini" ([S1], #688), which saw no implicit cache hit in 270 calls. Prices are USD per 1M tokens, Standard tier. Sittings per $5 use the #688 arithmetic and thinking figures.

## Answer

1. **3.5 Flash-Lite caches, but only part of the prompt.**
   - Hits start once a prompt reaches about 4,000 tokens. Prompts of 3,977 tokens or less never wrote a cache entry; one of 4,065 did.
   - After that the cache grows in steps of about 2,000 tokens, and roughly the last 1,600 to 3,800 tokens of the shared prefix stay uncached. Between 36% and 77% of the prefix was served from cache: 46% on average at prefixes of 4,000 to 6,300 tokens, and 60% at 5,400 to 8,300. The cost arithmetic assumed 100%.
   - Hits survived 90-second gaps between turns.
   - Sittings that share a system instruction also share its cache: a second sitting got 2,034 cached tokens on its very first call.
2. **3.8 Flash got no cache hits at all.** There were 56 calls at or above its documented 4,096-token minimum [S2], with prompts up to 9,400 tokens, between 09:44 and 10:46, on both routes. No hits on 3.8 Flash from this project as of today.
3. **The route does not change caching.** The Interactions API's stateful mode cached the same share as `generateContent` (0.59 against 0.60), in the same 2,000-token steps.
4. **The route does change how much thinking comes back as input.**
   - On `generateContent`, each reply's thinking returns as input one-for-one, as #688 found.
   - On Interactions, the prompt grew by 58% of the previous thinking in one sitting and by 3% in the other.
   - In that second sitting, the prompt on several turns grew by less than the visible text alone. The server seems to trim or condense the history, and Google's docs do not describe this.
5. **Which sittings-per-$5 figure to budget on:**

| Setup | Cached as #688 modeled it | Cached as observed | No cache hits |
|---|---|---|---|
| 3.5 Flash-Lite `low` | 141 | **110 to 111** | 83 |
| 3.8 Flash `low`, to 2026-12-31 / from 2027-01-01 | 67 / 33 | (no hits seen) | **35 / 17** |
| 3.8 Flash `medium`, to 2026-12-31 / from 2027-01-01 | 55 / 27 | (no hits seen) | **29 / 14** |

   Budget Flash-Lite on about 110, with 83 as the floor if caching stops. Budget 3.8 Flash on the no-hit figures. If 3.8 Flash ever caches like Flash-Lite does, its figures would be 51 / 25 at `low` and 44 / 22 at `medium`.
6. **For the stack, the route is close to cost-neutral.** On Flash-Lite with caching, Interactions gives 110 to 112 against 110 to 111. Without hits, it is worth 1 to 7 sittings per $5, because it carries back less thinking: 3.8 Flash `medium` gets 32 to 36 instead of 29. Two things weigh against it, and neither was checked:
   - its history handling is not documented (finding 4);
   - it stores interactions on Google's servers by default [S3], which means learner conversations held server-side.

## How it was measured

- **Same sittings as #688.** The tutor ran the LearnLM guide's math-coach instruction at temperature 1.0, and 3.5 Flash-Lite at `minimal` played the learners from "Task: check whether LearnLM's teaching holds on the cheaper Gemini models". The tutor here was **3.5 Flash-Lite at `low`**. 3.8 Flash at `medium` was probed in 4-turn runs on both routes, three times.
- **Padded instruction.** The ticket proposed padding the instruction to about 2,000 tokens, the cost shape's size. But replies measured about 75 tokens, not the shape's 350, so a 2,000-token prompt would not reach 4,096 within 15 turns. The instruction was padded with fixed lesson text instead, to about 3,350 tokens (crossing 4,096 partway through the sitting) or about 5,400 (above it from the start). The size was chosen to test the cache, not to mimic Crux. Each run's instruction started with its own code, so no run could reuse another run's cache.
- **Runs.**

  | Run | Prompt start | Route | Sittings | Turns |
  |---|---|---|---|---|
  | Threshold | ~3,350 | `generateContent` | 2 | 15 |
  | Steady state | ~5,400 | `generateContent` | 2 | 15 |
  | Steady state | ~5,400 | Interactions | 2 | 15 |
  | Gap | ~5,400 | `generateContent` | 1 | 8, with 90-second pauses |

  The 3.8 Flash probes used about 5,400 and about 8,150 tokens (the latter twice, 40 minutes apart).
- **Read per call:** `prompt_token_count` and `cached_content_token_count` (`generateContent`), or `total_input_tokens` and `total_cached_tokens` (Interactions) [S4]. The shared prefix of a call is the previous call's whole prompt.
- **Fitted cache rule.** Cached tokens = whole 2,048-token blocks of (shared prefix - 1,700), once the prefix reaches about 4,000. Over the 91 Flash-Lite calls it is off by 272 tokens per call on average, and its total is within 1% of what was observed. A cruder rule, prefix minus 2,800, gives the same sittings per $5 (110 against 111). The #688 rule (whole prefix from 4,096) overstates cached tokens by 73%.
- **Spend:** about $0.36 ($0.17 in the runs, about $0.19 in the probes).
- **Scripts and data:** `%TEMP%\crux-688` (`measure_cache.py`, `probe_cache.py`, `cache_summary.py`, `recost_cache.py`, and the `c_thr`, `ss` and `c_gap` folders), local, not committed.

## Not verified

- **Why 3.8 Flash does not cache.** It may be specific to this project, to the model or to this week. Implicit caching has "no cost saving guarantee" [S2]. Explicit caching was left out, as the ticket said ("Research: LearnLM and Gemini through the Google GenAI SDK" priced it).
- **Flash-Lite's exact minimum.** It is not on the caching page [S2]. About 4,000 was observed.
- **What Interactions does to the history** (finding 4), and whether it changes teaching.
- **How long Interactions keeps stored conversations,** and whether `store=false` changes caching.
- **The cache rule outside the measured range.** Prefixes ran from 3,368 to 8,303 tokens; the typical sitting stays within about 4,000 to 10,000.
- **Crux's own prompt.** Its layout (where a per-learner summary sits, retrieval after the history) decides how much of the prefix is identical from call to call.

## Sources (all read 2026-10-21)

- [S1] "What thinking tokens add to a sitting's cost on Gemini", `docs/research/thinking-cost.md` (#688)
- [S2] Gemini API context caching, https://ai.google.dev/gemini-api/docs/generate-content/caching ("Last updated 2026-10-13 UTC"): 3.8 Flash minimum 4,096; Flash-Lite not listed; implicit caching "no cost saving guarantee".
- [S3] Gemini API, migrate to Interactions, multi-turn conversations: "The Interactions API stores interactions by default, enabling server-side state management for multi-turn conversations." Interactions quickstart: stateful mode is "Ideal for most chat and agentic workflows where you want the server to manage history and optimize caching." (via Google's Gemini docs index)
- [S4] `google-genai` 2.32.0, Interactions `Usage` type: `total_cached_tokens`, "Number of tokens in the cached part of the prompt (the cached content)."
- [S5] Gemini Interactions API overview, https://ai.google.dev/gemini-api/docs/interactions-overview ("Last updated 2026-10-15 UTC"): stateful mode "allows the system to more easily utilize implicit caching for the conversation history".
