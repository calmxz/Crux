# The Terms of Use and the Privacy Policy

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what Crux promises: the Terms of Use, and the Privacy Policy with its contacts, breaches, and processors. What the owner may read, deleting and closing, and how long data stays are in [`privacy.md`](privacy.md).

## The Terms of Use

The terms use plain words throughout, and state the cost and the law from the main file's "Who Crux is for" ([#677]).

- **Age:** "You must be 18 or over, and old enough to agree to these terms where you live." (see [`age.md`](age.md)) ([#677]).
- **Graded work:** "Crux teaches; it won't do your work for you. Don't use it where your course or exam forbids outside help." The tutor's teaching is unchanged (see [`teaching.md`](teaching.md)) ([#677]).
- **Standard lines** ([#677]):
  - "Crux is an AI tutor and can make mistakes. Check anything important against your course material."
  - "Crux is provided as is, without guarantees it will be available or error-free."
  - "As far as the law allows, [owner] isn't liable for losses from using Crux."
  - "Crux may change, and may close with notice (see the Privacy Policy)."
  - "You keep ownership of what you upload. You let Crux use it only to tutor you. Only upload what you have the right to use."

### Harm and misuse

The Terms state the harm line and what misuse leads to. Both are in [`misuse.md`](misuse.md) ([#677]).

### Changes to the terms

- Changes that matter are emailed 14 days ahead. These are changes to what is stored, who sees or processes it, new uses of data, and new rules on what learners may do ([#677]).
- The learner then agrees with a tick: "Crux's terms changed: [what changed]. [Agree] [Close my account]". It shows the next time they open Crux, on any browser, before any tutoring ([#677], [#733]).
- A learner who never comes back sees nothing. The account waits, and the idle rule in [`privacy.md`](privacy.md) applies ([#733]).
- Other changes, such as a typo or a clearer sentence, are dated in a "What changed" list ([#677]).

## The Privacy Policy

### Who runs Crux

- Crux is run by the owner, named, in the Philippines ([#677]). Until opening, "Who runs Crux" says the owner built it (see [Contacts](#contacts)) ([#754]).
- Until the Commission says otherwise, Crux handles learning progress as possibly sensitive information about education, declined kinds, all kinds alike, as possibly sensitive information about health or sexual life, and the 18+ tick as information about age. Learning progress means objectives shown and passed, mastered topics, check answers and photos, and preferences. This is why sign-up asks for specific consent. If the Commission does not answer, or turns the request away, declined kinds stay handled as sensitive ([#677], [#776]).
- Crux follows the same standards wherever its learners are ([#677]).

### Contacts

- The owner is the data protection officer. From opening, the site and the Privacy Policy publish "Data Protection Officer, Crux", the owner's home postal address, a dedicated phone number (a prepaid SIM used only for Crux), and the role email ([#677]).
- Until opening, the site and the Trial Privacy Notice give only privacy@ and the owner's LinkedIn, naming the owner as the one who built Crux. The officer's title, postal address and phone are published with the before-opening checklist (see [`quality-bar.md`](quality-bar.md)). The owner accepts that this gives less than the Commission's advisory expects during the trial ([#754]).
- The owner's actual name and details are filled in when the policy is written ([#677]).
- Data requests (a copy, deletion) go to the Crux email, privacy@ the domain ([#677], [#717]). A trial link has no email: its holder erases it in Settings, and nothing is erased on an emailed request (see [`trial-links.md`](trial-links.md)) ([#755]). The owner's LinkedIn or other profiles are a general contact ([#677]).
- Where that inbox sits, in the trial and from opening, is in [`email.md`](email.md) ([#717]).

### Copies and requests

Copies of a learner's data and requests by email are in [`email.md`](email.md#copies-and-requests).

### Breaches

If sensitive or sign-in data, decline records included, reaches the wrong hands with a real risk of serious harm, the owner tells the National Privacy Commission and the affected learners within 72 hours. The owner sends the Commission a yearly summary of incidents ([#677], [#776]). The learners' notice goes from the owner page: an email to every account, locked and closing ones included, and to every other address Crux holds, and a notice page on every live trial link (see [`email.md`](email.md)) ([#755]). A switched-off link is not reached, though its stub may still hold kinds ([#776]).

### What it covers

The Privacy Policy says ([#677], [#679], [#681], [#716], [#717], [#732], [#733]):

- what is stored and for how long (see [`privacy.md`](privacy.md));
- "Deleting a session erases it. Another session may still mention something from it, until you delete that one too.";
- a removed file's earlier replies stay in the conversation until the session is deleted;
- "If you ask for a copy while closing, its link works until 11:59 pm Philippine time on the 7th day after it's sent, plus any days Crux was down. If we can't send it, we keep it at most 30 days. We erase the copy after that, and keep it no longer, except while our daily job is down.";
- "Limits on how long we keep something end at our daily job's last run within them, and run longer only while that job is down.";
- a date for erasing data moves if a notice goes out late, or if Crux is down, so nobody loses their chance to act ([#735]);
- the processors below, and where they process data;
- the dated anonymous counts, including the under-18 count, and the cookieless arrivals count;
- the sign-in cookie;
- "Your browser remembers your theme choice (Match my device, Light or Dark). Crux never receives it." ([#779]);
- the human check, the email sender, the code limits and the region check;
- the burst guard, the hand blocks and their keep time, and the owner's reading of Cloudflare's request analytics only to find a network to block ([#770]);
- the misuse flag, sealed sessions, and the email of their account, being kept longer only if reported to the authorities, what is saved with each decline, what a flag or a share lets the owner read, and the blocked-email list;
- the guest and trial rules;
- error reports with no learner text;
- the learner's rights: a copy, correction, deletion, withdrawing consent, and complaining to the National Privacy Commission;
- the 72-hour breach rule;
- "If Crux becomes a paid service, nothing moves without your agreement."

### Processors

| Processor | Used for | Agreement and place |
|---|---|---|
| Google Cloud | Cloud Run, Cloud Storage, Agent Platform, Error Reporting, Monitoring, BigQuery | Google Cloud's data processing addendum. Data "may be processed in any country", and Crux's data is stored in Singapore ([#679], [#717]) |
| Cloudflare | Static files, the Worker, DNS, the registrar, Email Routing, Turnstile | Its self-serve agreement. It sees network addresses at its edge, and its Security Analytics keeps sampled request details, with addresses and paths, for 31 days, which the owner reads only to find a network to block. The hand blocks sit in its settings ([#770]). Turnstile reads the network address, browser details and connection fingerprint, and Cloudflare uses those signals partly for its own purposes, outside the agreement ([#716], [#717]) |
| Supabase | The database | Part of its Terms on every plan, with Supabase Pte. Ltd (Singapore). Data stored in Singapore ([#717]) |
| Resend | Crux's email | Covers all plans. Processing mainly in the US, with sent emails in its log 30 days and in its backups up to 7 days after ([#717], [#762]) |
| The Crux Gmail, in the trial | The Crux email | No agreement, an exception the owner accepted. Zoho or Workspace from opening ([#717]) |

## Gaps

- **Right of access:** whether a copy (see [`email.md`](email.md#copies-and-requests)) that leaves out declines still counting and an open flag meets the Data Privacy Act's right of access (section 16(c)) is unchecked ([#776]).

## On screen

"Who runs Crux" is in [`landing-screens.md`](landing-screens.md) ([#754]).

[#677]: https://github.com/calmxz/Crux/issues/677
[#679]: https://github.com/calmxz/Crux/issues/679
[#681]: https://github.com/calmxz/Crux/issues/681
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#732]: https://github.com/calmxz/Crux/issues/732
[#733]: https://github.com/calmxz/Crux/issues/733
[#735]: https://github.com/calmxz/Crux/issues/735
[#754]: https://github.com/calmxz/Crux/issues/754
[#762]: https://github.com/calmxz/Crux/issues/762
[#755]: https://github.com/calmxz/Crux/issues/755
[#770]: https://github.com/calmxz/Crux/issues/770
[#776]: https://github.com/calmxz/Crux/issues/776
[#779]: https://github.com/calmxz/Crux/issues/779
