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

Each run hits the live LLM and is metered against your daily cap; the default
10 runs across 9 fixtures = 90 sessions, ~3-6 turns each = a few hundred
calls. Use --runs 3 for a quick smoke check.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Force an in-memory DB before importing anything that touches db.database.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import prompts, tutor  # noqa: E402
from agent.types import ToolContext  # noqa: E402
from contracts import TopicProfile  # noqa: E402
from db.database import Base  # noqa: E402
from db.models import Session as SessionModel  # noqa: E402
from db.models import User  # noqa: E402
from services import profile_service  # noqa: E402

PATTERN_DIR = Path(__file__).parent / "focus_patterns"
PATTERNS = ("linear", "topic_shift", "tangent", "vague_signal")
PASS_THRESHOLD = 0.85


def _make_session_factory():
    # StaticPool keeps a single shared connection so the in-memory DB persists
    # across sessions opened during the run.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    `expected_clear_at_turn` (None means must-not-clear)."""
    user_id, session_id = _seed_session(SessionLocal, fixture)
    db = SessionLocal()
    try:
        messages: list[dict] = []
        cleared_at: int | None = None

        for turn_idx, user_turn in enumerate(fixture["user_turns"], start=1):
            messages.append({"role": "user", "content": user_turn})

            profile = profile_service.load_profile(db, session_id)
            session_row = db.get(SessionModel, session_id)
            prompt_state = {
                "topic": session_row.topic,
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
            reply_parts: list[str] = []
            async for ev in tutor.run_streaming(messages, system_prompt, ctx):
                if ev.type == "assistant_delta":
                    reply_parts.append(ev.data.get("text", ""))
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


async def _main_async(runs: int) -> dict[str, tuple[float, int]]:
    SessionLocal = _make_session_factory()
    results: dict[str, tuple[float, int]] = {}

    for pattern in PATTERNS:
        path = PATTERN_DIR / f"{pattern}.json"
        fixtures = json.loads(path.read_text(encoding="utf-8"))
        passes = []
        for run_idx in range(runs):
            for fix_idx, fixture in enumerate(fixtures):
                try:
                    ok = await _run_fixture(SessionLocal, fixture)
                except Exception as e:  # noqa: BLE001
                    print(
                        f"  [{pattern} run={run_idx} fix={fix_idx}] error: {e}",
                        file=sys.stderr,
                    )
                    ok = False
                passes.append(ok)
        rate = sum(passes) / len(passes) if passes else 0.0
        results[pattern] = (rate, len(passes))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Runs per fixture (default 10).",
    )
    args = parser.parse_args()

    if os.environ.get("LLM_STUB") == "1":
        print(
            "WARNING: LLM_STUB=1 — results are not meaningful; the stub does "
            "not exercise focus-clearing logic.",
            file=sys.stderr,
        )

    results = asyncio.run(_main_async(args.runs))

    print("\n=== Focus-clearing reliability (spec §6.3) ===")
    failed = []
    for pattern, (rate, n) in results.items():
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
