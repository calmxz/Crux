# Tools: abuse monitoring, data regions and email providers

Part of [Spec facts that rested on search snippets](../snippet-fact-checks.md), checked on 2026-11-11 for #762.

## 5. Vertex AI abuse monitoring and its exception

**Spec says:**

- `privacy.md:102`, the row "Google's copy": "Only prompts its filters flag, up to 90 days, with no opt-out. Google staff may read flagged content, and it is never used for training. A short-term cache of at most 24 hours. Deleting in Crux cannot reach these ([#677], [#679], [#717])."

#717 says: "Gemini 3.5 Flash-Lite and 3.8 Flash fall in the standard abuse-monitoring category, inferred from Google's list (only Gemini 4 Argon Cyber Permissive is in the Frontier category): only prompts the safety checks flag are kept, up to 90 days, and the current page offers no opt-out."

**Source:** "Abuse monitoring | Gemini Enterprise Agent Platform", `https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/abuse-monitoring` (redirected from `/vertex-ai/generative-ai/docs/learn/abuse-monitoring`). "Last updated 2026-11-10 UTC."

**Page says:**

- Under "Google models not designated as "Google Frontier Models" or "Advanced AI"": "Prompt logging and human review: If automated safety classifiers detect suspicious activity that requires further investigation into whether a customer has violated our policies, then Google may log customer prompts solely for the purpose of examining whether a violation of the AUP or Prohibited Use Policy has occurred. This data won't be used to train or fine-tune any AI/ML models. This data is stored securely for up to 90 days in the same region or multi-region selected by the customer for their project".
- "Action: Authorized Google employees may assess the flagged prompts and may reach out to the customer for clarification."
- The exception: "Customers in scope: Only customers whose use of Google Cloud is governed by the Google Cloud Platform Terms of Service. This means that customers with a Google Cloud Master Agreement are exempt from prompt logging for this abuse monitoring by default."
- Under "Google Frontier Models": "Models in scope: Gemini 4 Carbon (Google Frontier Model), Gemini 4 Carbon for cyber (Google Frontier Cyber Model), Gemini 4 Argon Cyber Permissive (Google Frontier Cyber Model)". These logs keep "customer prompts and responses" "for up to 30 days".

**Verdict: confirmed** for the spec's 90 days, flagged prompts only, staff review, no training and no opt-out. The only exception the page names is a Google Cloud Master Agreement. The spec names Google Cloud's data processing addendum as the agreement (`privacy.md:152`) and no Master Agreement, so Crux falls under the online terms and is in scope. Neither 3.5 Flash-Lite nor 3.8 Flash is on the Frontier list. This page does not cover the "short-term cache of at most 24 hours" in the same row; I did not check it.

**Changed in #717 only:** the Frontier list now has three models, not one. #717's parenthesis "only Gemini 4 Argon Cyber Permissive is in the Frontier category" is out of date. No spec line repeats it, so no spec fix is needed.

**Also on the page:**

- `ai-layer.md:34` names a possible grader move to "Gemini 4 Argon". The Frontier list names "Gemini 4 Argon Cyber Permissive", not plain Gemini 4 Argon, so plain Argon is not on the list today. That move should recheck this page, since Google adds Gemini 4 models to the list.
- The 90-day logs sit "in the same region or multi-region selected by the customer". Crux calls the global address (`ai-layer.md:9`), and the page does not say where flagged prompts sit for a global call.

## 6. Data regions at Clerk, Auth0, Stytch and Mailgun

**Spec says:** nothing about any of the four regions. #717 rejected "a hosted sign-in service such as Clerk or Auth0 (sees the learner's address, one more processor)". Stytch and Mailgun are not named in the spec or the resolution.

### 6a. Clerk

**Source:** "Data Processing Addendum", `https://clerk.com/legal/dpa`. "Last updated: November 26, 2024".

**Page says:** "4.4 Clerk may store and process Customer Personal Data anywhere Clerk or its Sub-processors maintain facilities, subject to clause 5 of this DPA." The DPF note says personal data from the EU, Switzerland and the UK "can be safely transferred from those locations by Clerk customers to Clerk in the United States (U.S.)."

**Verdict: no claim.** The DPA names no hosting region and offers no region choice. It names transfers to Clerk in the United States.

### 6b. Auth0

**Source:** "Auth0 Tenants - Auth0 Docs", `https://auth0.com/docs/get-started/auth0-overview/create-tenants`.

**Page says:** "We support the following locality values for the public cloud deployment option". The table lists Australia (AU), Canada (CA), Europe (EU; EU, EU-2), Japan (JP), United Kingdom (UK) and United States of America (US; US, US-3, US-4, US-5). "Tenant environments cannot be chosen manually, but localities based on the selected region may be specified, which control the assigned tenant domain and the region where your data will be hosted."

**Verdict: no claim.** Six regions, none in Southeast Asia.

### 6c. Stytch

**Source:** Stytch Docs, "Data compliance", `https://stytch.com/docs/resources/policies/security-and-trust/compliance/data-compliance.md` (the Markdown form listed in Stytch's `llms.txt`; the HTML docs URLs I tried redirect to a sign-in page).

**Page says:** "Because Stytch operates exclusively out of U.S. servers, achieving this level of rigid localization with their service is not possible."

**Verdict: no claim.** US only. The page links its DPA to Twilio's data protection addendum.

### 6d. Mailgun

**Source:** Mailgun Help Center, "Can I transfer my domain to another region (US to EU, EU to US)?", `https://help.mailgun.com/hc/en-us/articles/360007512013-Can-I-transfer-my-domain-to-another-region-US-to-EU-EU-to-US`. I did not find Mailgun's API reference page on regions; its URL returned 404.

**Page says:** "Yes, since there is not a way to change the region of a domain once it has been created (due to possible GDPR implications), there is a process that can allow you to migrate the domain (and most of its properties) from one region to another." And: "By far, the most common migration we see customers utilize is moving their domain from the US to the EU region."

**Verdict: no claim.** The article shows a US region and an EU region, chosen per domain and fixed at creation. It does not list all regions.

## 7. Sending rules and prices at Postmark, MailerSend, Brevo and ZeptoMail

**Spec says:** nothing about these four. The spec uses Resend (`operations.md:9`: "Resend Free sends Crux's email from the domain: 100 a day and 3,000 a month, from Tokyo's sending region."). #717 rejected "Brevo (its footer on every email), Amazon SES (a new account and test mode)".

### 7a. Postmark

**Sources:** "Postmark Pricing and Free Trial", `https://postmarkapp.com/pricing`; "Message Streams", `https://postmarkapp.com/message-streams`.

**Page says:**

- Pricing: "Free", "$0.00/mo", "Test your integration with 100 emails/month", "100 emails/month.", "No overages allowed in this plan." The next plan is "Basic", "$15.00/mo", "Starting at 10,000 emails/month."
- Message Streams: "Postmark is no longer for transactional email only." In the table "Transactional or broadcast?", the "Examples" row reads "Password resets, receipts, invitations, comment notifications" for Transactional and "Product announcements, release notes, daily digests, ToS updates" for Broadcast. The "Opt-out link" row reads "Not required" for Transactional and "Required" for Broadcast.

**Verdict: no claim.** The free plan is 100 emails a month, below Crux's 100 a day.

### 7b. MailerSend

**Source:** "Pricing", `https://www.mailersend.com/pricing`. The plan cards render with JavaScript. The text below is from the FAQ data and tooltips in the page's HTML, which I read in the downloaded file.

**Page says:** "Once your account is approved, you can subscribe to a Free plan. This plan lets you send up to 500 emails per month for free!Simply go to the Plan and billing page and enter your organization’s address and credit card information to complete your subscription. The billing period starts right after you enter your credit card details.The number of emails that you have sent automatically resets every 30 days." The free tooltip reads "500 emails/month and other limits apply". The trial includes "500 emails/month, 100 API requests/day, and 1 day of Log retention".

**Verdict: no claim.** The free plan needs account approval and a credit card.

### 7c. Brevo

**Source:** "FAQs - What are the limits of the Free plan?", `https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan`.

**Page says:** "The Free plan includes 300 email sends per day. The daily limit resets every day, and unused emails do not roll over to the next day." The question "Can I remove the Sent with Brevo sticker on emails with the Free plan?" has the answer "No. Emails sent from the Free plan always include the Sent with Brevo sticker." To remove it, the page says to "upgrade to a Starter (with the Remove Brevo branding add-on), Standard, Professional, or Enterprise plan."

**Verdict: confirmed** for #717's rejection reason ("its footer on every email"). The page calls it a sticker, not a footer.

### 7d. ZeptoMail

**Sources:** `https://www.zoho.com/zeptomail/` now redirects to "Zoho CPaaS", `https://www.zoho.com/cpaas/`. `https://www.zoho.com/zeptomail/pricing.html` redirects to "Credit-Based SMS, WhatsApp, Voice, and Email | Zoho CPaaS Pricing", `https://www.zoho.com/cpaas/pricing.html`. I read the prices in a browser, because they fill in with JavaScript.

**Page says:**

- Home: "The email channel—ZeptoMail—is optimized for one thing: getting your transactional emails to the inbox, fast. Built exclusively for transactional email, our infrastructure is isolated from marketing traffic which means your users receive critical emails like verification codes and password resets instantly, without delays."
- Pricing: "Email (Available across all regions)", "US$2.50", "per email credit", "10,000 emails per credit", "Email credits valid for 6 months", "Each email to a recipient counts as one email", "First credit is free".

**Verdict: changed.** ZeptoMail is now the email channel of Zoho CPaaS, and its own URLs redirect there. It stays transactional-only and credit-priced. No spec line needs a fix.
