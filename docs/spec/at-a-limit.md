# At a limit

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what happens at a limit and how started checks finish. What Crux counts, the limits and the messages are in [`spending.md`](spending.md).

## At a limit

### Nothing can be sent

- At the learner's tutoring limit, the daily ceiling, the month's budget, or a workspace limit or the credit running out, the chat box is off until the reset. No message sent at a limit is kept, and no distress check runs ([#802]).
- This holds for accounts, trial links, and guests at the guest caps, who see the guest limit line and the demo video ([#802]).
- That limit's message, with the month's "Email me when it's back" tick-box, shows where the chat box was, as for guests. The file button stays beside it, since uploads keep working ([#802]).
- The open page asks Crux whether the limit still holds each time the learner comes back to the tab, and at midnight, so a raise or the credit coming back reopens the box then ([#802]).
- At the owner's share, the owner's own chat box gives way to "You've used your owner share this month" the same way, and nothing the owner sends is kept. Test accounts follow it. After a raise, or when the share refills on the 1st, the box returns when the owner comes back to the tab or at the midnight call ([#802]).
- Still working, for accounts and trial links: everything that costs no AI, a started check (see [Started checks finish](#started-checks-finish)), starting a check within the check limit, the ceiling and the month, and file uploads and reads within the reading limit ([#802]).
- The whole-tutor switch and the region stop keep their own rules (see [`live-faults.md`](live-faults.md) and [`security.md`](security.md)) ([#802]).

### The reply that fills the bar

- Teaching stops at the reply that fills the learner's bar. No reply is cut off, except one our AI provider refuses, or one that faults on Crux's side, which the tutor answers again (see [`ai-layer.md`](ai-layer.md) and [`refusals.md`](refusals.md)) ([#675], [#678], [#735], [#771], [#802]).
- A message accepted before the bar filled, because it was queued behind the reply that fills it or sent from another browser at that moment, is answered at once, past the bar, together with anything else queued, as one reply. Then the box closes ([#802]).
- The owner's own share is like a learner's bar, so one such reply runs past it too ([#802]).
- Crux knows the cost only when the reply arrives, so it adds its own fixed line after the last reply past the bar: "That's today's tutoring. The tutor will pick up here tomorrow." It names the reset that applies, such as "on Monday". This costs no AI ([#734], [#802]).

### At the ceiling, the month, or a stop

- The daily ceiling and the month's budget are shared by every learner, so nothing runs past them. A queued message goes back into the learner's box unsent. No calendar day spends more than the ceiling, apart from a started check ([#802]).
- At a credit or workspace stop, where no call can run, a queued message goes back into the box the same way ([#802]).
- When any limit is reached while the page is open, the next send shows the limit message in the box's place ([#675], [#802]). That includes the ceiling, the month, the learner's limit filled in another browser or by a background answer, a credit or workspace stop, and a lowered limit.
- The words of a message handed back come back in the box when it returns, while that tab stays open. Nothing is stored, and no message a stop caught waits while Crux is stopped ([#802]).
- A check answer a stop caught isn't kept, and the problem is swapped when the check resumes (see [`mastery-check.md`](mastery-check.md)) ([#802]).
- Guests are handled the same way ([#802]).

### Waiting messages

A message can still wait for another reason: the whole-tutor switch, the region stop, a reply that faulted twice, an open age question, a lock, a harmful file or a seal ([#734], [#771], [#802]).

- Such a message still waits on a visit at a full limit, and is answered after the reset. After the reset, opening the app answers every waiting message and starts every waiting file's read, oldest session first, several in one session together. The cost comes off the new limit ([#675], [#734], [#802]).
- An owner's raise counts as a reset. If a block clears while the app is open, the answers run then, without reopening, and only once across browsers. Blocks are a tap on the age question, "Keep my account", agreeing to terms, removing a held file, lifting a seal or a lock, a raise, or midnight passing ([#734], [#736]). A message the whole-tutor switch stopped is answered as [`live-faults.md`](live-faults.md) says ([#736]).
- The session the learner is in goes first, so a new message there still starts within the main file's 5 seconds ([#734]).
- A background answer never opens a check problem. After reteaching in a half-done check, the next problem waits until the learner opens that session ([#734]).
- A background answer is not a sitting, and it does not restart the 7-day clock (see [`feedback.md`](feedback.md) and [`sessions.md`](sessions.md)) ([#734]).
- A session that needs a step from the learner first, such as the "continue" or "refresh first" offer, waits until they open it. The offer comes first, then the answer ([#734]).
- In a session held by a harmful file (see [`files.md`](files.md)), a waiting message stays waiting until the file is gone. An age statement in it waits too ([#734]).
- Deleting a session erases its waiting messages ([#671], [#734]).

### Files at a limit

- A file's read into its outline uses the reading limit, not the tutoring limit (see [`spending.md`](spending.md)), so a full tutoring limit doesn't stop it. Its cost still counts in the budget and the ceiling ([#802]).
- A file sent before the ceiling or the month ran out is read in full ([#675]). When that read uses the last of them, the read finishes and Crux shows a fixed line saying the file uploaded successfully, then the limit message ([#734], [#802]).
- The fixed line shows only for a usable file. If the read finds a harmful file or fails, Crux shows that message at once, in place of the line (see [`files.md`](files.md)) ([#734]).
- A file sent when the ceiling or the month is already used, or Crux is stopped, is stored, converted and split into pages at once, since that costs no AI. A file that fails shows the "Couldn't read this file" line then (see [`files.md`](files.md)) ([#734], [#802]).
- Only its AI read waits. Crux says so, naming the reset that applies: "Your file is saved. It'll be read when you're back tomorrow." After the reset, opening the app starts the read. The file counts toward the allowance while it waits, and the learner can remove it ([#734]).
- Once a read uses the last of the ceiling or the month, other files' reads wait for the next reset. While the owner has files switched off, files' reads wait too ([#734], [#802]).
- A typed message sent with a file is answered after its read. If the read waits for the reading limit, the message waits with it, and a later message in that session is answered on its own. If the read used the last of the ceiling or the month, the message goes back into the box unsent ([#734], [#802]).

## Started checks finish

- A mastery check that has started runs to the end, with its result and the after-mastery menu, past the learner's limit, the ceiling and the month ([#675]).
- This covers a half-done check resumed on a later day, its "refresh first" step, and disputes on it ([#675]).
- At a limit, the chat box stays for the check's answers and its end step. Once the result shows, with the after-mastery menu on a pass, the box gives way to the limit message. The menu stays in the thread, and the learner picks after the reset ([#802]).
- The offer has "Start the check" and "Not yet" buttons, and the "continue" or "refresh first" offer has buttons too. They need no AI to read (see [`mastery-check.md`](mastery-check.md)) ([#734]).
- A check starts when the learner accepts it, by a tap, or by a typed reply the tutor reads while the box is open. Only the check limit, the ceiling and the month can stop it starting; a full tutoring limit doesn't. At 99% of the ceiling or the month it starts, and runs past them ([#734], [#802]).
- A tap on "Start the check" with no checks left this week shows "Your next check is ready on Monday". At a used ceiling or month, it shows that limit's message and "Your check is ready when you're back". Either way no problem has been seen, the objectives stay shown, and the tutor offers the check again on return ([#734], [#802]).
- **Reteaching stops at the limits.** After a real miss in the refresh, the objective is taught as usual (see [`mastery-check.md`](mastery-check.md)). A limit stops that teaching like any teaching: the box closes, and the check stays half-done. Earlier answers still count. The problems that follow run past the limits ([#731], [#734], [#802]).
- A check does not finish when the owner switches checks off for a fault, at a workspace limit or a credit stop, or at the owner's share for the owner's own check. It pauses as half-done, and the box closes (see [`mastery-check.md`](mastery-check.md)) ([#675], [#678], [#802]).
- A guest's mini check stops at the guest caps, the ceiling and the month like any guest reply, since a guest can resend an older saved state (see [`data-model.md`](data-model.md)) ([#719], [#733], [#734]).

## On screen

The waiting badge on a session in the list is in [`app-shell.md`](app-shell.md) ([#752]). The limit message in the box's place, and the fixed lines after a filling reply and after a file, are in [`learning-screen.md`](learning-screen.md) ([#751], [#802]).

[#671]: https://github.com/calmxz/Crux/issues/671
[#675]: https://github.com/calmxz/Crux/issues/675
[#678]: https://github.com/calmxz/Crux/issues/678
[#719]: https://github.com/calmxz/Crux/issues/719
[#731]: https://github.com/calmxz/Crux/issues/731
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#736]: https://github.com/calmxz/Crux/issues/736
[#751]: https://github.com/calmxz/Crux/issues/751
[#752]: https://github.com/calmxz/Crux/issues/752
[#771]: https://github.com/calmxz/Crux/issues/771
[#802]: https://github.com/calmxz/Crux/issues/802
