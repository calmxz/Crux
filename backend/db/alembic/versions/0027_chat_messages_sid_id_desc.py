"""index on chat_messages (session_id, id DESC) (F-09)

Revision ID: 0027_chat_messages_sid_id_desc
Revises: 0026_documents_content_sha256
Create Date: 2026-09-19

Session history is loaded newest-first (`routes/sessions.py`, ORDER BY
ChatMessage.id DESC LIMIT n within one session). The only existing index is
ix_chat_messages_session_created (session_id, created_at), which confines the
scan to the session but still leaves the planner a sort on id. A
(session_id, id DESC) index turns the page fetch into an index scan with no
sort. This query runs on every session open and on every resume.

Built with CREATE INDEX CONCURRENTLY: chat_messages takes a write on every
user message and every assistant turn, and a plain CREATE INDEX holds a
SHARE lock that blocks those for the duration. CONCURRENTLY cannot run
inside a transaction, hence the autocommit_block (same shape as
0025_learning_events_created_at).

Idempotency, both retry modes: if_not_exists / if_exists cover "index built
but alembic_version never stamped". A CONCURRENTLY build that fails part-way
leaves an INVALID index of the same name, and IF NOT EXISTS matches on name
only -- it would no-op and stamp the revision, leaving an index the planner
ignores but every INSERT still maintains. So the upgrade drops an invalid
namesake first (migration review, HIGH).

C-12: `SET lock_timeout = '5s'` -- chat_messages is the hottest table in the
schema, so bound the time this migration is willing to sit in the lock queue.
Session-level SET, not SET LOCAL, so it survives the commits that
autocommit_block performs. That is also why it is widened around the
concurrent statements and RESET afterwards:

  - CREATE/DROP INDEX CONCURRENTLY takes only SHARE UPDATE EXCLUSIVE, which
    never blocks an application read or write, so the 5s bound buys none of
    C-12's protection there. It does, however, govern the virtual-xid waits
    the concurrent build performs after each heap scan -- so any transaction
    open longer than 5s anywhere on the DB (the pg_dump backup cron holds one
    for its whole run) would abort the build and leave an INVALID index that
    every INSERT still maintains.
  - RESET afterwards so a later revision in the same `alembic upgrade head`
    run does not silently inherit a 5s cap on a genuine rewrite.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027_chat_messages_sid_id_desc"
down_revision: Union[str, None] = "0026_documents_content_sha256"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_chat_messages_sid_id_desc"


def upgrade() -> None:
    ctx = op.get_context()
    if ctx.dialect.name == "postgresql":
        op.execute("SET lock_timeout = '5s'")

    with ctx.autocommit_block():
        if ctx.dialect.name == "postgresql":
            # See the docstring: the concurrent build must not inherit the 5s
            # cap, or a single long-running transaction elsewhere on the DB
            # aborts it and strands an INVALID index on the hottest table.
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
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME} "
                f"ON chat_messages (session_id, id DESC)"
            )
        else:
            op.create_index(
                INDEX_NAME,
                "chat_messages",
                ["session_id", sa.text("id DESC")],
                unique=False,
                if_not_exists=True,
            )

    if ctx.dialect.name == "postgresql":
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
            table_name="chat_messages",
            if_exists=True,
            postgresql_concurrently=True,
        )

    if ctx.dialect.name == "postgresql":
        op.execute("RESET lock_timeout")
