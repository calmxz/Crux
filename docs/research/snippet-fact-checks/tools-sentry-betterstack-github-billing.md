# Tools: Sentry, Better Stack, GitHub and Cloud Billing

Part of [Spec facts that rested on search snippets](../snippet-fact-checks.md), checked on 2026-11-11 for #762.


Research for issue #762. Checked on **2026-11-11**. Each fact in section 3 of the snippet-only list is checked against the page that owns it. Quotes are copied from the page. Most facts fed #717, whose resolution and its later pointers are the decision record used here.

Several facts in this section are not stated in the spec or in the #717 resolution. They came from searches for providers the decision did not choose. For those nine rows (2, 4a, 6a to 6d, 7a, 7b and 12), the verdict is **no claim**, a label added to the five in the issue: the page was read and its content is recorded, but there is no spec sentence to confirm or correct. The original snippet claims are not reconstructed.

| # | Fact | Verdict | Source |
|---|---|---|---|
| 1a | Sentry: "Prevent Storing of IP Addresses", the browser setting and the location rule | partly | Sentry docs: JavaScript APIs, Server-Side Data Scrubbing, JavaScript and Python Data Collected |
| 1b | Sentry: push alerts in the Sentry mobile app | unverified | No Sentry docs page found. `getsentry/sentry-mobile` README |
| 2 | Better Stack free plan | no claim | Better Stack pricing |
| 3 | GitHub push protection on a free personal public repo | confirmed | GitHub Docs: About GitHub Advanced Security; Push protection; Secret scanning |
| 4a | Cloud Billing API: month-to-date cost | no claim | Cloud Billing API REST reference; Set up programmatic notifications |
| 4b | Billing export to a Singapore dataset has no backfill | confirmed | Set up Cloud Billing data export to BigQuery |
| 5 | Vertex AI (Agent Platform) abuse monitoring and its exception | confirmed (the #717 model list is out of date) | Abuse monitoring, Gemini Enterprise Agent Platform |
| 6a | Clerk data region | no claim | Clerk Data Processing Addendum |
| 6b | Auth0 data regions | no claim | Auth0 Docs: Auth0 Tenants |
| 6c | Stytch data region | no claim | Stytch Docs: Data compliance |
| 6d | Mailgun data regions | no claim | Mailgun Help Center article |
| 7a | Postmark sending rules and price | no claim | Postmark pricing; Message Streams |
| 7b | MailerSend sending rules and price | no claim | MailerSend pricing (FAQ data in the page) |
| 7c | Brevo sending rules and price | confirmed (the #717 rejection reason) | Brevo Help Center: limits of the Free plan |
| 7d | ZeptoMail sending rules and price | changed (now Zoho CPaaS) | Zoho CPaaS home and pricing |
| 8 | Google Auth Platform: 100 test users while in testing | confirmed, with an exception that covers Crux | Google Cloud Help: Manage App Audience |
| 9 | Turnstile in the LinkedIn and Facebook in-app browsers | unverified (no first-party page names either app) | Cloudflare: Supported browsers; Turnstile mobile implementation |
| 10 | Zoho Mail Forever Free plan | partly (the plan is offered only in some data centres) | Zoho Mail pricing; Zoho Mail subscription help |
| 11 | Google Workspace Business Starter price in the Philippines | confirmed (annual plan only) | Google Workspace pricing, `hl=en_ph` |
| 12 | Betterleaks: author, launch date, drop-in for gitleaks | no claim (the spec's use is supported) | `betterleaks/betterleaks` and `gitleaks/gitleaks` repositories |

## 1a. Sentry: IP addresses and location

**Spec says:**

- `operations.md:61`: "**At opening:** if only browser errors were hard to fix in the trial, Sentry is added for the browser. If Error Reporting failed more broadly, Sentry replaces it for both, with Error Reporting's notifications off. Either way Sentry collects no network addresses: its browser setting off, "Prevent Storing of IP Addresses" on, and a rule removing the location it derives ([#717])."
- `quality-bar.md:236`: "The Sentry judgement, with its address settings if added ([#717])".

#717 uses this to meet the no-address rule from #716: "Error tracker: must not collect network addresses (such tools do by default)".

**Sources:**

- "APIs | Sentry for JavaScript", `https://docs.sentry.io/platforms/javascript/configuration/apis/#setUser` (the identify-user URL redirects here). No date shown.
- "Server-Side Data Scrubbing | Sentry Docs", `https://docs.sentry.io/security-legal-pii/scrubbing/server-side-scrubbing/`. No date shown.
- "Data Collected | Sentry for JavaScript", `https://docs.sentry.io/platforms/javascript/data-management/data-collected/`. No date shown.
- "Data Collected | Sentry for Python", `https://docs.sentry.io/platforms/python/data-management/data-collected/`. No date shown.

**Page says:**

- JavaScript APIs: "To ensure your users' IP addresses are never stored in your event data, you can go to your project settings, click on "Security & Privacy" , and enable "Prevent Storing of IP Addresses" or use Sentry's server-side data scrubbing to remove $user.ip_address. Adding such a rule ultimately overrules any other logic."
- Server-Side Data Scrubbing: "Geographic information is extracted from the user's IP address. This occurs even if the setting to stop storing IP addresses is turned on." And: "To scrub geo data, it's necessary to add an Advanced Data Scrubbing rule. For example, the rule `[Remove] [Anything] from [$user.geo.**]` will remove all geo information."
- JavaScript Data Collected: "By default, the SDK sends the user's IP address. To disable it, set dataCollection: { userInfo: false }." And: "Even when this is disabled, IP addresses can still reach Sentry through collected HTTP headers, cookies, or query parameters (for example, the X-Forwarded-For header). Add these terms to the partially-matched deny lists for those categories so their values are filtered:" The example that follows sets `httpHeaders`, `cookies` and `urlQueryParams` each to `{ deny: [ "forwarded" , "-ip" , "remote-" , "via" , "-user" ] }`.
- Python Data Collected: "By default, the Sentry SDK doesn't send the user's IP address. Even if enabled, whether you're able to send the user's IP address or not, will depend on the integrations you enable in Sentry's SDK. Most integrations won't set the user's IP address at all." Then: "When using data_collection, the user's IP address is sent by default. Disable it by setting user_info to False." And: "Even when this is disabled, IP addresses can still reach Sentry through collected HTTP headers, cookies, or query parameters (for example, the X-Forwarded-For header)." Also: "By default, the Sentry SDK sends HTTP request headers to Sentry but filters out any headers that contain sensitive data."
- "Scrubbing Sensitive Data | Sentry for JavaScript" (`https://docs.sentry.io/platforms/javascript/data-management/sensitive-data/`) still names the older option: "User context → Automated behavior is controlled via sendDefaultPii."

**Verdict: partly.** The setting "Prevent Storing of IP Addresses" exists under the project's "Security & Privacy" settings, and the location rule is needed and works as the spec says. The browser setting is `dataCollection: { userInfo: false }` (or the older `sendDefaultPii`). But both Data Collected pages say an address can still reach Sentry in headers, cookies or query parameters, such as `X-Forwarded-For`, with the user setting off. The pages do not say whether "Prevent Storing of IP Addresses" also removes addresses held in those fields. So the pages do not show that the three settings the spec names make Sentry collect no network addresses. This matters for the backend case: `hosting.md:76` says Cloudflare adds "the visitor's network address" to each request.

**Fix:**

- `operations.md:61`: replace "its browser setting off, "Prevent Storing of IP Addresses" on, and a rule removing the location it derives" with "the SDK's user-info setting off in the browser and the backend, its header, cookie and query-parameter deny lists dropping forwarding and IP headers (such as `X-Forwarded-For`), "Prevent Storing of IP Addresses" on, and a rule removing the location it derives". The planted-error test in `quality-bar.md` can then check that a Sentry event holds no address in any field.
- `quality-bar.md:236`: no wording change. "Its address settings" now covers the deny lists too.
- Decision touched: #717 ("Either way Sentry collects no network addresses: its browser setting off, "Prevent Storing of IP Addresses" on, and a rule removing the location it derives"). Only the list of settings grows. The choice stands.

## 1b. Sentry: push alerts in the mobile app

**Spec says:** nothing. No spec file mentions a Sentry app or Sentry push alerts. Crux's pushes go to the Google Cloud app (`operations.md:59`, `operations.md:67`, `operations.md:73`). The #717 resolution does not mention a Sentry app either.

**Source and what I tried:**

- `https://docs.sentry.io/product/sentry-mobile-app/` returned HTTP 404.
- "Sentry Notifications" (`https://docs.sentry.io/product/notifications/`) lists workflow, deploy, spend and weekly-report notifications, sent "by email". It names no mobile app or push.
- A code search of `getsentry/sentry-docs` for "Sentry mobile app" found nothing.
- The repository `getsentry/sentry-mobile` (description "Sentry Mobile App", last push 2026-10-27) has a README that says: "Note: Please be aware that this project is currently not actively maintained. PRs will not be merged." and "A flutter application with the focus on Release Health". Its `pubspec.yaml` lists no messaging or notification package.
- The Play Store page for its app ID `io.sentry.mobile.app` returned HTTP 404.

**Verdict: unverified.** I found no first-party page that says whether Sentry pushes alerts to a phone app. The evidence above does not prove there is no such app. The spec does not depend on it.

## 2. Better Stack free plan

**Spec says:** nothing. Better Stack is not named in the spec or the #717 resolution. #717 chose Monitoring uptime checks and rejected "UptimeRobot; GitHub's scheduled jobs".

**Source:** "Pricing | Better Stack", `https://betterstack.com/pricing`. No date shown.

**Page says:** the free card reads, line by line: "Free for personal projects", "$0", "per month", "10 monitors & heartbeats, 1 status page", "Slack & e-mail alerts", "100,000 exceptions per month", "5,000 session replays", "3 GB logs retained for 3 days", "3 GB traces retained for 3 days", "30 GB metrics", "3 GB web events retained for 3 days".

The uptime feature list also shows "Up to 30 seconds check frequency" and "Push notifications", but that list belongs to the paid monitor add-on ("Additional 50 monitors", "$25 per month"). The free card does not list push notifications or a check interval.

**Verdict: no claim.** The free card names only Slack and email alerts. It does not say "commercial use"; it says "Free for personal projects".

## 3. GitHub push protection on a free personal repo

**Spec says:**

- `quality-bar.md:144`: "GitHub push protection refuses known key formats at GitHub. Betterleaks stops a secret at commit on the owner's computer, and fails in CI ([#717])."
- `quality-bar.md:214`: "Push protection on ([#717])", a before-the-trial check.
- `quality-bar.md:132`: "Push protection, Betterleaks and osv-scanner each fail on a planted case."

The repo `calmxz/Crux` is public and owned by a personal account. GitHub's API for it reports `"secret_scanning_push_protection":{"status":"enabled"}`.

**Sources:**

- "About GitHub Advanced Security", `https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security`.
- "Push protection - GitHub Docs", `https://docs.github.com/en/code-security/concepts/secret-security/push-protection` (redirected from `/secret-scanning/introduction/about-push-protection`).
- "Secret scanning", `https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning`.

No page shows a date.

**Page says:**

- About GitHub Advanced Security: "Some features are also available for free for public repositories on GitHub.com." Its table "summarizes the availability of GitHub Secret Protection features for public and private repositories". The row "Push protection" reads Yes for "Public repository without GitHub Secret Protection", No for "Private repository without GitHub Secret Protection", and Yes for "Public or private repository with GitHub Secret Protection".
- Push protection: "You can enable push protection for repositories at the repository, organization, or enterprise level. This form of push protection: Requires GitHub Secret Protection to be enabled". And for users: "Push protection for users is only available on GitHub.com, and is specific to your GitHub account. This form of push protection:", followed by the bullets "Is enabled by default" and "Stops you from pushing secrets to public repositories on GitHub".
- Secret scanning: "Public repositories: Secret scanning runs automatically for free." The next lines are "Organization-owned private and internal repositories: Available with GitHub Secret Protection enabled on GitHub Team or GitHub Enterprise Cloud." and "User-owned repositories: Available on GitHub Enterprise Cloud with Enterprise Managed Users."

**Verdict: confirmed.** Push protection is free for a public repository. Two lines read as contradictions. "Requires GitHub Secret Protection" describes repository-level push protection in general, and the "User-owned repositories" line lists the Enterprise route for private user repositories. The table splits rows by public and private, and its public row reads Yes without Secret Protection. The Crux repo already has push protection on.

**Also on the page:** it is free only because the repo is public. If the repo became private on a free personal account, the table's "Private repository without GitHub Secret Protection" row reads No, and Secret Protection needs GitHub Team or Enterprise.

## 4a. Cloud Billing API: month-to-date cost

**Spec says:** nothing about the Billing API. The spec reads the bill from the billing export (`operations.md:114`, quoted in 4b). #717 rejected "A budget messaging Crux for the bill."

**Sources:**

- "Cloud Billing API | Google Cloud Documentation", `https://docs.cloud.google.com/billing/docs/reference/rest`. "Last updated 2025-09-04 UTC."
- "Set up programmatic notifications | Cloud Billing", `https://docs.cloud.google.com/billing/docs/how-to/budgets-programmatic-notifications`. "Last updated 2026-11-10 UTC."

**Page says:**

- The API "Allows developers to manage billing for their Google Cloud Platform projects programmatically." Its resources are `v1.billingAccounts`, `v1.billingAccounts.projects`, `v1.billingAccounts.subAccounts`, `v1.organizations.billingAccounts`, `v1.projects`, `v1.services` and `v1.services.skus`. The methods create, get, list, move and patch billing accounts, read and set a project's billing info, and list services and SKUs ("Lists all publicly available SKUs for a given cloud service."). No method returns costs.
- A budget notification carries `costAmount`: "The amount of costs accrued. The type of costs tracked depends on budget filters & settings." And `costIntervalStart`: "The start of the budget alert period. `costAmount` includes costs for usage starting at this time. This is the first day of the budget's time period (month, quarter, year, or a custom date range) during which the budget usage occurred."

**Verdict: no claim.** The Cloud Billing API gives no cost figure. Of the pages I read, only budget notifications carry a month-to-date figure, and #717 rejected that route, so the decision's choice of the export stands.

## 4b. The billing export has no backfill

**Spec says:**

- `operations.md:114`: "Google's billing export goes to a BigQuery dataset in Singapore, read by the daily job through a read-only role. It is turned on before the first Gemini call, since it has no backfill ([#717])."
- `quality-bar.md:212`: "The billing export on, before the first Gemini call in the Crux project ([#717])".

**Source:** "Set up Cloud Billing data export to BigQuery", `https://docs.cloud.google.com/billing/docs/how-to/export-data-bigquery-setup`. "Last updated 2026-11-10 UTC."

**Page says:**

- "If you configure the dataset to use a multi-region location (EU or US), the dataset includes Google Cloud billing data incurred from the start of the previous month from when you first enabled the export, unless you are re-enabling the export."
- "If your dataset is configured to use a supported region location, your FOCUS usage cost data, standard usage cost data, and detailed usage cost data only reflect Google Cloud billing data incurred starting from the date you enabled Cloud Billing export, and after. That is, Google Cloud billing data is not added retroactively for non-multi-region dataset locations, so you won't see Cloud Billing data from before you enable export."
- The supported Asia Pacific regions include "asia-southeast1 (Singapore)".
- "When you first enable the FOCUS, standard or detailed usage cost export to BigQuery, it might take a few hours to start seeing Google Cloud cost data propagate to your BigQuery dataset."

**Verdict: confirmed.** With a Singapore dataset, the export has no backfill. A US or EU multi-region dataset would backfill, so "no backfill" holds because of the Singapore choice.
