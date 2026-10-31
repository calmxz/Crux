# Crux

Crux is an adaptive tutor: it teaches a learner a topic until they prove they have mastered it, then lets them stop or move on to a related topic.

## Language

**Learner**:
The person learning with Crux.
_Avoid_: user, student

**Account**:
What a learner signs up for and signs in to, known by one email address. It holds their sessions and their record. A learner can close it; it is erased a week later unless they sign back in and choose to keep it. One with no visit for 12 months is closed after two warnings.
_Avoid_: profile, user

**Guest**:
Someone using Crux without an account, before it opens: on the public link, a sample topic or a short run on their own topic, or with a trial link. Nothing about who they are is kept.
_Avoid_: visitor, anonymous user

**Trial link**:
The private link Crux emails when the owner approves someone's request for the trial before Crux opens: the whole learning loop, typed only, within a learner's tutoring limit, with sessions kept under the link until the trial ends or the owner switches it off.
_Avoid_: invite, code, password

**Tutor**:
The AI that teaches the learner, tracks which learning objectives they have shown, and offers a mastery check once every one not dropped is shown.
_Avoid_: agent, bot, assistant

**Owner**:
The person who runs Crux, shares it, and decides whether a paid launch follows. Only the owner sees how many learners reached each step and what they said in feedback.
_Avoid_: admin

**Budget**:
The money Crux may spend on tutoring in a month, guests and trial links included, of which no single day may spend more than a set part. The owner's own tutoring is not in it. When it, or the day's part, runs out, no learner is tutored until it resets, except to finish a mastery check already under way.
_Avoid_: quota

**Owner's share**:
The money the owner's own tutoring may spend in a month, kept apart from the budget. When it runs out, only the owner's account stops until the owner raises it.

**Tutoring limit**:
How much tutoring one learner may use, counted in what it costs: a day's worth and a week's worth, whichever runs out first. When it runs out, the learner is not tutored until it resets, except to finish a mastery check already under way.
_Avoid_: allowance, quota, credits

**Preference**:
How the learner likes to be taught, such as with real-world examples, remembered across sessions only when the learner agrees.
_Avoid_: profile

**Request**:
What the learner brings to start a session: their own words, files, or both. It can be broader than a topic; the session keeps it as what the learner came for.
_Avoid_: query, prompt

**File**:
A PDF, image, PowerPoint or Word document the learner gives the tutor, with their request or later in a session: course material, a problem sheet, a past exam paper, a syllabus. The session keeps it, within the learner's storage allowance, and the tutor teaches from it. A photo of the learner's own working, given as an answer in a mastery check, is not a file.
_Avoid_: lesson file, document, attachment, upload

**Session**:
One line of learning that starts from a learner's request and holds its topic, any prerequisite topics, and the related topics that follow. A learner can have several sessions and resume any of them; the tutor names each one, and the learner can rename or delete it. The tutor suggests a new one for something unrelated, or for a switch away from a topic not yet mastered. The learner can decline: the new topic then follows a mastered one in the session, or replaces an unfinished one.
_Avoid_: chat, thread, conversation

**Sitting**:
One continuous stretch of learning in one visit. A topic is reached in a sitting or two.
_Avoid_: lesson, visit

**Topic**:
The bounded thing a learner sets out to master: small enough to be set out as (usually) 3 to 5 learning objectives and reached in a sitting or two, and something the learner can show they know in writing. A request too broad to master (such as "calculus" or "derivatives") is narrowed into a topic (such as "the chain rule") before teaching starts; one too narrow (a single problem) is widened to the topic that contains it.
_Avoid_: course

**Prerequisite topic**:
A topic the tutor finds missing while teaching another. The other topic is paused while it is learned in the same session, and the tutor returns to it after.
_Avoid_: remedial topic

**Learning objective**:
One of the things a topic is set out as, each something the learner should be able to do: usually 3 to 5, and fewer only when a file covers the topic thinly, or the learner drops some, and the learner wants nothing added. The tutor sets them out, from the learner's files when there are any; the learner sees them and can ask for changes. A dropped one stays listed but is not taught or checked unless picked back up.
_Avoid_: goal, outcome, skill

**Shown**:
A learning objective the learner has proven during teaching by solving a fresh problem with no help, in a way that shows the method. It decides when the mastery check is offered, and never earns mastery.
_Avoid_: done, learned, completed

**Passed**:
A learning objective the learner has got right in a mastery check. Unlike shown, it counts toward mastery, and it stays passed, in every one of the learner's sessions, unless its session is deleted, or a re-mark after a marking fault finds the answer wrong.
_Avoid_: mastered (for an objective)

**Record**:
Every topic the learner has mastered and every learning objective they have passed, across all their sessions. Every session's tutor relies on it, and the learner sees it in one list.
_Avoid_: profile, progress, history

**Slip**:
A careless mistake in a method the learner knows, which they fix themselves once the tutor points at it. Unlike a misconception, it changes nothing.
_Avoid_: typo, error

**Diagnostic**:
A short set of questions, run only when the learner says they already know some of a topic, to find which learning objectives they can skip. It never earns mastery.
_Avoid_: placement test, pre-test

**Twin**:
A problem the tutor writes in the same shape as one the learner brought, with different details, to teach on, so that it never works the learner's own problem.
_Avoid_: look-alike, clone

**Mastery**:
The verdict that a learner has proven they know a topic: every learning objective not dropped has passed a mastery check, in one check or across several. It is yes or no, with no levels.

**Mastery check**:
The short written test the tutor offers once the learner has shown every learning objective not dropped: closed book, with no help, and each answer marked against its model answer. Passing it is the only way to earn mastery; after a fail, the next one covers only the objectives missed.
_Avoid_: quiz, exam, test

**Model answer**:
The worked answer the tutor writes for a mastery check problem, checked before the learner sees the problem. The learner's answer is marked against it, and the learner sees it in the result.
_Avoid_: answer key, solution

**Related topic**:
A topic the learner takes on after mastering one, in the same session: one their request or files cover, or one that builds directly on the topic just mastered. The tutor offers 2 or 3 at each mastery.
