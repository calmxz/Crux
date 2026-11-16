# Security

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers the visitor's country and address, keys in addresses, the request guards, the content security policy, the other headers, and how they are checked. Where things run, the Worker's secret header and where Crux checks the country are in [`hosting.md`](hosting.md). The repo's guards, such as CodeQL and osv-scanner, are in [`quality-bar.md`](quality-bar.md). The Build notes at the end hold provider settings for the build ticket.

## The visitor's country and address

- Cloudflare removes `CF-IPCountry` from a Worker's calls to an origin outside Cloudflare, such as Cloud Run (Cloudflare's HTTP headers page) ([#769]).
- So the Worker reads the country from `request.cf.country` and the address from `CF-Connecting-IP`. It sends both to the backend in Crux's own headers, after deleting any incoming headers of those names ([#769]).
- The backend reads only those headers, behind the secret-header check, and never `X-Forwarded-For` ([#769]). The address is what the code limits, the wrong-link counts and the copy page's wrong-code counts read ([#716], [#717], [#762], [#770]).
- The country `XX` (no data), `T1` (Tor) and an empty country get the region message, like the EU and the UK ([#769]).
- The Worker drops `Referer` on its calls to Cloud Run, so a page's path never reaches the backend that way ([#769]).

## Keys in addresses

- A trial link's key and the copy page's code sit after a `#` in the address, for example `/t/#AbC123…` (draft format). Browsers never send that part, so Cloudflare, its analytics and Crux's logs never see it ([#770]).
- The app reads it, sends it in the body of its first `/api` call, and clears the address bar. The invite and copy emails carry the `#` form ([#770]).
- The session search's term also travels in a request body, never in an address (see [`app-shell.md`](app-shell.md#the-all-sessions-page)) ([#780]).
- Guessing is stopped as before: a long random key, 10 wrong links or codes an hour per network, and the request guards below ([#717], [#762], [#770]).

## Request guards

Free Cloudflare rules guard `/api/` before the Worker. No per-network count runs in the Worker, and Cloudflare's automatic flood protection stays on ([#770]).

### The rules

- **The burst guard** is Cloudflare's one free rate limiting rule on `/api/`. Once a network passes 300 `/api` calls in 10 seconds, counted per Cloudflare data centre, its `/api` calls are refused for 10 seconds. A class of 25 opening together, about 200 calls (25 × 8, a guess), is never refused. A flood from one network gets through at about 15 calls a second (300 per 10-second count plus 10-second block) ([#674], [#770]).
- **The no-session rule** is a free custom rule that refuses `/api/` calls with no sign-in cookie, except on the open paths. It tests only that the sign-in cookie's name is there, so it stops scanners, not a deliberate script. The backend still checks the cookie on each call. Live and staging each have their own copy ([#770]).
- **The open paths** are the routes the API contract marks public: warm-on-open, the landing page's state calls, guest mode and its samples, sign-in, the email code, the Google sign-in return, "One more thing" and its "Email me if spots open" tick, opening a trial link, Request access, the copy page, `/api/client-error`, and the outside check's endpoints ([#770]).
- **Hand blocks:** after a push, the owner finds the network in Cloudflare's Security Analytics and adds its single address to the hand-block list, which a custom rule refuses on `/api/`. Pages still load, but nothing that needs `/api/` works for that network ([#770]).
- At its 8:05 am run, the daily job lifts each hand block at least 12 hours old, so every block lasts past the next 8 am reset of the Worker's 100,000. A block lasts 12 to 36 hours: one set at 7:55 am lasts 24 hours, one at 2 pm 18 hours, one at 9 pm 35 hours. It lasts longer only while the daily job is down or a lift fails. A network that comes back is blocked again by hand ([#770]).
- The owner is told when a lift fails, when a block outlives 36 hours, and when the list holds anything but single addresses ([#770]).
- A blocked address may be shared, by a mobile carrier or campus Wi-Fi, so a block shuts out anyone else on it while it lasts. That is why guests are not limited by network address. A hand block takes that cost only for a network the owner judged a script ([#677], [#770]).
- Only `/api/*` runs the Worker. Every other unknown address gets the app's files, which are free and never count toward the Worker's 100,000 a day ([#770]).

### The pushes

- A push when more than 3,000 `/api` calls arrive in 10 minutes, in total across routes. It links a chart of the calls by route, which shows the busiest. A busy class makes about 1,000 to 1,500 in 10 minutes (a guess) ([#770]).
- A backstop push when more than 30,000 `/api` calls arrive in any 24 hours ([#770]).
- Both are metric alerts on Crux's own logs on live, which hold the route, never an address (see [`operations.md`](operations.md)) ([#770]).
- **Example:** a script floods one route at 50 calls a second from 9 am. About 15 a second get through, so the push comes at about 9:03. If about 93,000 of the day's 100,000 are left (a guess), they last until about 10:43. A script at 2 calls a second never trips the first push; with about 6,700 normal calls in the past 24 hours (a guess), the backstop comes after about 3.2 hours ([#770]).
- The 300 and both pushes' numbers are re-set before opening from the trial's real counts (see [`quality-bar.md`](quality-bar.md)) ([#770]).
- The session search's pause and the all-sessions page's batch size are set so that a check passes: 25 learners opening Crux, then the page, and searching within the same 10 seconds stay under the burst guard's 300, counting the class's own opening of about 200 calls. As a guess, one page call and 3 search calls each add 100, which reaches 300 and fails, so the build needs a longer pause or a later first batch; scroll batches, retries and the re-check on Back count too. Ten searches each over 10 minutes add about 750 to a busy class's 1,000 to 1,500: 1,750 to 2,250, under the 3,000 push. About 50 search calls a learner a day, 1,250 for 25, added to about 6,700 other calls (a guess) make about 7,950, under the 30,000 backstop and the Worker's 100,000. The trial's real counts re-set these with the 300 ([#780]).

### What a learner sees

- A **Cloudflare refusal** is a 403 or 429 that does not carry Crux's error shape: one shape, set in the API contract, that every error from the backend or the Worker carries, with a Crux error code. The Worker turns any answer from Cloud Run not in that shape into Crux's "can't be reached" code, so a Cloudflare refusal is always one made before the Worker ([#770]).
- A tap, such as Send, shows as sending, and the app tries once more after 10 seconds. If that is refused too, the learner sees "Crux can't be reached right now. Try again later.", and a typed message stays in the box. The call never reached the Worker, so the retry cannot send a message twice. Every other error keeps its own handling ([#770]).
- A session search fired by typing, or a batch of the all-sessions page fired by scrolling, counts as a tap: it shows "Loading..." and tries once more after 10 seconds. Nothing is sent during the wait: when it ends, one search goes with whatever is typed then, and a refused batch is fetched again with it ([#780]).
- A learner whose sign-in cookie is missing or lapsed sees what a signed-out visitor sees now. A learner on a blocked network sees "Crux can't be reached right now. Try again later." Neither ever sees the other's screen ([#770]).
- On the landing page, warm-on-open tries again after 10 seconds before the page greys (see [`landing-screens.md`](landing-screens.md)). Asking for finished answers and `/api/client-error` show nothing on a refusal. They back off, and error reports are dropped rather than retried ([#770]).
- A mastery check refused mid-way stays half-done, as [`ai-layer.md`](ai-layer.md) keeps it when the tutor is busy ([#770]).

### Staging and releases

- **Staging's gate:** staging's copy of the no-session rule also refuses every request to the staging host, pages included, unless it carries a long random secret. The open-path check sends it in a header. The owner's browser holds it in a cookie, set once from one staging page left open for pasting it (draft). So no one else spends the shared 100,000 or the test budget through staging ([#770]).
- The secret is a GitHub secret, filled into the rule when the rule is applied, so it sits in Cloudflare's rule text, never in the repo ([#770]).
- The burst guard, both copies of the no-session rule and the hand-block rule live in the repo. The open paths come from the API contract's public routes ([#770]).
- A release changes staging's copy when it reaches staging, and live's at the live step. The burst guard and the hand-block rule serve both hosts, so they never change when a release reaches staging. A release never changes the hand-block list's entries ([#770]).
- **The open-path check** calls every open path with no sign-in cookie, expecting Crux's own answer, and one member route with no sign-in cookie, expecting Cloudflare's 403. Its bodies fail validation on every open path, so it adds no wrong-link or wrong-code count and sends no email, AI call or push. It runs on staging before live, and on live after each release. Staging's browser paths run locally, so this check is what catches a rule mistake before live ([#770]).
- No release or rollback leaves the serving code with an open path refused, or a member route open with no sign-in cookie. A dropped open path stops the release on staging. A rollback re-applies the previous rules with the previous code, in its one step (see [`hosting.md`](hosting.md)) ([#716], [#770]).

### Limits and cost

- Custom rules in use: 3 of Free's 5 (live's copy, staging's copy with the gate, the hand-block rule). The hand-block list is Free's one custom list, of up to 10,000 entries. The burst guard is Free's one rate limiting rule ([#770]).
- Staging shares live's 100,000 a day, since the allowance is the Cloudflare account's, and shares the per-network burst count ([#770]).
- A flood that the burst guard lets through and nobody blocks reaches Cloud Run, up to the 100,000 a day. At about 100 ms a call (Cloud Run rounds up to 100 ms; a slower call bills more), about 13 such days spend the free credit, and about 15 reach the USD 6 cap. The first month's billing report settles the real cost ([#726], [#770]).

## The content security policy

The policy is on every page Crux serves ([#769]):

- Everything comes only from Crux's own address unless named here.
- Scripts and frames also come from Turnstile (`https://challenges.cloudflare.com`, per Cloudflare's Turnstile page). Google sign-in is a plain redirect and loads no script ([#717]).
- No inline scripts. The load-failure handler is its own file (see [`operations.md`](operations.md)).
- Images, and connections, also go to Crux's files bucket by its own path, never Google's shared storage address alone, wherever the app shows or sends a learner's file.
- No outside image loads, so a reply cannot send text out through one.
- Inline styles only as KaTeX and Mermaid need them.
- The demo video is one of Crux's own files (see [`landing-screens.md`](landing-screens.md)). The file viewer frames nothing.
- If Sentry is added, how it loads and sends is in [`operations.md`](operations.md).

## The other headers

These are on every page Crux serves too ([#769]):

- HSTS, sent without preload in v1, since a preload is hard to undo.
- `X-Content-Type-Options: nosniff`.
- `Referrer-Policy: strict-origin-when-cross-origin` or stricter.
- No framing by other sites.

So an outside site never receives a page's path as the referrer, and a trial link's key and the copy page's code never leave that way ([#769]).

## Where the headers are set

- The headers are set in the repo, not in Cloudflare's dashboard. This covers the static files and every response the Worker makes or passes on from Cloud Run ([#769]).
- No Cloudflare feature may add a script to the pages ([#769]).

## The checks

- A browser path checks the headers on a static page, an unknown address, a trial-link address and the copy page. The other browser paths are in [`ordinary-tests.md`](ordinary-tests.md) ([#769]).
- Before the trial, one check on the live address finds the headers. It also finds that every script on the landing page and a legal page is one the build made ([#769]).
- Turnstile's hostname check is proven on staging, with real keys, since Cloudflare's test keys always answer with `example.com` ([#769]).
- Before the trial, checks on live find the request guards and the open paths working. They also find that calls Cloudflare refuses, by a custom rule or the burst guard, do not count toward the Worker's 100,000: Cloudflare's metrics page says requests blocked by WAF "will not count", and its limits page does not say. That check passes only if the Worker still gives Crux's own answer after more than 100,000 refused calls in one UTC day, run before any learner. A third finds that Security Analytics on Free shows the source address of busy traffic ([#770]).
- A fourth finds that a `#` trial link opens from the Gmail and Outlook apps, in the existing check (see [`quality-bar.md`](quality-bar.md)). If any of the last three fails, the part that rests on it comes back to the owner as a recorded change ([#770]).

## Build notes

These specifics are left to the build ticket. They were checked while deciding, and change as the providers do ([#769], [#770]).

- Cloudflare features that add scripts or change pages stay off: Bot Fight Mode (its JavaScript detections cannot be turned off), Web Analytics, Rocket Loader, Email Address Obfuscation and Zaraz. `Cache-Control: no-transform` stops Email Obfuscation and the analytics beacon.
- Whether wrangler's local runtime applies `_headers`, and whether it overwrites `CF-Connecting-IP` the way the edge does.
- Miniflare's `cf` option sets one country per runtime, so the region path needs its own run, with wrangler's real-location fetch turned off.
- The policy's full list: `object-src 'none'`, `base-uri 'none'`, `form-action 'self'`, a worker source if the file viewer needs one, and `media-src` for the video.
- Sentry's tunnel option, if Sentry is added.
- The rule expressions, such as `starts_with(http.request.uri.path, "/api/")`. The cookie tests use `http.cookie` ("the entire cookie as a string", with no plan note); the per-cookie field needs Pro. The gate's test matches the secret's value.
- The Worker's `run_worker_first` list is `/api/*`.
- **Signed out or blocked:** after a Cloudflare 403 on a member route, the app calls one open path. An answer in Crux's error shape, or the burst guard's 429, means signed out, since custom rules run before rate limiting. A Cloudflare 403 means blocked. An ordinary test covers each outcome.
- **Releases:** each rule is changed on its own through the API, since replacing the whole custom ruleset would remove the other rules. The order of widening and narrowing live's copy around the traffic switch, in a release and a rollback; what happens when one rule's change fails part-way; and how a failed check reaches the owner, such as the failed release job's email.
- **The open-path check:** a browser user agent, since Browser Integrity Check challenges a missing or unusual one; and a check that the no-session rule, not a hand block or another rule, made a refusal before it counts as a miss.
- **Hand-block upkeep:** a block's age from the list entry's own added time, measured to the scheduled 8:05 am, not from a comment the token could edit. How the owner is told of a failed lift, an old block, or a list that holds more entries than the owner added.
- **The gate cookie:** `SameSite=Lax`, so Google's sign-in return to staging carries it.
- **The pushes:** a metric alert counts over a rolling window of at most 25 hours, so the backstop uses 24 hours, not the calendar day. The by-route chart is a Cloud Monitoring chart of the log-based metric, linked from the push's text.

[#674]: https://github.com/calmxz/Crux/issues/674
[#677]: https://github.com/calmxz/Crux/issues/677
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#726]: https://github.com/calmxz/Crux/issues/726
[#762]: https://github.com/calmxz/Crux/issues/762
[#769]: https://github.com/calmxz/Crux/issues/769
[#770]: https://github.com/calmxz/Crux/issues/770
[#780]: https://github.com/calmxz/Crux/issues/780
