# Ways to cap requests per network

Part of [Research: a site-wide request cap per network](../site-wide-request-cap.md) (#760). Facts and quotes are in [`cloudflare-limits.md`](cloudflare-limits.md), cited here as [L]. Numbers marked "derived" are arithmetic on those facts, not stated by any source.

## What any cap must allow

The numbers below are examples. The right values depend on two facts that nothing in the spec gives yet:

- **How many `/api` calls one learner makes.** Opening the app calls the backend at once (warm-on-open). Waiting answers are fetched in a loop, less often the longer they wait (`hosting.md`). Each message, file upload link and check is a call.
- **How many learners share one network address.** A class on school Wi-Fi, or many phones behind one mobile carrier address, look like one network. The Workers binding page warns that addresses "can be shared by many users in many valid cases" [L].

A cap set below a shared network's normal use turns away real learners. A cap set well above it lets a slow bot through. Every option below has this tradeoff. Only option 3 counts over a window long enough to separate the two.

## Option 1: the Free rate limiting rule on `/api` (a burst guard)

**How it works.** One WAF rate limiting rule on the domain's zone matches `starts_with(http.request.uri.path, "/api/")`. It counts per network address and data centre. Past N requests in 10 seconds, it blocks that network's `/api` calls for 10 seconds [L].

**Numbers it allows (derived).** At most N calls per 10 seconds from one network. A network that stays under that rate is never blocked. At N = 30, that is 10,800 calls an hour and 259,200 a day.

**What a blocked visitor sees.** Pages and files still load, because the rule matches `/api` only. Each `/api` call returns 429 with Cloudflare's own body (error 1015), which Free cannot change [L]. The app can show its own message for a 429, with a fixed 10-second wait.

**Cost.**

- Money: none.
- Rules: the Free plan's only rate limiting rule.
- Complexity: a zone setting, made in the dashboard or by API. No Crux code apart from the app's 429 message.
- Blocked calls never reach Cloud Run. The Workers metrics page leaves them out of the Worker's request total, but whether they count toward the 100,000-a-day allowance is unstated [L].

**Domain and `workers.dev`.** It covers the live site from the trial on, because the trial runs on the domain. It cannot cover a Worker on `workers.dev`, such as staging if staging stays there [L]. So it cannot be tested on staging unless staging uses a host on the domain.

**Limits.** It stops floods, not a steady bot. A bot sending about 1.2 calls a second stays far under any useful N. That rate still spends the Worker's daily allowance and, by the illustration in [L], can spend Cloud Run's free credit over a month. An `/api/`-only rule also misses unknown paths outside `/api`. Unless the Worker lists its paths in `run_worker_first`, a bot that omits the navigation header runs the Worker on those paths, and spends its allowance [L].

## Option 2: a per-network limit in the Worker (the Rate Limiting binding)

**How it works.** Before forwarding an `/api` call to Cloud Run, the Worker calls `limit()` with the network address as the key. The window is 10 or 60 seconds [L]. The Worker can hold more than one limit, for example one for all `/api` calls and a lower one for sending a message.

**Numbers it allows (derived).** L calls per 60 seconds gives 60 × L an hour and 1,440 × L a day per network, per Cloudflare location. At L = 60, that is 3,600 an hour and 86,400 a day. The count is approximate: "Requests can exceed this threshold" [L].

**What a blocked visitor sees.** The Worker writes the response. Crux can return 429 in its own JSON error shape, with the seconds left in the window. The app shows Crux's own words.

**Cost.**

- Money: none found, but the binding's plan and price are unstated on the pages read [L].
- Rules: none. The one WAF rule stays free for option 1.
- Complexity: a few lines in the Worker and a binding in its Wrangler configuration. It can be tested on staging and in local runs, because it lives in Worker code.
- Each checked call runs the Worker, so blocked calls still use the Worker's daily allowance. They don't reach Cloud Run.

**Domain and `workers.dev`.** It works the same on both, so staging gets it too.

**Limits.** It is still a per-minute count, so it shares option 1's weakness against a slow bot. To keep one network under a quarter of the Worker's daily allowance (25,000), L would have to be about 17 a minute (derived). That is likely too low for a class sharing one address.

**Privacy.** The Worker passes the address to Cloudflare as a key, and Cloudflare holds the count for the window. Cloudflare already sees addresses at its edge as a processor (`hosting.md`). The decision should still say whether this is a new address record. The main file says "The only address records are the sign-in code limits and the wrong-link counts". The Worker can pass a scrambled address as the key, so the count isn't tied to a readable address.

## Option 3: an hourly or daily cap in a Durable Object

**How it works.** The Worker asks a Durable Object, keyed by the scrambled network address, to add one to that network's count for the hour. Over the cap, the Worker refuses the call. "If you need one strict limit across all locations, implement a rate limiter with Durable Objects." [L]

**Numbers it allows.** Any window and any limit. For example, 1,000 calls an hour per network allows at most 24,000 a day (derived). That is under a quarter of the Worker's daily allowance. A class can still burst within the hour, because the count is per hour, not per minute.

**What a blocked visitor sees.** As option 2: Crux's own 429 and message, with the time until the hour resets. The wording could follow "Too many wrong links" in `landing-screens.md`.

**Cost.**

- Money: none within the Free plan's Durable Object allowance of 100,000 requests and 100,000 SQLite row writes a day [L]. Each `/api` call adds one Durable Object request. A stored count also adds a row write. These allowances are the same size as the Worker's, so they run out at the same pace.
- Rules: none.
- Complexity: the most of the three. It needs a Durable Object class and its migration in the Worker's configuration, expiry of old counts, and tests. Each call adds a round trip to the object.
- Privacy: a count keyed by a scrambled address, kept for an hour, is a new address record. It needs a recorded change to the main file's "Where data lives" and to `privacy.md`, with an expiry like the code limits'.

**Domain and `workers.dev`.** It works the same on both.

**Limits.** Many networks at once (a botnet) can still spend the Worker's allowance, since each stays under its own cap. No per-network cap stops that. The Worker's daily allowance and the Cloud Run spend cap remain the last stops.

## Paid variants, for comparison

These are recorded changes to the main file's free-hosting rule.

- **Cloudflare Pro**, "$20 /mo billed annually, or $25/mo billed monthly" (https://www.cloudflare.com/plans/). It allows 2 rules, periods up to 1 minute, blocks up to 1 hour and a custom response [L]. It is still a per-minute count.
- **Workers Paid**, "a minimum charge of $5 USD per month for an account", with "10 million included per month" (https://developers.cloudflare.com/workers/platform/pricing/). It removes the 100,000-a-day ceiling, which is the thing that takes the API down for everyone. It also removes the ceiling that bounds Cloud Run's exposure, so a per-network cap matters more on it.

## Summary

| | 1. Free WAF rule | 2. Worker binding | 3. Durable Object |
|---|---|---|---|
| Window | 10 s, block 10 s | 10 or 60 s | Any (hour, day) |
| Stops a slow bot | No | No | Yes, per network |
| Blocked response | Cloudflare's 429 page | Crux's own 429 | Crux's own 429 |
| Uses Worker allowance when blocked | Not in the Worker's request total; daily count unstated | Yes | Yes, plus a Durable Object request |
| Covers `workers.dev` and staging | No | Yes | Yes |
| Money | 0 | 0 (plan unstated) | 0 within Free allowances |
| Effort | Zone setting | Small Worker change | Durable Object, tests, privacy change |
| New address record | No | To decide | Yes |

## How each fits the existing guards

- **Order.** Option 1 runs at Cloudflare's edge before the Worker. Options 2 and 3 run in the Worker before Cloud Run. All three act before Crux's own per-path guards, which run in Cloud Run.
- **The per-path guards stay.** The sign-in code limits (20 an hour per network), the copy page's wrong-code limit (10 an hour), the wrong-link limit (10 an hour) and Turnstile count specific actions over an hour. A site-wide cap counts all calls, so it must sit well above what those guards allow. Then a real learner meets the specific message, such as "Too many wrong links", before the general one.
- **What the site-wide cap adds.** Once a network passes the wrong-link limit, each further try is still a Cloud Run call that Crux refuses. A site-wide cap stops those calls before Cloud Run. Without one, a prober can keep making refused calls all day, bounded only by the Worker's allowance.
- **The owner page and the outside check.** The owner's calls count toward the cap like anyone's. The outside check runs every 5 minutes from 3 or more places (`operations.md`), far below any of these caps. Bot Fight Mode is a poor fit here, because it can challenge the outside check with no way to exempt it [L].
