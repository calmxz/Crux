# Spending and hosting: Turnstile, rate limits and Playwright

Part of [Spec facts that rested on search snippets](../snippet-fact-checks.md), checked on 2026-11-11 for #762.

## 7. Turnstile and Cloudflare's free rate limiting

**Spec says:**

- `accounts.md:32`: "A human check runs first, Cloudflare Turnstile. It is usually invisible, and shows at most a "Verify you are human" checkbox ([#674], [#717])."
- `hosting.md:164`: "Cloudflare sees network addresses at its edge, as a processor. Its automatic flood protection and the burst guard run there (see `privacy.md`) ([#716])."
- `privacy.md:153`, `trial.md:125`: Turnstile's signals go partly to Cloudflare's own use.
- `quality-bar.md:139`: "Turnstile passes inside LinkedIn's and Facebook's apps on the Request access form ([#717])."
- `account-screens.md:10`, `landing-screens.md:62`, `trial.md:44`: the human check on the sign-in card and the Request access form.

The spec states no Turnstile plan and no rule limits. "The burst guard" comes from #674: "Cloudflare's free rate-limiting rule counts only by network address over 10 seconds, and only if Crux's traffic goes through Cloudflare, so it can add only a burst guard".

### 7a. Turnstile free plan

**Source:** Cloudflare Turnstile docs, "Plans", `https://developers.cloudflare.com/turnstile/plans/` (read as `.md`). "Last updated Aug 14, 2026."

**Page says:**

- Plans table: "Pricing | Free | Contact Sales", "Number of widgets | Up to 20 widgets | Unlimited", "Unlimited challenges (traffic or verification requests) | Yes | Yes", "Hostname management | 10 hostnames per widget".
- Plans: "Turnstile can be used independently without requiring other Cloudflare services."

**Verdict: confirmed.** Turnstile is free, with unlimited challenges and up to 20 widgets.

### 7a2. What the widget shows (`accounts.md:32`)

**Spec says:** `accounts.md:32`: "It is usually invisible, and shows at most a "Verify you are human" checkbox ([#674], [#717])." `account-screens.md:10`: "The human check, when it shows, sits under the email field."

**Source:** Cloudflare Turnstile docs, "Widget modes", `https://developers.cloudflare.com/turnstile/concepts/widget/` (read as `.md`). "Last updated Apr 16, 2026."

**Page says:**

- Modes table: "**Managed** (recommended) | Automatically chooses between non-interactive or checkbox challenge based on visitor risk level." "**Non-Interactive** | Displays visible widget with loading spinner." "**Invisible** | Runs challenges completely in the background with no visible widget or loading indicators."
- Managed mode section: "Turnstile will only require interaction if a further check is necessary to verify that the visitor is human. When an interaction is required, the visitor will be prompted to select a box."
- Invisible mode section: "Invisible mode is similar to Non-Interactive mode where visitors will never interact with the Turnstile widget. Visitors will also not see a widget or any indication that an invisible browser challenge is in progress."
- Invisible mode section: "As a condition of enabling invisible mode, you must reference Cloudflare's Turnstile Privacy Addendum in your own privacy policy."

- Widget configurations, "Appearance modes" (`https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/widget-configurations/`): "`interaction-only`: The widget becomes visible only when visitor interaction is required and provides the cleanest visitor experience. Most visitors will never see the widget, but suspected bots will encounter the interactive challenge." Also: "Appearance modes only affect visible widget types (Managed and Non-Interactive)."

**Verdict: confirmed.** Managed mode with the `interaction-only` appearance does what the spec says: usually nothing shows, and a box to tick appears only when Cloudflare is unsure. The spec does not name the mode or the setting. The page does not print the label "Verify you are human". The Privacy Addendum duty applies to Invisible mode only.

**Fix:** name the setting in `accounts.md:32`: Managed mode with the `interaction-only` appearance. Chosen by the owner on 2026-11-11 over always-visible Managed mode and Invisible mode. `account-screens.md:10` and `privacy.md:153` stay as they are.

Decisions this touches: #674 and #717 (the human check), only in wording.

### 7b. Cloudflare's free rate-limiting rule

**Source:** Cloudflare WAF docs, "Rate limiting rules", `https://developers.cloudflare.com/waf/rate-limiting-rules/` (read as `.md`). "Last updated Aug 25, 2026." Also "Cloudflare DDoS Protection", `https://developers.cloudflare.com/ddos-protection/`. "Last updated Aug 14, 2026."

**Page says:** the "Availability" table, Free column:

- "Available fields in rule expression | Path, Verified Bot"
- "Counting characteristics | IP"
- "Counting periods | 10 s"
- "Mitigation timeout periods | 10 s"
- "Number of rules | 1"
- Also: "Rate limiting rules are not designed to allow a precise number of requests to reach your origin server. There may be a delay of up to a few seconds between detecting a request and updating rate counters."
- DDoS: "Standard, unmetered DDoS protection (layers 3-7) | Yes" for Free.

**Verdict: confirmed.** The free plan gives one rule, counted by IP over 10 seconds, blocking for 10 seconds, matching on path only. "Burst guard" fits. Flood protection is on the free plan. #760 owns the site-wide cap question.

## 8. Outside the spec: #738

**Issue says** (#738, "Pause local e2e until local runs use a patched Chromium with the sandbox on"):

- "Playwright 1.64.0, pinned in `frontend/package-lock.json`, bundles Chromium 156.0.8078.4."
- "Chrome 156.0.8078.73 fixes four Critical CVEs: CVE-2026-118306, CVE-2026-118331, CVE-2026-118344, and CVE-2026-118348. CVE-2026-118306 allows code execution outside the browser sandbox from a crafted page."
- "Playwright 1.64.1, the latest stable release on 2026-11-03, still bundles 156.0.8078.4."
- "Playwright adds `--no-sandbox` unless `chromiumSandbox: true` is set. `frontend/playwright.config.js` does not set it."

The issue's sources are a news site, a CVE aggregator and another project's PR. None owns the facts.

The worktree confirms the local part: `frontend/package-lock.json:1478` pins `@playwright/test` at `"version": "1.64.0"`, and `frontend/playwright.config.js` sets no `chromiumSandbox`, `launchOptions` or `channel`.

### 8a. The CVE numbers

**Source:**

- NVD API records, `https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2026-118306` and the same for 118331, 118344 and 118348. Published 2026-10-27.
- CVE.org records, `https://cveawg.mitre.org/api/cve/CVE-2026-118306` and the others. Assigner "Chrome", state "PUBLISHED".
- Chrome Releases, "Stable Channel Update for Desktop", Tuesday, October 27, 2026, `https://chromereleases.googleblog.com/2026/10/stable-channel-update-for-desktop_0562499947.html`.

**Page says:**

- Chrome Releases: "The Stable channel has been updated to 156.0.8078.73/.74 for Windows and Mac and 156.0.8078.73 to Linux". "This update includes 52 security fixes." The list starts "Critical CVE-2026-118306: Use after free in FileSystem.", "Critical CVE-2026-118331: Use after free in FileAPI.", "Critical CVE-2026-118348: Integer overflow in Skia.", "Critical CVE-2026-118344: Use after free in Layout." The other 48 are High or Medium.
- NVD, CVE-2026-118306: "Use after free in FileSystem in Google Chrome prior to 156.0.8078.73 allowed a remote attacker to execute arbitrary code outside the sandbox via a crafted HTML page. (Chromium security severity: Critical)". CVSS 3.1 9.6 CRITICAL.
- NVD, CVE-2026-118331: "Use after free in FileAPI in Google Chrome prior to 156.0.8078.73 allowed a remote attacker to execute arbitrary code outside the sandbox via a crafted HTML page. (Chromium security severity: Critical)". CVSS 3.1 8.8 HIGH.
- NVD, CVE-2026-118344: "Use after free in Layout in Google Chrome prior to 156.0.8078.73 allowed a remote attacker to execute arbitrary code inside the sandbox via a crafted HTML page. (Chromium security severity: Critical)". CVSS 3.1 8.8 HIGH.
- NVD, CVE-2026-118348: "Integer overflow in Skia in Google Chrome prior to 156.0.8078.73 allowed a remote attacker to potentially execute arbitrary code outside the sandbox via a crafted HTML page. (Chromium security severity: Critical)". CVSS 3.1 8.8 HIGH.

On all four NVD records, the CVSS 3.1 score is the only score, marked "Secondary". Its source ID, `134c704f-9b21-4f2e-91b3-4a467353bcc0`, is the same one that gives each record's CISA SSVC entry ("role": "CISA Coordinator"). NVD has added no score of its own, and Chrome gives none.

**Verdict: confirmed.** All four numbers exist, are rated Critical by Chromium, and are fixed in 156.0.8078.73.

**Also on the page:** the issue understates the risk. Three of the four, not one, describe code running outside the sandbox: 118306, 118331 and 118348 ("potentially"). The CVSS scores differ from Chromium's rating: one 9.6 Critical, three 8.8 High. If #738 is edited, say "Chromium rates all four Critical", and list 118331 and 118348 as outside-the-sandbox too.

### 8b. Playwright's bundled Chromium

**Source:**

- `packages/playwright-core/browsers.json` at tags `v1.64.0`, `v1.64.1` and `v1.65.0`, `https://raw.githubusercontent.com/microsoft/playwright/<tag>/packages/playwright-core/browsers.json`.
- GitHub releases for `microsoft/playwright`, read through the GitHub API.

**Page says:**

- v1.64.0 and v1.64.1: `"name": "chromium"`, `"revision": "1248"`, `"browserVersion": "156.0.8078.4"`.
- v1.65.0: `"revision": "1254"`, `"browserVersion": "158.0.8127.18"`.
- Releases: v1.64.0 published 2026-10-07, v1.64.1 published 2026-10-14, v1.65.0 published 2026-11-05.
- v1.65.0 notes, "Browser Versions": "Chromium 158.0.8127.18" and "Google Chrome 157".

**Verdict: changed.** On 2026-11-03, 1.64.1 was the latest stable release and bundled 156.0.8078.4, as the issue says. Playwright 1.65.0 came out on 2026-11-05 and bundles Chromium 158.0.8127.18. The issue's "Upgrade only" path is now open. Its acceptance check still applies: compare `browser.version()` with the latest Chrome stable security fix.

**Fix (in #738, not the spec):** "Playwright 1.65.0 (2026-11-05) bundles Chromium 158.0.8127.18. Upgrading `@playwright/test` to 1.65.0 replaces the 156.0.8078.4 build." The sandbox point in 8c stays.

### 8c. The `chromiumSandbox` default

**Source:**

- Playwright docs, "BrowserType", `https://playwright.dev/docs/api/class-browsertype`.
- Playwright source, `packages/playwright-core/src/server/chromium/chromium.ts` at `v1.64.0` (and at `v1.65.0`).
- Playwright docs source, `docs/src/api/params.md` at `v1.64.0`.

**Page says:**

- Docs, and `params.md` at v1.64.0: "Enable Chromium sandboxing. Defaults to `false`."
- Source at v1.64.0, lines 389 and 390:

  ```ts
      if (options.chromiumSandbox !== true)
        chromeArguments.push('--no-sandbox');
  ```

  v1.65.0 has the same two lines at 386 and 387.

**Verdict: confirmed.** Playwright launches Chromium with `--no-sandbox` unless `chromiumSandbox` is exactly `true`. The check sits in `_innerDefaultArgs`, the Chromium launcher's default arguments, with no condition on the channel, so it applies to `channel: 'chrome'` too. #738's Option B (`launchOptions: { chromiumSandbox: !process.env.CI }`) is the right switch.
