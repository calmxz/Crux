# Law and safety: profiling, advisory opinions and age rules

Part of [Spec facts that rested on search snippets](../snippet-fact-checks.md), checked on 2026-11-11 for #762.

## 4. NPC Circular 2022-04: "profiling"

**Spec says:**

- `trial.md:153`: "Is Crux "automated decision-making or profiling" that must be registered under NPC Circular 2022-04, Section 5?"
- `trial.md:154`: "If not, is the sworn declaration still needed?"
- `README.md:31`: "If the trial shows opening is worth it, an advisory opinion from the National Privacy Commission."

**Source:** NPC Circular No. 2022-04, "REGISTRATION OF PERSONAL DATA PROCESSING SYSTEM, NOTIFICATION REGARDING AUTOMATED DECISION-MAKING OR PROFILING, DESIGNATION OF DATA PROTECTION OFFICER, AND THE NATIONAL PRIVACY COMMISSION SEAL OF REGISTRATION", dated 05 December 2022. `https://privacy.gov.ph/wp-content/uploads/2023/05/Circular-2022-04-2.pdf`, 16 pages, text layer read with pypdf. The earlier attempt was blocked. This time a plain download worked.

**Page says:**

- Sec. 2(L): "“Profiling” refers to any form of automated processing of data consisting of the use of personal data, such as an individual’s economic situation, political or religious beliefs, behavioral or marketing activities, personal preferences, electronic communication data, location data, and financial data, among others, in order to evaluate, analyze, or predict his or her performance, qualities, and behavior, among others;"
- Sec. 2(A): "“Automated Decision-making” refers to a wholly or partially automated processing operation that can make decisions using technological means totally independent of human intervention; automated decision-making often involves profiling;"
- Sec. 5(A): "A Data Processing System processing personal or sensitive personal information involving automated decision-making or profiling shall, in all instances, be registered with the Commission."
- Sec. 6: "A PIC or PIP who does not fall under mandatory registration and does not undertake voluntary registration shall submit a sworn declaration (see Annex 1)."

**Verdict: confirmed.** Section 5 is the right section, and "automated decision-making or profiling" is its wording. The spec does not quote the definition. Sec. 2(L) is the definition the advisory question turns on. Its phrase "evaluate, analyze, or predict his or her performance" reads close to a tutor that marks mastery. This note does not decide whether it covers Crux.

**Also on the page:**

- Sec. 6 answers part of `trial.md:154`. A controller that neither must register nor registers by choice has to submit the sworn declaration. The question stays useful only if the NPC could say Crux needs neither.
- Sec. 40: "This Circular supersedes in its entirety NPC Circular No. 17-01." The NPC list shows no later circular that amends 2022-04. NPC Advisory 2025-01 clarifies Circular 2020-03, not 2022-04.
- Sec. 14: a Certificate of Registration "shall be valid for one (1) year from its date of issuance". This matches the yearly renewal in `trial.md:160`.

## 5. The route to an NPC advisory opinion

**Spec says:**

- `trial.md:150`: "If the trial shows a public opening is worth it, the owner first sends the National Privacy Commission a Request for Advisory Opinion, at least a month before opening ([#677]). It goes after the trial, not before ([#717], [#722])."
- `trial.md:151`: "It follows NPC Circular 18-01: a letter to the Privacy Commissioner and Chairman, by email or in person, with the facts, the questions and a certification that the matter is not pending. An answer comes within 20 working days. It is non-binding, and a fee may apply ([#677])."
- `quality-bar.md:232`: "The advisory letter sent, at least a month before opening ([#677])".
- `README.md:31`, as in fact 4.

**Source:**

- NPC Circular No. 18-01, "RULES OF PROCEDURE ON REQUESTS FOR ADVISORY OPINIONS", dated 10 September 2018. `https://privacy.gov.ph/wp-content/uploads/2022/01/Circular18-01_Request_forAdvisory_Opinion.pdf`
- NPC Circular No. 2023-01, as in fact 3.
- NPC "ADVISORY" on online payment of fees, dated 15 March 2024. `https://privacy.gov.ph/wp-content/uploads/2024/03/Fees_Advisory_Final_15-March-2024.pdf`
- NPC Citizen's Charter page, "REQUESTING ADVISORY OPINIONS", modified 2023-06-01. `https://privacy.gov.ph/citizens-charter/requesting-advisory-opinions/`

**Page says:**

- Circular 18-01, Sec. 4: "The requesting party shall submit a letter request for the issuance of an advisory opinion, addressed to the Privacy Commissioner and Chairman. The letter request may be delivered to the NPC personally, or sent by direct or electronic mail." Item (d) asks for "An affidavit or certification that the subject of the request for advisory opinion is not a matter pending in a case in litigation before the courts, the NPC or is not subject of an ongoing investigation or compliance check". Its footnote 1: "Affidavit duly notarized for individual data subjects and Secretary’s Certificate for juridical persons. This documentary requirement may be waived in meritorious cases."
- Circular 18-01, Sec. 10: "The advisory opinion shall be released to the requesting party not later than twenty (20) working days from date of receipt by the concerned division, unless the complexity and novelty of the subject matter requires a longer period of time for further evaluation."
- Circular 18-01, Sec. 2: an advisory opinion "shall serve to provide guidance to the requesting party and the general public, but shall not be used in the nature of a standing rule binding on the NPC when evaluating other cases regardless of the similarity of the facts and circumstances."
- Circular 18-01, Sec. 12: "Every request for the issuance of an advisory opinion may be subject to a reasonable fee, as may be prescribed by the NPC in a separate issuance."
- Circular 2023-01, Section 1: "Request for Advisory Opinion Php 7,500.00 Legal Research Fee for issuance of Advisory Opinions Php 75.00". Section 2: "All fees shall be collected in advance of any service to be rendered or materials to be furnished."
- Fees advisory, 2024-03-15, under "Advisory Opinion and Legal Research": a filled-out Service Request Assessment Form goes to the NPC policy email with the subject "Request for Advisory Opinion", and payment goes through the LANDBANK Link.Biz Portal.

**Verdict: partly.** The addressee, the delivery modes, the statement that nothing is pending, and the 20 working days match. These parts differ:

- For an individual, the "certification" is a notarized affidavit, unless the NPC waives it.

- "A fee may apply" is out of date. The separate issuance that Sec. 12 anticipated exists: PHP 7,500 plus PHP 75, paid in advance.
- "Non-binding" is close but loose. Sec. 2 says the opinion guides, and does not bind the NPC in other cases. The 20 working days can also run longer for a complex or novel matter.

**Fix:**

- `trial.md:151`: "It follows NPC Circular 18-01: a letter to the Privacy Commissioner and Chairman, by email or in person, with the facts, the questions and a notarized affidavit that the matter is not pending. An answer comes within 20 working days, or longer for a complex or novel matter. The opinion guides, and does not bind the Commission in other cases. NPC Circular 2023-01 sets a fee of PHP 7,500, plus PHP 75, paid in advance ([#677])."
- Decision this touches: #677, which set the advisory route. PHP 7,500 is a one-off cost before opening. Check whether `spending.md` should list it.

**Also on the page:**

- Circular 18-01, Sec. 5(b) lists requests the NPC will not accept. Item 4: "The request posits questions, issues or concerns that are too general in scope, overly abstract, anticipatory and speculative". Item 6: a request that "involves a request for review of a privacy notice, privacy manual, consent form, organization terms and conditions, or other privacy policies." A letter sent before Crux opens could be read as anticipatory. This note does not decide that.
- The older NPC page `https://privacy.gov.ph/requesting-advisory-opinion/` says: "You will receive our written response within 15 working days." The Citizen's Charter page and Circular 18-01 say 20 working days. The circular governs.

## 6. Age rules

**Spec says:**

- `README.md:39`: "Adults only (18 or over). Every way in has an "I am 18 or over" tick: sign-up, the Request access form, and the guest and trial-link entry".
- `privacy.md:11`: "**Age:** "You must be 18 or over, and old enough to agree to these terms where you live." (see [`age.md`](age.md)) ([#677])."
- `age.md:12`: "Share posts on LinkedIn and Facebook carry no age wording ([#681])."
- `ai-layer.md:9`: "The Google GenAI SDK calls Gemini Enterprise Agent Platform (formerly Vertex AI), for the meantime".
- The tick also appears at `accounts.md:62`, `trial.md:19`, `trial.md:44` and `landing-screens.md:62`.

The spec does not cite any vendor's age terms. The reason for 18+ is in #681, which cites the Gemini API terms and Google Cloud Service Specific Terms §20(d). #681 also holds the OpenAI claim. The LinkedIn 16+ and Facebook 13+ claims appear in neither `docs/spec/` nor #681. They come only from the fact list.

**Which Gemini terms apply.** Crux reaches Gemini through Agent Platform (`ai-layer.md:9`). So the binding age clause is Google Cloud's Service Specific Terms, not the Gemini API Additional Terms. The Gemini API terms were already read, so I did not recheck them.

### 6a. Google Cloud Service Specific Terms

**Source:** `https://cloud.google.com/terms/service-terms`. Its version list starts "Last modified October 30, 2026".

**Page says:** "20. Generative AI Services (formerly Section 19 (Generative AI Services))" … "d. Age Restrictions. Customer will not, and will not allow End Users to, use a Generative AI Service as part of a website, Customer Application, or other online service that is directed towards or is likely to be accessed by individuals under the age of 18."

**Verdict: confirmed.** The wording matches what #681 quotes from the 2026-10-12 version. It is still §20(d). I did not recheck that Agent Platform counts as a "Generative AI Service". That rests on `docs/research/learnlm-gemini.md`, section 3.

### 6b. OpenAI API, under 18

**Source:** "Under-18 guidance", `https://developers.openai.com/api/docs/guides/safety-checks/under-18-api-guidance`. No date shown. OpenAI's consumer Terms of Use returned 403, so this note claims nothing about them.

**Page says:** "Organizations serving minors must take reasonable steps to ensure that the content they are serving to minors via the API is safe and age appropriate".

**Verdict: confirmed.** The API allows serving minors with safeguards, as #681 says. The same page's best practices recommend OpenAI's most current flagship models for minors, as #681 also says. It adds a zero-data-retention condition for children under 13.

### 6c. LinkedIn

**Source:** LinkedIn User Agreement, `https://www.linkedin.com/legal/user-agreement`, "Effective on November 3, 2025".

**Page says:** "“Minimum Age” means 16 years old." The same clause raises it where the law requires an older age.

**Verdict: no claim.** The page gives 16, as the fact list says, but neither the spec nor #681 states LinkedIn's age.

### 6d. Facebook

**Source:** Meta Terms of Service, `https://www.facebook.com/legal/terms`, "Effective January 1, 2025". The page also links a new version, "Effective January 20, 2027".

**Page says:**

- Current terms, section 3.1: "you cannot use Facebook if: You are under 13 years old."
- Terms from 2027-01-20: "You are under 13 years old or under the minimum legal age in your country to use Facebook."

**Verdict: no claim.** The page gives 13, as the fact list says, but neither the spec nor #681 states Facebook's age. From 2027-01-20 the floor stays 13, and the new terms add any higher national minimum.

**Fix for fact 6:** none to `docs/spec/`. The 18+ rule rests on §20(d), which still holds. LinkedIn's 16 and Facebook's 13 mean the share posts can reach people under 18. #681 kept age wording off the posts and put it on the landing page and the ticks, so nothing changes.
