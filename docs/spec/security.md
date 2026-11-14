# Security

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers the visitor's country and address, the content security policy, the other headers, and how they are checked. Where things run, the Worker's secret header and where Crux checks the country are in [`hosting.md`](hosting.md). The repo's guards, such as CodeQL and osv-scanner, are in [`quality-bar.md`](quality-bar.md). The Build notes at the end hold provider settings for the build ticket.

## The visitor's country and address

- Cloudflare removes `CF-IPCountry` from a Worker's calls to an origin outside Cloudflare, such as Cloud Run (Cloudflare's HTTP headers page) ([#769]).
- So the Worker reads the country from `request.cf.country` and the address from `CF-Connecting-IP`. It sends both to the backend in Crux's own headers, after deleting any incoming headers of those names ([#769]).
- The backend reads only those headers, behind the secret-header check, and never `X-Forwarded-For` ([#769]). The address is what the code limits and wrong-link counts read ([#716], [#717]).
- The country `XX` (no data), `T1` (Tor) and an empty country get the region message, like the EU and the UK ([#769]).
- The Worker drops `Referer` on its calls to Cloud Run, so a page's path, a trial link's key included, never reaches the backend that way ([#769]).

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

## Build notes

These specifics are left to the build ticket. They were checked while deciding, and change as the providers do ([#769]).

- Cloudflare features that add scripts or change pages stay off: Bot Fight Mode (its JavaScript detections cannot be turned off), Web Analytics, Rocket Loader, Email Address Obfuscation and Zaraz. `Cache-Control: no-transform` stops Email Obfuscation and the analytics beacon.
- Whether wrangler's local runtime applies `_headers`, and whether it overwrites `CF-Connecting-IP` the way the edge does.
- Miniflare's `cf` option sets one country per runtime, so the region path needs its own run, with wrangler's real-location fetch turned off.
- The policy's full list: `object-src 'none'`, `base-uri 'none'`, `form-action 'self'`, a worker source if the file viewer needs one, and `media-src` for the video.
- Sentry's tunnel option, if Sentry is added.

[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#769]: https://github.com/calmxz/Crux/issues/769
