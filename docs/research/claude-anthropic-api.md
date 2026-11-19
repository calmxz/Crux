# Can Crux's AI layer run on Claude through Anthropic's API?

Research for issue #727 (child of #661), in two parts:

- **Part 1, the docs (items 1 to 9).** Read from Anthropic's own docs, terms and policies on **2026-11-02**, with no API call.
- **Part 2, the measurements.** Run on **2026-11-18** through Anthropic's API with the owner's key, for about USD 2 of the owner's credit.

Prices are USD per 1M tokens (MTok) unless a figure says otherwise. Source IDs like [S1] point to the list at the end. The files are listed under "The parts".

**Stop rule: did not fire.** The Philippines is a supported region [S1], and the terms allow a product that serves adult end users [S2][S3]. Nothing found rules Claude out.

## Part 2 in brief

- **Teaching:** Haiku 5.5 at `low` teaches as #684 asked and follows Crux's rules. Its tool reports are the weak point: imperfect in 6 of 6 sittings, against Sonnet 5.5's 3 of 3 clean. A revised reporting prompt removed the missed and duplicate records, but left 4 wrong values in 43, with 2 of 6 sittings clean, so it did not pass. Graphs, diagrams and file mistakes work on both.
- **The mastery check:** written-out working first tripped the `reasoning_extraction` safeguard, in 9 of 16 model-answer calls and 7 of 7 independent checks. A wording change fixed it, with 0 refusals in 92 later model-answer and independent-check calls.
- **Check accuracy:** model answers were right in every repeat, and no wrong answer was marked right. Marking was too strict until the must-contain points were limited to what the problem asks. A follow-up run found that Haiku 5.5 gave Sonnet's mark on all 16 hard-case answers in 2 repeats, for about a fifth less per check. A second found that Haiku can also write the model answers, with the Opus check kept: it caught one wrong worked solution in 14.
- **Cost:** a 15-reply sitting of teaching costs about USD 0.0063 on Haiku with a 1-hour cache. The spec's 0.045 on Flash-Lite also counts a check and a progress update. A 6-problem check costs 0.07 to 0.12, about 5 to 10 days of a learner's tutoring limit, so checks need a limit of their own.
- **The account:** read by the owner as an organization, linked on 2026-10-17, with a USD 100 monthly credit. It is not enforced on the history-editing check today. A new organization would be.

## Answer (Part 1, with Part 2's updates)

| Item | Answer in one line | Fits the spec as decided? | What would have to change |
|---|---|---|---|
| 1. Promotional credit | Expires on the date shown when issued, else after one year; the card is charged only when credits are bought. | Yes | The map: AI spend comes from the credit, then bought credits. Check the expiry in Console > Billing. |
| 2. Spend controls, rate limits | Prepaid credit, auto-reload off, plus a monthly spend limit on a workspace. Start-tier limits far exceed 25 learners. | Yes | #675: put back "prepaid credit with auto top-up off"; set the backstop as a workspace spend limit. |
| 3. Availability, terms | Offered in the Philippines; adult tutoring is allowed, with an AI notice in the product. | Partly | #677: the region check must block every unsupported region, not only the EU and UK. Show the AI notice on screen. |
| 4. Data | Inputs and outputs deleted within 30 days; no training; flagged chats kept 2 years. DPA applies. Storage US, inference global or US. | Partly | #677 and #717: new retention and abuse-monitoring lines. The DPA names no processing location. |
| 5. Sign-in without a key | Yes: Cloud Run's Google identity signs in through workload identity federation. The owner read the account as an organization (Part 2). | Yes, if the account is an organization | #716: the backend signs in to Anthropic through federation; Agent Platform and its role are dropped. |
| 6. Daily bill comparison | Anthropic's cost API can replace Google's billing export. It needs an admin credential, kept apart from the app's. | Partly | #717: new source, data up to 24 hours late, and a full-admin credential on its own identity. |
| 7. Safety refusals | Everyday biology and health lessons are not affected, the docs say. Part 2: no `bio` or `cyber` refusal on biology, chemistry or SQL-injection checks, but check prompts that asked for written-out working drew `reasoning_extraction` refusals, which are billed and get no fallback. | Partly | #679 and #678: a refusal rule for study blocks and checks; model answers framed as the learner's worked solution; the independent check returns no working. |
| 8. History edits | All three count as edits as Crux's prompt is ordered today. Each breaks the cache. Part 2: the owner's organization is not enforced today, but a new one would get a 400. | No | #679, #667 and #719: freeze the prompt start; send changes in the newest turn; restart the conversation on file removal; a build test with the beta header. |
| 9. Prices and dates | Sonnet 5.5's cache read is USD 0.10, not 0.20. Batch is half price. About 30% more tokens than older Claude models. | Yes | #679 and #678: use the prices in item 9. |

## The parts

- Part 1, items 1 to 6 (credit, spend limits and rate limits, availability and terms, data, sign-in, the bill comparison): `claude-anthropic-api-account.md`.
- Part 1, items 7 to 9 (safety refusals, history edits, prices and dates): `claude-anthropic-api-model.md`.
- Part 2, teaching against #684, pictures, file mistakes and tool reports, with the revised reporting prompt: `claude-anthropic-api-teaching.md`.
- Part 2, the mastery check (refusals, accuracy, Haiku 5.5 as the marker and the writer, cost per call): `claude-anthropic-api-check.md`.
- Part 2, costs, the re-costed budget, the owner's account and the history-edit test: `claude-anthropic-api-budget.md`.
- Follow-up, what the monthly plan credit's terms allow (read 2026-11-18): `claude-anthropic-api-credit.md`.

## Inputs for the decision that reopens #679

| Ticket | What these files change |
|---|---|
| #679 | Prices (item 9); refusal handling (item 7); no reasoning-trace fields; a frozen prompt start and append-only history (item 8). Part 2: Haiku 5.5 at `low` can teach, with its tool-report reliability as an AI test; model answers framed as the learner's worked solution, and an independent check that returns only an answer and a verdict; the 1-hour cache for the prompt start; Haiku 5.5 as a measured option for marking and the end step |
| #675 | Prepaid credit with auto-reload off, plus a workspace spend limit, as the backstop (items 1, 2). Part 2: a sitting's worth of about USD 0.0063; a separate limit for mastery checks, which cost 0.07 to 0.12 for 6 problems |
| #669 | Part 2: must-contain points are the minimum the problem asks for, and a point counts as covered in any words |
| #677 | Retention, training and flagged-data lines; the DPA; US storage, global or US inference; a wider region block; an on-screen AI notice (items 3, 4) |
| #716 | Federation from Cloud Run, `workspace:inference` scope; Agent Platform and its model-call role dropped (item 5) |
| #717 | The bill source becomes Anthropic's cost API with its own admin identity; the abuse-monitoring line (items 4, 6) |
| #678 | Batches at half price, 29-day result storage, no fallbacks; refusals counted as passes in safety tests (items 7, 9). Part 2: grading on Opus 5.5 through the Batch API cost about USD 0.031 a transcript |
| #667 | File removal restarts the conversation from a summary (item 8) |
| #719 | Store each reply's `content` array and the sent `system` and `tools` exactly; added page ranges kept or cleared server-side (item 8) |
| The map | AI spend from Anthropic's credit, then bought credits; the card only through bought credits (item 1). Part 2: the owner's credit is USD 100 a month, tied to the owner's plan. The credit's terms add no limit on a service for other people; it refreshes on the plan's billing date and stops requests when spent (`claude-anthropic-api-credit.md`) |

## Not verified

- **Account type on the Admin keys page.** The owner read the Console as an organization; the Admin keys page would confirm it.
- **The spend order of a non-Max promotional credit** against bought credits. The credit terms do not say [S4]. The owner's credit is the monthly kind, which is spent first [S5].
- **Evaluation-tier rate limits.** Not published [S7]. They no longer matter for a linked organization, which starts at least at the Start tier [S5].
- **The subprocessor list and its locations.** The Trust Center page needs a browser.
- **Chemistry and security beyond ordinary lessons.** Part 2 tested propane combustion and SQL-injection defence only.
- **How to continue a conversation after a refused turn** with empty content. No tutor turn was refused in Part 2.
- **An explicit statement that the plan credit may fund a service for other people.** The program terms are the Credit Terms [S4], which add no limit on end users; the permission rests on the Commercial Terms (`claude-anthropic-api-credit.md`). No page says it outright.
- **Which plan grants the owner's credit.** USD 100 a month fits Max or a small Team plan [S5].
- **The effective date of the regions and usage policies.** Both pages showed a version effective 2026-11-12, after the 2026-11-02 reading.
- **Teaching beyond algebra,** and a bare right answer to a fresh problem, which no Part 2 sitting reached.

## Sources (Part 1 read 2026-11-02; [S24] reread 2026-11-18)

- [S1] Anthropic Supported Regions Policy, https://www.anthropic.com/supported-countries (effective 2026-11-12): Philippines listed; "Use by persons while physically located in an unsupported region" barred.
- [S2] Anthropic Commercial Terms of Service, https://www.anthropic.com/legal/commercial-terms (effective 2025-06-17): A.1 end users; B no training; C DPA incorporated.
- [S3] Anthropic Usage Policy, https://www.anthropic.com/legal/aup (effective 2026-11-12): no industry banned; high-risk education clause; AI disclosure; minors guidelines.
- [S4] Anthropic Supplemental Credits Terms, https://www.anthropic.com/legal/credit-terms (effective 2024-03-04).
- [S5] API credits for Max, Ultra, and Team plans, https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers
- [S6] Claude Help Center, "How do I pay for my Claude API usage?", https://support.claude.com/en/articles/8977456-how-do-i-pay-for-my-claude-api-usage
- [S7] Rate limits, https://platform.claude.com/docs/en/api/rate-limits
- [S8] Workspaces, https://platform.claude.com/docs/en/manage-claude/workspaces
- [S9] Spend Limits API, https://platform.claude.com/docs/en/manage-claude/spend-limits-api
- [S10] Privacy Center, "How long do you store my organization's data?", https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data
- [S11] API and data retention, https://platform.claude.com/docs/en/manage-claude/api-and-data-retention
- [S12] Claude Help Center, "Covered Models", https://support.claude.com/en/articles/15425695
- [S13] Preserved thinking, https://platform.claude.com/docs/en/build-with-claude/preserved-thinking
- [S14] Batch processing, https://platform.claude.com/docs/en/build-with-claude/batch-processing
- [S15] Privacy Center, "Is my data used for model training?", https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training
- [S16] Anthropic Data Processing Addendum, https://www.anthropic.com/legal/data-processing-addendum (effective 2025-02-24): B.1 roles; G.1 48 hours; Schedule 4 points to https://www.anthropic.com/subprocessors (Trust Center, not loaded).
- [S17] Data residency, https://platform.claude.com/docs/en/manage-claude/data-residency
- [S18] Use WIF with Google Cloud, https://platform.claude.com/docs/en/manage-claude/wif-providers/gcp
- [S19] Workload Identity Federation, https://platform.claude.com/docs/en/manage-claude/workload-identity-federation
- [S20] Usage and Cost Analytics API, https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api
- [S21] Pricing, https://platform.claude.com/docs/en/about-claude/pricing
- [S22] WIF reference, OAuth scopes, https://platform.claude.com/docs/en/manage-claude/wif-reference
- [S23] Usage and Cost API (legacy), https://platform.claude.com/docs/en/manage-claude/usage-cost-api
- [S24] Refusals and fallback, https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback
- [S25] Prompting Claude Haiku 5.5, Safeguard refusals, https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5
- [S26] Prompting Claude Sonnet 5.5, Safeguard refusals, https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5; and the Sonnet 5.5 migration guide, https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide
- [S27] Prompting Claude Opus 5.5, Safeguard refusals, https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5; and the Opus 5.5 migration guide, https://platform.claude.com/docs/en/models/opus-5-5/migration-guide
- [S28] Building with thinking, Preserving thinking blocks, https://platform.claude.com/docs/en/build-with-claude/thinking
- [S29] Prompt caching, https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- [S30] Claude pricing, https://www.anthropic.com/pricing (redirects to https://claude.com/pricing): Sonnet 5.5 cache read USD 0.10, Opus 5.5 USD 0.20.
- [S31] Claude Haiku 5.5 overview and migration guide, https://platform.claude.com/docs/en/models/haiku-5-5/overview and https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide
- [S32] Model deprecations, https://platform.claude.com/docs/en/about-claude/model-deprecations
- [S33] Models overview, https://platform.claude.com/docs/en/about-claude/models/overview
- [S34] Model IDs and versions, https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions
- [S35] to [S40], read 2026-11-18 for the plan credit's terms: listed with their quotes in `claude-anthropic-api-credit.md`.
