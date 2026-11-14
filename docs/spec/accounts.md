# Accounts and sign-in

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers how someone gets an account and comes back to it, from opening on. Who may join is in the main file's "Who Crux is for". The age question is in [`age.md`](age.md). Closing an account is in [`privacy.md`](privacy.md). The way in before opening is in [`trial.md`](trial.md).

## Before opening

- Sign-up is off during the trial. Sign-in by Google or code works only for the owner's own email addresses ([#677], [#717], [#728] Answer 5). A test address goes on the same list (see [`feedback.md`](feedback.md)) ([#734]).
- No learner signs in during the trial. Trial-link users return through the link only (see [`trial.md`](trial.md)) ([#717], [#728] Answer 5).
- During the trial the landing page has no "Sign in", and the owner opens the sign-in page by its address. An email not on the list, by code or by Google, is refused before any code is sent: "Sign-up isn't open yet. To try Crux, use guest mode or ask for a trial link." From the EU or the UK, it gets the region message instead (see [`landing-screens.md`](landing-screens.md)) ([#754]).
- The rest of this file holds from opening.

## Ways in

- One page serves sign-up and sign-in. It offers **Continue with Google** and **Email me a code** ([#674]).
- There is no password, no emailed sign-in link and no other provider ([#674]). The trial link is an emailed link, for the trial only ([#717]).
- There is no separate email-verification step ([#674]).
- The same email by code and by Google is one account, matched on the email ([#674]).
- Crux's own backend runs both ways in. There is no sign-in service, and Supabase never sees the browser ([#717]).
- Nothing is typed to the tutor without an account, and there is no guest mode ([#674], [#677]).
- The landing page shows a pre-written example: a request, the tutor's narrowing questions and the learning objectives it proposes, written once, with no AI call ([#674], [#677]). The demo video stays beside it ([#754]).

### Continue with Google

- Crux uses the plain OAuth 2 redirect and asks only for `openid email`. Google returns only the email and whether it is verified. Google's ready-made sign-in button is not used ([#717]).
- Google's name and photo are never asked for or kept ([#674], [#717]).

### Email me a code

- The code is 6 random digits, stored scrambled. It is typed into the same page, lasts 10 minutes, and dies after 5 wrong tries ([#674], [#717]).
- A human check runs first, Cloudflare Turnstile in Managed mode with the `interaction-only` appearance. Most visitors see nothing; a box to tick appears only when Cloudflare is unsure ([#674], [#717], [#762]).
- Codes are limited to 3 an hour and 10 a day per email address, and 20 an hour per network address ([#674], [#717]). What these records keep is in [`privacy.md`](privacy.md).
- Throwaway email services are not blocked, and new accounts have no daily cap ([#674]).

### When the sender runs out

Email sending, and how many of the day's emails can be codes, is in [`operations.md`](operations.md) ([#735]).

- A code request the sender cannot serve shows: "We can't send codes right now. Use Continue with Google, or try again after 8:00 am." The time is the reset of Resend's day (see [`operations.md`](operations.md)) in the learner's own clock, "after 9:00 am" in Tokyo. When it falls on the learner's next date, the message adds "tomorrow": at 9 pm, "…try again after 8:00 am tomorrow". When the month ran out, when Resend is down, or while a breach notice is still sending, it says "try again later" instead ([#674], [#763]).
- The owner page shows a dated count of code requests refused because the sender ran out for the day or the month, each email address once per day ([#674], [#728] Answer 6).

### Inside LinkedIn's or Facebook's built-in browser

- Both buttons show there ([#674]).
- Crux detects the built-in browser where it can. Tapping Google there sends the learner to the same page in the phone's normal browser ([#674]).
- On iPhone, or wherever the jump fails, Crux shows its own note, naming the app it is in: "Google sign-in doesn't work inside the LinkedIn app. Open this page in your browser, or use a code." ([#674]).
- The code works inside these browsers ([#674]). The real-phone tests are in [`quality-bar.md`](quality-bar.md) ([#678]).

## From the EU or the UK

The rule is in the main file's "Who Crux is for".

- With a code: when someone taps "Email me a code", Crux checks the country. From the EU or the UK, an email with no account sees "Crux isn't available in your region yet." No code is sent ([#677], [#733]).
- With Google: Google hands back the email. If it has no account, Crux drops it and shows the same message ([#733]).
- Crux checks the email against its accounts and does not store it. No account is made and nothing is kept ([#677], [#733]).
- An email with an account signs in as normal from anywhere ([#733]).

## New learners: "One more thing"

- After the code or Google, an email with no account gets one step, "One more thing", with two required ticks and a Start button that needs both ([#674]):
  - "I am 18 or over"
  - "I agree to the Terms, and to Crux keeping my learning progress and what I share with the tutor, as the Privacy Policy explains" ([#677])
- The Terms and the Privacy Policy are linked from the step ([#674]).
- The account is made only on Start. A learner who leaves at the step has no account, and nothing is counted ([#674]).
- Start adds 1 to "signed up" inside a window (see [`feedback.md`](feedback.md)) ([#674], [#676]).
- Returning learners never see the step ([#674]).
- Crux keeps each tick with its date and the version of the Terms and Privacy Policy agreed to, for as long as the account exists. It keeps no birth date or age ([#674], [#677], [#681]).

## The learner cap

The cap itself is in the main file's "Money".

- Past the cap, an email with no account sees, at "One more thing": "Crux is full for now. Try again later.", with a tick-box, "Email me if spots open". No account is made. Only a ticked email is kept, for that one message ([#674], [#675]). To count "told Crux is full" once a day, a scrambled copy of the email is kept for that day only ([#719]).
- When the owner raises the cap, everyone who ticked gets one email, as soon as the sender's share allows (see [`operations.md`](operations.md)), in no order. There is no waitlist ([#675], [#735]).
- Learners with an account sign in as usual ([#675]).
- A spot never frees up by itself. A closed account keeps its spot, and a learner who returns after closing signs up afresh and takes a new spot ([#675], [#677]).
- The owner page's cap line and counts are in [`spending.md`](spending.md) ([#675]).

### The let-in list

- The owner adds an email on the owner page. That person signs up normally and gets past a full cap at "One more thing" ([#679]).
- They are an ordinary learner, with tutoring limits, spend in the budget, and counted like anyone ([#679]).
- The owner page shows "25 + N let in" ([#679]).
- An entry is erased at sign-up, or after 7 days. For any entry, the owner can choose "keep until I remove it", which still ends at sign-up ([#679]).
- Expiry runs in the daily housekeeping job, and sign-up also ignores an expired entry ([#728] Answer 7).
- Open sign-up stays: the list only adds named people past a full cap ([#679]).
- An entry also gets past the misuse block below, and the owner gets a note that this email was blocked. The person starts with a new, empty account ([#733]).

### The misuse block

- A blocked email (see [`misuse.md`](misuse.md) for how long) is checked at "One more thing", after the code or Google and before the cap. It sees a short message, and no account is made ([#677], [#733]).

## What an account holds about the person

- Crux keeps only the email to know who someone is. No name is asked or kept ([#674]).
- The tutor uses a name only if the learner types one, and only in that session. A name is not a preference ([#674]).
- The email is the account. It cannot be changed in v1. A learner who loses the inbox loses the way in, and a new email means a new, empty account ([#674]).

What else an account keeps is in [`sessions.md`](sessions.md), and the marks in [`feedback.md`](feedback.md).

## Staying signed in

- A learner stays signed in on that browser until they sign out, or until 30 days pass without a visit: any signed-in request, opening the app included. There is a Sign out button ([#674], [#719]).
- Closing the account signs the learner out on that browser. Other browsers stay signed in, and show "Keep my account" on opening ([#753]).
- This uses a sign-in cookie that the backend checks on each call. It is never used for counting ([#674], [#717]).

## Steps on opening Crux

These come from [`privacy.md`](privacy.md). They show the next time a learner opens Crux, on any browser, whether or not they had to sign in ([#677], [#733]):

- During a closing's 7 days: "Keep my account / Sign out".
- After a change that matters: the "terms changed" step.
- After a misuse warning or dismissal: the misuse card, which comes from [`misuse.md`](misuse.md) ([#764]).

If several apply, the order is: a lock, the age question (see [`age.md`](age.md)), the misuse card, "Keep my account", then the terms step ([#733], [#764]).

## On screen

The sign-in page, "One more thing" with its two ticks, the in-app-browser note, the sender-out and too-many-requests messages, "Too many codes today", the region message, the Sign out button, "Crux is full for now" with its tick-box and the misuse block's message are in [`account-screens.md`](account-screens.md) ([#753]). The rest of the layout is not decided (see the main file's Gaps). The landing page's pre-written example and the trial's sign-in refusal are in [`landing-screens.md`](landing-screens.md) ([#754]). The owner page's let-in list, "25 + N let in" and refused-codes count are in [`owner-screens.md`](owner-screens.md) ([#755]).

[#674]: https://github.com/calmxz/Crux/issues/674
[#675]: https://github.com/calmxz/Crux/issues/675
[#676]: https://github.com/calmxz/Crux/issues/676
[#677]: https://github.com/calmxz/Crux/issues/677
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#681]: https://github.com/calmxz/Crux/issues/681
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#728]: https://github.com/calmxz/Crux/issues/728
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#753]: https://github.com/calmxz/Crux/issues/753
[#754]: https://github.com/calmxz/Crux/issues/754
[#762]: https://github.com/calmxz/Crux/issues/762
[#755]: https://github.com/calmxz/Crux/issues/755
[#763]: https://github.com/calmxz/Crux/issues/763
[#764]: https://github.com/calmxz/Crux/issues/764
