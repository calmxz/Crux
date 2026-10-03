"""Supabase Auth (GoTrue) admin API calls made with the backend secret key.

The `sb_secret_...` key (settings.supabase_secret_key) replaces the legacy
service_role key; it is backend-only and must never be logged or echoed.
"""

import uuid

import httpx

from config import settings

_TIMEOUT_S = 10.0


class AuthAdminError(Exception):
    """The admin API call failed (transport error or non-2xx other than 404)."""


def admin_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_secret_key)


def delete_auth_user(user_id: str) -> None:
    """Delete the Supabase auth user. 404 counts as success (already gone).

    Raises AuthAdminError on any other failure. Error messages carry only the
    status code -- never the key or the response body.
    """
    key = settings.supabase_secret_key
    # Supabase auth ids are UUIDs. Rebuilding the path segment from the parsed
    # value rejects anything else and never forwards the raw string.
    try:
        safe_user_id = str(uuid.UUID(user_id))
    except (ValueError, AttributeError, TypeError):
        raise AuthAdminError("auth admin delete refused: user id is not a UUID") from None
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{safe_user_id}"
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    try:
        resp = httpx.delete(url, headers=headers, timeout=_TIMEOUT_S)
    except httpx.HTTPError as exc:
        raise AuthAdminError(f"auth admin request failed: {type(exc).__name__}") from None
    if resp.status_code == 404 or 200 <= resp.status_code < 300:
        return
    raise AuthAdminError(f"auth admin delete returned HTTP {resp.status_code}")
