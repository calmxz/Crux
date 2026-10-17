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


def test_nested_binding_restores_the_outer_bind(test_engine):
    inner = create_engine("sqlite:///:memory:")
    try:
        with bind_session_local(test_engine):
            with bind_session_local(inner):
                assert _bind() is inner
            assert _bind() is test_engine
    finally:
        inner.dispose()
