from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from config import settings
from db.models import UsageCounter
from services.sql_dialect import dialect_insert


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def check_and_increment(db: Session, user_id: str) -> tuple[bool, int]:
    """Return (allowed, current_used_count_after_call).

    If the cap is already reached, the count is not incremented and
    `allowed=False`. Otherwise the count is bumped and returned post-increment.

    Concurrency-safe: parallel callers for the same (user, day) cannot create
    duplicate rows or exceed the cap. A non-atomic SELECT-then-INSERT loses this
    race (each caller sees no row and INSERTs), which is exactly the bug PR #83's
    parallel reference uploads exposed.

    Step 1 atomically guarantees a single row exists via INSERT ... ON CONFLICT
    DO NOTHING against the `uq_usage_counters_user_date` constraint. Step 2
    increments under a row lock only while strictly below the cap, so the cap
    holds even under contention, and returns the post-increment count via
    `RETURNING` so no separate SELECT is needed on the allowed path.
    `scalar_one_or_none()` is safe because the unique constraint guarantees at
    most one matching row.
    """
    date_utc = _today_utc()

    insert = dialect_insert(db)
    db.execute(
        insert(UsageCounter)
        .values(user_id=user_id, date_utc=date_utc, count=0)
        .on_conflict_do_nothing(index_elements=["user_id", "date_utc"])
    )

    result = db.execute(
        update(UsageCounter)
        .where(
            UsageCounter.user_id == user_id,
            UsageCounter.date_utc == date_utc,
            UsageCounter.count < settings.daily_cap,
        )
        .values(count=UsageCounter.count + 1)
        .returning(UsageCounter.count)
    )
    new_count = result.scalar_one_or_none()
    if new_count is not None:
        # UPDATE matched: we incremented while under the cap.
        db.commit()
        return True, new_count

    # UPDATE matched no row: cap already reached. One fallback SELECT for the
    # count (this path returns 429 upstream; outside the happy-path budget).
    used = db.execute(
        select(UsageCounter.count).where(
            UsageCounter.user_id == user_id,
            UsageCounter.date_utc == date_utc,
        )
    ).scalar_one()
    db.commit()
    return False, used
