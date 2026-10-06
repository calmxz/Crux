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

Usage:
    GEMINI_API_KEY=... python backend/scripts/eval_subtopic_levels.py --runs 10

Each run hits the live LLM and is metered against your daily cap; the
default 10 runs across 2 patterns x up to 3 turns each = a few dozen calls.
Use --runs 3 for a quick smoke check.
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

PATTERN_DIR = Path(__file__).parent / "subtopic_patterns"
PATTERNS = ("declared_level", "tested_progression")
RUNS_PER_PATTERN = 10
THRESHOLD = 0.85


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
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


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

        for turn_idx, user_turn in enumerate(pattern["turns"], start=1):
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
            if matched_at is None and _matches(updated, expected):
                matched_at = turn_idx

        if matched_at is None:
            return False
        return matched_at <= expected["by_turn"]
    finally:
        db.close()


async def _main_async(runs_per_pattern: int) -> dict[str, tuple[float, int]]:
    SessionLocal = _make_session_factory()
    results: dict[str, tuple[float, int]] = {}

    for pattern_name in PATTERNS:
        path = PATTERN_DIR / f"{pattern_name}.json"
        pattern = json.loads(path.read_text(encoding="utf-8"))
        passes = []
        for run_idx in range(runs_per_pattern):
            try:
                ok = await _run_pattern_once(SessionLocal, pattern)
            except Exception as e:  # noqa: BLE001
                print(
                    f"  [{pattern_name} run={run_idx}] error: {e}",
                    file=sys.stderr,
                )
                ok = False
            passes.append(ok)
        rate = sum(passes) / len(passes) if passes else 0.0
        results[pattern_name] = (rate, len(passes))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs",
        type=int,
        default=RUNS_PER_PATTERN,
        help=f"Runs per pattern (default {RUNS_PER_PATTERN}).",
    )
    args = parser.parse_args()

    if os.environ.get("LLM_STUB") == "1":
        print(
            "WARNING: LLM_STUB=1 - results are not meaningful; the stub does "
            "not exercise subtopic-level patching.",
            file=sys.stderr,
        )

    results = asyncio.run(_main_async(args.runs))

    print("\n=== Subtopic-level reliability (R4.1 AC3) ===")
    failed = []
    for pattern_name, (rate, n) in results.items():
        flag = "PASS" if rate >= THRESHOLD else "FAIL"
        print(f"  {pattern_name:20s} {rate * 100:5.1f}%  ({n} runs)  [{flag}]")
        if rate < THRESHOLD:
            failed.append(pattern_name)

    if failed:
        print(
            f"\nFAILED patterns: {failed}. Threshold {THRESHOLD * 100:.0f}%.",
        )
        return 1
    print(f"\nAll {len(PATTERNS)} patterns >= {THRESHOLD * 100:.0f}%.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
