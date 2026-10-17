"""#580: one binding points every background session (SessionLocal) at a
test's engine, and restores the default bind when it ends."""

import pytest
from sqlalchemy import create_engine

from db.database import SessionLocal
from db.database import engine as default_engine
from tests.conftest import bind_session_local


@pytest.fixture
def test_engine():
    eng = create_engine("sqlite:///:memory:")
    yield eng
    eng.dispose()


def _bind():
    with SessionLocal() as db:
        return db.get_bind()


def test_binding_points_session_local_at_the_engine_then_restores(test_engine):
    with bind_session_local(test_engine):
        assert _bind() is test_engine
    assert _bind() is default_engine


def test_binding_restores_after_an_exception_inside(test_engine):
    with pytest.raises(ValueError), bind_session_local(test_engine):
        assert _bind() is test_engine
        raise ValueError("boom")
    assert _bind() is default_engine


def test_a_second_binding_is_refused_and_keeps_the_first(test_engine):
    other = create_engine("sqlite:///:memory:")
    try:
        with bind_session_local(test_engine):
            with pytest.raises(RuntimeError, match="already bound"), bind_session_local(other):
                pass
            assert _bind() is test_engine
        assert _bind() is default_engine
    finally:
        other.dispose()


def test_every_background_session_module_uses_the_shared_session_local():
    # One binding reaches them only while they all name this one object.
    import worker
    from routes import chat
    from services import ingestion_service, llm

    for module in (llm, chat, ingestion_service, worker):
        assert module.SessionLocal is SessionLocal, module.__name__
