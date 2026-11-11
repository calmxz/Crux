# Privacy promises: delete windows and Google's stored conversations

Part of [Spec facts that rested on search snippets](../snippet-fact-checks.md), checked on 2026-11-11 for #762.


Research for issue #762. Checked on **2026-11-11**. Each fact in section 2 of the snippet-only list is checked against the page that owns it. Quotes are copied from the page.

Two pointers in the fact list are loose. #677 did not choose a 30-day restore. It chose a 7-day undo and rejected holding everything for 30 days. #718 is a glossary PR. The decision that used the 7-day and 55-day figures is #679 (its Q9 and Q12). The Zoho question belongs to #717. #726 is the research ticket that looked into it.

| # | Fact | Verdict | Source |
|---|---|---|---|
| 1a | Khan Academy: 48 hours to undo a deletion | confirmed | Khan Academy Help Center, "How do I delete my account?" |
| 1b | Duolingo: 7 days to cancel a deletion | confirmed | Duolingo Help Center, "How do I delete my account and access my data?" |
| 1c | ChatGPT: no undo; data deleted within 30 days | confirmed | OpenAI Help Center, "Deleting your ChatGPT account" |
| 1d | Claude: no undo | confirmed | Claude Help Center, "Delete your Claude account". Anthropic Privacy Center, "How long do you store my data?" |
| 1e | Quizlet: no undo | confirmed | Quizlet Help Center, "Deleting your account" |
| 2a | Agent Platform keeps stored interactions 7 days | confirmed | Agent Platform docs: Interactions API overview and developer guide |
| 2b | Gemini Developer API keeps stored interactions 55 days | confirmed (Paid Tier; 1 day on Free Tier) | Gemini API docs, "Interactions API" |
| 2c | Gemini Developer API keeps every prompt 55 days for abuse checks (#679 Q9) | confirmed | Gemini API docs, "Abuse monitoring" |
| 3 | Resend keeps sent emails 30 days, not 1 day on Free | partly | Resend pricing page. Resend Data Processing Addendum |
| 4 | Zoho's DPA covers free-plan customers | unverified | Zoho privacy policy, Zoho Accounts help, Zoho GDPR page |

## 1. Delete and restore windows at other apps

**Spec says:** the spec cites none of these apps. It relies on them through #677:

- `privacy.md:50`: "The dialog names what is erased … and the date the 7 days end, with a "Send me a copy first" button ([#677], [#733])."
- `privacy.md:52`: "During the 7 days, the next time they open Crux, on any browser, they see "Keep my account / Sign out", with the same button."
- `privacy.md:54`: "Otherwise the account and its data are erased on day 8, in the daily housekeeping job ([#677], [#728] Answer 7)."
- `privacy.md:58`: "The owner chose the undo for the meantime. Erasing at once is the fallback if the undo causes problems ([#677])."

#677, Rejected: "**Erasing an account at once, or holding everything 30 days** (Q1): the owner chose a week to change one's mind, as in comparable learning apps (Khan Academy 48 hours, Duolingo 7 days); 30 days would reverse "deleting is irreversible"." The searches behind #677 also named ChatGPT, Claude and Quizlet as apps with no undo. ChatGPT's data was "erased within 30 days". For Claude, it said "A deleted chat leaves its back-end systems within 30 days". It found Duolingo's figure only in third-party guides.

### 1a. Khan Academy

**Source:** Khan Academy Help Center, "How do I delete my account?", `https://support.khanacademy.org/hc/en-us/articles/360034662972-How-do-I-delete-my-account`. Updated 2025-06-05. Plain fetch got 403, so I read it in a browser.

**Page says:** "If you try to log back in within 48 hours, your account will not be deleted. The account will restore itself and you will be notified of this through an email." Also: "Note: Deleting your account is a permanent action that will delete all progress. Your account cannot be restored once deleted."

**Verdict: confirmed.**

**Also on the page:** "After deletion, the same email address (and username!) can be used to create another account." Khan Academy undoes the deletion when the user signs in again, as Crux does with "Keep my account".

A second page, "Khan Academy’s automatic account deletion policies and procedures" (`https://support.khanacademy.org/hc/en-us/articles/28319258507021`, updated 2026-04-08), says "inactive Khan Academy accounts are deleted after 2 years of inactivity". It sends an "Initial notification (approximately 90 days before deletion)" and a "Reminder notification (approximately 28 days before deletion)". Crux uses 12 months, with emails 30 and 7 days before (`privacy.md:64`). That is Crux's own choice and does not rest on this page.

### 1b. Duolingo

**Source:** Duolingo Help Center, "How do I delete my account and access my data?", `https://www.duolingo.com/help/delete-my-account-and-data`. No date shown. The old `support.duolingo.com` address redirects to `www.duolingo.com/help`. The page renders only with JavaScript, so I read it in a browser.

**Page says:** "In case you change your mind, you’ll have 7 days to cancel the erasure process, via a link in the same email where you confirmed your request." Also: "Once completed, deletion cannot be undone. This deletion can take up to 30 days."

**Verdict: confirmed.** The 7 days now rest on Duolingo's own page, not on an unofficial guide.

**Also on the page:** the undo works through a link in the confirmation email, not by signing in. The user first confirms the request through a "Delete my data" link in that email. The page does not say when the 7 days start.

### 1c. ChatGPT

**Source:** OpenAI Help Center, "Deleting your ChatGPT account", `https://help.openai.com/en/articles/6378407-deleting-your-chatgpt-account`. "Updated: yesterday", so about 2026-11-10. Plain fetch got 403, so I read it in a browser.

**Page says:**

- "Deleting your ChatGPT account is permanent."
- "If you delete your account, we will delete your data within 30 days, except we may retain a limited set of data for longer where required or permitted by law."
- "No. Deleted accounts cannot be reactivated, but you can create a new account with the same email address after 30 days."

**Verdict: confirmed.** A search summary behind #677 gave "permanent and cannot be undone". I did not find that phrase on the current page. The substance is the same.

### 1d. Claude

**Source:**

- Claude Help Center, "Delete your Claude account", `https://support.claude.com/en/articles/9028421-delete-your-claude-account`. No date shown.
- Anthropic Privacy Center, "How long do you store my data?", `https://privacy.claude.com/en/articles/10023548-how-long-do-you-store-my-data`, dated "July 1, 2026".

**Page says:**

- Help Center: "Deleting your account is permanent. You'll lose access to your conversations, projects, and other saved data, and you can't recover the account afterward. If you want to keep your data, export it on web or desktop before you delete."
- Privacy Center, about a deleted conversation, not a deleted account: "When you delete a conversation it’s:", followed by two bullets, "Removed from your chat history immediately" and "Deleted from our back-end storage systems within 30 days".

**Verdict: confirmed.** Claude has no undo. The 30-day figure covers a deleted conversation. Neither page gives a time limit for erasing a deleted account.

**Also on the page:** the Privacy Center keeps flagged chats longer: "We retain inputs and outputs for up to 2 years and trust and safety classification scores for up to 7 years if your chat or session is flagged by our automated trust and safety systems as violating our Usage Policy."

### 1e. Quizlet

**Source:** Quizlet Help Center, "Deleting your account", `https://help.quizlet.com/hc/en-us/articles/360029768552-Deleting-your-account`. No date shown. Plain fetch got 403, so I read it in a browser.

**Page says:** "Please know that once you delete your account, it can't be recovered." Also: "If you delete your account, all the flashcard sets, folders, and classes that you've created will also be deleted in accordance with our data retention practices."

**Verdict: confirmed.**

**Fix for fact 1:** none. #677's comparison holds: the two learning apps give a short undo (48 hours, 7 days), and the three AI and study tools give none.

## 2. Stored conversations at Google: 7 days and 55 days

**Spec says:** the spec states neither figure. These lines rely on them:

- `ai-layer.md:10`: "Crux calls `generateContent`, for the meantime ([#679])."
- `ai-layer.md:12`: "Crux moves to the Interactions API, with storage off, only when Google's docs give a reason: a notice that `generateContent` is being retired, or a feature Crux needs launching only there."
- `privacy.md:102`: "| Google's copy | Only prompts its filters flag, up to 90 days, with no opt-out. … A short-term cache of at most 24 hours. Deleting in Crux cannot reach these ([#677], [#679], [#717]) |"

The figures are in #679, Rejected:

- Q9: "The Gemini Developer API, for the meantime (Q9): … the Developer API's prepaid credit is the only hard money stop, but it keeps every prompt for 55 days."
- Q12: "The Interactions API, stored or with storage off, for the meantime (Q12): Preview on Agent Platform, 7-day storage at Google, and nothing Crux needs".

The fact list's "Developer API 55" mixes two separate 55-day rules: stored interactions, and the abuse-monitoring copy that Q9 cites. I checked both.

### 2a. Agent Platform: stored interactions

**Source:**

- "Interactions API overview", Gemini Enterprise Agent Platform docs, `https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/interactions`. Last updated 2026-11-10 UTC.
- "Interactions API developer guide", `https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/interactions/developer-guide`. Last updated 2026-11-10 UTC.
- "Gemini Enterprise Agent Platform and zero data retention", `https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/zero-data-retention`. Last updated 2026-11-10 UTC. The old `cloud.google.com/vertex-ai/generative-ai/docs/data-governance` address redirects here.

**Page says:**

- Overview: "By default, the Interactions API stores interactions on the server (store=true) for 7 days so you can chain multi-turn conversations with previous_interaction_id and run asynchronous background tasks (background=true). To opt into stateless execution and support Zero Data Retention (ZDR) workflows, set store=false."
- Developer guide: "7-day time-to-live (TTL): Each stored interaction persists for 7 days from its created timestamp and is automatically deleted when the 7-day TTL expires."
- Zero data retention page: "If you do not specify a value for store, it defaults to true for all models. To achieve zero data retention, explicitly set store = false in your API requests."

**Verdict: confirmed.**

### 2b. Gemini Developer API: stored interactions

**Source:** "Interactions API", Gemini API docs, `https://ai.google.dev/gemini-api/docs/interactions`. No date shown. Read from Google's Markdown copy of the same page.

**Page says:** "**Paid Tier**: The system retains interactions for **55 days**." and "**Free Tier**: The system retains interactions for **1 day**." Also: "For Paid Tier projects, you can configure the retention window in AI Studio to automatically mark logs for deletion from project storage after 7, 14, 28, or 55 days."

**Verdict: confirmed** for the Paid Tier. The Free Tier keeps them 1 day.

### 2c. Gemini Developer API: the abuse-monitoring copy

**Source:** "Abuse monitoring", Gemini API docs, `https://ai.google.dev/gemini-api/docs/usage-policies`. No date shown. Read from Google's Markdown copy of the same page. The HTML page has the same "fifty-five" sentence.

**Page says:** "Google retains the following data for fifty-five (55) days for the purposes of detecting and preventing violations of the Prohibited Use Policy to maintain the safety and security of the Services, and any required legal or regulatory disclosures". The list is "**Prompts**", "**Contextual Information**" and "**Output**".

**Verdict: confirmed.** Q9's "keeps every prompt for 55 days" matches. The copy also holds context and replies.

**Fix for fact 2:** none to `docs/spec/`. Crux uses neither the Developer API nor stored interactions. The spec's condition "with storage off" at `ai-layer.md:12` is essential: on Agent Platform, storage is on unless each request sets `store=false`.

**Also on the pages, and bearing on #679:**

- The Gemini API page now says: "As of June 2026, it is Generally Available and the recommended interface for all new projects. While it is now considered legacy, the original `generateContent` API remains fully supported." That page is for the Developer API, not Agent Platform.
- The Agent Platform overview says: "The generateContent API remains fully supported alongside the Interactions API." It lists Gemini 3.5 Flash-Lite and Gemini 3.8 Flash as supported models, with no "preview" tag. Neither Agent Platform page I read shows a Pre-GA notice. A missing notice does not prove the API is GA on Agent Platform, so I do not state its launch stage. #679 Q12 rejected the Interactions API partly because it was "Preview on Agent Platform". That reason may be out of date. The move trigger at `ai-layer.md:12` still holds: neither page says `generateContent` is being retired.
- The zero data retention page backs the 24-hour cache in `privacy.md:102`. Of in-memory cached data, it says "It's deleted no later than 24 hours after it's written." Durable cached data is also "deleted no later than 24 hours after it's written, and is often evicted sooner."
- The same page says that "Only customers whose use of Google Cloud is governed by the Google Cloud Platform Terms of Service are subject to prompt logging for abuse monitoring." It gives no keep time. The 90-day figure in `privacy.md:102` belongs to section 3 of the fact list (the abuse-monitoring exception), so I did not check it here.
