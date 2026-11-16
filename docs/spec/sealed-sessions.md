# Sealed sessions

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers sealed flags, what a seal tells the learner, and a Reported session. The harm line, the misuse flag and misuse closures are in [`misuse.md`](misuse.md).

**Sealed flags**

A decline for anything sexual involving minors is handled differently ([#733]):

- The account locks at once, with no tutoring. The learner sees that it is locked, and how to reply ([#733]).
- The owner sees only the date and the kind, and for a session marked "Reported", its account's email (below). The session holding the decline, with its files, is sealed, so nobody can open it, the owner included ([#733], [#719]).
- The owner decides from that and from any reply, and closes the account or lifts the lock. Lifting it ends the seal, unless the session is Reported and the authorities have not answered (see "A Reported session" below) ([#733], [#777]).
- The learner cannot delete a sealed session. It is erased when its account or trial link is erased, on the usual schedule ([#733]).
- If the owner reports it to the authorities, the owner marks it "Reported" on the owner page. It then stays sealed until the authorities say what to do, past that erasure too. While its account or link lives, the owner then lifts the seal or erases it; in the reported hold, the owner erases it ([#733], [#743], [#777]). At an erasure before the answer is recorded, it moves to the reported hold, with its files, its flag's date, kind and number, and the account's email, which the owner can see so a report can name the account. A trial link has no email. Until erasure the learner sees no change (see [`data-model.md`](data-model.md)) ([#719]).

A message or reply Google blocks as prohibited content is sealed the same way. The first has no lock on the account, and a second locks it. Google's docs describe this category as "usually" child sexual abuse material, so it is not only that one kind, and nobody can lawfully test it with real examples ([#735]):

- It is a flag raised at once, with a push. The owner sees only the date and the kind.
- That session is sealed, with its files. The learner's other sessions keep working, until a second block on the account locks it, as above.
- The count stays on the account until the owner decides. Dismissing the flag or lifting a seal resets it to 0.
- The learner sees that the session is sealed, how to reply to the Crux email, and not to upload that file again.
- The owner decides from the date, the kind and any reply, and either lifts the seal or closes the account. A Reported seal waits for the answer (below) ([#777]).
- If nobody replies, the session stays sealed until it is erased with the account.
- A guest has no flag (see above). They see the block message, and that guest session ends.

Whichever way it was sealed, nothing reaches a sealed session: no lookup, no share, no background answer and no re-mark. Its waiting messages stay waiting until the seal is lifted, and a re-mark it missed runs then ([#735], [#736]).

A seal from Google's block stands apart from any open flag. A flag already waiting keeps its choices, and its sessions can still be read, apart from the sealed one. The message on a sealed session carries a flag number, so a reply can be matched, including from a trial link ([#735]).

A sealed session's mastered topics and passed objectives stay on the Record, and the tutor still counts them. Every way into it shows the sealed message, and a message naming it leaves out "open … to pick it up". Its files leave the learner's allowance while it is sealed (see [`files.md`](files.md#the-allowance-and-the-store)). What the learner sees, and where, is in [`app-shell.md`](app-shell.md) ([#752]).

**What a seal tells the learner**

- A seal never names its kind, on email or screen. Every sealed message, the sealed session's and the lock card's, adds one fixed line, the **fixed reason line**: "Sessions are sealed when they may hold content that is never allowed, so nobody can read them." ([#764])
- A closure decided on a sealed flag names no kind and does not say the owner read anything. Its email: "Crux's owner closed your account on 3 Nov, about your sealed session. Sign in to read why. To contest this, reply by 11:59 pm on 10 Nov, Philippine time. After that, your account is erased." With two sealed sessions, it says "your sealed sessions". It quotes the sealed flag's number ([#764], [#772]).
- A lift shows no card for the seal itself. The seal's kind stays with the sealed session, and is erased at the lift or with the session ([#719], [#764]).
- **A seal on a waiting flag:** each part is told its own way. If the owner lifts the seal and takes no other action, the readable part gets a misuse card naming its kinds, its 30 days counted from the lift, with the dismissed email, counting only the readable declines. A trial link gets the card only, at its next visit. If the owner closes, the lock card names the readable part's kinds, then adds "Another session was sealed." and the fixed reason line. The sealed session is never said to be read ([#764], [#776], [#777]).
- A trial link switched off from a sealed flag gets Crux's sealed wording (see [`landing-screens.md`](landing-screens.md)) ([#764]).

**A Reported session**

- Until the owner records "The authorities answered" on the owner page, a Reported seal can't be lifted. A mark made by mistake is undone only that way ([#777]).
- Meanwhile the owner can still settle the flag, and the session stays sealed. Lifting a lock ends every unreported seal under it, and a Reported one only once its answer is recorded. Dismissing a Google seal's flag closes it, resets the count to 0 and takes it out of the daily email; a later block raises a new flag with no lock ([#777]).
- A lock lift decides the flag, even one with nothing readable in it, and closing is then no longer offered for it. The count returns to 0, the flag leaves the daily email, and new declines can raise a new flag. Readable declines get their card and email as for a seal on a waiting flag above, counted from the lock lift. The email is a required one, at most one per flag ([#777]).
- After the answer, the owner lifts the seal or erases the session. A lift works as any lift, and Crux keeps no record of the report beyond the restore log's and backups' usual 8 days. A lift resets a Google seal's count to 0 even past a later flag, which stays open; an erase leaves the flag and the count to the owner. During a misuse closure's 7 days, both wait: a kept closure erases the session with the account, and an upheld contest restores it sealed ([#777]).
- **Erase** works like a deletion: the session, its files, and its mastered topics and passed objectives go, and the learner then gets the erase card (see [`account-screens.md`](account-screens.md)). If its own seal still locks the account or link, the dialog's "Lift the lock" lifts it in the same step; a Google seal with no lock has Erase only. To close as well, the owner closes from the flag instead ([#777]).
- Once the answer is recorded, an erasure of the account or link takes the session with it, and nothing goes to the reported hold ([#777]).

## On screen

The message on a sealed session is in [`app-shell.md`](app-shell.md) ([#752]).

## Gaps

- **Child-protection law:** the owner chose not to seek advice before the trial. Whether RA 11930 applies to Crux, and what it requires, stays unconfirmed. It repealed RA 9775 in 2022 ([#743], [#762]).

[#719]: https://github.com/calmxz/Crux/issues/719
[#733]: https://github.com/calmxz/Crux/issues/733
[#735]: https://github.com/calmxz/Crux/issues/735
[#743]: https://github.com/calmxz/Crux/issues/743
[#736]: https://github.com/calmxz/Crux/issues/736
[#752]: https://github.com/calmxz/Crux/issues/752
[#762]: https://github.com/calmxz/Crux/issues/762
[#764]: https://github.com/calmxz/Crux/issues/764
[#772]: https://github.com/calmxz/Crux/issues/772
[#776]: https://github.com/calmxz/Crux/issues/776
[#777]: https://github.com/calmxz/Crux/issues/777
