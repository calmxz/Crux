# Harm and misuse

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers the Terms' harm line, how the tutor applies it, and what happens when a learner keeps crossing it. What the owner may read is in [`privacy.md`](privacy.md).

## Harm

"Crux teaches subjects; it won't help carry out harm" ([#677]):

- weapons and explosives;
- breaking into systems or other people's accounts;
- making drugs or other illegal goods;
- explicit sexual content (anatomy, reproduction and sexual health are taught);
- harassing, threatening or targeting a real person;
- methods of self-harm.

Google's usage policy also applies, and is linked ([#677]).

- A subject can be studied, not carried out. The chemistry of combustion is taught, and building a device is not. LD50 is taught, and a synthesis route is not ([#677]).
- The tutor applies the line the same way every time. A cover story ("for my novel", "hypothetically", "for school") does not change a decline. It judges the whole conversation, not each message alone ([#677]).
- A learner who says something like "I don't want to be here anymore" is not refused. The tutor pauses the lesson, responds with care, and points to a crisis line ([#677]). The line is fixed text: "Philippines: call 1553. Elsewhere: findahelpline.com". The number and the link are checked before each stage (see [`quality-bar.md`](quality-bar.md)) ([#735]). A message a limit or a switch stopped never reaches the tutor at that moment, so a separate check runs (see [`spending.md`](spending.md)) ([#734], [#736]). A request for a method that shows the learner's own distress gets the same care, and is not reported as a decline. One behind a cover story is ([#733]).
- Harmful requests and files are declined (see [`learning-loop.md`](learning-loop.md) and [`files.md`](files.md)) ([#665], [#667]).

## Misuse

Crux counts declines, and the owner decides. A trial link follows [`trial.md`](trial.md) ([#677], [#717], [#733]). A guest has no flag, since nothing is kept after the tab closes ([#677]).

**The flag**

- The tutor reports each decline to Crux through a tool call, naming its kind from the harm list above, and marking the two cases that flag at once (see [`ai-layer.md`](ai-layer.md)) ([#677], [#733]). A harmful file's decline is in [`files.md`](files.md) ([#732]).
- A decline here means a refusal under that list. Refusing a bare answer, turning a task toward its skill, and a file with nothing learnable are not declines. ([#733]).
- A message or reply Google blocks for harm has no tool call, so Crux reads Google's block result itself. It counts as a decline, kind "blocked by Google". A block that is not about harm is not a decline. If Google's category is prohibited content, it is a sealed flag with no lock (see below) ([#733], [#735]). Which block results count is in [`ai-layer.md`](ai-layer.md).
- Crux saves each decline's date, kind and place in its session on the account, with no words from the chat or a file. Deleting a session does not undo a decline ([#733]).
- An account is flagged on 3 declines within 7 days ([#677]).
- It is flagged at once on 1 decline for a threat against a real person, or for anything sexual involving minors ([#677], [#733]).
- A flag shows on the owner page and in the owner's daily email. A flag raised at once also pushes to the owner's phone ([#733]).
- A flag changes nothing for the learner, except under "Sealed flags" below. They keep learning, the tutor keeps declining, and nothing says they are flagged ([#733]).

**The owner's decision**

The owner reads the chat in the flagged sessions (see [`privacy.md`](privacy.md)), then ([#733]):

| Flag | The owner can |
|---|---|
| No warning on record | Warn or dismiss |
| A warning on record | Close or dismiss |
| A flag raised at once | Close with no warning, or dismiss |

- An account has one open flag at a time. A decline that flags at once, arriving while a flag waits, moves that flag to the last row ([#733]).
- After a warning or a dismissal, the count returns to 0, including declines that arrived while the flag waited. A warning stays on record ([#733]).
- What is saved with a decline is erased once the message naming it is sent or shown, or when the decline drops out of the 7 days with no flag ([#733]).

**What the learner is told**

The learner hears only after the owner decides. Each message gives the reason, using the saved kinds, and says the owner read those sessions that were still there ([#677], [#733]).

- **Warned:** an email: "This breaks Crux's terms. Another time closes your account."
- **Dismissed:** an email: "The tutor declined 3 of your requests (making drugs or other illegal goods, methods of self-harm), so the owner read those sessions on Saturday. No action was taken."
- **Closed:** an email with the reason, the date, and that replying before then contests it.

**Sealed flags**

A decline for anything sexual involving minors is handled differently ([#733]):

- The account locks at once, with no tutoring. The learner sees that it is locked, and how to reply ([#733]).
- The owner sees only the date and the kind. The session holding the decline, with its files, is sealed, so nobody can open it, the owner included ([#733]).
- The owner decides from that and from any reply, and closes the account or lifts the lock. Lifting it ends the seal ([#733]).
- The learner cannot delete a sealed session. It is erased when its account or trial link is erased, on the usual schedule ([#733]).
- If the owner reports it to the authorities, the owner marks it "Reported" on the owner page. It then stays sealed past that erasure until the authorities say what to do, and the owner then erases it ([#733], [#743]).

A message or reply Google blocks as prohibited content is sealed the same way. The first has no lock on the account, and a second locks it. Google's docs describe this category as "usually" child sexual abuse material, so it is not only that one kind, and nobody can lawfully test it with real examples ([#735]):

- It is a flag raised at once, with a push. The owner sees only the date and the kind.
- That session is sealed, with its files. The learner's other sessions keep working, until a second block on the account locks it, as above.
- The count stays on the account until the owner decides. Dismissing the flag or lifting a seal resets it to 0.
- The learner sees that the session is sealed, how to reply to the Crux email, and not to upload that file again.
- The owner decides from the date, the kind and any reply, and either lifts the seal or closes the account.
- If nobody replies, the session stays sealed until it is erased with the account.
- A guest has no flag (see above). They see the block message, and that guest session ends.

Whichever way it was sealed, nothing reaches a sealed session: no lookup, no share, no background answer and no re-mark. Its waiting messages stay waiting until the seal is lifted, and a re-mark it missed runs then ([#735], [#736]).

A seal from Google's block stands apart from any open flag. A flag already waiting keeps its choices, and its sessions can still be read, apart from the sealed one. The message on a sealed session carries a flag number, so a reply can be matched, including from a trial link ([#735]).

**A misuse closure**

- The account locks for 7 days. Nothing is erased yet ([#733]).
- If the owner upholds a contest, the account is restored as it was, and no block is set ([#677], [#733]).
- A contest that arrives in the 7 days is entered on the owner page, which holds the erasure until the owner decides. A contest after that is settled by the let-in list (see [`accounts.md`](accounts.md)) ([#733]).
- Otherwise it is erased on day 8, in the daily housekeeping job ([#733]). The 7 days start when the closure email is sent, and a contest entered before then still counts (see [`operations.md`](operations.md)) ([#735]).
- A lock is read-only: the learner can read, and tap the age question, but not be tutored or close the account ([#733]).
- Erasing wins over a flag. A flag waiting when an account is erased goes with it, with no block. A tap on Yes erases at once, with no block. A learner who closes and signs up again starts with no warning on record ([#681], [#733]).
- The email is then kept scrambled for 12 months, to block rejoining. How the block works at sign-up is in [`accounts.md`](accounts.md) ([#677], [#733]).

## On screen

Layout is not decided (see the main file's Gaps). These rules need: the locked account, the message on a sealed session, the message when Google blocks a reply, and the owner page's flagged sessions, with warn, dismiss, close, restore, lift and "Reported" ([#677], [#733]).

## Gaps

- **Child-protection law:** the owner chose not to seek advice before the trial. Whether RA 9775 and RA 11930 apply to Crux, and what they require, stays unconfirmed ([#743]).

[#665]: https://github.com/calmxz/Crux/issues/665
[#667]: https://github.com/calmxz/Crux/issues/667
[#677]: https://github.com/calmxz/Crux/issues/677
[#681]: https://github.com/calmxz/Crux/issues/681
[#717]: https://github.com/calmxz/Crux/issues/717
[#732]: https://github.com/calmxz/Crux/issues/732
[#733]: https://github.com/calmxz/Crux/issues/733
[#735]: https://github.com/calmxz/Crux/issues/735
[#743]: https://github.com/calmxz/Crux/issues/743
[#734]: https://github.com/calmxz/Crux/issues/734
[#736]: https://github.com/calmxz/Crux/issues/736
