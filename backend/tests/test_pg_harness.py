"""#574: the shared Postgres teardown plan, checked without a database."""

from __future__ import annotations

import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, create_engine

from db.database import Base
from tests import pg_harness
from tests.pg_harness import teardown_plan


def _names(plan) -> list[str]:
    return [table.name for table, _ in plan]


def test_plan_covers_every_table_and_orders_children_first():
    names = _names(teardown_plan(Base.metadata))

    for table in Base.metadata.tables.values():
        if {"user_id", "session_id"} & set(table.c.keys()):
            assert table.name in names
    assert names.index("chunk_embeddings") < names.index("documents")
    for table in Base.metadata.tables.values():
        if any(fk.column.table.name == "sessions" for fk in table.foreign_keys):
            assert names.index(table.name) < names.index("sessions"), table.name
    assert names[-1] == "users"


def test_plan_predicates_match_on_user_and_session():
    plan = dict((t.name, pred) for t, pred in teardown_plan(Base.metadata))

    def sql(name: str) -> str:
        return str(plan[name]("U", "S").compile(compile_kwargs={"literal_binds": True}))

    # Rows in any other session of uid go too, or deleting that session
    # would hit an FK.
    of_uid = "IN (SELECT sessions.id \nFROM sessions \nWHERE sessions.user_id = 'U')"
    assert sql("llm_call_log") == (
        f"llm_call_log.user_id = 'U' OR llm_call_log.session_id = 'S'"
        f" OR llm_call_log.session_id {of_uid}"
    )
    assert sql("chat_messages") == (
        f"chat_messages.session_id = 'S' OR chat_messages.session_id {of_uid}"
    )
    assert sql("sessions") == "sessions.user_id = 'U' OR sessions.id = 'S'"
    assert sql("users") == "users.id = 'U'"


def test_plan_covers_a_keyed_table_with_no_fk():
    md = MetaData()
    Table("users", md, Column("id", String, primary_key=True))
    Table("sessions", md, Column("id", String, primary_key=True), Column("user_id", String))
    Table("audit", md, Column("id", Integer, primary_key=True), Column("user_id", String))
    Table("settings", md, Column("key", String, primary_key=True))

    assert sorted(_names(teardown_plan(md))) == ["audit", "sessions", "users"]

    # A child of that keyed table with neither column is unreachable too.
    Table(
        "audit_notes",
        md,
        Column("id", Integer, primary_key=True),
        Column("audit_id", ForeignKey("audit.id")),
    )
    with pytest.raises(ValueError, match="'audit_notes'"):
        teardown_plan(md)


def test_plan_raises_on_a_table_it_cannot_reach():
    md = MetaData()
    Table("users", md, Column("id", String, primary_key=True))
    Table(
        "sessions",
        md,
        Column("id", String, primary_key=True),
        Column("user_id", ForeignKey("users.id")),
    )
    Table(
        "documents",
        md,
        Column("id", Integer, primary_key=True),
        Column("session_id", ForeignKey("sessions.id")),
    )
    Table(
        "pages",
        md,
        Column("id", Integer, primary_key=True),
        Column("document_id", ForeignKey("documents.id")),
    )

    with pytest.raises(ValueError, match="'pages'"):
        teardown_plan(md)


def _seeder_failing_on(monkeypatch, failing: set[str]):
    """A PgSeeder over three recorded seeds whose teardown fails for the
    uids in `failing`. Returns (seeder, uids attempted)."""
    attempted: list[str] = []

    def fake_run_teardown(db, plan, uid, sid):
        attempted.append(uid)
        if uid in failing:
            raise RuntimeError(f"teardown failed for {uid}")

    monkeypatch.setattr(pg_harness, "run_teardown", fake_run_teardown)
    # Never connects: run_teardown is faked and sessions open lazily.
    seeder = pg_harness.PgSeeder(create_engine("sqlite://"))
    seeder.seeds = [("u1", "s1"), ("u2", "s2"), ("u3", "s3")]
    return seeder, attempted


def test_teardown_attempts_every_seed_and_raises_the_one_failure(monkeypatch):
    seeder, attempted = _seeder_failing_on(monkeypatch, {"u1"})

    with pytest.raises(RuntimeError, match="u1"):
        seeder.teardown()
    assert attempted == ["u1", "u2", "u3"]


def test_teardown_raises_every_failure_as_a_group(monkeypatch):
    seeder, attempted = _seeder_failing_on(monkeypatch, {"u1", "u3"})

    with pytest.raises(ExceptionGroup) as exc:
        seeder.teardown()
    assert attempted == ["u1", "u2", "u3"]
    assert [str(e) for e in exc.value.exceptions] == [
        "teardown failed for u1",
        "teardown failed for u3",
    ]
