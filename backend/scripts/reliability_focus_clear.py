"""Focus-clearing reliability checkpoint (spec §6.3).

Manual, hand-scripted, NOT in CI. Runs the tutor agent against the real LLM
across 4 prompt patterns (linear, topic_shift, tangent, vague_signal). Each
fixture seeds a session with a focus_target_gap, then feeds the scripted
user turns through the tutor. After each turn it reloads the profile and
checks whether focus_target_gap cleared.

Pass criterion per pattern: >= 85% of runs match the fixture's expectation
(cleared by `expected_clear_at_turn`, or never cleared when null). Failing
patterns exit 1 so the spec rule "3 prompt iterations, then swap model" can
be applied.

Usage:
    GEMINI_API_KEY=... python backend/scripts/reliability_focus_clear.py --runs 10

Each run hits the live LLM and is billed by the provider. Metering lands in
the script's in-memory DB with a fresh user per run: the per-user cap never
trips, and none of it reaches your real ledger. --max-cost (default $5) stops
starting new fixture runs once this process's recorded spend reaches it, so a
run can overshoot it by one fixture run; a cost stop prints no verdict and
exits 3. GLOBAL_DAILY_COST_CAP_USD (counting this process's spend) still
applies: a call it refuses ends the eval the same way, discarding the fixture
run it hit. The default 10 runs across 9 fixtures = 90 sessions, ~3-6 turns each
= a few hundred calls. Use --runs 3 for a quick smoke check.
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
from db.models import DailyCostLedger, User  # noqa: E402
from db.models import Session as SessionModel  # noqa: E402
from lib import error_codes  # noqa: E402
from services import profile_service, prompt_state  # noqa: E402

PATTERN_DIR = Path(__file__).parent / "focus_patterns"
PATTERNS = ("linear", "topic_shift", "tangent", "vague_signal")
PASS_THRESHOLD = 0.85
DEFAULT_MAX_COST = Decimal("5")
# Distinct from a threshold failure (1) and an argparse usage error (2).
COST_STOP_EXIT = 3
CAP_CODES = frozenset({error_codes.GLOBAL_COST_CAP_REACHED, error_codes.DAILY_COST_CAP_REACHED})


@dataclasses.dataclass
class EvalOutcome:
    results: dict[str, tuple[float, int]]
    completed: int
    planned: int
    spend: Decimal
    cost_stopped: bool
    # The refusal code when a cost cap refused a tutor call (#605).
    cap_refused: str | None = None


class _CapRefused(BaseException):
    """#605: a cost cap refused a tutor call, so the run never reached the
    model. A BaseException so the per-run `except Exception` cannot score it."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


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


def _seed_session(SessionLocal, fixture: dict) -> tuple[str, str]:
    db = SessionLocal()
    try:
        user_id = f"u-{uuid.uuid4().hex[:8]}"
        session_id = str(uuid.uuid4())
        db.add(User(id=user_id))
        db.add(
            SessionModel(
                id=session_id,
                user_id=user_id,
                topic=fixture.get("topic", "test topic"),
                topic_profile_json=TopicProfile(
                    focus_target_gap=fixture["focus_gap"]
                ).model_dump_json(),
            )
        )
        db.commit()
        return user_id, session_id
    finally:
        db.close()


async def _run_fixture(SessionLocal, fixture: dict) -> bool:
    """One fixture run. Returns True if the model's clearing behavior matched
    `expected_clear_at_turn` (None means must-not-clear). Raises _CapRefused
    if a cost cap refused a turn's call."""
    user_id, session_id = _seed_session(SessionLocal, fixture)
    db = SessionLocal()
    try:
        messages: list[dict] = []
        cleared_at: int | None = None

        for turn_idx, user_turn in enumerate(fixture["user_turns"], start=1):
            messages.append({"role": "user", "content": user_turn})

            # The seed has no level; keep the diagnostic off so the eval
            # measures focus clearing, as it was calibrated.
            state = dataclasses.replace(
                prompt_state.assemble(
                    prompt_state.gather_session_inputs(db, db.get(SessionModel, session_id)),
                    prompt_state.TurnInputs(retrieval_required=False),
                ),
                diagnostic_required=False,
            )
            system_prompt = prompts.build_system_prompt(state)

            ctx = ToolContext(
                db=db,
                session_id=session_id,
                user_id=user_id,
                turn_started_at=datetime.now(timezone.utc),
            )
            reply_parts: list[str] = []
            cap_code: str | None = None
            async for ev in tutor.run_streaming(messages, system_prompt, ctx):
                if ev.type == "assistant_delta":
                    reply_parts.append(ev.data.get("text", ""))
                elif ev.type == "error" and ev.data.get("code") in CAP_CODES:
                    cap_code = ev.data["code"]
            if cap_code is not None:
                raise _CapRefused(cap_code)
            reply = "".join(reply_parts)
            messages.append({"role": "assistant", "content": reply})

            updated = profile_service.load_profile(db, session_id)
            if cleared_at is None and updated.focus_target_gap is None:
                cleared_at = turn_idx

        expected = fixture.get("expected_clear_at_turn")
        if expected is None:
            return cleared_at is None
        return cleared_at is not None and cleared_at <= expected
    finally:
        db.close()


async def _main_async(runs: int, max_cost: Decimal) -> EvalOutcome:
    """Runs every fixture `runs` times, checking recorded spend against
    `max_cost` before each fixture run (never mid-run). On reaching it, starts
    no further runs and returns with `cost_stopped` set. A cost cap refusing
    a call mid-run discards that run and returns with `cap_refused` set."""
    SessionLocal = _make_session_factory()
    results: dict[str, tuple[float, int]] = {}
    fixtures_by_pattern = {
        pattern: json.loads((PATTERN_DIR / f"{pattern}.json").read_text(encoding="utf-8"))
        for pattern in PATTERNS
    }
    planned = runs * sum(len(fixtures) for fixtures in fixtures_by_pattern.values())
    completed = 0

    for pattern, fixtures in fixtures_by_pattern.items():
        passes = []
        for run_idx in range(runs):
            for fix_idx, fixture in enumerate(fixtures):
                spend = _total_spend(SessionLocal)
                if spend >= max_cost:
                    return EvalOutcome(results, completed, planned, spend, cost_stopped=True)
                try:
                    ok = await _run_fixture(SessionLocal, fixture)
                except _CapRefused as refused:
                    return EvalOutcome(
                        results,
                        completed,
                        planned,
                        _total_spend(SessionLocal),
                        cost_stopped=True,
                        cap_refused=refused.code,
                    )
                except Exception as e:  # noqa: BLE001
                    print(
                        f"  [{pattern} run={run_idx} fix={fix_idx}] error: {e}",
                        file=sys.stderr,
                    )
                    ok = False
                passes.append(ok)
                completed += 1
        rate = sum(passes) / len(passes) if passes else 0.0
        results[pattern] = (rate, len(passes))
    return EvalOutcome(results, completed, planned, _total_spend(SessionLocal), cost_stopped=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Runs per fixture (default 10).",
    )
    parser.add_argument(
        "--max-cost",
        type=_positive_usd,
        default=DEFAULT_MAX_COST,
        help=(
            "Start no new fixture run once recorded spend reaches this many USD "
            f"(default {DEFAULT_MAX_COST}). Checked between fixture runs, so "
            "spend can overshoot it by one run."
        ),
    )
    args = parser.parse_args()

    if os.environ.get("LLM_STUB") == "1":
        print(
            "WARNING: LLM_STUB=1 — results are not meaningful; the stub does "
            "not exercise focus-clearing logic.",
            file=sys.stderr,
        )

    try:
        outcome = asyncio.run(_main_async(args.runs, args.max_cost))
        return _report(outcome, args.max_cost)
    finally:
        # Also on Ctrl-C or a crash: the calls made so far are billed.
        # _main_async binds SessionLocal before its first await.
        print(f"\nTotal spend: ${_total_spend(SessionLocal):.4f}")


def _report(outcome: EvalOutcome, max_cost: Decimal) -> int:
    if outcome.cap_refused is not None:
        print(
            f"\nCost cap refused a call ({outcome.cap_refused}): spent ${outcome.spend:.4f}. "
            f"Completed {outcome.completed} of {outcome.planned} planned runs. "
            "No verdict over partial results."
        )
        return COST_STOP_EXIT
    if outcome.cost_stopped:
        print(
            f"\nCost limit reached: spent ${outcome.spend:.4f}, limit ${max_cost:.4f}. "
            f"Completed {outcome.completed} of {outcome.planned} planned runs. "
            "No verdict over partial results."
        )
        return COST_STOP_EXIT

    print("\n=== Focus-clearing reliability (spec §6.3) ===")
    failed = []
    for pattern, (rate, n) in outcome.results.items():
        flag = "PASS" if rate >= PASS_THRESHOLD else "FAIL"
        print(f"  {pattern:14s} {rate * 100:5.1f}%  ({n} runs)  [{flag}]")
        if rate < PASS_THRESHOLD:
            failed.append(pattern)

    if failed:
        print(
            f"\nFAILED patterns: {failed}. Threshold {PASS_THRESHOLD * 100:.0f}%. "
            "Per spec §6.3: iterate prompts up to 3 times, then swap model.",
        )
        return 1
    print(f"\nAll {len(PATTERNS)} patterns >= {PASS_THRESHOLD * 100:.0f}%.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
