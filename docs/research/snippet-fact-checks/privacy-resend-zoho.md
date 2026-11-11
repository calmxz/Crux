# Privacy promises: Resend and Zoho

Part of [Spec facts that rested on search snippets](../snippet-fact-checks.md), checked on 2026-11-11 for #762.

## 3. Resend keeps sent emails 30 days

**Spec says:**

- `operations.md:11`: "Sent emails stay in Resend's log for up to 30 days (see [`privacy.md`](privacy.md)) ([#717])."
- `privacy.md:99`: "| Sent emails, in Resend's log | Up to 30 days ([#717]) |"
- `privacy.md:155`: "| Resend | Crux's email | Covers all plans. Processing mainly in the US, with sent emails in its log up to 30 days ([#717]) |"
- `trial.md:123`, in the Trial Privacy Notice: ""Your invite is kept in our email provider's log for up to 30 days.""

Resend's plan and limits appear at `operations.md:9`. The other Resend lines do not use the 30 days. The "1 day on Free" came from a third-party review that #717's session treated as the outlier. It said one day on Free and three days on Pro.

**Source:**

- Resend, "Pricing", `https://resend.com/pricing`. No date shown. Also its Markdown copy for agents, `https://resend.com/pricing.md`, which gives the same table.
- Resend, "Data Processing Addendum", `https://resend.com/legal/dpa`. "Last update: December 31st, 2025".
- Also searched for a retention or erasure rule, with none found: the Resend docs index `https://resend.com/docs/llms.txt`, and the dashboard docs for emails (`https://resend.com/docs/dashboard/emails/introduction.md`) and logs (`https://resend.com/docs/dashboard/logs/introduction.md`).

**Page says:**

- Pricing, the feature table for Free, Pro, Scale and Enterprise. The row is "Data retention", with the description "Search your emails and logs to debug or troubleshoot deliverability issues.", and the values "30 days", "30 days", "30 days" and "Flexible".
- Pricing, the Free plan summary under "Transactional plans": "100 emails a day, 3 domains, 3 inboxes, Ticket support, 10,000 automation runs, 30-day data retention."
- DPA, Exhibit A, under "The period for which the personal data will be retained": "We process personal data on behalf of the Customer for as long as the Agreement is active. When the Customer terminates their use of the Services, we delete their user/customer data within 90 days of the account termination."
- DPA, 2.4: "Following completion of the Services, at Customer's choice, Company shall return or delete Customer's Personal Data, unless further storage of such Personal Data is required or authorized by applicable law."

**Verdict: partly.**

- The 30 days on Free is right, and no Resend page shows 1 day.
- The pricing page describes 30 days in which emails and logs can be searched. No Resend page I read says that a sent email is erased after 30 days. The DPA's only stated limit is deletion within 90 days after the account ends. "Up to 30 days" therefore promises more than Resend states.

**Fix:**

- `operations.md:11`: "Resend shows sent emails in its log for 30 days. Its agreement deletes them within 90 days after Crux's Resend account ends, and states no earlier date (see [`privacy.md`](privacy.md)) ([#717])."
- `privacy.md:99`: "| Sent emails, at Resend | Shown in its log for 30 days. Resend's agreement deletes them within 90 days after Crux's account with Resend ends, and states no earlier date ([#717]) |"
- `privacy.md:155`: "… Processing mainly in the US. Sent emails shown in its log for 30 days, and deleted within 90 days after the account ends ([#717]) |"
- `trial.md:123`: ""Your invite stays in our email provider's log for 30 days. The provider may keep it until we close our account with them, and up to 90 days after.""
- Another option is to ask Resend whether sent emails are erased after the 30 days. If Resend confirms it in writing, the current wording can stay, with that source.
- Decision this touches: #717. It accepted the invite sitting in Resend's log and disclosed it: "Crux keeps no record of who got which link, though Resend's log holds each invite up to 30 days." The same line went into #677 by pointer. If the email can stay longer, the owner should check whether that tradeoff still holds.

**Also on the pages:**

- DPA preamble: "This Addendum shall become legally binding upon Customer entering into the Agreement or upon execution of this Addendum." It names no plan. This backs "Covers all plans" at `privacy.md:155`.
- DPA 6.1: "Customer acknowledges that Company's primary processing operations take place in the United States". This backs "Processing mainly in the US".

## 4. Zoho's DPA and the free plan

**Spec says:** the spec does not claim that the DPA covers the free plan. It keeps the question open:

- `operations.md:52`: "**From opening:** Zoho Mail's free plan if Zoho's processor agreement covers it, otherwise Google Workspace Business Starter, about USD 84 a year."
- `operations.md:162`: "**Zoho's processor agreement:** whether it covers the free plan. Open on [#726] ([#717])."
- `quality-bar.md:235`: "The Crux email's switch: Zoho if its agreement covers the free plan, otherwise Workspace, with trial mail moved or deleted ([#717])".
- `hosting.md:36`, `privacy.md:156` and `README.md:124` also treat it as open.

#726 recorded on 2026-11-02: "Not stated: no Zoho page says the agreement covers or excludes the free plan. Zoho signs one on request per organization."

**Source:**

- Zoho Privacy Policy, `https://www.zoho.com/privacy.html`, "Last updated on: 22nd Dec 2025".
- Zoho Accounts help, "Privacy", `https://help.zoho.com/portal/en/kb/accounts/manage-your-zoho-account/articles/privacy`, "Updated: 1 year ago". It renders only with JavaScript, so I read it in a browser.
- Zoho, "GDPR", `https://www.zoho.com/gdpr.html`. No date shown.
- Zoho Terms of Service, `https://www.zoho.com/terms.html`, "Last updated on: 2nd March 2022".
- Zoho Mail pricing, `https://www.zoho.com/mail/zohomail-pricing.html`. No date shown.
- Also read, with nothing on the DPA and plans: Zoho Mail, "GDPR Readiness" (`https://www.zoho.com/mail/gdpr.html`), and Zoho's sub-processor page (`https://www.zoho.com/privacy/sub-processors.html`). The sub-processor page loads its list with JavaScript, and a plain fetch got only its header.

**Page says:**

- Privacy Policy: "To enable you to be compliant with your data protection obligations , we are prepared to sign an appropriate Data Processing Addendum (DPA). You can request a DPA from Zoho by completing this form . Once we get your request, we'll forward the DPA to you for your signature."
- Accounts help: "A user signs in to their Zoho account to initiate the DPA. The DPA form can be found under the Privacy tab." Also "Note: Zoho's legal team reserves the right to reject a DPA request." And "Only the administrator of an organization can initiate a DPA request."
- GDPR page: "If you are the organization administrator and would like to sign a DPA with us, please drop an email to legal@zohocorp.com to request a copy of the Data Processing Addendum mentioning in which Data Center you've signed up for your Zoho account."
- Terms of Service: no mention of a DPA.
- Mail pricing: "Forever Free Plan *" with "Email hosting for one domain for up to 5 users", and "*Available only in select data centers".

**Verdict: unverified.** No page I could open says whether the DPA covers the free plan, and none excludes it. The DPA text sits behind a Zoho sign-in, as #726 found.

**Fix:** none. The spec already keeps the switch conditional. The check stays the one in #726: before opening, create the free organization, request the DPA from its Privacy tab, and see whether Zoho approves. The GDPR page asks for the data center in the request, and the free plan exists only in some data centers. So the request should name the data center the free organization uses.
