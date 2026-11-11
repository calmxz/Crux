# Spending and hosting: provider spend caps and Cloud Monitoring

Part of [Spec facts that rested on search snippets](../snippet-fact-checks.md), checked on 2026-11-11 for #762.


Research for issue #762. Checked on **2026-11-11**. Each fact in section 4 of the snippet-only list, and the one fact outside the spec (#738), is checked against the page that owns it. Quotes are copied from the page.

Three notes on where the facts come from:

- OpenAI's and Anthropic's spend caps are not in `docs/spec/`. They appear in #675's input on #679: "The provider must offer prepaid credit with auto top-up off and a hard monthly spend cap (Gemini, OpenAI and Anthropic all do, checked 2026-10-26)." #679 then dropped the prepaid-credit rule, because Agent Platform has none. This note checks that sentence, one row per provider.
- The research note for #726 (`docs/research/open-hosting-checks.md` at `b97bf17`) already read the GCP spend caps page and the Observability pricing page. So this note does not recheck the cap claims that come from the spend caps page:
  - "not instant", and the overage billed to the card (`spending.md:120`);
  - "gross" use (`hosting.md:34`);
  - the cap being per service and per project (`ai-layer.md:13`);
  - "Google's month may reset later than Crux's" (`operations.md:27`);
  - Cloud Storage taking no cap (`hosting.md:35`);
  - Google pausing every Cloud Run service at the cap (`hosting.md:40`).

  It rechecks only "Agent Platform has no prepaid credit", which rests on a different page.
- Of the tickets #674 to #676, only #674 states facts 5 to 7. #716 and #717 carry them on. #735 is the platform batch that states facts 2 to 4.

| # | Fact | Verdict | Source |
|---|---|---|---|
| 1a | OpenAI: prepaid credit, auto top-up optional, hard monthly spend cap | confirmed | OpenAI "Spend limits" guide. OpenAI Help Center, prepaid API billing |
| 1b | Anthropic: prepaid credit, auto top-up optional, hard monthly spend cap | confirmed | Claude Platform Docs "Rate limits". Claude Help Center, paying for API usage |
| 1c | Google: Agent Platform has no prepaid credit | confirmed | Gemini API "Billing" |
| 2a | Cloud Monitoring charges for alerting from no sooner than 1 September 2027, USD 0.35 a month per log-based rule | confirmed | Google Cloud Observability pricing, and its pricing examples |
| 2b | A log-based rule sends at most 20 notifications a day, and at least 5 minutes apart for an open alert | confirmed | Cloud Monitoring "Quotas and limits" |
| 3 | A GCS V4 signed URL lasts 7 days at most | partly | Cloud Storage "Signed URLs". `gcloud storage sign-url` reference |
| 4 | Resend allows 40 MB per email | no claim (the page gives 40 MB) | Resend "Attachments" and "Send Email" API reference |
| 5 | Google sign-in is blocked in the LinkedIn and Facebook in-app browsers (`disallowed_useragent`) | partly | Google OAuth 2.0 "Web Server Applications" and "Policies" |
| 6 | An `intent://` link opens the system browser | unverified | Chrome "Android Intents with Chrome". Android "Build web apps in WebView" |
| 7a | Turnstile free plan | confirmed | Cloudflare Turnstile "Plans" |
| 7a2 | `accounts.md:32`: Turnstile "is usually invisible, and shows at most a "Verify you are human" checkbox" | partly | Cloudflare Turnstile "Widget modes" |
| 7b | Cloudflare's free rate-limiting rule | confirmed | Cloudflare WAF "Rate limiting rules" |
| 8a | #738: the four Chrome CVE numbers | confirmed | NVD and CVE.org records. Chrome Releases, 2026-10-27 |
| 8b | #738: Playwright 1.64.1, the latest stable release, still bundles Chromium 156.0.8078.4 | changed | Playwright `browsers.json` at v1.64.0, v1.64.1 and v1.65.0. GitHub releases |
| 8c | #738: Playwright adds `--no-sandbox` unless `chromiumSandbox: true` | confirmed | Playwright docs and source at v1.64.0 |

## 1. Spend caps at the providers

**Spec says:**

- `spending.md:118`: "Agent Platform has no prepaid credit. Google's spend cap is the backstop, set a little above Crux's own stop so Crux stops first ([#675], [#679])."
- `spending.md:120`: "The cap is not instant, and an overage is billed to the card ([#679])." This rests on the spend caps page, which is out of scope.
- `ai-layer.md:13`: each project "has its own spend-cap budget on the service "Gemini Enterprise Agent Platform (formerly Vertex AI)", not "Gemini API" ([#679])."
- `README.md:123` and `ai-layer.md:146`: research #727 checks Claude through Anthropic's API. If Crux moves to Claude, Anthropic's cap becomes the backstop.

The spec names no OpenAI or Anthropic cap. The claim lives in #675's input on #679, quoted above.

### 1a. OpenAI

**Source:**

- OpenAI API docs, "Spend limits", `https://platform.openai.com/docs/guides/spend-limits` (read as `.md`). No date shown.
- OpenAI Help Center, "Setting up and managing prepaid API billing", `https://help.openai.com/en/articles/8264644-how-can-i-set-up-prepaid-billing`. Shows "Updated: 17 hours ago".

**Page says:**

- Spend limits: "Use spend alerts to track monthly API costs. To stop traffic after tracked spend reaches a configured amount, enforce a hard spend limit for your organization or an individual project."
- Spend limits, project steps: "To make API responses fail after the project reaches the limit, turn on **Enforce a hard limit**."
- Spend limits: "Enforcement is not instantaneous, so recorded spend can slightly exceed the configured amount."
- Prepaid billing: "Prepaid billing lets you purchase credits before using the API. Your credit balance decreases as you use the API." and "New API accounts use prepaid billing."
- Prepaid billing: "Auto recharge adds credits when your balance falls below the threshold you set."
- Prepaid billing: "Do not rely on the prepaid balance as an instantaneous spending cutoff."

**Verdict: confirmed.** OpenAI has prepaid credit, opt-in auto recharge, and a hard monthly spend limit per organization or project. Neither stop is instant.

### 1b. Anthropic

**Source:**

- Claude Platform Docs, "Rate limits", `https://platform.claude.com/docs/en/api/rate-limits` (read as `.md`; `docs.claude.com` redirects there). No date shown.
- Claude Help Center, "How do I pay for my Claude API usage?", `https://support.claude.com/en/articles/8977456-how-do-i-pay-for-my-claude-api-usage`. Shows "Updated over a week ago".

**Page says:**

- Rate limits: "Each of the Start, Build, and Scale tiers carries a monthly spend cap, which is the maximum your organization can spend on the API each calendar month. You can view your organization’s monthly spend cap and set your own limit on the Billing page in the Claude Console."
- Rate limits: "When usage reaches a spend limit you set, requests return HTTP 400 with error type `invalid_request_error`."
- Rate limits: "Once you reach your tier’s spend cap, API usage pauses until 00:00 UTC on the first day of the next month, unless you request a higher limit sooner. While usage is paused, API requests return HTTP 429".
- Help Center: "Claude API and playground usage is billed through prepaid usage credits." and "If you run out of credits, you can no longer call the API or use the playground until you add more."
- Help Center: "Auto-reload purchases additional credits automatically when your balance falls below a threshold you set." It is set up with a button, and can be turned off.

**Verdict: confirmed.** Anthropic has prepaid credit, opt-in auto-reload, and a monthly spend limit the owner sets below the tier's cap.

**Also on the page:** an owner-set limit returns HTTP 400 `invalid_request_error`, not 429. If #727 moves Crux to Claude, the cap handling in `spending.md:121` must treat that 400 as "Google refuses calls" does today. The tier caps start at USD 500 a month (Start), far above Crux's budget, so the owner-set limit is the one that matters.

### 1c. Google: Agent Platform has no prepaid credit

**Source:** Gemini API docs, "Billing", `https://ai.google.dev/gemini-api/docs/billing` (read as `.md.txt`; the HTML renders with JavaScript). No date shown.

**Page says:**

- "Prepay credits apply only to Gemini API usage costs; you can't use them to pay for other Google Cloud services."
- Under "Can I use my Prepay credits for other Google Cloud services, like Gemini Enterprise Agent Platform?": "No, Prepay credits are strictly locked to Gemini API usage. Any other Google Cloud services you use (Compute, Storage, Gemini Enterprise Agent Platform) are billed using the standard Cloud charging cycle."

**Verdict: confirmed.** Prepay exists only for the Gemini API. Agent Platform bills through the normal Cloud charging cycle.

**Also on the page:** the Gemini API now has its own project spend caps, marked "Experimental: The feature is experimental and limited in scope. You are subject to overages for around a 10 minute latency period." It also has billing-account tier caps, "Tier 1 | $250". #679's rejected list says of the Developer API: "the Developer API's prepaid credit is the only hard money stop, but it keeps every prompt for 55 days." Its experimental project caps are a second stop, so "the only hard money stop" is no longer exact. The rejection rests on the 55-day retention, which this note did not check, so nothing changes.

## 2. Cloud Monitoring alerting

**Spec says:**

- `operations.md:161`: "**Whether alerting starts to cost:** Google may charge from no sooner than 1 September 2027. Research on [#726] reads it as about USD 0.35 a month per log-based rule, so about USD 0.70 a month for the two rules ([#717])."
- `operations.md:88`: "There are two alert rules: one for access requests, and one for everything else. Each rule can send at most 20 notifications a day, so a flood of requests cannot silence an urgent message. Anything past 20 still shows on the owner page and in the daily email ([#735])."
- `operations.md:75` to `operations.md:84`: a push comes "from a marked log line and an alert rule", for the budget, the ceiling, Google's cap, the full store, the owner's share, "each new access request", a misuse flag and a failed AI test round.
- `operations.md:67` and `operations.md:69`: uptime checks every 5 minutes, "About 78,000 checks a month … of the 1 million free".
- `hosting.md:36` lists alerting among hosting costs outside the AI budget.

The spec does not state the 5-minute interval.

### 2a. The charge from 2027

**Source:**

- Google Cloud Observability pricing, `https://cloud.google.com/stackdriver/pricing` (redirects to `https://cloud.google.com/products/observability/pricing`). No date shown.
- Google Cloud Observability pricing examples, `https://cloud.google.com/stackdriver/observability-pricing-examples`. No date shown.

**Page says:**

- Pricing: "Starting no sooner than September 1, 2027, Cloud Monitoring will begin charging for alerting. The pricing model is as follows: $0.35 per month for each metric reference in an alerting policy."
- Pricing: "Alerting policies with the following query types can have only a single condition: Log match, used in log-based alerts."
- Pricing: "Metric alerting policies that use Billing, Quota, or Uptime metrics are not charged. … Log-based alerting policies for Personalized Service Health logs are not charged."
- Pricing examples, "Example 7: 100 log-based alerting policies": "100 conditions (one condition per log-based alerting policy)", "100 metric references * $0.35 per month = $3.50 per month", "Points returned cost: $0 (Log-based alerting policies do not return points.)".

**Verdict: confirmed.** Two log-based rules cost about USD 0.70 a month from no sooner than 1 September 2027. Uptime alerts stay free.

**Also on the page:** the #726 note says "The pricing examples page gives no log-based example", and #726 lists "whether a log-based rule counts as a metric reference" as not verified. Today the page has Example 7, which settles it: each log-based rule is one metric reference. `operations.md:161` can drop "reads it as" and state the figure. The uptime free tier is "1 million executions per Google Cloud project", as the spec says.

### 2b. Notification limits per log-based rule

**Source:** Cloud Monitoring, "Cloud Monitoring quotas and limits", `https://cloud.google.com/monitoring/quotas` (redirects to `docs.cloud.google.com`). "Last updated 2026-11-06 UTC."

**Page says:** in the alerting limits table, for policy type "LBA" (log-based alerting):

- "Maximum number of new alerts per log-based alerting policy | 20 alerts per day"
- "Maximum number of notifications per log-based alerting policy | 20 notifications per day"
- "Maximum rate of new alerts per log-based alerting policy | 2 new alerts per minute"
- "Minimum interval between notifications for an open alert per log-based alerting policy | 5 minutes"
- Footnote 3: "Monitoring generates notifications for an open alert when the minimum time between notifications elapses and a log entry matches the alert labels. … All notifications that Monitoring generates count towards the alerting policy's limit of 20 notifications per day."
- Footnote 4: "If the query of your log-based alerting policy extracts labels, then each combination of extracted label values represents its own alert timeline. Therefore, you can receive multiple notifications within 5 minutes."

The log-based alerts page (`https://cloud.google.com/logging/docs/alerting/log-based-alerts`, "Last updated 2026-11-06 UTC") adds: "A log-based alerting policy specifies the minimum time between notifications." Its example uses `"period" : "300s"`.

**Verdict: confirmed.** The 20-a-day limit in `operations.md:88` matches. The 5-minute minimum is real, though the spec does not state it.

**Also on the page, and bearing on what the spec relies on:**

- The page does not say what happens to a second matching log line while an alert is open and the 5 minutes have not passed. Footnote 3 says only that a notification is generated when the interval "elapses and a log entry matches". On that wording, a second push inside 5 minutes may never be sent, unless another matching line arrives later. The "everything else" rule carries eight kinds of push, such as a budget run-out and a misuse flag. The access-request rule fires once for each request.
- Footnote 4 says extracted labels give each label value its own alert timeline. A push-kind label would keep different kinds apart. It would not keep two access requests apart, unless each request has its own label value. The 20-a-day limit still covers the whole rule.
- "2 new alerts per minute" also caps bursts on each rule.
- Suggestion: add a real-phone test to `quality-bar.md` near line 154: two pushes of different kinds, and two access requests, each pair inside 5 minutes, all reach the phone. The result decides whether the rules need labels. This touches #735's two-rule decision only in detail.
