# The trial and opening

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them. Where this file names an area file not yet written, use that file's source tickets in the main file's index.

This file covers the first two of the main file's "Stages": the trial without accounts, and the advisory opinion before opening. Sign-up from opening is in [`accounts.md`](accounts.md).

## During the trial

- Crux is deployed with sign-up off. Sign-in is for the owner only (see [`accounts.md`](accounts.md)) ([#677], [#728] Answer 5).
- The landing page shows the demo video and guest mode, in place of the pre-written example ([#677]). It also offers Request access ([#717]).
- From the EU or the UK, the public link shows the demo video and the region message (see [`accounts.md`](accounts.md)), with no guest mode and no Request access ([#677], [#717]).
- The trial stays without accounts. Crux erases the email once the invite is sent, and keeps no record of its own that ties a person to a trial link ([#717], [#722]).
- If the trial does not show that opening is worth it, Crux stays a portfolio project, and guest mode stays ([#677], [#733]).

## Entry

Guests and trial-link users pass the same step, once per browser, before the first reply. It has two required ticks ([#677], [#717]):

- "I am 18 or over"
- "I agree to the Trial Terms and Privacy Notice"

A tap on Yes to the age question clears them on that browser (see [`age.md`](age.md)), and a change to the Trial Terms shows them again ([#733]).

## Guest mode

The public link offers two choices ([#677]):

- **A sample topic:** one of 2 or 3, each the full loop on one learning objective, about 10 minutes. It is taught, then checked by a 2-problem mini check with marking (see [`mastery-check.md`](mastery-check.md)). It earns nothing.
- **The guest's own topic:** narrowed and taught as usual, for up to 10 tutor replies. The limit shows before they start: "Guest mode: up to 10 tutor replies. Nothing is saved. Don't type personal details."

At the limit: "That's the end of guest mode for your own topic", with links to the sample topics and, while the trial runs, Request access ([#677], [#717], [#733]).

- Guest mode is typing only (see the main file's "Stages"). A guest who tries to upload a file or a photo sees "Uploading your own files needs a trial link." with a Request access button while the trial runs, and nothing is stored ([#722], [#733]).
- Nothing is kept after the tab closes ([#677]).
- Replies are counted per browser by a random ID. It is never used for counting learners or for analytics ([#677]).
- Guest mode has its own daily spend cap inside the daily ceiling, USD 0.25 for the meantime, changeable on the owner page. The cap stays the same after the trial ends, if guest mode stays on ([#734]).
- **When guest mode stops:** at the guest cap, the daily ceiling or the month's budget, a guest sees "Guest mode is full for today. Back tomorrow." (for the month, "Back on 1 Dec.") and the demo video ([#677], [#679], [#734]). Someone who has not typed sees only that line and the video ([#734]). A mini check already started finishes first, past all three, and an open age question still works ([#675], [#679], [#733], [#734]). If the stop caught a message, the distress check in [`spending.md`](spending.md) runs ([#734]).
- When Google's cap stops Crux, a guest sees the month's line and the video. Google refuses the calls, so a mini check cannot finish. It is dropped, since guests keep nothing ([#734]).
- The owner page has a switch for guest mode (see `ai-tests.md`) ([#678]).

## Request access

- The form has the email, the human check, "I am 18 or over", and this line: "Trial places are limited. Request once; we'll email you a private link if you're approved. We keep your email only until we approve or decline your request, at most 30 days. [Privacy Notice]" ([#717]).
- Each new request pushes to the owner's phone. The owner page lists waiting requests, and the owner approves or declines each one ([#717]).
- A request not decided in 30 days, or still waiting when the trial ends, is declined ([#717]). The 30-day declines run in the daily housekeeping job ([#717], [#728] Answer 7).
- Every request is new. Crux keeps no record of past requests, and the owner is the duplicate check ([#717]).

**On approval:** Crux makes a trial link with a random 128-bit key, emails it, and erases the email. The owner never sees the link. The invite says ([#717]):

> You're in. Tap to start: [Open Crux]. Using another device? Open this email there and tap the same link. Keep this email: it's your only way back in. Trial places are limited, so a lost link may not be replaced.

**On decline:** a short email, then the email is erased ([#717]):

> Thanks for asking about Crux. The trial is limited for now. If Crux opens to everyone, you'll be able to sign up then. Follow [the owner's LinkedIn] to hear when it does.

If the day's emails have run out, an invite or decline waits for the next day. A request is never kept past its 30 days, so one still unsent then is erased without an email ([#717]).

## Trial links

### Opening one

- The first time this link opens on a browser, the entry ticks show if they have not been given there, with this notice ([#717], [#722], [#733]): "This link is for you only. Anyone with it sees your sessions and uses your limit. If it's used on more than 3 browsers, it may be switched off. Don't type or upload personal details, such as your name on a problem sheet."
- The link is then swapped for a sign-in cookie, and the key leaves the address bar. That browser stays signed in until 30 days without a visit ([#717]).
- Another device opens the same link from the invite email and sees the same sessions. A one-time note after the first sign-in says: "To use Crux on another device, open your invite email there and tap the link." ([#717])
- A link works from anywhere, including the EU and the UK, like an account (see [`hosting.md`](hosting.md)) ([#735]).
- There is no device code and no "copy my link" ([#717]). A new link opened on a browser replaces the old sign-in there ([#733]).
- A person who loses the email asks again and, if approved, gets a new, empty trial space ([#717]).
- The key is stored scrambled. A network that tries 10 wrong links in an hour is refused for the rest of the hour. Its address is kept only that hour ([#717]).

### What a link carries

The main file's "Stages" sets the rule. In detail:

- Every step of the learning loop, with files in a session and photo answers in a check, under the rules decided for accounts (see [`files.md`](files.md) and [`mastery-check.md`](mastery-check.md)) ([#722]).
- The same tutoring limit as an account (see [`spending.md`](spending.md)) ([#677]).
- An account's storage allowance, in the shared store (see [`files.md`](files.md)) ([#722]).
- Sessions stay under the link until it dies (below). Removing a file or deleting a session erases at once, apart from a sealed session (see [`misuse.md`](misuse.md)) ([#717], [#722], [#733]).
- Anonymous feedback, which is kept. A tap on Yes to the age question removes its words and quote permissions (see [`feedback.md`](feedback.md)) ([#677], [#717], [#734]).

Left out, since Crux keeps no email for a link: the "email me" tick-boxes, "You can email me about this", the copy of data by email, Close account, and the let-in list ([#722]).

### Browsers, switching off and misuse

- Browsers are counted per link by random IDs, with no network addresses. The owner page shows the count and flags more than 3 ([#677], [#717]).
- The owner can switch a link off. The person may request again ([#717]).
- Declines count toward a misuse flag per link, raised as for accounts (see [`misuse.md`](misuse.md)) ([#677], [#717], [#733]).
- The owner reads the chat in the flagged sessions, then dismisses the flag or switches the link off. There is no warning, since there is no email ([#677], [#733]).
- A sealed flag from the tutor's report locks the link, as for accounts. One from Google's block seals only that session, and a second locks the link ([#735]). The owner decides from the date and the kind, and either lifts the lock or seal, or switches the link off. What is sealed stays in place (see [`misuse.md`](misuse.md)) ([#733]).
- After a dismissal, the holder sees the same notice as an account's email on their next visit. A link switched off for misuse shows the reason ([#733]).
- A share on the feedback page ends when the link dies ([#733]).

### When a link dies

A link dies when the owner switches it off, its holder taps Yes to the age question (see [`age.md`](age.md)), or the trial ends. Its sessions, files, pages, photo answers and preferences are erased ([#717], [#722], [#728] Answer 2, [#733]).

### Telling a link holder

Crux has no email for a link, so it uses an on-screen notice at the holder's next visit ([#733]):

- **The Trial Terms change:** the entry ticks show again.
- **The trial is ending:** a notice with the date, shown ahead of time. It reminds the holder that they can untick a quote or a share until then ([#734]).
- **A data breach:** a notice saying what happened.

A holder who does not visit cannot be reached ([#733]).

## Money and counts

- Guests and trial links spend from the learners' budget and the daily ceiling (see the main file's "Money") ([#677]).
- Nothing in the trial counts toward the go-public bar. The window starts on the day of the first public post ([#677]).
- The dated under-18 count does include trial endings (see [`age.md`](age.md)) ([#728]).

## The trial's notices

**The Trial Terms** carry the upload lines decided for accounts (see [`privacy.md`](privacy.md)) ([#722]). They also say a quote tick can't be undone once the link has ended ([#734]).

**The Trial Privacy Notice** says ([#677], [#717], [#722], [#728], [#733]):

- A request's email is kept at most 30 days.
- "Your invite is kept in our email provider's log for up to 30 days."
- Files and photo answers are kept with the link's sessions. They are erased at once when removed or when their session is deleted, and erased with the link when it dies.
- Turnstile's signals go partly to Cloudflare's own use, and the Crux email is a Gmail with no processor agreement during the trial (see [`privacy.md`](privacy.md)).
- Error reports carry no learner text.
- The dated under-18 count exists.
- A decline saves its date, kind and place in its session, until the owner acts or it drops out of the 7 days.
- Deleting a session erases it, but another session may still mention something from it.
- The owner may read flagged or shared sessions (see [`privacy.md`](privacy.md)).
- A holder who does not visit cannot be reached with a notice.

## Known gap

Files and photos can show a name, and the owner may see one when reading a session flagged for misuse. The trial accepts this, covered by the notice and by erasure ([#722]).

## Ending the trial

- The owner ends the trial with a button on the owner page, whether or not Crux will open. It takes a date at least 7 days ahead, which link holders see, and the daily housekeeping job ends the trial on that date ([#733]).
- Every trial link dies, with any flag still waiting and any notice not yet seen. The anonymous feedback answers and quote permissions stay (see [`feedback.md`](feedback.md)) ([#677], [#722], [#733], [#734]).
- Waiting requests are declined with the email above. An invite still waiting to send gets the decline email in its place ([#717], [#733]).
- Request access goes. Guest mode stays until sign-up opens, or for good if Crux stays a portfolio project ([#677], [#733]). When sign-up opens, the landing page shows the pre-written example (see [`accounts.md`](accounts.md)) ([#677]).
- Nothing from the trial is carried into an account ([#677]).

## The advisory opinion

- If the trial shows a public opening is worth it, the owner first sends the National Privacy Commission a Request for Advisory Opinion, at least a month before opening ([#677]). It goes after the trial, not before ([#717], [#722]).
- It follows NPC Circular 18-01: a letter to the Privacy Commissioner and Chairman, by email or in person, with the facts, the questions and a certification that the matter is not pending. An answer comes within 20 working days. It is non-binding, and a fee may apply ([#677]).
- It asks ([#677]):
  - Is Crux "automated decision-making or profiling" that must be registered under NPC Circular 2022-04, Section 5?
  - If not, is the sworn declaration still needed?
  - Is a learner's progress sensitive information about education?

## Opening

- The before-opening checklist is in `quality-bar.md`, and it is done before anyone but the owner signs up, even privately to one friend ([#677], [#680]).
- Within 20 days of the first account holder who is not the owner, the owner registers Crux on the Commission's registration system (NPCRS), unless the Commission's answer says it is not needed. It costs about PHP 500, then PHP 350 a year, as summarised in 2023. A private share counts the same as a public one ([#677], [#722]).
- Trial-link users are not counted toward the 20 days ([#722]).

## On screen

Layout is not decided (see the main file's Gaps). These rules need: the landing page's guest mode (sample topics, own-topic box and limit line, Request access), the entry ticks and the trial link notice, the Request access form, its "request received" page and its region message, the one-time device note, the network-refused message, what a dead or switched-off link shows, the guest's upload line, the link holder's notices, and the owner page's requests list (approve, decline, days left), trial-link list with browser counts and switch-off, guest cap setting, and the button that ends the trial ([#677], [#717], [#722], [#733]).

[#675]: https://github.com/calmxz/Crux/issues/675
[#677]: https://github.com/calmxz/Crux/issues/677
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#680]: https://github.com/calmxz/Crux/issues/680
[#717]: https://github.com/calmxz/Crux/issues/717
[#722]: https://github.com/calmxz/Crux/issues/722
[#728]: https://github.com/calmxz/Crux/issues/728
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
