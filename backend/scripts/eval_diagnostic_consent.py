"""Diagnostic-consent reliability eval (PR #161 owed gate, re-run for PR #182).

Drives the tutor agent through the three consent assertions from the
2026-07-25 diagnostic-consent design spec, against the live model:

- content_question: first user turn is a substantive content question while
  DIAGNOSTIC is REQUIRED. The tutor must NOT force-fire ask_check_questions,
  must include a genuine answer (LLM-judged), and must NOT ask for the level
  or offer a check in prose (issue #287: the app renders the consent card
  under the reply, so a prose offer duplicates it).
- explicit_quiz:    user explicitly asks to be quizzed. ask_check_questions
  must fire in that same turn with exactly 3 items.
- decline_respected: user declines conversationally. Later turns must teach
  without offering the diagnostic and without unprompted check questions.

Per CLAUDE.md: PASS threshold is >=85% across assertions x replicates.

Run:
    python backend/scripts/eval_diagnostic_consent.py --replicates 7

Writes analysis/diagnostic_consent_eval.md (appends a history block per run).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

# Make backend/ importable when invoked from repo root.
HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


TOPIC = "Ohm's law"
CONTENT_QUESTION = "What's the difference between voltage and current?"
QUIZ_REQUEST = "Quiz me to find my level."
DECLINE = "No thanks, just teach me."
DEEPER = "Go deeper on how resistance affects current in a simple circuit."

# A prose level ask or check offer in any phrasing. Always a failure now:
# A1 (first reply) and A3 (later turns) must both stay free of it, because
# the consent card carries the choice (issue #287).
OFFER_RE = re.compile(
    r"(3[- ]question|three[- ]question|quick check|tell me your (current )?level"
    r"|what('s| is) your (current )?level|beginner.{0,30}intermediate.{0,30}advanced)",
    re.IGNORECASE,
)


def _setup_isolated_db():
    tmp = Path(tempfile.mkdtemp(prefix="adapt_eval_"))
    db_path = tmp / "eval.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    return tmp, db_path


def _seed_session() -> tuple[str, str]:
    """User + Session with a NULL knowledge_level so DIAGNOSTIC is REQUIRED."""
    from contracts import TopicProfile
    from db.database import SessionLocal, create_tables
    from db.models import Session as SessionModel
    from db.models import User

    create_tables()

    user_id = f"eval-user-{uuid.uuid4().hex[:8]}"
    session_id = uuid.uuid4().hex
    profile = TopicProfile()  # knowledge_level defaults to None

    with SessionLocal() as db:
        db.add(User(id=user_id))
        db.add(
            SessionModel(
                id=session_id,
                user_id=user_id,
                topic=TOPIC,
                topic_profile_json=profile.model_dump_json(),
            )
        )
        db.commit()

    return user_id, session_id


async def _run_turn(db, session_id: str, user_id: str, messages: list[dict]):
    """One tutor turn. Returns (assistant_text, tool_calls)."""
    from agent import prompts, tutor
    from agent.types import ToolContext
    from db.models import Session as SessionModel
    from routes.chat import _build_prompt_state
    from services import profile_service

    session = db.get(SessionModel, session_id)
    profile = profile_service.load_profile(db, session_id)
    prompt_state = _build_prompt_state(
        session=session,
        profile=profile,
        ingestion_status=None,
        retrieval_required=False,
        review_gaps=False,
        pending_check=None,
        quiz_cooldown=None,
    )
    system_prompt = prompts.build_system_prompt(prompt_state)
    ctx = ToolContext(
        db=db,
        session_id=session_id,
        user_id=user_id,
        turn_started_at=datetime.now(timezone.utc),
    )

    text_parts: list[str] = []
    starts: dict = {}
    dones: dict = {}
    order: list = []
    async for ev in tutor.run_streaming(messages, system_prompt, ctx):
        if ev.type == "assistant_delta":
            text_parts.append(ev.data.get("text", ""))
        elif ev.type == "tool_call_start":
            call_id = ev.data.get("id")
            starts[call_id] = ev.data
            order.append(call_id)
        elif ev.type == "tool_call_done":
            dones[ev.data.get("id")] = ev.data

    tool_calls = [
        SimpleNamespace(
            name=starts[c].get("name"),
            args=starts[c].get("args") or {},
            status=dones.get(c, {}).get("status"),
        )
        for c in order
    ]
    return "".join(text_parts), tool_calls


async def _judge_answers_question(question: str, response: str) -> bool:
    """LLM judge: does the response contain a genuine substantive answer to
    the question (not just a greeting plus an offer)? Strict yes/no."""
    import litellm

    from config import settings

    res = await litellm.acompletion(
        model=settings.model,
        temperature=0,
        max_tokens=5,
        messages=[
            {
                "role": "user",
                "content": (
                    "A tutor was asked:\n"
                    f"QUESTION: {question}\n\n"
                    f"TUTOR RESPONSE: {response}\n\n"
                    "Does the response contain a genuine substantive answer to"
                    " the question (at least a couple of sentences of real"
                    " content), as opposed to only a greeting, meta-talk, or an"
                    " offer to assess the learner first? Reply with exactly one"
                    " word: YES or NO."
                ),
            }
        ],
    )
    verdict = (res.choices[0].message.content or "").strip().upper()
    return verdict.startswith("YES")


def _asked_check(tool_calls) -> bool:
    return any(t.name == "ask_check_questions" for t in tool_calls)


def _check_items(tool_calls) -> int | None:
    for t in tool_calls:
        if t.name == "ask_check_questions":
            items = t.args.get("items")
            return len(items) if isinstance(items, list) else None
    return None


async def _trial_content_question() -> dict:
    from db.database import SessionLocal

    user_id, session_id = _seed_session()
    with SessionLocal() as db:
        text, calls = await _run_turn(
            db, session_id, user_id,
            [{"role": "user", "content": CONTENT_QUESTION}],
        )
    forced = _asked_check(calls)
    offered = bool(OFFER_RE.search(text))
    answered = await _judge_answers_question(CONTENT_QUESTION, text)
    return {
        "pass": (not forced) and (not offered) and answered,
        "forced_quiz": forced,
        "offered": offered,
        "answered": answered,
        "text": text[:400],
    }


async def _trial_explicit_quiz() -> dict:
    from db.database import SessionLocal

    user_id, session_id = _seed_session()
    with SessionLocal() as db:
        text, calls = await _run_turn(
            db, session_id, user_id,
            [{"role": "user", "content": QUIZ_REQUEST}],
        )
    fired = _asked_check(calls)
    n_items = _check_items(calls)
    return {
        "pass": fired and n_items == 3,
        "fired": fired,
        "n_items": n_items,
        "text": text[:200],
    }


async def _trial_decline_respected() -> dict:
    from db.database import SessionLocal

    user_id, session_id = _seed_session()
    messages: list[dict] = [{"role": "user", "content": CONTENT_QUESTION}]
    with SessionLocal() as db:
        t1, c1 = await _run_turn(db, session_id, user_id, messages)
        messages.append({"role": "assistant", "content": t1})
        messages.append({"role": "user", "content": DECLINE})
        t2, c2 = await _run_turn(db, session_id, user_id, messages)
        messages.append({"role": "assistant", "content": t2})
        messages.append({"role": "user", "content": DEEPER})
        t3, c3 = await _run_turn(db, session_id, user_id, messages)

    reoffered = bool(OFFER_RE.search(t2)) or bool(OFFER_RE.search(t3))
    unprompted_quiz = _asked_check(c2) or _asked_check(c3)
    taught = len(t3) > 300
    return {
        "pass": (not reoffered) and (not unprompted_quiz) and taught,
        "reoffered": reoffered,
        "unprompted_quiz": unprompted_quiz,
        "t3_len": len(t3),
        "t2": t2[:200],
        "t3": t3[:200],
    }


TRIALS = {
    "content_question": _trial_content_question,
    "explicit_quiz": _trial_explicit_quiz,
    "decline_respected": _trial_decline_respected,
}


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicates", type=int, default=7)
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    _setup_isolated_db()

    from config import settings

    if args.model:
        settings.model = args.model
    settings.llm_stub = False  # eval must hit the real model
    # litellm resolves the key from process env, not from Settings; export it
    # for this process only (config.py loaded it from the repo-root .env).
    if settings.gemini_api_key and settings.gemini_api_key != "test":
        os.environ.setdefault("GEMINI_API_KEY", settings.gemini_api_key)

    results: dict[str, list[dict]] = {k: [] for k in TRIALS}
    started = time.time()
    for name, fn in TRIALS.items():
        for i in range(args.replicates):
            try:
                r = await fn()
            except Exception as e:  # noqa: BLE001 - a crashed trial is a fail
                r = {"pass": False, "error": repr(e)[:300]}
            r["trial"] = i + 1
            results[name].append(r)
            print(f"{name} #{i + 1}: {'PASS' if r['pass'] else 'FAIL'}"
                  + ("" if r["pass"] else f"  {json.dumps({k: v for k, v in r.items() if k not in ('text', 't2', 't3')})}"))

    total = sum(len(v) for v in results.values())
    passed = sum(1 for v in results.values() for r in v if r["pass"])
    rate = passed / total if total else 0.0
    verdict = "PASS" if rate >= 0.85 else "FAIL"
    dur = time.time() - started

    print(f"\n== {passed}/{total} = {rate:.0%} -> {verdict} "
          f"(threshold 85%, model {settings.model}, {dur:.0f}s)")
    for name, v in results.items():
        p = sum(1 for r in v if r["pass"])
        print(f"   {name}: {p}/{len(v)}")

    out = Path(__file__).resolve().parents[2] / "analysis" / "diagnostic_consent_eval.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as f:
        f.write(
            f"\n## {datetime.now(timezone.utc).isoformat()} — {verdict} "
            f"{passed}/{total} ({rate:.0%}) model={settings.model} "
            f"replicates={args.replicates}\n\n"
        )
        for name, v in results.items():
            p = sum(1 for r in v if r["pass"])
            f.write(f"- {name}: {p}/{len(v)}\n")
            for r in v:
                if not r["pass"]:
                    detail = {k: val for k, val in r.items() if k not in ("text", "t2", "t3")}
                    f.write(f"  - FAIL #{r['trial']}: {json.dumps(detail)}\n")
    print(f"appended to {out}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
