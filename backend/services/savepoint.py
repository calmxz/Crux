"""Core-level SAVEPOINT for best-effort reads on the request session.

Leaf module: pgvector_store, prompt_state and retrieval_service import it.
"""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session


@contextmanager
def core_savepoint(db: Session) -> Generator[None]:
    """Run the block inside a SAVEPOINT; on an exception roll back to it and
    re-raise. The caller catches and logs.

    On Postgres a failed statement aborts the whole transaction, so a plain
    try/except around a best-effort read does not contain the failure: the
    next statement on the session raises InFailedSqlTransaction. Rolling back
    to the savepoint undoes only what the block did.

    The savepoint is taken at Core level (`db.connection().begin_nested()`)
    rather than via `Session.begin_nested()`, which unconditionally flushes
    pending ORM state regardless of autoflush. The request session runs with
    autoflush=False by design; forcing a flush here would surface an
    unrelated write error as a failure of the read.

    No dialect guard: on sqlite the savepoint is harmless, and the chat
    statement budget then counts what Postgres pays (#565). A connection-level
    failure (dropped connection, pooler reset) is beyond what a savepoint can
    save.
    """
    with db.connection().begin_nested():
        yield
