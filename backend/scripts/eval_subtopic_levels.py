"""Subtopic-level patch reliability eval (R4.1 AC3, extends WS-G3).

Manual, paid, live-LLM. Not run in CI.
Pass criterion per pattern: >= 0.85 of runs produce a subtopic_levels entry
whose key contains the expected subtopic (canonicalized substring match --
naming drift like 'u-sub' vs 'u-substitution' counts as a miss only if the
expected token is absent) at one of the expected levels by the stated turn.
Failing patterns exit 1.

Mirrors backend/scripts/reliability_focus_clear.py's session-setup,
turn-feeding, and profile-reload wiring: an in-memory StaticPool sqlite DB,
one seeded Session per run, turns fed one at a time through
tutor.run_streaming with the profile reloaded after each turn.

A pattern turn is a chat message (a string) or the structured answer step
{"action": "answer_checks_correctly"}: it answers every pending Item of the
open check Set correctly through check_service.answer, Closes the Set through
check_service.complete and runs the follow-up turn on the results summary,
as the learner's clicks and Done button do in the app. When a follow-up poses
the Check's next Set, the step answers that too (at most 3 Sets): one more
paid call per extra Set. Every pattern is
validated before the first run; a malformed one exits 4 having spent nothing.

Usage:
    GEMINI_API_KEY=... python backend/scripts/eval_subtopic_levels.py --runs 10
    ... --pattern tested_progression --runs 10 --max-cost 1   # one pattern

Each run hits the live LLM and is billed by the provider. Metering lands in
the script's in-memory DB with a fresh user per run: the per-user cap never
trips, and none of it reaches your real ledger. --max-cost (default $5) stops
starting new runs once this process's recorded spend reaches it, so a run
can overshoot it by one run; a cost stop prints no verdict and exits 3.
GLOBAL_DAILY_COST_CAP_USD (counting this process's spend) still applies. The
default 10 runs per pattern: declared_level makes 3 calls a run,
tested_progression 3 to 5 (one follow-up per Set), so 60 to 80 calls for
both. Use --runs 3 for a quick smoke check.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Force an in-memory DB before importing anything that touches db.database.
# Assigned, not defaulted: an exported DATABASE_URL must not reach it (#596).
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import prompts, tutor  # noqa: E402
from agent.types import ToolContext  # noqa: E402
from contracts import TopicProfile  # noqa: E402
from db.database import Base, SessionLocal  # noqa: E402
from db.models import ChatMessage, DailyCostLedger, LearningEvent, User  # noqa: E402
from db.models import Session as SessionModel  # noqa: E402
from services import check_service, profile_service, prompt_state  # noqa: E402

PATTERN_DIR = Path(__file__).parent / "subtopic_patterns"
PATTERNS = ("declared_level", "tested_progression")
ANSWER_STEP = {"action": "answer_checks_correctly"}
# Sets per Check: openapi.yaml caps AskCheckQuestionsArgs.set_total at 3.
MAX_SETS = 3
RUNS_PER_PATTERN = 10
THRESHOLD = 0.85
DEFAULT_MAX_COST = Decimal("5")
# Distinct from a threshold failure (1) and an argparse usage error (2).
COST_STOP_EXIT = 3
BAD_PATTERN_EXIT = 4


@dataclasses.dataclass
class EvalOutcome:
    results: dict[str, tuple[float, int]]
    completed: int
    planned: int
    spend: Decimal
    cost_stopped: bool


def _positive_usd(value: str) -> Decimal:
    try:
        usd = Decimal(value)
    except InvalidOperation:
        raise argparse.ArgumentTypeError(f"not a number: {value!r}") from None
    if not usd.is_finite() or usd <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive amount, got {value!r}")
    return usd


def _total_spend(SessionLocal) -> Decimal:
    # Every date, not cost_meter.global_spend: that filters to today (UTC), so
    # a run crossing UTC midnight would read $0. This DB only ever holds this
    # invocation's spend.
    with SessionLocal() as db:
        total = db.scalar(select(func.coalesce(func.sum(DailyCostLedger.cost_usd), 0)))
    return Decimal(str(total))


def _valid_turn(turn) -> bool:
    return isinstance(turn, str) or turn == ANSWER_STEP


def _load_pattern(path: Path) -> dict:
    """A pattern fixture, refusing a malformed one here rather than failing
    every paid run of it."""
    pattern = json.loads(path.read_text(encoding="utf-8"))
    for n, turn in enumerate(pattern["turns"], start=1):
        if not _valid_turn(turn):
            raise ValueError(f"{path.name} turn {n}: unknown turn {turn!r}")
    missing = {"subtopic", "levels", "by_turn"} - set(pattern.get("expected", {}))
    if missing:
        raise ValueError(f"{path.name}: expected lacks {sorted(missing)}")
    return pattern


def _load_patterns(names) -> dict[str, dict]:
    return {name: _load_pattern(PATTERN_DIR / f"{name}.json") for name in names}


def _matches(profile, expected) -> bool:
    levels = profile.subtopic_levels or {}
    want = expected["subtopic"].strip().casefold()
    for key, lvl in levels.items():
        if want in key.strip().casefold() and lvl in expected["levels"]:
            return True
    return False


def _make_session_factory():
    # StaticPool keeps a single shared connection so the in-memory DB persists
    # across sessions opened during the run.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    # The LLM adapter opens its own sessions (cap gate, settlement, call log)
    # from db.database.SessionLocal; bind it here so they reach this DB too.
    SessionLocal.configure(bind=engine)
    return SessionLocal


def _seed_session(SessionLocal, pattern: dict) -> tuple[str, str]:
    db = SessionLocal()
    try:
        user_id = f"u-{uuid.uuid4().hex[:8]}"
        session_id = str(uuid.uuid4())
        db.add(User(id=user_id))
        db.add(
            SessionModel(
                id=session_id,
                user_id=user_id,
                topic=pattern.get("topic", "test topic"),
                topic_profile_json=TopicProfile().model_dump_json(),
            )
        )
        db.commit()
        return user_id, session_id
    finally:
        db.close()


async def _stream_reply(messages: list[dict], system_prompt: str, ctx: ToolContext) -> str:
    reply_parts: list[str] = []
    async for ev in tutor.run_streaming(messages, system_prompt, ctx):
        if ev.type == "assistant_delta":
            reply_parts.append(ev.data.get("text", ""))
    return "".join(reply_parts)


async def _chat_turn(db, session_id: str, user_id: str, messages: list[dict]) -> None:
    # The seed has no level; keep the diagnostic off so the eval
    # measures subtopic patching, as it was calibrated.
    state = dataclasses.replace(
        prompt_state.assemble(
            prompt_state.gather_session_inputs(db, db.get(SessionModel, session_id)),
            prompt_state.TurnInputs(retrieval_required=False),
        ),
        diagnostic_required=False,
    )
    ctx = ToolContext(
        db=db,
        session_id=session_id,
        user_id=user_id,
        turn_started_at=datetime.now(timezone.utc),
    )
    reply = await _stream_reply(messages, prompts.build_system_prompt(state), ctx)
    messages.append({"role": "assistant", "content": reply})


async def _answer_step(db, session_id: str, user_id: str, messages: list[dict]) -> bool:
    """Answer the open Set correctly, as the learner's clicks and Done button
    do, then every later Set a follow-up poses. A follow-up that replies
    without posing the next Set leaves the Check between Sets, as in the app.
    Returns False, doing nothing, when no Set is open."""
    answered = False
    for _ in range(MAX_SETS):
        pc = check_service.open_set(db.get(SessionModel, session_id))
        if pc is None:
            break
        await _answer_set(db, session_id, user_id, messages, pc)
        answered = True
    return answered


async def _answer_set(db, session_id: str, user_id: str, messages: list[dict], pc: dict) -> None:
    """Answer every pending Item of Set `pc` correctly, Close it and run the
    follow-up turn."""
    for index, item in enumerate(pc["items"]):
        if item.get("status", "pending") == "pending":
            check_service.answer(db, session_id, index, item["correct_index"])
    summary, cooldown = check_service.complete(db, session_id)

    # Mirrors routes/sessions.py::_followup_context, less its daily message
    # cap (a fresh user per run never reaches it).
    inputs = dataclasses.replace(
        prompt_state.gather_session_inputs(
            db, db.get(SessionModel, session_id), learner_prefs={}, gap_accuracy={}
        ),
        rolling_summary=None,
        pending_check=None,
        current_check=None,
        quiz_cooldown=cooldown,
    )
    state = dataclasses.replace(
        prompt_state.assemble(inputs, prompt_state.TurnInputs(retrieval_required=False)),
        diagnostic_required=False,
    )
    ctx = ToolContext(
        db=db,
        session_id=session_id,
        user_id=user_id,
        turn_started_at=datetime.now(timezone.utc),
        suppress_check=True,
        diagnostic_required=(inputs.profile.knowledge_level is None),
    )
    # The summary turn is not persisted in the app, so later turns never see it.
    followup = [*messages, {"role": "user", "content": summary}]
    reply = await _stream_reply(followup, prompts.build_system_prompt(state), ctx)
    messages.append({"role": "assistant", "content": reply})


async def _run_pattern_once(SessionLocal, pattern: dict) -> bool:
    """One run of a pattern. Feeds `pattern["turns"]` one at a time, reloading
    the profile after each turn, and records the earliest turn at which
    `_matches` becomes true. Returns True if that turn is at or before
    `pattern["expected"]["by_turn"]`."""
    user_id, session_id = _seed_session(SessionLocal, pattern)
    db = SessionLocal()
    try:
        messages: list[dict] = []
        expected = pattern["expected"]
        matched_at: int | None = None

        for turn_idx, turn in enumerate(pattern["turns"], start=1):
            if isinstance(turn, str):
                messages.append({"role": "user", "content": turn})
                await _chat_turn(db, session_id, user_id, messages)
            elif not _valid_turn(turn):
                raise ValueError(f"turn {turn_idx}: unknown turn {turn!r}")
            elif not await _answer_step(db, session_id, user_id, messages):
                print(
                    f"  [{pattern['name']}] turn {turn_idx}: no open check Set; "
                    "answer step skipped",
                    file=sys.stderr,
                )

            updated = profile_service.load_profile(db, session_id)
            if matched_at is None and _matches(updated, expected):
                matched_at = turn_idx

        ok = matched_at is not None and matched_at <= expected["by_turn"]
        if not ok:
            _report_miss(db, session_id, pattern["name"])
        return ok
    finally:
        db.close()


def _report_miss(db, session_id: str, name: str) -> None:
    """#612: what the tutor did in a failed run, so a miss can be told apart:
    no patch, a patch under another subtopic name, or a refused patch. Reads
    the tool calls the tutor persisted on its replies."""
    profile = profile_service.load_profile(db, session_id)
    events = db.scalars(select(LearningEvent).where(LearningEvent.session_id == session_id)).all()
    correct = sum(1 for e in events if e.correct)
    lines = [
        f"  [{name}] miss: subtopic_levels={(profile.subtopic_levels or {})!r}; "
        f"graded {correct}/{len(events)} correct"
    ]
    replies = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id, ChatMessage.role == "assistant")
        .order_by(ChatMessage.id)
    ).all()
    for n, reply in enumerate(replies, start=1):
        for call in json.loads(reply.tool_calls_json or "[]"):
            if call["name"] == "ask_check_questions":
                args = {"gap": call["args"].get("gap")}
            else:
                args = {k: v for k, v in call["args"].items() if k != "session_id"}
            line = f"    reply {n} {call['name']} {args!r} {call['status']}"
            if call.get("error"):
                line += f": {call['error']}"
            lines.append(line)
    print("\n".join(lines), file=sys.stderr)


async def _main_async(
    patterns: dict[str, dict], runs_per_pattern: int, max_cost: Decimal
) -> EvalOutcome:
    """Runs every pattern `runs_per_pattern` times, checking recorded spend
    against `max_cost` before each run (never mid-run). On reaching it, starts
    no further runs and returns with `cost_stopped` set."""
    SessionLocal = _make_session_factory()
    results: dict[str, tuple[float, int]] = {}
    planned = runs_per_pattern * len(patterns)
    completed = 0

    for pattern_name, pattern in patterns.items():
        passes = []
        for run_idx in range(runs_per_pattern):
            spend = _total_spend(SessionLocal)
            if spend >= max_cost:
                return EvalOutcome(results, completed, planned, spend, cost_stopped=True)
            try:
                ok = await _run_pattern_once(SessionLocal, pattern)
            except Exception as e:  # noqa: BLE001
                print(
                    f"  [{pattern_name} run={run_idx}] error: {e}",
                    file=sys.stderr,
                )
                ok = False
            passes.append(ok)
            completed += 1
        rate = sum(passes) / len(passes) if passes else 0.0
        results[pattern_name] = (rate, len(passes))
    return EvalOutcome(results, completed, planned, _total_spend(SessionLocal), cost_stopped=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs",
        type=int,
        default=RUNS_PER_PATTERN,
        help=f"Runs per pattern (default {RUNS_PER_PATTERN}).",
    )
    parser.add_argument(
        "--max-cost",
        type=_positive_usd,
        default=DEFAULT_MAX_COST,
        help=(
            "Start no new run once recorded spend reaches this many USD "
            f"(default {DEFAULT_MAX_COST}). Checked between runs, so spend can "
            "overshoot it by one run."
        ),
    )
    parser.add_argument(
        "--pattern",
        action="append",
        choices=PATTERNS,
        help="Run only this pattern; repeat for more (default: every pattern).",
    )
    args = parser.parse_args()

    if os.environ.get("LLM_STUB") == "1":
        print(
            "WARNING: LLM_STUB=1 - results are not meaningful; the stub does "
            "not exercise subtopic-level patching.",
            file=sys.stderr,
        )

    # Every pattern before the first paid run, so a bad one costs nothing.
    try:
        patterns = _load_patterns(args.pattern or PATTERNS)
    except (OSError, ValueError, KeyError) as e:
        print(f"Bad pattern fixture: {e}", file=sys.stderr)
        return BAD_PATTERN_EXIT

    try:
        outcome = asyncio.run(_main_async(patterns, args.runs, args.max_cost))
        return _report(outcome, args.max_cost)
    finally:
        # Also on Ctrl-C or a crash: the calls made so far are billed.
        # _main_async binds SessionLocal before its first await.
        print(f"\nTotal spend: ${_total_spend(SessionLocal):.4f}")


def _report(outcome: EvalOutcome, max_cost: Decimal) -> int:
    if outcome.cost_stopped:
        print(
            f"\nCost limit reached: spent ${outcome.spend:.4f}, limit ${max_cost:.4f}. "
            f"Completed {outcome.completed} of {outcome.planned} planned runs. "
            "No verdict over partial results."
        )
        return COST_STOP_EXIT

    print("\n=== Subtopic-level reliability (R4.1 AC3) ===")
    failed = []
    for pattern_name, (rate, n) in outcome.results.items():
        flag = "PASS" if rate >= THRESHOLD else "FAIL"
        print(f"  {pattern_name:20s} {rate * 100:5.1f}%  ({n} runs)  [{flag}]")
        if rate < THRESHOLD:
            failed.append(pattern_name)

    if failed:
        print(
            f"\nFAILED patterns: {failed}. Threshold {THRESHOLD * 100:.0f}%.",
        )
        return 1
    print(f"\nAll {len(outcome.results)} patterns >= {THRESHOLD * 100:.0f}%.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
