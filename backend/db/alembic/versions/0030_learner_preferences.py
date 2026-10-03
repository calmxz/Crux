"""add users.check_ins + users.reply_length; coerce feedback_pref (#356)

Revision ID: 0030_learner_preferences
Revises: 0029_current_check
Create Date: 2026-09-24

Learner preferences (#342/#356) become an enum trio on the users row:
feedback_pref [hints, direct_answers], check_ins [often, sometimes,
only_when_asked], reply_length [brief, balanced, thorough].

ADD COLUMN ... NOT NULL DEFAULT '<constant>' is a catalog-only change on
Postgres 11+ (no table rewrite). C-12: lock_timeout caps how long the
ACCESS EXCLUSIVE request queues behind a long transaction.

feedback_pref stays nullable (NULL = "never set", see 0020) and reads as
"hints". Non-NULL values outside the enum predate it (free string) and are
coerced to "hints". The coercion is not reversed on downgrade: the original
values are not recoverable and the pre-enum column accepted "hints" anyway.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0030_learner_preferences"
down_revision: Union[str, None] = "0029_current_check"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    is_pg = op.get_context().dialect.name == "postgresql"
    if is_pg:
        op.execute("SET lock_timeout = '5s'")
    # Before the ALTERs: the scan then runs under ROW EXCLUSIVE, not inside
    # the ACCESS EXCLUSIVE window the ADD COLUMNs take until commit.
    op.execute(
        "UPDATE users SET feedback_pref = 'hints' "
        "WHERE feedback_pref IS NOT NULL "
        "AND feedback_pref NOT IN ('hints', 'direct_answers')"
    )
    op.add_column(
        "users",
        sa.Column(
            "check_ins",
            sa.String(),
            nullable=False,
            server_default=sa.text("'sometimes'"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "reply_length",
            sa.String(),
            nullable=False,
            server_default=sa.text("'balanced'"),
        ),
    )
    if is_pg:
        op.execute("RESET lock_timeout")


def downgrade() -> None:
    is_pg = op.get_context().dialect.name == "postgresql"
    if is_pg:
        op.execute("SET lock_timeout = '5s'")
    op.drop_column("users", "reply_length")
    op.drop_column("users", "check_ins")
    if is_pg:
        op.execute("RESET lock_timeout")
