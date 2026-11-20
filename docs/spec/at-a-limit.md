# At a limit

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what happens at a limit and how started checks finish. What Crux counts, the tutoring limits and the messages are in [`spending.md`](spending.md).

## At a limit

### The reply that fills the bar

- Teaching stops at the reply that fills the learner's bar. No reply is cut off, except one Google blocks, or one that faults on Crux's side, which the tutor answers again (see [`ai-layer.md`](ai-layer.md) and [`refusals.md`](refusals.md)) ([#675], [#678], [#735], [#771]).
- Crux knows the cost only when the reply arrives, so it adds its own fixed line after that reply: "That's today's tutoring. Answer whenever you like, and the tutor will pick up here tomorrow." It names the reset that applies, such as "on Monday". This costs no AI ([#734]).
- When the ceiling or the month runs out between replies, the learner's next reply gets the "full" message ([#675]).

### What a stopped message keeps

- A learner is **turned away** when they send something and a limit stops Crux answering it ([#675]).
- A message stopped by any limit is kept. It stays in the conversation, marked as waiting. After the reset, opening the app answers every kept message and starts every kept file's read, oldest session first, several in one session together. The cost comes off the new limit ([#675], [#734]).
- If the limit fills while answering, the rest stay waiting. They also stay waiting on any visit when tutoring cannot run, such as a full limit, an open age question or a lock ([#734]). A message whose reply faulted twice waits too (see [`ai-layer.md`](ai-layer.md)) ([#771]).
- An owner's raise counts as a reset. If a block clears while the app is open, the answers run then, without reopening, and only once across browsers. Blocks are a tap on the age question, "Keep my account", agreeing to terms, removing a held file, lifting a seal or a lock, a raise, or midnight passing ([#734], [#736]). A message the whole-tutor switch stopped is answered as [`live-faults.md`](live-faults.md) says ([#736]).
- The session the learner is in goes first, so a new message there still starts within the main file's 5 seconds ([#734]).
- A background answer never opens a check problem. After reteaching in a half-done check, the next problem waits until the learner opens that session ([#734]).
- A background answer is not a sitting, and it does not restart the 7-day clock (see [`feedback.md`](feedback.md) and [`sessions.md`](sessions.md)) ([#734]).
- A session that needs a step from the learner first, such as the "continue" or "refresh first" offer, waits until they open it. The offer comes first, then the answer ([#734]).
- In a session held by a harmful file (see [`files.md`](files.md)), a kept message stays waiting until the file is gone. An age statement in it waits too ([#734]).
- Deleting a session erases its waiting messages ([#671], [#734]).

### Files at a limit

- A file sent before the limit is read in full ([#675]).
- When that read fills the limit, the read finishes and Crux shows a fixed line saying the file uploaded successfully, then the limit message. The tutor answers after the reset ([#734]).
- The fixed line shows only for a usable file. If the read finds a harmful file or fails, Crux shows that message at once, in place of the line (see [`files.md`](files.md)) ([#734]).
- A file sent when a limit is already full is stored, converted and split into pages at once, since that costs no AI. A file that fails shows the "Couldn't read this file" line then (see [`files.md`](files.md)) ([#734]).
- Only its AI read waits. Crux says so, naming the reset that applies: "Your file is saved. It'll be read when you're back tomorrow." After the reset, opening the app starts the read, and it comes off the new limit. The file counts toward the allowance while it waits, and the learner can remove it ([#734]).
- Once a read fills the limit, other kept files wait for the next reset. While the owner has files switched off, kept files' reads wait too ([#734]).
- A typed message sent with that file is answered after its read ([#734]).

### A learner in distress

A limit stops a message before the tutor reads it. So Crux sends only that message to the model and asks one yes-or-no question: is this person in distress? ([#734])

- **Yes:** Crux adds a care line and, on its own line, the crisis line the tutor points to (see [`misuse.md`](misuse.md)). Both are fixed text.
- **No:** the person sees only the limit message, or the switch's paused line. A check that fails or is blocked counts as no (see [`refusals.md`](refusals.md)) ([#735]).
- The limit message shows at once, and any care line follows it ([#735]).
- This applies to learners, trial links and guests. It also runs on a typed reply while an age question is open, since the tutor is not reading then (see [`age.md`](age.md)). It also runs on a message the whole-tutor or guest-mode switch stopped (see [`live-faults.md`](live-faults.md)) ([#736]).
- These checks have a pot of USD 0.05 a day, paid from the owner's share. It is outside the budget and the ceiling, and inside Google's cap as it stands. The owner can change the amount on the owner page ([#734]).
- When the pot runs out, the share runs out, or Google's cap stops Crux, no check runs ([#734]).
- The tutor still reads a kept message after the reset. A guest's message is never read later ([#734]).

## Started checks finish

- A mastery check that has started runs to the end, with its result and the after-mastery menu, past the learner's limit, the ceiling and the month ([#675]).
- This covers a half-done check resumed on a later day, its "refresh first" step, and disputes on it ([#675]).
- The offer has "Start the check" and "Not yet" buttons, and the "continue" or "refresh first" offer has buttons too. They need no AI to read (see [`mastery-check.md`](mastery-check.md)) ([#734]).
- A check starts when the learner accepts it with room left, by a tap or a typed reply the tutor reads. At 99% of the limit it starts, and runs past the limit ([#734]).
- A tap on "Start the check" when a limit is already full does not start it. The learner sees the limit message and "Your check is ready when you're back". No problem has been seen, and the objectives stay shown. The tutor offers the check again on return ([#734]).
- A typed "yes" at a full limit is kept like any message, since nothing reads it, and the tutor offers the check again ([#734]).
- **Reteaching stops at the limits.** After a real miss in the refresh, the objective is taught as usual (see [`mastery-check.md`](mastery-check.md)). A limit stops that teaching like any teaching, and the check stays half-done. Earlier answers still count. The problems that follow run past the limits ([#731], [#734]).
- A check does not finish when the owner switches checks off for a fault, or when Google refuses calls. It pauses as half-done (see [`mastery-check.md`](mastery-check.md)) ([#675], [#678]).
- A guest's mini check stops at the guest caps, the ceiling and the month like any guest reply, since a guest can resend an older saved state (see [`data-model.md`](data-model.md)) ([#719], [#733], [#734]).

## On screen

The waiting badge on a session in the list is in [`app-shell.md`](app-shell.md) ([#752]).

[#671]: https://github.com/calmxz/Crux/issues/671
[#675]: https://github.com/calmxz/Crux/issues/675
[#678]: https://github.com/calmxz/Crux/issues/678
[#719]: https://github.com/calmxz/Crux/issues/719
[#731]: https://github.com/calmxz/Crux/issues/731
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#736]: https://github.com/calmxz/Crux/issues/736
[#752]: https://github.com/calmxz/Crux/issues/752
[#771]: https://github.com/calmxz/Crux/issues/771
