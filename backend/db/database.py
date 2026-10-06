import logging

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _normalized_url(url: str) -> str:
    """Force psycopg3 driver for bare postgresql:// URLs. SQLAlchemy defaults
    to psycopg2 otherwise, which we don't ship. Idempotent for explicit drivers."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def _build_engine_kwargs(url: str) -> dict:
    kwargs: dict = {}
    if url.startswith("sqlite:"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Supabase transaction-mode pooler (port 6543) multiplexes backends across
        # clients. psycopg3 names prepared statements `_pg3_N` per connection and
        # collides when the pooler hands the same backend to a new client. Disable
        # statement prepare entirely. See psycopg docs §"Pgbouncer".
        # G-07 follow-up: psycopg's connect_timeout (seconds) bounds the TCP
        # connect. Without it a DB-level hang is unbounded, so a probe or any
        # sync route blocks a worker thread -- holding an anyio limiter token
        # and a pool slot -- until the OS gives up.
        kwargs["connect_args"] = {
            "prepare_threshold": None,
            "connect_timeout": int(settings.db_connect_timeout_s),
        }
        # B-10: detect dead pooled connections after idle (pre_ping) and make
        # pool sizing explicit + env-tunable instead of SQLAlchemy defaults.
        kwargs["pool_pre_ping"] = True
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
        kwargs["pool_recycle"] = 1800
        # F-01: shed load instead of hanging 30 s (SQLAlchemy's default) on
        # pool exhaustion -- a fast 500 beats a queue of stalled requests.
        kwargs["pool_timeout"] = settings.db_pool_timeout_s
    return kwargs


_db_url = _normalized_url(settings.database_url)
_is_sqlite = _db_url.startswith("sqlite:")
_engine_kwargs = _build_engine_kwargs(_db_url)

engine = create_engine(_db_url, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Legacy idempotent column additions for pre-Alembic sqlite dev DBs.
# Postgres goes through Alembic (see backend/db/alembic/). This block is a
# no-op on Postgres because the columns are part of the baseline revision.
_MIGRATIONS: tuple[str, ...] = (
    "ALTER TABLE chat_messages ADD COLUMN tool_calls_json TEXT NOT NULL DEFAULT '[]'",
    "ALTER TABLE chat_messages ADD COLUMN citations_json TEXT NOT NULL DEFAULT '[]'",
    "ALTER TABLE sessions ADD COLUMN kw_index_json TEXT NOT NULL DEFAULT '[]'",
    "ALTER TABLE documents ADD COLUMN error TEXT",
    "ALTER TABLE documents ADD COLUMN page_count INTEGER",
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    # Postgres schema is owned by Alembic (backend/db/alembic/). Skipping
    # create_all here also avoids has_table() probes against the Supabase
    # pooler at boot, which can hit prepared-statement collisions.
    if not _is_sqlite:
        return
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for sql in _MIGRATIONS:
            try:
                conn.exec_driver_sql(sql)
            except OperationalError:
                # Column already present - these statements are idempotent
                # catch-up DDL for pre-Alembic sqlite dev DBs, so a duplicate
                # column error is the expected steady state.
                log.debug("legacy sqlite migration already applied: %s", sql)
