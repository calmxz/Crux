"""add sessions.topic_suggest_state

Revision ID: 0031_topic_suggest_state
Revises: 0030_learner_preferences
Create Date: 2026-09-25

#354: the tutor offers a topic card once per session, on the first reply after
the learner's level becomes known. Nothing on the row says whether the level
was unknown when the session started (the level picker's PATCH leaves no
trace), so the session records it at create: "awaiting_level" when it starts
without a level, "done" once the card was offered, NULL otherwise. Existing
rows stay NULL and never get a card.

Nullable ADD COLUMN with no default is a catalog-only change on Postgres (no
table rewrite). C-12: lock_timeout caps how long the ACCESS EXCLUSIVE request
queues behind a long transaction on the hot sessions table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0031_topic_suggest_state"
down_revision: Union[str, None] = "0030_learner_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    is_pg = op.get_context().dialect.name == "postgresql"
    if is_pg:
        op.execute("SET lock_timeout = '5s'")
    op.add_column(
        "sessions",
        sa.Column("topic_suggest_state", sa.String(16), nullable=True),
    )
    if is_pg:
        op.execute("RESET lock_timeout")


def downgrade() -> None:
    is_pg = op.get_context().dialect.name == "postgresql"
    if is_pg:
        op.execute("SET lock_timeout = '5s'")
    op.drop_column("sessions", "topic_suggest_state")
    if is_pg:
        op.execute("RESET lock_timeout")
