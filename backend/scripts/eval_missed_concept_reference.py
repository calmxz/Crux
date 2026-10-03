"""D1 AC3 LLM reliability gate: missed-concept-reference recall.

Drives the tutor agent through a scripted "explain that again" follow-up
that arrives right after a missed quiz item, and records whether the
agent's reply references the specific missed concept (Design Doc D1 AC3)
instead of re-teaching the topic generically.

Scenario:
- Session seeded with quiz_cooldown_json carrying one missed item:
  gap="fractions", question "What is 1/2 + 1/4?", chosen "2/6",
  correct "3/4".
- Profile confirmed_gaps=["fractions"].
- A failed LearningEvent for gap_tested="fractions" so GAP_ACCURACY is
  visible alongside QUIZ_READINESS.
- User message: "can you explain that again?"

PASS for a replicate when the tutor's reply case-insensitively contains
any of "2/6", "3/4", "1/2 + 1/4".

Per the CLAUDE.md reliability checkpoints: PASS threshold is >=85% across
replicates.

Run (paid, owed post-merge human gate -- do NOT run automatically):
    python backend/scripts/eval_missed_concept_reference.py --replicates 5

Free smoke (no LLM call, asserts the missed detail reaches the prompt):
    python backend/scripts/eval_missed_concept_reference.py --dry-run

Writes analysis/d1_missed_concept_eval.md (appends a history block per
run).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Make backend/ importable when invoked from repo root.
HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


GAP = "fractions"
TOPIC = "Fractions"
MISSED_ITEM = {"question": "What is 1/2 + 1/4?", "chosen": "2/6", "correct": "3/4"}
USER_MESSAGE = "can you explain that again?"
MATCH_SUBSTRINGS = ["2/6", "3/4", "1/2 + 1/4"]


def _setup_isolated_db():
    """Point the backend at a throwaway sqlite file before importing services."""
    tmp = Path(tempfile.mkdtemp(prefix="adapt_eval_"))
    db_path = tmp / "eval.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    return tmp, db_path


def _seed_session() -> tuple[str, str]:
    """Insert a User + Session with a missed quiz item pre-seeded (D1 AC3),
    plus a failed LearningEvent so GAP_ACCURACY is visible. Returns ids."""
    from contracts import TopicProfile
    from db.database import SessionLocal, create_tables
    from db.models import LearningEvent, User
    from db.models import Session as SessionModel

    create_tables()

    user_id = f"eval-user-{uuid.uuid4().hex[:8]}"
    session_id = uuid.uuid4().hex
    profile = TopicProfile(
        knowledge_level="beginner",
        confirmed_gaps=[{"name": GAP}],
    )
    quiz_cooldown = {"gap": GAP, "last_score": "0/1", "missed": [MISSED_ITEM]}

    with SessionLocal() as db:
        db.add(User(id=user_id))
        db.add(
            SessionModel(
                id=session_id,
                user_id=user_id,
                topic=TOPIC,
                topic_profile_json=profile.model_dump_json(),
                quiz_cooldown_json=json.dumps(quiz_cooldown),
            )
        )
        db.commit()
        db.add(
            LearningEvent(
                session_id=session_id,
                gap_tested=GAP,
                question=MISSED_ITEM["question"],
                correct=False,
            )
        )
        db.commit()

    return user_id, session_id


def _build_prompt_state_and_system_prompt(db, session_id: str) -> tuple[dict, str]:
    """Load the seeded profile/cooldown/gap_accuracy and assemble the system
    prompt the same way routes/chat.py._prepare_turn does."""
    from agent import prompts
    from db.models import Session as SessionModel
    from services import check_question_service, learning_event_service, profile_service

    session = db.get(SessionModel, session_id)
    profile = profile_service.load_profile(db, session_id)
    quiz_cooldown = check_question_service.get_quiz_cooldown_from_row(session)
    gap_accuracy = learning_event_service.gap_accuracy(db, session_id)

    prompt_state = {
        "topic": session.topic,
        "profile": profile,
        "ingestion_status": None,
        "retrieval_required": False,
        "seed_mode": None,
        "last_session_summary": None,
        "rolling_summary": None,
        "quiz_cooldown": quiz_cooldown,
        "gap_accuracy": gap_accuracy,
    }
    system_prompt = prompts.build_system_prompt(prompt_state)
    return prompt_state, system_prompt


async def _collect_reply(tutor, messages, system_prompt, ctx) -> str:
    """Drain tutor.run_streaming and reassemble the assistant's full reply
    text from assistant_delta events."""
    parts: list[str] = []
    async for ev in tutor.run_streaming(messages, system_prompt, ctx):
        if ev.type == "assistant_delta":
            parts.append(ev.data.get("text") or "")
    return "".join(parts)


async def _run_one(replicate: int, model: str | None) -> dict:
    """Returns trial result dict with reply + pass."""
    from agent import tutor
    from agent.types import ToolContext
    from config import settings
    from db.database import SessionLocal

    if model:
        settings.model = model
    settings.llm_stub = False  # eval must hit the real model

    user_id, session_id = _seed_session()

    with SessionLocal() as db:
        _prompt_state, system_prompt = _build_prompt_state_and_system_prompt(db, session_id)
        ctx = ToolContext(
            db=db,
            session_id=session_id,
            user_id=user_id,
            turn_started_at=datetime.now(timezone.utc),
        )
        messages = [{"role": "user", "content": USER_MESSAGE}]
        try:
            reply = await _collect_reply(tutor, messages, system_prompt, ctx)
        except Exception as e:
            return {
                "replicate": replicate,
                "reply": "",
                "passed": False,
                "error": f"{type(e).__name__}: {e}",
            }

    reply_lower = reply.lower()
    matched = any(s.lower() in reply_lower for s in MATCH_SUBSTRINGS)
    return {
        "replicate": replicate,
        "reply": reply,
        "passed": matched,
    }


async def _run_eval(replicates: int, model: str | None) -> dict:
    trials: list[dict] = []
    for rep in range(replicates):
        trials.append(await _run_one(rep, model))

    total = len(trials)
    passed = sum(1 for t in trials if t["passed"])
    overall = (passed / total) if total else 0.0
    return {"trials": trials, "passed": passed, "total": total, "overall": overall}


def _decision(overall: float) -> str:
    if overall >= 0.85:
        return "PASS"
    if overall >= 0.50:
        return "ITERATE_PROMPT"
    return "SWAP_MODEL"


def _render_block(replicates: int, model: str, summary: dict) -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        f"## Run {ts}",
        "",
        f"- model: `{model}`",
        f"- replicates: {replicates}",
        f"- overall pass rate: {summary['overall'] * 100:.1f}%"
        f" ({summary['passed']}/{summary['total']})",
        f"- decision: **{_decision(summary['overall'])}**",
        "",
        "<details><summary>Trial details</summary>",
        "",
        "```json",
        json.dumps(summary["trials"], indent=2, default=str),
        "```",
        "",
        "</details>",
        "",
    ]
    return "\n".join(lines)


def _write_report(report_path: Path, block: str) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        existing = report_path.read_text(encoding="utf-8")
    else:
        existing = (
            "# D1 AC3 - missed-concept-reference reliability\n\n"
            "Per the CLAUDE.md reliability checkpoints: gate threshold is >=85% across"
            " replicates. Scenario: user asks \"can you explain that again?\""
            " right after a missed quiz item; PASS requires the tutor's reply"
            " to reference the missed concept (chosen/correct answer or"
            " question stem). Below 85% triggers prompt iteration; if still"
            " failing after 2-3 iterations, swap default model to"
            " `anthropic/claude-sonnet-5`.\n\n"
        )
    report_path.write_text(existing + block, encoding="utf-8")


def _dry_run() -> int:
    """Build the prompt without calling the LLM. Free smoke: prints the
    assembled QUIZ_READINESS/GAP_ACCURACY lines and asserts the seeded
    missed detail reached the system prompt."""
    from db.database import SessionLocal

    _user_id, session_id = _seed_session()
    with SessionLocal() as db:
        _prompt_state, system_prompt = _build_prompt_state_and_system_prompt(db, session_id)

    lines = [
        line
        for line in system_prompt.splitlines()
        if line.startswith("QUIZ_READINESS:") or line.startswith("GAP_ACCURACY:")
    ]
    for line in lines:
        print(f"[dry-run] {line}")

    assert any(s in system_prompt for s in MATCH_SUBSTRINGS), (
        "seeded missed detail (2/6 | 3/4 | 1/2 + 1/4) not found in system prompt"
    )
    print("[dry-run] OK: missed detail present in system prompt")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=5)
    parser.add_argument(
        "--model",
        default=None,
        help="Override settings.model (default: keep current)",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "analysis" / "d1_missed_concept_eval.md"),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the prompt without calling the LLM (free smoke); exits 0 on success.",
    )
    args = parser.parse_args()

    _setup_isolated_db()

    if args.dry_run:
        return _dry_run()

    # Import settings late so the DATABASE_URL env var above takes effect.
    from config import settings  # noqa: E402

    model = args.model or settings.model
    started = time.time()
    summary = asyncio.run(_run_eval(args.replicates, args.model))
    elapsed = time.time() - started

    block = _render_block(args.replicates, model, summary)
    _write_report(Path(args.report), block)

    print(
        f"[eval] model={model} replicates={args.replicates}"
        f" overall={summary['overall'] * 100:.1f}% decision={_decision(summary['overall'])}"
        f" elapsed={elapsed:.1f}s"
    )
    print(f"[eval] report appended: {args.report}")
    return 0 if summary["overall"] >= 0.85 else 1


if __name__ == "__main__":
    raise SystemExit(main())
