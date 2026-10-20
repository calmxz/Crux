# What a tutoring session costs on candidate AI models

Research for issue #672 (child of #661). All prices are USD per 1M tokens, standard (interactive) tier, read from official provider pages on **2026-10-20**. Source IDs like [S1] point to the list at the end. Model quality is not assessed here; this is a cost and terms answer only.

## Answer

The cheapest current models that fit a chat tutor are **OpenAI gpt-6-luna** and **Anthropic Claude Haiku 5.5**. Both list $0.10 in / $0.50 out with 10% cache reads, and both come to about **$0.0077 per typical session, so roughly 650 typical sessions per USD 5**. Close behind: **Mistral Small 4** (~490), **DeepSeek deepseek-flash** (~550 off-peak, ~270 at peak), OpenAI gpt-5.6-luna (~300). Google's cheapest current models cost more per session because of their output price: **Gemini 3.1 Flash-Lite ~210, Gemini 3.5 Flash-Lite ~150**.

USD 5 a month buys about 20 typical sessions a day across **all** users combined, even on the cheapest models. Under open sign-up, a hard spend cap and per-user limits are what keep that budget safe (see "Budget threats").

**Terms finding that changes the shortlist:** the Gemini API terms (paid and free) require developers to be 18+ and forbid using the API in a service "directed towards or is likely to be accessed by individuals under the age of 18" [S3]. A student tutor shared openly on social media is likely to reach under-18s. OpenAI and Anthropic both allow serving minors if you add safeguards [S12][S19].

## Session shapes (assumptions)

Each learner turn is one model call. The conversation is resent every turn, so prompts grow. Retrieved passages from an uploaded file go into the current call only, after the cache breakpoint, and are **not** kept in history. A mastery check is two extra calls (write the questions, then grade the answers). One more call at the end updates the learner's progress record. Reasoning/thinking is assumed **off or at minimum effort** (see the sensitivity table: the default settings bill extra output).

| | Light | Typical | Heavy |
|---|---|---|---|
| Source material | topic only, no file | uploaded file, retrieval | uploaded file, retrieval |
| Learner turns | 6 | 15 | 40 |
| System prompt + tutor rules + learner summary (tokens) | 1,500 | 2,000 | 2,500 |
| Learner message (tokens) | 40 | 60 | 100 |
| Tutor reply (tokens) | 250 | 350 | 500 |
| Retrieved passages per turn (tokens) | 0 | 1,500 (3 x 500) | 2,500 (5 x 500) |
| Mastery check: questions out / learner answers in / grading out | 400 / 150 / 300 | 600 / 300 / 400 | 600 / 400 / 500 |
| Progress update call (out) | 300 | 300 | 300 |
| **Model calls per session** | 9 | 18 | 43 |
| **Average prompt tokens per call (incl. history)** | 2,912 | 6,922 | 17,570 |
| **Total output tokens per session** | 2,500 | 6,550 | 21,400 |

Instructions for the mastery-check calls add 300 tokens (questions) and 200 tokens (grading rubric). The progress call adds 200.

### Arithmetic

For call *k*: `input_k = system + history_k + new_k + retrieved_k`, where `history` holds every earlier learner message and tutor reply.

- **cached_k** = `system + history_k - reply_(k-1)`, meaning everything up to and including the previous learner message. This counts only if it meets the model's minimum cacheable length.
- **fresh_k** = `input_k - cached_k - retrieved_k`, meaning the previous reply plus the new message. Billed at the cache-write rate where one exists (Anthropic, OpenAI GPT-5.6+), otherwise at the input rate.
- **cost_k** = `cached_k x read + fresh_k x (write or input) + retrieved_k x input + output_k x output`. Session cost = sum over all calls.

Worked example, **Claude Haiku 5.5, typical shape** (read $0.01, write $0.125, input $0.10, output $0.50 [S13]):

- Call 1: 2,060 fresh x 0.125 + 1,500 retrieved x 0.10 + 350 out x 0.50 = (257.5 + 150 + 175) / 1M = **$0.00058**
- Call 2: 2,060 cached x 0.01 + 410 fresh x 0.125 + 1,500 x 0.10 + 350 x 0.50 = **$0.00040**
- Calls 3-18 rise slowly as the cached history grows. Call 15 is $0.00045. The session totals **$0.00771**, and 5 / 0.00771 = **648 sessions**.

Gemini differs in two ways: no cached reads until the shared prefix reaches 4,096 tokens (call 7 in the typical shape), and output is $2.50 instead of $0.50. That is why Gemini 3.5 Flash-Lite comes out about 4x more expensive per session.

## Results

### Cost per session with prompt caching (primary), and sessions per USD 5

| Model | Light | /$5 | Typical | /$5 | Heavy | /$5 |
|---|---|---|---|---|---|---|
| OpenAI gpt-6-luna | $0.00206 | 2,423 | $0.00771 | 648 | $0.03056 | 163 |
| Anthropic Claude Haiku 5.5 | $0.00206 | 2,423 | $0.00771 | 648 | $0.03056 | 163 |
| Mistral Ministral 3 8B (small model) | $0.00141 | 3,534 | $0.00726 | 688 | $0.03192 | 156 |
| DeepSeek deepseek-flash, off-peak | $0.00228 | 2,190 | $0.00910 | 549 | $0.03403 | 146 |
| Mistral Small 4 | $0.00254 | 1,968 | $0.01021 | 489 | $0.04155 | 120 |
| OpenAI gpt-5.6-luna | $0.00463 | 1,080 | $0.01674 | 298 | $0.06539 | 76 |
| DeepSeek deepseek-flash, peak | $0.00457 | 1,095 | $0.01821 | 274 | $0.06805 | 73 |
| Gemini 3.1 Flash-Lite (shuts down 2027-05-07) | $0.00934 | 535 | $0.02353 | 212 | $0.08211 | 60 |
| Mistral Large 3 | $0.00722 | 692 | $0.03075 | 162 | $0.12779 | 39 |
| Gemini 3.5 Flash-Lite | $0.01295 | 385 | $0.03282 | 152 | $0.11351 | 44 |
| OpenAI gpt-5.4-mini | $0.01645 | 303 | $0.06086 | 82 | $0.23983 | 20 |
| Gemini 3.8 Flash, promo price to 2026-12-31 | $0.02614 | 191 | $0.06567 | 76 | $0.23027 | 21 |
| Gemini 3.8 Flash, from 2027-01-01 | $0.05227 | 95 | $0.13133 | 38 | $0.46053 | 10 |
| Anthropic Claude Sonnet 5.5 (higher-tier reference) | $0.03912 | 127 | $0.14507 | 34 | $0.54843 | 9 |

Excluded on purpose: Gemini 2.5 Flash-Lite ($0.10/$0.40) is limited "to users who have actively used them in the past"; Google says new projects should use 3.5 Flash-Lite or 3.8 Flash [S6]. Older-generation nano tiers (gpt-5-nano $0.05/$0.40, gpt-5.4-nano $0.20/$1.25 [S7]) are cheaper on paper but not modeled. gpt-6-luna is OpenAI's current "most efficient model for focused, high-volume tasks" [S8]. Batch/Flex discounts (50%) don't fit live chat. They could cover non-interactive calls such as grading.

### Without caching (worst case where caching is best-effort)

Gemini implicit caching, DeepSeek disk caching and Mistral cached input are automatic or best-effort, with no hit guarantee [S4][S22]. This is their floor.

| Model | Light /$5 | Typical /$5 | Heavy /$5 |
|---|---|---|---|
| gpt-6-luna / Claude Haiku 5.5 | 1,291 | 317 | 57 |
| Ministral 3 8B | 1,161 | 254 | 42 |
| DeepSeek flash off-peak / Mistral Small 4 | 920 | 221 | 39 |
| gpt-5.6-luna | 606 | 152 | 28 |
| Gemini 3.1 Flash-Lite | 485 | 122 | 22 |
| DeepSeek flash peak | 460 | 110 | 19 |
| Gemini 3.5 Flash-Lite | 354 | 93 | 17 |
| Mistral Large 3 | 296 | 69 | 12 |

Caching multiplies typical sessions per $5 by 1.6x to 2.7x and heavy ones by 2.5x to 3.7x, because the resent history dominates long sessions.

### Sensitivity: thinking tokens (typical shape, cached, +500 thinking tokens per call)

Where a model thinks, those tokens bill as output. gpt-6-luna defaults to `reasoning.effort: medium` [S8], Haiku 5.5 uses adaptive thinking at default effort `medium` [S15], Gemini's output price is "including thinking tokens" [S1], and DeepSeek's thinking mode is the default [S20].

| Model | Sessions/$5 thinking off | with +500 thinking/call |
|---|---|---|
| gpt-6-luna / Claude Haiku 5.5 | 648 | 409 |
| Ministral 3 8B | 688 | 580 |
| DeepSeek flash off-peak | 549 | 344 |
| Mistral Small 4 | 489 | 320 |
| gpt-5.6-luna | 298 | 181 |
| DeepSeek flash peak | 274 | 172 |
| Gemini 3.1 Flash-Lite | 212 | 135 |
| Gemini 3.5 Flash-Lite | 152 | 90 |

500 thinking tokens per call costs about 30-41% of capacity on most models. Ministral 3 8B loses only 16%, because its output price equals its input price. Actual thinking length at default effort was not measured.

## Prices used

| Model | Input | Cached read | Cache write | Output | Source |
|---|---|---|---|---|---|
| Gemini 3.5 Flash-Lite | 0.30 | 0.03 | none (implicit) | 2.50 | [S1] |
| Gemini 3.1 Flash-Lite | 0.25 | 0.025 | none (implicit) | 1.50 | [S1] |
| Gemini 3.8 Flash | 0.75 to 2026-12-31, then 1.50 | 0.075, then 0.15 | none (implicit) | 3.75, then 7.50 | [S1] |
| gpt-6-luna | 0.10 | 0.01 | 0.125 | 0.50 | [S7][S8] |
| gpt-5.6-luna | 0.20 | 0.02 | 0.25 | 1.20 | [S7] |
| gpt-5.4-mini | 0.75 | 0.075 | none | 4.50 | [S7] |
| Claude Haiku 5.5 (prompts up to 100k tokens) | 0.10 | 0.01 | 0.125 (5-min) | 0.50 | [S13] |
| Claude Haiku 5.5 (prompts over 100k) | 0.50 | 0.05 | 0.625 | 2.50 | [S13] |
| Claude Sonnet 5.5 | 2.00 | 0.10 | 2.50 | 10.00 | [S13] |
| deepseek-flash, peak | 0.30 | 0.006 | none | 1.20 | [S20] |
| deepseek-flash, off-peak | 0.15 | 0.003 | none | 0.60 | [S20] |
| Mistral Small 4 | 0.15 | 0.015 | not stated | 0.60 | [S26] |
| Ministral 3 8B | 0.15 | 0.015 | not stated | 0.15 | [S26] |
| Mistral Large 3 | 0.50 | 0.05 | not stated | 1.50 | [S26] |

Pricing notes:

- **Gemini 3.8 Flash promo.** Paid prices double on 2027-01-01 [S1].
- **Gemini 3.1 Flash-Lite shutdown.** Scheduled for 2027-05-07 [S6].
- **DeepSeek peak hours.** 01:00-04:00 and 06:00-10:00 UTC, Monday to Friday. All other hours are off-peak at half price [S20].
- **Mistral Large 4.** On sale at $0.68/$2.09 (list $1.36/$4.18) [S26].
- **OpenAI long context.** Prompts over 272K tokens cost 2x input and 1.5x output [S7][S8].
- **Data-residency uplift.** OpenAI regional endpoints cost +10% [S7], and Anthropic's US-only inference costs 1.1x [S13].

## Prompt caching by provider

| Provider | Mechanism | Write cost | Read cost | Minimum prefix | Lifetime |
|---|---|---|---|---|---|
| Anthropic | Automatic (`cache_control` at top level) or explicit breakpoints, up to 4 [S14] | 1.25x input (5-min), 2x (1-hour) [S13] | 0.1x input (Haiku 5.5) [S13] | 512 tokens for Haiku 5.5 and Sonnet 5.5 [S14] | 5 min, refreshed on each hit; 1 h option [S13] |
| OpenAI GPT-5.6 and later (incl. gpt-6-luna) | Implicit or explicit breakpoints; content after the last breakpoint "is processed at the uncached input-token rate without a cache-write charge" [S9] | 1.25x input [S9] | 0.1x input [S9] | 1,024 visible tokens [S9] | At least 30 min after last write or reuse [S9] |
| OpenAI earlier (e.g. gpt-5.4-mini) | Implicit only | none [S9] | model-specific cached rate [S7] | varies [S9] | in-memory or 24h [S9] |
| Google Gemini | Implicit caching "enabled by default for all Gemini 2.5 and newer models" [S4] | none listed for implicit | listed "context caching price" [S1] | 4,096 for 3.8/3.6 Flash; Flash-Lite not listed [S4] | not stated |
| DeepSeek | Disk cache "enabled by default for all users"; "best-effort" [S22] | none | cache-hit price [S20] | not stated | not stated |
| Mistral | "cached input tokens reduce input cost by up to 90% for repeated prompts" [S27] | not stated | cached-input price [S26] | not stated | not stated |

**Design note.** To get these cache hits with per-turn retrieval, the retrieved passages must sit after the last cache breakpoint and stay out of the long-lived history. If they stay in history, the heavy shape's largest prompt reaches about 126,000 tokens. Claude Haiku 5.5 then bills 9 of the 40 turns at its over-100k price, 5x the base rate [S13]. The whole conversation also gets resent.

## Embeddings for an uploaded lesson file

The file is assumed to be a 30-page PDF at about 500 words a page: 15,000 words, roughly 20,000 tokens, or **22,000 tokens** with 10% chunk overlap. A 30-slide pptx is usually a fraction of that. Query embeddings are assumed at one 60-token query per learner turn, which is 900 tokens per typical session.

| Embedding model | Price /1M | One file | Files per $5 | Query embeds, typical session |
|---|---|---|---|---|
| OpenAI text-embedding-3-small | 0.02 [S7] | $0.00044 | 11,363 | $0.000018 |
| Voyage voyage-4-lite (first 200M tokens free per account) | 0.02 [S33] | $0.00044 | 11,363 | $0.000018 |
| Voyage voyage-4 (200M free) | 0.06 [S33] | $0.00132 | 3,787 | $0.000054 |
| Mistral mistral-embed | 0.10 [S28] | $0.00220 | 2,272 | $0.000090 |
| OpenAI text-embedding-3-large | 0.13 [S7] | $0.00286 | 1,748 | $0.000117 |
| Gemini Embedding 2 (free on free tier) | 0.20 text [S1] | $0.00440 | 1,136 | $0.000180 |

- **Anthropic.** "does not offer its own embedding model"; its docs point to Voyage AI as one option [S17].
- **DeepSeek.** Lists no embedding model [S20].
- **Gemini PDFs.** If a PDF is sent to Gemini directly rather than as extracted text, "Tokens for the DOCUMENT modality (for example, PDFs) are billed at the image token rate" [S1].

Query embeddings are negligible: at most 2.3% of a typical session on the cheapest chat models, using Gemini Embedding 2. Ingesting a file is a one-time cost per file. On the priciest embedder that is about half of one typical session on gpt-6-luna or Haiku 5.5. On the $0.02 embedders it is about 6% of one session.

**Alternative to retrieval.** Put the whole 22,000-token file in the cached prefix. On gpt-6-luna or Haiku 5.5 a typical session then costs $0.0120 instead of $0.0077, still about 420 sessions per $5. It skips the embedding pipeline, at roughly 1.5x the chat cost. The same pattern holds on the other models: whole-file runs 1.1x to 1.8x the retrieval cost.

## Free tiers and data-use terms

| Provider | Standing free API tier? | Rate limits | Prompts used for training / product improvement? |
|---|---|---|---|
| Google Gemini | **Yes.** Free input and output on 3.5 Flash-Lite, 3.1 Flash-Lite, 3.8 Flash, 3.6 Flash, Gemini Embedding 2 and Gemma 4; Gemini 4 Argon not on free tier [S1] | Per project, not per key; RPD resets at midnight Pacific [S2]. **Numbers are not published on the page.** "View your active rate limits in AI Studio" [S2] | **Yes on free tier.** See quote below |
| Mistral | **Yes.** "Free mode: API access is enabled by default with no credit card required. Usage and rate limits apply." [S29] | Organization-level RPS, tokens/minute, tokens/month; "Free mode (the default) has the lowest limits, intended for evaluation and prototyping" [S30]. Numbers only in the admin Limits page | **Possibly, opt-out available.** See below |
| OpenAI | **No free token allowance** on the pricing page [S7]. The "Free" row in the usage-tier table is a usage-limit tier ($100/month cap, "allowed geography"), not a credit grant [S10] | Per org/project, by tier [S10] | **No by default.** "data sent to the OpenAI API is not used to train or improve OpenAI models (unless you explicitly opt in to share data with us)" [S11]. Abuse-monitoring logs kept up to 30 days [S11] |
| Anthropic | **No.** "New users receive a small amount of free credits to test the API" [S13] | Tier-based; new orgs may start in an Evaluation tier [S16] | **No by default.** "By default, we will not use your inputs or outputs from our commercial products (e.g. ... Anthropic API ...) to train our models", except feedback you explicitly submit [S18] |
| DeepSeek | **No** free tier on the pricing page. Usage is deducted from "topped-up balance or granted balance" [S20] | Concurrency only: 2,500 for deepseek-flash, per account [S21] | **Not stated in the API terms** [S24]. The privacy policy says DeepSeek uses personal data "to train and improve our technology", stores it "in People's Republic of China", and that end users of developer-built apps are outside its scope [S25] |
| Voyage (embeddings) | 200M free tokens per account for the voyage-4 series [S33] | not checked | not checked |

### Gemini terms, quoted [S3] (effective March 23, 2026)

- Unpaid services: "Google uses the content you submit to the Services and any generated responses to provide, improve, and develop Google products and services and machine learning technologies". Also: "human reviewers may read, annotate, and process your API input and output ... Do not submit sensitive, confidential, or personal information to the Unpaid Services."
- Paid services: "Google doesn't use your prompts ... or responses to improve our products". Prompts are logged "for a limited period of time" for abuse detection.
- Region: "You may use only Paid Services when making API Clients available to users in the European Economic Area, Switzerland, or the United Kingdom."
- Age, which applies to paid and free: "You must be 18 years of age or older to use the APIs. You also will not use the Services as part of a website, application, or other service ... that is directed towards or is likely to be accessed by individuals under the age of 18."

### Mistral terms

The commercial terms say Mistral will not train on customer data except when "you (i) opted-in to training on a Mistral AI Product set to opt-out by default or (ii) have not opted-out of training on a Mistral AI Product set to opt-in by default" [S32]. Studio/API training can be turned off under Admin panel > Privacy > "Anonymous improvement data" [S31]. The fetched pages do not say which default applies to Free-mode API use. Assume it is on until you disable it.

### Serving minors, for comparison

- **OpenAI** says developers "should implement additional safeguards when using our API to serve minors (under 18 years old)". It also says not to process personal data of children under 13 "without first implementing zero data retention" [S12].
- **Anthropic** asks organizations "providing minors with the ability to directly interact with products that incorporate our API(s)" to implement safeguards and to disclose that users are talking to an AI [S19].

So serving minors is allowed with conditions at both. Under Gemini's terms it is not allowed.

**Net for v1.** The Gemini free tier can't hold up an open launch:

- quotas are per project, so every user draws from one shared pool;
- prompts on it go to training and human review;
- it is barred for EEA/UK/CH users;
- and the under-18 clause rules Gemini out for a student audience whether the tier is paid or free.

Mistral's free mode is described as "evaluation and prototyping" only.

## Budget threats under open sign-up

1. **Total volume.** $5 covers about 650 typical sessions a month on the cheapest models, about 20 a day across all users. On Gemini 3.5 Flash-Lite it is about 150 a month, 5 a day.
2. **One heavy user.** Two heavy sessions a day for 30 days (60 sessions, cached) costs:
   - $1.83 on gpt-6-luna or Haiku 5.5 (37% of budget), $2.49 on Mistral Small 4, $4.08 on DeepSeek flash at peak;
   - $4.93 on Gemini 3.1 Flash-Lite, $6.81 on Gemini 3.5 Flash-Lite, $13.82 on Gemini 3.8 Flash (promo) and $27.63 after 2027-01-01;
   - $32.91 on Claude Sonnet 5.5.

   **Three such users exhaust the budget even on the cheapest models.**
3. **Marathon sessions.** History is resent every turn, so cost grows with the square of session length. One 100-turn heavy-style session costs $0.09 cached and $0.39 uncached on gpt-6-luna or Haiku 5.5. On Gemini 3.5 Flash-Lite it costs $0.33 cached and $1.23 uncached. A turn cap or history summarization is needed.
4. **Defaults that bill extra.** Reasoning defaults to `medium` on gpt-6-luna [S8] and thinking mode is the default on DeepSeek [S20]; 500 thinking tokens per call cuts capacity by about 30-41% (see the sensitivity table). Haiku 5.5 bills prompts over 100k tokens at 5x [S13]. OpenAI bills prompts over 272K at 2x [S7].
5. **Price changes on a schedule.** Gemini 3.8 Flash doubles on 2027-01-01 [S1]. DeepSeek "reserves the right to adjust" prices [S20].
6. **Overage past a prepaid balance.** Gemini prepay is "subject to overages during the approximately 10 minute billing pipeline latency" [S5].

Hard caps that exist:

| Provider | Cap |
|---|---|
| OpenAI | Hard spend limit per org or project; requests return 429 at the limit [S10] |
| Anthropic | Your own spend limit below the tier cap; usage pauses at the cap [S16] |
| Gemini | Prepay: minimum $5 top-up, and "When your Prepay credit balance on the billing account hits $0, all API keys ... will stop working" [S5] |
| DeepSeek | Spends only from the topped-up or granted balance [S20] |

None of these is per user. Per-user daily session or token limits have to be built into Crux itself.

## Not verified

- **Gemini free-tier limits.** RPM/RPD numbers are not on the docs page; they show only in AI Studio for a signed-in project [S2].
- **Gemini Flash-Lite caching.** The minimum implicit-cache prefix for 3.5 and 3.1 Flash-Lite is not in the table [S4]; the model assumes 4,096. Whether implicit caching has a storage charge is also not stated; the model assumes none.
- **Mistral caching and training.** The caching mechanism and minimum are not documented on the pages read; the model applies the cached-input price to the shared prefix. The default training setting for Free-mode API use is not stated.
- **mistral-embed price.** The $0.10 comes from the model card [S28]. It is not in the main pricing table [S26].
- **DeepSeek training.** Whether DeepSeek trains on API inputs: the terms are silent [S24].
- **Token counts across providers.** Anthropic says Claude 4.7+ models (incl. Haiku 5.5) produce "approximately 30% more tokens for the same text" than its previous tokenizer [S13][S15]. There is no cross-provider conversion, so Claude's real cost per session may run up to about 30% above the figures here. Other providers' tokenizers also differ; DeepSeek gives "1 English character ~ 0.3 token" [S23].
- **Voyage.** Free-tier rate limits and data-use terms were not checked.

## Sources (all read 2026-10-20)

- [S1] Gemini Developer API pricing, https://ai.google.dev/gemini-api/docs/pricing (page "Last updated 2026-10-19 UTC")
- [S2] Gemini API rate limits, https://ai.google.dev/gemini-api/docs/rate-limits
- [S3] Gemini API Additional Terms of Service, https://ai.google.dev/gemini-api/terms ("Effective March 23, 2026")
- [S4] Gemini context caching, https://ai.google.dev/gemini-api/docs/caching (page "Last updated 2026-10-13 UTC")
- [S5] Gemini billing, https://ai.google.dev/gemini-api/docs/billing
- [S6] Gemini deprecations, https://ai.google.dev/gemini-api/docs/deprecations
- [S7] OpenAI API pricing, https://platform.openai.com/docs/pricing
- [S8] OpenAI GPT-6 Luna model page, https://developers.openai.com/api/docs/models/gpt-6-luna
- [S9] OpenAI prompt caching guide, https://developers.openai.com/api/docs/guides/prompt-caching
- [S10] OpenAI rate limits guide, https://developers.openai.com/api/docs/guides/rate-limits
- [S11] OpenAI "Your data" guide, https://developers.openai.com/api/docs/guides/your-data
- [S12] OpenAI under-18 API guidance, https://developers.openai.com/api/docs/guides/safety-checks/under-18-api-guidance
- [S13] Anthropic pricing, https://platform.claude.com/docs/en/about-claude/pricing
- [S14] Anthropic prompt caching, https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- [S15] Claude Haiku 5.5 overview, https://platform.claude.com/docs/en/models/haiku-5-5/overview
- [S16] Anthropic rate limits and spend limits, https://platform.claude.com/docs/en/api/rate-limits
- [S17] Anthropic embeddings guide, https://platform.claude.com/docs/en/build-with-claude/embeddings
- [S18] Anthropic Privacy Center, "Is my data used for model training?", https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training
- [S19] Anthropic, "Guidelines for Organizations Serving Minors", https://support.claude.com/en/articles/9307344-responsible-use-of-anthropic-s-models-guidelines-for-organizations-serving-minors
- [S20] DeepSeek Models & Pricing, https://api-docs.deepseek.com/quick_start/pricing
- [S21] DeepSeek Rate Limit & Isolation, https://api-docs.deepseek.com/quick_start/rate_limit
- [S22] DeepSeek context caching, https://api-docs.deepseek.com/guides/kv_cache
- [S23] DeepSeek token usage, https://api-docs.deepseek.com/quick_start/token_usage
- [S24] DeepSeek Open Platform Terms of Service, https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html ("Effective date: April 29, 2026")
- [S25] DeepSeek Privacy Policy, https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html
- [S26] Mistral API pricing, https://docs.mistral.ai/inference/pricing (redirect target of https://mistral.ai/pricing/api/)
- [S27] Mistral pricing page and FAQ, https://mistral.ai/pricing
- [S28] Mistral Embed model card, https://docs.mistral.ai/models/mistral-embed-23-12
- [S29] Mistral Studio, activate and generate an API key, https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key
- [S30] Mistral Help, "Why am I hitting API rate limits", https://help.mistral.ai/en/articles/698531-why-am-i-hitting-api-rate-limits-and-how-do-i-increase-them
- [S31] Mistral Help, "Can I opt out of my input or output data being used for training?", https://help.mistral.ai/en/articles/455207-can-i-opt-out-of-my-input-or-output-data-being-used-for-training
- [S32] Mistral Commercial Terms of Service, https://legal.mistral.ai/terms/commercial-terms-of-service
- [S33] Voyage AI pricing, https://docs.voyageai.com/docs/pricing
