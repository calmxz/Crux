"""TDD: migration 0010 chains onto the current head (0009)."""

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from db.database import Base
from db.models import Session as SessionModel
from db.models import User


def _load_migration():
    path = (
        Path(__file__).resolve().parents[1]
        / "db" / "alembic" / "versions" / "0010_subjects_lessons.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0010", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_0010_chains_onto_0009():
    mod = _load_migration()
    assert mod.revision == "0010_subjects_lessons"
    assert mod.down_revision == "0009_usage_counter_unique"


def test_session_rolling_summary_columns(db_session):
    """TDD: Session model has rolling_summary and rolling_summary_count columns."""
    user = User(id="test-user")
    db_session.add(user)
    db_session.flush()

    s = SessionModel(id="s-roll", user_id=user.id)
    db_session.add(s)
    db_session.commit()

    assert s.rolling_summary is None
    assert s.rolling_summary_count is None

    s.rolling_summary = "earlier we covered X"
    s.rolling_summary_count = 12
    db_session.commit()

    assert s.rolling_summary == "earlier we covered X"
    assert s.rolling_summary_count == 12


def _load_versions_module(filename: str, modname: str):
    path = (
        Path(__file__).resolve().parents[1]
        / "db" / "alembic" / "versions" / filename
    )
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_learning_events_created_at_index_declared_on_model():
    """F-07: the windowed review-queue scan filters on created_at, so the
    column needs its own index (ix_learning_events_session covers session_id
    only)."""
    from db.models import LearningEvent

    names = {ix.name for ix in LearningEvent.__table__.indexes}
    assert "ix_learning_events_created_at" in names


def test_documents_content_sha_index_declared_on_model():
    """C-08: the partial unique index that makes an identical re-upload a
    no-op must exist on the model, not only in the migration."""
    from db.models import Document

    names = {ix.name for ix in Document.__table__.indexes}
    assert "uq_documents_session_sha" in names
    assert "content_sha256" in Document.__table__.c


def test_chat_messages_sid_id_desc_index_declared_on_model():
    """F-09: session history is ordered by id DESC, which the existing
    (session_id, created_at) index cannot serve without a sort."""
    from db.models import ChatMessage

    names = {ix.name for ix in ChatMessage.__table__.indexes}
    assert "ix_chat_messages_sid_id_desc" in names


def _sqlite_engine():
    """Model-derived schema on in-memory SQLite -- the same shape every test
    fixture uses, and the only way to exercise the CHECK constraints without a
    live Postgres (the alembic chain itself is Postgres-only from 0003 on)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


# C-16: the five tables 0001_phase7_baseline created with a nullable,
# defaultless created_at. chunk_embeddings and llm_call_log are out of scope.
CREATED_AT_TABLES = ("users", "sessions", "learning_events", "documents", "chat_messages")


def test_0028_chains_onto_0027():
    mod = _load_versions_module("0028_created_at_and_checks.py", "migration_0028")
    assert mod.revision == "0028_created_at_and_checks"
    assert mod.down_revision == "0027_chat_messages_sid_id_desc"


def test_0028_covers_the_five_baseline_created_at_tables():
    """The migration and the model must agree on which tables move; a table
    tightened in one place only is silent schema drift."""
    mod = _load_versions_module("0028_created_at_and_checks.py", "migration_0028_tables")
    assert mod.CREATED_AT_TABLES == CREATED_AT_TABLES
    names = {name for _table, name, _expr in mod.CHECKS}
    assert names == {"documents_status_check", "chat_messages_role_check"}


def test_documents_status_check_declared_on_model():
    """C-15: documents.status had no CHECK, so a typo in any writer could
    persist a status no reader understands."""
    from db.models import Document

    checks = {
        c.name for c in Document.__table__.constraints if c.name is not None
    }
    assert "documents_status_check" in checks


def test_chat_messages_role_check_declared_on_model():
    """C-15: chat_messages.role had no CHECK even though status did."""
    from db.models import ChatMessage

    checks = {
        c.name for c in ChatMessage.__table__.constraints if c.name is not None
    }
    assert "chat_messages_role_check" in checks


@pytest.mark.parametrize("table", CREATED_AT_TABLES)
def test_created_at_is_not_null_with_server_default(table):
    """C-16: a row written outside the ORM must still get a timestamp."""
    insp = inspect(_sqlite_engine())
    col = {c["name"]: c for c in insp.get_columns(table)}["created_at"]
    assert col["nullable"] is False, f"{table}.created_at must be NOT NULL"
    assert col["default"] is not None, f"{table}.created_at needs a server default"


def test_created_at_filled_when_insert_omits_it():
    """The server default, not the ORM default, is what covers a raw INSERT.
    Read the value back as raw SQL: the column is timezone=True but SQLite's
    CURRENT_TIMESTAMP carries no offset, so an ORM round-trip would hand back
    a naive datetime -- a distraction from what this test is proving."""
    engine = _sqlite_engine()
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO chat_messages"
                " (session_id, role, content, tool_calls_json, citations_json)"
                " VALUES ('s1', 'user', 'hello', '[]', '[]')"
            )
        )
        conn.commit()
        value = conn.execute(
            text("SELECT created_at FROM chat_messages ORDER BY id DESC LIMIT 1")
        ).scalar()
    assert value is not None


def test_documents_status_check_rejects_unknown_status():
    engine = _sqlite_engine()
    with pytest.raises(IntegrityError):
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO documents (session_id, filename, status)"
                    " VALUES ('s1', 'notes.pdf', 'bogus')"
                )
            )
            conn.commit()


@pytest.mark.parametrize("status", ["pending", "processing", "ready", "failed"])
def test_documents_status_check_allows_every_live_value(status):
    """Every value any writer in backend/ can produce must still insert."""
    engine = _sqlite_engine()
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO documents (session_id, filename, status)"
                " VALUES ('s1', 'notes.pdf', :status)"
            ),
            {"status": status},
        )
        conn.commit()


def test_chat_messages_role_check_rejects_unknown_role():
    engine = _sqlite_engine()
    with pytest.raises(IntegrityError):
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO chat_messages"
                    " (session_id, role, content, tool_calls_json, citations_json)"
                    " VALUES ('s1', 'system', 'hello', '[]', '[]')"
                )
            )
            conn.commit()


@pytest.mark.parametrize("role", ["user", "assistant"])
def test_chat_messages_role_check_allows_every_live_value(role):
    engine = _sqlite_engine()
    with engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO chat_messages"
                " (session_id, role, content, tool_calls_json, citations_json)"
                " VALUES ('s1', :role, 'hello', '[]', '[]')"
            ),
            {"role": role},
        )
        conn.commit()


def test_0030_chains_onto_0029():
    mod = _load_versions_module("0030_learner_preferences.py", "migration_0030")
    assert mod.revision == "0030_learner_preferences"
    assert mod.down_revision == "0029_current_check"


def test_learner_preference_columns_default_on_bare_insert(db_session):
    """#356: a users row created without preferences gets the defaults."""
    db_session.add(User(id="pref-defaults"))
    db_session.commit()
    user = db_session.get(User, "pref-defaults")
    assert user.check_ins == "sometimes"
    assert user.reply_length == "balanced"


def test_0027_chains_onto_0026():
    mod = _load_versions_module(
        "0027_chat_messages_sid_id_desc.py", "migration_0027"
    )
    assert mod.revision == "0027_chat_messages_sid_id_desc"
    assert mod.down_revision == "0026_documents_content_sha256"


def test_0026_chains_onto_0025():
    mod = _load_versions_module(
        "0026_documents_content_sha256.py", "migration_0026"
    )
    assert mod.revision == "0026_documents_content_sha256"
    assert mod.down_revision == "0025_learning_events_created_at"


def test_0025_chains_onto_0024():
    mod = _load_versions_module(
        "0025_learning_events_created_at.py", "migration_0025"
    )
    assert mod.revision == "0025_learning_events_created_at"
    assert mod.down_revision == "0024_sessions_chunk_centroid"


def test_0024_chains_onto_0023():
    mod = _load_versions_module(
        "0024_sessions_chunk_centroid.py", "migration_0024"
    )
    assert mod.revision == "0024_sessions_chunk_centroid"
    assert mod.down_revision == "0023_worker_queue"


def test_revision_ids_fit_alembic_version_column():
    """alembic_version.version_num is varchar(32) on Postgres. A longer
    revision id passes every sqlite test and then fails `alembic upgrade
    head` live with "value too long for type character varying(32)"
    (caught by CI on PR #327 for a 35-char id)."""
    versions = Path(__file__).resolve().parents[1] / "db" / "alembic" / "versions"
    for path in sorted(versions.glob("0*.py")):
        spec = importlib.util.spec_from_file_location(f"chk_{path.stem}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert len(mod.revision) <= 32, f"{path.name}: revision id {mod.revision!r} exceeds 32 chars"
