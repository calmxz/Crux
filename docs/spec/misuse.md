# Harm and misuse

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers the Terms' harm line, how the tutor applies it, and what happens when a learner keeps crossing it. Sealed flags and Reported sessions are in [`sealed-sessions.md`](sealed-sessions.md). What the owner may read is in [`privacy.md`](privacy.md).

## Harm

"Crux teaches subjects; it won't help carry out harm" ([#677]):

- weapons and explosives;
- breaking into systems or other people's accounts;
- making drugs or other illegal goods;
- explicit sexual content (anatomy, reproduction and sexual health are taught);
- harassing, threatening or targeting a real person;
- methods of self-harm.

Anthropic's usage policy also applies, and is linked ([#677], [#802]).

- A subject can be studied, not carried out. The chemistry of combustion is taught, and building a device is not. LD50 is taught, and a synthesis route is not ([#677]).
- The tutor applies the line the same way every time. A cover story ("for my novel", "hypothetically", "for school") does not change a decline. It judges the whole conversation, not each message alone ([#677]).
- A learner who says something like "I don't want to be here anymore" is not refused. The tutor pauses the lesson, responds with care, and points to a crisis line ([#677]). The line is fixed text, in the tutor's replies and in Crux's own line alike: "Please contact your local crisis hotline.", for the meantime. A number later is a recorded change ([#735], [#802]). A typed reply while the age question is open never reaches the tutor at that moment, so a separate check runs (see [`refusals.md`](refusals.md)). No check runs at a limit, on a message a switch stopped, or from a barred country ([#734], [#736], [#802]). Two exceptions get no care line: a distress message whose reply is refused and whose distress check is refused or fails gets a decline, and a guest's refusal past the guests' pot gets only the refusal line ([#802]). A request for a method that shows the learner's own distress gets the same care, and is not reported as a decline. One behind a cover story is ([#733]).
- Harmful requests and files are declined (see [`learning-loop.md`](learning-loop.md) and [`files.md`](files.md)) ([#665], [#667]).

## Misuse

Crux counts declines, and the owner decides. A trial link follows [`trial-links.md`](trial-links.md) ([#677], [#717], [#733]). A guest has no flag, since nothing is kept after the tab closes ([#677]). The tutor's report of sexual content involving minors ends a guest's session instead (see [`landing-screens.md`](landing-screens.md)) ([#802]).

**The flag**

- The tutor reports each decline to Crux through a tool call, naming its kind from the harm list above, and marking the two cases that flag at once (see [`ai-layer.md`](ai-layer.md)) ([#677], [#733]). A harmful file's decline is in [`files.md`](files.md) ([#732]).
- A decline here means a refusal under that list. Refusing a bare answer, turning a task toward its skill, and a file with nothing learnable are not declines. ([#733]).
- A message or reply our AI provider refuses as `bio`, `cyber` or `general_harms` has no tool call, so Crux reads the refusal's category itself. It counts as a decline, kind "refused by our AI provider", after the distress check for `general_harms`. Any other refusal is not a decline ([#733], [#735], [#802]). Which refusals count is in [`refusals.md`](refusals.md).
- Crux saves each decline's date, kind and place in its session on the account, with no words from the chat or a file. Deleting a session does not undo a decline ([#733]). Crux handles the kinds as possibly sensitive (see [`terms-and-policy.md`](terms-and-policy.md)) ([#776]).
- An account is flagged on 3 declines within 7 days ([#677]).
- It is flagged at once on 1 decline for a threat against a real person, or for anything sexual involving minors ([#677], [#733]).
- A flag shows on the owner page and in the owner's daily email. A flag raised at once also pushes to the owner's phone ([#733]).
- A flag changes nothing for the learner, except under "Sealed flags" in [`sealed-sessions.md`](sealed-sessions.md). They keep learning, the tutor keeps declining, and nothing says they are flagged ([#733]).

**The owner's decision**

The owner reads the chat in the flagged sessions (see [`privacy.md`](privacy.md)), where a refused message shows only as "Refused by our AI provider", with its date. A flag made only of refusals is judged from dates and kinds, or dismissed. Then ([#733], [#802]):

| Flag | The owner can |
|---|---|
| No warning on record | Warn or dismiss |
| A warning on record | Close or dismiss |
| A flag raised at once | Close with no warning, or dismiss |

- An account has one open flag at a time. A decline that flags at once, arriving while a flag waits, moves that flag to the last row ([#733]).
- After a warning or a dismissal, the count returns to 0, including declines that arrived while the flag waited. A warning stays on record ([#733]).
- What is saved with a decline is erased when the decline drops out of the 7 days with no flag. Once the owner decides, it is kept as "How long the kinds are kept" below sets out ([#733], [#764]). A decline in a sealed flag stays with its sealed session until the seal is lifted, or goes with the session ([#719], [#764]).

**What the learner is told**

The warned, dismissed and closed emails are in [`account-screens.md`](account-screens.md#misuse-emails) ([#764]).

**Where the kinds are read**

- **Warned or dismissed:** the **misuse card**, an opening page with Continue that names the declined kinds. Its wording is in [`account-screens.md`](account-screens.md) ([#764]).
- Each decision's card shows at every opening, on any browser, until Continue is tapped once. It first shows at the next opening, in the order [`accounts.md`](accounts.md) gives. A learner already in the app sees it only at the next opening, unlike a lock's page ([#764]).
- Several waiting cards show one after another, oldest decision first ([#764]).
- While the account is locked, the card waits, and shows once the lock ends. This includes a card from an earlier decision when a later closure's contest is upheld ([#764]).
- **Closed:** the lock card names the kinds (see [`account-screens.md`](account-screens.md)) ([#764]).
- Cards and lock cards name kinds in the harm list's words, or "refused by our AI provider". They never name the mark that flags at once ([#764]).
- **A trial link:** a dismissal shows the misuse card on the next visit. A link switched off from its flag shows a line Crux writes (see [`trial-links.md`](trial-links.md) and [`landing-screens.md`](landing-screens.md)) ([#764]).

**How long the kinds are kept**

- **Warned or dismissed:** the kinds are kept until Continue is tapped on that card, or 30 days after the owner's decision, whichever comes first. The 30 days run through a lock, and end at the daily job's last run within them. The count and the decision's date are kept until Continue, or until the account is erased, at the latest by the 12-month idle erasure. On a trial link, the same 30 days apply, and the count and date are kept until Continue or until the link dies. Each decline's place in its session is erased at the owner's decision ([#764], [#776]).
- After the 30 days, the card and a copy give the count and the date only. The emails are unchanged, so their "Sign in to read why" no longer shows why ([#776]).
- **Closed:** they stay with the lock, until the account is erased or a contest is upheld. Each decline's place stays with the lock, for the owner's contest reading. Any older card still waiting is kept, and shows after the restore ([#764]).
- **A trial link switched off for misuse:** the kinds stay in its stub until the ended page first shows them, or 30 days after the owner's decision, whichever comes first. The stub then keeps the count and the general line ([#764], [#776]).
- Kinds waiting for a card no longer count toward a flag, and the 7-day rule does not erase them; the 30 days do ([#764], [#776]).
- The restore log keeps these steps through a database restore (see [`backups-and-releases.md`](backups-and-releases.md)) ([#764]).

**A misuse closure**

- The account locks for 7 days. Nothing is erased yet ([#733]).
- If the owner upholds a contest, the account is restored as it was, and no block is set ([#677], [#733]). Crux emails "Crux's owner read your reply about flag 4790 and restored your account. You can use Crux again." ([#755])
- An upheld contest on a sealed-flag closure also restores the account as it was. The seal stays until the owner lifts it ([#764]).
- If the owner keeps the closure, the account is erased at the run its last day sets, or at the next daily run if that has passed. Crux emails the decision: "Crux's owner read your reply about flag 4790 and kept the closure. Your account will be erased after 11:59 pm on 18 Mar, Philippine time.", or "Your account will now be erased." once that date has passed ([#755], [#772])
- A contest counts when it reaches the Crux inbox by 11:59 pm on the last day, by the inbox's received time. The owner can enter it on the owner page until the run that would erase, and it holds the erasure until the owner decides. Without one entered, the owner is reminded from the first run after the last day (see [`operations.md`](operations.md)) ([#753], [#772]). A contest after that is settled by the let-in list (see [`accounts.md`](accounts.md)) ([#733]).
- Otherwise it is erased one run after that reminder: day 10, at 8:05 am on 12 Nov for a closure on 3 Nov. From 12:00 am after the last day, the account opens to its card only (see [`dates.md`](dates.md)) ([#733], [#772]). The 7 days start when Resend accepts the closure email ([#735]).
- A lock is read-only: the learner can read, tap the age question, and untick a quote or a share, but not be tutored, start a session, rename one, or close the account ([#733], [#734], [#753]).
- A misuse closure's lock also bars deleting a session and removing a file. The sessions the owner may read to judge a contest stay until the owner decides. The learner asks by email to have one erased, by its exact name, and Crux warns the account's address and erases it after the warning's last day, as [`dates.md`](dates.md) says ([#755], [#772]). The warning names the session, even when a session the tutor never named carries its request's first words, which can echo a declined request ([#764]). A session whose first request our AI provider refused shows "New session" instead ([#802]). A sealed-flag lock lasts until the owner decides, so it does not bar them; the sealed session itself can never be deleted ([#753]).
- Erasing wins over a flag. A flag waiting when an account is erased goes with it, with no block. A tap on Yes erases at once, with no block. A learner who closes and signs up again starts with no warning on record ([#681], [#733]).
- The email is then kept scrambled for 12 months, to block rejoining. How the block works at sign-up is in [`accounts.md`](accounts.md) ([#677], [#733]).

## Gaps

- **Two sessions sharing a name** when a learner asks by email to erase one by its exact name, under a misuse lock or during a closing: older than [#802], and more frequent now that a refused first request shows "New session" ([#802]).

## On screen

The lines when our AI provider refuses a reply are lines in the thread (see [`learning-screen.md`](learning-screen.md)) ([#751]). The rest of the layout is not decided (see the main file's Gaps). The locked account, the misuse card and the erase card are in [`account-screens.md`](account-screens.md) ([#753], [#764], [#777]). A guest's block message and a trial link's lock, notices and ended pages are in [`landing-screens.md`](landing-screens.md) ([#754]). The owner page's flags, closures and reported hold are in [`owner-screens.md`](owner-screens.md) ([#755]).

[#665]: https://github.com/calmxz/Crux/issues/665
[#667]: https://github.com/calmxz/Crux/issues/667
[#677]: https://github.com/calmxz/Crux/issues/677
[#681]: https://github.com/calmxz/Crux/issues/681
[#717]: https://github.com/calmxz/Crux/issues/717
[#719]: https://github.com/calmxz/Crux/issues/719
[#732]: https://github.com/calmxz/Crux/issues/732
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#736]: https://github.com/calmxz/Crux/issues/736
[#751]: https://github.com/calmxz/Crux/issues/751
[#753]: https://github.com/calmxz/Crux/issues/753
[#754]: https://github.com/calmxz/Crux/issues/754
[#755]: https://github.com/calmxz/Crux/issues/755
[#764]: https://github.com/calmxz/Crux/issues/764
[#772]: https://github.com/calmxz/Crux/issues/772
[#776]: https://github.com/calmxz/Crux/issues/776
[#777]: https://github.com/calmxz/Crux/issues/777
[#802]: https://github.com/calmxz/Crux/issues/802
