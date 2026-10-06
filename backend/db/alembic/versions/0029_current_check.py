"""add sessions.current_check_json

Revision ID: 0029_current_check
Revises: 0028_created_at_and_checks
Create Date: 2026-09-24

#340: a check is now 1..3 sets posed one per turn. pending_check_json holds
only the OPEN set and is cleared when that set completes, so the check-level
pointer (set_total, last closed set_index, gaps seen) needs its own
nullable Text column. It survives between sets and is cleared when the final
set closes, the learner stops, or the session ends.

Nullable ADD COLUMN with no default is a catalog-only change on Postgres (no
table rewrite). C-12: lock_timeout caps how long the ACCESS EXCLUSIVE request
queues behind a long transaction on the hot sessions table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029_current_check"
down_revision: Union[str, None] = "0028_created_at_and_checks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    is_pg = op.get_context().dialect.name == "postgresql"
    if is_pg:
        op.execute("SET lock_timeout = '5s'")
    op.add_column(
        "sessions",
        sa.Column("current_check_json", sa.Text(), nullable=True),
    )
    if is_pg:
        op.execute("RESET lock_timeout")


def downgrade() -> None:
    is_pg = op.get_context().dialect.name == "postgresql"
    if is_pg:
        op.execute("SET lock_timeout = '5s'")
    op.drop_column("sessions", "current_check_json")
    if is_pg:
        op.execute("RESET lock_timeout")
