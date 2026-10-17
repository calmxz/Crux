"""Shared harness for the opt-in Postgres tests (#574).

The seed fixtures in conftest.py create a unique user + session per test and
tear them down with the plan built here. The plan is derived from the table
metadata, so a new table with a `user_id` or `session_id` column is covered
with no test edit, and a table the plan cannot reach fails loudly instead of
leaking rows.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import ColumnElement, MetaData, Table, or_
from sqlalchemy.orm import Session

import db.models  # noqa: F401  (registers every table on Base.metadata)

Predicate = Callable[[str, str], ColumnElement[bool]]


def _dependents(metadata: MetaData, roots: set[str]) -> set[str]:
    """Every table that FKs a root, directly or through other tables."""
    reached = set(roots)
    grew = True
    while grew:
        grew = False
        for table in metadata.tables.values():
            if table.name in reached:
                continue
            if any(fk.column.table.name in reached for fk in table.foreign_keys):
                reached.add(table.name)
                grew = True
    return reached


def _predicate(table: Table) -> Predicate:
    cols = table.c
    if table.name == "users":
        return lambda uid, sid: cols.id == uid

    def pred(uid: str, sid: str) -> ColumnElement[bool]:
        terms = []
        if "user_id" in cols:
            terms.append(cols.user_id == uid)
        if "session_id" in cols:
            terms.append(cols.session_id == sid)
        if table.name == "sessions":
            terms.append(cols.id == sid)
        return or_(*terms)

    return pred


def teardown_plan(metadata: MetaData) -> list[tuple[Table, Predicate]]:
    """Children-first deletes for every table tied to `users` or `sessions`,
    ending with `sessions` then `users`. Raises if a dependent table has
    neither a `user_id` nor a `session_id` column to delete by."""
    reached = _dependents(metadata, {"users", "sessions"})
    plan = []
    for table in reversed(metadata.sorted_tables):
        if table.name not in reached:
            continue
        if table.name not in ("users", "sessions") and not (
            {"user_id", "session_id"} & set(table.c.keys())
        ):
            raise ValueError(
                f"teardown cannot reach table {table.name!r}: it depends on users/sessions"
                " but has no user_id or session_id column"
            )
        plan.append((table, _predicate(table)))
    return plan


def run_teardown(db: Session, plan: list[tuple[Table, Predicate]], uid: str, sid: str) -> None:
    """Delete every row the plan ties to uid/sid, in one transaction. Any
    error (an FK violation from a row the plan missed) propagates."""
    for table, pred in plan:
        db.execute(table.delete().where(pred(uid, sid)))
    db.commit()
