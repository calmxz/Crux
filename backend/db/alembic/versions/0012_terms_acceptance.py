"""terms acceptance columns on users

Revision ID: 0012_terms_acceptance
Revises: 0011_drop_subjects_lessons
"""
import sqlalchemy as sa
from alembic import op

revision = "0012_terms_acceptance"
down_revision = "0011_drop_subjects_lessons"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("accepted_terms_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("terms_version", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "terms_version")
    op.drop_column("users", "accepted_terms_at")
