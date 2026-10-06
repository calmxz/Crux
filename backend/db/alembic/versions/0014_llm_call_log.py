"""llm_call_log: per-call LLM cost attribution table (roadmap R3)

Revision ID: 0014_llm_call_log
Revises: 0013_learning_event_detail
"""
import sqlalchemy as sa
from alembic import op

revision = "0014_llm_call_log"
down_revision = "0013_learning_event_detail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_call_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.String(), sa.ForeignKey("sessions.id"), nullable=True),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_llm_call_log_user", "llm_call_log", ["user_id"])
    op.create_index("ix_llm_call_log_session", "llm_call_log", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_call_log_session", table_name="llm_call_log")
    op.drop_index("ix_llm_call_log_user", table_name="llm_call_log")
    op.drop_table("llm_call_log")
