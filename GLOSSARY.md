# Crux

Crux is an adaptive tutor: it teaches a learner a topic until they prove they have mastered it, then lets them stop or move on to a related topic.

## Language

**Learner**:
The person learning with Crux.
_Avoid_: user, student

**Tutor**:
The AI that teaches the learner, tracks how well they are doing, and offers a mastery check when it judges them ready.
_Avoid_: agent, bot, assistant

**Session**:
One line of learning that starts from a learner's request and holds its topic and the related topics that follow. A learner can have several sessions and resume any of them; something unrelated starts a new one.
_Avoid_: chat, thread, conversation

**Topic**:
The bounded thing a learner sets out to master. A request too broad to master (such as "calculus") is narrowed into a topic before teaching starts.
_Avoid_: course

**Learning objective**:
One of the few things a topic is set out as, each something the learner should be able to do. The learner sees them.
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
