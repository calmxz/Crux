"""B-10: engine kwargs - pre_ping + explicit pool sizing on Postgres."""
from db import database


def test_postgres_engine_kwargs_have_pool_config():
    kw = database._build_engine_kwargs("postgresql+psycopg://u:p@h/db")
    assert kw["pool_pre_ping"] is True
    assert kw["pool_size"] >= 1
    assert kw["max_overflow"] >= 0
    assert kw["pool_recycle"] == 1800
    assert kw["connect_args"]["prepare_threshold"] is None


def test_postgres_engine_kwargs_have_pool_timeout():
    """F-01: pool exhaustion must shed load, not block for SQLAlchemy's 30s default."""
    from config import settings

    kw = database._build_engine_kwargs("postgresql+psycopg://u:p@h/db")
    assert kw["pool_timeout"] == settings.db_pool_timeout_s


def test_postgres_engine_kwargs_bound_the_connect():
    """G-07 follow-up: without connect_timeout a TCP-level DB hang is
    unbounded -- the /ready probe thread (and any sync route) would block
    holding a pool slot and an anyio limiter token until the OS gives up."""
    kw = database._build_engine_kwargs("postgresql://x")
    assert kw["connect_args"]["connect_timeout"] == 5


def test_sqlite_engine_kwargs_unchanged():
    kw = database._build_engine_kwargs("sqlite:///x.db")
    assert kw == {"connect_args": {"check_same_thread": False}}
    assert "connect_timeout" not in kw["connect_args"]
