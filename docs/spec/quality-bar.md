# The quality bar

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what "solid" means, the real-phone tests, security, accessibility, what is measured before it counts, the repo, and what each stage needs before it starts. Ordinary tests are in [`ordinary-tests.md`](ordinary-tests.md), and AI tests in [`ai-tests.md`](ai-tests.md). How a stage's list is ticked is in [`spec-process.md`](spec-process.md).

## Who "solid" is for

Two bars, both met before sharing: the app (what learners, and recruiters trying it, experience) and the repo (what technical interviewers read). When time runs short, the app comes first ([#678]).

## The first click

The rule is in the main file's "Speed". It is checked by hand on the owner's phone, after an hour with no use, on 3 different days ([#678]). What Crux tries if it fails is in [`hosting.md`](hosting.md) ([#716]).

## Ordinary tests

The ordinary tests, the component tests and the browser paths are in [`ordinary-tests.md`](ordinary-tests.md) ([#678], [#769]).

## Real-phone tests

These run on the owner's Android phone ([#678]). iPhone is untested: a known gap from the trial on, since link holders and Request access reach Crux from phone apps. A failed request can be tried again in the phone's browser, and the invite link works again from the email ([#678], [#717], [#736]).

- **Before the trial:** Turnstile passes inside LinkedIn's and Facebook's apps on the Request access form. A trial link opened from the Gmail and Outlook apps lands signed in and stays so ([#717]).
- **Before opening, and whenever sign-in changes:** the Google button inside those two apps jumps to the phone's browser or shows Crux's note, never Google's error page. The code works inside them, including switching to the mail app and back ([#674], [#678]). This also settles whether LinkedIn's jump works on Android ([#678]).

## Security

- GitHub push protection refuses known key formats at GitHub. Betterleaks stops a secret at commit on the owner's computer, and fails in CI ([#717]).
- osv-scanner fails on any known hole in the libraries Crux uses, unless a written exception gives a reason and an expiry date. Dependabot opens fix pull requests ([#717]).
- osv-scanner also scans the built backend image, under the same rule. hadolint checks the backend Dockerfile ([#750]).
- CodeQL on the backend and the frontend blocks a merge on a finding of high or above, until it is fixed or dismissed with GitHub's reason. Medium and low findings show and do not block. CodeQL also runs weekly; a finding there on unchanged code is an alert, fixed by its own pull request ([#750], [#769]).
- Before opening, the owner works through the OWASP Top 10 ([#678]).

## Accessibility

- Every screen, the owner pages included, meets WCAG 2.2 AA ([#769]).
- The proof ([#769]):
  - oxlint's jsx-a11y rules;
  - axe (`@axe-core/playwright`) inside the browser paths (see [`ordinary-tests.md`](ordinary-tests.md));
  - a contrast test over both themes' colours, the diagrams' and graphs' colours included, against AA's ratios: 4.5:1 for text, and 3:1 for large text, interface parts and the parts of a picture needed to read it;
  - the owner's own keyboard and screen-reader pass before the trial.
- How a picture reads as text is in [`learning-screen.md`](learning-screen.md) ([#769]).

## Knowing when something is wrong

The tools are in [`operations.md`](operations.md) ([#717]).

- Phone notifications come within minutes: errors from Crux, and the outside check ([#678], [#717]). Error Reporting goes quiet for 6 hours after 20 notifications in an hour, and the uptime check is separate ([#717]).
- The services' security emails go straight to the owner's own email ([#717]).
- A one-page breach plan is written before the trial. It has the National Privacy Commission notice and the learner email already drafted, so the 72 hours from knowing are spent filling in and sending ([#678]). For link holders, it drafts the on-screen notice in [`trial.md`](trial.md) ([#733]).

## Measured before it counts

**Before the trial, on the owner's own sittings** ([#678]):

- A week of Crux's spend count against Google's bill. More than 10% apart tightens the limits by the gap.
- The cost per reply of the note at 40 mastered topics, and the cost of a lookup reply. If either is too costly, the owner decides then, as a recorded change ([#732]).

**During the trial, from trial-link users** ([#678], [#679], [#717]):

- Sittings per mastery. More than 3 means the tutoring limits and the learner cap are revisited before opening.

The age question's reliability on the chosen model is what the high-risk age tests measure ([#678]).

## Build checks

These settle how Google's services behave, while that part is built:

- that `OFF` holds on Agent Platform for the pinned models; how a block arrives mid-stream; whether a blocked attempt is charged ([#735]);
- whether Gemini reads each listed image format ([#732]);
- whether Gemini can read a topic's pages straight from the bucket on the global address ([#716]);
- the smoke test: the model-call-only role is enough for the service accounts, after which the Express API keys are deleted ([#716]).

## The repo

- **The README:** what Crux is, the live link, how to run it locally, an architecture section with a diagram, the key decisions with their reasons, and how Crux tests its AI: the tiers, the grader, and what blocks a release ([#678]). The decisions link the closed tickets and `spec-change` issues ([#680]).
- **CI:** tests, style checks and type checks ([#678]).

## What each stage needs

- A test runs before the first stage where someone other than the owner can reach its feature. A feature only accounts have is tested before opening ([#678], [#736]).
- Each item says who ticks it: **check** (an agent, with proof) or **owner** ([#680]).
- Items done by hand on live, such as the phone tests and the alerts, are done before the stage starts, and read no learner's data ([#736]).

### Before the trial

| Item | Who |
|---|---|
| Every AI test passes, including those on files and photo answers ([#678], [#722]) | check |
| The tutor's instructions frozen, and the test cap raised first if the deep round will not fit ([#736]) | owner |
| A deep round, on the version that starts the trial ([#678]) | check |
| The grader judges its example list correctly ([#678]) | check |
| Every ordinary test for what guests and trial links can reach passes, including the isolation test ([#678], [#736]) | check |
| The first-click speed, on 3 days ([#678]) | owner |
| The real-phone tests for the trial ([#717]) | owner |
| The spend, note and lookup measures ([#678]) | owner |
| The fidelity test on real decks: Word equations, SmartArt, speaker notes ([#716], [#722]) | check |
| The build checks, and the smoke test with the Express keys deleted ([#716], [#732], [#735]) | check |
| A deliberate error reaches the owner's phone within minutes, which also proves the request-log filter keeps Crux's own logs ([#717]) | owner |
| An uptime alert and a new-request push reach the phone, and so do two requests 2 minutes apart. The Google Cloud app receives a push ([#717], [#735], [#762]) | owner |
| The breach plan, with how the NPC takes breach notices confirmed ([#678], [#762]) | owner |
| A test restore of a dump that replays the log ([#716], [#735]) | check |
| The Trial Terms and Trial Privacy Notice published ([#677], [#717]) | owner |
| The spend caps set: the Crux and Crux tests projects, and Cloud Run on live and staging ([#679], [#716]) | owner |
| The domain bought and verified with Resend, and Email Routing to the Crux Gmail ([#717]) | owner |
| The billing export on, before the first Gemini call in the Crux project ([#717]) | owner |
| Essential Contacts set ([#717]) | owner |
| Push protection on ([#717]) | check |
| The processor terms of Google Cloud, Cloudflare, Supabase and Resend accepted ([#717]) | owner |
| Two-step sign-in on the Resend account ([#717]) | owner |
| The crisis line's number and link verified, and the directory's terms read ([#735]) | owner |
| The owner's keyboard and screen-reader pass over every screen, the owner pages included ([#769]) | owner |
| The live headers check: the headers on the live address, and only scripts the build made on the landing page and a legal page (see [`security.md`](security.md)) ([#769]) | check |
| Turnstile's hostname check proven on staging, with real keys (see [`security.md`](security.md)) ([#769]) | check |

### Before opening

Done before anyone but the owner signs up, even privately to one friend ([#677]).

| Item | Who |
|---|---|
| Every ordinary test for what only accounts reach passes: sign-up and sign-in, the code limits, account closing and the idle warnings, the age tick-box, and the rest ([#678], [#717], [#736]) | check |
| The real-phone tests for opening ([#678]) | owner |
| The tutor's instructions frozen, and the test cap raised first if the deep round will not fit ([#736]) | owner |
| A deep round, on the version that opens ([#678]) | check |
| The OWASP self-review ([#678]) | owner |
| The README ([#678]) | check |
| Sittings per mastery reviewed ([#678]) | owner |
| The advisory letter sent, at least a month before opening ([#677]) | owner |
| The Terms and Privacy Policy published, with the officer's contact ([#677]) | owner |
| The reworded consent tick and the EU/UK check in sign-up ([#677]) | check |
| The Crux email's switch: Zoho if its agreement covers the free plan, otherwise Workspace, with trial mail moved or deleted ([#717]) | owner |
| The Sentry judgement, with its address settings if added ([#717]) | owner |
| Google's sign-in screen moved to production, with the Privacy Policy on the domain ([#717]) | owner |
| The crisis line's number and link verified again, and the directory's terms read ([#735]) | owner |

## Gaps

- **Whether warm-on-open meets the 5 seconds off-peak.** Example: Ana sends her first message 3 seconds after opening at 6 am, before the backend is up ([#716]).
- **How a screen reader hears a reply while it streams, and how maths written in LaTeX is read out:** open on [#771] ([#769]).
- **How the owner meets the 72-hour rule when nobody is watching.** The breach plan covers the writing. Example: the host emails on a Friday night that its database was exposed ([#677]).

[#674]: https://github.com/calmxz/Crux/issues/674
[#677]: https://github.com/calmxz/Crux/issues/677
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#680]: https://github.com/calmxz/Crux/issues/680
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#722]: https://github.com/calmxz/Crux/issues/722
[#732]: https://github.com/calmxz/Crux/issues/732
[#733]: https://github.com/calmxz/Crux/issues/733
[#735]: https://github.com/calmxz/Crux/issues/735
[#736]: https://github.com/calmxz/Crux/issues/736
[#750]: https://github.com/calmxz/Crux/issues/750
[#762]: https://github.com/calmxz/Crux/issues/762
[#769]: https://github.com/calmxz/Crux/issues/769
[#771]: https://github.com/calmxz/Crux/issues/771
