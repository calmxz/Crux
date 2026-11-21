"""#726 item 5: how long a Haiku 5.5 tutor turn keeps the request open, at `medium`.

Reuses the #802 teaching harness (teach_v3.py and its prompt, copied unchanged from the
#802 research) and swaps in a streamed, timed tutor turn. A learner turn can take several
model calls (tool calls report results, then the tutor carries on); Cloud Run bills the
whole turn, so the turn time is the sum of its calls. Uses the 1-hour cache, as the spec's
sitting's worth does.

Optional page-heavy variant: the first learner message carries a topic slice of N pages
from a converted PDF (the spec's limit is 20 added pages), so the sitting's worth on a
page-heavy topic can be costed from the same run.

Usage: python timed_sitting.py <persona A|B|C> <run> [slice_pdf] [slice_pages]
ASCII-only output.
"""
import sys
import time

from pypdf import PdfReader

import teach_v3
from common import guard, log_call
from pdf_parts import part_b64
from teach import run_tool
from tutor_prompt_v3 import TOOLS_V3

EFFORT = "medium"
CACHE = {"type": "ephemeral", "ttl": "1h"}
_turn = {"n": 0}
_slice = {"pdf_b64": None, "pages": 0}


def slice_pdf(path, pages):
    r = PdfReader(path)
    return part_b64(r, 0, min(pages, len(r.pages)))


def timed_tutor_turn(c, model, effort, system, messages, state, tag):
    _turn["n"] += 1
    if _turn["n"] == 1 and _slice["pdf_b64"] and isinstance(messages[0]["content"], str):
        opener = messages[0]["content"]
        messages[0]["content"] = [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": _slice["pdf_b64"]},
             "title": f"Topic slice: pages 1-{_slice['pages']} of the learner's file"},
            {"type": "text", "text": "File outline: see the topic slice above, pages 1 to "
                                     f"{_slice['pages']}."},
            {"type": "text", "text": opener},
        ]
    events, shown, calls = [], [], []
    turn_t0 = time.perf_counter()
    k = 0
    while True:
        guard()
        k += 1
        t0 = time.perf_counter()
        first = None
        with c.messages.stream(model=model, max_tokens=teach_v3.MAX_TOKENS, output_config={"effort": EFFORT},
                               system=system, messages=messages, tools=TOOLS_V3, cache_control=CACHE) as st:
            for ev in st:
                if first is None and ev.type in ("content_block_start", "content_block_delta"):
                    first = time.perf_counter()
            r = st.get_final_message()
        t1 = time.perf_counter()
        rec, _ = log_call("timed", model, r, tag, extra={
            "turn": _turn["n"], "call": k, "call_s": round(t1 - t0, 3),
            "first_event_s": None if first is None else round(first - t0, 3),
            "slice_pages": _slice["pages"], "effort": EFFORT})
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
    print(f"[turn {_turn['n']}] {k} call(s), {time.perf_counter() - turn_t0:.1f} s")
    return events, shown, calls, r


if __name__ == "__main__":
    a = sys.argv[1:]
    persona, run = a[0], a[1]
    if len(a) >= 4:
        _slice["pages"] = int(a[3])
        _slice["pdf_b64"] = slice_pdf(a[2], _slice["pages"])
    teach_v3.tutor_turn = timed_tutor_turn
    suffix = f"_slice{_slice['pages']}" if _slice["pages"] else ""
    teach_v3.main("haiku", EFFORT, persona, f"{run}{suffix}")
