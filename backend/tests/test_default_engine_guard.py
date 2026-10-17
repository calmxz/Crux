"""#579: the conftest guard refuses and records a connection on the default
engine, so a best-effort path that swallows the refusal still fails its test."""

import pytest

from db.database import SessionLocal
from tests import conftest


def test_default_engine_connection_is_refused_and_recorded(request):
    db = SessionLocal()
    try:
        with pytest.raises(RuntimeError, match="default engine"):
            db.connection()
    finally:
        db.close()

    assert conftest._default_engine_hits == [request.node.nodeid]
    # Cleared, so this test's own teardown check passes.
    conftest._default_engine_hits.clear()
