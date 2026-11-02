# Claude through Anthropic's API: credit, limits, terms, data, sign-in and bills (items 1 to 6)

Part of "Can Crux's AI layer run on Claude through Anthropic's API?" (issue #727, Part 1), read on **2026-11-02**. The summary table, the unknowns and the source list [S1] to [S34] are in `claude-anthropic-api.md`.

## 1. The promotional credit

- **Expiry, any promotional credit:** it expires "at the time indicated when issued". With no time given, it lasts one year [S4].
- Credits are non-refundable and non-transferable. They also expire if the account is closed [S4].
- **If the USD 100 is the Max plan's monthly API credit:** it arrives each billing cycle and expires at its end [S5]. That is USD 100 a month, not once.
- The Console shows each credit's amount and expiry in the Promotional credits section of the Billing page [S5]. **The account's own expiry: check in Console > Billing.**
- **Spent before the card?** API use is prepaid. The card is charged only when the owner buys credits or auto-reload buys them [S6].
- For the Max plan credit: "Included credits are spent first, then any credits you've purchased" [S5]. For other promotional credits, the docs read do not state the order.
- **Auto-reload trap:** auto-reload watches only the bought balance. It can fire while promotional credit remains [S5]. Keep it off.
- **After the credit runs out:** with no bought credit and auto-reload off, requests stop with "Your credit balance is too low" [S5][S6].
- **Spend limits still apply:** usage paid with credits counts toward the monthly spend cap [S5].
- Fits the spec: yes. An empty prepaid balance is itself a hard stop.

## 2. Spend controls and rate limits

- **Hard monthly cap:** each tier has one: Start USD 500, Build USD 1,000, Scale USD 200,000 [S7]. At the cap, requests return 429 with `enforced_spend_limit_reached` until the next month [S7].
- **Own spend limit:** the owner can set a lower monthly limit on the Billing page. Past it, requests return 400 `invalid_request_error` [S7].
- **Workspace spend limit:** each workspace can take its own monthly limit and alerts. The Default Workspace cannot [S7][S8]. Crux needs its own workspace.
- Limits are monthly only, reset at 00:00 UTC on the 1st [S7][S9]. There is no provider-side daily limit, so Crux's counter keeps the daily ceiling.
- **Prepaid credit with auto-reload off:** available, and auto-reload can be turned off [S6]. This restores the backstop #675 first chose and #679 dropped.
- The Spend Limits API is for Claude Enterprise only, not Console organizations [S9]. Limits are set by hand in the Console.
- No doc read gives an API to read the credit balance left. The Billing page shows it [S6].
- **Rate limits, Start tier:** each 5.5 model gets 4,000 requests, 2,000,000 input tokens and 400,000 output tokens a minute [S7].
- Cached reads do not count toward the input-token limit on these models [S7].
- **New accounts may start lower,** in an "Evaluation tier" whose limits are not published. They rise with usage history [S7].
- Sharp jumps in traffic can also hit "acceleration limits" [S7].
- **Can 25 learners reach them?** Say all 25 send a message every 20 seconds: 75 requests a minute.
- At 5,000 uncached input tokens and 1,000 output tokens a call, that is 375,000 and 75,000 a minute. Both are under a fifth of Start tier.
- Batches have their own limits: Start tier 1,000 requests a minute, 200,000 queued [S7].
- Fits the spec: yes. The Evaluation tier's limits are unknown until the owner checks the Console's Rate limits page.

## 3. Availability and terms

- **Philippines:** listed in the Supported Regions Policy [S1]. The page read shows a version effective 2026-11-12; no earlier version was shown.
- The policy also bars "use by persons while physically located in an unsupported region" [S1]. That covers Crux's learners.
- Crux's region check blocks only the EU and UK (#677). Both are supported regions [S1]. Unsupported regions would also need blocking.
- **Commercial use:** the Commercial Terms allow using the API "to power products and services Customer makes available to its own customers and end users" [S2].
- Anthropic "may not train models on Customer Content from Services" [S2].
- **Adult tutoring:** the Usage Policy prohibits no industry outright [S3]. Its minors guidelines apply only to products serving minors [S3]; Crux is 18+.
- **AI notice:** a consumer-facing chatbot must say it is AI "at the beginning of each chat session or in the product interface" [S3].
- #677's terms say "Crux is an AI tutor". The notice must also appear on screen, not only in the terms.
- **High-risk education rule:** it covers grading "that determines admission, graduation, licensure, or certification" [S3]. A mastery check grants none of these, so it falls outside.
- The Usage Policy bars submitting "AI-assisted work without proper permission" [S3]. #677's terms already say not to use Crux where a course forbids outside help.
- The Usage Policy shown is also effective 2026-11-12 [S3].
- Fits the spec: partly. The region check and the on-screen notice need changes.

## 4. Data, for the Privacy Policy

- **How long prompts and replies are kept:** "we automatically delete inputs and outputs on our backend within 30 days of receipt or generation" [S10].
- Exceptions: features with their own storage, such as the Files API, and data kept "to enforce our Usage Policy" [S10].
- The API docs say conversation content "is not retained by default", except for Covered Models [S11]. This differs from the Privacy Center; budget on 30 days.
- **Covered Models** need at least 30 days' retention: Fable 5, Fable 5.1, Mythos 5, Mythos 5.1 [S12]. Haiku 5.5, Sonnet 5.5 and Opus 5.5 are not on the list.
- **Batch results** stay downloadable for 29 days after creation [S14]. Batches are not eligible for zero data retention [S11].
- **Training:** "By default, we will not use your inputs or outputs from our commercial products ... to train our models" [S15].
- The exception is feedback the customer chooses to send [S15]. Crux sends none.
- **Safety checks:** for a flagged chat, Anthropic keeps inputs and outputs "for up to 2 years". It keeps classification scores "for up to 7 years" [S10].
- This holds even under zero data retention [S11]. It is the abuse-monitoring line #717 asks for.
- **Processor agreement:** the Data Processing Addendum is "incorporated into these Terms by reference" [S2]. Anthropic is the processor; Crux is the controller [S16].
- The addendum promises breach notice within 48 hours [S16]. #677's own 72-hour duty to the Commission fits after it.
- The addendum names no processing location. Its subprocessor list is on Anthropic's Trust Center [S16], which did not load without a browser.
- **Where inference runs:** `inference_geo` takes `"global"` (the default, "any available geography") or `"us"` (US only) [S17].
- US-only inference costs 1.1x on every token type [S21]. It works on Claude 4.6 and later models, and on batches [S17].
- **Where data is stored:** workspace geo sets storage at rest. "Currently, `"us"` is the only available workspace geo" [S17].
- Fits the spec: partly. #677 wants an agreement that says where data is processed; Anthropic's says it only in the docs.

## 5. Signing in without a stored key

- **Yes, documented for Cloud Run.** Cloud Run can request a Google-signed identity token for its attached service account [S18].
- Anthropic validates the token through standard discovery, with "no extra Google Cloud configuration required" [S18].
- It must be a user-managed service account, not the Compute Engine default [S18].
- **Anthropic side:** a federation issuer (`https://accounts.google.com`), an Anthropic service account and a federation rule matching the Google account's `sub` and `email` [S18].
- Setting this up needs the admin, owner or primary owner role [S19].
- The SDK swaps the token for a short-lived Anthropic token and refreshes it before it expires [S19]. The default lifetime is 3,600 seconds; the Console wizard sets 600 [S19].
- **Scope for the app:** `workspace:inference` allows only the inference endpoints in one workspace: Messages, token counting, Models and the OpenAI-compatible chat endpoint [S22].
- Tests in GitHub can federate the same way. Anthropic's docs index lists a GitHub Actions guide (https://platform.claude.com/docs/en/manage-claude/wif-providers/github-actions), not read here.
- **Fallback:** if federation is not available, an API key goes in Secret Manager.
- Fits the spec: yes, if the account is an organization (see the top of this file).

## 6. The daily bill comparison

- **Yes, Anthropic's cost API can replace Google's billing export.** The Usage and Cost Analytics API reports cost in USD by day, model and token type [S20].
- It is in beta (`analytics-usage-cost-2026-08-24`) [S20].
- Each row's `amount` is "the cost after discounts and before any credits are applied" [S20]. That matches Crux's count at list price.
- **Freshness:** data "typically refreshes within 4 hours" and "can take up to 24 hours" [S20]. Values can change until about 7 days after the month ends [S20].
- The older Usage and Cost API typically shows data within 5 minutes and remains supported [S23].
- **Key needed:** an Admin API key (`sk-ant-admin01-...`) or an OAuth token with the `org:admin` scope. Workspace API keys do not work [S20][S23].
- **Keeping it apart from the app:** give the report job its own credential [S20]. Anthropic recommends a federation rule with `org:admin` over a stored admin key [S20].
- That rule must target its own service account with the admin role [S22]. The app's rule stays at `workspace:inference`.
- "Finer-grained scopes (by resource, or read versus write) are not available" [S22]. The report job's identity can do everything an admin can.
- Fits the spec: partly. A day-old comparison works, but the comparison's credential is a full admin, not a read-only role.
