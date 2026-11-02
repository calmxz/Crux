# Claude through Anthropic's API: refusals, history edits and prices (items 7 to 9)

Part of "Can Crux's AI layer run on Claude through Anthropic's API?" (issue #727, Part 1), read on **2026-11-02**. The summary table, the unknowns and the source list [S1] to [S34] are in `claude-anthropic-api.md`.

## 7. Safety refusals

- **Which models refuse:** Haiku 5.5, Sonnet 5.5 and Opus 5.5 all run safety classifiers [S24].
- A refusal is HTTP 200 with `stop_reason: "refusal"` and a `stop_details.category` [S24].
- **Categories:** Haiku 5.5: `cyber`, `bio`, `frontier_llm`, `general_harms` [S25]. Sonnet 5.5 adds `reasoning_extraction` [S26]. Opus 5.5: "including" `bio`, `cyber`, `reasoning_extraction` [S27].
- **Ordinary lessons:** for `bio`, "Everyday health and educational questions aren't affected", on all three models [S25][S26][S27].
- For `cyber`, "Benign cybersecurity work can also trigger this category" [S24]. Finding flaws in source code is allowed [S26].
- There is no chemistry category. The docs read do not say which category covers chemistry.
- **A risk for mastery checks:** `reasoning_extraction` fires on prompts that ask for the model's reasoning in its output [S24].
- Examples: a scratchpad section, or a `reasoning` field in JSON or tool input [S24]. "A short explanation" of an answer is still fine [S24].
- So check-marking prompts and tools must not ask for a reasoning trace. Whether a learner-facing worked solution triggers it is unverified.
- **What a refused call returns:** empty content, or partial output to discard if it came mid-stream [S24].
- **Fallback:** Sonnet 5.5's server-side fallback retries only `cyber` and `frontier_llm`, on Sonnet 5 [S26]. Opus 5.5 retries all but `reasoning_extraction` [S27].
- Haiku 5.5 has no server-side fallback. "Sending the same request to Claude Haiku 5.5 again usually returns another refusal" [S25].
- Batches do not accept the `fallbacks` parameter [S24].
- A fallback model usually cannot read the refusing model's thinking, so that turn runs without it [S13].
- **Billing:** a refusal before any output is billed for `bio`, `frontier_llm` and `reasoning_extraction`; not for others [S24].
- **For a study block:** the tutor's turn produces nothing. Crux must show its own message, log the category, and decide whether to retry on another model.
- **For a mastery check:** a refused call leaves a problem, answer or mark missing. Crux needs a rule, for example retry once on another model, then pause the check.
- **For #678's safety tests** (LD50, thermite and the others): a classifier refusal may replace the tutor's own decline. The test must count that as a pass.
- The docs read do not say how to continue a conversation after a refused turn with empty content.
- Fits the spec: partly. Crux needs refusal handling it does not have.

## 8. History edits

**The claim is verified.** On Haiku 5.5, Sonnet 5.5 and Opus 5.5, accounts created on or after 2026-08-31 get a 400 error on an edited history [S13].

That holds when a request leaves `prefix_mismatch_behavior` unset. Older accounts get no error; "failing blocks reach the model" [S13].

**Three different outcomes, often mixed up:**

| What happens | When | Source |
|---|---|---|
| **The API rejects it (400)** | A thinking block is sent back after an edit, on an account from 2026-08-31 on, or with `prefix_mismatch_behavior: "error"` | [S13] |
| **The API rejects it (400), any account** | A thinking block's own content or signature is changed | [S28] |
| **The thinking is dropped** | `"drop_block"` is set (beta); or the current model or account cannot read the block | [S13] |
| **The cache breaks** | Any change before the cached part of the prompt, thinking or not | [S29] |

- **What the check covers:** the top-level `system`, `tools` and every message before a thinking block [S13].
- Changing `effort`, `max_tokens` or `cache_control` markers is not an edit [S13]. A top-level effort change still restarts most of the cache [S13].
- **What counts as an edit:** editing, reordering or deleting an earlier message. Also changing `system` or `tools`, or shortening an earlier `tool_result` [S13].
- **Removing thinking blocks** from the start, the end, or all of them is allowed; "the model loses that reasoning" [S13]. Removing one from the middle is not.
- Within a tool-use turn, thinking blocks must be sent back [S28].
- **If Crux never sends thinking back,** "the check has nothing to test, and the model gets none of its earlier reasoning" [S13].
- **To find which column the account is in,** edit a Fable 5.1 conversation and send it without the beta header. A 400 means the newer column [S13].
- **Account binding:** Sonnet 5.5 and Haiku 5.5 thinking works only in the account that produced it [S13]. Moving accounts loses it.
- **Batches:** where the table shows a 400, a batch item drops the failing blocks instead [S13].

**Removing a file from a session (#667).**

- #679 puts the file outline and topic slice before the conversation. Removing a file changes that early text, so it is an edit [S13].
- Every later thinking block fails, and the cache restarts at the change [S13][S29].
- The doc's fix is to leave old content in place and announce changes in the newest turn [S13].
- That conflicts with #667: "Removing a file erases it at once." Crux cannot keep resending an erased file.
- **What it would need:** on removal, start a fresh conversation: one summary message plus the next turn ("simple compaction") [S13].
- Or strip all earlier thinking blocks, which is allowed [S13]. Either way the model loses its earlier reasoning, and the cache is written again.

**The topic slice's least-recently-used page range dropping out (#679).**

- If the added pages sit in the slice, before the conversation, adding a range is an edit as well as dropping one [S13].
- If the pages come back as a tool result, dropping a range shortens an earlier `tool_result`. That is also an edit [S13].
- **What it would need:** send each added range in the newest turn, and never take it out [S13].
- To remove old ranges, use server-side context editing (`clear_tool_uses_20250919`, beta). The check compares what Crux sent, so it is not an edit [S13].
- Or drop the 20-page cap's eviction and let ranges stay until the topic ends.

**Crux's own conversation format (#679).**

- #679 keeps "the model's thought blocks kept unchanged". For Claude, that means storing each reply's `content` array exactly as returned [S13].
- That includes empty `thinking` blocks and their signatures. "A serializer that skips empty blocks removes thinking" [S13].
- Persist the rendered `system` and `tools` exactly as sent, and replay them. Do not re-render from templates [S13].
- The prompt order puts "the learner's note and teaching state last". If that block is rewritten each turn, it is an edit [S13].
- **What it would need:** freeze `system` and `tools` for a conversation, and append state changes as new messages.
- A mid-conversation system message carries operator updates without editing the start [S13]. A turn-scoped one with `clear_at` suits per-turn state (beta) [S13].
- A topic change replaces the slice. Treat it like a file removal: start a fresh conversation with a summary.

## 9. Prices and dates

**Per-model prices** (standard API, prompts up to 100,000 tokens for Haiku) [S21][S30]:

| Model | Input | 5-minute cache write | 1-hour cache write | Cache read | Output |
|---|---|---|---|---|---|
| Haiku 5.5 | 0.10 | 0.125 | 0.20 | 0.01 | 0.50 |
| Haiku 5.5, prompt over 100,000 tokens | 0.50 | 0.625 | 1.00 | 0.05 | 2.50 |
| Sonnet 5.5 | 2.00 | 2.50 | 4.00 | **0.10** | 10.00 |
| Opus 5.5 | 4.00 | 5.00 | 8.00 | 0.20 | 20.00 |

- **The conflict is settled: Sonnet 5.5's cache read is USD 0.10** [S21][S30]. Opus 5.5 and Sonnet 5.5 read at 0.05x input, so 0.20 is Opus's figure [S21].
- `docs/research/llm-session-cost.md` is right. No Anthropic page read today gives 0.20 for Sonnet 5.5.
- The `claude-api` skill's model notes (cached 2026-10-06) say Sonnet 5.5 cache reads cost USD 0.20. That disagrees with the pricing pages.
- **Cache writes:** 5-minute writes cost 1.25x input; 1-hour writes cost 2x [S21]. A hit also refreshes the entry [S21].
- The smallest cacheable prompt is 512 tokens on all three models [S29].
- **Haiku 5.5 over 100,000 tokens:** 5x every rate [S21]. The prompt length "counts all of its input tokens, including cache reads and cache writes" [S21].
- **Batch discount:** 50% on input and output [S21]. Batch prices: Haiku 0.05 / 0.25, Sonnet 1 / 5, Opus 2 / 10 [S21].
- Caching multipliers "stack with ... the Batch API discount" [S21]. Batches can take over 5 minutes, so the 1-hour cache suits them [S14].
- **Tokenizer:** Claude 4.7 and later "produce approximately 30 percent more tokens for the same text than earlier models" [S21]. Haiku 5.5 uses it [S31].
- No Anthropic page compares its tokens with Gemini's.
- **Thinking adds input:** Haiku 5.5 keeps every earlier turn's thinking in context, billed as input [S31]. Clearing it is a context-editing option [S31].
- **Retirement dates**, not sooner than: Opus 5.5 2027-09-22, Sonnet 5.5 2027-09-28, Haiku 5.5 2027-10-07 [S32].
- Anthropic gives "at least 60 days' notice before model retirement" [S32].
- **Pinning:** "Every Claude model ID is a pinned snapshot, including the dateless IDs" [S33]. `claude-haiku-5-5` stays the same model for its lifetime [S34].
- Fits the spec: yes.
