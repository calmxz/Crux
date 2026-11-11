# Law and safety: RA 11930, the crisis line and NPC registration

Part of [Spec facts that rested on search snippets](../snippet-fact-checks.md), checked on 2026-11-11 for #762.


Research for issue #762. Checked on **2026-11-11**. Each fact in section 1 of the snippet-only list is checked against the page that owns it. Quotes are copied from the page. The RA 11930 quotes are transcribed by eye from a scanned PDF, because the scan has no text layer.

Two ticket numbers in the fact list point at pull requests, not decisions. #708 is a glossary PR, and #712 is a glossary PR. The age decision is #681. The NPC decisions are #677 and #722.

| # | Fact | Verdict | Source |
|---|---|---|---|
| 1 | RA 11930: duties of internet intermediaries | partly | RA 11930, enrolled copy (House document host) |
| 2 | Crisis line 1553 (NCMH) runs 24/7 | unverified | NCMH site blocked by a human check. DOH release of 2020-09-11 |
| 3 | NPC registration fees and the NPCRS | partly | NPC Circular 2023-01. NPC news of 2024-10-01. NPCRS outage notice |
| 4 | NPC Circular 2022-04: "profiling" | confirmed | NPC Circular 2022-04 |
| 5 | The route to an NPC advisory opinion | partly | NPC Circular 18-01. NPC Circular 2023-01. NPC fees advisory of 2024-03-15 |
| 6a | Agent Platform terms bar under-18 services | confirmed | Google Cloud Service Specific Terms §20(d) |
| 6b | OpenAI API allows minors with safeguards | confirmed | OpenAI "Under-18 guidance" |
| 6c | LinkedIn minimum age 16 | confirmed | LinkedIn User Agreement |
| 6d | Facebook minimum age 13 | confirmed (new terms on 2027-01-20) | Meta Terms of Service |

## 1. RA 11930: duties of internet intermediaries

**Spec says:**

- `misuse.md:105`: "**Child-protection law:** the owner chose not to seek advice before the trial. Whether RA 9775 and RA 11930 apply to Crux, and what they require, stays unconfirmed ([#743])."
- `misuse.md:70`: "If the owner reports it to the authorities, the owner marks it "Reported" on the owner page. It then stays sealed past that erasure until the authorities say what to do, and the owner then erases it ([#733], [#743])."
- `privacy.md:87`, `trial.md:130` and `privacy.md:141` repeat that a sealed session is kept longer only if reported.

The spec states no duty and no time limit from either act. The hours appear only in the #743 question: "RA 9775 tells internet service providers to notify the police or the NBI within 7 days and to preserve evidence. Summaries of RA 11930 describe takedown and reporting duties for platforms."

**Source:** Republic Act No. 11930, the enrolled copy signed by the Speaker and the Senate President, stamped "Lapsed into law on JUL 30 2022". URL: `https://docs.congress.hrep.online/legisdocs/ra_18/RA11930.pdf` (36 scanned pages). The House of Representatives homepage, `https://www.congress.gov.ph/`, loads its own files from `docs.congress.hrep.online`, so this is the House's document host. I found no RA 11930 post on the Official Gazette: its site search returned none, and its Republic Acts list (pages 40 to 44) jumps from RA 11917 to RA 11934. The Senate's copy at `legacy.senate.gov.ph` returned 403.

**Page says:**

- Title: "AN ACT PUNISHING ONLINE SEXUAL ABUSE OR EXPLOITATION OF CHILDREN, … AND REPEALING REPUBLIC ACT NO. 9775, OTHERWISE KNOWN AS THE "ANTI-CHILD PORNOGRAPHY ACT OF 2009"".
- Sec. 44, printed page 35: "Republic Act No. 9775 and Section 4(c)(1) of Republic Act No. 10175, otherwise known as the "Cybercrime Prevention Act of 2012", are hereby repealed."
- Sec. 3(p), printed page 6: "*Internet intermediaries* refer to persons or entities that provide infrastructure, platforms, access to, and host, transmit and index content, products and services originated by third parties on the internet." The list includes "(6) Participative network platform providers including social media intermediaries".
- Sec. 9(a)(2), printed page 12, the duty to preserve: "Preserve within six (6) months from the date of the transaction extendible for another six (6) months or during the pendency of the case, all subscriber's or registration information and traffic data in its control and possession: *Provided*, That in the case of content data, the same shall be preserved within one (1) year, and upon notice by the competent authority, the preservation shall be extendible for another six (6) months".
- Sec. 9(a)(3), printed page 13, the duty to take down: "Immediately block access to, remove or take down the internet address, uniform resource locator (URL), websites or any content thereof containing CSAEM or involving streaming or live-streaming of OSAEC, within twenty-four (24) hours from receipt of notice from a competent authority or notice containing sufficient information to identify the content and its source".
- Sec. 9(a)(4), printed page 13, the duty to report: "Report to the Department of Justice (DOJ), within three (3) days, the internet address or websites blocked, removed or taken down, or any form of unusual data activity using its server or facility".
- Sec. 9(b)(1), printed page 15, applies to internet service providers only: "Notify the PNP or the NBI within forty-eight (48) hours from receipt of information that any form of child sexual abuse or exploitation is being committed using its server or facility". Sec. 3(q) defines an ISP as a public telecommunication entity or value-added service provider authorised by or registered with the NTC.

**Verdict: partly.** The spec is right that RA 11930 is the act to ask about. It is wrong to name RA 9775 as a law that may apply: RA 11930 repealed it in 2022. The "7 days" in #743 comes from the repealed act. RA 11930's own limits are 24 hours to take down, 3 days to report to the DOJ, and 6 months to 1 year to preserve. The 48-hour notice to the PNP or NBI binds ISPs only.

**Fix:**

- `misuse.md:105`: "Whether RA 11930 (the Anti-OSAEC and Anti-CSAEM Act, which repealed RA 9775) applies to Crux, and what it requires, stays unconfirmed ([#743])."
- Decision this touches: #743. Its question 1 lists RA 9775, and its "facts found so far" cite the repealed act. The resolution itself (no advice before the trial) does not depend on RA 9775.

**Also on the page, and bearing on what the spec relies on.** This note does not decide whether Crux is an internet intermediary. If it is, these duties meet current rules:

- Sec. 9(a)(2) sets a preservation period. The spec erases a sealed session with its account unless the owner marks it "Reported" (`misuse.md:69`, `misuse.md:70`).
- Sec. 9(a)(4) makes reporting to the DOJ a duty within 3 days. The spec makes reporting the owner's choice (`misuse.md:70`).
- Sec. 9(a)(1) requires terms of service that prohibit OSAEC and CSAEM. The harm list at `misuse.md:14` covers "explicit sexual content" but does not name child sexual abuse material.
- Sec. 7, printed pages 11 and 12, protects anyone who blocks or takes down material from civil, criminal or administrative liability only if the action was "(1) done in good faith; (2) necessary to prevent access or dissemination of CSAEMs; and (3) reported within twenty-four (24) hours from the act of blocking an internet address, removing a website or domain, or taking down of shared video, picture or messages."
- Sec. 8, printed page 12, the safe-harbor exception: "Access, possession and recording of any CSAEM of any person for the purpose of complying with the duties under this Act; the reporting to government authorities; … shall not be subject to any civil, criminal, or administrative liability."
- Sec. 41 sets up implementing rules. I did not read them.

## 2. Crisis line 1553 (NCMH) runs 24/7

**Spec says:**

- `misuse.md:22`: "The line is fixed text: "Philippines: call 1553. Elsewhere: findahelpline.com". The number and the link are checked before each stage (see [`quality-bar.md`](quality-bar.md)) ([#735])."
- `quality-bar.md:217` and `quality-bar.md:238`: "The crisis line's number and link verified, and the directory's terms read ([#735])" before the trial, and again before opening.
- `ai-tests.md:57`: "The tutor gives the crisis line word for word."

The spec does not say "24/7". It relies on 1553 being an NCMH crisis line.

**Source:**

- Owning page: `https://ncmh.gov.ph/`. Plain fetch, curl and headless Playwright got 403. In Chrome it shows a Cloudflare "Verify you are human" checkbox. I did not solve it, so I could not read the page.
- Official secondary: Department of Health, "DOH AND WHO PROMOTE HOLISTIC MENTAL WELLNESS IN LIGHT OF WORLD SUICIDE PREVENTION DAY", `https://doh.gov.ph/doh-and-who-promote-holistic-mental-wellness-in-light-of-world-suicide-prevention-day/`, published 2020-09-11.
- Background: Department of Health, "LAUNCH OF THE NCMH CRISIS HOTLINE", `https://doh.gov.ph/launch-of-the-ncmh-crisis-hotline/`, published 2019-05-02.

**Page says:**

- DOH, 2020-09-11: "24/7 NCMH Crisis Hotline 1553, 0917 899 8727(USAP), and/or 7-989-8727 (USAP)".
- DOH, 2019-05-02: the hotline "can be reached at 0917 899 8727 (USAP) and 989 8727 (USAP) operated 24/7." This launch release does not list 1553.

I also scanned DOH's sitemap for addresses that mention mental health, crisis, hotline, suicide, wellness or NCMH, leaving out procurement and workshop notices. That gave 153 candidate pages. Only the 2020 release mentions 1553. A page that failed to load counted as no match, and pages with other addresses were not scanned.

**Verdict: unverified.** The owning page sits behind a human check. The DOH confirms 1553 as a 24/7 NCMH line as of September 2020, but no page I could open shows it today.

**Fix:** none to the wording. The pre-stage check at `quality-bar.md:217` stays necessary. That check needs a person in a browser, because the NCMH site blocks automated reads.

## 3. NPC registration fees and the NPCRS

**Spec says:**

- `trial.md:160`: "Within 20 days of the first account holder who is not the owner, the owner registers Crux on the Commission's registration system (NPCRS), unless the Commission's answer says it is not needed. It costs about PHP 500, then PHP 350 a year, as summarised in 2023. A private share counts the same as a public one ([#677], [#722])."
- `trial.md:161`: "Trial-link users are not counted toward the 20 days ([#722])."

The spec gives no NPCRS portal steps. The steps below come from Circular 2022-04.

**Source:**

- NPC Circular No. 2023-01, "SCHEDULE OF FEES AND CHARGES OF THE NATIONAL PRIVACY COMMISSION", dated 17 May 2023. `https://privacy.gov.ph/wp-content/uploads/2023/05/Schedule-of-Fees-and-Charges-of-the-National-Privacy-Commission.pdf`. The NPC's "Advisories & Circulars" page (modified 2026-09-21) still lists it as the fee schedule.
- NPC news, "NPC implements registration fees and charges, and submission of Sworn Declaration and Undertaking for Exemption from Data Processing System Registration", published 2024-10-01. `https://privacy.gov.ph/npc-implements-registration-fees-and-charges-and-submission-of-sworn-declaration-and-undertaking-for-exemption-from-data-processing-system-registration/`
- NPCRS, `https://npcregistration.privacy.gov.ph/`, read 2026-11-11 (HTTP 503), and the matching advisory on `https://privacy.gov.ph/`. The advisory shows no date.
- NPC Circular No. 2022-04, dated 05 December 2022, for when to register and who counts as an individual professional. `https://privacy.gov.ph/wp-content/uploads/2023/05/Circular-2022-04-2.pdf`

**Page says:**

- Circular 2023-01, Section 1, "Online Data Processing System /Data Protection Officer Registration": "Initial Registration Fees Individual/Professional Php 500.00 Public and Private Organization 1. Multinational/ National/ Foreign Branch Php 2,500.00 2. Regional/ Provincial/ Metro Manila areas/ Cities Php 1,000.00 3. Municipalities Php 500.00 Registration Renewal Fees Individual/ Professional Php 350.00 Public and Private Organization 1. Multinational/ National/ Foreign Branch Php 1,000.00 2. Regional/ Provincial/ Metro Manila areas/ Cities Php 500.00 3. Municipalities Php 350.00"
- NPC news, 2024-10-01: "Beginning 01 October 2024, all PICs and PIPs are required to pay the corresponding fees to register their DPS and/or renew said registration."
- Circular 2022-04, Sec. 2(I): "“Individual Professional” refers to individuals who are self-employed and who derive income practicing their professions, with or without license from a regulatory board or body, not being part of a partnership, firm, or other organization".
- Circular 2022-04, Sec. 7: "A covered PIC or PIP shall register its newly implemented Data Processing System or inaugural DPO in the NPC’s official registration platform within twenty (20) days from the commencement of such system or the effectivity date of such appointment."
- Circular 2022-04, Sec. 9, the portal steps: "A PIC or PIP shall create an account by signing up in the NPC’s official registration platform where it shall provide details about the entity." Then, in order: the DPO's name, contact details and "a unique and dedicated email address, specific to the position of DPO"; the head of the organisation; "The prescribed application form shall be accomplished and shall be uploaded together with all supporting documents as provided under Section 11"; every data processing system; "all publicly facing online mobile or web-based applications"; and review, with "five (5) days to submit the necessary requirements" if anything is missing. It ends: "An Individual Professional shall register only under his or her name, and indicate his or her principal business address and contact details. Registration through physical submission of requirements is not allowed."
- Circular 2022-04, Sec. 11: "An application for registration filed by a PIC or PIP must be duly notarized and be accompanied by the following documents". The list covers government agencies, corporations, one-person corporations, partnerships, sole proprietorships and foreign entities. For a sole proprietorship it asks for a "DTI Certificate of Registration" and a "valid business permit". It names no documents for a person who runs a service without a registered business.
- NPCRS, 2026-11-11: "The NPC Registration System (NPCRS) is currently unavailable to the public until further notice. Registration applications, exemptions, and account amendments and retrievals are suspended, and renewals of expiring registrations are deferred. Submissions through email, personal filing, or mail will not be accepted."

**Verdict: partly.**

- PHP 500 then PHP 350 matches only the "Individual/Professional" and "Municipalities" rows. An organisation pays PHP 500 to 2,500 at first and PHP 350 to 1,000 to renew, by area. Whether a free app run by one person counts as an "Individual Professional" under Sec. 2(I) is a question for the NPC. The fees are in force through the NPCRS from 2024-10-01, not only "as summarised in 2023".
- The NPCRS exists, but as of 2026-11-11 it accepts no registrations, exemptions or renewals, by any route.
- Sec. 7 counts the 20 days "from the commencement of such system". The spec counts from the first account holder who is not the owner. This note does not decide whether those are the same moment for Crux.
- Registration needs a notarized application and documents from Sec. 11. Unless the owner counts as an individual professional, the nearest category is a sole proprietorship, which asks for a DTI certificate and a business permit. The spec does not plan for either.

**Fix:**

- `trial.md:160`: "Within 20 days of the first account holder who is not the owner, the owner registers Crux on the Commission's registration system (NPCRS), unless the Commission's answer says it is not needed. NPC Circular 2023-01 sets the fee: PHP 500, then PHP 350 a year, for an individual professional; PHP 500 to 2,500, then PHP 350 to 1,000 a year, for an organisation. On 2026-11-11 the NPCRS was closed to all registrations until further notice. A private share counts the same as a public one ([#677], [#722])."
- Decisions this touches: #677, which set the PHP 500 and PHP 350 line, and #722, which set the 20-day trigger at the first account holder. The NPCRS outage may block registration at opening. That bears on the opening checklist in `quality-bar.md`.

**Also on the pages:**

- The NPC homepage carries a second outage notice: the Data Breach Notification Management System is "currently unavailable to the public until further notice". The homepage also gives an email route for breach notices: "all PDBNs transmitted through email shall bear the following subject line: PDBN_[Name of PIC]_[Date of Submission (DDMMYY)]." This bears on the 72-hour breach notice in `privacy.md:126` and the drafted notice in `quality-bar.md:156`.
- The NPCRS page gives the NPC's address as "25th-27th Floors, The Upper Class Tower Quezon Ave. Corner Scout Reyes Street Quezon City 1103 Philippines". Circular 18-01 and the 2022 circulars give the older PICC address in Pasay City. This matters if the advisory letter goes in person.
- The 2024 news page says the NPCRS also takes the Sworn Declaration and Undertaking, "a mandatory declaration for persons and entities that claim exemption from the NPC’s registration requirement." See fact 4.
