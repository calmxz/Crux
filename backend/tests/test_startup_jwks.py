"""S3.2: empty/unresolvable JWKS must kill startup, not 500 per request."""

import pytest
from fastapi.testclient import TestClient

import main
from config import settings
from services import auth


@pytest.fixture(autouse=True)
def _reset_jwks_cache():
    auth._JWKS_CACHE["client"] = None
    auth._JWKS_CACHE["fetched_at"] = 0.0
    yield
    auth._JWKS_CACHE["client"] = None
    auth._JWKS_CACHE["fetched_at"] = 0.0


@pytest.fixture(autouse=True)
def _no_create_tables(monkeypatch):
    # The lifespan's create_tables runs on the default engine (#579).
    monkeypatch.setattr(main, "create_tables", lambda: None)


def test_startup_boots_when_auth_disabled(monkeypatch):
    # Disable auth by clearing supabase_url -> supabase_jwks_url becomes "".
    # F-61: startup now fail-fasts on unconfigured auth unless AUTH_OPTIONAL
    # is explicitly set -- this test is exercising the opt-out path.
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "auth_optional", True)
    assert settings.supabase_jwks_url == ""
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200


def test_startup_fails_on_unreachable_jwks(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://proj.supabase.co")

    def boom(self):
        raise Exception("dns failure")

    monkeypatch.setattr(auth.PyJWKClient, "get_jwk_set", boom)
    with pytest.raises(RuntimeError, match="JWKS"):
        with TestClient(main.app):
            pass


def test_startup_warms_jwks_cache(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://proj.supabase.co")
    monkeypatch.setattr(auth.PyJWKClient, "get_jwk_set", lambda self: object())
    with TestClient(main.app):
        assert auth._JWKS_CACHE["client"] is not None
        assert auth._JWKS_CACHE["fetched_at"] > 0.0
