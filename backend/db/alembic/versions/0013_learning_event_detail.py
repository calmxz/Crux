"""learning_events: per-answer detail columns (roadmap R0.2)

Revision ID: 0013_learning_event_detail
Revises: 0012_terms_acceptance
"""
import sqlalchemy as sa
from alembic import op

revision = "0013_learning_event_detail"
down_revision = "0012_terms_acceptance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_events",
        sa.Column("selected_index", sa.Integer(), nullable=True),
    )
    op.add_column(
        "learning_events",
        sa.Column("correct_index", sa.Integer(), nullable=True),
    )
    op.add_column(
        "learning_events",
        sa.Column("options_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "learning_events",
        sa.Column("purpose", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("learning_events", "purpose")
    op.drop_column("learning_events", "options_json")
    op.drop_column("learning_events", "correct_index")
    op.drop_column("learning_events", "selected_index")
