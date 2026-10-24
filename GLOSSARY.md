# Crux

Crux is an adaptive tutor: it teaches a learner a topic until they prove they have mastered it, then lets them stop or move on to a related topic.

## Language

**Learner**:
The person learning with Crux.
_Avoid_: user, student

**Tutor**:
The AI that teaches the learner, tracks which learning objectives they have shown, and offers a mastery check once every one not dropped is shown.
_Avoid_: agent, bot, assistant

**Preference**:
How the learner likes to be taught, such as with real-world examples, remembered across sessions only when the learner agrees.
_Avoid_: profile

**Request**:
What the learner brings to start a session: their own words, files, or both. It can be broader than a topic; the session keeps it as what the learner came for.
_Avoid_: query, prompt

**File**:
A PDF, image, PowerPoint or Word document the learner gives the tutor, with their request or later in a session: course material, a problem sheet, a past exam paper, a syllabus. The session keeps it, and the tutor teaches from it. A photo of the learner's own working, given as an answer in a mastery check, is not a file.
_Avoid_: lesson file, document, attachment, upload

**Session**:
One line of learning that starts from a learner's request and holds its topic, any prerequisite topics, and the related topics that follow. A learner can have several sessions and resume any of them. The tutor suggests a new one for something unrelated, or for a switch away from a topic not yet mastered.
_Avoid_: chat, thread, conversation

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
A learning objective the learner has got right in a mastery check. Unlike shown, it counts toward mastery, and it stays passed.
_Avoid_: mastered (for an objective)

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
A topic next to one the learner has just mastered, offered as what to learn next. It continues in the same session.
