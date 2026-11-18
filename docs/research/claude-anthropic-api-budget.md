# Claude through Anthropic's API: costs, the budget and the account (Part 2)

Part 2 of #727, measured on **2026-11-18**. Index: `claude-anthropic-api.md`. Prices are USD, from Part 1's item 9 [S21]. How the sittings and checks ran is in `claude-anthropic-api-teaching.md` and `claude-anthropic-api-check.md`.

## Answer

- **Teaching costs far less than the spec's Flash-Lite figure.** A 15-reply sitting on Haiku 5.5 at `low` costs about 0.006 with a 1-hour cache. The spec's sitting's worth is 0.045, but that figure also counts a check and a progress update, costed by arithmetic, so the two are not like for like.
- **Mastery checks are now most of the AI spend.** A 6-problem check costs 0.07 to 0.12, about 5 to 10 days of a learner's tutoring limit. So #675's conflict is confirmed: checks need a limit of their own.
- **The owner's account** reads as an organization, linked on 2026-10-17, with a USD 100 monthly credit. It is not enforced on the history-editing check today.

## A sitting's cost

15 learner replies of teaching, with no check and no progress update. The cost research's sitting adds both (#688). Tool calls make about 23 to 26 calls a sitting.

| | Haiku 5.5 `low` (6 sittings) | Sonnet 5.5 `low` (3 sittings) |
|---|---|---|
| Measured, 5-minute cache, replies seconds apart | 0.0057 (0.0046 to 0.0062) | 0.082 (0.079 to 0.088) |
| No caching at all | 0.0224 | 0.457 |
| 5-minute cache expired before every reply | 0.0195 | 0.351 |
| 1-hour cache, every reply within the hour | 0.0063 | 0.091 |
| Share of input tokens read from cache, measured | 96% | 97% |
| Output tokens a sitting, thinking included | about 5,900 | about 4,700 |

- **The scenarios come from the per-call usage by arithmetic:**
  - "No caching" prices every cache read and cache write as plain input. Caching cuts a sitting about 3.9 times on Haiku (0.0224 / 0.0057) and about 5.6 times on Sonnet (0.457 / 0.082).
  - "Expired" turns the first call of each reply from a cache read into a 5-minute cache write, at 1.25 times input [S21].
  - "1 hour" prices every cache write at 2 times input [S21] and keeps every read.
- **The budget figure is the 1-hour cache.** Real learners pause for more than 5 minutes, which the scripted sittings did not. The 1-hour cache costs about 10% more than the measured best case, while expiry every reply costs more than 3 times as much.
- **Not counted:** the simulated learner, about 0.002 a sitting, which Crux would not pay.

## The budget, re-costed

The spec's amounts are a learners' budget of USD 8 a month, a USD 2 daily ceiling, and tutoring limits of 2 sittings' worth a day, 4 a week and about 17 a month (`docs/spec/README.md`, `spending.md`).

| | Flash-Lite, the spec now | Haiku 5.5, 1-hour cache | Haiku 5.5, cache expired each reply |
|---|---|---|---|
| A sitting's worth | 0.045 | 0.0063 | 0.0195 |
| Sittings in the USD 8 month | about 178 | about 1,270 | about 410 |
| Sittings in the USD 2 day | about 44 | about 317 | about 103 |
| A learner's daily limit (2 sittings' worth) | 0.090 | 0.0126 | 0.039 |
| A learner's month at most (17 sittings' worth) | 0.77 | 0.107 | 0.33 |
| 25 learners at full use (17 sittings' worth each) | 19.1 | 2.68 | 8.29 |

- **The arithmetic, for Haiku with the 1-hour cache:** 8 / 0.0063 = 1,270. 2 / 0.0063 = 317. 17 x 0.0063 = 0.107, and 25 x 0.107 = 2.68.
- **And for Flash-Lite:** 8 / 0.045 = 178. 17 x 0.045 = 0.77, and 25 x 0.77 = 19.1.
- **Not like for like.** The Flash-Lite column is the spec's sitting: 15 turns plus the check and a progress update, costed by arithmetic (#688). The Haiku columns are measured teaching only, with checks costed below. A Flash-Lite sitting of teaching alone would cost less than 0.045.

### Mastery checks against the limit

- **A check's cost:** 0.012 to 0.020 a problem, so 2 problems cost 0.023 to 0.041, 6 cost 0.070 to 0.123, and 10 cost 0.116 to 0.205. Add 0.003 for each slip fix or walk-through.
- **Against a day's limit:** a 6-problem check is 0.070 / 0.0126 = 5.6 to 0.123 / 0.0126 = 9.8 days of a learner's daily limit. At #727's question stage the estimate was 0.11; the measurement agrees.
- **With Haiku 5.5 marking** (`claude-anthropic-api-check.md`), a 6-problem check is 0.053 to 0.101, so 0.053 / 0.0126 = 4.2 to 0.101 / 0.0126 = 8.0 days. The examples below use Sonnet marking.
- **Example monthly costs for 25 learners**, as examples for #675 and not a recommendation. A month is 4.33 weeks.

| Example check limit | Per learner a month | 25 learners a month |
|---|---|---|
| 1 check of 6 problems a week | 0.30 to 0.53 | 7.6 to 13.3 |
| 3 checks of 6 problems a week | 0.91 to 1.60 | 23 to 40 |

- **The arithmetic:** 4.33 x 0.070 = 0.30, and 4.33 x 0.123 = 0.53. Three a week: 13 x 0.070 = 0.91, and 13 x 0.123 = 1.60.
- **Against the old estimate:** #727's question estimated about USD 16 a month at typical use and 32 at full use, for 25 learners. Measured, teaching at full use is about 2.7, with the 1-hour cache, and checks make up the rest at whatever limit #675 sets.

### The credit

- **The owner's credit is USD 100 a month.** That it is the Max plan's API credit is an inference from the amount and "monthly": Max's credit is "$100 USD" a month [S5]. Such credits arrive "each billing cycle", expire at the cycle's end, and "Included credits are spent first" [S5].
- **Use for Crux:** the page says "you can use them to build and run your own applications and agents" [S5]. Linking also accepts program terms that the page does not show. They were not read.
- **When it runs out:** "If the organization has no credits left, API requests stop until your next monthly API credits arrive" [S5], unless bought credit remains.
- So the USD 8 learners' budget, the owner's USD 3 and about USD 5 of tests fit inside it many times over. The credit lasts only while the owner's plan does.
- **The run itself cost about USD 2:** 2.02 logged, across the smoke and history-edit tests, the sittings, the hard cases, the probe, both whole checks and the grading batch (0.37). A first teaching run crashed after about 12 calls that were not logged, a few cents at most.

## The owner's account

Checked by the owner in the Console and claude.ai on **2026-11-18**:

| Fact | Answer | What it decides |
|---|---|---|
| Account type | An organization, as the owner read the Console. Not yet confirmed on the Admin keys page | Items 5 and 6 can proceed: the Admin API and federation need an organization [S18][S20] |
| When the organization was linked | 2026-10-17, as claude.ai shows it | Not the creation date. The test below settles item 8 directly. |
| The credit | USD 100 a month, taken to be the Max plan's credit | See above |

## History edits on this account

Item 8 said accounts created on or after 2026-08-31 get a 400 on an edited history [S13]. Measured on each of Haiku 5.5, Sonnet 5.5 and Opus 5.5:

1. **Minting.** A first turn with thinking, at `high`. Each model returned one thinking block.
2. **Edits, no beta header.** The next turn resent the history with the first user message's text changed, or with the page block removed, as a file removal or a page range dropping out would do. **Every request returned 200.** The thinking was kept: the input count matched the unedited request.
3. **With the beta header only** (`thinking-binding-controls-2026-08-01`). The edited history returned 200 with an `input_transformations` entry of type `thinking_mismatch_allowed` and reason `prefix_binding_mismatch`. This is the API reporting that the block would fail on an enforced account.
4. **With `thinking.block_binding.prefix_mismatch_behavior` set to `"error"`.** The edited history returned 400: "The block is bound to a different conversation." The same setting on the unedited history returned 200, with an empty `input_transformations`.

**So this organization is not enforced by default today.** Edits cost only the cache, and the reasoning is kept.

- **The fixes in item 8 still hold.** Anthropic says to build append-only, so that the same code works on every account [S13].
- **A new organization is enforced by default.** That includes one opened later under a corporation, if it was created on or after 2026-08-31 [S13].
- **The beta header alone** reports every would-fail block, so a build test can catch an edit before it ships.

## What this changes

- **#675:** set a sitting's worth in dollars from the Haiku figure with the 1-hour cache, about 0.0063, once the model is chosen. Give mastery checks a limit of their own. Make prepaid credit, with auto-reload off, the backstop (Part 1, items 1 and 2).
- **#679:** use the 1-hour cache for the teaching prompt's start, or count the expiry case in the budget.
- **#667 and #719:** keep the history append-only (item 8), and add a build test that sends the beta header and fails on any `thinking_mismatch_allowed` entry.
- **The map:** the AI spend comes from a monthly USD 100 credit tied to the owner's plan, then from bought credit.
