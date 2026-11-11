# Tools: Google sign-in testing, Turnstile, Zoho Mail, Workspace and Betterleaks

Part of [Spec facts that rested on search snippets](../snippet-fact-checks.md), checked on 2026-11-11 for #762.

## 8. Google Auth Platform: 100 test users while in testing

**Spec says:**

- `accounts.md:9`: "Sign-up is off during the trial. Sign-in by Google or code works only for the owner's own email addresses ([#677], [#717], [#728] Answer 5). A test address goes on the same list (see [`feedback.md`](feedback.md)) ([#734])."
- `accounts.md:11`: "An email not on the list, by code or by Google, is refused before any code is sent".
- `accounts.md:26`: "Crux uses the plain OAuth 2 redirect and asks only for `openid email`. Google returns only the email and whether it is verified."
- `quality-bar.md:237`, before opening: "Google's sign-in screen moved to production, with the Privacy Policy on the domain ([#717])".

The spec does not state the 100-user figure.

**Source:** "Manage App Audience - Google Cloud Platform Console Help", `https://support.google.com/cloud/answer/15549945?hl=en`. No date shown.

**Page says:**

- "Projects configured with a publishing status of Testing are limited to up to 100 test users listed in the OAuth consent screen. A test user consumes a project's test user quota once added to the project."
- "Authorizations by a test user will expire seven days from the time of consent."
- "The only exception to this behavior is if your app requests a subset of the following: name, email address, and user profile (through the userinfo.email, userinfo.profile, openid scopes or their OpenID Connect equivalents ). For such requests, your users do not need to be in the trusted user list, they will not see a warning message, and their authorizations will not expire after 7 days. If your app uses Sign in with Google to authenticate users then this exception also applies."
- Under "In Production": "Projects configured with a publishing status of In production are available to any user with a Google Account." And: "Your project's configuration may be subject to verification before its name and logo are displayed on an authorization screen or before it may request authorization of sensitive or restricted scopes."

**Verdict: confirmed.** Testing allows up to 100 test users.

**Also on the page, and it matters more:** Crux asks only for `openid email`, so the exception applies. In Testing, any Google account can sign in to Crux, with no test-user list, no warning and no 7-day expiry. Google's Testing status therefore does not limit who signs in during the trial. That limit rests only on Crux's own list (`accounts.md:9`, `accounts.md:11`), which the spec already has, so no spec line is wrong. The real-phone or before-opening tests should not count on Google's test-user list as a second guard. Moving to production (`quality-bar.md:237`) changes little for these scopes, but the page says Google may verify the project before it shows Crux's name and logo.

## 9. Turnstile in the LinkedIn and Facebook in-app browsers

**Spec says:**

- `quality-bar.md:139`: "**Before the trial:** Turnstile passes inside LinkedIn's and Facebook's apps on the Request access form. A trial link opened from the Gmail and Outlook apps lands signed in and stays so ([#717])."
- `accounts.md:32`: "A human check runs first, Cloudflare Turnstile. It is usually invisible, and shows at most a "Verify you are human" checkbox ([#674], [#717])."

The spec treats this as a test to run, not as a known fact.

**Sources:**

- "Supported browsers", `https://developers.cloudflare.com/cloudflare-challenges/reference/supported-browsers/` (read as its Markdown form). "Last updated Aug 18, 2026". Its description: "Browser compatibility for challenge pages, Turnstile, and JavaScript detections."
- "Mobile implementation", Turnstile docs, from `https://developers.cloudflare.com/turnstile/llms-full.txt`. "Last updated May 5, 2026".

**Page says:**

- Supported browsers, under "Limited browser support": "Custom or heavily modified browser engines and embedded browsers."
- Under "WebViews and in-app browsers": "Challenges may behave differently depending on embedded browser contexts." The bullets: "WebViews in mobile applications may have limited functionality compared to full browsers", "In-app browsers often have restricted JavaScript capabilities", "Email client preview windows typically cannot complete Interactive Challenges".
- Mobile implementation: "On mobile devices, Turnstile works in mobile browsers without additional configuration." For WebViews it lists requirements, including "JavaScript execution must be enabled.", "DOM storage API must be available." and "Access to `challenges.cloudflare.com`".

**Verdict: unverified.** No first-party Cloudflare page names LinkedIn or Facebook. The full Turnstile and Challenges docs (`llms-full.txt` for each) contain neither name. Cloudflare lists in-app browsers only as "limited" support. The spec's real-phone test is the only way to settle this, and the spec already plans it.

## 10. Zoho Mail Forever Free plan

**Spec says:**

- `operations.md:52`: "**From opening:** Zoho Mail's free plan if Zoho's processor agreement covers it, otherwise Google Workspace Business Starter, about USD 84 a year. Trial mail in the Gmail is moved or deleted at the switch."
- `operations.md:162`: "**Zoho's processor agreement:** whether it covers the free plan. Open on [#726] ([#717])."
- `quality-bar.md:235`: "The Crux email's switch: Zoho if its agreement covers the free plan, otherwise Workspace, with trial mail moved or deleted ([#717])".

**Sources:**

- "Zoho Mail Pricing | Compare Editions", `https://www.zoho.com/mail/zohomail-pricing.html`. No date shown.
- "Flexible subscription and extra storage options - Zoho Mail", `https://www.zoho.com/mail/help/adminconsole/subscription.html`. No date shown.

**Page says:**

- Pricing: "Forever Free Plan *", "Email hosting for one domain for up to 5 users 5 GB Mail storage per user IMAP/ POP/ Active Sync not included.", "*Available only in select data centers". The plan card adds "Up to 5 users From the 6th user all users enter a paid plan" and "Mobile app".
- Help: "Free plan: In Zoho Mail Free plan, you can add up to 5 users to an organization, and host one domain for free with web-only access. And each user gets up to 5 GB of free mail storage." And: "Note: Please note that our free plan is currently available only in selected data centers and may not be accessible in all regions."

**Verdict: partly.** The plan exists with one domain, up to 5 users and 5 GB each, web and app access only. But Zoho offers it only in some data centres and regions, and neither page names them. I found no Zoho page that does; `https://www.zoho.com/know-your-datacenter.html` loads its content with JavaScript and gave no text. So the spec's fallback rule tests only the agreement, not whether the plan is open to a Philippine sign-up.

**Fix:**

- `operations.md:52`: "Zoho Mail's free plan if Zoho offers it to Crux's account and Zoho's processor agreement covers it, otherwise Google Workspace Business Starter".
- `operations.md:162`: add "and whether the free plan is offered in the data centre a Philippine sign-up lands in".
- `quality-bar.md:235`: "Zoho if its free plan is offered to Crux and its agreement covers it, otherwise Workspace".
- Decisions touched: #717 (the Crux email at opening) and #726 (the open Zoho check). Part 2 of this research checks the Zoho agreement itself.

## 11. Google Workspace Business Starter: price in the Philippines

**Spec says:**

- `operations.md:52`: "otherwise Google Workspace Business Starter, about USD 84 a year."
- `hosting.md:36`: "Other hosting costs outside the AI budget are the domain (below), a minimum instance if the fallback is needed (below), alerting (see [`operations.md`](operations.md)), and Workspace if Zoho's agreement fails ([#675], [#716], [#717])."
- #717, "Left to other tickets": "Workspace (about USD 84 a year) from opening if Zoho's agreement fails."

**Source:** "Compare Flexible Pricing Plan Options | Google Workspace", `https://workspace.google.com/intl/en_ph/pricing.html`, which redirects to `https://workspace.google.com/pricing?hl=en_ph`. Read in a plain fetch and in a browser, where I switched the "Annual" toggle off to see the monthly price. No date shown.

**Page says:**

- "All plans billed monthly, all prices $USD".
- With the switch "Annual (Save 16% with 1 year commitment)" on: Starter "$6.30$7**", "/ user per month". The price details read "10% off", "10% Introductory", "Limited to 20 users", "$7.00", "$6.30", then "For all users", "$7.00", and "Price is per user/month and does not include tax".
- With the switch off: Starter "$7.56$8.40**", "/ user per month".
- "**Offer available to new Google Workspace customers only. This introductory price is only available for the first 20 users added, for 12 months. Standard pricing will apply to all users after 12 months."

**Verdict: confirmed, for the annual plan only.** USD 7 a user a month on a 1-year commitment is USD 84 a year before tax. The flexible plan is USD 8.40 a month, about USD 101 a year. A first-year discount of 10% applies to new customers. The page shows prices in USD for the `en_ph` locale.

**Suggested wording (optional):** `operations.md:52`: "about USD 84 a year on the annual plan, before tax". No decision changes.

## 12. Betterleaks: author, launch date, drop-in for gitleaks

**Spec says:**

- `quality-bar.md:144`: "Betterleaks stops a secret at commit on the owner's computer, and fails in CI ([#717])."
- `quality-bar.md:132`: "Push protection, Betterleaks and osv-scanner each fail on a planted case."
- `old-code.md:57` drops the old CI's gitleaks.

The spec states no author, no launch date and no drop-in claim. #717 rejected "Push protection alone; gitleaks."

**Sources:**

- The repository `betterleaks/betterleaks`: README on `main`, README at tags `v1.0.0` and `v1.10.0`, `docs/v2_migration.md`, `.pre-commit-hooks.yaml`, and GitHub's API for its releases, tags and contributors. Homepage field: `https://betterleaks.com`. License MIT.
- The repository `gitleaks/gitleaks`: README on `main`.

**Page says:**

- Author. README (`main` and `v1.10.0`): "Betterleaks is a configurable, fast, and thorough secrets scanner. It is maintained by the folks who made Gitleaks, including the original author." README at `v1.0.0`: "Wait wtf this isn't Gitleaks. You're right, it's not but it's built by the same people who maintained Gitleaks and ships with some cool new features." The README does not name the original author. GitHub's contributor lists show `zricethezav`, whose profile name is "Zachary Rice", as the top contributor to both repositories (278 commits to Betterleaks, 671 to gitleaks). No page I read says in words that he is the original author. The gitleaks README says: "Gitleaks is feature complete. I'm not merging new features into Gitleaks. Future releases will be security patches only. I'm shifting my focus to [Betterleaks](https://github.com/betterleaks/betterleaks)". The README is "supported by" Aikido Security.
- Launch date. The repository was created 2026-02-03. The tag `v1.0.0` points at a commit dated 2026-02-20, but it has no GitHub release. The first published release is `v1.0.1`, published 2026-02-20. The latest release is `v1.10.0`, published 2026-11-04; `v2.0.0-rc.7` was published the same day.
- Drop-in. No README or doc I read uses "drop-in" or "replacement". The `v1.0.0` README says: "Betterleaks supports both `betterleaks` and `gitleaks` naming conventions for backwards compatibility. The `betterleaks` variants take precedence." The `v1.10.0` README says: "Automatically loading `.betterleaks.toml` or `.gitleaks.toml` from a git or source target requires `--unsafe-auto-load-config`; only enable it for targets you trust." The v2 guide: "Rename `GITLEAKS_CONFIG` and `GITLEAKS_CONFIG_TOML` environment variables to their `BETTERLEAKS_*` equivalents. Neither `.betterleaks.toml` nor `.gitleaks.toml` is automatically loaded from a target or the working directory." And: "Legacy location fingerprints and `.gitleaksignore` discovery are not supported". And: "Existing `betterleaks:allow` and `gitleaks:allow` comments still work by default."
- Pre-commit. `.pre-commit-hooks.yaml` defines the hook `betterleaks` ("Detect hardcoded secrets using Betterleaks"), which scans `git diff --cached`.

**Verdict: no claim.** The spec states none of the three facts. Betterleaks comes from the gitleaks maintainers; the README does not name the original author. It launched in February 2026. v1.0.0 accepted gitleaks names for backwards compatibility. v1.10.0 no longer loads a `.gitleaks.toml` from a target without a flag, and the v2 release candidate drops gitleaks environment variables and `.gitleaksignore`. Nothing first-party calls it a drop-in. The spec's use, a pre-commit check plus a CI run, is supported by the hook file.

**Also on the page:** v2 is a release candidate that changes the CLI, the config fields, the JSON report and the ignore-file format. The v2 guide also says: "CLI scans detect secrets without provider requests by default. Use `-v` / `--validate` for validation". When the build pins a version, pin v1.x or v2 on purpose, and check whether validation (which sends a found secret to its provider) is on.
