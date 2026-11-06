# The AI layer

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them. Where this file names an area file not yet written, use that file's source tickets in the main file's index.

This file covers how Crux reaches its AI, which model does each job, how a prompt is built, what the tutor reports, what happens when a call fails or is blocked, the maths library, and the distress check's call. The amounts are in the main file's "Money". What Crux decides instead of the model is in the main file's "Crux decides". This file is written from [#679] as it stands. Research [#727] may reopen it, and a reopening edits this file ([#680]).

## Route and projects

- The Google GenAI SDK calls Gemini Enterprise Agent Platform (formerly Vertex AI), for the meantime, at the **global** address at list price ([#679]). Where that means Google may process data is in [`privacy.md`](privacy.md).
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
- The tutor's instruction is in [`teaching.md`](teaching.md). The outline, the topic slice and the added pages are in [`files.md`](files.md). The note is in [`sessions.md`](sessions.md).

### Text that is never an instruction

The main file lists these sources. Crux defends against them in layers, with no upload scanner ([#679]):

- File content is fenced as data, under an instruction saying so ([#679]). The main file's other sources, and a stopped message sent to the distress check, are fenced the same way ([#735]).
- The marker never sees files, and Crux applies the pass rule ([#669], [#679]).
- The tutor's tools only fetch pages and look things up in the current session's earlier conversation, or another session's only when the learner names it ([#679]). Its other tools only tell Crux what happened, and Crux decides what follows.
- The age answer is Crux's own buttons ([#679]).
- The strict tests check the rest (see `ai-tests.md`) ([#678], [#679]).
- The tutor has no Google Search tool ([#679]).

## What the tutor reports

The tutor reports to Crux only through tool calls, never by Crux reading the chat ([#679]):

- a problem's result;
- the age question (see [`age.md`](age.md));
- a page request;
- a lookup;
- related topics, each tagged with where it came from, for Crux to sort (see [`learning-loop.md`](learning-loop.md));
- a decline, naming its kind from the harm list, with a mark for the two cases that flag at once (see [`misuse.md`](misuse.md)) ([#733]).

Each turn carries an idempotency key, so a tool result is recorded once ([#716]).

## When a call fails

- **Overload:** only 429 and 503 are retried, twice, at about 0.5 s and 1.5 s with jitter. There is no retry once streaming has started ([#716]).
- If no first word has arrived by about 5 seconds, the learner sees "The tutor is busy right now. Try again in a minute." The sitting is kept, and a mastery check under way pauses as half-done ([#679], [#716]).
- Mastery-check calls use the same retries, but "Marking…" may wait up to about 20 seconds, since that is not a reply starting ([#716]). Writing a problem gets the same wait ([#735]).
- Crux does not switch to another model on its own during an outage (see the map's Out of scope list) ([#679], [#716]).
- When Google's spend cap stops Crux, [`spending.md`](spending.md) applies ([#679]).

## When Google blocks a call

A blocked call has no tool call, so Crux reads Google's block result itself ([#733]). This covers a blocked message and a blocked reply ([#735]).

| Block result | Counts as | What happens |
|---|---|---|
| Prohibited content | A sealed flag | The session is sealed. A second on the account locks it (see [`misuse.md`](misuse.md)) ([#735]) |
| Any other harm result, should one occur with the filters off | A decline, kind "blocked by Google" | As [`misuse.md`](misuse.md) says ([#733]) |
| Recitation, language, personal details, or an unspecified policy reason | A failed call, not a decline | The retry below ([#735]) |

**A failed call of this kind** gets one retry per message, with a hidden line: "Explain in your own words. Don't quote the text." The file's pages still go. The line is not saved or carried to later turns, and the retry runs even if the blocked attempt filled a limit ([#735]). If the retry is blocked too, the learner sees "The tutor couldn't answer that. Try asking another way." A background answer leaves that line in place of the reply ([#735]).

**A reply blocked partway through:** the words shown so far are removed, and Crux saves none of them. A failed call of the kind above then gets its retry. After a harm result, the learner sees "The tutor can't continue that reply". This is the one exception to the main file's "a reply is never cut off midway" ([#735]).

**A blocked message** stays in the conversation for the learner, and is left out of later prompts and the lookup. It counts once. Messages answered together count as one message. A tool result from a removed reply is dropped ([#735]).

**During a mastery check** ([#735]):

- A blocked problem is thrown away unseen, and a new one is written. It is not a decline.
- If marking is blocked after the retry, the problem is swapped at once: "We couldn't mark that one because our AI provider's filter stopped the marking. This doesn't count against you. Here's a new problem."
- After 2 swaps on the same problem, or 2 blocked writes in a row, the check pauses as half-done. The owner's daily email lists it. Opening the check resumes it, with the problem swapped and the count back at 0.
- A blocked slip fix or walk-through is treated like blocked marking.
- A blocked dispute stays unused: "We couldn't check that dispute. Try again later."
- A blocked re-mark leaves the pass standing, and the daily email lists it.
- A prohibited-content result seals the session. The check waits half-done until the seal is lifted.

**Reading a file:** a failed call of this kind follows the failed-read rule in [`files.md`](files.md) after its retry. A harm result gets no retry: prohibited content seals the session, and any other counts as a harmful file. Overload, or a cap, never uses up a read's tries ([#735]).

## The maths library

The library is SymPy. Where it runs in a check is in [`mastery-check.md`](mastery-check.md).

- **What it reads:** only LaTeX, with the Lark backend. `parse_expr` and `sympify` never run on outside text ([#716]).
- **What goes to it:** only expression and number answers. Equations, sets, intervals and worded answers go to the AI's independent working ([#716]).
- **How it compares:** by simplifying and a numeric spot-check. Each comparison runs in a separate process, killed after a few seconds ([#716]).

| Result | When |
|---|---|
| Match | The difference simplifies to 0, or is near 0 at several random points |
| No match | Any valid point clearly differs |
| Can't tell | A point cannot be evaluated, the time runs out, or the answer is not an expression or number |

- **Model answers:** a match is saved. No match throws the problem away unseen, and a new one is written and checked. "Can't tell" goes to the AI's independent working ([#679]).
- **Final answers:** it also compares the learner's final answer with the model answer. A disagreement with the marker brings a fresh re-mark, told whether the final values match, before the learner sees a result ([#679]).
- The library never marks alone, and the working is still judged ([#679]).

## The distress check's call

When a limit stops a message, Crux asks the model whether the person is in distress. What follows from the answer is in [`spending.md`](spending.md) ([#734]).

- The call sends only the stopped message, and asks one yes-or-no question ([#734]). The answer comes in a fixed format ([#735]).
- It spends from the distress check's pot, USD 0.05 a day, paid from the owner's share. The owner can change the amount on the owner page ([#734]).
- No check runs when the pot or the share has run out, or when Google's cap has stopped Crux ([#734]).
- A call that fails, is blocked, or returns anything else counts as "no". It is never a decline, and it never seals a session ([#735]).

## Gaps

- **The AI layer may change:** research [#727] checks Claude through Anthropic's API ([#680]).
- **Build checks on Google's behaviour:** how a block arrives mid-stream, and whether a blocked attempt is charged ([#735]).
- **How reliably Flash-Lite at `low` calls its tools:** a tutor that forgets to report a solved problem leaves an objective unshown. Open on [#678] ([#679]).
- **Whether the topic slice keeps the file rules on real decks,** and whether Gemini can read pages straight from the bucket: see [`files.md`](files.md).
- **What a sitting costs on Agent Platform:** see [`spending.md`](spending.md).

## On screen

Layout is not decided (see the main file's Gaps). These rules need: "The tutor is busy right now", the two lines when Google blocks a reply, and the message when a problem is swapped ([#679], [#733], [#735]).

[#669]: https://github.com/calmxz/Crux/issues/669
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#680]: https://github.com/calmxz/Crux/issues/680
[#684]: https://github.com/calmxz/Crux/issues/684
[#716]: https://github.com/calmxz/Crux/issues/716
[#727]: https://github.com/calmxz/Crux/issues/727
[#728]: https://github.com/calmxz/Crux/issues/728
[#733]: https://github.com/calmxz/Crux/issues/733
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
