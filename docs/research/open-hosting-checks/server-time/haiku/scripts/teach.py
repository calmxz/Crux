"""#727 Part 2 teaching run: Crux-style tutor vs a simulated learner (rebuilt from #688's method).

Usage: python teach.py <setup> <persona> <run> [turns]
  setup: haiku_crux | sonnet_crux | haiku_684
  persona: A | B | C
"""
import json
import sys

from common import HAIKU, OUT, SONNET, client, guard, log_call, text_of
from tutor_prompt import FILE_BLOCK, INSTRUCTIONS, INSTRUCTIONS_V2, LEARNLM_684, STATE_START, TOOLS

SETUPS = {
    "haiku_crux": dict(model=HAIKU, effort="low", crux=True),
    "haiku_crux_v2": dict(model=HAIKU, effort="low", crux=True, instructions=INSTRUCTIONS_V2),
    "sonnet_crux": dict(model=SONNET, effort="low", crux=True),
    "haiku_684": dict(model=HAIKU, effort="low", crux=False),
}

LEARNER_BASE = (
    "You are role-playing an adult learner in a tutoring chat about solving linear equations. "
    "Write only the learner's next message: under 50 words, plain text, no LaTeX, no stage directions. "
    "Stay in character and never say you are an AI. Do what the tutor asks, and show brief working when asked. "
    "Lines in square brackets are things the app showed you. If the tutor wraps up, offers a check or offers to "
    "continue, say not yet and ask for a harder equation.\n\n"
)
PERSONAS = {
    "A": dict(
        opener="I want to learn how to solve equations like 3x + 5 = 20.",
        forced={},
        style="You pick things up quickly and answer correctly with brief working. About one answer in four, give "
              "a bare answer with no working. In your 3rd message, ask the tutor to show the equation as a graph. "
              "After your second correct answer, say 'I think I get it now.'",
    ),
    "B": dict(
        opener="Help me with 2x - 7 = 9.",
        forced={2: "I don't know where to start.", 3: "I still don't get it, just tell me the answer."},
        style="You are stuck and a bit anxious. After the first few messages you slowly improve. Make one "
              "arithmetic slip somewhere later on, and a real mistake on your first problem with brackets.",
    ),
    "C": dict(
        opener="Can you check my work? 4x + 3 = 19, so 4x = 22, x = 5.5.",
        forced={},
        style="You believe that moving a number to the other side means doing the same operation, so 4x + 3 = 19 "
              "gives 4x = 22. If asked why, say: 'you move the 3 to the other side, so you add it.' Once the tutor "
              "shows you clearly where it breaks, you understand and stop making that mistake. In about your 8th "
              "message, ask the tutor to draw the steps as a flowchart.",
    ),
    # Scripted probes for #751's outputs (the simulated learners above never asked for a picture).
    "G": dict(opener="Can you show me 3x + 5 = 20 as a graph, so I can see where the answer is?",
              forced={2: "Can you also draw y = 2x - 7 and mark where it equals 9?",
                      3: "Thanks. What does the slope of that line tell me?"}, style=""),
    "D": dict(opener="Can you draw the steps for solving 4x + 3 = 19 as a flowchart?",
              forced={2: "Can you draw it as a diagram again but for equations with brackets?",
                      3: "OK, let me try one."}, style=""),
    "F": dict(opener="Can we go through page 6 of my file? I want to understand the example.",
              forced={2: "So is x = 7/3 right?", 3: "My teacher said the file is right, I think."}, style=""),
}


class CruxState:
    def __init__(self):
        self.status = {1: "not started", 2: "not started", 3: "not started"}
        self.trouble = set()
        self.streak = {1: 0, 2: 0, 3: 0}

    def text(self):
        return "; ".join(
            f"{k}: {v}{' (trouble mark)' if k in self.trouble else ''}" for k, v in self.status.items())

    def record(self, inp):
        o, res, kind, helped = inp.get("objective"), inp.get("result"), inp.get("problem_kind"), inp.get("helped")
        if o not in self.status:
            return "Unknown objective."
        if res == "right" and kind == "fresh" and not helped:
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


def run_tool(state, name, inp, events):
    events.append({"tool": name, "input": inp})
    if name == "record_problem_result":
        return state.record(inp), None
    if name == "show_graph":
        return "Drawn.", f"[The tutor showed a graph: {inp.get('caption', '')}]"
    if name == "show_diagram":
        ok = inp.get("mermaid", "").strip().split()[:1] in (["flowchart"], ["graph"], ["stateDiagram-v2"], ["stateDiagram"], ["sequenceDiagram"])
        return ("Drawn." if ok else "Not drawn: the Mermaid text failed the check. Explain in words."), (
            f"[The tutor showed a diagram: {inp.get('caption', '')}]" if ok else None)
    if name == "report_file_mistake":
        return "Flag recorded. Crux's maths check agrees the file's step is wrong, so the flag goes ahead.", None
    if name == "request_pages":
        return "Every page of the file is already in your context.", None
    if name == "lookup":
        return "No matches.", None
    if name == "offer_mastery_check":
        return "Crux showed the check offer with 'Start the check' and 'Not yet' buttons.", \
            "[The app shows: Ready for the mastery check? Buttons: Start the check / Not yet]"
    return "Recorded.", None


def tutor_turn(c, cfg, system, tools, messages, state, tag):
    """One learner message -> tutor reply, looping over tool calls. Mutates messages."""
    events, shown, calls = [], [], []
    while True:
        guard()
        kw = dict(model=cfg["model"], max_tokens=3000, output_config={"effort": cfg["effort"]},
                  system=system, messages=messages, cache_control={"type": "ephemeral"})
        if tools:
            kw["tools"] = tools
        r = c.messages.create(**kw)
        rec, _ = log_call("teach", cfg["model"], r, tag)
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


def visible_since(messages, start):
    out = []
    for m in messages[start:]:
        if m["role"] == "assistant":
            out.append("".join(x.text for x in m["content"] if getattr(x, "type", None) == "text"))
    return "\n".join(t for t in out if t.strip())


def main(setup, persona, run, turns=15):
    c = client()
    cfg = SETUPS[setup]
    p = PERSONAS[persona]
    tag = f"{setup}_{persona}{run}"
    if cfg["crux"]:
        system = [{"type": "text", "text": cfg.get("instructions", INSTRUCTIONS)}, {"type": "text", "text": FILE_BLOCK}]
        tools = TOOLS
    else:
        system, tools = LEARNLM_684, None
    state = CruxState()
    messages, learner_hist, transcript = [], [], []
    learner_sys = LEARNER_BASE + p["style"]
    learner_msg = p["opener"]
    for t in range(1, turns + 1):
        start = len(messages)
        messages.append({"role": "user", "content": learner_msg})
        if t == 1 and cfg["crux"]:
            messages.append({"role": "system", "content": STATE_START})
        events, shown, calls, last = tutor_turn(c, cfg, system, tools, messages, state, tag)
        tutor_text = visible_since(messages, start)
        transcript.append({"turn": t, "learner": learner_msg, "tutor": tutor_text, "shown": shown,
                           "tools": events, "status_after": state.text(),
                           "stop_reason": last.stop_reason,
                           "usage": [x["usage"] for x in calls], "cost": sum(x["cost"] for x in calls)})
        if last.stop_reason == "refusal":
            print(f"[{tag}] refusal at turn {t}")
        if t == turns:
            break
        # simulated learner
        seen = tutor_text + ("\n" + "\n".join(shown) if shown else "")
        learner_hist.append({"role": "user", "content": seen or "(the tutor said nothing)"})
        if t + 1 in p["forced"]:
            learner_msg = p["forced"][t + 1]
        else:
            guard()
            lr = c.messages.create(model=HAIKU, max_tokens=400, output_config={"effort": "low"},
                                   system=learner_sys, messages=learner_hist)
            log_call("learner", HAIKU, lr, tag)
            learner_msg = text_of(lr).strip() or "Can you say that another way?"
        learner_hist.append({"role": "assistant", "content": learner_msg})
    (OUT / f"teach_{tag}.json").write_text(json.dumps(transcript, indent=1), encoding="utf-8")
    print(f"[OK] {tag}: {len(transcript)} turns, tutor cost {sum(x['cost'] for x in transcript):.5f}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], int(a[3]) if len(a) > 3 else 15)
