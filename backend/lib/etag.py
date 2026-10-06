"""F-18 backend half (#331): strong HTTP ETag / If-None-Match on hot GETs.

Pure ASGI, deliberately not BaseHTTPMiddleware -- that class buffers every
response through an anyio stream, which would break SSE on /chat/stream and
/sessions/{id}/check/complete (same reason as lib/request_id.py,
lib/body_limit.py and lib/error_handlers.py).

Only GET/HEAD on the allowlisted path prefixes are buffered and hashed; every
other scope is forwarded message-by-message with `send` untouched. Both SSE
routes today are POST, so they are never held -- a future streaming GET under
an allowlisted prefix would be buffered and must be excluded here first. The
tag is a strong sha256 of the exact
response body, so it needs no per-model `updated_at` plumbing and stays correct
for the endpoints that aggregate several rows into one payload.

Tagged 200s also get `cache-control: no-cache`, which means "revalidate before
reuse", not "do not store": without it a response carrying an ETag and no
freshness headers lets the browser heuristically reuse the cached body without
asking, and the client would never send the If-None-Match this layer exists to
answer.

Not to be confused with the `etag` field in the ProfileResponse *body*
(services/profile_service.profile_etag): that is an If-Match optimistic
concurrency token for profile writes and is unrelated to this header.
"""

import hashlib

CONDITIONAL_METHODS = frozenset({"GET", "HEAD"})

# Dropped from a 304: RFC 9110 requires no body, and a stale content-length
# would desynchronise the connection.
_STRIP_ON_304 = (b"content-length", b"content-type")


def _path_matches(path: str, prefixes: tuple[str, ...]) -> bool:
    """Segment-prefix match: /api/sessions covers /api/sessions and
    /api/sessions/abc, but not /api/sessionsx."""
    return any(path == p or path.startswith(p + "/") for p in prefixes)


def _if_none_match_matches(raw_values: list[bytes], etag: str) -> bool:
    """RFC 9110 If-None-Match, weak comparison.

    The header may repeat and each instance may hold a comma-separated list.
    `*` matches any existing representation; a `W/` prefix is stripped before
    comparing, because weak comparison is the rule for conditional GETs.
    """
    for raw in raw_values:
        for entry in raw.decode("latin-1").split(","):
            candidate = entry.strip()
            if not candidate:
                continue
            if candidate == "*":
                return True
            if candidate.startswith("W/"):
                candidate = candidate[2:].strip()
            if candidate == etag:
                return True
    return False


class ETagMiddleware:
    """Stamp a strong ETag on allowlisted GETs and answer 304 on a match."""

    def __init__(self, app, prefixes: tuple[str, ...] = ()):
        self.app = app
        self.prefixes = tuple(prefixes)

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope.get("method", "").upper() not in CONDITIONAL_METHODS
            or not _path_matches(scope.get("path", ""), self.prefixes)
        ):
            await self.app(scope, receive, send)
            return

        if_none_match = [
            value
            for name, value in (scope.get("headers") or ())
            if name.lower() == b"if-none-match"
        ]

        state: dict = {"start": None}
        chunks: list[bytes] = []

        async def send_buffered(message):
            message_type = message["type"]
            if message_type == "http.response.start":
                state["start"] = message
                return
            if message_type != "http.response.body":
                await send(message)
                return
            chunks.append(message.get("body", b"") or b"")
            if message.get("more_body", False):
                return
            await _flush(send, state["start"], b"".join(chunks), if_none_match)

        await self.app(scope, receive, send_buffered)


async def _flush(send, start, body: bytes, if_none_match: list[bytes]) -> None:
    if start is None:  # pragma: no cover - body before start is a broken app
        return
    headers = list(start.get("headers") or [])

    if start["status"] != 200:
        # Errors and redirects are forwarded untagged and unchanged.
        await send(start)
        await send({"type": "http.response.body", "body": body, "more_body": False})
        return

    etag = '"' + hashlib.sha256(body).hexdigest() + '"'
    headers = [h for h in headers if h[0].lower() != b"etag"]
    headers.append((b"etag", etag.encode("ascii")))
    if not any(h[0].lower() == b"cache-control" for h in headers):
        headers.append((b"cache-control", b"no-cache"))

    if _if_none_match_matches(if_none_match, etag):
        # A 304 repeats the headers the 200 would have carried (etag,
        # cache-control) and drops the entity ones.
        headers = [h for h in headers if h[0].lower() not in _STRIP_ON_304]
        await send({**start, "status": 304, "headers": headers})
        await send({"type": "http.response.body", "body": b"", "more_body": False})
        return

    await send({**start, "headers": headers})
    await send({"type": "http.response.body", "body": body, "more_body": False})
