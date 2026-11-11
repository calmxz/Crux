# Spec facts that rested on search snippets

Checked on 2026-11-11 for [#762](https://github.com/calmxz/Crux/issues/762). About 60 facts in the spec came from web-search result snippets, and nobody opened the page that owns each one. This note checks each fact against that page. Each check quotes the spec with `file:line`, names the source, quotes the page word for word, and gives a verdict. Line numbers refer to `docs/spec/` at commit `d581e86`.

Verdicts:

- **confirmed:** the page says what the spec says.
- **partly:** some parts match and some do not.
- **changed:** the page was updated, and the spec or a decision reflects an older version.
- **unverified:** the owning page could not be opened, or no first-party page states the fact. No fact was settled from a snippet or from memory.
- **no claim:** neither the spec nor the decision states the fact. The page was read and is recorded, with nothing to confirm or correct.

## Summary

| Part | Rows | Confirmed | Partly | Changed | Unverified | No claim |
|---|---|---|---|---|---|---|
| 1. Law and safety | 9 | 5 | 3 | 0 | 1 | 0 |
| 2. Privacy promises | 10 | 8 | 1 | 0 | 1 | 0 |
| 3. Sign-in, email and operations tools | 20 | 6 | 2 | 1 | 2 | 9 |
| 4. Spending and hosting | 15 | 10 | 3 | 1 | 1 | 0 |
| **Total** | **54** | **29** | **9** | **2** | **5** | **9** |

No fact is wrong outright. Nine are only partly right, and most of those need a spec fix.

## Proposed spec fixes

Each fix is a proposal for the owner. None is applied here.

| # | Fix | Spec lines | Decisions touched |
|---|---|---|---|
| 1 | Name RA 11930 alone: it repealed RA 9775 in 2022 (Sec. 44) | `misuse.md:105` | #743 |
| 2 | NPC registration: fees depend on the tier (PHP 500 to 2,500, renewal 350 to 1,000); the NPCRS portal is suspended "until further notice"; the 20 days count from the start of the system; the application is notarized | `trial.md:160` | #677, #722 |
| 3 | NPC advisory opinion: PHP 7,500 plus PHP 75, paid in advance; "anticipatory and speculative" requests are turned away | `trial.md:151` | #677 |
| 4 | Resend: the 30 days is a search and log window, not a stated erasure date; the DPA deletes customer data within 90 days of account termination. Reword, or ask Resend to confirm erasure in writing | `operations.md:11`, `privacy.md:99`, `privacy.md:155`, `trial.md:123` | #717 |
| 5 | Sentry: addresses still arrive through headers such as `X-Forwarded-For`; add the SDK deny lists for headers, cookies and query parameters | `operations.md:61` | #717 |
| 6 | Zoho Mail Free is "available only in select data centers"; make the fallback conditional on Zoho offering it to Crux | `operations.md:52`, `operations.md:162`, `quality-bar.md:235` | #717, #726 |
| 7 | GCS signed URLs: a link signed with a system-managed key lasts at most 12 hours, so the 7-day copy-of-data link fails under the no-stored-keys rule. Options: a link to Crux that hands out fresh short links, one stored signing key, or a 12-hour link | `operations.md:43`, `privacy.md:55`, `privacy.md:85`, `privacy.md:86`, `privacy.md:122`, `privacy.md:135`, `account-screens.md:103`, `quality-bar.md:90` | #735, #716 |
| 8 | Turnstile: "usually invisible" and "at most a checkbox" describe two different widget modes; pick one. Invisible mode requires a reference to Cloudflare's Turnstile Privacy Addendum | `accounts.md:32`, `privacy.md:153` | #674 to #676 |
| 9 | Cloud Monitoring: the pricing page's Example 7 settles that a log-based rule is billed as a metric reference; drop "reads it as" | `operations.md:161` | #726 |

## Open questions for the owner

- **RA 11930 duties (#743).** If Crux counts as an internet intermediary under Sec. 3(p), Sec. 9(a) requires a takedown within 24 hours of notice, a report to the DOJ within 3 days, and keeping data for 6 months (content data for 1 year). The spec makes reporting the owner's choice (`misuse.md:70`) and erases a sealed session with its account (`misuse.md:69`). Fix 1 only renames the law; this question stays open for the lawyer before the trial.
- **NPC systems down.** The NPCRS and the breach notification system are both unavailable. The NPC homepage gives an email route for breach notices. This bears on `privacy.md:126` and `quality-bar.md:156`.

## Still unverified

| Fact | Why | Next step |
|---|---|---|
| Crisis line 1553 (NCMH) | ncmh.gov.ph sits behind a human check. The only official copy read is a DOH release from 2020 | A person opens ncmh.gov.ph before the trial, as `quality-bar.md:217` already requires |
| The Zoho DPA covers the free plan | The DPA text needs a Zoho sign-in | Already open in the spec; ask Zoho |
| Sentry mobile app push alerts | No current docs page; the app is "not actively maintained" | None: the spec does not rely on it |
| Turnstile in the LinkedIn and Facebook in-app browsers | No first-party page names either app | The real-phone test the spec already requires |
| `intent://` opens the system browser | No first-party page covers LinkedIn or Facebook | The same real-phone test |

## Records out of date, with no spec change

- #717 lists only Gemini 4 Argon Cyber Permissive in the Frontier abuse-monitoring category; the page now also lists Gemini 4 Carbon and Gemini 4 Carbon for cyber.
- #679 rejected the Interactions API partly as a preview; Google now calls it generally available as of June 2026.
- #679 called the Developer API's prepaid credit "the only hard money stop"; the Gemini API now also has experimental project spend caps. The rejection rests on the 55-day retention, so it stands.
- #738: Playwright 1.65.0 (2026-11-05) bundles Chromium 158.0.8127.18, so the upgrade path is open. Three of its four CVEs, not one, describe code running outside the sandbox.
- The fact list behind this ticket cited #708, #712 and #718, which are glossary PRs. The decisions that used the facts are #681, #677, #722 and #679.

## The checks

Each file quotes the spec, the source and the page for every fact it covers. The first file of each part holds that part's summary table.

**1. Law and safety**

- [RA 11930, the crisis line and NPC registration](snippet-fact-checks/law-ra11930-crisis-line-npc-registration.md): 1. RA 11930: duties of internet intermediaries; 2. Crisis line 1553 (NCMH) runs 24/7; 3. NPC registration fees and the NPCRS
- [Profiling, advisory opinions and age rules](snippet-fact-checks/law-profiling-advisory-opinion-ages.md): 4. NPC Circular 2022-04: "profiling"; 5. The route to an NPC advisory opinion; 6. Age rules

**2. Privacy promises**

- [Delete windows and Google's stored conversations](snippet-fact-checks/privacy-delete-windows-google-storage.md): 1. Delete and restore windows at other apps; 2. Stored conversations at Google: 7 days and 55 days
- [Resend and Zoho](snippet-fact-checks/privacy-resend-zoho.md): 3. Resend keeps sent emails 30 days; 4. Zoho's DPA and the free plan

**3. Sign-in, email and operations tools**

- [Sentry, Better Stack, GitHub and Cloud Billing](snippet-fact-checks/tools-sentry-betterstack-github-billing.md): 1a. Sentry: IP addresses and location; 1b. Sentry: push alerts in the mobile app; 2. Better Stack free plan; 3. GitHub push protection on a free personal repo; 4a. Cloud Billing API: month-to-date cost; 4b. The billing export has no backfill
- [Abuse monitoring, data regions and email providers](snippet-fact-checks/tools-abuse-monitoring-regions-email.md): 5. Vertex AI abuse monitoring and its exception; 6. Data regions at Clerk, Auth0, Stytch and Mailgun; 7. Sending rules and prices at Postmark, MailerSend, Brevo and ZeptoMail
- [Google sign-in testing, Turnstile, Zoho Mail, Workspace and Betterleaks](snippet-fact-checks/tools-google-auth-turnstile-zoho-workspace-betterleaks.md): 8. Google Auth Platform: 100 test users while in testing; 9. Turnstile in the LinkedIn and Facebook in-app browsers; 10. Zoho Mail Forever Free plan; 11. Google Workspace Business Starter: price in the Philippines; 12. Betterleaks: author, launch date, drop-in for gitleaks

**4. Spending and hosting**

- [Provider spend caps and Cloud Monitoring](snippet-fact-checks/spending-caps-monitoring.md): 1. Spend caps at the providers; 2. Cloud Monitoring alerting
- [Signed URLs, Resend size and in-app browsers](snippet-fact-checks/spending-signed-urls-resend-in-app-sign-in.md): 3. A GCS V4 signed URL lasts 7 days at most; 4. Resend allows 40 MB per email; 5. Google sign-in in the LinkedIn and Facebook in-app browsers; 6. An `intent://` link opens the system browser
- [Turnstile, rate limits and Playwright](snippet-fact-checks/spending-turnstile-rate-limits-playwright.md): 7. Turnstile and Cloudflare's free rate limiting; 8. Outside the spec: #738
