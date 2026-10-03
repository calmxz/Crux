"""Supabase JWT verification + FastAPI auth dependency.

JWKS is fetched lazily from `settings.supabase_jwks_url` on first verify call
and cached in-process. Tokens are validated against the cached keys; on
unknown `kid`, JWKS is refetched once before failing.

For tests that don't want to hit Supabase, override the `current_user_id`
dependency on `app.dependency_overrides`.
"""
from __future__ import annotations

import threading
import time
from typing import Any

import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient

from config import settings

_JWKS_CACHE: dict[str, Any] = {"client": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 60 * 60  # refresh hourly
# F-19: serialises the refresh. Without it every concurrent request that
# observes the stale cache builds its own PyJWKClient (one JWKS fetch each).
_JWKS_LOCK = threading.Lock()
JWT_LEEWAY_SECONDS = 30  # F-41: absorb small backend-vs-Supabase clock skew


def expected_issuer() -> str:
    """F-50: issuer must come from the same normalized (rstripped) base the
    JWKS URL uses -- a trailing slash in SUPABASE_URL otherwise 401s every
    token with an issuer mismatch."""
    return settings.supabase_url.rstrip("/") + "/auth/v1"


def _jwks_cache_stale(now: float) -> bool:
    return (
        _JWKS_CACHE["client"] is None
        or now - _JWKS_CACHE["fetched_at"] > _JWKS_TTL_SECONDS
    )


def _new_jwks_client() -> PyJWKClient:
    """F-19: pin the cache settings instead of inheriting PyJWT's 300 s
    default lifespan, which would silently refetch JWKS 12x per hour."""
    return PyJWKClient(
        settings.supabase_jwks_url,
        cache_jwk_set=True,
        lifespan=_JWKS_TTL_SECONDS,
    )


def _get_jwks_client() -> PyJWKClient:
    # Lock-free fast path: a warm, fresh cache is the common case.
    if not _jwks_cache_stale(time.time()):
        return _JWKS_CACHE["client"]
    if not settings.supabase_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="auth_not_configured",
        )
    # F-19: double-checked -- whoever loses the lock race finds a fresh cache.
    with _JWKS_LOCK:
        if _jwks_cache_stale(time.time()):
            _JWKS_CACHE["client"] = _new_jwks_client()
            _JWKS_CACHE["fetched_at"] = time.time()
    return _JWKS_CACHE["client"]


def validate_jwks_startup() -> None:
    """Fail fast at boot when auth is configured but JWKS is unusable (S3.2).

    Auth is enabled iff `settings.supabase_jwks_url` is non-empty. A fetch
    failure here means every authenticated request would 500; dying at
    startup surfaces the misconfiguration immediately. On success the
    fetched client warms the per-process cache.
    """
    if not settings.supabase_jwks_url:
        if settings.auth_optional:
            return
        raise RuntimeError(
            "auth is not configured (SUPABASE_URL is empty) and AUTH_OPTIONAL "
            "is not set; refusing to boot a deploy where every authenticated "
            "request would fail (F-61)"
        )
    client = _new_jwks_client()
    try:
        client.get_jwk_set()
    except Exception as e:
        raise RuntimeError(
            f"JWKS fetch failed at startup ({settings.supabase_jwks_url}): {e}"
        ) from e
    _JWKS_CACHE["client"] = client
    _JWKS_CACHE["fetched_at"] = time.time()


def _decode_token(token: str) -> dict:
    """Verify a Supabase JWT and return the decoded payload, else raise 401.

    JWKS connectivity failures raise 503 (upstream outage, retryable);
    an unknown `kid` or any invalid token raises 401 (F-07).
    """
    try:
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            issuer=expected_issuer(),
            leeway=JWT_LEEWAY_SECONDS,
            options={"verify_aud": True, "verify_exp": True, "verify_iss": True},
        )
    except jwt.PyJWKClientConnectionError as e:
        # F-07: JWKS endpoint unreachable -- an upstream outage, not a bad
        # token. 503 keeps client retry semantics honest. Must precede the
        # PyJWKClientError arm (it is a subclass).
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_unavailable",
        ) from e
    except (jwt.PyJWKClientError, jwt.InvalidTokenError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
        ) from e
    return payload


def verify_supabase_jwt(token: str) -> str:
    """Return the Supabase user id (`sub`) for a valid JWT, else raise."""
    payload = _decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token"
        )
    return sub


def accepted_terms_from_request(request: Request) -> bool:
    """F-52: True iff the verified JWT carries the accepted_terms metadata
    claim the register form sets via signUp options.data. Direct-API signups
    that never saw the checkbox get no claim -> no consent stamp."""
    claims = getattr(request.state, "jwt_claims", None) or {}
    meta = claims.get("user_metadata") or {}
    return meta.get("accepted_terms") is True


def current_user_id(request: Request) -> str:
    """FastAPI dependency: extract bearer token, verify, return user id.

    Routes use `user_id: str = Depends(current_user_id)` instead of accepting
    `user_id` from the request body or form.
    """
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # `auth[7:]` skips the "Bearer " prefix matched above; safer than split
    # because `"Bearer "` (trailing space, no token) returns "" cleanly,
    # whereas split(None, 1)[1] raises IndexError on whitespace-only suffix.
    token = auth[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing_token",
        )
    payload = _decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_token",
        )
    # F-52: routes that create the users row read consent from the verified
    # claim, not from row-existence folklore.
    request.state.jwt_claims = payload
    return sub
