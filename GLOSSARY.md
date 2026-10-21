# Crux

Crux is an adaptive tutor: it teaches a learner a topic until they prove they have mastered it, then lets them stop or move on to a related topic.

## Language

**Learner**:
The person learning with Crux.
_Avoid_: user, student

**Tutor**:
The AI that teaches the learner, tracks how well they are doing, and offers a mastery check when it judges them ready.
_Avoid_: agent, bot, assistant

**Request**:
What the learner brings to start a session: their own words, files, or both. It can be broader than a topic; the session keeps it as what the learner came for.
_Avoid_: query, prompt

**File**:
A PDF, image, PowerPoint or Word document the learner gives the tutor, with their request or later in a session: course material, a problem sheet, a past exam paper, a syllabus. The session keeps it, and the tutor teaches from it.
_Avoid_: lesson file, document, attachment, upload

**Session**:
One line of learning that starts from a learner's request and holds its topic and the related topics that follow. A learner can have several sessions and resume any of them. The tutor suggests a new one for something unrelated, or for a switch away from a topic not yet mastered.
_Avoid_: chat, thread, conversation

**Topic**:
The bounded thing a learner sets out to master: small enough to be set out as (usually) 3 to 5 learning objectives and reached in a sitting or two, and something the learner can show they know in writing. A request too broad to master (such as "calculus" or "derivatives") is narrowed into a topic (such as "the chain rule") before teaching starts; one too narrow (a single problem) is widened to the topic that contains it.
_Avoid_: course

**Learning objective**:
One of the things a topic is set out as, each something the learner should be able to do: usually 3 to 5, and fewer only when a file covers the topic thinly and the learner wants nothing added. The tutor sets them out, from the learner's files when there are any; the learner sees them and can ask for changes.
_Avoid_: goal, outcome, skill

**Diagnostic**:
A short set of questions, run only when the learner says they already know some of a topic, to find which learning objectives they can skip. It never earns mastery.
_Avoid_: placement test, pre-test

**Twin**:
A problem the tutor writes in the same shape as one the learner brought, with different details, to teach on, so that it never works the learner's own problem.
_Avoid_: look-alike, clone

**Mastery**:
The verdict that a learner has proven they know something, earned only by passing a mastery check.

**Mastery check**:
The short test the tutor offers when it judges the learner ready. Passing it is the only way to earn mastery.
_Avoid_: quiz, exam, test

**Related topic**:
A topic next to one the learner has just mastered, offered as what to learn next. It continues in the same session.
