# The monthly API credit for Max, Ultra and Team plans: what its terms allow

Read on **2026-11-18** from Anthropic's own pages, with no sign-in. This builds on item 1 of `claude-anthropic-api-account.md`. The source list [S1] to [S34] is in `claude-anthropic-api.md`; new sources [S35] to [S40] are at the end of this file.

Quotes are exact, with straight quote marks. A line marked **Reading** is this file's interpretation, not Anthropic's words.

## Answer

- **Which terms:** the "program terms" are the Supplemental Credit Terms [S4][S5][S35]. They form part of the Commercial Terms, which govern API use [S2][S36].
- **A service for other people:** allowed by the Commercial Terms [S2]. The credit terms add no limit on end users. They bar transfer or sale of the credit itself [S4].
- **Products:** covers the API, Message Batches API, Agent SDK, Playground and Managed Agents. Claude Code is not covered [S5][S35].
- **Expiry and order:** expires at the end of each billing cycle, with no rollover. It is spent before bought credits [S5][S35].
- **Plan lapse:** new credits stop when the plan ends. Credits already granted last until they expire [S5][S35].
- **Credit runs out:** bought credits take over if any exist. With none, requests stop. The plan is never charged [S5][S35].
- **Other:** the linked organization moves to at least the Start tier. Credit-paid usage counts toward the monthly spend cap [S5].

## 1. Which terms govern the credit and its usage

- **The program terms are the Credit Terms.** The claim step says: "accept the [program terms](https://www.anthropic.com/legal/credit-terms) by linking" [S5].
- The Help Center names them: "Review the Supplemental Credit Terms, then Link organization" [S35].
- That is the page already read as [S4], effective 2024-03-04. No other credit program terms were found on the pages read.
- **The Credit Terms attach to an agreement.** They "form part of the agreement you or the organization ... have with Anthropic that links to or otherwise references these Credit Terms" [S4].
- The Commercial Terms reference them: credits "are subject to Anthropic's Supplemental Credits Terms" (H.1) [S2]. The Consumer Terms never mention credits [S36].
- **Reading:** so the agreement the Credit Terms form part of is the Commercial Terms.
- **API usage is under the Commercial Terms, not the Consumer Terms.** "Our Commercial Terms of Service govern your use of any Anthropic API key, the Anthropic Console" [S36].
- **The plan itself.** "Our consumer offerings (e.g., Claude.ai) are governed by our Consumer Terms of Service instead" [S2].
- **Reading:** that covers a Max or Ultra plan. Whether a Team plan is a consumer offering was not checked.
- **The amount does not prove the plan.** Max gets "$100 USD"; Team gets "$20 USD per seat" (Standard) or "$100 USD per seat" (Premium), pooled [S5].
- So USD 100 can also come from a Team plan with five Standard seats or one Premium seat.
- **Also incorporated:** the Usage Policy, the Supported Regions Policy and the Service Specific Terms. Each is "incorporated by reference into these Terms" (D.2) [S2].
- The Service Specific Terms (effective 2026-08-31) have no clause on credits [S37]. The Usage Policy read is still the 2026-11-12 version [S3].

## 2. A product or service that other people use

- **The Commercial Terms allow it.** "Anthropic gives Customer permission to use the Services, including to power products and services Customer makes available to its own customers and end users" (A.1) [S2].
- **No credit-specific limit was found** on commercial use, third-party end users, or personal or non-commercial use [S4][S5][S35].
- **No sentence explicitly allows it for the plan credit either.** The permission comes through the chain above: Credit Terms, then Commercial Terms.
- **"Your own" applications.** The credits let "you ... build and run your own applications and agents" [S5].
- The Help Center says: "Use them to build Claude into your own apps and agents with the Claude API" [S35].
- **Reading:** "your own" means apps you build, as against Claude Code or the Claude apps. The FAQ draws that line: "The credits are for building your own apps and agents on the Claude Platform" [S35].
- **Transfer and holder-only use.** "Customer may not transfer or sell Credits ... and Credits may only be used by the holder of the Anthropic account to which the Credits are associated" [S4].
- **Reading:** Crux's backend makes every call from the owner's organization, so the holder uses the credits. Learners never hold or receive them.
- **Resale.** Customer must not "resell the Services except as expressly approved by Anthropic" (D.4) [S2].
- **Reading:** a tutor built on the API is a product, not a resale of raw API access.
- **Not for consumer use.** "Services under these Terms are not for consumer use" [S2].
- **Reading:** this sorts products into the two sets of terms. It does not bar an individual from using the API.
- **Linked billing is a different feature.** It "lets your customers link their own Claude Console organization to your app". Plans "can't be linked" [S40].
- **Reading:** that rule, and the linked-billing exclusion in section 3 [S35], stop the credit paying for usage in someone else's app. Neither touches Crux serving learners from its own organization.

## 3. Which products it covers

| Product | Covered | Source |
|---|---|---|
| Claude API (Messages API) | Yes | [S5][S35] |
| Message Batches API | Yes: "The Claude API (Messages API and Message Batches API)" | [S35] |
| Claude Agent SDK | Yes, with an API key from the linked organization | [S5][S35] |
| Playground in the Console | Yes | [S5][S35] |
| Claude Managed Agents | Yes | [S5][S35] |
| Claude Code | No: "Interactive Claude Code in the terminal, IDE, desktop, or web" | [S5][S35] |

- Also not covered: "Extra usage in Claude, Claude Code, or Claude Cowork". Nor is "Claude on Amazon Bedrock, Google Cloud Vertex AI, or Microsoft Foundry" [S35].
- [S5] names the Batch API only as a way to spend less: "It costs 50 percent less."
- **Agent SDK billing depends on sign-in.** It is covered "when you run them yourself with an API key from your linked Claude Console organization" [S35].
- "When you're signed in with your Claude plan instead, claude -p and Agent SDK usage still draw from your plan's usage limits" [S35][S38].
- **A product may not use the owner's claude.ai login.** "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products" [S39].
- So, without Anthropic's approval, Crux signs in with an API key or federation, not the owner's plan.
- **Linked billing is also excluded.** The credits don't apply to "Claude usage in third-party apps that's billed through linked billing" [S35][S6].

## 4. Expiry, rollover and spend order

- **Arrival:** "Credits arrive each billing cycle, shortly after your plan payment is processed. On annual plans, credits arrive monthly" [S5].
- **Expiry:** "Unused credits expire at the end of each billing cycle (or monthly for annual plans) and don't roll over" [S5].
- This fits the Credit Terms: promotional credits "expire at the time indicated when issued" [S4]. The Billing page shows each expiry date [S5].
- **Order against bought credits:** "Included credits are spent first, then any credits you've purchased" [S5].
- The Help Center qualifies it: "For usage they cover, your monthly credits are spent before any credits you've purchased" [S35][S6].
- **Reading:** Claude Code usage never touches the plan credit. It draws only on bought credits.
- **Order against other promotional credits:** not stated on any page read.
- **Bought credits** "expire one year from the purchase date" and are non-refundable [S6][S4].

## 5. Plan lapse, downgrade, unlinking, Team plans and company organizations

- **Cancel, downgrade or refund:** "New credits stop when your plan ends. Credits you already have stay usable until they expire" [S5].
- **Eligibility while active:** "Your eligible plan must be active and in good standing" [S5].
- **Max to Ultra:** "You receive prorated API credits right away, then $200 USD each billing cycle" [S5].
- **Max or Ultra to Team:** "The link to your Max or Ultra plan ends." A Team owner can claim after 7 days on the Team plan [S5].
- **Unlinking or changing the organization:** "You can't change the linked organization yourself ... To change it later, contact support" [S5]. No page says what happens to the balance.
- **One link each way:** "Each plan links to one Console organization, and each Console organization can receive credits from one plan" [S5].
- **Team plans:** credits are "pooled into one monthly balance, capped at $500 USD". They are based on seats at the start of each billing month [S5].
- Team claims need a Primary Owner or Owner on the plan [S5].
- **Account closure:** credits "automatically expire if Customer closes its Anthropic account and cannot be recovered" [S4].
- **Company organizations:** no page read sets a different rule. "Customer" is "you or the organization, company, or other entity that you represent" [S2][S4].

## 6. When the credit runs out

- **Bought credits exist:** "requests continue using purchased credits. Auto-reload, if it's turned on, adds credits to the purchased balance" [S5].
- **No credits left:** "API requests stop until your next monthly API credits arrive. Usage is never charged to your Claude plan" [S5].
- The error is: "Your credit balance is too low to access the Anthropic API" [S5].
- **Invoiced organizations:** "usage beyond the API credits is billed as usual" [S5].
- **Auto-reload ignores the plan credit.** "Auto-reload is based only on your purchased balance. It reloads when that balance reaches your threshold, even if included credits remain" [S5].
- Auto-reload charges the card "on a recurring basis ... until Customer opts out" [S4]. It can be turned off on the Billing page [S6].

## 7. Other restrictions

- **Rate-limit tier:** "Organizations linked to an eligible plan move up to at least the Start tier" [S5].
- This settles the Evaluation-tier unknown in item 2 of `claude-anthropic-api-account.md` for a linked organization.
- Credits over USD 200 a month move an organization to at least Build. The credits "don't count toward moving to a higher tier" [S5].
- **Spend cap:** "Usage paid with credits counts toward your organization's monthly spend cap" [S5][S7].
- Caps reset on the 1st of each calendar month, but credits refresh on the billing cycle [S5]. The two dates can differ.
- **Workspaces:** "Every API key and workspace in the linked organization draws from the same balance" [S5].
- To cap one project, "give it its own workspace and set that workspace's spend limit" [S5]. The Default Workspace cannot take one [S8].
- **Platforms:** "These credits apply only to the Claude API in the Claude Console" [S5].
- **Data use and retention:** no page sets a different rule for credit-paid usage. The Commercial Terms and DPA apply as for bought credits [S2].
- **Organization type:** no page requires an individual or a company organization. Only roles are required: Owner, Admin or Billing in the Console [S5].
- **Plan usage limits:** "Credits don't change your usage limits in Claude or Claude Code" [S5].

## Not verified

- **Which plan grants the owner's credit.** USD 100 fits Max or a small Team plan [S5]. The owner can check the plan in claude.ai Settings > Billing.
- **An explicit statement that the plan credit may fund a service for other people.** None was found. The permission rests on Commercial Terms A.1 through H.1 [S2].
- **The claim screen on claude.ai.** It needs a sign-in. Two pages say it links the Credit Terms [S5][S35]; the screen itself was not seen.
- **Spend order against other promotional credits.** No page states it.
- **The balance after unlinking** or a support-made change of organization. The docs say only "contact support" [S5].
- **Whether a company-owned organization changes anything.** No page says it does.
- **The data handling of credit-paid usage.** No page sets a separate rule; none confirms the same rule either.

## What this changes

### #802 (the AI layer and how the credit fits the budget)

- The credit can pay for Crux's tutoring calls under the Commercial Terms. The credit terms add no extra limit on that use.
- Budget USD 100 a month that does not roll over. It refreshes on the owner's plan billing date, not the 1st.
- Batches and the Agent SDK draw on the credit too. Claude Code use by the owner does not.
- The backend signs in with an API key or federation from the linked organization. Without Anthropic's approval, it cannot use the owner's claude.ai login [S39].
- The credit depends on the owner keeping the plan active and in good standing. Plan the AI budget for the month it lapses.
- The linked organization is fixed. Build Crux in it, or ask support to move the link.

### #675 (spending limits)

- With no bought credit and auto-reload off, requests stop when the credit runs out. That is a hard stop at USD 100 a month.
- Keep auto-reload off. It fires on the bought balance even while plan credit remains [S5].
- Set a workspace spend limit for Crux. Every key in the organization shares one balance [S5].
- The spend cap and the credit reset on different dates. Size the workspace limit with both in mind.
- Start tier is the floor for the linked organization, so the Evaluation-tier risk is gone [S5].

## Sources (new IDs only, read 2026-11-18)

- [S35] Claude Help Center, "Monthly API credits for Max, Ultra, and Team plans", https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-ultra-and-team-plans (marked "Updated today" on 2026-11-18): "Review the Supplemental Credit Terms, then Link organization."
- [S36] Anthropic Consumer Terms of Service, https://www.anthropic.com/legal/consumer-terms (effective 2025-10-08): "Our Commercial Terms of Service govern your use of any Anthropic API key, the Anthropic Console".
- [S37] Anthropic Service Specific Terms, https://www.anthropic.com/legal/service-specific-terms (effective 2026-08-31): no clause on credits.
- [S38] Claude Help Center, "Use the Claude Agent SDK with your Claude plan", https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan: the 2026-10-07 update says when signed in with a plan, the Agent SDK and claude -p "still draw from your subscription limits".
- [S39] Agent SDK overview, https://code.claude.com/docs/en/agent-sdk/overview: "Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products".
- [S40] Claude Help Center, "Offer linked billing in your platform", https://support.claude.com/en/articles/18467110-offer-linked-billing-in-your-platform: "Claude subscription plans (Pro, Max, Ultra, Team, and Enterprise) can't be linked".
