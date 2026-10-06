"""Batch 6: F-50 issuer normalization, F-57 CORS, F-61 auth fail-fast."""
import pytest

from config import settings
from services import auth as auth_service


def test_issuer_ignores_trailing_slash(monkeypatch):
    """F-50: a trailing slash on SUPABASE_URL must not change the issuer."""
    monkeypatch.setattr(settings, "supabase_url", "https://proj.supabase.co/")
    assert auth_service.expected_issuer() == "https://proj.supabase.co/auth/v1"
    monkeypatch.setattr(settings, "supabase_url", "https://proj.supabase.co")
    assert auth_service.expected_issuer() == "https://proj.supabase.co/auth/v1"


def test_startup_refuses_unconfigured_auth(monkeypatch):
    """F-61: missing SUPABASE_URL must refuse boot unless AUTH_OPTIONAL=true."""
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_jwks_url_override", "")
    monkeypatch.setattr(settings, "auth_optional", False)
    with pytest.raises(RuntimeError, match="auth is not configured"):
        auth_service.validate_jwks_startup()


def test_startup_allows_opt_out(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_jwks_url_override", "")
    monkeypatch.setattr(settings, "auth_optional", True)
    auth_service.validate_jwks_startup()  # must not raise


def test_cors_disallows_credentials():
    """F-57: Bearer auth needs no credentialed CORS."""
    from main import app
    cors = next(
        m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware"
    )
    assert cors.kwargs.get("allow_credentials") is False


def test_accepted_terms_from_request_reads_user_metadata():
    from types import SimpleNamespace

    from services import auth as auth_service

    req = SimpleNamespace(state=SimpleNamespace(
        jwt_claims={"user_metadata": {"accepted_terms": True}}
    ))
    assert auth_service.accepted_terms_from_request(req) is True

    req2 = SimpleNamespace(state=SimpleNamespace(jwt_claims={}))
    assert auth_service.accepted_terms_from_request(req2) is False

    req3 = SimpleNamespace(state=SimpleNamespace())  # no claims attr
    assert auth_service.accepted_terms_from_request(req3) is False
