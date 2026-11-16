# Trial links

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers trial links: opening one, the link code, erasing a link, what a link carries, misuse, when a link dies, and telling a link holder. Guest mode, Request access and the rest of the trial are in [`trial.md`](trial.md).

## Trial links

### Opening one

- The first time this link opens on a browser, the entry ticks show if they have not been given there, with this notice ([#717], [#722], [#733]): "This link is for you only. Anyone with it sees your sessions and uses your limit. If it's used on more than 3 browsers, it may be switched off. Don't type or upload personal details, such as your name on a problem sheet."
- The key sits after a `#` (see [`security.md`](security.md)) ([#770]). The link is then swapped for a sign-in cookie, and the key leaves the address bar. That browser stays signed in until 30 days without a visit ([#717]).
- Another device opens the same link from the invite email and sees the same sessions. A one-time note after the first sign-in says: "To use Crux on another device, open your invite email there and tap the link." ([#717])
- A link works from anywhere, including the EU and the UK, like an account (see [`hosting.md`](hosting.md)) ([#735]).
- There is no device code and no "copy my link" ([#717]). A new link opened on a browser replaces the old sign-in there ([#733]).
- A person who loses the email asks again and, if approved, gets a new, empty trial space ([#717]).
- The key is stored scrambled. A network that tries 10 wrong links in an hour is refused for the rest of the hour. Its address is kept only that hour ([#717]).

### The link code

- At approval, each link gets a random 6-character code from 31 characters that can't be confused (no 0, O, 1, I or L), made separately from its key and unique among live links and stubs. The owner page names the link by it, with the date it was made, and the holder's trial Settings page shows "Trial link K7Q-4MP" (see [`owner-screens.md`](owner-screens.md)) ([#755]).
- A quoted code tells the owner which link an email is about, for looking things up and answering. It is not proof of holding the link, since a screenshot of Settings shows it, so nothing is switched off or erased on an emailed request ([#755]).
- An email to the Crux inbox quoting a code is deleted once answered, with the reply in Sent and the copy in Trash, and at the trial's end at the latest ([#755]).

### Erasing a link

- The holder erases their link with "Erase this trial link" on their trial Settings page, after typing "delete". It erases at once what a tap on Yes erases: sessions, files, pages, photo answers, preferences, feedback words and quote permissions. A published quote keeps only where it was published and the remove-by date, until the owner marks it removed (see [`feedback.md`](feedback.md)) ([#755]).
- A link locked by a sealed flag can't be erased this way until the owner decides ([#755]).
- They may request access again ([#755]).

### What a link carries

The main file's "Stages" sets the rule. In detail:

- Every step of the learning loop, with files in a session and photo answers in a check, under the rules decided for accounts (see [`files.md`](files.md) and [`mastery-check.md`](mastery-check.md)) ([#722]).
- The same tutoring limit as an account (see [`spending.md`](spending.md)) ([#677]).
- An account's storage allowance, in the shared store (see [`files.md`](files.md)) ([#722]).
- Sessions stay under the link until it dies (below). Removing a file or deleting a session erases at once, apart from a sealed session (see [`sealed-sessions.md`](sealed-sessions.md)) ([#717], [#722], [#733]).
- Anonymous feedback, which is kept. A tap on Yes to the age question removes its words and quote permissions (see [`feedback.md`](feedback.md)) ([#677], [#717], [#734]).

Left out, since Crux keeps no email for a link: the "email me" tick-boxes, "You can email me about this", the copy of data by email, Close account (a link has "Erase this trial link" instead, above), and the let-in list ([#722], [#755]).

### Browsers, switching off and misuse

- Browsers are counted per link by random IDs, with no network addresses. The owner page shows the count and flags more than 3 ([#677], [#717]).
- The owner can switch a link off. The person may request again ([#717]).
- Declines count toward a misuse flag per link, raised as for accounts (see [`misuse.md`](misuse.md)) ([#677], [#717], [#733]).
- The owner reads the chat in the flagged sessions, then dismisses the flag or switches the link off. There is no warning, since there is no email ([#677], [#733]).
- A sealed flag from the tutor's report locks the link, as for accounts. One from Google's block seals only that session, and a second locks the link ([#735]). The owner decides from the date and the kind, and either lifts the lock or seal, or switches the link off. What is sealed stays in place (see [`sealed-sessions.md`](sealed-sessions.md)) ([#733]).
- After a dismissal, the holder sees the misuse card on their next visit (see [`misuse.md`](misuse.md)). A link switched off from its flag shows a reason Crux writes: the kinds in the harm list's words, from the decline records, or for a sealed flag the fixed reason line ([#733], [#764]).
- A share on the feedback page ends when the link dies ([#733]).

### When a link dies

A link dies when the owner switches it off, its holder taps Yes to the age question (see [`age.md`](age.md)), its holder erases it ([#755]), or the trial ends. Its sessions, files, pages, photo answers and preferences are erased ([#717], [#722], [#728] Answer 2, [#733]). A sealed session marked "Reported" with no answer recorded stays in the reported hold (see [`data-model.md`](data-model.md)) ([#719], [#777]).

A stub stays: the link's scrambled key, its scrambled sign-in cookie IDs, its state and, for a link switched off, the reason (a misuse reason keeps its kinds only until first shown, or 30 days after the owner's decision, see [`misuse.md`](misuse.md)) ([#764], [#776]), so a holder returning by key or by cookie sees it. A stub also keeps the link code, so the owner's dead-link list can name it. A link that died by a Yes, or that its holder erased, keeps only its state, with no code ([#755]). The stub goes when the trial ends, or 12 months after the link died, whichever comes first. The owner page lists dead links and why while their stubs last ([#719]).

### Telling a link holder

Crux has no email for a link, so it uses an on-screen notice at the holder's next visit ([#733]):

- **The Trial Terms change:** the entry ticks show again.
- **The trial is ending:** a notice with the date and time, shown ahead of time. It reminds the holder that they can untick a quote or a share until then ([#734], [#772]).
- **A data breach:** a notice saying what happened.
- **A re-mark** that changed a mark (see [`live-faults.md`](live-faults.md)) ([#736]).

A holder who does not visit cannot be reached ([#733]).

## Known gaps

- Files and photos can show a name, and the owner may see one when reading a session flagged for misuse. The trial accepts this, covered by the notice and by erasure ([#722]).

[#677]: https://github.com/calmxz/Crux/issues/677
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#722]: https://github.com/calmxz/Crux/issues/722
[#728]: https://github.com/calmxz/Crux/issues/728
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#736]: https://github.com/calmxz/Crux/issues/736
[#755]: https://github.com/calmxz/Crux/issues/755
[#764]: https://github.com/calmxz/Crux/issues/764
[#770]: https://github.com/calmxz/Crux/issues/770
[#772]: https://github.com/calmxz/Crux/issues/772
[#776]: https://github.com/calmxz/Crux/issues/776
[#777]: https://github.com/calmxz/Crux/issues/777
