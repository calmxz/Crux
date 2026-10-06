"""index on learning_events.created_at (F-07)

Revision ID: 0025_learning_events_created_at
Revises: 0024_sessions_chunk_centroid
Create Date: 2026-09-19

GET /api/review/queue now bounds its scan to the last REVIEW_WINDOW_DAYS
days (services/review_queue_service.py). ix_learning_events_session already
confines that query to the caller's sessions, so the created_at predicate
was a filter over those rows rather than a full-table scan; this index gives
the planner a second access path (range-scan the window, then join) for a
query that runs on each sidebar boot. Which plan wins should be settled with
EXPLAIN (ANALYZE, BUFFERS) on the live DB -- see the PR notes.

Built with CREATE INDEX CONCURRENTLY: learning_events takes a write on every
graded check answer, and a plain CREATE INDEX holds a SHARE lock that blocks
those writes for the duration. CONCURRENTLY cannot run inside a transaction,
hence the autocommit_block (same shape as 0023_worker_queue).

Idempotency, both retry modes: if_not_exists / if_exists cover "index built
but alembic_version never stamped". A CONCURRENTLY build that fails part-way
leaves an INVALID index of the same name, and IF NOT EXISTS matches on name
only -- it would no-op and stamp the revision, leaving an index the planner
ignores but every INSERT still maintains. So the upgrade drops an invalid
namesake first (migration review, HIGH).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0025_learning_events_created_at"
down_revision: Union[str, None] = "0024_sessions_chunk_centroid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        # `--sql` offline mode has no bind to probe with, so skip the guard
        # there and emit the plain statements.
        if ctx.dialect.name == "postgresql" and not ctx.as_sql:
            invalid = op.get_bind().execute(
                sa.text(
                    "SELECT 1 FROM pg_index "
                    "WHERE indexrelid = "
                    "to_regclass('ix_learning_events_created_at') "
                    "AND NOT indisvalid"
                )
            ).scalar()
            if invalid:
                op.execute(
                    "DROP INDEX CONCURRENTLY IF EXISTS "
                    "ix_learning_events_created_at"
                )
        op.create_index(
            "ix_learning_events_created_at",
            "learning_events",
            ["created_at"],
            unique=False,
            if_not_exists=True,
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_learning_events_created_at",
            table_name="learning_events",
            if_exists=True,
            postgresql_concurrently=True,
        )
