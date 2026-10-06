"""Real `current_user_id` dependency tests (Phase 7 T9).

Generates an RSA keypair in-process and patches `services.auth._get_jwks_client`
to return a stub PyJWKClient that vends the corresponding public key. Lets us
exercise the actual `jwt.decode` path (RS256, audience check, exp check) with
zero network access and no Supabase dependency.

Covers the happy path plus the failure modes the dependency must reject:
missing header, malformed scheme, expired, wrong audience, wrong signature,
missing `sub` claim.
"""

from __future__ import annotations

import threading
import time

import jwt
import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from services import auth
from services import auth as auth_module
from services.auth import accepted_terms_from_request, current_user_id

TEST_SUPABASE_URL = "https://test-project.supabase.co"

# Captured before the autouse patch_jwks_client fixture replaces the module
# attribute, so the F-19 concurrency test can exercise the real implementation.
_REAL_GET_JWKS_CLIENT = auth_module._get_jwks_client


@pytest.fixture(scope="module")
def rsa_keys() -> dict:
    """One keypair per test module; generation is ~100ms so worth caching."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return {"private_pem": private_pem, "public_key": public_key, "private_key": private_key}


@pytest.fixture(autouse=True)
def patch_jwks_client(monkeypatch, rsa_keys):
    """Stub _get_jwks_client so signing-key lookup returns our test public key.

    Also resets the module-level cache so a prior test's stub doesn't leak,
    and pins settings.supabase_url so the iss check has a stable value to
    validate against.
    """
    auth_module._JWKS_CACHE["client"] = None
    auth_module._JWKS_CACHE["fetched_at"] = 0.0
    monkeypatch.setattr(auth_module.settings, "supabase_url", TEST_SUPABASE_URL)

    class _FakeSigningKey:
        def __init__(self, key):
            self.key = key

    class _FakeJWKSClient:
        def __init__(self, public_key):
            self._public_key = public_key

        def get_signing_key_from_jwt(self, _token):
            return _FakeSigningKey(self._public_key)

    monkeypatch.setattr(
        auth_module,
        "_get_jwks_client",
        lambda: _FakeJWKSClient(rsa_keys["public_key"]),
    )


def _sign(rsa_keys: dict, *, sub: str = "user-123", aud: str = "authenticated",
          exp_offset: int = 3600, iss: str | None = None,
          extra: dict | None = None) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "aud": aud,
        "iss": iss if iss is not None else f"{TEST_SUPABASE_URL}/auth/v1",
        "iat": now,
        "exp": now + exp_offset,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, rsa_keys["private_pem"], algorithm="RS256")


@pytest.fixture
def app() -> FastAPI:
    """Minimal FastAPI app with a single auth-protected route to exercise
    the dependency through the full request lifecycle."""
    app = FastAPI()

    @app.get("/whoami")
    def whoami(user_id: str = Depends(current_user_id)) -> dict:
        return {"user_id": user_id}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_valid_token_returns_sub(client, rsa_keys):
    token = _sign(rsa_keys, sub="user-abc")
    r = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == {"user_id": "user-abc"}


@pytest.fixture
def consent_app() -> FastAPI:
    """F-52: a route mirroring the real chat.py/sessions.py wiring -- the
    real `current_user_id` dependency stashes `request.state.jwt_claims`,
    and the handler reads it back through `accepted_terms_from_request`.
    Proves the stash-to-helper wiring end-to-end at the FastAPI DI level,
    not just the SimpleNamespace unit tests in test_auth_config_batch6.py."""
    app = FastAPI()

    @app.get("/consent")
    def consent(request: Request, user_id: str = Depends(current_user_id)) -> dict:
        return {"user_id": user_id, "accepted_terms": accepted_terms_from_request(request)}

    return app


@pytest.fixture
def consent_client(consent_app: FastAPI) -> TestClient:
    return TestClient(consent_app)


def test_current_user_id_stash_reaches_accepted_terms_from_request_true(consent_client, rsa_keys):
    """A token whose user_metadata carries accepted_terms=true -> the claim
    stashed by current_user_id is visible to accepted_terms_from_request."""
    token = _sign(rsa_keys, extra={"user_metadata": {"accepted_terms": True}})
    r = consent_client.get("/consent", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == {"user_id": "user-123", "accepted_terms": True}


def test_current_user_id_stash_reaches_accepted_terms_from_request_false(consent_client, rsa_keys):
    """A token with no accepted_terms claim (direct-API signup bypassing the
    register checkbox) -> accepted_terms_from_request reads False, not a
    default that masks the missing claim."""
    token = _sign(rsa_keys)  # no user_metadata claim at all
    r = consent_client.get("/consent", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == {"user_id": "user-123", "accepted_terms": False}


def test_jwks_client_built_once_under_concurrent_refresh(monkeypatch):
    """F-19: when the cache is stale every concurrent request sees the stale
    read and, unguarded, builds its own PyJWKClient -- N JWKS fetches and N
    throwaway caches per refresh. Double-checked locking builds exactly one,
    and the constructor pins the cache settings instead of taking PyJWT's
    300 s default lifespan."""
    ctor_calls: list[dict] = []
    ctor_lock = threading.Lock()

    class _CountingJWKClient:
        def __init__(self, uri, **kwargs):
            with ctor_lock:
                ctor_calls.append({"uri": uri, **kwargs})
            # Widen the race window so an unlocked implementation loses.
            time.sleep(0.01)

    monkeypatch.setattr(auth_module, "PyJWKClient", _CountingJWKClient)
    auth_module._JWKS_CACHE["client"] = None
    auth_module._JWKS_CACHE["fetched_at"] = 0.0

    thread_count = 20
    barrier = threading.Barrier(thread_count)
    results: list[object] = []
    errors: list[Exception] = []

    def worker() -> None:
        try:
            barrier.wait()
            results.append(_REAL_GET_JWKS_CLIENT())
        except Exception as e:
            # Re-surfaced via the `assert not errors` below; a bare raise here
            # would die in the worker thread and leave the barrier deadlocked.
            errors.append(e)

    try:
        threads = [threading.Thread(target=worker) for _ in range(thread_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, errors
        assert len(ctor_calls) == 1, ctor_calls
        assert ctor_calls[0]["uri"] == auth_module.settings.supabase_jwks_url
        assert ctor_calls[0]["cache_jwk_set"] is True
        assert ctor_calls[0]["lifespan"] == 3600
        assert auth_module._JWKS_TTL_SECONDS == 3600
        # Every caller got the one cached instance.
        assert len({id(r) for r in results}) == 1
        assert len(results) == thread_count
    finally:
        auth_module._JWKS_CACHE["client"] = None
        auth_module._JWKS_CACHE["fetched_at"] = 0.0


def test_missing_authorization_header_returns_401(client):
    r = client.get("/whoami")
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_token"
    assert r.headers.get("www-authenticate") == "Bearer"


def test_non_bearer_scheme_returns_401(client, rsa_keys):
    token = _sign(rsa_keys)
    r = client.get("/whoami", headers={"Authorization": f"Basic {token}"})
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_token"


def test_empty_bearer_returns_401(client):
    r = client.get("/whoami", headers={"Authorization": "Bearer "})
    assert r.status_code == 401
    assert r.json()["detail"] == "missing_token"


def test_expired_token_returns_401(client, rsa_keys):
    token = _sign(rsa_keys, exp_offset=-60)
    r = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_token"


def test_wrong_audience_returns_401(client, rsa_keys):
    token = _sign(rsa_keys, aud="some-other-service")
    r = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_token"


def test_wrong_issuer_returns_401(client, rsa_keys):
    token = _sign(rsa_keys, iss="https://attacker.example.com/auth/v1")
    r = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_token"


def test_missing_sub_returns_401(client, rsa_keys):
    """Token signs cleanly but has no `sub` claim — must still be rejected."""
    now = int(time.time())
    token = jwt.encode(
        {"aud": "authenticated", "iat": now, "exp": now + 3600},
        rsa_keys["private_pem"],
        algorithm="RS256",
    )
    r = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_token"


def test_wrong_signature_returns_401(client, rsa_keys):
    """Token signed by an unrelated keypair must fail signature verification."""
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    now = int(time.time())
    token = jwt.encode(
        {"sub": "user-x", "aud": "authenticated", "iat": now, "exp": now + 3600},
        other_pem,
        algorithm="RS256",
    )
    r = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_token"


def test_malformed_token_returns_401(client):
    r = client.get(
        "/whoami", headers={"Authorization": "Bearer not.a.real.jwt"}
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_token"


def test_auth_not_configured_when_jwks_url_missing(monkeypatch, app, rsa_keys):
    """Restore the real `_get_jwks_client` and clear the URL — dependency
    must raise 500 `auth_not_configured` rather than crash with a None."""
    auth_module._JWKS_CACHE["client"] = None

    # Re-import the original function (the autouse fixture patched it; undo here).
    import importlib
    fresh = importlib.reload(auth_module)
    monkeypatch.setattr(fresh.settings, "supabase_url", "")
    monkeypatch.setattr(fresh.settings, "supabase_jwks_url_override", "")
    fresh._JWKS_CACHE["client"] = None

    # Re-bind the route to the freshly reloaded dependency, otherwise the
    # original module-level reference still points at the patched stub.
    app2 = FastAPI()

    @app2.get("/whoami")
    def whoami(user_id: str = Depends(fresh.current_user_id)) -> dict:
        return {"user_id": user_id}

    token = _sign(rsa_keys)
    c = TestClient(app2)
    r = c.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 500
    assert r.json()["detail"] == "auth_not_configured"

    # Restore module state for any later tests in the session.
    importlib.reload(auth_module)


class _RaisingJwksClient:
    def __init__(self, exc):
        self._exc = exc

    def get_signing_key_from_jwt(self, token):
        raise self._exc


def test_unknown_kid_returns_401_not_500(monkeypatch):
    """F-07: a spoofed/unknown kid is a bad token (401), not a server error."""
    monkeypatch.setattr(
        auth,
        "_get_jwks_client",
        lambda: _RaisingJwksClient(pyjwt.PyJWKClientError('Unable to find a signing key')),
    )
    with pytest.raises(HTTPException) as exc:
        auth.verify_supabase_jwt("h.p.s")
    assert exc.value.status_code == 401
    assert exc.value.detail == "invalid_token"


def test_jwks_connection_failure_returns_503(monkeypatch):
    """F-07: JWKS unreachable is an upstream outage (503), not invalid auth."""
    monkeypatch.setattr(
        auth,
        "_get_jwks_client",
        lambda: _RaisingJwksClient(pyjwt.PyJWKClientConnectionError("fetch failed")),
    )
    with pytest.raises(HTTPException) as exc:
        auth.verify_supabase_jwt("h.p.s")
    assert exc.value.status_code == 503
    assert exc.value.detail == "auth_unavailable"


def test_decode_called_with_leeway(monkeypatch):
    """F-41: 30s leeway absorbs backend-vs-Supabase clock skew at exp boundary."""

    class _Key:
        key = "test-key"

    class _Client:
        def get_signing_key_from_jwt(self, token):
            return _Key()

    captured = {}

    def _fake_decode(token, key, **kwargs):
        captured.update(kwargs)
        return {"sub": "user-1"}

    monkeypatch.setattr(auth, "_get_jwks_client", lambda: _Client())
    monkeypatch.setattr(auth.jwt, "decode", _fake_decode)
    assert auth.verify_supabase_jwt("h.p.s") == "user-1"
    assert captured["leeway"] == auth.JWT_LEEWAY_SECONDS == 30
