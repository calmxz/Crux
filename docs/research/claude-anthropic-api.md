# Can Crux's AI layer run on Claude through Anthropic's API? Part 1, the docs

Research for issue #727 (child of #661), Part 1 only (items 1 to 9). Read from Anthropic's own docs, terms and policies on **2026-11-02**. Prices are USD per 1M tokens (MTok). Source IDs like [S1] point to the list at the end. No API call was made and nothing was spent. Part 2 (measuring) is not in these files. Items 1 to 9 are in two parts, listed under "The parts".

**Stop rule: did not fire.** The Philippines is a supported region [S1], and the terms allow a product that serves adult end users [S2][S3]. Nothing found rules Claude out.

**Two unknowns gate items 5, 6 and 8.** Check both in the Console before Part 2:

- **Is the owner's Console account an organization?** "The Admin API is unavailable for individual accounts" [S20]. Workload identity federation needs service accounts and an admin role [S18]. If the account is individual, items 5 and 6 need a switch to an organization first.
- **When was the account created?** Accounts created on or after 2026-08-31 get a 400 error on an edited history [S13]. Older accounts do not, unless they ask for it.

## Answer

| Item | Answer in one line | Fits the spec as decided? | What would have to change |
|---|---|---|---|
| 1. Promotional credit | Expires on the date shown when issued, else after one year; the card is charged only when credits are bought. | Yes | The map: AI spend comes from the credit, then bought credits. Check the expiry in Console > Billing. |
| 2. Spend controls, rate limits | Prepaid credit, auto-reload off, plus a monthly spend limit on a workspace. Start-tier limits far exceed 25 learners. | Yes | #675: put back "prepaid credit with auto top-up off"; set the backstop as a workspace spend limit. |
| 3. Availability, terms | Offered in the Philippines; adult tutoring is allowed, with an AI notice in the product. | Partly | #677: the region check must block every unsupported region, not only the EU and UK. Show the AI notice on screen. |
| 4. Data | Inputs and outputs deleted within 30 days; no training; flagged chats kept 2 years. DPA applies. Storage US, inference global or US. | Partly | #677 and #717: new retention and abuse-monitoring lines. The DPA names no processing location. |
| 5. Sign-in without a key | Yes: Cloud Run's Google identity signs in through workload identity federation. | Yes, if the account is an organization | #716: the backend signs in to Anthropic through federation; Agent Platform and its role are dropped. |
| 6. Daily bill comparison | Anthropic's cost API can replace Google's billing export. It needs an admin credential, kept apart from the app's. | Partly | #717: new source, data up to 24 hours late, and a full-admin credential on its own identity. |
| 7. Safety refusals | Everyday biology and health lessons are not affected, the docs say. A refusal returns an empty reply that Crux must handle. | Partly | #679 and #678: a refusal rule for study blocks and checks; no "write out your reasoning" fields. |
| 8. History edits | All three count as edits as Crux's prompt is ordered today. Each breaks the cache; on new accounts, sent-back thinking also gets a 400. | No | #679, #667 and #719: freeze the prompt start; send changes in the newest turn; restart the conversation on file removal. |
| 9. Prices and dates | Sonnet 5.5's cache read is USD 0.10, not 0.20. Batch is half price. About 30% more tokens than older Claude models. | Yes | #679 and #678: use the prices in item 9. |

## The parts

- Items 1 to 6 (credit, spend limits and rate limits, availability and terms, data, sign-in, the bill comparison): `claude-anthropic-api-account.md`.
- Items 7 to 9 (safety refusals, history edits, prices and dates): `claude-anthropic-api-model.md`.

## Inputs for the grilling session that reopens #679

| Ticket | What this file changes |
|---|---|
| #679 | Prices (item 9); refusal handling (item 7); no reasoning-trace fields; a frozen prompt start and append-only history (item 8) |
| #675 | Prepaid credit with auto-reload off, plus a workspace spend limit, as the backstop (items 1, 2) |
| #677 | Retention, training and flagged-data lines; the DPA; US storage, global or US inference; a wider region block; an on-screen AI notice (items 3, 4) |
| #716 | Federation from Cloud Run, `workspace:inference` scope; Agent Platform and its model-call role dropped (item 5) |
| #717 | The bill source becomes Anthropic's cost API with its own admin identity; the abuse-monitoring line (items 4, 6) |
| #678 | Batches at half price, 29-day result storage, no fallbacks; refusals counted as passes in safety tests (items 7, 9) |
| #667 | File removal restarts the conversation from a summary (item 8) |
| #719 | Store each reply's `content` array and the sent `system` and `tools` exactly; added page ranges kept or cleared server-side (item 8) |
| The map | AI spend from Anthropic's credit, then bought credits; the card only through bought credits (item 1) |

## Not verified

- **Account type and account age** (top of this file). Both are in the Console.
- **The spend order of a non-Max promotional credit** against bought credits. The credit terms do not say [S4].
- **Evaluation-tier rate limits.** Not published [S7].
- **The subprocessor list and its locations.** The Trust Center page needs a browser.
- **Which category covers chemistry,** and whether a worked solution for the learner triggers `reasoning_extraction`.
- **How to continue a conversation after a refused turn** with empty content.
- **Whether federation works on an individual Console account.** The pages state the admin role and service accounts, not the account type.
- **The effective date of the regions and usage policies.** Both pages show a version effective 2026-11-12, after today.

## Sources (all read 2026-11-02)

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
