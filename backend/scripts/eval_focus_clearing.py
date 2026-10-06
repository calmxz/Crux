"""Phase 3 LLM reliability gate: focus_target_gap clearing reliability.

Drives the tutor agent through four scripted patterns (Design Doc §6.3) and
records whether the agent correctly clears (or correctly does NOT clear) the
focus_target_gap field on the TopicProfile.

Patterns:
- linear_demonstrated: user shows understanding -> focus SHOULD clear
- topic_shift:         user redirects to a new topic -> focus SHOULD clear
- tangent_clarify:     user asks for sub-clarification on the same gap ->
                       focus should NOT clear
- vague_signal:        user says "ok got it" with no demonstration ->
                       focus should NOT clear

Per the CLAUDE.md reliability checkpoints: PASS threshold is >=85% across patterns x replicates.

Run:
    python backend/scripts/eval_focus_clearing.py --replicates 5

Writes analysis/mlp_checkpoint.md (appends a history block per run).
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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Make backend/ importable when invoked from repo root.
HERE = Path(__file__).resolve().parent
BACKEND_DIR = HERE.parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@dataclass(frozen=True)
class Pattern:
    name: str
    user_message: str
    expect_clear: bool


PATTERNS: list[Pattern] = [
    Pattern(
        name="linear_demonstrated",
        user_message=(
            "I think I get it now. Recursion is a function that calls itself"
            " on a smaller subproblem until it hits a base case that stops"
            " the chain. For factorial: factorial(n) returns n * factorial(n-1)"
            " and the base case is factorial(0) = 1."
        ),
        expect_clear=True,
    ),
    Pattern(
        name="topic_shift",
        user_message=(
            "Actually, let's set recursion aside for now. Can we move on"
            " to discuss iteration and for-loops instead?"
        ),
        expect_clear=True,
    ),
    Pattern(
        name="tangent_clarify",
        user_message=(
            "Wait, before we move on, can you explain again what a base case"
            " is in a recursive function? I'm not sure I follow."
        ),
        expect_clear=False,
    ),
    Pattern(
        name="vague_signal",
        user_message="ok got it",
        expect_clear=False,
    ),
]


def _setup_isolated_db():
    """Point the backend at a throwaway sqlite file before importing services."""
    tmp = Path(tempfile.mkdtemp(prefix="adapt_eval_"))
    db_path = tmp / "eval.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    return tmp, db_path


def _seed_session(focus_gap: str) -> tuple[str, str]:
    """Insert a User + Session with focus_target_gap pre-seeded. Returns ids."""
    from contracts import TopicProfile
    from db.database import SessionLocal, create_tables
    from db.models import Session as SessionModel
    from db.models import User

    create_tables()

    user_id = f"eval-user-{uuid.uuid4().hex[:8]}"
    session_id = uuid.uuid4().hex
    profile = TopicProfile(
        knowledge_level="intermediate",
        confirmed_gaps=[{"name": focus_gap}],
        focus_target_gap=focus_gap,
    )

    with SessionLocal() as db:
        db.add(User(id=user_id))
        db.add(
            SessionModel(
                id=session_id,
                user_id=user_id,
                topic="Recursion",
                topic_profile_json=profile.model_dump_json(),
            )
        )
        db.commit()

    return user_id, session_id


async def _collect_tool_calls(tutor, messages, system_prompt, ctx) -> list:
    """Drain tutor.run_streaming and reassemble per-call tool records from the
    tool_call_start / tool_call_done event pairs.

    Returns a list of SimpleNamespace(name, args, status, error) matching the
    shape the old non-streaming ToolCallRecord list exposed to this script.
    """
    from types import SimpleNamespace

    starts: dict = {}
    dones: dict = {}
    order: list = []
    async for ev in tutor.run_streaming(messages, system_prompt, ctx):
        if ev.type == "tool_call_start":
            call_id = ev.data.get("id")
            starts[call_id] = ev.data
            order.append(call_id)
        elif ev.type == "tool_call_done":
            dones[ev.data.get("id")] = ev.data

    tool_calls = []
    for call_id in order:
        start = starts[call_id]
        done = dones.get(call_id, {})
        tool_calls.append(
            SimpleNamespace(
                name=start.get("name"),
                args=start.get("args") or {},
                status=done.get("status"),
                error=done.get("error"),
            )
        )
    return tool_calls


async def _run_one(pattern: Pattern, model: str | None) -> dict:
    """Returns trial result dict with observed_clear + pass."""
    from agent import prompts, tutor
    from agent.types import ToolContext
    from config import settings
    from db.database import SessionLocal
    from services import profile_service

    if model:
        settings.model = model
    settings.llm_stub = False  # eval must hit the real model

    user_id, session_id = _seed_session(focus_gap="recursion")

    with SessionLocal() as db:
        profile = profile_service.load_profile(db, session_id)
        prompt_state = {
            "topic": "Recursion",
            "profile": profile,
            "ingestion_status": None,
            "retrieval_required": False,
            "seed_mode": None,
            "last_session_summary": None,
        }
        system_prompt = prompts.build_system_prompt(prompt_state)
        ctx = ToolContext(
            db=db,
            session_id=session_id,
            user_id=user_id,
            turn_started_at=datetime.now(timezone.utc),
        )
        messages = [{"role": "user", "content": pattern.user_message}]
        try:
            tool_calls = await _collect_tool_calls(tutor, messages, system_prompt, ctx)
        except Exception as e:
            return {
                "pattern": pattern.name,
                "observed_clear": None,
                "expected_clear": pattern.expect_clear,
                "passed": False,
                "error": f"{type(e).__name__}: {e}",
                "tool_calls": [],
            }

    observed_clear = any(
        tc.name == "update_topic_profile"
        and tc.args.get("focus_target_gap") is None
        and tc.args.get("focus_clear_reason") is not None
        for tc in tool_calls
    )
    return {
        "pattern": pattern.name,
        "observed_clear": observed_clear,
        "expected_clear": pattern.expect_clear,
        "passed": observed_clear == pattern.expect_clear,
        "tool_calls": [
            {"name": tc.name, "args": tc.args, "status": tc.status, "error": tc.error}
            for tc in tool_calls
        ],
    }


async def _run_eval(replicates: int, model: str | None) -> dict:
    trials: list[dict] = []
    for pattern in PATTERNS:
        for rep in range(replicates):
            res = await _run_one(pattern, model)
            res["replicate"] = rep
            trials.append(res)

    by_pattern: dict[str, dict] = {}
    for t in trials:
        slot = by_pattern.setdefault(t["pattern"], {"passed": 0, "total": 0})
        slot["total"] += 1
        if t["passed"]:
            slot["passed"] += 1

    total = sum(s["total"] for s in by_pattern.values())
    passed = sum(s["passed"] for s in by_pattern.values())
    overall = (passed / total) if total else 0.0
    return {"trials": trials, "by_pattern": by_pattern, "overall": overall}


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
        f"- replicates per pattern: {replicates}",
        f"- overall pass rate: {summary['overall'] * 100:.1f}%",
        f"- decision: **{_decision(summary['overall'])}**",
        "",
        "| Pattern | Passed | Total | Rate |",
        "|---|---:|---:|---:|",
    ]
    for name, slot in summary["by_pattern"].items():
        rate = (slot["passed"] / slot["total"]) if slot["total"] else 0.0
        lines.append(f"| {name} | {slot['passed']} | {slot['total']} | {rate * 100:.0f}% |")
    lines.append("")
    lines.append("<details><summary>Trial details</summary>")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(summary["trials"], indent=2, default=str))
    lines.append("```")
    lines.append("")
    lines.append("</details>")
    lines.append("")
    return "\n".join(lines)


def _write_report(report_path: Path, block: str) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        existing = report_path.read_text(encoding="utf-8")
    else:
        existing = (
            "# Phase 3 MLP Checkpoint - focus_target_gap clearing reliability\n\n"
            "Per the CLAUDE.md reliability checkpoints: gate threshold is >=85% across the four"
            " Design Doc S6.3 patterns. Below 85% triggers prompt iteration; if"
            " still failing after 2-3 iterations, swap default model to"
            " `anthropic/claude-sonnet-5`.\n\n"
        )
    report_path.write_text(existing + block, encoding="utf-8")


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
        default=str(REPO_ROOT / "analysis" / "mlp_checkpoint.md"),
    )
    args = parser.parse_args()

    _setup_isolated_db()

    # Import settings late so the env var above takes effect.
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
