from types import SimpleNamespace

import pytest

from config import settings
from routes import health as health_route


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_alias(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_ok_when_db_reachable(client):
    """G-07: /health is a liveness probe (the process answers). /ready adds
    the dependency the process cannot serve traffic without."""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_unavailable_when_db_raises(client, monkeypatch):
    def boom(_db):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(health_route, "_probe", boom)

    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


class _FakeSession:
    """Records the SQL the probe issues, and which dialect it thinks it is on."""

    def __init__(self, dialect_name):
        self._bind = SimpleNamespace(dialect=SimpleNamespace(name=dialect_name))
        self.statements = []

    def get_bind(self):
        return self._bind

    def execute(self, stmt, params=None):
        self.statements.append(str(stmt))
        self.params = getattr(self, "params", []) + [params]
        return SimpleNamespace(scalar_one=lambda: 1)


def test_probe_bounds_the_statement_on_postgresql(monkeypatch):
    """G-07: the probe is bounded at the driver, not by abandoning the thread.

    asyncio.wait_for used to time the awaiter out while the worker thread kept
    running _probe on a Session that get_db was about to close -- and each
    abandoned thread held an anyio limiter token plus a pool slot. The bound
    now lives in the transaction: SET LOCAL statement_timeout, issued before
    the SELECT and in the same transaction.
    """
    monkeypatch.setattr(settings, "readiness_timeout_s", 2.0)
    db = _FakeSession("postgresql")

    health_route._probe(db)

    # set_config(..., true) is SET LOCAL with bind parameters (semgrep
    # avoid-sqlalchemy-text): the value never becomes SQL text.
    assert db.statements[0] == "SELECT set_config('statement_timeout', :v, true)"
    assert db.params[0] == {"v": "2000"}
    assert "SELECT 1" in db.statements[1]


def test_probe_does_not_set_statement_timeout_on_sqlite(monkeypatch):
    """SET LOCAL is Postgres-only syntax; sqlite (dev/CI) just round-trips."""
    monkeypatch.setattr(settings, "readiness_timeout_s", 2.0)
    db = _FakeSession("sqlite")

    health_route._probe(db)

    assert not any("statement_timeout" in s for s in db.statements)
    assert len(db.statements) == 1


@pytest.mark.parametrize("path", ["/health", "/healthz"])
def test_liveness_probes_do_not_touch_the_db(client, monkeypatch, path):
    def boom(_db):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(health_route, "_probe", boom)
    assert client.get(path).status_code == 200
