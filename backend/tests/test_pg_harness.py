"""#574: the shared Postgres teardown plan, checked without a database."""

from __future__ import annotations

import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table

from db.database import Base
from tests.pg_harness import teardown_plan


def _names(plan) -> list[str]:
    return [table.name for table, _ in plan]


def test_plan_covers_every_table_and_orders_children_first():
    names = _names(teardown_plan(Base.metadata))

    # Every table today is tied to users or sessions; a new one must be too,
    # or this test makes someone decide.
    assert sorted(names) == sorted(Base.metadata.tables)
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

    assert sql("llm_call_log") == "llm_call_log.user_id = 'U' OR llm_call_log.session_id = 'S'"
    assert sql("chat_messages") == "chat_messages.session_id = 'S'"
    assert sql("sessions") == "sessions.user_id = 'U' OR sessions.id = 'S'"
    assert sql("users") == "users.id = 'U'"


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
