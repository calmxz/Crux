"""Shared harness for the opt-in Postgres tests (#574).

The `pg_seed` fixture in conftest.py hands each test a PgSeeder, which
creates a unique user + session and tears it down with the plan built here.
The plan is derived from the table metadata, so a new table with a `user_id`
or `session_id` column is covered with no test edit, and a table the plan
cannot reach fails loudly instead of leaking rows.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from sqlalchemy import ColumnElement, Engine, MetaData, Table, or_
from sqlalchemy.orm import Session, sessionmaker

from db.database import Base
from db.models import Session as SessionModel
from db.models import User

Predicate = Callable[[str, str], ColumnElement[bool]]
_KEYS = {"user_id", "session_id"}


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
    """Children-first deletes for every table with a `user_id` or `session_id`
    column or an FK path to `users`/`sessions`, ending with `users`. Raises
    if an FK-dependent table has neither column to delete by."""
    keyed = {t.name for t in metadata.tables.values() if _KEYS & set(t.c.keys())}
    reached = _dependents(metadata, {"users", "sessions"} | keyed)
    plan = []
    for table in reversed(metadata.sorted_tables):
        has_key = bool(_KEYS & set(table.c.keys()))
        if table.name not in reached and not has_key:
            continue
        if table.name not in ("users", "sessions") and not has_key:
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


class PgSeeder:
    """Call with an id prefix and Session fields to seed a unique user +
    session; returns (Session factory, uid, sid). teardown() removes every
    seed, then raises what failed (an ExceptionGroup if more than one)."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        self.plan = teardown_plan(Base.metadata)
        self.seeds: list[tuple[str, str]] = []

    def __call__(self, prefix: str, **session_fields):
        uid = f"{prefix}-{uuid.uuid4().hex[:12]}"
        sid = f"{prefix}-s-{uuid.uuid4().hex[:12]}"
        # Recorded first, so a seed that fails halfway is still torn down.
        self.seeds.append((uid, sid))
        with self.Session() as db:
            db.add(User(id=uid))
            db.flush()
            db.add(SessionModel(id=sid, user_id=uid, **session_fields))
            db.commit()
        return self.Session, uid, sid

    def teardown(self) -> None:
        errors: list[Exception] = []
        for uid, sid in self.seeds:
            try:
                with self.Session() as db:
                    run_teardown(db, self.plan, uid, sid)
            except Exception as e:
                errors.append(e)
        if len(errors) == 1:
            raise errors[0]
        if errors:
            raise ExceptionGroup("pg seed teardown failed", errors)
