# Refusals and the distress check

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what happens when the AI provider refuses a call, the distress check, and what Crux keeps of a refused message. How Crux reaches its AI, the models and what happens when a call fails are in [`ai-layer.md`](ai-layer.md).

## When our AI provider refuses a call

A refused call has no tool call, so Crux reads the refusal's category itself ([#733], [#802]). This covers a refused message and a refused reply ([#735]).

| Category | Counts as | What happens |
|---|---|---|
| `bio`, `cyber`, `general_harms` | A decline, kind "refused by our AI provider" | As [`misuse.md`](misuse.md) says. A `general_harms` refusal goes to the distress check first, below ([#802]) |
| `frontier_llm`, `reasoning_extraction` | A failed call, not a decline | "The tutor couldn't answer that. Try asking another way.", with no retry ([#802]) |
| A category Crux doesn't know | As `general_harms` | The owner's daily email names the new category ([#802]) |

- **A reply refused partway:** the words shown so far are removed, and Crux saves none of them. It then follows its category's line: a decline shows "The tutor can't continue that reply", and a failed call shows the failed-call line. This and a fault on Crux's side (see [A broken reply](ai-layer.md#a-broken-reply)) are the two exceptions to the main file's "a reply is never cut off midway" ([#735], [#771], [#802]).
- A refused message is left out of later prompts and the lookup. It counts once. Messages answered together count as one message. A tool result from a removed reply is dropped ([#735]).
- A background answer that is refused leaves its line in place of the reply ([#735]).
- Seals come only from the tutor's own report of sexual content involving minors (see [`sealed-sessions.md`](sealed-sessions.md)). At-once flags come only from the tutor's own report too, so a refused reply can't raise one ([#802]).

### What Crux keeps of a refused message

- A refused message's text is erased when it is refused, and never shown to the owner once it is refused ([#802]).
- The learner sees it on screen until they leave the page. After that, and for the owner in a flagged or shared session, it shows only as "Refused by our AI provider", with its date. A copy holds only that marker ([#802]).
- A message that waited first (the whole-tutor switch, the region stop, a reply that faulted twice, a typed reply at the age question, a lock, a harmful file, a seal) is stored while it waits, and erased when its reply is refused. A refused distress check on it erases nothing, and it is still answered ([#802]).
- A message refused as `general_harms` is erased after its distress check, which reads it. A check cut off by a stopped server is claimed and run again, as [`hosting.md`](hosting.md) does for claims, and then follows the distress rules below if it still fails ([#802]).
- The erasure has its own entry in the restore log, with a test that it survives a restore (see [`backups-and-releases.md`](backups-and-releases.md)). It erases the text, keeps the marker, clears any waiting state, and resets a session name taken from the refused words; a name the learner gave stays ([#802]).
- A session whose first request was refused shows "New session" until the tutor names it from the next request it answers, including a session whose first words showed while that request waited (see [`sessions.md`](sessions.md)) ([#802]).
- A flag made only of refusals is judged from dates and kinds, or dismissed (see [`misuse.md`](misuse.md)) ([#802]).

### During a mastery check

A refused check call follows the rule for its job, with no retry. It is never a decline, and never seals a session ([#735], [#802]).

- A refused write or independent check: the problem is thrown away unseen, and a new one is written.
- Refused marking: the problem is swapped at once: "We couldn't mark that one because our AI provider's filter stopped the marking. This doesn't count against you. Here's a new problem."
- After 2 swaps on the same problem, or 2 refused writes in a row, the check pauses as half-done. The owner's daily email lists it. Opening the check resumes it, with the problem swapped and the count back at 0.
- A refused slip fix or walk-through is treated like refused marking.
- A refused dispute stays unused: "We couldn't check that dispute. Try again later."
- A refused re-mark leaves the mark standing, and the daily email lists it.

### Reading a file

A harm-category refusal counts as a harmful file. Any other follows the failed-read rule in [`files.md`](files.md). Overload, a limit or a stop never uses up a read's tries ([#735], [#802]).

## The distress check

The distress check asks the model one yes-or-no question about a message: is this person in distress? The call sends only that message, and the answer comes in a fixed format ([#734], [#735]). It runs in two places ([#802]):

- **A `general_harms` refusal in teaching,** before anything else:
  - Yes: the care line, then the crisis line, and no decline.
  - No: a decline.
  - Refused, or failed after its overload retries: a decline, with the refusal line and no care line.
- **A typed reply while the age question is open,** since the tutor isn't reading then (see [`age.md`](age.md)). Yes gives the care line and the crisis line. A check there that is refused or fails counts as no: the learner sees only "please tap Yes or No".

The care line and the crisis line are fixed text (see [`misuse.md`](misuse.md)). No distress check runs at a limit, on a message the whole-tutor switch or the guest-mode switch stopped, from a barred country, or when a workspace limit or the credit has stopped Crux ([#802]).

### The distress pots

- Accounts' and trial links' checks use a pot of USD 0.05 a day, paid from the owner's share. Once it is used, their refusal checks keep running, paid from the rest of the share, up to a second USD 0.05 that day. After that they get the neutral care line, and no decline ([#734], [#802]).
- Guests' checks have their own pot of USD 0.02 a day, paid from the owner's share. Once it is used, a guest's refusal gets only the refusal line, "The tutor can't continue that reply", with no care line ([#802]).
- A check on a typed reply at the age question stops at its pot. Once it is used, or the owner's share is empty, the learner there sees only "please tap Yes or No" ([#802]).
- If the owner's share is empty, each refusal gets its pot's fallback: the refusal line for guests, the neutral care line for accounts and trial links ([#802]).
- The neutral care line names no helpline and doesn't say the person is in distress ([#802]).
- The pots are outside the budget and the ceiling, and inside Crux's workspace limit. The owner can change all three amounts on the owner page, and gets a push when the accounts' pot or the guests' pot runs out, at most once a day each ([#734], [#802]).

## Gaps

- **Build checks on refusals:** how a refusal arrives mid-stream, and whether a refused attempt is charged ([#735], [#802]).

## On screen

The decline line, the failed-call line, and "Refused by our AI provider" in place of a refused message are lines in the thread, in [`learning-screen.md`](learning-screen.md) ([#751], [#802]).

[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#751]: https://github.com/calmxz/Crux/issues/751
[#771]: https://github.com/calmxz/Crux/issues/771
[#802]: https://github.com/calmxz/Crux/issues/802
