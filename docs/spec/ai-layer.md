# The AI layer

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers how Crux reaches its AI, which model does each job, how a prompt is built, what the tutor reports, and what happens when a call fails. Refused calls and the distress check's call are in [`refusals.md`](refusals.md), and the maths library is in [`maths-library.md`](maths-library.md). The amounts are in the main file's "Money". What Crux decides instead of the model is in the main file's "Crux decides". This file is written from [#679], as [#802] changed it.

## Route and account

- Crux calls Claude through Anthropic's Messages API and its SDK ([#802]). Every model call goes through one module ([#679]).
- Inference runs at the `global` setting, at list price ([#802]). Where that means Anthropic may process data is in [`terms-and-policy.md`](terms-and-policy.md).
- Crux keeps every conversation in its own format, with the model's thinking blocks kept unchanged, except when a topic's prompt restarts (see [The prompt](#the-prompt)) ([#679], [#802]).
- The account is an individual Console account, for the meantime. Setting up an organization later is a recorded change, after Anthropic support confirms the Max plan's credit stays ([#802]).
- The account has three workspaces, each with a monthly spend limit the owner sets by hand in the Console: **Crux**, **Crux tests**, and **Crux research**, for research runs and the owner's computer. Nothing runs in the Default Workspace ([#802]). The amounts and what a limit does are in the main file's "Money" and [`spending.md`](spending.md).
- Re-marks of learners' checks run in the Crux workspace, on the data where it lives. The live backend has no key for the Crux tests workspace ([#728] Answer 1, [#802]).

### Signing in to Anthropic

- Crux signs in with stored API keys. Live Crux's key is in Google's Secret Manager, and is rotated at each release ([#802]).
- Tests and staging use keys of the Crux tests workspace, as staging already lives with the tests (see [`backups-and-releases.md`](backups-and-releases.md)). The owner's computer uses a key of the Crux research workspace ([#802]).

## Models by job

| Job | Model | Effort | If it fails its tests |
|---|---|---|---|
| Teaching chat, including related-topic suggestions | Haiku 5.5 | The lowest that passes, starting at `medium`, then `high` | Sonnet 5.5, as a recorded change, with its own 40-sitting round, from `medium` |
| Writing problems and model answers | Haiku 5.5 | The lowest that passes, starting at `medium` | Sonnet 5.5, as a recorded change |
| Marking, slip fixes, walk-throughs | Haiku 5.5 | The lowest that passes each job's tests, starting at `medium` | That job alone moves to Sonnet 5.5, as a recorded change |
| The independent check of each model answer, worked solution included | Opus 5.5 | The lowest that passes, starting at `low` | A failed round moves the level up |
| Re-marks | Opus 5.5 | The lowest that passes, starting at `low` | A failed round moves the level up |
| Grading AI tests | Opus 5.5, through the Batch API | The lowest that passes, starting at `low` | A failed round moves the level up |
| Reading a file into its outline | Haiku 5.5 | The lowest that passes, starting at `low` | Sonnet 5.5, as a recorded change |
| The distress check | Haiku 5.5 | The lowest that passes, starting at `low` | Sonnet 5.5, as a recorded change |

All of these come from [#802]. Each job runs at the lowest effort that passes its strict tests (see [`ai-tests.md`](ai-tests.md)).

- Each move to Sonnet brings a new strict round on that job, and nothing goes live until it passes ([#802]).
- A move of the teaching chat to Sonnet comes with the money revisited. At about USD 0.109 a sitting's worth, 25 learners at full use would need about 25 x 17 x 0.109 = USD 46 a month ([#802]).

### Settings on every call

- Effort is set explicitly. Temperature is left unset. Tool definitions are strict ([#802]).
- Versions are pinned: Haiku 5.5 (retires no sooner than 2027-10-07), Sonnet 5.5 (2027-09-28) and Opus 5.5 (2027-09-22). A retired version counts as a model change ([#802]).
- Crux counts each call's cost as [`spending.md`](spending.md) says.

## The prompt

- **Order, for caching:** the instructions first, then the file outline and topic slice, then the conversation. The learner's note and teaching state are appended as messages, never replaced. A change in an objective's status leaves the cached part intact ([#679], [#802]).
- **Append-only:** the prompt is built append-only, so the same code works on an account where Anthropic refuses an edited history. A file removal, an added range dropping out, or anything else that would change the earlier prompt restarts the topic's prompt. The conversation's text is re-sent without the removed pages and without the tutor's earlier thinking, and the cache restarts once ([#802]). Removing a file still erases it at once (see [`files.md`](files.md)).
- A build test sends the beta header and fails on any `thinking_mismatch_allowed` entry ([#802]).
- **Size:** every Haiku prompt stays under 100,000 tokens. When one would pass it, Crux drops the least recently used added ranges until the prompt is under about 75,000. A dropped page asked about again is re-sent from storage. The limit of 20 added pages stays. If the slice and the conversation alone pass 100,000, that reply costs 5 times as much, and is counted as usual ([#802]).
- **Caching:** the 1-hour cache is used on every call except file reads, which use no cache ([#802]).
- **A quiet line in the thread** appears while the session is open, 50 minutes after the tutor's last reply, outside a check, when re-writing the cache would cost more than a whole sitting's worth, which is about 49,000 tokens. It talks of "today's tutoring", never money. Its wording is drafted in the build for the owner ([#726], [#802]).
- The tutor writes maths as LaTeX, using only what KaTeX draws, which the prompt names. It writes session and topic names without LaTeX ([#771]).
- The tutor's instruction is in [`teaching.md`](teaching.md). The outline, the topic slice and the added pages are in [`files.md`](files.md). The note is in [`sessions.md`](sessions.md).

### Text that is never an instruction

The main file lists these sources. Crux defends against them in layers, with no upload scanner ([#679]):

- File content is fenced as data, under an instruction saying so ([#679]). The main file's other sources, and a message sent to the distress check, are fenced the same way ([#735], [#802]).
- The marker never sees files, and Crux applies the pass rule ([#669], [#679]).
- The tutor's tools only fetch pages and look things up in the current session's earlier conversation, or another session's only when the learner names it ([#679]). Its other tools only tell Crux what happened, and Crux decides what follows.
- The age answer is Crux's own buttons ([#679]).
- The strict tests check the rest (see [`ai-tests.md`](ai-tests.md)) ([#678], [#679]).
- The tutor has no web search tool ([#679], [#802]).

## What the tutor reports

The tutor reports to Crux only through tool calls, never by Crux reading the chat ([#679]):

- a problem's result: one report per problem, in the turn the problem ends, before that turn's reply, including a turn that offers the check. It holds the problem's kind (fresh, own or twin), the most serious thing that happened, in this order: misconception, wrong, slip not fixed, gave up, slip fixed, bare right, right, and, for a fresh problem only, whether help was given ([#802]). What each result does is in [`teaching.md`](teaching.md), and the check of a practice answer is in [`maths-library.md`](maths-library.md);
- the age question (see [`age.md`](age.md));
- a page request;
- a lookup;
- related topics, each tagged with where it came from, for Crux to sort (see [`learning-loop.md`](learning-loop.md));
- a decline, naming its kind from the harm list, with a mark for the two cases that flag at once (see [`misuse.md`](misuse.md)) ([#733]);
- a diagram, as Mermaid text of one of the three types in [`teaching.md`](teaching.md) ([#769]), and a graph, as a function in LaTeX with its range and the points or tangent to mark (see [`teaching.md`](teaching.md)) ([#751]);
- a file mistake, with the file's maths step in LaTeX where there is one, and what the teacher said about one (see [`files.md`](files.md)) ([#751]).

Each turn carries an idempotency key, so a tool result is recorded once ([#716]).

A repeated report on the same problem in the same topic, matched by the problem as written, keeps the more serious result, and counts as helped if either report says so. A status already changed is recomputed, only ever toward less credit ([#802]).

## When a call fails

- **Overload:** only rate-limit and overload errors are retried, twice, at about 0.5 s and 1.5 s with jitter. Overload is never retried once streaming has started ([#716]). A broken reply is answered again once (see [A broken reply](#a-broken-reply)) ([#771]).
- If no first word has arrived by about 5 seconds, the learner sees "The tutor is busy right now. Try again in a minute." The sitting is kept, and a mastery check under way pauses as half-done ([#679], [#716]).
- Mastery-check calls use the same retries, but "Marking…" may wait up to about 20 seconds, since that is not a reply starting ([#716]). Writing a problem gets the same wait ([#735]).
- Crux does not switch to another model on its own during an outage (see the map's Out of scope list) ([#679], [#716]).
- When a workspace limit or the credit stops Crux, [`spending.md`](spending.md) applies ([#802]).

### A broken reply

A broken reply is one whose stream ends before the reply is complete, for any reason except the AI provider refusing it ([#802]). Crux's server tells the two kinds apart, never the browser ([#771]):

- **A lost connection:** the learner's connection drops or the phone sleeps, while Crux carries on. Crux finishes the reply by itself, and a learner who leaves finds it at the next opening. Whether Crux finishes the same reply within its request or answers again through Cloud Tasks is left to the build. No work runs outside a request either way (see [`hosting.md`](hosting.md)).
- **A fault on Crux's side:** Crux's server, the Worker, a time limit, or an error from Anthropic partway. The words so far are removed, none are saved, and the tutor answers again from the start.
- Crux answers again once per message. A second fault leaves the message waiting, answered at the next opening or with the learner's next message in that session.
- The new answer runs even if the broken words filled the learner's own tutoring limit. Anything else that stops a reply follows that stop's rule.
- During a mastery check, a reply that faults twice pauses the check as half-done. An answer that runs as a background answer never opens a check problem.
- Tool results from words that are removed are dropped, as for a refused reply. The new answer reports afresh under the turn's idempotency key, so an age question or a decline is recorded once.
- A broken attempt is counted like any reply (see [`spending.md`](spending.md)).
- A guest's browser acts for the guest, since Crux holds nothing for them (see [`landing-screens.md`](landing-screens.md)).

## Gaps

- **How reliably Haiku 5.5 reports problems:** no setup passed the reporting test on [#802], so the first big round decides. Haiku on photo answers is untested, as is its non-maths teaching until that round, and walk-throughs on Haiku have never run ([#802]).
- **Which Anthropic errors count as overload,** a build check. A spend limit's 429 (`enforced_spend_limit_reached`) is a stop, not overload ([#802]).
- **Build checks on the prompt:** counting a prompt's tokens before sending it, for the 100,000-token rule; whether dropping earlier thinking avoids the binding error; and how long the report and the practice check add before the first word ([#802]).
- **Whether the topic slice keeps the file rules on real decks,** and the outline read in parts, untested: see [`files.md`](files.md).

## On screen

The session screen is in [`learning-screen.md`](learning-screen.md): "The tutor is busy right now", the lines when our AI provider refuses a reply, the message when a problem is swapped, and the quiet line are lines in the thread, and diagrams and graphs show inside the tutor's message ([#751]). How a reply arrives and breaks, and how maths shows, are there too ([#771]).

[#669]: https://github.com/calmxz/Crux/issues/669
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#716]: https://github.com/calmxz/Crux/issues/716
[#726]: https://github.com/calmxz/Crux/issues/726
[#728]: https://github.com/calmxz/Crux/issues/728
[#733]: https://github.com/calmxz/Crux/issues/733
[#735]: https://github.com/calmxz/Crux/issues/735
[#751]: https://github.com/calmxz/Crux/issues/751
[#769]: https://github.com/calmxz/Crux/issues/769
[#771]: https://github.com/calmxz/Crux/issues/771
[#802]: https://github.com/calmxz/Crux/issues/802
