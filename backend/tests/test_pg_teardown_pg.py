"""#574: the shared teardown leaves nothing behind on Postgres.

One row is seeded in every table the plan covers, so an FK the plan orders
wrong fails here. The seeded tables are enumerated from the plan: a newly
covered table with no seeder below fails this test instead of passing it.

**Opt-in**: skipped unless `TEST_DATABASE_URL` is set. Run locally with
`scripts/pg_tests.sh tests/test_pg_teardown_pg.py --no-cov`. Never point it
at a production database.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from config import settings
from db.models import (
    ChatMessage,
    ChunkEmbedding,
    DailyCostLedger,
    Document,
    LearningEvent,
    LlmCallLog,
    UsageCounter,
)
from tests.pg_harness import run_teardown

TEST_DB = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DB,
    reason="TEST_DATABASE_URL not set - skipping live Postgres teardown test",
)

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _document_id(db, sid):
    return db.execute(select(Document.id).where(Document.session_id == sid)).scalar_one()


# One row per covered table, keyed by table name. Run parents first.
SEEDERS = {
    "chat_messages": lambda db, uid, sid: ChatMessage(session_id=sid, role="user", content="hi"),
    "usage_counters": lambda db, uid, sid: UsageCounter(user_id=uid, date_utc=TODAY, count=1),
    "learning_events": lambda db, uid, sid: LearningEvent(
        session_id=sid, gap_tested="joins", question="Q?", correct=True
    ),
    "documents": lambda db, uid, sid: Document(session_id=sid, filename="t.pdf", status="ready"),
    "chunk_embeddings": lambda db, uid, sid: ChunkEmbedding(
        session_id=sid,
        document_id=_document_id(db, sid),
        chunk_index=0,
        chunk_text="joins",
        embedding=[0.1] * settings.embedding_dim,
    ),
    "daily_cost_ledger": lambda db, uid, sid: DailyCostLedger(
        user_id=uid, date_utc=TODAY, cost_usd=Decimal("0.0001")
    ),
    "llm_call_log": lambda db, uid, sid: LlmCallLog(
        user_id=uid, session_id=sid, purpose="chat", model="m", cost_usd=Decimal("0.0001")
    ),
}


def _counts(db, plan, uid, sid) -> dict[str, int]:
    return {
        table.name: db.execute(
            select(func.count()).select_from(table).where(pred(uid, sid))
        ).scalar_one()
        for table, pred in plan
    }


def test_teardown_removes_a_row_from_every_covered_table(pg_seed):
    Session, uid, sid = pg_seed("teardown-pg", topic="sql")
    plan = pg_seed.plan
    with Session() as db:
        for table, _ in reversed(plan):
            if table.name in ("users", "sessions"):
                continue
            db.add(SEEDERS[table.name](db, uid, sid))
            db.flush()
        db.commit()
        seeded = _counts(db, plan, uid, sid)
        assert all(n >= 1 for n in seeded.values()), seeded

    with Session() as db:
        run_teardown(db, plan, uid, sid)

    with Session() as db:
        assert set(_counts(db, plan, uid, sid).values()) == {0}
