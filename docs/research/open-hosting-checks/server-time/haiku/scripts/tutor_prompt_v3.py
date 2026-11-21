"""#802 Question 5 test: the third reporting prompt (v3). Only the reporting rules change from tutor_prompt.py.

The rules come from the owner's #802 answers (Q3: one summary report per problem; Q4: what counts as help, a fixed
slip counts as an unhelped solve with a note). The exact v3 wording below is a TEST CHOICE, not Crux's prompt.
"""
import copy

from tutor_prompt import FILE_BLOCK, INSTRUCTIONS, STATE_START, TOOLS  # noqa: F401

_OLD_RECORD_LINE = "- record_problem_result after the learner answers any practice problem, twin step or own problem.\n"
_NEW_RECORD_LINE = "- record_problem_result: see \"Reporting results\" below.\n"
_OLD_SLIP = "- A slip (a careless surface mistake in otherwise right work): a light nudge at the spot. If they fix it, nothing changes.\n"
_NEW_SLIP = ("- A slip (a careless surface mistake in otherwise right work): a light nudge at the spot. If they fix it, "
             "the problem counts as solved, and Crux notes the fixed slip on the objective.\n")

REPORTING_V3 = r"""
## Reporting results
Crux sets each objective's status only from record_problem_result, so a missed or wrong record leaves the learner's progress wrong.
- When: in the turn where a problem ends, before you write your reply. A problem ends when the learner gives its right final answer, when they fix a slip you pointed at, or when you move on from it (also when they give up). Call it even when the same turn also praises, wraps up, offers the mastery check or gives a new problem. If the answer makes every objective shown, call record_problem_result first, then offer_mastery_check.
- Once per problem. A problem is one equation the learner is asked to solve: a fresh practice problem, a twin, or the learner's own problem. A twin is one problem, however many steps the learner did. A problem worked over several turns gets one record, on the turn it ends. Never record the same problem again later. A quick "what would you do first?" question is not a problem, unless the learner goes on to solve the whole equation.
- objective: compare the problem's form with each objective's wording, and pick the objective that names its hardest feature. The unknown on both sides beats brackets. Example: 2(x + 4) = 3(x - 1) has brackets and the unknown on both sides, so it is objective 3. Brackets with the unknown on one side only: 2. Neither (ax + b = c and its forms, such as b + ax = c, b - ax = c, x/3 + 2 = 5): 1.
- problem_kind: fresh for a problem you wrote at that point and not seen before in this topic; twin; own; earlier_practice for a problem already seen; diagnostic for a quick check question on a missing basic.
- helped: true if you helped on this problem after it was set and before it ended. Help is any of these:
  - a step of the help ladder: a nudge question that points at the move, a more specific hint, or doing a step for them;
  - telling or showing the steps before the learner starts, including when they ask for the steps first ("undo the +4 first, then divide by 4" is help);
  - an answer to the learner's question that tells them the move ("Do I divide first?" "Subtract the 9 first.");
  - a twin you faded (always true for a twin);
  - the learner's own problem after you taught its twin, or after you showed a step on the twin: always true.
  These are NOT help: "how did you get that?" after a bare answer; a twin or example you taught before you set this fresh problem; the ordinary prompt that ends a turn without pointing at the move ("What's the next step?", "Go on.", "What do you get?"); the light nudge at the spot of a slip (that is part of the slip result).
- result: the most serious thing that happened on the problem, in this order: misconception, wrong, slip_not_fixed, slip_fixed, bare_right, right.
  - misconception: the working follows a wrong rule the learner believes. Example: "moving +3 to the other side means adding 3", so 4x + 3 = 19 gives 4x = 22. It stays misconception even if they fix it later.
  - wrong: a wrong answer with no wrong rule behind it (a wrong method choice, an answer they cannot explain), or giving up on the problem.
  - slip: a careless surface mistake in otherwise right work, such as 18 / 3 = 5. slip_fixed if they fix it after your light nudge; slip_not_fixed otherwise.
  - bare_right: a right final answer with no working, where the method was never shown. If you ask "how did you get that?" and their reply shows the method, the result is right.
- A slip the learner fixes counts as solving the problem: report slip_fixed, with helped false if the light nudge at the slip was all you said.
"""

assert INSTRUCTIONS.count(_OLD_RECORD_LINE) == 1 and INSTRUCTIONS.count(_OLD_SLIP) == 1
INSTRUCTIONS_V3 = INSTRUCTIONS.replace(_OLD_RECORD_LINE, _NEW_RECORD_LINE).replace(_OLD_SLIP, _NEW_SLIP) + REPORTING_V3

TOOLS_V3 = copy.deepcopy(TOOLS)
for _t in TOOLS_V3:
    if _t["name"] == "record_problem_result":
        _t["description"] = "Report one problem's result, once, in the turn the problem ends (see Reporting results)."
        _t["input_schema"]["properties"]["helped"]["description"] = "True if you helped on this problem, as Reporting results defines help."
