# What Cloudflare and Cloud Run offer for a per-network cap

Part of [Research: a site-wide request cap per network](../site-wide-request-cap.md) (#760). All pages were read on 2026-11-12. Numbers in square brackets point to the source list at the end.

## WAF rate limiting rules on the Free plan

A rate limiting rule matches requests with an expression, counts them per "characteristic", and acts once the count passes a limit within a period [1].

The Free column of the availability table [1]:

| Setting | Free | Pro, for comparison |
|---|---|---|
| Fields in the rule expression | Path, Verified Bot | Host, URI, Path, Full URI, Query, Verified Bot |
| Counting characteristics | IP | IP |
| Cache exclusion | No | No |
| Counting periods | 10 s | All supported values up to 1 min |
| Mitigation timeout periods | 10 s | All supported values up to 1 h |
| Number of rules | 1 | 2 |

What this means for Crux:

- **One rule, matched on path only.** The rule can match `starts_with(http.request.uri.path, "/api/")`. The `starts with` operator and `starts_with()` function carry no plan note. Only "Access to the `matches` operator requires a Cloudflare Business or Enterprise plan" [2].
- **Counted by network address and data centre.** "Every rate limiting rule includes the Cloudflare data center ID ( `cf.colo.id`) as a mandatory characteristic." "Counters are not shared across data centers, with the exception of data centers associated with the same geographical location." [3]
- **Every matching request counts, cached or not.** On plans without the setting, "Cloudflare will also apply rate limiting to cached assets (the parameter is enabled by default)" [4]. A rule on `/` would count every file in a page load. A rule on `/api/` counts only the calls that go on to Cloud Run.
- **Not exact.** "There may be a delay of up to a few seconds between detecting a request and updating rate counters." [1] Rules "operate in **fail-open mode** (allowing requests through rather than blocking them) during infrastructure overload", and "There is no customer-visible signal for fail-open events." [5]

**Actions.** The API values are "`block`, `js_challenge` (Non-Interactive Challenge), `managed_challenge` (Managed Challenge), `challenge` (Interactive Challenge), or `log`" [4]. With a challenge, "Customers on Free, Pro, and Business plans cannot select a duration ... their rate limiting rule will always perform request throttling for these actions." [4] With *Block*, the action holds for the 10-second timeout: "By default, Cloudflare will apply the rule action for the configured duration (or mitigation timeout), regardless of the request rate during this period." [1]

**What the Free rule can cap (derived).** With a 10-second period and a 10-second block, a network that keeps under N requests per 10 seconds is never blocked. It can make 360 × N requests an hour and 8,640 × N a day. At N = 30, that is 10,800 an hour and 259,200 a day. The Free rule is a burst guard, not an hourly or daily cap. The decision on "how people sign up from a shared link" (#674) reached the same reading: the free rule "counts only by network address over 10 seconds ... so it can add only a burst guard".

## What a blocked visitor sees

- **Status code.** Block returns 429 by default. Changing the code needs a custom response: "You must enter a value between `400` and `499`. The default value is `429` (`Too many requests`)." [4]
- **No custom response on Free.** In the rule editor, under "Configure a custom response for blocked requests": "This feature is only available on Pro plans and above." [6]
- **No custom error pages on Free.** Custom Errors has "Availability | No" in the Free column, with 0 rules and 0 assets [7].
- **The page Cloudflare shows** is error 1015. Its documentation says: "The website you are trying to visit has received too many requests and has temporarily blocked you from accessing it." It advises the visitor: "Wait for a period of time, then try accessing the website again later." [8]

So on Free, the body of a blocked response is Cloudflare's, not Crux's. If the rule matches only `/api/`, page loads are never blocked. The visitor sees whatever the app shows when an `/api` call returns 429, so the app can turn the status into Crux's own words. The app can't read a "wait N seconds" value from Crux's body, because the body is Cloudflare's. The block always lasts 10 seconds on Free, so the app can use that fixed value.

## How a rule fits in front of the Worker

- **Rules belong to a zone.** The rule editor is "the **Security rules** page" of a zone, and the guides are titled "for a zone" [6][1]. Crux's own domain is a zone. Its rules cover the site from the trial on, since `hosting.md` turns the `workers.dev` address off from then.
- **`workers.dev` is Cloudflare's zone, not the owner's.** "All requests to a `workers.dev` hostname are evaluated by [Browser Integrity Check] ... on the Cloudflare-managed `workers.dev` zone." "You cannot turn off this check for a `workers.dev` hostname." [9] The page's remedy for rules is to "Serve your Worker on a Custom Domain or route in a zone you own" [9]. A staging Worker left on `workers.dev` gets no rate limiting rule.
- **A Custom Domain Worker is the origin.** "Custom Domains are routes to a domain or subdomain ... within a Cloudflare zone where the Worker is the origin." [10]
- **Security rules run first.** "Cloudflare security features powered by the Ruleset Engine run in a fixed sequence of phases." `http_ratelimit` is one of them [11]. The Workers metrics page says of its request total: "Requests blocked by WAF or other security features will not count." [12] So a request the rule blocks is not in the Worker's request total and never reaches Cloud Run. The limits page [16] doesn't say whether the 100,000-a-day count is kept the same way.
- **Static files skip the Worker.** "Cloudflare will first attempt to serve static assets if one matches the incoming request." "If an appropriate static asset if not found, Cloudflare will invoke your Worker script." [13] "Requests to static assets are free and unlimited." [14]
- **Unknown paths depend on the Worker's configuration.** In single-page-application mode, Cloudflare serves `/index.html` "for navigation requests (those with `Sec-Fetch-Mode: navigate` headers) which don't match any other asset" [24]. Its routing diagram sends a request that is not a navigation to the Worker script [24]. A bot that omits that header can therefore run the Worker on any unknown path. With `run_worker_first` set to a list of patterns, such as `/api/*`, "This approach disables the automatic `Sec-Fetch-Mode: navigate` detection" [24]. Then only listed paths run the Worker, and other unknown paths get the app's files. The spec does not fix this setting yet.

## The Worker's own options

### The Rate Limiting binding

The Worker calls `limit({ key })` and decides the response itself [15].

- **Windows:** "The duration of the rate limit window, in seconds. Must be either `10` or `60`." [15]
- **Limit:** "The request threshold for calls to `limit()` within the given `period`, per Cloudflare location. Requests can exceed this threshold" [15].
- **Approximate and local:** "Rate limits are approximate and apply separately in each Cloudflare location." [15] It "is backed by the same infrastructure that serves rate limiting rules" [15].
- **Several limits:** "You can define and configure multiple rate limiting configurations per Worker" [15].
- **Key advice:** "It is not recommended to use IP addresses or locations (regions or countries), since these can be shared by many users in many valid cases." [15] Crux has no user ID before an `/api` call reaches Cloud Run, so a network address is the only key the Worker has.
- **Response:** the Worker returns its own response, for example `new Response(..., { status: 429 })` [15]. Crux can send JSON in its own error shape, with the seconds to wait.
- **Strict limits:** "If you need one strict limit across all locations, implement a rate limiter with Durable Objects." [15]
- **Plan and price:** unstated. The binding page, the Workers pricing page [14] and the Workers limits page [16] don't mention the binding's plan or price.

Each checked request has already run the Worker, so it counts toward the Worker's daily allowance. It does not reach Cloud Run.

### Durable Objects

A Durable Object can hold a counter for any window, such as an hour or a day. "Durable Objects are available both on Workers Free and Workers Paid plans." On Free, "Only Durable Objects with SQLite storage backend are available." [14] The Free plan allows Durable Object "Requests | 100,000 / day" and SQLite "Rows written | 100,000 / day" [14].

### The Worker's daily allowance

"Accounts on the Workers Free plan have a daily request limit of 100,000 requests, resetting at midnight UTC. When a Worker exceeds this limit, Cloudflare returns **Error 1027**." [16] A route can fail open ("Bypasses the Worker") or fail closed ("Returns a Cloudflare `1027` error page") [16]. For paths listed in `run_worker_first`, "If you exceed your free tier request limits, these requests will receive a 429 (Too Many Requests) response instead of falling back to static asset serving." [17]

This allowance is shared by every visitor. One network that spends it stops the API for everyone until midnight UTC. Averaged over a day, 100,000 requests is about 1.2 a second (derived).

### Other free Cloudflare tools

- **DDoS protection** is "Available on all plans", and "Cloudflare automatically detects and mitigates distributed denial-of-service (DDoS) attacks" [18]. It acts on floods, not on a steady trickle from one network.
- **Bot Fight Mode** is free, but "Cannot be customized, adjusted, or reconfigured via WAF custom rules", and "they may challenge API or mobile app traffic" [19]. "You cannot bypass or skip Bot Fight Mode using WAF custom rules or Page Rules." [19] It could challenge Crux's `/api` calls and the outside check, with no way to exempt them.
- **WAF custom rules** (5 on Free [20]) can block by path or other fields, but they don't count requests.

## Cloud Run's side

- **What a refused call still costs.** Cloud Run charges "for the resources you use, rounded up to the nearest 100 millisecond", and Tier 1 requests cost "$0.40" per 1,000,000 [21]. A call that Crux's code refuses, such as a wrong trial link past the limit, still costs a request and instance time.
- **An illustration (derived).** Suppose one network uses the Worker's whole allowance, 100,000 calls a day, one at a time. At up to 100 ms each, that is up to 10,000 instance-seconds a day, or 300,000 a month. `hosting.md` puts the free credit at about 128,000 busy CPU-seconds in Singapore. So the 100,000-a-day ceiling alone can spend the credit and trip the USD 6 cap.
- **Maximum instances** bounds cost overall: "You can use this setting as a way to control your costs" [22]. It caps all callers together, not one network.
- **Cloud Armor** rate limiting rules can "Throttle requests per client based on a threshold you configure", but "Cloud Armor also protects serverless NEGs when traffic is routed through a load balancer." [23] Crux has no load balancer. Since the Worker is Cloud Run's only caller, a per-network cap on Cloud Run's side was not found on the pages read.

## Sources

1. Cloudflare, Rate limiting rules (incl. Availability): https://developers.cloudflare.com/waf/rate-limiting-rules/
2. Cloudflare, Rules language operators: https://developers.cloudflare.com/ruleset-engine/rules-language/operators/
3. Cloudflare, How Cloudflare determines the request rate: https://developers.cloudflare.com/waf/rate-limiting-rules/request-rate/
4. Cloudflare, Rate limiting parameters: https://developers.cloudflare.com/waf/rate-limiting-rules/parameters/
5. Cloudflare, Troubleshoot rate limiting rules: https://developers.cloudflare.com/waf/rate-limiting-rules/troubleshooting/
6. Cloudflare, Create a rate limiting rule in the dashboard: https://developers.cloudflare.com/waf/rate-limiting-rules/create-zone-dashboard/
7. Cloudflare, Custom Errors: https://developers.cloudflare.com/rules/custom-errors/
8. Cloudflare, Error 1015: https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1015/
9. Cloudflare, workers.dev: https://developers.cloudflare.com/workers/configuration/routing/workers-dev/
10. Cloudflare, Custom Domains: https://developers.cloudflare.com/workers/configuration/routing/custom-domains/
11. Cloudflare, Security features interoperability: https://developers.cloudflare.com/waf/feature-interoperability/
12. Cloudflare, Workers metrics and analytics: https://developers.cloudflare.com/workers/observability/metrics-and-analytics/
13. Cloudflare, Static assets, Worker script: https://developers.cloudflare.com/workers/static-assets/routing/worker-script/
14. Cloudflare, Workers pricing: https://developers.cloudflare.com/workers/platform/pricing/
15. Cloudflare, Workers Rate Limiting binding: https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/
16. Cloudflare, Workers limits: https://developers.cloudflare.com/workers/platform/limits/
17. Cloudflare, Static assets billing and limitations: https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/
18. Cloudflare, DDoS Protection: https://developers.cloudflare.com/ddos-protection/
19. Cloudflare, Bot Fight Mode: https://developers.cloudflare.com/bots/get-started/bot-fight-mode/
20. Cloudflare, Custom rules: https://developers.cloudflare.com/waf/custom-rules/
21. Google Cloud, Cloud Run pricing: https://cloud.google.com/run/pricing
22. Google Cloud, Maximum instances for services: https://cloud.google.com/run/docs/configuring/max-instances
23. Google Cloud, Cloud Armor security policy overview: https://cloud.google.com/armor/docs/security-policy-overview
24. Cloudflare, Static assets, Single Page Application: https://developers.cloudflare.com/workers/static-assets/routing/single-page-application/
