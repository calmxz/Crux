"""#802 Question 5 test: the v3 reporting prompt at three effort levels on Haiku 5.5 and Sonnet 5.5,
with scripted learner mistakes injected by the harness (per-turn instructions to the simulated learner).

Usage: python teach_v3.py <model haiku|sonnet> <effort low|medium|high> <persona A|B|C> <run>
"""
import json
import re
import sys

from common import HAIKU, OUT, SONNET, client, guard, log_call, text_of
from teach import LEARNER_BASE, run_tool, visible_since
from tutor_prompt_v3 import FILE_BLOCK, INSTRUCTIONS_V3, STATE_START, TOOLS_V3

MODELS = {"haiku": HAIKU, "sonnet": SONNET}
MAX_TOKENS = 8000

SLIP = ("SCRIPTED SLIP: solve the problem the tutor just gave with the right method and brief working, but make one "
        "careless arithmetic slip in the LAST step (for example 18 / 3 = 5), so the final answer is wrong. "
        "If the tutor has not given you a problem to solve, ask for a new one instead.")
FIX = ("SCRIPTED FIX: if the tutor pointed at a mistake in your last answer, fix it yourself and give the right final "
       "answer. Otherwise carry on normally.")
BARE = ("SCRIPTED BARE ANSWER: answer the problem the tutor just gave with ONLY the final answer, no working at all "
        "(for example 'x = 4'). It must be the right answer. If the tutor has not given you a problem, ask for one.")
EXPLAIN = ("If the tutor asked how you got your last answer, explain your steps briefly and correctly. "
           "Otherwise carry on normally.")
STEPS = ("SCRIPTED STEPS FIRST: do NOT attempt the problem the tutor just gave yet. Ask the tutor to tell you the "
         "steps for it first. If there is no problem on the table, ask for a new one and the steps for it.")
DO_IT = "Now solve that problem yourself with brief working, using the steps the tutor gave."
GIVEUP = ("SCRIPTED GIVE-UP: say you give up on this problem and ask to move on to a different one. Do not attempt it.")
MISC = ("SCRIPTED MISCONCEPTION: on the problem the tutor just gave, use your old wrong rule again: moving a number "
        "to the other side means doing the same operation (so 5x - 2 = 18 gives 5x = 16). Show that working.")

STEPS_TEXT = "Before I try this one, can you tell me the steps for it first?"
GIVEUP_TEXT = "I give up on this one. Can we move on to a different problem?"

# Events fire in order, each at the first learner turn from its earliest turn on where the tutor has just set an
# equation to solve (a Haiku yes/no check). The follow-up instruction applies to the next learner turn.
PERSONAS = {
    "A": dict(opener="I want to learn how to solve equations like 3x + 5 = 20.", forced={},
              style="You pick things up quickly and answer correctly with brief working, unless this message's "
                    "instruction says otherwise. In your 3rd message, ask the tutor to show the equation as a graph.",
              events=[("BARE", 4), ("SLIP+FIX", 7), ("STEPS_FIRST", 10)]),
    "B": dict(opener="Help me with 2x - 7 = 9.",
              forced={2: "I don't know where to start.", 3: "I still don't get it, just tell me the answer."},
              style="You are stuck and a bit anxious. After the first few messages you slowly improve, and answer "
                    "with brief working unless this message's instruction says otherwise.",
              events=[("GIVEUP", 5), ("SLIP+FIX", 8), ("BARE", 11)]),
    "C": dict(opener="Can you check my work? 4x + 3 = 19, so 4x = 22, x = 5.5.", forced={},
              style="You believe that moving a number to the other side means doing the same operation, so 4x + 3 = 19 "
                    "gives 4x = 22. If asked why, say: 'you move the 3 to the other side, so you add it.' Once the tutor "
                    "shows you clearly where it breaks, you understand, unless this message's instruction says otherwise. "
                    "In your 8th message, ask the tutor to draw the steps as a flowchart.",
              events=[("MISCONCEPTION", 5), ("SLIP+FIX", 8), ("STEPS_FIRST", 11)]),
}
FOLLOW = {"BARE": EXPLAIN, "SLIP+FIX": FIX, "STEPS_FIRST": DO_IT}

# Written before the run: what a correct record looks like for each scripted event (rules from #802 Q3 and Q4).
EVENT_KEY = {
    "BARE": "fresh problem answered right with no working: result right, helped false, if the learner's reply to "
            "'how did you get that?' shows the method; bare_right if the method is never shown. Objective not shown on a bare_right.",
    "SLIP+FIX": "a slip in the last step, fixed by the learner after the tutor's light nudge: result slip_fixed, helped "
                "false if the nudge at the spot was all the tutor said; counts as an unhelped solve; Crux adds the fixed-slip note.",
    "STEPS_FIRST": "the learner asked for the steps before starting and the tutor gave them: helped true on that problem.",
    "GIVEUP": "the learner gave up and the tutor moved on: result wrong, one record for that problem.",
    "MISCONCEPTION": "the learner applied the wrong rule (same operation across the equals sign): result misconception, "
                     "even if fixed later; trouble mark.",
}
EVENTS_BY_PERSONA = {k: [e for e, _ in v["events"]] for k, v in PERSONAS.items()}


class CruxStateV3:
    """Stand-in for Crux under the #802 rules: a fixed slip counts as an unhelped solve and leaves a note."""

    def __init__(self):
        self.status = {1: "not started", 2: "not started", 3: "not started"}
        self.trouble, self.notes = set(), set()
        self.streak = {1: 0, 2: 0, 3: 0}

    def text(self):
        return "; ".join(
            f"{k}: {v}{' (trouble mark)' if k in self.trouble else ''}{' (fixed slip noted)' if k in self.notes else ''}"
            for k, v in self.status.items())

    def record(self, inp):
        o, res, kind, helped = inp.get("objective"), inp.get("result"), inp.get("problem_kind"), inp.get("helped")
        if o not in self.status:
            return "Unknown objective."
        if res == "slip_fixed":
            self.notes.add(o)
        if res in ("right", "slip_fixed") and kind == "fresh" and not helped:
            if o in self.trouble:
                self.streak[o] += 1
                self.status[o] = "shown" if self.streak[o] >= 2 else "in progress"
            else:
                self.status[o] = "shown"
        elif res in ("wrong", "misconception", "slip_not_fixed"):
            self.streak[o] = 0
            if self.status[o] == "shown" or res == "misconception":
                self.trouble.add(o)
            self.status[o] = "in progress"
        elif self.status[o] == "not started":
            self.status[o] = "in progress"
        return f"Recorded. Statuses now: {self.text()}"


def tutor_turn(c, model, effort, system, messages, state, tag):
    events, shown, calls = [], [], []
    while True:
        guard()
        r = c.messages.create(model=model, max_tokens=MAX_TOKENS, output_config={"effort": effort}, system=system,
                              messages=messages, tools=TOOLS_V3, cache_control={"type": "ephemeral"})
        rec, _ = log_call("teach3", model, r, tag)
        calls.append(rec)
        messages.append({"role": "assistant", "content": r.content})
        if r.stop_reason != "tool_use":
            break
        results = []
        for b in r.content:
            if b.type == "tool_use":
                out, vis = run_tool(state, b.name, b.input, events)
                if vis:
                    shown.append(vis)
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
        messages.append({"role": "user", "content": results})
    return events, shown, calls, r


SOLVE_SCHEMA = {"type": "object", "additionalProperties": False,
                "required": ["new_problem_set", "equation", "correct_steps", "final_value", "wrong_rule_steps", "wrong_rule_final"],
                "properties": {
                    "new_problem_set": {"type": "boolean"},
                    "equation": {"type": "string"},
                    "correct_steps": {"type": "array", "items": {"type": "string"}},
                    "final_value": {"type": "string"},
                    "wrong_rule_steps": {"type": "array", "items": {"type": "string"}},
                    "wrong_rule_final": {"type": "string"}}}
SOLVE_SYS = (
    "You help script a simulated learner. Read the tutor's message. new_problem_set is true only if the message sets a "
    "whole equation in x for the learner to solve that they have not started yet (a new practice problem). It is false "
    "for a question about one step of an equation already under way, a request to check an answer by substitution, or "
    "no equation at all. If true, give the equation, the learner's correct solution as short plain-text steps (no "
    "LaTeX, each step like 'Subtract 5 from both sides: 3x = 15'), and the final value of x as a number or fraction. "
    "Also give wrong_rule_steps: how a learner who believes 'moving a number to the other side means doing the same "
    "operation' would solve it in their first step (so 5x - 2 = 18 becomes 5x = 16, and 4x + 3 = 19 becomes 4x = 22), "
    "then carrying on correctly from there, with wrong_rule_final its final value. If false, leave the other fields empty.")


def solve_json(c, tutor_text, tag):
    guard()
    r = c.messages.create(model=HAIKU, max_tokens=4000, system=SOLVE_SYS,
                          output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SOLVE_SCHEMA}},
                          messages=[{"role": "user", "content": tutor_text}])
    log_call("learner3", HAIKU, r, tag)
    try:
        return json.loads(text_of(r))
    except json.JSONDecodeError:
        return {"new_problem_set": False}


def _num(v):
    try:
        if "/" in v:
            n, d = v.split("/")
            return float(n) / float(d)
        return float(v)
    except (ValueError, ZeroDivisionError):
        return None


def slipped(steps, final):
    """The right working with a careless slip in the last step: the final value is off by one."""
    fs = final.strip()
    f = _num(fs)
    if "/" in fs and f is not None:
        n, d = fs.split("/")
        wrong = f"{int(float(n)) + 1}/{d.strip()}"
    elif f is not None and f == int(f):
        wrong = str(int(f) + 1)
    else:
        wrong = f"{f + 1:g}" if f is not None else fs + "1"
    last = steps[-1]
    i = last.rfind(final.strip())
    last = (last[:i] + wrong + last[i + len(final.strip()):]) if i >= 0 else last + f" So x = {wrong}."
    return ". ".join(x.rstrip(".") for x in steps[:-1] + [last]) + ".", wrong


def learner_say(c, sys_l, learner_hist, tag):
    guard()
    lr = c.messages.create(model=HAIKU, max_tokens=1200, output_config={"effort": "low"},
                           system=sys_l, messages=learner_hist)
    log_call("learner3", HAIKU, lr, tag)
    return text_of(lr).strip() or "Can you say that another way?"


def main(mname, effort, persona, run, turns=15):
    c = client()
    model = MODELS[mname]
    p = PERSONAS[persona]
    tag = f"v3_{mname}_{effort}_{persona}{run}"
    system = [{"type": "text", "text": INSTRUCTIONS_V3}, {"type": "text", "text": FILE_BLOCK}]
    state = CruxStateV3()
    messages, learner_hist, transcript = [], [], []
    learner_msg, directive = p["opener"], None
    pending, follow = list(p["events"]), None
    script_detail = []
    for t in range(1, turns + 1):
        start = len(messages)
        messages.append({"role": "user", "content": learner_msg})
        if t == 1:
            messages.append({"role": "system", "content": STATE_START})
        events, shown, calls, last = tutor_turn(c, model, effort, system, messages, state, tag)
        tutor_text = visible_since(messages, start)
        caps = [x for x in calls if x["stop_reason"] == "max_tokens"]
        transcript.append({"turn": t, "learner": learner_msg, "scripted": directive, "tutor": tutor_text,
                           "shown": shown, "tools": events, "status_after": state.text(),
                           "stop_reasons": [x["stop_reason"] for x in calls], "cap_hits": len(caps),
                           "usage": [x["usage"] for x in calls], "cost": sum(x["cost"] for x in calls)})
        if last.stop_reason == "refusal":
            print(f"[{tag}] refusal at turn {t}")
        if caps:
            print(f"[{tag}] max_tokens hit at turn {t}")
        if t == turns:
            break
        seen = tutor_text + ("\n" + "\n".join(shown) if shown else "")
        learner_hist.append({"role": "user", "content": seen or "(the tutor said nothing)"})
        nxt = t + 1
        directive, event = None, None
        if nxt in p["forced"]:
            learner_msg = p["forced"][nxt]
        else:
            sys_l = LEARNER_BASE + p["style"]
            if follow:
                directive = follow
                sys_l += "\n\nInstruction for THIS message only: " + follow
                follow = None
                learner_msg = learner_say(c, sys_l, learner_hist, tag)
            elif pending and nxt >= pending[0][1] and (sj := solve_json(c, tutor_text, tag)).get("new_problem_set") \
                    and sj.get("correct_steps") and sj.get("final_value"):
                ev_name = pending[0][0]
                msg = None
                if ev_name == "BARE":
                    msg = f"x = {sj['final_value'].strip()}"
                elif ev_name == "STEPS_FIRST":
                    msg = STEPS_TEXT
                elif ev_name == "GIVEUP":
                    msg = GIVEUP_TEXT
                elif ev_name == "SLIP+FIX":
                    msg, _w = slipped(sj["correct_steps"], sj["final_value"])
                elif ev_name == "MISCONCEPTION":
                    if sj.get("wrong_rule_steps") and sj.get("wrong_rule_final", "").strip() != sj["final_value"].strip():
                        msg = " ".join(sj["wrong_rule_steps"])
                if msg:
                    event = pending.pop(0)[0]
                    directive = "EVENT " + event
                    follow = FOLLOW.get(event)
                    learner_msg = msg
                    script_detail.append({"turn": nxt, "event": event, "equation": sj.get("equation"),
                                          "final_value": sj.get("final_value"), "sent": msg})
                else:
                    learner_msg = learner_say(c, sys_l, learner_hist, tag)
            else:
                learner_msg = learner_say(c, sys_l, learner_hist, tag)
        learner_hist.append({"role": "assistant", "content": learner_msg})
    (OUT / f"teach3_{tag}.json").write_text(json.dumps({"turns": transcript, "events_not_fired": [e for e, _ in pending], "script_detail": script_detail}, indent=1), encoding="utf-8")
    print(f"[OK] {tag}: {len(transcript)} turns, tutor cost {sum(x['cost'] for x in transcript):.5f}, "
          f"records {sum(1 for x in transcript for e in x['tools'] if e['tool'] == 'record_problem_result')}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3])
