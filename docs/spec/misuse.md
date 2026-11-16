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
- Crux saves each decline's date, kind and place in its session on the account, with no words from the chat or a file. Deleting a session does not undo a decline ([#733]). Crux handles the kinds as possibly sensitive (see [`privacy.md`](privacy.md)) ([#776]).
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
- What is saved with a decline is erased when the decline drops out of the 7 days with no flag. Once the owner decides, it is kept as "How long the kinds are kept" below sets out ([#733], [#764]). A decline in a sealed flag stays with its sealed session until the seal is lifted, or goes with the session ([#719], [#764]).

**What the learner is told**

The learner hears only after the owner decides. No email names a declined kind. Each gives the count, says the owner read the flagged sessions that were still there, and sends the learner to sign in. The kinds are read in the app ([#677], [#733], [#764]).

- **Warned:** an email: "The tutor declined 3 of your requests, and Crux's owner read those sessions that were still there. This breaks Crux's terms. Another time closes your account. Sign in to read why." ([#764])
- **Dismissed:** an email: "The tutor declined 3 of your requests, and Crux's owner read those sessions that were still there. On 4 Mar the owner took no action. Sign in to read why." ([#764])
- **Closed:** an email: "Crux's owner closed your account on 3 Nov. The tutor declined 3 of your requests, and the owner read those sessions that were still there. Sign in to read why. To contest this, reply by 11:59 pm on 10 Nov, Philippine time. After that, your account is erased." ([#764], [#772])
- The count includes declines that arrived while the flag waited. The date is the day of the owner's decision ([#764]).
- Each of these emails ends with "If you reply, quote flag 4821.", so a reply can be matched to its flag. The owner page shows an account's flag with no email ([#755]).
- The contest outcomes under "A misuse closure" name no kind. Nor do the owner's own replies from the Crux inbox ([#755], [#764]).

**Where the kinds are read**

- **Warned or dismissed:** the **misuse card**, an opening page with Continue that names the declined kinds. Its wording is in [`account-screens.md`](account-screens.md) ([#764]).
- Each decision's card shows at every opening, on any browser, until Continue is tapped once. It first shows at the next opening, in the order [`accounts.md`](accounts.md) gives. A learner already in the app sees it only at the next opening, unlike a lock's page ([#764]).
- Several waiting cards show one after another, oldest decision first ([#764]).
- While the account is locked, the card waits, and shows once the lock ends. This includes a card from an earlier decision when a later closure's contest is upheld ([#764]).
- **Closed:** the lock card names the kinds (see [`account-screens.md`](account-screens.md)) ([#764]).
- Cards and lock cards name kinds in the harm list's words, or "blocked by Google". They never name the mark that flags at once ([#764]).
- **A trial link:** a dismissal shows the misuse card on the next visit. A link switched off from its flag shows a line Crux writes (see [`trial.md`](trial.md) and [`landing-screens.md`](landing-screens.md)) ([#764]).

**How long the kinds are kept**

- **Warned or dismissed:** the kinds are kept until Continue is tapped on that card, or 30 days after the owner's decision, whichever comes first. The 30 days run through a lock, and end at the daily job's last run within them. The count and the decision's date are kept until Continue, or until the account is erased, at the latest by the 12-month idle erasure. On a trial link, the same 30 days apply, and the count and date are kept until Continue or until the link dies. Each decline's place in its session is erased at the owner's decision ([#764], [#776]).
- After the 30 days, the card and a copy give the count and the date only. The emails are unchanged, so their "Sign in to read why" no longer shows why ([#776]).
- **Closed:** they stay with the lock, until the account is erased or a contest is upheld. Each decline's place stays with the lock, for the owner's contest reading. Any older card still waiting is kept, and shows after the restore ([#764]).
- **A trial link switched off for misuse:** the kinds stay in its stub until the ended page first shows them, or 30 days after the owner's decision, whichever comes first. The stub then keeps the count and the general line ([#764], [#776]).
- Kinds waiting for a card no longer count toward a flag, and the 7-day rule does not erase them; the 30 days do ([#764], [#776]).
- The restore log keeps these steps through a database restore (see [`hosting.md`](hosting.md)) ([#764]).

**Sealed flags**

A decline for anything sexual involving minors is handled differently ([#733]):

- The account locks at once, with no tutoring. The learner sees that it is locked, and how to reply ([#733]).
- The owner sees only the date and the kind, and for a session marked "Reported", its account's email (below). The session holding the decline, with its files, is sealed, so nobody can open it, the owner included ([#733], [#719]).
- The owner decides from that and from any reply, and closes the account or lifts the lock. Lifting it ends the seal, unless the session is Reported and the authorities have not answered (see "A Reported session" below) ([#733], [#777]).
- The learner cannot delete a sealed session. It is erased when its account or trial link is erased, on the usual schedule ([#733]).
- If the owner reports it to the authorities, the owner marks it "Reported" on the owner page. It then stays sealed past that erasure until the authorities say what to do, and the owner then lifts the seal or erases it ([#733], [#743], [#777]). At an erasure before the answer is recorded, it moves to the reported hold, with its files, its flag's date, kind and number, and the account's email, which the owner can see so a report can name the account. A trial link has no email. Until erasure the learner sees no change (see [`data-model.md`](data-model.md)) ([#719]).

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
- **A seal on a waiting flag:** each part is told its own way. If the owner lifts the seal and takes no other action, the readable part gets a misuse card naming its kinds. If the owner closes, the lock card names the readable part's kinds, then adds "Another session was sealed." and the fixed reason line. The sealed session is never said to be read ([#764]).
- A trial link switched off from a sealed flag gets Crux's sealed wording (see [`landing-screens.md`](landing-screens.md)) ([#764]).

**A Reported session**

- Until the owner records "The authorities answered" on the owner page, a Reported seal can't be lifted. A mark made by mistake is undone only that way ([#777]).
- Meanwhile the owner can still settle the flag, and the session stays sealed. Lifting a lock ends every unreported seal under it, and a Reported one only once its answer is recorded. Dismissing a Google seal's flag closes it and resets the count to 0 ([#777]).
- A lock lift decides the flag, and closing is then no longer offered for it. Readable declines in the flag then get their misuse card with the dismissed email, both counting only the readable declines. The card's 30 days count from the lift. A trial link gets the card at its next visit ([#777]).
- After the answer, the owner lifts the seal or erases the session. A lift works as any lift, and Crux keeps no record of the report. During a misuse closure's 7 days, both wait: a kept closure erases the session with the account, and an upheld contest restores it sealed ([#777]).
- **Erase** works like a deletion: the session, its files, and its mastered topics and passed objectives go. If its own seal still locks the account or link, the same step lifts the lock. To close as well, the owner closes from the flag instead. The learner then gets the erase card (see [`account-screens.md`](account-screens.md)) ([#777]).
- Once the answer is recorded, an erasure of the account or link takes the session with it, and nothing goes to the reported hold ([#777]).

**A misuse closure**

- The account locks for 7 days. Nothing is erased yet ([#733]).
- If the owner upholds a contest, the account is restored as it was, and no block is set ([#677], [#733]). Crux emails "Crux's owner read your reply about flag 4790 and restored your account. You can use Crux again." ([#755])
- An upheld contest on a sealed-flag closure also restores the account as it was. The seal stays until the owner lifts it ([#764]).
- If the owner keeps the closure, the account is erased at the run its last day sets, or at the next daily run if that has passed. Crux emails the decision: "Crux's owner read your reply about flag 4790 and kept the closure. Your account will be erased after 11:59 pm on 18 Mar, Philippine time.", or "Your account will now be erased." once that date has passed ([#755], [#772])
- A contest counts when it reaches the Crux inbox by 11:59 pm on the last day, by the inbox's received time. The owner can enter it on the owner page until the run that would erase, and it holds the erasure until the owner decides. Without one entered, the owner is reminded from the first run after the last day (see [`operations.md`](operations.md)) ([#753], [#772]). A contest after that is settled by the let-in list (see [`accounts.md`](accounts.md)) ([#733]).
- Otherwise it is erased one run after that reminder: day 10, at 8:05 am on 12 Nov for a closure on 3 Nov. From 12:00 am after the last day, the account opens to its card only (see [`dates.md`](dates.md)) ([#733], [#772]). The 7 days start when Resend accepts the closure email ([#735]).
- A lock is read-only: the learner can read, tap the age question, and untick a quote or a share, but not be tutored, start a session, rename one, or close the account ([#733], [#734], [#753]).
- A misuse closure's lock also bars deleting a session and removing a file. The sessions the owner may read to judge a contest stay until the owner decides. The learner asks by email to have one erased, by its exact name, and Crux warns the account's address and erases it after the warning's last day, as [`dates.md`](dates.md) says ([#755], [#772]). The warning names the session, even when a session the tutor never named carries its request's first words, which can echo a declined request ([#764]). A sealed-flag lock lasts until the owner decides, so it does not bar them; the sealed session itself can never be deleted ([#753]).
- Erasing wins over a flag. A flag waiting when an account is erased goes with it, with no block. A tap on Yes erases at once, with no block. A learner who closes and signs up again starts with no warning on record ([#681], [#733]).
- The email is then kept scrambled for 12 months, to block rejoining. How the block works at sign-up is in [`accounts.md`](accounts.md) ([#677], [#733]).

## On screen

The message when Google blocks a reply is a line in the thread (see [`learning-screen.md`](learning-screen.md)) ([#751]). The rest of the layout is not decided (see the main file's Gaps). The message on a sealed session is in [`app-shell.md`](app-shell.md) ([#752]). The locked account, the misuse card and the erase card are in [`account-screens.md`](account-screens.md) ([#753], [#764], [#777]). A guest's block message and a trial link's lock, notices and ended pages are in [`landing-screens.md`](landing-screens.md) ([#754]). The owner page's flags, closures and reported hold are in [`owner-screens.md`](owner-screens.md) ([#755]).

## Gaps

- **Child-protection law:** the owner chose not to seek advice before the trial. Whether RA 11930 applies to Crux, and what it requires, stays unconfirmed. It repealed RA 9775 in 2022 ([#743], [#762]).

[#665]: https://github.com/calmxz/Crux/issues/665
[#667]: https://github.com/calmxz/Crux/issues/667
[#677]: https://github.com/calmxz/Crux/issues/677
[#681]: https://github.com/calmxz/Crux/issues/681
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#732]: https://github.com/calmxz/Crux/issues/732
[#733]: https://github.com/calmxz/Crux/issues/733
[#735]: https://github.com/calmxz/Crux/issues/735
[#743]: https://github.com/calmxz/Crux/issues/743
[#734]: https://github.com/calmxz/Crux/issues/734
[#736]: https://github.com/calmxz/Crux/issues/736
[#751]: https://github.com/calmxz/Crux/issues/751
[#752]: https://github.com/calmxz/Crux/issues/752
[#753]: https://github.com/calmxz/Crux/issues/753
[#754]: https://github.com/calmxz/Crux/issues/754
[#762]: https://github.com/calmxz/Crux/issues/762
[#755]: https://github.com/calmxz/Crux/issues/755
[#764]: https://github.com/calmxz/Crux/issues/764
[#772]: https://github.com/calmxz/Crux/issues/772
[#776]: https://github.com/calmxz/Crux/issues/776
[#777]: https://github.com/calmxz/Crux/issues/777
