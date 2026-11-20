# The AI layer

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers how Crux reaches its AI, which model does each job, how a prompt is built, what the tutor reports, and what happens when a call fails. Blocked calls and the distress check's call are in [`refusals.md`](refusals.md), and the maths library is in [`maths-library.md`](maths-library.md). The amounts are in the main file's "Money". What Crux decides instead of the model is in the main file's "Crux decides". This file is written from [#679] as it stands. Research [#727] may reopen it, and a reopening edits this file ([#680]).

## Route and projects

- The Google GenAI SDK calls Gemini Enterprise Agent Platform (formerly Vertex AI), for the meantime, at the **global** address at list price ([#679]). Where that means Google may process data is in [`terms-and-policy.md`](terms-and-policy.md).
- Crux calls `generateContent`, for the meantime ([#679]).
- Crux keeps every conversation in its own format, with the model's thought blocks kept unchanged. Every model call goes through one module ([#679]).
- Crux moves to the Interactions API, with storage off, only when Google's docs give a reason: a notice that `generateContent` is being retired, or a feature Crux needs launching only there. The move means rewriting that module and a full AI test round. The owner checks Google's changelog at each monthly strict test round ([#678], [#679]).
- There are two Google Cloud projects on the owner's one billing account: **Crux** and **Crux tests**. Each has its own spend-cap budget on the service "Gemini Enterprise Agent Platform (formerly Vertex AI)", not "Gemini API" ([#679]). The amounts and what a cap does are in the main file's "Money" and [`spending.md`](spending.md).
- Re-marks of learners' checks run in the Crux project, on the data where it lives. The live backend gets no access to the Crux tests project ([#728] Answer 1).

### Signing in to Google

- Crux and the tests reach Gemini through service accounts, with a custom role that allows only model calls (`aiplatform.endpoints.predict`). A smoke test confirms that role is enough ([#716]).
- Live Crux uses Cloud Run's own identity. Tests in GitHub use workload identity federation. The owner's computer uses the owner's Google login, acting as the account ([#716]).
- No Google key is stored anywhere. The Express API keys are deleted once the smoke test passes on the service accounts ([#716]).

## Models by job

| Job | Model | Thinking level |
|---|---|---|
| Teaching chat, including related-topic suggestions | 3.5 Flash-Lite | `low` on every call, never `minimal` |
| Every mastery-check call: writing problems and model answers, the independent working, marking, re-marking, and the end step | 3.5 Flash-Lite | Per job, the lowest level that passes the strict tests, starting at `medium` |
| Reading a file into its outline | 3.5 Flash-Lite | The lowest level that passes the file tests, starting at `low` |
| The distress check | 3.5 Flash-Lite | The lowest level that passes its AI test, starting at `low` |
| Grading AI tests | 3.8 Flash | `medium` |

All of these come from [#679], except the distress check ([#735]). Flash-Lite's `low` setting comes from the teaching test on [#684]. At `minimal` it asked for a topic it had been given, and repeated a hint instead of stepping it up.

- The grader moves to Gemini 4 Argon only if 3.8 Flash fails the grader's example list, or the tutor moves to 3.8 Flash ([#679]).
- If Flash-Lite cannot pass a job, the planned fallback is 3.8 Flash, as a recorded change. For the check's calls, that means revisiting the tutoring limits. For the teaching chat, it means the budget about doubling and the grader moving to Argon. For the distress check, it means 3.8 Flash at `low` ([#679], [#735]).

### Settings on every call

- The thinking level is set explicitly ([#679]).
- Temperature is left unset, since Flash-Lite ignores custom values ([#679]).
- Versions are pinned: `gemini-3.5-flash-lite` (retires 21 July 2027 or later) and `gemini-3.8-flash` (2 September 2027 or later). A retired version counts as a model change ([#679]).
- Request logging stays off ([#679]).
- Google's adjustable filters (harassment, hate speech, sexually explicit, dangerous content) are set explicitly to `OFF`. Only Google's built-in protections can block for harm. Turning a filter on is a recorded change ([#735]).
- Google's terms allow this. The owner alone is responsible for that choice, and Google's copyright indemnity may not cover a reply made with filters off ([#735]).
- Crux counts each call's cost as [`spending.md`](spending.md) says.

## The prompt

- **Order, for caching:** the instructions first, then the file outline and topic slice, then the conversation, with the learner's note and teaching state last. A change in an objective's status leaves the cached part intact ([#679]).
- The tutor writes maths as LaTeX, using only what KaTeX draws, which the prompt names. It writes session and topic names without LaTeX ([#771]).
- The tutor's instruction is in [`teaching.md`](teaching.md). The outline, the topic slice and the added pages are in [`files.md`](files.md). The note is in [`sessions.md`](sessions.md).

### Text that is never an instruction

The main file lists these sources. Crux defends against them in layers, with no upload scanner ([#679]):

- File content is fenced as data, under an instruction saying so ([#679]). The main file's other sources, and a stopped message sent to the distress check, are fenced the same way ([#735]).
- The marker never sees files, and Crux applies the pass rule ([#669], [#679]).
- The tutor's tools only fetch pages and look things up in the current session's earlier conversation, or another session's only when the learner names it ([#679]). Its other tools only tell Crux what happened, and Crux decides what follows.
- The age answer is Crux's own buttons ([#679]).
- The strict tests check the rest (see [`ai-tests.md`](ai-tests.md)) ([#678], [#679]).
- The tutor has no Google Search tool ([#679]).

## What the tutor reports

The tutor reports to Crux only through tool calls, never by Crux reading the chat ([#679]):

- a problem's result;
- the age question (see [`age.md`](age.md));
- a page request;
- a lookup;
- related topics, each tagged with where it came from, for Crux to sort (see [`learning-loop.md`](learning-loop.md));
- a decline, naming its kind from the harm list, with a mark for the two cases that flag at once (see [`misuse.md`](misuse.md)) ([#733]);
- a diagram, as Mermaid text of one of the three types in [`teaching.md`](teaching.md) ([#769]), and a graph, as a function in LaTeX with its range and the points or tangent to mark (see [`teaching.md`](teaching.md)) ([#751]);
- a file mistake, with the file's maths step in LaTeX where there is one, and what the teacher said about one (see [`files.md`](files.md)) ([#751]).

Each turn carries an idempotency key, so a tool result is recorded once ([#716]).

## When a call fails

- **Overload:** only 429 and 503 are retried, twice, at about 0.5 s and 1.5 s with jitter. Overload is never retried once streaming has started ([#716]). A broken reply is answered again once (see [A broken reply](#a-broken-reply)) ([#771]).
- If no first word has arrived by about 5 seconds, the learner sees "The tutor is busy right now. Try again in a minute." The sitting is kept, and a mastery check under way pauses as half-done ([#679], [#716]).
- Mastery-check calls use the same retries, but "Marking…" may wait up to about 20 seconds, since that is not a reply starting ([#716]). Writing a problem gets the same wait ([#735]).
- Crux does not switch to another model on its own during an outage (see the map's Out of scope list) ([#679], [#716]).
- When Google's spend cap stops Crux, [`spending.md`](spending.md) applies ([#679]).

### A broken reply

A broken reply is one whose stream ends before the reply is complete, for any reason except Google blocking it. Crux's server tells the two kinds apart, never the browser ([#771]):

- **A lost connection:** the learner's connection drops or the phone sleeps, while Crux carries on. Crux finishes the reply by itself, and a learner who leaves finds it at the next opening. Whether Crux finishes the same reply within its request or answers again through Cloud Tasks is left to the build. No work runs outside a request either way (see [`hosting.md`](hosting.md)).
- **A fault on Crux's side:** Crux's server, the Worker, a time limit, or an error from Google partway. The words so far are removed, none are saved, and the tutor answers again from the start.
- Crux answers again once per message. A second fault leaves the message waiting, answered at the next opening or with the learner's next message in that session.
- The new answer runs even if the broken words filled the learner's own tutoring limit, as the retry after a block does. Anything else that stops a reply leaves the message waiting under that rule.
- During a mastery check, a reply that faults twice pauses the check as half-done. An answer that runs as a background answer never opens a check problem.
- Tool results from words that are removed are dropped, as for a reply Google removes. The new answer reports afresh under the turn's idempotency key, so an age question or a decline is recorded once.
- A broken attempt is counted like any reply (see [`spending.md`](spending.md)). Answering again after a broken reply and the retry after a block are separate, each once per message.
- A guest's browser acts for the guest, since Crux holds nothing for them (see [`landing-screens.md`](landing-screens.md)).

## Gaps

- **The AI layer may change:** research [#727] checks Claude through Anthropic's API ([#680]).
- **How reliably Flash-Lite at `low` calls its tools:** a tutor that forgets to report a solved problem leaves an objective unshown. Open on [#678] ([#679]).
- **Whether the topic slice keeps the file rules on real decks,** and whether Gemini can read pages straight from the bucket: see [`files.md`](files.md).
- **What a sitting costs on Agent Platform:** see [`spending.md`](spending.md).

## On screen

The session screen is in [`learning-screen.md`](learning-screen.md): "The tutor is busy right now", the two lines when Google blocks a reply, and the message when a problem is swapped are lines in the thread, and diagrams and graphs show inside the tutor's message ([#751]). How a reply arrives and breaks, and how maths shows, are there too ([#771]).

[#669]: https://github.com/calmxz/Crux/issues/669
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#680]: https://github.com/calmxz/Crux/issues/680
[#684]: https://github.com/calmxz/Crux/issues/684
[#716]: https://github.com/calmxz/Crux/issues/716
[#727]: https://github.com/calmxz/Crux/issues/727
[#728]: https://github.com/calmxz/Crux/issues/728
[#733]: https://github.com/calmxz/Crux/issues/733
[#735]: https://github.com/calmxz/Crux/issues/735
[#751]: https://github.com/calmxz/Crux/issues/751
[#769]: https://github.com/calmxz/Crux/issues/769
[#771]: https://github.com/calmxz/Crux/issues/771
