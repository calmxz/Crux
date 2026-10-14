"""#518: token verification against a JWKS served over HTTP, with no stub.

The Playwright e2e job signs in by pointing `supabase_jwks_url_override` at a
throwaway JWKS it serves itself. That works only because the production
verify path trusts exactly the keys in the configured JWKS. These tests run
the real PyJWKClient against a real HTTP JWKS and pin that contract: a token
signed by the served key passes, and a token signed by any other key gets a
401, even when it reuses the served key's `kid`.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from services import auth as auth_module
from services.auth import current_user_id, validate_jwks_startup

ISSUER_ORIGIN = "http://e2e-auth.invalid"
KID = "e2e-test-key"


def _rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def served_key() -> rsa.RSAPrivateKey:
    return _rsa_key()


@pytest.fixture(scope="module")
def jwks_url(served_key):
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(served_key.public_key(), as_dict=True)
    body = json.dumps({"keys": [{**jwk, "kid": KID, "alg": "RS256", "use": "sig"}]}).encode()

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (stdlib hook name)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/jwks.json"
    server.shutdown()
    server.server_close()


@pytest.fixture
def client(monkeypatch, jwks_url):
    monkeypatch.setattr(auth_module.settings, "supabase_url", ISSUER_ORIGIN)
    monkeypatch.setattr(auth_module.settings, "supabase_jwks_url_override", jwks_url)
    monkeypatch.setitem(auth_module._JWKS_CACHE, "client", None)
    monkeypatch.setitem(auth_module._JWKS_CACHE, "fetched_at", 0.0)
    # The same boot check the e2e backend runs: fetches the served JWKS.
    validate_jwks_startup()

    app = FastAPI()

    @app.get("/whoami")
    def whoami(user_id: str = Depends(current_user_id)):
        return {"user_id": user_id}

    return TestClient(app)


def _token(key: rsa.RSAPrivateKey, kid: str = KID) -> str:
    now = int(time.time())
    claims = {
        "sub": "8d0f6a52-3c1e-4c55-9f3a-1d2b7e9c4a10",
        "aud": "authenticated",
        "iss": ISSUER_ORIGIN + "/auth/v1",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


def _get(client, token: str):
    return client.get("/whoami", headers={"Authorization": f"Bearer {token}"})


def test_token_signed_by_served_key_is_accepted(client, served_key):
    r = _get(client, _token(served_key))
    assert r.status_code == 200
    assert r.json() == {"user_id": "8d0f6a52-3c1e-4c55-9f3a-1d2b7e9c4a10"}


def test_foreign_key_reusing_served_kid_is_rejected(client):
    r = _get(client, _token(_rsa_key()))
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_token"


def test_foreign_key_with_unknown_kid_is_rejected(client):
    r = _get(client, _token(_rsa_key(), kid="not-in-the-jwks"))
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_token"
