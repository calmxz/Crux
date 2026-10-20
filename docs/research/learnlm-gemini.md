# LearnLM and Gemini through the Google GenAI SDK

Research for issue #682 (child of #661). All pages were read on **2026-10-20** and are official Google pages. Source IDs like [S1] point to the list at the end. Prices are USD per 1M tokens, Standard tier. Session arithmetic is reused unchanged from the #672 note ([S28]). Re-deriving it reproduces every Gemini figure in that note exactly.

Vertex AI has been renamed **Gemini Enterprise Agent Platform** ("formerly Vertex AI Platform" [S10]), and its docs now redirect to `docs.cloud.google.com/gemini-enterprise-agent-platform/...`. This note uses "Agent Platform (Vertex AI)".

## Answer

1. **What LearnLM is now.** It is no longer a separate model. "LearnLM is no longer a separate listing in AI Studio. Instead, LearnLM capabilities have been integrated into Gemini starting with the 2.5 model series" [S3].
   - It is training, not a prompt: Google added "our pedagogical data to post-training mixtures" and "fine-tuned it to follow pedagogical system instructions" [S2]. System instructions are how you switch the behaviour on.
   - The only models Google names are 2.5 Pro (evaluations [S1]) and an unspecified "Gemini 3.1" (the guide [S2]). No current model card mentions LearnLM, Flash-Lite cards included [S7]. **On Flash-Lite, LearnLM rests only on that series-level sentence.**
   - No `learnlm-*` model id is listed on the current models or deprecations pages [S5][S6]. The Cloud page's "Build with Gemini" buttons open `gemini-2.5-pro-preview-05-06`, which shut down on 2025-12-02 [S1][S5].
2. **The prompt guide** gives system-instruction examples and five learning principles. It covers setting objectives, the diagnostic, and teaching with misconception checks. It partly covers quiz writing. It says nothing about a server-held mastery threshold, a later retest, or demotion; those remain Crux's own logic (table below).
3. **The two platforms have the same age bar.** The Agent Platform (Vertex AI) terms contain the same under-18 clause as the Developer API terms: Service Specific Terms §20(d) [S9]. Moving to Agent Platform does not let Crux admit under-18 learners on Gemini.
   - Neither platform trains on paid traffic. People read prompts only when abuse detection flags them, on either platform.
   - The Developer API has a standing free tier, which trains on prompts and has human review. Agent Platform has only a 90-day trial for new Google Cloud users; otherwise it needs billing.
   - Prices: the global endpoint costs the same as the Developer API. Regional endpoints cost 10% more.
4. **SDK.** `google-genai` covers everything the loop needs on both platforms:
   - streaming;
   - structured output from a JSON schema;
   - explicit caching (v1beta on the Developer API; 4,096-token minimum on Agent Platform; $1.00 per 1M tokens per hour storage on Flash-Lite);
   - PDF input, inline up to 50 MB or through the Files API.

   **pptx** is not a document-vision type. File Search accepts it.
5. **Sessions per USD 5 (typical session, cached).** Which row applies depends on how far you take Google's series-level LearnLM claim:
   - Gemini 3.1 Flash-Lite: about **212**, but it may shut down from 2027-05-07.
   - Gemini 3.5 Flash-Lite: about **152**.
   - Gemini 3.1 Pro Preview: about **26**. This is the only tier near a model Google named. It has no free tier, and its thinking cannot be turned off, so even 26 is optimistic.

   One in-house check would settle which row applies (see "Not verified").

## 1. LearnLM's current status

| Claim | Quote | Source |
|---|---|---|
| No separate model | "LearnLM is no longer a separate listing in AI Studio. Instead, LearnLM capabilities have been integrated into Gemini starting with the 2.5 model series." (page last updated 2026-04-28) | [S3] |
| What "infused" means | "We're improving Gemini models for learning by enabling the addition of our pedagogical data to post-training mixtures alongside their rapidly expanding set of capabilities." | [S2] p10 |
| Activated by system instructions | "By infusing Gemini with LearnLM research, we've fine-tuned it to follow pedagogical system instructions. This means you can bring out behaviors like 'act as a supportive math tutor' without the need for additional fine-tuning" | [S2] p1 |
| Same, Cloud page | "With appropriate system instructions, Gemini can leverage LearnLM's research and grounding in learning science to elicit pedagogical behavior." | [S1] |
| Models Google names | "With LearnLM infused, Gemini 2.5 is the leading model for learning ... educators and experts preferred Gemini 2.5 Pro" (May 2025 evaluation) | [S1] |
| | "LearnLM ... is now infused directly into Gemini. With these capabilities and advancements, Gemini 3.1 is our most intelligent model" (no variant named) | [S2] p1 |
| | "We're infusing LearnLM directly into Gemini 2.5" (May 20, 2025) | [S4] |
| Model cards | The 3.5 Flash-Lite, 3.1 Flash-Lite, 3.8 Flash, 3.1 Pro, 4 Argon and 3 Pro cards contain no mention of LearnLM, pedagogy or learning science. 3.5 Flash-Lite "is based on Gemini 3.1 Flash-Lite", which "is based on Gemini 3 Pro" | [S7] |
| Stale link | The Cloud page's "Build with Gemini" buttons target `model=gemini-2.5-pro-preview-05-06`. The deprecations page lists that id as released May 6, 2025, shut down December 2, 2025, replacement `gemini-3.1-pro-preview` | [S1][S5] |

**What LearnLM changes about how the tutor teaches:** the architecture stays the same. The tutor's system instruction should state a pedagogical role and behaviours (next section), and the model is tuned to follow them. The flow's state lives in Crux's server either way: the objective list, mastery records, threshold and retest schedule.

## 2. The prompt guide's teaching instructions, mapped to the proposed mastery flow

The guide ([S2]) is titled "LearnLM Partner Prompt Guide" in its PDF metadata, is © 2025 under CC BY 4.0, and cites "LMArena, as of February 2026". It has three parts:

- five learning principles;
- a PARTS framework for content-creation prompts: Persona, Act, Recipient, Theme, Structure (p3);
- example system instructions.

### Principles (p7, "How it's incorporated into LearnLM capabilities in Gemini")

- **Inspire active learning.** "Encourages reasoning, supports knowledge application, and creates space for meaningful struggle and timely feedback."
- **Manage cognitive load.** "Structures responses clearly, breaks down complexity, and sequences information into logical parts."
- **Adapt to the learner.** "Responds to learner inputs, adjusts tone and difficulty, and supports differentiated pathways."
- **Stimulate curiosity.** "Asks open-ended questions and provides thoughtful follow-ups and explanations, along with real-world examples."
- **Deepen metacognition.** "Encourages learners to reflect on their thought processes and promotes planning skills."

### Example system instruction for a tutor (p6, verbatim)

> You are a supportive high school math coach. Start by asking what topic the student needs help with. Use one step per turn and adapt based on their responses. Encourage them to explain their thinking. If they're stuck, give a gentle nudge, not the answer. Use simple language, analogies, or visuals. Keep your tone warm and confidence-building. When they show understanding, summarize key takeaways and offer to continue or try a new challenge.

The same page asks the developer to check three things. Does the model "stay in the role you've given it"? Does it "follow your instructional logic, like 'first, wait' > 'then, guide' > 'then, summarize', 'then, ask'"? Does it "demonstrate learning-aligned behavior like scaffolding, questioning, and feedback"? Page 10 adds "Define the role and tone up front" and "Design prompts with clear objectives, explicit instructions, and sufficient context."

### Mapping to the flow proposed on #664

| Flow step | What the guide gives | Coverage |
|---|---|---|
| 1. Set learning objectives | Course-based tutor: "Review the documents, then surface high-level topics and negotiate a study plan for the conversation." Authoring assistant: "define the learning goal". p10: "Design prompts with clear objectives". | **Covered**, as a conversation with the learner. The guide has nothing on storing objectives as data. |
| 2. Short diagnostic | Adaptive quiz generator: "Before generating questions, ask for subject, level, and specific topic. Start simple, increase difficulty if correct, and ask for explanations." Math coach: "Start by asking what topic the student needs help with." Principle: adapt to the learner. | **Covered** as adaptive questioning. Nothing on mapping results to objectives. |
| 3. Teach, checking understanding and correcting misconceptions | Math discourse coach: "ask them to explain how they got their answer and why they chose that strategy ... help them identify patterns or errors in reasoning", with expected behaviour "Surfaces patterns or misconceptions" and "Validates reasoning or redirects". Math coach: "one step per turn", "If they're stuck, give a gentle nudge, not the answer". Image tutor: "Ask guiding questions so you don't give them the answer directly." Principles: active learning, cognitive load, metacognition. | **Covered.** This is the guide's core. |
| 4. Quiz each objective with new questions; server marks mastery at a threshold | Assessment creator: "create 20 questions that assess critical-thinking skills rather than mere recall. Include: source, question, answer, and rationale." Adaptive quiz: "Feedback per answer", "Summarize or continue after five questions". p8: "Call your prompt logic in production using structured inputs." | **Partial.** The guide covers writing questions and giving feedback. It says nothing about recording results, thresholds or mastery. These calls are structured-output calls, where pedagogical tuning matters less than in chat turns. |
| 5. Later retest; failing demotes and sends weak objectives back to teaching | Course-based tutor: "Track the content reviewed and encourage further study as needed." p8 Monitor step: "log user input and output". | **Not covered.** Spaced retest and demotion are app logic. |

## 3. Developer API vs Agent Platform (Vertex AI)

Both are reachable from the same `google-genai` SDK.

| | Gemini Developer API | Agent Platform (Vertex AI) |
|---|---|---|
| **Under-18 end users** | **Barred.** "You also will not use the Services as part of a website, application, or other service (collectively, 'API Clients') that is directed towards or is likely to be accessed by individuals under the age of 18." [S8] | **Barred.** §20(d) Age Restrictions: "Customer will not, and will not allow End Users to, use a Generative AI Service as part of a website, Customer Application, or other online service that is directed towards or is likely to be accessed by individuals under the age of 18." [S9]. "Gemini Enterprise Agent Platform API (formerly Vertex AI API)" is listed under "Generative AI Services" [S10]. §20(g) makes this a "Use Restriction"; §20(f): "Google may immediately suspend or terminate Customer's use of a Generative AI Service based on any suspected violation of ... subsection (d)" [S9] |
| Developer age | "You must be 18 years of age or older to use the APIs." [S8] | No developer-age clause in the Google Cloud terms [S11] |
| Training on prompts | Free tier: Google "uses the content you submit ... to provide, improve, and develop Google products and services and machine learning technologies". Paid: "Google doesn't use your prompts (including associated system instructions, cached content, and files ...) or responses to improve our products" [S8] | "Google will not use Customer Data to train or fine-tune any AI/ML models without Customer's prior permission or instruction." (§18) [S9] |
| Read by people | Free tier: "human reviewers may read, annotate, and process your API input and output ... Do not submit sensitive, confidential, or personal information to the Unpaid Services." Paid: "Google logs prompts and responses for a limited period of time, solely for detecting and preventing violations of the Prohibited Use Policy" [S8]. Flagged content: "authorized Google employees may assess the flagged content" [S16] | Only when flagged: "Google may log Customer prompts solely for the purpose of reviewing and determining whether a violation has occurred" (GCP Terms §4.3) [S11]. For online-terms customers, "Google may additionally conduct human review of prompts flagged by our abuse" monitoring [S15]. Implicit cache data is "deleted no later than 24 hours after it's written" and "never used to train or fine-tune models" [S14] |
| Free use | Standing free tier on 3.5 Flash-Lite, 3.1 Flash-Lite and 3.8 Flash. Its "Used to improve our products" row reads "Yes", and Flash-Lite context caching is "Not available" on it [S18]. 3.1 Pro Preview and 4 Argon have no free tier [S18] | Express mode: "New users to Google Cloud can sign up ... in a free tier to try Agent Platform for free for up to 90 days". "If you are an existing Google Cloud user or after enabling billing, the 90 day free tier is removed." [S17] |
| 3.5 Flash-Lite in / cached / out | 0.30 / 0.03 / 2.50 [S18] | Global 0.30 / 0.03 / 2.50; non-global 0.33 / 0.033 / 2.75 [S19] |
| 3.1 Flash-Lite in / cached / out | 0.25 / 0.025 / 1.50 [S18] | Global 0.25 / 0.025 / 1.50; non-global 0.275 / 0.0275 / 1.65 [S19] |
| 3.8 Flash in / out | 0.75 / 3.75 to 2026-12-31, then 1.50 / 7.50 [S18] | Same promo and later price, global [S19] |
| Explicit cache storage | Flash-Lite: $1.00 per 1M tokens per hour. 3.8 Flash: $0.50, then $1.00 from 2027-01-01 [S18] | Flash and Flash-Lite: $0.000001 per token-hour, which is $1.00 per 1M per hour [S19] |
| SDK client | `genai.Client(api_key=...)` | `genai.Client(enterprise=True, project=..., location='global')` [S27] |

**For the decision:** Agent Platform does not solve the under-18 problem and does not lower the price. What changes is the data terms: Google Cloud's no-training clause, and logging only when abuse is flagged. It also needs billing once any trial ends; there is no standing free tier. Google's own products do serve teens: the I/O post says Learn About is now available "for more learners (including teens)" [S4]. The developer terms for both APIs still forbid it.

Where I looked for an under-18 clause, or an exception to one:

- Gemini API Additional Terms [S8]: clause found.
- Google Cloud Service Specific Terms [S9]: clause found, §20(d). No education carve-out in that section.
- Google Cloud Platform Terms of Service [S11]: no age clause.
- Generative AI Prohibited Use Policy [S12]: no age clause; minors appear only in the child sexual abuse prohibition.
- Google Cloud AUP [S13]: same as [S12].

## 4. SDK capabilities the learning loop needs (`google-genai`, current forms)

- **Streaming:** `client.models.generate_content_stream(model=..., contents=...)` yields chunks, with `chunk.text` on each [S27].
- **Structured output:** `config=types.GenerateContentConfig(response_mime_type='application/json', response_json_schema=Model.model_json_schema())`, or a plain JSON-schema dict [S27]. The SDK warns: "don't duplicate it in your input prompt". 3.5 and 3.1 Flash-Lite list structured outputs as supported [S6].
- **System instruction:** `GenerateContentConfig(system_instruction=...)`. This is where the guide's pedagogical instructions go [S2][S27].
- **Explicit caching:** `client.caches.create(model=..., config=types.CreateCachedContentConfig(contents=..., system_instruction=..., ttl='3600s'))`, then `GenerateContentConfig(cached_content=cache.name)` [S27].
  - "Beta: Explicit context caching is currently in Beta. Endpoints and SDK methods are available under v1beta." Default TTL is 1 hour [S20].
  - Minimum size on Agent Platform: "Gemini 3 (with exceptions) and Gemini 4 models: 4,096 tokens", for implicit and explicit caching alike [S21]. The Developer API caching page lists implicit minimums only, and Flash-Lite is not on it [S20].
  - **Design consequence:** the 2,000-token system prompt cannot be cached explicitly by itself. A prefix of system prompt plus a whole lesson file clears the minimum.
  - Holding a 24,000-token prefix for one hour costs $0.024 in storage, about 73% of a typical 3.5 Flash-Lite session (see section 5).
- **Implicit caching:** "enabled by default for all Gemini 2.5 and newer models" with "no cost saving guarantee"; 4,096-token minimum on Gemini 3 Flash models [S20]. Agent Platform's minimum for 3.7 and 3.8 Flash implicit caching is 6,144 [S21].
- **PDF input:**
  - Inline: `types.Part.from_bytes(data=..., mime_type='application/pdf')`. Files API: `client.files.upload(...)`. Inline payloads go up to "100 MB per request/payload (50 MB for PDFs)". Files API uploads go up to "2 GB per file, up to 20GB per project" and last 48 hours [S24].
  - "Gemini supports PDF files up to 50MB or 1000 pages" [S22].
  - On Gemini 3 models, a PDF page costs 560 tokens at default resolution (280 at `low`) [S23]. Pages are counted under the IMAGE modality, and "You are not charged for tokens originating from the extracted native text in PDFs" [S22].
  - A 30-page PDF sent raw is therefore about 16,800 tokens on every call that includes it. That is close to the 22,000-token extracted-text figure in #672, so the #672 shape (extract, then retrieve passages per turn) still holds.
- **pptx:** "document vision **only meaningfully understands PDFs**. Other types will be extracted as pure text" [S22]. pptx is not on the documented supported-types lists for generate requests [S24]. **File Search** does list `application/vnd.openxmlformats-officedocument.presentationml.presentation` [S25]. It bills "embeddings at $0.15 / 1M tokens", and retrieved tokens are charged at the model's input rate [S18]. Options for pptx: File Search, or convert to PDF or text on the server.
- **Thinking:** 3.5 and 3.1 Flash-Lite default to `minimal`, which "does not guarantee that thinking is off" [S26]. 3.8 Flash defaults to `medium`, and `minimal` returns an error. "You cannot disable thinking for Gemini 3.1 Pro", whose default is `high` [S26]. Set the level with `GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level='minimal'))` [S26].

## 5. Sessions per USD 5 on Gemini only

The session shapes, call counts and caching rule are from #672 [S28]:

- Typical session: 18 calls, average prompt 6,922 tokens, 6,550 output tokens.
- Cached reads apply only once the shared prefix reaches 4,096 tokens.

Re-running that arithmetic reproduces #672's Gemini figures to the cent. Prices have not changed since then [S18].

| Model | Light /$5 | Typical cost | Typical /$5 | Heavy /$5 | Typical uncached /$5 | Typical, +500 thinking/call /$5 | Default thinking | LearnLM evidence |
|---|---|---|---|---|---|---|---|---|
| Gemini 3.1 Flash-Lite (earliest shutdown 2027-05-07 [S5]) | 535 | $0.0235 | **212** | 60 | 122 | 135 | `minimal` | series-level sentence only |
| Gemini 3.5 Flash-Lite (no shutdown announced [S5]) | 385 | $0.0328 | **152** | 44 | 93 | 90 | `minimal` | series-level sentence only |
| Gemini 3.8 Flash, promo to 2026-12-31 | 191 | $0.0657 | 76 | 21 | 42 | 50 | `medium` (understated) | series-level sentence only |
| Gemini 3.8 Flash from 2027-01-01 | 95 | $0.1313 | 38 | 10 | 21 | 25 | `medium` (understated) | series-level sentence only |
| Gemini 3.1 Pro Preview ($2.00 / cached $0.20 / $12.00 [S18]) | 66 | $0.1882 | **26** | 7 | 15 | 16 | `high`, cannot disable (understated) | nearest to the Pro models Google evaluated |

- **Agent Platform regional endpoint (+10%), typical session:** 193 on 3.1 Flash-Lite, 138 on 3.5 Flash-Lite, 69 on 3.8 Flash promo.
- **Whole 22,000-token file in the prefix instead of retrieval, typical session:**
  - when implicit caching hits: 169 sessions on 3.1 Flash-Lite, 125 on 3.5 Flash-Lite;
  - with no cache hits: 37 and 30;
  - with an explicit 1-hour cache: 92 and 77. This assumes one cache per session, stored for one hour, and that the conversation after the cached prefix still hits the implicit cache.
- **One heavy user** (2 heavy sessions a day for 30 days): $4.93 on 3.1 Flash-Lite, $6.81 on 3.5 Flash-Lite, $39.41 on 3.1 Pro Preview.
- **Free tier:** costs $0, but prompts are used for training and human review [S8]. #672 also found three more limits: quotas are per project, shared by every user; numbers appear only in AI Studio; it is barred for EEA, UK and Swiss users.

## Not verified

- **LearnLM on Flash-Lite.** No Google page or evaluation names a Flash-Lite model. Suggested check: run the guide's p6 math-coach system instruction on 3.5 Flash-Lite and on 3.1 Pro Preview in AI Studio with the same learner script, and compare against the p6 checklist (stays in role, one step per turn, nudges instead of answering).
- **Which "Gemini 3.1" the guide means.** It names no variant [S2].
- **Developer API explicit-cache minimum for Flash-Lite.** Not on the caching page [S20]. The 4,096 figure is from Agent Platform [S21].
- **PDF tokens per page.** The document-processing page says "Each document page is equivalent to 258 tokens" [S22]. The media-resolution page gives 560 at default for Gemini 3 [S23]. The section above uses 560.
- **pptx sent directly to `generate_content`.** Not documented and not tested. File Search store limits and storage pricing were not checked.
- **Express-mode eligibility.** An AI Studio API key is backed by a Cloud project. Whether that makes the user an "existing Google Cloud user", and so loses the 90-day free tier, is not stated [S17].
- **Education exception to §20(d).** None was found in the five documents listed in section 3. Separate education agreements were not searched.
- **Agent Platform regional rules for EEA, UK and CH users.** Not checked.
- **Free-tier rate limits.** Still visible only in AI Studio (see #672).

## Sources (all read 2026-10-20)

- [S1] Google Cloud, "LearnLM in Gemini", https://cloud.google.com/solutions/learnlm (no update date shown)
- [S2] Google, LearnLM prompt guide (PDF metadata title "LearnLM Partner Prompt Guide", © 2025, cites LMArena "as of February 2026"), https://services.google.com/fh/files/misc/learnlm_prompt_guide.pdf
- [S3] Gemini API, LearnLM, https://ai.google.dev/gemini-api/docs/learnlm ("Last updated 2026-04-28 UTC")
- [S4] Google blog, "I/O 2025: LearnLM in Gemini 2.5 and more AI updates to help people learn" (May 20, 2025), https://blog.google/products-and-platforms/products/education/google-gemini-learnlm-update/
- [S5] Gemini API deprecations, https://ai.google.dev/gemini-api/docs/deprecations ("Last updated 2026-10-20 UTC")
- [S6] Gemini API models, https://ai.google.dev/gemini-api/docs/models ("Last updated 2026-10-19 UTC"); model page gemini-3.5-flash-lite (via Google's Gemini docs index)
- [S7] Google DeepMind model cards: https://deepmind.google/models/model-cards/gemini-3-5-flash-lite/ (published 21 July 2026), .../gemini-3-1-flash-lite/ (3 March 2026), .../gemini-3-8-flash/ (2 September 2026), .../gemini-3-1-pro/ (19 February 2026), .../gemini-4-argon/ (13 October 2026), https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-3-Pro-Model-Card.pdf
- [S8] Gemini API Additional Terms of Service, https://ai.google.dev/gemini-api/terms ("Effective March 23, 2026")
- [S9] Google Cloud Service Specific Terms, https://cloud.google.com/terms/service-terms ("Last modified October 12, 2026"), §18 Training Restriction, §20 Generative AI Services
- [S10] Google Cloud Services Summary, https://cloud.google.com/terms/services ("Last modified October 12, 2026")
- [S11] Google Cloud Platform Terms of Service, https://cloud.google.com/terms ("Last modified October 12, 2026"), §3.3 Restrictions, §4.3 Generative AI Safety and Abuse
- [S12] Generative AI Prohibited Use Policy, https://policies.google.com/terms/generative-ai/use-policy ("Last Modified: December 17, 2024")
- [S13] Google Cloud Acceptable Use Policy, https://cloud.google.com/terms/aup ("Last modified October 12, 2026")
- [S14] Agent Platform, zero data retention (formerly Vertex AI data governance), https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/zero-data-retention ("Last updated 2026-10-15 UTC")
- [S15] Agent Platform, abuse monitoring, https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/abuse-monitoring ("Last updated 2026-10-19 UTC")
- [S16] Gemini API usage policies, abuse monitoring, https://ai.google.dev/gemini-api/docs/usage-policies (via Google's Gemini docs index)
- [S17] Agent Platform express mode overview, https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/start/express-mode/overview ("Last updated 2026-10-19 UTC")
- [S18] Gemini Developer API pricing, https://ai.google.dev/gemini-api/docs/pricing ("Last updated 2026-10-19 UTC")
- [S19] Agent Platform generative AI pricing, https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing (redirect target of the Vertex AI pricing URL)
- [S20] Gemini API context caching, https://ai.google.dev/gemini-api/docs/caching ("Last updated 2026-10-13 UTC")
- [S21] Agent Platform context caching overview, https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/context-cache/context-cache-overview ("Last updated 2026-10-19 UTC")
- [S22] Gemini API document processing, https://ai.google.dev/gemini-api/docs/document-processing (via Google's Gemini docs index)
- [S23] Gemini API media resolution, https://ai.google.dev/gemini-api/docs/media-resolution (via Google's Gemini docs index)
- [S24] Gemini API file input methods, https://ai.google.dev/gemini-api/docs/file-input-methods (via Google's Gemini docs index)
- [S25] Gemini API File Search, supported file types, https://ai.google.dev/gemini-api/docs/file-search (via Google's Gemini docs index)
- [S26] Gemini API thinking, https://ai.google.dev/gemini-api/docs/thinking (via Google's Gemini docs index)
- [S27] Google Gen AI Python SDK (`google-genai`) README, https://github.com/googleapis/python-genai (via Google's Gemini docs index; current SDK forms only)
- [S28] "What a tutoring session costs on candidate AI models", local branch `research/llm-session-cost`, `docs/research/llm-session-cost.md` (#672)
