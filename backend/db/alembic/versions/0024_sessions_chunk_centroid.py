"""sessions.chunk_centroid (lazily materialised session centroid)

Revision ID: 0024_sessions_chunk_centroid
Revises: 0023_worker_queue
Create Date: 2026-09-19

F-05: semantic_fallback_required averaged every chunk_embeddings row of the
session on every OPTIONAL chat turn. Cache the mean on the session row and
recompute only when ingestion or a document delete invalidates it.

Nullable with no server default, so ADD COLUMN is a catalog-only change --
no table rewrite, no long ACCESS EXCLUSIVE hold. Postgres-only (mirrors
0002_chunk_embeddings): on SQLite the column comes from
Base.metadata.create_all, so the migration is a no-op there.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0024_sessions_chunk_centroid"
down_revision: Union[str, None] = "0023_worker_queue"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Pinned, not read from settings: a migration must describe the schema as it
# was at this revision, exactly as 0002_chunk_embeddings does for
# chunk_embeddings.embedding.
EMBEDDING_DIM = 768


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # C-12: ADD COLUMN is catalog-only, but it still takes ACCESS EXCLUSIVE on
    # `sessions` -- the hottest table in the app -- and entrypoint.sh runs
    # `alembic upgrade head` while the previous instance still serves traffic.
    # Without a lock timeout the ALTER queues behind an in-flight read and
    # every later session read queues behind it. Failing fast instead kills
    # the new container (set -e) and leaves the old one serving.
    op.execute("SET lock_timeout = '5s'")
    op.add_column(
        "sessions",
        sa.Column("chunk_centroid", Vector(EMBEDDING_DIM), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("SET lock_timeout = '5s'")
    # Lossy by design and safe: chunk_centroid is a derived cache, fully
    # recomputable from chunk_embeddings.embedding (retrieval_service
    # ._compute_centroid). NULL already means "not computed yet", so a
    # re-upgrade owes no backfill.
    op.drop_column("sessions", "chunk_centroid")
