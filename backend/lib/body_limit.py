"""C-03: reject oversized request bodies before anything tries to parse them.

Without this gate, a client can post an arbitrarily large JSON document and
the framework will buffer the whole thing in memory before the route's
validation ever sees it -- the size check has to happen upstream of parsing
to be worth anything.

Deliberately pure ASGI rather than BaseHTTPMiddleware: BaseHTTPMiddleware
buffers responses, which would break SSE streaming on /chat/stream. Mirrors
lib/request_id.py.

Multipart uploads are exempt by content-type (not by path): they are
legitimately far larger than any JSON body, and routes/upload.py enforces its
own MAX_UPLOAD_BYTES against both the declared Content-Length and the bytes
actually read.
"""

import json

_BODY_TOO_LARGE_CODE = "body_too_large"


class _BodyTooLarge(Exception):
    """Raised from the wrapped receive() once the 413 has been sent."""


class BodySizeLimitMiddleware:
    """Reject non-multipart request bodies larger than `max_bytes` with 413.

    Two checks, because neither alone is sufficient:

    * A declared Content-Length over the limit is rejected immediately, so an
      oversized body is never read off the socket at all.
    * The streamed bytes are counted as they arrive, which covers chunked
      requests (no Content-Length) and a client that lies about the length.
    """

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = int(max_bytes)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers") or []
        content_type = b""
        content_length = None
        for key, value in headers:
            lowered = key.lower()
            if lowered == b"content-type":
                content_type = value
            elif lowered == b"content-length":
                content_length = value

        if content_type.lower().lstrip().startswith(b"multipart/form-data"):
            await self.app(scope, receive, send)
            return

        if content_length is not None:
            try:
                declared = int(content_length)
            except (TypeError, ValueError):
                declared = None  # unparsable: fall through to counting
            if declared is not None and declared > self.max_bytes:
                await self._send_413(send)
                return

        state = {"received": 0, "response_started": False, "rejected": False}

        async def guarded_receive():
            message = await receive()
            if message["type"] != "http.request":
                return message
            state["received"] += len(message.get("body") or b"")
            if state["received"] <= self.max_bytes:
                return message
            if state["response_started"]:
                # Too late to send a status; end the request stream so the
                # app unwinds cleanly instead of blocking on more body.
                return {"type": "http.disconnect"}
            await self._send_413(send)
            state["rejected"] = True
            raise _BodyTooLarge()

        async def guarded_send(message):
            # Once the 413 is out, every message from the app is dropped.
            # FastAPI wraps body reading in its own `except Exception` and
            # would otherwise answer a second time, which is an ASGI protocol
            # violation ("multiple http.response.start messages").
            if state["rejected"]:
                return
            if message["type"] == "http.response.start":
                state["response_started"] = True
            await send(message)

        try:
            await self.app(scope, guarded_receive, guarded_send)
        except _BodyTooLarge:
            return

    async def _send_413(self, send) -> None:
        payload = json.dumps(
            {
                "detail": {
                    "code": _BODY_TOO_LARGE_CODE,
                    "max_bytes": self.max_bytes,
                }
            }
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})
