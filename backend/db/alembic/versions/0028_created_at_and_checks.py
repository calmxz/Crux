"""created_at NOT NULL + defaults, documents.status / chat_messages.role CHECKs

Revision ID: 0028_created_at_and_checks
Revises: 0027_chat_messages_sid_id_desc
Create Date: 2026-09-21

Two QA re-triage Wave 4 items, one migration because both are pure schema
constraints over the same five tables.

C-16 -- created_at (users, sessions, chat_messages, learning_events,
documents). 0001_phase7_baseline created all five nullable with no server
default, and db/models.py only carried a Python-side `default=_utcnow`. So
any row written outside the ORM -- raw SQL, a partial restore, a future bulk
import -- could land with created_at NULL, and the sidebar ordering, the
review-queue window and the insights aggregation all silently drop or
mis-sort such a row. This backfills NULLs to now(), adds
`DEFAULT now()` and makes the column NOT NULL.

C-15 -- two CHECK constraints, mirroring the chat_messages_status_check that
0003 added:
  documents.status IN ('pending', 'processing', 'ready', 'failed')
      The ingestion state machine: routes/upload.py writes 'pending' (and
      'failed' for the reject-on-ingest-refusal row), worker.py writes
      'processing' and resets stuck rows to 'pending',
      services/ingestion_service.py writes 'ready' / 'failed'. The
      DocumentStatus contract (contracts/models.py) declares exactly these
      four. Legacy rows may still hold NULL; a CHECK admits NULL, and this
      migration deliberately does not change the column's nullability.
  chat_messages.role IN ('user', 'assistant')
      routes/chat.py persists the user turn, agent/tutor.py persists the
      assistant turn (including the F-14 partial-on-abort path). System and
      tool messages are assembled in memory for the LLM call and never
      persisted.

VALIDATE CONSTRAINT fails loudly if live data violates either set. That is
the point -- the PR owes a precheck (`SELECT DISTINCT status FROM
documents`, `SELECT DISTINCT role FROM chat_messages`, plus created_at NULL
counts) before this runs against Supabase.

C-12: `SET lock_timeout = '5s'` at the top so the ALTER TABLEs queue behind a
long-running transaction for at most five seconds rather than holding the
lock queue open behind them, and RESET at the end so a later revision in the
same `alembic upgrade head` run does not inherit the cap.

Lock honesty, for the record: alembic runs one revision inside one
transaction, and this revision needs none of the CONCURRENTLY machinery that
0025-0027 used autocommit_block for. So every ACCESS EXCLUSIVE lock taken
here is held until the revision commits, which means the ADD CONSTRAINT ...
NOT VALID / VALIDATE CONSTRAINT split does not shorten the blocking window
the way it would across separate transactions -- it is used because the
constraints are added to tables that already hold data and it keeps the
validating scan off the "must hold every lock while scanning" path if this
is ever re-run statement-by-statement. Splitting across commits would need
0026-style idempotency guards for a partially-applied revision; the five
tables are small at this scale, so atomicity wins.

Dialect branch: sqlite gets batch_alter_table (copy-and-move), Postgres gets
the raw statements. Note that the sqlite branch is effectively unreachable:
`alembic upgrade head` against sqlite already dies at 0003, which calls
op.create_check_constraint (NotImplementedError: "No support for ALTER of
constraints in SQLite dialect"). Every sqlite DB in this repo -- pytest
fixtures and local dev -- is built by Base.metadata.create_all from
db/models.py, which carries both CHECKs and the NOT NULL + server_default
directly. The branch is kept so the file is not Postgres-only by accident,
but if it ever does run, batch mode's table recreate does NOT restore
expression-based or partial indexes (uq_sessions_active_topic,
ix_chat_messages_sid_id_desc, uq_documents_session_sha all reflect as
"unsupported"); rebuild a sqlite dev DB from db/models.py instead.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028_created_at_and_checks"
down_revision: Union[str, None] = "0027_chat_messages_sid_id_desc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The five tables 0001_phase7_baseline created with a nullable, defaultless
# created_at. chunk_embeddings (0002) and llm_call_log (0014) are out of scope
# for this revision, and db/models.py leaves them as they are so model and
# schema stay in step.
# chat_messages is the hot table; it goes last so its ACCESS EXCLUSIVE lock
# (held to commit inside the single migration transaction) opens as late as
# possible, and its CHECK runs right after its ALTER (see upgrade()).
CREATED_AT_TABLES: tuple[str, ...] = (
    "users",
    "sessions",
    "learning_events",
    "documents",
    "chat_messages",
)

# (table, constraint name, CHECK expression). Names match db/models.py.
CHECKS: tuple[tuple[str, str, str], ...] = (
    (
        "documents",
        "documents_status_check",
        "status IN ('pending', 'processing', 'ready', 'failed')",
    ),
    (
        "chat_messages",
        "chat_messages_role_check",
        "role IN ('user', 'assistant')",
    ),
)


def upgrade() -> None:
    ctx = op.get_context()

    if ctx.dialect.name == "postgresql":
        op.execute("SET lock_timeout = '5s'")

        for table in CREATED_AT_TABLES:
            # Backfill first: SET NOT NULL rejects the whole ALTER if a single
            # row still holds NULL.
            op.execute(
                f"UPDATE {table} SET created_at = now() WHERE created_at IS NULL"
            )
            # One ALTER TABLE, so one lock acquisition per table.
            op.execute(
                f"ALTER TABLE {table} "
                "ALTER COLUMN created_at SET DEFAULT now(), "
                "ALTER COLUMN created_at SET NOT NULL"
            )
            # This table's CHECKs immediately after its ALTER, so no table
            # is re-locked later in the transaction.
            for check_table, name, expr in CHECKS:
                if check_table != table:
                    continue
                op.execute(
                    f"ALTER TABLE {table} ADD CONSTRAINT {name} "
                    f"CHECK ({expr}) NOT VALID"
                )
                op.execute(f"ALTER TABLE {table} VALIDATE CONSTRAINT {name}")

        op.execute("RESET lock_timeout")
        return

    # sqlite (see the docstring: unreachable through the chain, kept for
    # completeness). batch_alter_table recreates each table under a temp name
    # and moves the rows across.
    for table in CREATED_AT_TABLES:
        # Plain string like the Postgres branch: `table` is a module constant,
        # never user input, and semgrep blocks sa.text() on f-strings.
        op.execute(f"UPDATE {table} SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                "created_at",
                existing_type=sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )

    for table, name, expr in CHECKS:
        with op.batch_alter_table(table) as batch_op:
            batch_op.create_check_constraint(name, expr)


def downgrade() -> None:
    ctx = op.get_context()

    if ctx.dialect.name == "postgresql":
        op.execute("SET lock_timeout = '5s'")

        for table, name, _expr in CHECKS:
            op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")

        for table in CREATED_AT_TABLES:
            op.execute(
                f"ALTER TABLE {table} "
                "ALTER COLUMN created_at DROP NOT NULL, "
                "ALTER COLUMN created_at DROP DEFAULT"
            )

        op.execute("RESET lock_timeout")
        return

    for table, name, _expr in CHECKS:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(name, type_="check")

    for table in CREATED_AT_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(
                "created_at",
                existing_type=sa.DateTime(timezone=True),
                nullable=True,
                server_default=None,
            )
