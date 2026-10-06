"""sessions: nullable rolling summary columns (roadmap P2 AC3)

Revision ID: 0016_session_rolling_summary
Revises: 0015_llm_call_log_tokens
"""
import sqlalchemy as sa
from alembic import op

revision = "0016_session_rolling_summary"
down_revision = "0015_llm_call_log_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("rolling_summary", sa.Text(), nullable=True))
    op.add_column("sessions", sa.Column("rolling_summary_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "rolling_summary_count")
    op.drop_column("sessions", "rolling_summary")
