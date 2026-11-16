# Area files

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers the area files: what each one covers, its source tickets, and its estimated size.

The owner approves this list before any area file is written ([#680](https://github.com/calmxz/Crux/issues/680)). Each file has one subject and stays under the repo's file-size check of 5,000 tokens. That is 20,000 bytes, roughly 3,000 words with links.

Sizes estimate the current rules, stated without reasons. Source tickets decided the subject; "+" marks later tickets that changed its rules. A file states its rules once and links the shared rules in [`README.md`](README.md).

| File | Covers | Source tickets | Est. words |
|---|---|---|---|
| [`learning-loop.md`](learning-loop.md) | The loop end to end; requests and narrowing; topics, learning objectives and changes to them; what happens after mastery | 662, 664, 665, 666, 670 (+667, 668, 671, 677, 679) | 1,550 |
| [`teaching.md`](teaching.md) | How the tutor teaches; objective statuses and readiness; the help ladder; the diagnostic; detours and prerequisite topics; the never-ready menu; preferences | 663, 668 (+667, 670, 671, 769) | 750 |
| [`mastery-check.md`](mastery-check.md) | The offer, problems and model answers, marking and the pass rule, disputes, fails, half-done checks, photo answers | 663, 669 (+667, 671, 677, 678, 679, 716, 722, 769, 771) | 1,050 |
| [`learning-screen.md`](learning-screen.md) | The session screen: the objectives panel, the check and its result on screen, menus and buttons, Crux's own lines, pictures, mistake marks, replies arriving and breaking, maths, screen readers, frontend modules | 751 (+754, 769, 770, 771, 780) | 1,200 |
| [`app-shell.md`](app-shell.md) | The app around the session screen: where it opens, the session list, the all-sessions page, rename and delete, "What you've mastered", files on screen, held and sealed sessions on screen | 752 (+753, 754, 769, 771, 780) | 3,050 |
| [`account-screens.md`](account-screens.md) | Sign-in, the steps on opening, a locked account, the Settings page, the feedback page, closing an account and the copy page on screen | 753 (+754, 769, 772, 776, 777) | 1,850 |
| [`landing-screens.md`](landing-screens.md) | The landing page, guest mode, Request access, "Who runs Crux", the legal pages, the demo video, and a trial link's entry, notices and endings on screen | 754 (+769, 770, 771, 772, 776, 777) | 2,100 |
| [`owner-screens.md`](owner-screens.md) | The owner page, its areas and dialogs, and the daily email on screen | 755 (+772, 777) | 2,200 |
| [`files.md`](files.md) | Files: types and limits, how files shape objectives, file mistakes, storage and conversion, pages sent to the tutor, the allowance | 667 (+669, 670, 671, 675, 677, 679, 681, 716, 717, 722) | 1,300 |
| [`sessions.md`](sessions.md) | What Crux remembers: sessions, the note, the lookup, the session search, passed work across sessions, the 7-day refresh, renaming and deleting | 671 (+664, 674, 676, 677, 678, 681, 716, 722, 731, 780) | 2,900 |
| [`accounts.md`](accounts.md) | Sign-up and sign-in, codes and their limits, staying signed in, the let-in list, registering with the Commission | 674 (+675, 677, 679, 681, 717, 753, 754, 772, 776, 777) | 1,250 |
| [`age.md`](age.md) | The tutor's age question, closing an under-18 account, the same for guests and trial links | 681 (+677, 679, 717, 722, 754, 777) | 600 |
| [`spending.md`](spending.md) | Tutoring limits, Google's caps, started checks finishing, spending messages, what the owner page changes | 675 (+667, 671, 674, 676, 677, 678, 679, 716, 717, 722, 728, 731, 733, 734, 771) | 1,100 |
| [`trial.md`](trial.md) | Guest mode, Request access, the advisory opinion, ending the trial | 677, 722 (+717, 754, 770, 772, 776, 777) | 2,050 |
| [`trial-links.md`](trial-links.md) | Trial links: opening one, the link code, erasing a link, what a link carries, misuse, when a link dies, telling a link holder | 677, 722 (+717, 770, 772, 776, 777) | 1,250 |
| [`privacy.md`](privacy.md) | When the owner reads sessions, deleting and retention | 677 (+679, 681, 716, 717, 722, 753, 770, 772, 776, 777) | 1,900 |
| [`terms-and-policy.md`](terms-and-policy.md) | Terms of Use, Privacy Policy and processors | 677 (+679, 681, 716, 717, 754, 770, 776) | 1,400 |
| [`misuse.md`](misuse.md) | The harm line, the misuse flag, the owner's decision, misuse closures | 677 (+665, 667, 732, 733, 753, 754, 772, 776, 777) | 1,850 |
| [`sealed-sessions.md`](sealed-sessions.md) | Sealed flags, what a seal tells the learner, a Reported session | 677 (+733, 772, 776, 777) | 1,350 |
| [`feedback.md`](feedback.md) | The feedback page, counts, who sees the owner page, the go-public bar, budget-caused misses | 676 (+674, 675, 677, 678, 679, 681, 717, 722, 728, 733, 734, 772) | 1,200 |
| [`ai-layer.md`](ai-layer.md) | Route and projects, models and call settings, the prompt, tool calls, failed and blocked calls, the maths library, the distress check's call | 679, 684 (+678, 716, 728, 733, 734, 735, 769, 771) | 1,300 |
| [`hosting.md`](hosting.md) | Hosting and runtime, background answers, the Worker, the database, logs, the converter, secrets | 716 (+675, 678, 717, 722, 726, 732, 733, 734, 735, 750, 754, 769, 770, 771) | 2,050 |
| [`backups-and-releases.md`](backups-and-releases.md) | Backups and the restore log, environments and staging, releases | 716 (+678, 679, 726, 735, 750, 769, 770, 772, 776, 777) | 1,200 |
| [`security.md`](security.md) | The visitor's country and address, keys in addresses, the request guards, the content security policy, the other headers, where they are set, their checks, build notes | 769 (+716, 717, 770, 780) | 2,500 |
| [`tools.md`](tools.md) | The backend's and the frontend's tools: lint, the API made from the contract, the build checks, the fallback | 750, 769 | 550 |
| [`operations.md`](operations.md) | Errors, uptime, how the owner is told, the bill | 717 (+675, 716, 728, 733, 734, 735, 753, 769, 770, 772) | 1,450 |
| [`email.md`](email.md) | Email sending, who gets the day's emails, late and refused emails, copies of data and emailed requests, the Crux email | 717 (+675, 677, 734, 735, 753, 770, 772, 776, 777) | 1,950 |
| [`dates.md`](dates.md) | When a printed date takes effect, notices that wait for email, past the last day, when Crux acts, outages, the daily job | 772 (+675, 676, 677, 679, 716, 717, 719, 728, 733, 734, 735, 753, 755, 762, 763, 764, 770, 776) | 1,700 |
| [`quality-bar.md`](quality-bar.md) | What "solid" means; real-phone tests, security, accessibility, what is measured before it counts, repo and CI; the stage checklists | 678 (+677, 680, 716, 717, 722, 728, 732, 733, 734, 735, 736, 743, 750, 769, 770, 771, 776) | 1,750 |
| [`ordinary-tests.md`](ordinary-tests.md) | Ordinary tests by area, component tests, browser paths and how they run | 678, 769 (+670, 671, 674, 675, 676, 677, 679, 680, 681, 716, 717, 719, 722, 728, 732, 733, 734, 735, 736, 743, 750, 755, 762, 770, 771, 772, 777, 780) | 1,950 |
| [`ai-tests.md`](ai-tests.md) | AI tests: risk tiers, runs, the grader and the owner's spot-reads, the release gate, what stops a round | 678 (+667, 669, 679, 680, 716, 728, 732, 733, 734, 735, 736, 771) | 1,400 |
| [`live-faults.md`](live-faults.md) | A fail on the live version: the owner's switches and what each does, re-marks after a marking fault | 678 (+669, 679, 728, 734, 735, 736, 754, 780) | 1,600 |
| [`spec-process.md`](spec-process.md) | How this spec changes after the lock, `post-v1` issues, build tickets naming their sections, rule reports, stage issues | 680 (+750, 769) | 850 |
| [`data-model.md`](data-model.md) | What Crux stores and what each item belongs to, erasing a home, the backend modules | 719 (+770, 772, 776, 777) | 2,300 |
| [`old-code.md`](old-code.md) | The comparison against the old code: the verdicts, each backend and frontend module's fate, what is copied with its tests, what is left behind, the CI removed | 750 (+769, 771, 780) | 1,500 |
