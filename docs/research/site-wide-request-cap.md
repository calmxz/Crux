# Research: a site-wide request cap per network (#760)

Question: how should Crux cap the requests one network can make across the whole site, so bots probing addresses or hammering the backend cannot spend the Cloud Run budget? What does Cloudflare's free plan offer, how does a rule fit in front of Crux's Worker, and what does a blocked visitor see?

Every fact comes from Cloudflare's or Google Cloud's own pages, read on **2026-11-12**. Where a page was silent, the note says "unstated". The decision belongs to a later decision ticket. This note does not change the spec.

## Files

- [`site-wide-request-cap/cloudflare-limits.md`](site-wide-request-cap/cloudflare-limits.md): what the Free plan's rate limiting rule, the Workers Rate Limiting binding, Durable Objects and Cloud Run offer, with quotes and the source list.
- [`site-wide-request-cap/options.md`](site-wide-request-cap/options.md): three ways to apply a cap, with their numbers, what a blocked visitor sees, costs, and how each fits the existing guards.

## Short answer

Cloudflare's Free plan gives one rate limiting rule. It matches on path, counts by network address per data centre, and allows only a 10-second period and a 10-second block. Its blocked response is Cloudflare's own 429 page, which Free cannot change. That makes it a burst guard, not a budget guard. A network that stays under the limit is never blocked, so a slow bot passes.

The tighter limit today is the Worker's own: 100,000 requests a day on Workers Free, shared by everyone. One steady network at about 1.2 calls a second spends it, which stops the API for everyone until midnight UTC. By rough arithmetic, that many calls a day can also spend Cloud Run's free credit over a month.

So no free option caps one network over an hour or a day without code. The three ways, in order of effort:

| | What it caps | Blocked visitor sees | Cost |
|---|---|---|---|
| 1. Free WAF rule on `/api/` | Bursts: N calls per 10 s per network, then a 10 s block | Cloudflare's 429 (error 1015) on `/api` calls; the app can show its own message | 0; the one Free rule; a zone setting |
| 2. Workers Rate Limiting binding | N calls per 10 or 60 s per network, approximate, per location | Crux's own 429 and message | 0 (plan unstated); a small Worker change; blocked calls still use the Worker's allowance |
| 3. Durable Object counter | Any window, such as an hour, strict | Crux's own 429 and message | 0 within Free allowances; the most code; a new address record |

How a rule fits in front of the Worker: WAF rules belong to a zone. Crux's domain is a zone, and the spec runs the trial on the domain with `workers.dev` turned off, so a rule covers the trial. A request the rule blocks never reaches Cloud Run. The Workers metrics page says requests blocked by the WAF "will not count" in the Worker's request total. A Worker on `workers.dev`, such as staging, gets no rule. Options 2 and 3 live in Worker code, so they work on both.

## A conflict in the spec

`hosting.md` already says Cloudflare's "automatic flood protection and the burst guard run there", citing #716. The burst guard comes from the decision on "how people sign up from a shared link" (#674), which read the Free rule as able to "add only a burst guard". No spec file gives the burst guard's path, numbers or response. So the spec names a site-wide burst guard but doesn't define it, while #760 says the spec has no site-wide cap. Both are true in part. The decision ticket should settle whether the burst guard is option 1, and give its numbers.

## Recommendation (not a decision)

Use option 1 and option 2 together, and decide option 3 on the trial's numbers.

- Option 1 costs nothing and keeps floods away from Cloud Run, and likely from the Worker's daily allowance (see "Not settled").
- Set the Worker's `run_worker_first` to a list of paths, such as `/api/*`, so unknown paths outside it serve the app's files and never run the Worker.
- Option 2 adds Crux's own 429 and message, a 60-second window, and coverage on staging.
- Neither stops a slow bot, so the Worker's daily allowance and the Cloud Run spend cap remain the backstop.
- If the trial shows steady misuse, or the measured use leaves room for an hourly cap, add option 3 with its privacy change.

Set the numbers from measurement, not guesses. Count the `/api` calls one learner makes on opening and per minute of a busy sitting. Multiply by the largest class expected on one network.

## Not settled

- **Normal call rates.** How many `/api` calls an opening and a busy sitting make, and how many learners may share one network address. Each cap's numbers depend on these.
- **The binding's plan and price.** The Workers Rate Limiting binding page, the Workers pricing page and the Workers limits page don't state them.
- **Whether WAF-blocked requests count toward the Worker's 100,000 a day.** The metrics page says they don't count in its request total. The limits page doesn't say how the daily count is kept.
- **Fail-open or fail-closed for Crux's Worker.** The limits page describes both modes for routes. Which one applies to a Custom Domain Worker with static assets, at the daily limit, is unstated. The static assets page says `run_worker_first` paths get a 429.
- **Which paths run the Worker.** In single-page-application mode without a `run_worker_first` list, a request without the navigation header runs the Worker on any unknown path. An `/api/`-only rule doesn't count those. The spec doesn't fix this setting.
- **Where staging runs.** If staging stays on `workers.dev`, option 1 cannot be tested there.
- **The Cloud Run cost of a refused call.** The illustration in `cloudflare-limits.md` uses up to 100 ms per call, from the pricing page's rounding. The first month's billing report settles the real figure.
- **Whether a binding key is an address record.** The main file allows only two address records. The decision says whether a count Cloudflare holds for 60 seconds, keyed by a scrambled address, is one.
