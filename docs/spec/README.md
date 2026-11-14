# Crux v1 spec

**Draft: not locked.**

This is the current set of rules for Crux v1. The closed tickets on the respec map ([#661](https://github.com/calmxz/Crux/issues/661)) keep the reasons. Each rule links its source tickets.

## How to use this spec

- Read this file first, then the area files your ticket names.
- Use the terms as [`GLOSSARY.md`](../../GLOSSARY.md) defines them. The glossary holds no rules.
- A rule that limits more than one area, with no area that owns it, is in this file. Every other rule is in its area file, and other areas link to it.
- If a file disagrees with the ticket it cites, or a rule you need is missing, see [`spec-process.md`](spec-process.md). Do not invent the rule.

## What Crux is

Crux is an adaptive tutor for students, self-learners and professionals ([#661](https://github.com/calmxz/Crux/issues/661)). It teaches a topic until the learner understands it properly. A topic is typed, or comes from the learner's own files ([#662](https://github.com/calmxz/Crux/issues/662), [#667](https://github.com/calmxz/Crux/issues/667)).

The tutor offers a mastery check once the learner has shown every learning objective not dropped. A topic is mastered when every objective not dropped is passed, in one check or across several ([#663](https://github.com/calmxz/Crux/issues/663), [#668](https://github.com/calmxz/Crux/issues/668), [#669](https://github.com/calmxz/Crux/issues/669)). Then the learner stops, or picks a related topic from a short menu. An unrelated topic gets a suggestion to start a new session, which the learner can decline ([#670](https://github.com/calmxz/Crux/issues/670)).

v1 is a solid end-to-end portfolio project, shared openly for feedback ([#661](https://github.com/calmxz/Crux/issues/661)). A bar of learner counts and feedback, set before sharing, decides whether a paid public launch follows, as a separate effort ([#676](https://github.com/calmxz/Crux/issues/676)).

Crux runs as a React frontend on Cloudflare, a FastAPI backend on Google Cloud Run, Supabase Postgres, and Google Cloud Storage ([#716](https://github.com/calmxz/Crux/issues/716)). The tutor runs on Gemini models through Google's Agent Platform, for the meantime ([#679](https://github.com/calmxz/Crux/issues/679)).

## Shared rules

### Stages

Crux opens in three stages ([#677](https://github.com/calmxz/Crux/issues/677), [#717](https://github.com/calmxz/Crux/issues/717), [#722](https://github.com/calmxz/Crux/issues/722)):

1. A trial without accounts: guest mode and trial links.
2. If the trial shows opening is worth it, an advisory opinion from the National Privacy Commission.
3. Open sign-up with accounts.

- A trial link carries every v1 feature except sign-up, accounts, and what needs a learner's email. Guest mode stays typing only ([#722](https://github.com/calmxz/Crux/issues/722)).
- What each stage needs before it starts is in [`quality-bar.md`](quality-bar.md), ticked on one stage issue per stage ([#680](https://github.com/calmxz/Crux/issues/680)).

### Who Crux is for

- Adults only (18 or over). Every way in has an "I am 18 or over" tick: sign-up, the Request access form, and the guest and trial-link entry ([#681](https://github.com/calmxz/Crux/issues/681), [#677](https://github.com/calmxz/Crux/issues/677), [#717](https://github.com/calmxz/Crux/issues/717)). How the tutor handles a learner who says they are under 18 is in [`age.md`](age.md).
- Crux is not available in the EU or the UK. Sign-up, guest mode and Request access check the country from the network address, and nothing blocks the whole site (see [`hosting.md`](hosting.md) and [`security.md`](security.md)) ([#677](https://github.com/calmxz/Crux/issues/677), [#716](https://github.com/calmxz/Crux/issues/716), [#717](https://github.com/calmxz/Crux/issues/717), [#769](https://github.com/calmxz/Crux/issues/769)).
- Crux is free. Philippine law applies, including the Data Privacy Act ([#677](https://github.com/calmxz/Crux/issues/677)).

### Money

All figures marked "for the meantime" can change if [Decide: the AI layer](https://github.com/calmxz/Crux/issues/679) is reopened (see Gaps).

- **Learners' budget:** USD 8 a month, for the meantime. Guests and trial links spend from it ([#675](https://github.com/calmxz/Crux/issues/675), [#677](https://github.com/calmxz/Crux/issues/677), [#679](https://github.com/calmxz/Crux/issues/679), [#717](https://github.com/calmxz/Crux/issues/717)).
- **Daily ceiling:** a quarter of the budget (USD 2), for the meantime. No calendar day spends more, apart from a started mastery check (see [`spending.md`](spending.md)). The owner can change it on the owner page ([#675](https://github.com/calmxz/Crux/issues/675), [#679](https://github.com/calmxz/Crux/issues/679)).
- **Changing the budget:** only as a recorded change. The one standing exception is a bigger budget for a re-run after a budget-caused miss, at most one re-run in the whole effort ([#675](https://github.com/calmxz/Crux/issues/675), [#676](https://github.com/calmxz/Crux/issues/676), [#679](https://github.com/calmxz/Crux/issues/679)).
- **Learner cap:** 25 accounts, for the meantime, counting every account ever made. The owner raises it. An email on the owner's let-in list gets past a full cap (see [`accounts.md`](accounts.md)) ([#675](https://github.com/calmxz/Crux/issues/675), [#679](https://github.com/calmxz/Crux/issues/679)).
- **The owner's own use:** outside the learner cap, the budget, the daily ceiling, the tutoring limits and every count. It spends from the owner's share, USD 3 a month ([#676](https://github.com/calmxz/Crux/issues/676), [#679](https://github.com/calmxz/Crux/issues/679)). Re-marks of learners' checks after a marking fault run in the Crux project and spend from the owner's share too ([#728](https://github.com/calmxz/Crux/issues/728)). So does the distress check in [`spending.md`](spending.md) ([#734](https://github.com/calmxz/Crux/issues/734)). So does the small call in [`operations.md`](operations.md) that tests whether Google has reopened after its cap ([#735](https://github.com/calmxz/Crux/issues/735)).
- **Tests:** test spend never counts toward the learners' budget or the Crux project's cap. Tests have their own Google Cloud project, Crux tests, capped at about USD 5 a month for now and raised by hand. Credits and the card are shared ([#678](https://github.com/calmxz/Crux/issues/678), [#679](https://github.com/calmxz/Crux/issues/679)).
- **Time:** days, weeks and months for the budget, the ceiling, the tutoring limits and budget-caused misses are in the owner's time zone. Messages give reset times in the learner's own clock ([#675](https://github.com/calmxz/Crux/issues/675), [#676](https://github.com/calmxz/Crux/issues/676)). Email shares count on Resend's day instead, 8 am to 8 am Philippine time (see [`operations.md`](operations.md)) ([#763](https://github.com/calmxz/Crux/issues/763)).
- **Hosting stays on free tiers:** Cloud Run's free credit under a USD 6 cap, and Cloud Storage at a few cents a month (about 20 GB at most, see [`files.md`](files.md)). A domain, about USD 10 to 11 a year, is bought before the trial ([#716](https://github.com/calmxz/Crux/issues/716), [#717](https://github.com/calmxz/Crux/issues/717)). Any minimum instance is a recorded change to this rule ([#716](https://github.com/calmxz/Crux/issues/716)). So is a second trip of the Cloud Run cap (see [`hosting.md`](hosting.md)) ([#735](https://github.com/calmxz/Crux/issues/735)).

The rest of the money rules are in [`spending.md`](spending.md).

### Where data lives

- Crux's data is stored in Singapore ([#716](https://github.com/calmxz/Crux/issues/716)).
- Real learner data never reaches the owner's computer. Development uses fake data, CI a throwaway database, and staging synthetic data only ([#678](https://github.com/calmxz/Crux/issues/678), [#716](https://github.com/calmxz/Crux/issues/716)).
- No network address or request header is logged for anyone. The only address records are the sign-in code limits and the wrong-link counts, each kept for an hour ([#716](https://github.com/calmxz/Crux/issues/716), [#717](https://github.com/calmxz/Crux/issues/717)).

### Crux decides, the model does not

Crux itself, not the model ([#679](https://github.com/calmxz/Crux/issues/679)):

- holds teaching state and its counts;
- applies the pass rule and does every mark's arithmetic;
- takes the age answer from the learner's tap;
- sorts the after-mastery menu;
- keeps spend and limits;
- chooses which pages are sent, and which model and level run each job.

The tutor reports to Crux only through tool calls, never by Crux reading the chat ([#679](https://github.com/calmxz/Crux/issues/679)).

Text from these sources is never an instruction: a file's text, a mastery-check answer (typed or photo), looked-up text, and a session name ([#667](https://github.com/calmxz/Crux/issues/667), [#669](https://github.com/calmxz/Crux/issues/669), [#671](https://github.com/calmxz/Crux/issues/671), [#679](https://github.com/calmxz/Crux/issues/679)).

### Speed

- The landing page shows at once. The tutor starts replying within about 5 seconds at any time of day, including after hours idle. A reply is never cut off midway, except one Google blocks (see [`ai-layer.md`](ai-layer.md)). The 5 seconds do not cover the wait while a file given with the request is read (see [`files.md`](files.md)) ([#732](https://github.com/calmxz/Crux/issues/732)). If no free host can meet this, it returns as a recorded change to the free-hosting rule ([#678](https://github.com/calmxz/Crux/issues/678)).

## Area files

The owner approves this list before any area file is written ([#680](https://github.com/calmxz/Crux/issues/680)). Each file has one subject and stays under the repo's file-size check of 5,000 tokens. That is 20,000 bytes, roughly 3,000 words with links.

Sizes estimate the current rules, stated without reasons. Source tickets decided the subject; "+" marks later tickets that changed its rules. A file states its rules once and links the shared rules above.

| File | Covers | Source tickets | Est. words |
|---|---|---|---|
| [`learning-loop.md`](learning-loop.md) | The loop end to end; requests and narrowing; topics, learning objectives and changes to them; what happens after mastery | 662, 664, 665, 666, 670 (+667, 668, 671, 677, 679) | 1,550 |
| [`teaching.md`](teaching.md) | How the tutor teaches; objective statuses and readiness; the help ladder; the diagnostic; detours and prerequisite topics; the never-ready menu; preferences | 663, 668 (+667, 670, 671, 769) | 750 |
| [`mastery-check.md`](mastery-check.md) | The offer, problems and model answers, marking and the pass rule, disputes, fails, half-done checks, photo answers | 663, 669 (+667, 671, 677, 678, 679, 716, 722, 769) | 1,050 |
| [`learning-screen.md`](learning-screen.md) | The session screen: the objectives panel, the check and its result on screen, menus and buttons, Crux's own lines, pictures, mistake marks, frontend modules | 751 (+754, 769) | 1,200 |
| [`app-shell.md`](app-shell.md) | The app around the session screen: where it opens, the session list, rename and delete, "What you've mastered", files on screen, held and sealed sessions on screen | 752 (+753, 754, 769) | 1,850 |
| [`account-screens.md`](account-screens.md) | Sign-in, the steps on opening, a locked account, the Settings page, the feedback page, closing an account and the copy page on screen | 753 (+754, 769) | 1,850 |
| [`landing-screens.md`](landing-screens.md) | The landing page, guest mode, Request access, "Who runs Crux", the legal pages, the demo video, and a trial link's entry, notices and endings on screen | 754 (+769) | 2,100 |
| [`owner-screens.md`](owner-screens.md) | The owner page, its areas and dialogs, and the daily email on screen | 755 | 2,200 |
| [`files.md`](files.md) | Files: types and limits, how files shape objectives, file mistakes, storage and conversion, pages sent to the tutor, the allowance | 667 (+669, 670, 671, 675, 677, 679, 681, 716, 717, 722) | 1,300 |
| [`sessions.md`](sessions.md) | What Crux remembers: sessions, the note, the lookup, passed work across sessions, the 7-day refresh, renaming and deleting | 671 (+664, 674, 676, 677, 678, 681, 716, 722, 731) | 800 |
| [`accounts.md`](accounts.md) | Sign-up and sign-in, codes and their limits, staying signed in, the let-in list | 674 (+675, 677, 679, 681, 717, 753, 754) | 1,250 |
| [`age.md`](age.md) | The tutor's age question, closing an under-18 account, the same for guests and trial links | 681 (+677, 679, 717, 722, 754) | 600 |
| [`spending.md`](spending.md) | Tutoring limits, Google's caps, started checks finishing, spending messages, what the owner page changes | 675 (+667, 671, 674, 676, 677, 678, 679, 716, 717, 722, 728, 731, 733, 734) | 1,100 |
| [`trial.md`](trial.md) | Guest mode, Request access and trial links, the advisory opinion, ending the trial | 677, 722 (+717, 754) | 1,750 |
| [`privacy.md`](privacy.md) | Terms of Use, Privacy Policy and processors, when the owner reads sessions, deleting and retention | 677 (+679, 681, 716, 717, 722, 753, 754) | 1,800 |
| [`misuse.md`](misuse.md) | The harm line, the misuse flag, the owner's decision, sealed flags, misuse closures | 677 (+665, 667, 732, 733, 753, 754) | 700 |
| [`feedback.md`](feedback.md) | The feedback page, counts, who sees the owner page, the go-public bar, budget-caused misses | 676 (+674, 675, 677, 678, 679, 681, 717, 722, 728, 733, 734) | 1,200 |
| [`ai-layer.md`](ai-layer.md) | Route and projects, models and call settings, the prompt, tool calls, failed and blocked calls, the maths library, the distress check's call | 679, 684 (+678, 716, 728, 733, 734, 735, 769) | 1,300 |
| [`hosting.md`](hosting.md) | Hosting and runtime, background answers, the Worker, the database, backups, environments and staging, logs, the converter, secrets | 716 (+675, 678, 679, 717, 722, 726, 732, 733, 734, 735, 750, 754, 769) | 1,800 |
| [`security.md`](security.md) | The visitor's country and address, the content security policy, the other headers, where they are set, their checks, build notes | 769 (+716, 717) | 700 |
| [`tools.md`](tools.md) | The backend's and the frontend's tools: lint, the API made from the contract, the build checks, the fallback | 750, 769 | 550 |
| [`operations.md`](operations.md) | Email sending, errors, uptime, how the owner is told, the bill, the daily job | 717 (+675, 676, 677, 679, 716, 728, 733, 734, 735, 753, 769) | 1,500 |
| [`quality-bar.md`](quality-bar.md) | What "solid" means; real-phone tests, security, accessibility, what is measured before it counts, repo and CI; the stage checklists | 678 (+677, 680, 716, 717, 722, 728, 732, 733, 734, 735, 736, 743, 750, 769) | 1,750 |
| [`ordinary-tests.md`](ordinary-tests.md) | Ordinary tests by area, component tests, browser paths and how they run | 678, 769 (+670, 671, 674, 675, 676, 677, 679, 680, 681, 716, 717, 719, 722, 728, 732, 733, 734, 735, 736, 743, 750, 755, 762) | 1,950 |
| [`ai-tests.md`](ai-tests.md) | AI tests: risk tiers, runs, the grader and the owner's spot-reads, the release gate, what stops a round | 678 (+667, 669, 679, 680, 716, 728, 732, 733, 734, 735, 736) | 1,400 |
| [`live-faults.md`](live-faults.md) | A fail on the live version: the owner's switches and what each does, re-marks after a marking fault | 678 (+669, 679, 728, 734, 735, 736, 754) | 1,600 |
| [`spec-process.md`](spec-process.md) | How this spec changes after the lock, `post-v1` issues, build tickets naming their sections, rule reports, stage issues | 680 (+750, 769) | 850 |
| [`data-model.md`](data-model.md) | What Crux stores and what each item belongs to, erasing a home, the backend modules | 719 | 2,300 |
| [`old-code.md`](old-code.md) | The comparison against the old code: the verdicts, each backend and frontend module's fate, what is copied with its tests, what is left behind, the CI removed | 750 (+769) | 1,500 |

## Gaps

These are not decided yet. Do not build them from guesses.

- **Conflicts between closed tickets:** found while writing this file, and answered by the owner on [#728](https://github.com/calmxz/Crux/issues/728). An area file takes its answer from there. The gaps no ticket was given were answered by the owner on [#731](https://github.com/calmxz/Crux/issues/731), [#732](https://github.com/calmxz/Crux/issues/732), [#733](https://github.com/calmxz/Crux/issues/733), [#734](https://github.com/calmxz/Crux/issues/734), [#735](https://github.com/calmxz/Crux/issues/735) and [#736](https://github.com/calmxz/Crux/issues/736).
- **Screens and layout:** the session screen is in [`learning-screen.md`](learning-screen.md) ([#751](https://github.com/calmxz/Crux/issues/751)), the app around it, the session list and files on screen in [`app-shell.md`](app-shell.md) ([#752](https://github.com/calmxz/Crux/issues/752)), sign-in, settings, feedback and closing in [`account-screens.md`](account-screens.md) ([#753](https://github.com/calmxz/Crux/issues/753)), the landing page, guest mode and trial links in [`landing-screens.md`](landing-screens.md) ([#754](https://github.com/calmxz/Crux/issues/754)), and the owner page and the daily email in [`owner-screens.md`](owner-screens.md) ([#755](https://github.com/calmxz/Crux/issues/755)). Area files name the screen items their rules need.
- **The AI layer may change:** research [#727](https://github.com/calmxz/Crux/issues/727) checks Claude through Anthropic's API. If it reopens [#679](https://github.com/calmxz/Crux/issues/679), the route, the models, the grader and the "for the meantime" figures can change.
- **Open hosting checks:** research [#726](https://github.com/calmxz/Crux/issues/726) (database pooler security, the Cloud Run cap and server time, alerting charges, Zoho's agreement). See [`hosting.md`](hosting.md) and [`operations.md`](operations.md).
- **The old code:** the backend's and the frontend's comparisons are in [`old-code.md`](old-code.md) ([#750](https://github.com/calmxz/Crux/issues/750), [#769](https://github.com/calmxz/Crux/issues/769)). Where the new code lives, and when the old code goes, is open on [#781](https://github.com/calmxz/Crux/issues/781). Bringing the deployment back is on the map's "Not yet specified" list.
- **Ideas v1 does not need:** on the map's "Out of scope" list until the lock, then `post-v1` issues ([#680](https://github.com/calmxz/Crux/issues/680)).
