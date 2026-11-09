# Live faults

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers what happens when an AI test fails on the live version: what the owner switches off, what each switch does, and re-marks after a marking fault. The tests, their tiers and when rounds run are in [`ai-tests.md`](ai-tests.md).

## When a live test fails

### A high-risk fail

The owner switches off the part its test covers, until a fix passes ([#678], [#736]).

| Tests that fail | What goes off |
|---|---|
| Grading integrity | The mastery check |
| Instructions planted in files | Files and the mastery check |
| A harmful file, or a harmless one refused | Files |
| The lookup | The lookup |
| Age, the harm line and the twin rule | The whole tutor |

- The owner page has a switch for each, plus guest mode, for a fault only guests reach. The switches apply to the owner's account on live too. Dev, the AI tests and staging have their own settings ([#678], [#679], [#736]).
- A fault only in a decline's kind, with the decline still made, switches nothing. It is handled like any other strict fail, below ([#736]).
- A failing distress check has no switch. It keeps running until a fix passes, and it blocks releases like any strict fail ([#736]).
- A fault no fix can solve leaves its part off, with no time limit. If Flash-Lite cannot pass the job, the fallback in [`ai-layer.md`](ai-layer.md) applies, as a recorded change ([#679], [#736]).

### Any other strict fail

Nothing goes off. The fail pushes to the owner, an issue opens, and nothing that needs a round is released until a fix passes. The owner may still switch a part off by hand ([#736]).

## What each switch does

Learners see what is paused: "Checks are paused while we fix something; your progress is kept" ([#678]). Each part's line is a screens item. Where two switches are off, each applies ([#736]).

**The whole tutor** ([#736])

- A message sent while it is off is kept, marked as waiting, with this line: "The tutor is down while we fix something. Your message is saved: tap it to try again." It is answered when the learner refreshes the page, taps the message, sends another message there, or next opens the app. A tap too early leaves it waiting.
- The distress check in [`spending.md`](spending.md) runs on that message.
- A check under way pauses as half-done, as below. An answer sent to an open problem meanwhile is not kept, and the problem is swapped on return.
- Guests see guest mode's paused line, below.

**Guest mode** ([#736])

- The public link shows that guest mode is paused, with the demo video. A guest's message is never kept, and the distress check runs on it. A started mini check is dropped. It is also dropped when checks are off, since guests keep nothing.

**The mastery check** ([#678], [#736])

- A check under way pauses as half-done, and resumes under the half-done rules when checks come back, with the open problem swapped (see [`mastery-check.md`](mastery-check.md)). Photo answers stop with it.
- A ready learner is not offered a check. The tutor says checks are paused, and offers it when they are back.
- Disputes wait: "You can dispute this when they're back." A dispute stays open until the next check on that objective starts, so none is lost. A pending slip fix or walk-through waits the same way.
- Reteaching after a refresh miss carries on, with the lookup and files as in teaching, unless those are off too. When the objective is shown again, the next problem waits.

**Files** ([#678], [#736])

- Uploads stop, and existing files are kept out of teaching and out of check-problem writing. Teaching carries on without them. Viewing and removing files still work. Photo answers carry on, since they are answers, under the checks switch.
- A read under way is dropped, with no try used up and no charge. The file stays saved, and its read starts on the learner's next refresh, tap or opening once files are back.
- A file given with the request gets: "Files are paused while we fix something. Your file is saved and will be read when they're back. You can wait, or tell me what you'd like to learn without it." A message held meanwhile is taken as the request (see [`files.md`](files.md)).
- After a planted-file fail, the line also says: "Our testing showed that text inside a file could affect the tutor." Crux does not search learners' files.

**The lookup** ([#678])

- The tutor says it cannot look things up right now.

## Re-marks after a marking fault

Once a marking fault is fixed, every mark the faulty marker gave since the last round that passed the failing test is re-marked by the fixed marker, from the saved answers. That covers passes and fails, checks that failed overall, half-done checks and disputes ([#678], [#736]).

- If the fault was in the model answers, a fresh marker checks each saved model answer first and corrects it, as a dispute does. Otherwise the saved model answers stand ([#669], [#736]).
- The re-mark reads any slip fix or walk-through saved with the answer ([#736]).
- Re-marks run in the Crux project and spend from the owner's share ([#728] Answer 1). Where they pause is in [`spending.md`](spending.md) ([#734]).
- Checks stay off until the re-marks finish. The owner page shows their progress, and the owner switches checks back on ([#736]).
- **After a planted-file fail,** a fresh marker checks the model answers of every check that used files since the last round that passed that test. A wrong one is corrected, and its answers re-marked. Checks come back once those re-checks finish ([#736]).
- A sealed session is never re-marked while sealed, and its re-mark runs if the seal is lifted (see [`misuse.md`](misuse.md)), and a blocked re-mark leaves the mark standing (see [`ai-layer.md`](ai-layer.md)) ([#735]).

| Re-mark finds | What happens |
|---|---|
| Right | Right. A mark that was wrong follows the rules for a dispute won (see [`mastery-check.md`](mastery-check.md)) |
| A slip | Right if it was fixed in the end step, or never offered a fix. Wrong if a fix was offered and not made |
| Wrong | A pass is undone (below) |
| Unsure | A pass is undone the same way. A mark that was wrong stays wrong, and keeps its dispute |

The re-mark gives what a correct marker would have given at the time ([#736]).

- A half-done check is re-marked before it resumes, like live marking: a slip or unsure there goes through the end step as usual ([#736]).
- **Several checks on one objective:** any check the re-mark finds right passes it, dated that check. A later check's wrong answer still shows as wrong, and takes nothing away. The objective notes that the earlier check was re-marked as correct. A half-done check drops the problems of an objective that is now passed, and ends with no result if nothing is left ([#736]).
- A problem whose mark changes gets a fresh dispute ([#678]).
**An undone pass** ([#736]):

- The objective stays shown, with no trouble mark. Its topic is no longer mastered.
- In a mastered topic, it is checked again on 2 problems, whenever the learner chooses. If the learner is in another topic, that topic pauses meanwhile, as for a dropped objective (see [`learning-loop.md`](learning-loop.md)).
- In a topic not yet mastered, it joins the next check, with the objectives still to prove.
- Several undone objectives in one topic share one check, 2 problems each. The learner is told how many objectives it covers.
- The topic stays fixed, but the learner may drop the undone objective, as after a fail (see [`mastery-check.md`](mastery-check.md)). Anything added or reworded becomes the next topic.
- A re-added dropped objective's pass, undone, returns its topic to the narrower mastery (see [`learning-loop.md`](learning-loop.md)).
- A failed objective that was dropped, and is now found right, is passed and back in its topic. The topic gets its full name back, and its dropped-objective offer is used up.
- The go-public counts change as [`feedback.md`](feedback.md) says. A window already judged keeps its verdict ([#678]).

### Telling the learner

Only learners whose marks change are told ([#678]).

- **A finished check:** an account gets an email: "We re-marked a check after a fault in our marking. See what changed in Crux." It is a required email (see [`operations.md`](operations.md)). On their next visit, an account or a trial link sees the change on screen ([#736]):
  - Wrong: "We found a fault in our marking and re-marked your check from 20 Feb. Problem 3 was marked right but isn't. Take a check on that objective any time." ([#678])
  - Unsure: "We can't be sure of Problem 2 after a fault in our marking. Take a check on it any time."
  - Right: "We found a fault in our marking and re-marked your check from 20 Feb. Problem 2 was marked wrong but is right, so 'chain rule' is passed."
- **A half-done check:** no email. When the learner next opens it: "A mark in this check changed after a fault in our marking. You'll see it in your result." ([#736])

## On screen

The session screen is in [`learning-screen.md`](learning-screen.md): each part's "paused" line, the tap on a waiting message and the re-mark notices in the thread, and the dispute's wait line in the problem sheet ([#751]). The rest of the layout is not decided (see the main file's Gaps). These rules need: the owner page's switches and re-mark progress ([#678], [#736]).

[#669]: https://github.com/calmxz/Crux/issues/669
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#728]: https://github.com/calmxz/Crux/issues/728
[#734]: https://github.com/calmxz/Crux/issues/734
[#735]: https://github.com/calmxz/Crux/issues/735
[#736]: https://github.com/calmxz/Crux/issues/736
[#751]: https://github.com/calmxz/Crux/issues/751
