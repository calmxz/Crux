"""documents.content_sha256 + partial unique index (C-08)

Revision ID: 0026_documents_content_sha256
Revises: 0025_learning_events_created_at
Create Date: 2026-09-19

POST /api/upload now hashes the uploaded bytes and returns the existing row
when the same (session_id, sha) is already held, so a double-submit or a
retried request no longer duplicates a document and its embeddings.

The column is added nullable with no default: that is a catalog-only change
on Postgres 11+, no table rewrite, so legacy rows stay NULL and are simply
never deduped.

The index is PARTIAL and UNIQUE:
  WHERE content_sha256 IS NOT NULL AND status <> 'failed'
NULL hashes (legacy rows) are excluded so they can never collide, and failed
rows are excluded so a retry after a failed ingest is always allowed to
insert a fresh row. `op.create_index` cannot express a portable partial
WHERE, hence raw SQL on postgresql and `sqlite_where` elsewhere.

Built with CREATE INDEX CONCURRENTLY: documents takes a write on every
upload and on every worker status transition, and a plain CREATE UNIQUE
INDEX holds a SHARE lock that blocks those for the duration. CONCURRENTLY
cannot run inside a transaction, hence the autocommit_block (same shape as
0025_learning_events_created_at).

Idempotency covers BOTH statements, because autocommit_block() COMMITs the
enclosing transaction on entry: the ADD COLUMN is durable before the index
build starts, while alembic_version is only stamped once upgrade() returns.
So a failed index build leaves the column present at revision 0025, and the
retry (entrypoint.sh runs `alembic upgrade head` on every boot) must not
trip over it. Hence ADD COLUMN IF NOT EXISTS on postgresql, the same guard
0023_worker_queue uses, plus IF NOT EXISTS / IF EXISTS on the index.

A CONCURRENTLY build that fails part-way also leaves an INVALID index of the
same name, and IF NOT EXISTS matches on name only -- it would no-op and stamp
the revision, leaving an index the planner ignores while every INSERT still
maintains it. So the upgrade drops an invalid namesake first (migration
review, HIGH).

C-12: `SET lock_timeout = '5s'` so the ALTER TABLE queues behind a long
running transaction for at most five seconds instead of holding the lock
queue open behind it. It is a session-level SET, not SET LOCAL, so it
survives the commits that autocommit_block performs -- which is why it is
reset to 0 inside the block: CREATE INDEX CONCURRENTLY takes only SHARE
UPDATE EXCLUSIVE and blocks no upload traffic, but it does wait on the
virtual-xid locks of older transactions, and a 5s cap there would cancel the
build and leave an INVALID namesake for nothing.

NOTE: if duplicate live rows already existed for the same (session_id, sha),
the CONCURRENTLY build would raise and leave an invalid index behind.
Nothing can have written content_sha256 before this revision, so that cannot
happen on the first run; on a re-run after a partial upgrade the
invalid-namesake guard above clears it.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026_documents_content_sha256"
down_revision: Union[str, None] = "0025_learning_events_created_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "uq_documents_session_sha"
PARTIAL_WHERE = "content_sha256 IS NOT NULL AND status <> 'failed'"


def upgrade() -> None:
    ctx = op.get_context()
    if ctx.dialect.name == "postgresql":
        op.execute("SET lock_timeout = '5s'")
        # IF NOT EXISTS: autocommit_block() below commits this ALTER, so a
        # failed index build leaves the column behind at revision 0025 and the
        # next boot re-runs upgrade(). sqlite has no ADD COLUMN IF NOT EXISTS,
        # hence the branch.
        op.execute(
            "ALTER TABLE documents ADD COLUMN IF NOT EXISTS content_sha256 varchar(64)"
        )
    else:
        op.add_column(
            "documents",
            sa.Column("content_sha256", sa.String(length=64), nullable=True),
        )

    with ctx.autocommit_block():
        if ctx.dialect.name == "postgresql":
            # CREATE INDEX CONCURRENTLY takes SHARE UPDATE EXCLUSIVE and
            # blocks no writer, but it waits on older transactions' virtual
            # xids -- the C-12 5s cap would cancel the build there and leave
            # an INVALID namesake. The cap exists for the ALTER TABLE above.
            op.execute("SET lock_timeout = 0")
            # `--sql` offline mode has no bind to probe with, so skip the
            # guard there and emit the plain statements.
            if not ctx.as_sql:
                invalid = op.get_bind().execute(
                    sa.text(
                        "SELECT 1 FROM pg_index "
                        "WHERE indexrelid = to_regclass(:name) "
                        "AND NOT indisvalid"
                    ),
                    {"name": INDEX_NAME},
                ).scalar()
                if invalid:
                    op.execute(
                        f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}"
                    )
            op.execute(
                f"CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME} "
                f"ON documents (session_id, content_sha256) "
                f"WHERE {PARTIAL_WHERE}"
            )
        else:
            op.create_index(
                INDEX_NAME,
                "documents",
                ["session_id", "content_sha256"],
                unique=True,
                if_not_exists=True,
                sqlite_where=sa.text(PARTIAL_WHERE),
            )

    if ctx.dialect.name == "postgresql":
        # Do not leak the 5s cap onto a later revision in the same
        # `alembic upgrade head` run.
        op.execute("RESET lock_timeout")


def downgrade() -> None:
    ctx = op.get_context()
    if ctx.dialect.name == "postgresql":
        op.execute("SET lock_timeout = '5s'")

    with ctx.autocommit_block():
        if ctx.dialect.name == "postgresql":
            op.execute("SET lock_timeout = 0")
        op.drop_index(
            INDEX_NAME,
            table_name="documents",
            if_exists=True,
            postgresql_concurrently=True,
        )

    if ctx.dialect.name == "postgresql":
        op.execute("RESET lock_timeout")

    # Lossy and one-way in practice: every stored hash is destroyed, so a
    # re-upgrade starts all-NULL and dedupe stops covering existing documents
    # until each is re-uploaded. Deployed routes/upload.py also reads and
    # writes this column, so running this downgrade under current code breaks
    # every upload -- roll the code back first.
    # DROP COLUMN takes ACCESS EXCLUSIVE: re-apply the C-12 cap so it cannot
    # queue unbounded behind a long transaction (migration review, MEDIUM).
    if ctx.dialect.name == "postgresql":
        op.execute("SET lock_timeout = '5s'")
    op.drop_column("documents", "content_sha256")
    if ctx.dialect.name == "postgresql":
        op.execute("RESET lock_timeout")
