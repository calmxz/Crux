# Blocked calls and the distress check

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what happens when the AI provider blocks a call, and the distress check's call. How Crux reaches its AI, the models and what happens when a call fails are in [`ai-layer.md`](ai-layer.md).

## When Google blocks a call

A blocked call has no tool call, so Crux reads Google's block result itself ([#733]). This covers a blocked message and a blocked reply ([#735]).

| Block result | Counts as | What happens |
|---|---|---|
| Prohibited content | A sealed flag | The session is sealed. A second on the account locks it (see [`sealed-sessions.md`](sealed-sessions.md)) ([#735]) |
| Any other harm result, should one occur with the filters off | A decline, kind "blocked by Google" | As [`misuse.md`](misuse.md) says ([#733]) |
| Recitation, language, personal details, or an unspecified policy reason | A failed call, not a decline | The retry below ([#735]) |

**A failed call of this kind** gets one retry per message, with a hidden line: "Explain in your own words. Don't quote the text." The file's pages still go. The line is not saved or carried to later turns, and the retry runs even if the blocked attempt filled a limit ([#735]). If the retry is blocked too, the learner sees "The tutor couldn't answer that. Try asking another way." A background answer leaves that line in place of the reply ([#735]).

**A reply blocked partway through:** the words shown so far are removed, and Crux saves none of them. A failed call of the kind above then gets its retry. After a harm result, the learner sees "The tutor can't continue that reply". This and a fault on Crux's side (see [A broken reply](ai-layer.md#a-broken-reply)) are the two exceptions to the main file's "a reply is never cut off midway" ([#735], [#771]).

**A blocked message** stays in the conversation for the learner, and is left out of later prompts and the lookup. It counts once. Messages answered together count as one message. A tool result from a removed reply is dropped ([#735]).

**During a mastery check** ([#735]):

- A blocked problem is thrown away unseen, and a new one is written. It is not a decline.
- If marking is blocked after the retry, the problem is swapped at once: "We couldn't mark that one because our AI provider's filter stopped the marking. This doesn't count against you. Here's a new problem."
- After 2 swaps on the same problem, or 2 blocked writes in a row, the check pauses as half-done. The owner's daily email lists it. Opening the check resumes it, with the problem swapped and the count back at 0.
- A blocked slip fix or walk-through is treated like blocked marking.
- A blocked dispute stays unused: "We couldn't check that dispute. Try again later."
- A blocked re-mark leaves the mark standing, and the daily email lists it.
- A prohibited-content result seals the session. The check waits half-done until the seal is lifted.

**Reading a file:** a failed call of this kind follows the failed-read rule in [`files.md`](files.md) after its retry. A harm result gets no retry: prohibited content seals the session, and any other counts as a harmful file. Overload, or a cap, never uses up a read's tries ([#735]).

## The distress check's call

When a limit or a switch stops a message, Crux asks the model whether the person is in distress. What follows from the answer is in [`at-a-limit.md`](at-a-limit.md) ([#734]).

- The call sends only the stopped message, and asks one yes-or-no question ([#734]). The answer comes in a fixed format ([#735]).
- It spends from the distress check's pot, USD 0.05 a day, paid from the owner's share. The owner can change the amount on the owner page ([#734]).
- No check runs when the pot or the share has run out, or when Google's cap has stopped Crux ([#734]).
- A call that fails, is blocked, or returns anything else counts as "no". It is never a decline, and it never seals a session ([#735]).

## Gaps

- **Build checks on Google's behaviour:** how a block arrives mid-stream, and whether a blocked attempt is charged ([#735]).

[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#771]: https://github.com/calmxz/Crux/issues/771
