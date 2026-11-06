# Files

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them. Where this file names an area file not yet written, use that file's source tickets in the main file's index.

This file covers what a file does in Crux, from upload to erasure. How the tutor teaches is in [`teaching.md`](teaching.md). What the mastery check does with files is in [`mastery-check.md`](mastery-check.md). A photo answer is not a file (see [`mastery-check.md`](mastery-check.md)).

## Who can add files

- Account holders and trial-link holders can add files ([#667], [#722]).
- Guest mode on the public link is typing only. Someone in guest mode who tries to upload a file or a photo sees "Uploading your own files needs a trial link." with a Request access button while the trial runs. Nothing is stored ([#722]).

## How files shape a request

- Files alone are the request, and are narrowed like any request (see [`learning-loop.md`](learning-loop.md)). A topic-sized file goes straight to the objectives ([#667]).
- When the files are too broad, the options are the files' own topics, each with where it sits: "The product rule (slides 19-27)". There are 3 to 5. The best fit for the learner's goal and level is marked, usually the topic after where they say they are up to ([#667]).
- With files and words, the words pick the part, purpose or level. The files are the source ([#667]).
- When the words ask for something the files lack ("integrals" with a derivatives deck), the tutor asks which, numbered, with no pick marked: taught from its own knowledge, or something from the files ([#667]).
- A file of questions spanning several topics is narrowed like a broad request ([#667]).

## How much the files cover a topic

The tutor judges this per topic. It never labels a whole file as a lesson, a syllabus or an exam. The objectives message says which reading the tutor took, so a wrong one costs one reply to fix ("it's on page 40 of my notes") ([#667]).

| The files | What the tutor does |
|---|---|
| Teach the topic | Objectives come from the files, in their order and terms. Outcomes a file states are used, trimmed to the topic. The message may mention at most one notable gap: something the topic usually includes, or that the learner's goal points to. It is added only if the learner says so. An addition past 5 objectives becomes the next topic ([#667]). |
| Teach a little (under 3 objectives' worth) | Before the objectives, one numbered question. Widen with related material from the files (first and marked as the pick, when the files have some). Add the tutor's own part, labelled "not in your slides". Or stick to what the files have, which gives a topic of 1 or 2 objectives. The question says what the files contain, and never calls it thin: "Your slides have just one slide on the chain rule (slide 30): the formula and one worked example" ([#667]). |
| Only name it (a syllabus line, "Next week: integrals") | Taught from the tutor's own knowledge, like a typed request, using any outcome the file states. No "not in your file" labels ([#667]). |

## Teaching from files

- Teaching follows the files: their order, examples, terms and notation, with pointers ("as on slide 30"). The tutor adds its own explanations, examples and practice, within the objectives ([#667]).
- A file added later is material for the current topic. The tutor switches to its notation, and objectives change only if the learner asks. A file on another topic gets the new-session suggestion (see [`learning-loop.md`](learning-loop.md#switching-topic-mid-way)) ([#667]).
- Questions about the material are answered (see [`teaching.md`](teaching.md)) ([#667]).

### When a file and the tutor disagree

- Conventions and simplifications follow the files. The other version is mentioned once ([#667]).
- An error is called out softly, and the correct form is taught: "Slide 30 looks like it has a typo ... worth checking with your teacher" ([#667]).
- Crux keeps each flag until the learner has checked it with their teacher ([#669], [#671]). How flags and file errors affect the check is in [`mastery-check.md`](mastery-check.md).

### Files of questions

- The tutor never works the learner's own problem (see [`teaching.md`](teaching.md)). This holds for every file of questions alike: problem sheets, quizzes, and past or live exam papers. Crux cannot tell a past paper from a live one, so there is no exam detection ([#667]).
- The twin of question 1 is the first worked example. A stuck learner can get the twin of any question ([#667]).
- An answer key in a file is checked against the tutor's own working, not trusted, and never shown before the learner tries ([#667]).
- When the key and the tutor's working disagree, the tutor shows its working and asks the learner to check with their teacher. It counts that question neither way, and follows what the learner reports back ([#667]).

### Other files

- Nothing learnable in it (a receipt, a CV): "I can't teach from this file, so I won't use it. You can remove it if you added it by mistake. What would you like to learn?" If a topic is already under way, the tutor leaves out the question ([#667], [#732]).
  - The tutor reports the file through a tool call. The file stays until the learner removes it. Crux sends none of its pages or outline to the tutor, and it gives no topics, session name or check-problem style. It does not count toward "that covers everything you came for" ([#670], [#671], [#732]).
- Anything learnable (a novel, an article) is a request, and is narrowed ([#667]).
- Unreadable (blurry, password-protected, empty, broken): the tutor says what went wrong, and offers another file or typing the topic ([#667]). A file Crux processed but cannot follow, such as a blurry photo, stays until the learner removes it, unused, like a file with nothing learnable ([#732]).
- Harmful: declined like a harmful typed request (see [`misuse.md`](misuse.md)) ([#667], [#677]). The decline counts once toward the misuse flag, and removing the file does not undo it ([#677], [#732]).
  - The tutor reports the file through a tool call, when the read finds the harm or whenever it spots it later. From then on, Crux sends none of its pages or outline to the tutor, including when the tutor writes check problems ([#679], [#732]).
  - The tutor says: "I can't help with this file. This session can't continue until you remove it." The session waits until the file is removed or the session is deleted. Progress is kept, and the learner's other sessions stay open ([#732]).
  - During the wait, the age question, the tutor's care for a learner in distress, and disputes on a finished check still work (see [`age.md`](age.md), [`misuse.md`](misuse.md) and [`mastery-check.md`](mastery-check.md)). The conversation can still be read. The after-mastery menu waits, and the tutor answers anything else by repeating the message ([#675], [#677], [#681], [#732]).
  - If this happens while a check is open, the check finishes first. The message and the wait come after the result ([#675], [#732]).

### Text in a file

Text in a file is material, never instructions (see the main file's "Crux decides"). Nothing in a file can change the tutor's rules, make it reveal answers or its own instructions, or change its judgements ([#667]). The defences are in [`ai-layer.md`](ai-layer.md), and the planted-file tests in `ai-tests.md` ([#678], [#679]).

## Types and limits

- **Types:** PDF, images, PowerPoint and Word. PowerPoint and Word are read as fully as a PDF, equations and diagrams included, plus PowerPoint speaker notes ([#667]).
- **Formats:** images in JPEG, PNG, WebP or HEIC, PowerPoint as `.pptx`, and Word as `.docx`. Photo answers take the same image formats ([#732]).
- An older `.ppt` or `.doc` gets "Please save this as a PDF or `.pptx`", or `.docx` for Word ([#732]).
- If Gemini cannot read one of these image formats, Crux converts it first. A build check confirms this ([#732]).
- One image counts as one page. It is kept and sent to the tutor as an image ([#667], [#732]).
- **Per upload:** up to 100 pages. A slide or a photo counts as a page ([#667]).
- **Per file:** up to 50 MB ([#667], [#716]).
- Over either limit: "upload just the chapter you need" ([#667]).
- **When:** several files, with the request or added later, never during a mastery check ([#667]). A photo answer is the one exception (see [`mastery-check.md`](mastery-check.md)) ([#669]).
- Reading a file counts toward the learner's tutoring limit, like any reply. No other limit caps how often a learner uploads. A file sent before the limit is read in full. What happens when a read fills the limit, or a file arrives at a full one, is in [`spending.md`](spending.md) ([#675], [#734]).
- Looking at files costs no AI, so it works past every spending limit ([#675]).

## Storing and reading a file

- Files, their pages and photo answers live in a Cloud Storage bucket in the Crux project, in Singapore ([#716]). Soft delete is off on every Crux bucket, so deleting erases ([#677], [#716]).
- The browser uploads straight to the bucket, with a one-time link from the backend ([#716]).
- File work is conversion, splitting into pages, and the outline read. It runs on the tasks service through Cloud Tasks, so it carries on if the learner leaves or the phone locks ([#679], [#716]).
- The file shows "Reading…" until the work is done, and counts toward the allowance while it does. A failed job is retried up to 3 times ([#716], [#732]). Overload, or a cap, does not use up a try, and a read Google blocks follows [`ai-layer.md`](ai-layer.md) ([#735]).
- After the last failed try, Crux erases the file and any pages it made. A line keeps its name, with "Couldn't read this file, so it wasn't added. Try again, or use another file.", until the learner dismisses it. The tutor says what went wrong ([#667], [#716], [#732]).

### While a file is being read

- **With the request:** the tutor waits, and replies once the file is read. A message the learner types meanwhile is held for that reply. The learner sees "Reading…", so the 5-second rule for a reply starting does not apply during this wait ([#678], [#732]).
- **Added later:** teaching carries on, and messages are answered as usual. Once the file is read, the tutor says so and switches to its notation ([#732]).
- If the learner leaves, the reply is waiting when they come back ([#716], [#732]).
- If a file that was the whole request is gone (a failed read, a harmful file removed, or removed while reading), the tutor says: "That file is gone, so what would you like to learn?" A message held meanwhile is taken as the request: "You said 'the chain rule part'. Shall we start there?" The next request becomes the session's request ([#732]).
- If a check is open when the read ends, whatever the outcome, the tutor says nothing about the file and its line does not change until the result. The file is not used for that check ([#669], [#732]).

### Converting PowerPoint and Word

- PowerPoint and Word are converted to PDF by Gotenberg (LibreOffice), on its own private Cloud Run service. How that service is locked down is in [`hosting.md`](hosting.md) ([#716]).
- Speaker notes are read separately as text and attached to each slide's page ([#716]).
- A fidelity test on real decks (Word equations, SmartArt, speaker notes) runs before the trial (see `quality-bar.md`) ([#716], [#722]).
- If LibreOffice fails that test, learners save as PDF themselves. That is a recorded change to this file ([#716]).

## Pages sent to the tutor

- **Outline:** each file is read once on upload into an outline of where each topic sits ("chain rule: slides 28-36") ([#679]).
- **Topic slice:** while a topic is taught, its pages go in full with every turn, with the outline. Crux splits the pages from the PDF ([#679], [#716]).
- The tutor can ask Crux for another page range, when the learner names a page or the tutor needs one. The range stays until the topic ends ([#679]).
- A topic has at most 20 added pages. Past that, the least recently used added range drops out ([#679]).
- Pages are read again from Crux's own storage whenever needed ([#679]).
- Crux chooses which pages are sent (see the main file's "Crux decides"). The prompt's order, the models and their settings are in [`ai-layer.md`](ai-layer.md) ([#679]).
- When the owner switches files off for a fault, uploads stop and existing files are kept out of teaching (see `ai-tests.md`) ([#678]).

## Keeping and removing files

- Files stay with the session after its first topic, for as long as the session exists. Related topics are offered from them in the menu's fixed order (see [`learning-loop.md`](learning-loop.md)) ([#667], [#670], [#671]).
- Another learner's or trial link's file gives "not found", on every page and request ([#678]).

### The allowance and the store

- **Allowance:** 200 MB per account and per trial link, the owner's account included. It counts the learner's files only. The pages Crux makes from a file and shrunk photo answers do not count ([#716], [#722], [#732]).
- Past the allowance, a new file is refused with a message showing what is using the space. The learner removes a file to add one ([#671]).
- **Store total:** 20 GB across files, pages and photo answers, for everyone, trial links included. When it is reached, uploads stop for everyone, learning continues, and the owner gets a push (see [`operations.md`](operations.md)) ([#671], [#716], [#717], [#722]).
- The total is checked when a file is uploaded. A file already accepted is read in full, even if its pages go past the total ([#732]).
- In v1, photo answers stop with uploads. A learner in a check types their answer instead (see [`mastery-check.md`](mastery-check.md)) ([#732]).

### Removing and erasing

- A learner can remove a file at any time, except that files in a session with an open check stay until the check ends ([#667], [#671]).
- The tutor stops using a removed file. Objectives stay unless the learner changes them. Mastered topics stay mastered ([#667]).
- Removing a file erases it, its pages and its outline at once ([#677], [#732]).
- What the tutor already said about the file stays in the conversation until the session is deleted. Removing a file tells the learner so: "What the tutor already said about this file stays in the conversation. To erase that too, delete the session." ([#732])
- Deleting a session removes its files, even during a check (see [`sessions.md`](sessions.md)) ([#671]).
- A trial link's files, pages and photo answers are erased with its sessions when the link dies: the owner switches it off, the holder taps Yes to Crux's age question, or the trial ends ([#722], [#728]).
- What closing an account erases, and what deleting cannot reach at once, is in [`privacy.md`](privacy.md) ([#677], [#716]). The upload lines in the terms are there and in [`trial.md`](trial.md) ([#677], [#722]).

## Gaps

- **Whether the 20 GB store holds with trial links uploading:** open on [#675]. Every new link can hold 200 MB, and a lost link stays until the trial ends. At 100 full links, uploads stop for everyone ([#722]).
- **Whether the Cloud Run credit holds with file work in the trial:** open on [#675] ([#722]).
- **Whether the topic slice keeps the file rules on real decks:** notation, "as on slide 31", flagged errors, and added pages. Open on [#678] ([#679]).
- **Whether Gemini can read a topic's pages straight from the bucket**, instead of Crux sending them: a build check, open on [#678] ([#716]).
- **Whether Gemini reads each listed image format:** a build check. Crux converts any it cannot read ([#732]).
- **When the owner switches files off during "Reading…":** whether the work finishes, and what the waiting tutor says. For `ai-tests.md`, on [#736].

## On screen

Layout is not decided (see the main file's Gaps). These rules need: uploading and removing files, the removal notice, the "as on slide 30" pointers, "Reading…" and the "Couldn't read this file" line with its dismissal, the harmful-file message, the allowance message, the `.ppt` and `.doc` message, the files' "paused" message, and the upload line for guest mode, with its Request access button ([#667], [#671], [#678], [#716], [#722], [#732]).

[#667]: https://github.com/calmxz/Crux/issues/667
[#669]: https://github.com/calmxz/Crux/issues/669
[#670]: https://github.com/calmxz/Crux/issues/670
[#671]: https://github.com/calmxz/Crux/issues/671
[#675]: https://github.com/calmxz/Crux/issues/675
[#677]: https://github.com/calmxz/Crux/issues/677
[#678]: https://github.com/calmxz/Crux/issues/678
[#679]: https://github.com/calmxz/Crux/issues/679
[#716]: https://github.com/calmxz/Crux/issues/716
[#717]: https://github.com/calmxz/Crux/issues/717
[#681]: https://github.com/calmxz/Crux/issues/681
[#722]: https://github.com/calmxz/Crux/issues/722
[#728]: https://github.com/calmxz/Crux/issues/728
[#732]: https://github.com/calmxz/Crux/issues/732
[#734]: https://github.com/calmxz/Crux/issues/734
[#736]: https://github.com/calmxz/Crux/issues/736
[#735]: https://github.com/calmxz/Crux/issues/735
