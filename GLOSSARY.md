# Crux

Crux is an adaptive tutor. It teaches a learner a topic until they prove they have mastered it. Then the learner can stop or move on to a related topic.

## Language

**Learner**:
The person learning with Crux.
_Avoid_: user, student

**Account**:
What a learner signs up for and signs in to, linked to one email address. It holds their sessions and their record. A learner can close their account, and it is erased a week later unless they sign back in and choose to keep it. An account with no visit for 12 months is closed after two warnings.
_Avoid_: profile, user

**Guest**:
Someone who uses Crux without an account, before Crux opens. A guest uses either the public link, for a sample topic or a short run on their own topic, or a trial link. Crux keeps nothing about who they are.
_Avoid_: visitor, anonymous user

**Trial link**:
The private link that Crux emails to someone when the owner approves their request to join the trial before Crux opens. It gives the whole learning loop, by typing only (no files or photo answers), within a learner's tutoring limit. Crux keeps the sessions under the link until the trial ends or the owner switches the link off.
_Avoid_: invite, code, password

**Tutor**:
The AI that teaches the learner and tracks which learning objectives the learner has shown. When the learner has shown every learning objective they have not dropped, the tutor offers a mastery check.
_Avoid_: agent, bot, assistant

**Owner**:
The person who runs Crux, shares it, and decides whether a paid launch comes next. Only the owner sees how many learners reached each step and what learners said in feedback.
_Avoid_: admin

**Budget**:
The most money Crux can spend on tutoring in a month, including tutoring for guests and for trial links. Each day also has its own cap, a set part of the budget. The owner's own tutoring is not part of the budget. When the budget or the daily cap runs out, no learner is tutored until it resets. The one exception: a learner can finish a mastery check that has already started.
_Avoid_: quota

**Owner's share**:
The most money the owner's own tutoring can spend in a month. It is separate from the budget. When it runs out, only the owner's account stops, until the owner raises the share.

**Tutoring limit**:
The most tutoring one learner can use, measured by what it costs. There is a daily limit and a weekly limit, and whichever runs out first applies. When it runs out, the learner is not tutored until it resets. The one exception: they can finish a mastery check that has already started.
_Avoid_: allowance, quota, credits

**Preference**:
How the learner likes to be taught, such as with real-world examples. Crux remembers it across sessions only if the learner agrees.
_Avoid_: profile

**Request**:
What the learner gives to start a session: their own words, files, or both. A request can be broader than a topic. The session keeps the request to show what the learner came for.
_Avoid_: query, prompt

**File**:
A PDF, image, PowerPoint, or Word document that the learner gives the tutor, with their request or later in a session. Examples are course material, a problem sheet, a past exam paper, and a syllabus. The session keeps the file, within the learner's storage allowance, and the tutor teaches from it. A photo of the learner's handwritten working (the steps to their answer), given as an answer in a mastery check, is not a file.
_Avoid_: lesson file, document, attachment, upload

**Session**:
The learning that starts from one request. It holds the request's topic, any prerequisite topics, and the related topics that follow. A learner can have several sessions and go back to any of them. The tutor names each session, and the learner can rename or delete it.

The tutor suggests a new session when the learner asks for something unrelated, or wants to switch away from a topic not yet mastered. The learner can say no. Then the new topic stays in the same session: it comes after the current topic if that topic is mastered, or replaces it if not.
_Avoid_: chat, thread, conversation

**Study block**:
One period of learning without a break, during one visit, with no set length. A topic is small enough to finish in one or two study blocks.
_Avoid_: sitting, lesson, visit

**Topic**:
The specific thing a learner aims to master. It is small enough to split into learning objectives (usually 3 to 5) and to finish in one or two study blocks. The learner can show they know it in writing.

Before teaching starts, the tutor narrows a request that is too broad (such as "calculus" or "derivatives") to a topic (such as "the chain rule"). It widens a request that is too narrow (a single problem) to the topic that contains it.
_Avoid_: course

**Prerequisite topic**:
A topic the learner is missing, which the tutor finds while teaching another topic. The tutor pauses the other topic, teaches the prerequisite topic in the same session, and then goes back to the other topic.
_Avoid_: remedial topic

**Learning objective**:
One thing the learner should be able to do, as part of a topic. A topic usually has 3 to 5. It has fewer only if the learner wants nothing added, and either a file covers the topic only briefly or the learner has dropped some.

The tutor writes the learning objectives, using the learner's files when there are any. The learner sees them and can ask for changes. A dropped learning objective stays on the list, but it is not taught or checked unless it is added back.
_Avoid_: goal, outcome, skill

**Shown**:
A learning objective the learner has proven during teaching. To prove it, the learner solves a new problem with no help and shows the method. Shown objectives decide when the tutor offers the mastery check, but they never count toward mastery.
_Avoid_: done, learned, completed

**Passed**:
A learning objective the learner has answered correctly in a mastery check. Unlike a shown objective, a passed objective counts toward mastery. It stays passed in all of the learner's sessions. Only two things undo it: its session is deleted, or a re-mark after a marking fault finds the answer wrong.
_Avoid_: mastered (for an objective)

**Record**:
Every topic the learner has mastered and every learning objective they have passed, across all their sessions. The tutor uses it in every session, and the learner sees it as one list.
_Avoid_: profile, progress, history

**Slip**:
A careless mistake in a method the learner knows. The learner fixes it on their own once the tutor points to it. Unlike a misconception, it does not change the learning objective's status, even one already shown.
_Avoid_: typo, error

**Diagnostic**:
A short set of questions that finds which learning objectives the learner can skip. The tutor runs it only when the learner says they already know some of a topic. It never counts toward mastery.
_Avoid_: placement test, pre-test

**Twin**:
A problem the tutor writes to teach with. It is the same kind of problem as one the learner brought, but with different details. The tutor teaches on the twin, so it never solves the learner's own problem.
_Avoid_: look-alike, clone

**Mastery**:
The verdict that a learner has proven they know a topic. Every learning objective they have not dropped has passed a mastery check, in one check or across several. Mastery is yes or no, with no levels.

**Mastery check**:
The short written test that the tutor offers when the learner has shown every learning objective they have not dropped. It is closed book, with no help, and each answer is marked against its model answer. Passing it is the only way to earn mastery. After a fail, the next check covers only the learning objectives the learner missed.
_Avoid_: quiz, exam, test

**Model answer**:
The step-by-step answer that the tutor writes for a mastery check problem. It is checked before the learner sees the problem. The learner's answer is marked against it, and the learner sees the model answer in the result.
_Avoid_: answer key, solution

**Related topic**:
A topic the learner starts after mastering one, in the same session. It is either covered by their request or files, or builds directly on the topic just mastered. Each time the learner masters a topic, the tutor offers 2 or 3 related topics.
