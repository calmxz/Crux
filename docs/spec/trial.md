# The trial and opening

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers the first two of the main file's "Stages": the trial without accounts, and the advisory opinion before opening. Trial links are in [`trial-links.md`](trial-links.md). Sign-up from opening is in [`accounts.md`](accounts.md).

## During the trial

- Crux is deployed with sign-up off. Sign-in is for the owner only (see [`accounts.md`](accounts.md)) ([#677], [#728] Answer 5).
- The landing page shows the demo video and guest mode, in place of the pre-written example ([#677]). It also offers Request access ([#717]).
- From the EU or the UK, the public link shows the demo video and the region message (see [`accounts.md`](accounts.md)), with no guest mode and no Request access ([#677], [#717]).
- The trial stays without accounts. Crux erases the email once the invite is sent, and keeps no record of its own that ties a person to a trial link ([#717], [#722]). The one exception is the holder's own: an email they send quoting their link code, deleted once answered (see [The link code](trial-links.md#the-link-code)) ([#755]).
- If the trial does not show that opening is worth it, Crux stays a portfolio project, and guest mode stays ([#677], [#733]).

## Entry

Guests and trial-link users pass the same step, once per browser, before the first reply. It has two required ticks ([#677], [#717]):

- "I am 18 or over"
- "I agree to the Trial Terms and Privacy Notice"

A tap on Yes to the age question clears them on that browser (see [`age.md`](age.md)), and a change to the Trial Terms shows them again ([#733]).

## Guest mode

The public link offers two choices ([#677]):

- **A sample topic:** one of 2 or 3, each the full loop on one learning objective, about 10 minutes. It is taught, then checked by a 2-problem mini check with marking (see [`mastery-check.md`](mastery-check.md)). It earns nothing. It ends at the result, with Crux's own fixed line in place of the after-mastery menu (see [`landing-screens.md`](landing-screens.md)) ([#754]).
- **The guest's own topic:** narrowed and taught as usual, for up to 10 tutor replies. The limit shows before they start: "Guest mode: up to 10 tutor replies. Nothing is saved. Don't type personal details."

At the limit: "That's the end of guest mode for your own topic", with links to the sample topics and, while the trial runs, Request access ([#677], [#717], [#733]).

- Guest mode is typing only (see the main file's "Stages"). A guest who tries to upload a file or a photo sees "Uploading your own files needs a trial link." with a Request access button while the trial runs, and nothing is stored ([#722], [#733]).
- Nothing is kept after the tab closes ([#677]). The tab holds the conversation, signed by Crux, and Crux stores nothing for a guest (see [`data-model.md`](data-model.md)) ([#719]).
- Replies are counted per browser by a random ID, which the browser holds with the count, signed ([#719]). It is never used for counting learners or for analytics ([#677]).
- Guest mode has its own daily spend cap inside the daily ceiling, USD 0.25 for the meantime, changeable on the owner page. The cap stays the same after the trial ends, if guest mode stays on ([#734]).
- Guest mode also has a monthly cap, USD 2 for the meantime, changeable on the owner page, so guests cannot use most of the month's budget ([#719]).
- **When guest mode stops:** at the guest cap, the monthly guest cap, the daily ceiling or the month's budget, a guest sees "Guest mode is full for today. Back tomorrow." (for the month, "Guest mode is full for this month. Back on 1 Dec.", [#754]) and the demo video ([#677], [#679], [#734]). Someone who has not typed sees only that line and the video, with Request access while the trial runs ([#734], [#754]). A guest's mini check stops at them like any guest reply, since a guest can resend an older saved state (see [`data-model.md`](data-model.md)) ([#719]). An open age question still works ([#675], [#679], [#733], [#734]). If the stop caught a message, the distress check in [`at-a-limit.md`](at-a-limit.md) runs ([#734]).
- When a workspace limit or the credit stops Crux, a guest sees the month's line and the video. Anthropic refuses the calls, so a mini check cannot finish. It is dropped, since guests keep nothing ([#734], [#802]).
- The owner page has a switch for guest mode (see [`live-faults.md`](live-faults.md)) ([#678]).

## Request access

- The form has the email, the human check, "I am 18 or over", and this line: "Trial places are limited. Request once; we'll email you a private link if you're approved. We keep your email only until we approve or decline your request, at most 30 days. [Privacy Notice]" ([#717]).
- Each new request pushes to the owner's phone. The owner page lists waiting requests, and the owner approves or declines each one ([#717]).
- A request not decided in 30 days is declined at the last daily run within them, and one still waiting when the trial ends at the first run after it ([#717], [#728] Answer 7, [#772]).
- Every request is new. Crux keeps no record of past requests, and the owner is the duplicate check ([#717]).

**On approval:** Crux makes a trial link with a random 128-bit key, emails it, and erases the email. The owner never sees the link. The invite says ([#717]):

> You're in. Tap to start: [Open Crux]. Using another device? Open this email there and tap the same link. Keep this email: it's your only way back in. Trial places are limited, so a lost link may not be replaced.

**On decline:** a short email, then the email is erased ([#717]):

> Thanks for asking about Crux. The trial is limited for now. If Crux opens to everyone, you'll be able to sign up then. Follow [the owner's LinkedIn] to hear when it does.

If the day's emails have run out, an invite or decline waits for Resend's next day, from 8 am Philippine time ([#763]). A request is never kept past its 30 days, so one still unsent then is erased without an email ([#717]).

## Money and counts

- Guests and trial links spend from the learners' budget and the daily ceiling (see the main file's "Money") ([#677]).
- Nothing in the trial counts toward the go-public bar. The window starts on the day of the first public post ([#677]).
- The dated under-18 count does include trial endings (see [`age.md`](age.md)) ([#728]).

## The trial's notices

**The Trial Terms** carry the upload lines decided for accounts (see [`terms-and-policy.md`](terms-and-policy.md)) ([#722]). They also say a quote tick can't be undone once the link has ended ([#734]).

**The Trial Privacy Notice** says ([#677], [#717], [#722], [#728], [#733], [#762]):

- A request's email is kept at most 30 days.
- "Your invite stays in our email provider's log for 30 days, and in its backups for up to 7 days after."
- Files and photo answers are kept with the link's sessions. They are erased at once when removed or when their session is deleted, and erased with the link when it dies, apart from those in a sealed session reported to the authorities ([#719]).
- Turnstile's signals go partly to Cloudflare's own use, and the Crux email is a Gmail with no processor agreement during the trial (see [`terms-and-policy.md`](terms-and-policy.md)).
- Error reports carry no learner text.
- "On a trial link, your browser remembers your theme choice (Match my device, Light or Dark). Crux never receives it." ([#779])
- The dated under-18 count exists.
- Network addresses: wrong-link counts for an hour, the burst guard, and hand blocks for 12 to 36 hours, longer only while the daily job is down or a lift fails; the owner reads Cloudflare's request analytics only to find a network to block ([#770]).
- A decline saves its date, kind and place in its session, for as long as [`misuse.md`](misuse.md) sets out ([#719]).
- "Crux handles the kinds of requests the tutor declines as possibly sensitive information." ([#776])
- Feedback answers and quote permissions are kept 6 months after the trial ends, or 12 months after the link died, whichever comes first, unless the holder erases the link ([#755]). Those of a published quote stay until the owner removes it ([#719]).
- A sealed session is kept longer only if reported to the authorities ([#719]).
- Deleting a session erases it, but another session may still mention something from it.
- The owner may read flagged or shared sessions (see [`privacy.md`](privacy.md)).
- A holder who does not visit cannot be reached with a notice.
- An email quoting a link code is kept until answered, then deleted ([#755]).
- "Erase this trial link" in Settings erases the link's sessions, files and feedback ([#755]).
- Until opening, its contacts are privacy@ and the owner's LinkedIn, naming the owner as the one who built Crux (see [`terms-and-policy.md`](terms-and-policy.md)) ([#754]).

## Known gaps

- Whether the entry tick "I agree to the Trial Terms and Privacy Notice" counts as consent specific to the purpose (Data Privacy Act, section 13(a)) is unchecked. The owner chose the notice line over a link-only tick ([#776]).
- Whether the trial treats learning progress as possibly sensitive is open ([#776]).

## Ending the trial

- The owner ends the trial with a button on the owner page, whether or not Crux will open. It takes a date at least 7 days ahead, which link holders see, and links end at 12:00 am after it. Once passed, it can't be moved or taken back ([#733], [#772]).
- Once set, the date can move later or be taken back, never earlier. A date set after a take-back is never earlier than the one taken back. Link holders see a fresh notice at their next visit ([#755]).
- Every trial link dies, with any flag still waiting and any notice not yet seen. The anonymous feedback answers and quote permissions stay as [`feedback.md`](feedback.md) sets out ([#677], [#719], [#722], [#733], [#734]). The stubs are erased, and any old link shows "The trial has ended". A sealed session marked "Reported" with no answer recorded stays ([#719], [#777]).
- Waiting requests are declined with the email above. An invite still waiting to send gets the decline email in its place ([#717], [#733]).
- Request access goes. Guest mode stays until sign-up opens, or for good if Crux stays a portfolio project ([#677], [#733]). When sign-up opens, the landing page shows the pre-written example (see [`accounts.md`](accounts.md)) ([#677]).
- Nothing from the trial is carried into an account ([#677]).

## The advisory opinion

- If the trial shows a public opening is worth it, the owner first sends the National Privacy Commission a Request for Advisory Opinion, at least a month before opening ([#677]). It goes after the trial, not before ([#717], [#722]).
- It follows NPC Circular 18-01: a letter to the Privacy Commissioner and Chairman, by email or in person, with the facts, the questions and a certification that the matter is not pending. An answer comes within 20 working days. It is non-binding, and costs PHP 7,500 plus PHP 75, paid in advance (NPC Circular 2023-01). The NPC turns away "anticipatory and speculative" requests ([#677], [#762]).
- It asks ([#677]):
  - Is Crux "automated decision-making or profiling" that must be registered under NPC Circular 2022-04, Section 5?
  - If not, is the sworn declaration still needed?
  - Is a learner's progress sensitive information about education?
  - Are declined kinds, such as methods of self-harm or explicit sexual content, sensitive information about health or sexual life? ([#764])

## Opening

The before-opening checklist and registering with the Commission are in [`accounts.md`](accounts.md#opening).

## On screen

The landing page, guest mode, the entry ticks and the trial link notice, the Request access page, the one-time device note, the network-refused message, what a dead or switched-off link shows, the guest's upload line and the link holder's notices are in [`landing-screens.md`](landing-screens.md) ([#754]). The rest of the layout is not decided (see the main file's Gaps). The owner page's requests list, trial-link list, dead links, guest cap setting and the end of the trial are in [`owner-screens.md`](owner-screens.md) ([#755]).

[#675]: https://github.com/calmxz/Crux/issues/675
[#677]: https://github.com/calmxz/Crux/issues/677
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#722]: https://github.com/calmxz/Crux/issues/722
[#728]: https://github.com/calmxz/Crux/issues/728
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#754]: https://github.com/calmxz/Crux/issues/754
[#755]: https://github.com/calmxz/Crux/issues/755
[#762]: https://github.com/calmxz/Crux/issues/762
[#763]: https://github.com/calmxz/Crux/issues/763
[#764]: https://github.com/calmxz/Crux/issues/764
[#770]: https://github.com/calmxz/Crux/issues/770
[#772]: https://github.com/calmxz/Crux/issues/772
[#776]: https://github.com/calmxz/Crux/issues/776
[#777]: https://github.com/calmxz/Crux/issues/777
[#779]: https://github.com/calmxz/Crux/issues/779
[#802]: https://github.com/calmxz/Crux/issues/802
