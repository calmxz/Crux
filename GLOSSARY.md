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
What the learner types or uploads to start a session, in their own words. It can be broader than a topic; the session keeps it as what the learner came for.
_Avoid_: query, prompt

**Session**:
One line of learning that starts from a learner's request and holds its topic and the related topics that follow. A learner can have several sessions and resume any of them. The tutor suggests a new one for something unrelated, or for a switch away from a topic not yet mastered.
_Avoid_: chat, thread, conversation

**Topic**:
The bounded thing a learner sets out to master: small enough to be set out as 3 to 5 learning objectives and reached in a sitting or two, and something the learner can show they know in writing. A request too broad to master (such as "calculus" or "derivatives") is narrowed into a topic (such as "the chain rule") before teaching starts; one too narrow (a single problem) is widened to the topic that contains it.
_Avoid_: course

**Learning objective**:
One of the 3 to 5 things a topic is set out as, each something the learner should be able to do. The tutor sets them out; the learner sees them and can ask for changes.
_Avoid_: goal, outcome, skill

**Diagnostic**:
A short set of questions, run only when the learner says they already know some of a topic, to find which learning objectives they can skip. It never earns mastery.
_Avoid_: placement test, pre-test

**Mastery**:
The verdict that a learner has proven they know something, earned only by passing a mastery check.

**Mastery check**:
The short test the tutor offers when it judges the learner ready. Passing it is the only way to earn mastery.
_Avoid_: quiz, exam, test

**Related topic**:
A topic next to one the learner has just mastered, offered as what to learn next. It continues in the same session.
