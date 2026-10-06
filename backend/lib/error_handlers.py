"""C-14: process-wide error handling.

Before this, nothing was registered: an unhandled exception fell through to
Starlette's ServerErrorMiddleware, which answers with a bare `Internal Server
Error` text body. Clients parsing the `ErrorResponse` contract
(`{"detail": {"code": ...}}`) got an unparseable body with no request id to
quote in a bug report.

Two layers, deliberately different mechanisms:

* `UnhandledErrorMiddleware` is pure ASGI and is registered INSIDE
  CORSMiddleware. `app.add_exception_handler(Exception, ...)` would NOT work
  here: that feeds ServerErrorMiddleware, which Starlette mounts OUTSIDE every
  user middleware, so its response never passes back through CORSMiddleware
  and a cross-origin browser client sees an opaque CORS failure instead of the
  body -- exactly the trap C-03 hit with the 413.
  Pure ASGI rather than BaseHTTPMiddleware because BaseHTTPMiddleware buffers
  responses, which would break SSE streaming on /chat/stream (same reason as
  lib/request_id.py and lib/body_limit.py).
* `ValueError` goes through the ordinary exception-handler mechanism.
  Starlette's ExceptionMiddleware runs INSIDE the user-middleware stack, so
  that response already passes through CORSMiddleware on its way out.
  Exact type only: pydantic's ValidationError and json.JSONDecodeError are
  ValueError subclasses, but an escaped one is usually server-side data
  corruption (a bad stored JSON blob), not a rejected input, so the handler
  re-raises anything that is not a plain ValueError and the catch-all above
  answers 500 internal_error instead.

Both bodies satisfy the ErrorResponse contract and carry the request id, which
is also on the X-Request-Id response header (RequestIdMiddleware is the
outermost layer, so it stamps even the responses written here).
"""

import json
import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from lib.request_id import request_id_var

log = logging.getLogger(__name__)

INTERNAL_ERROR_CODE = "internal_error"
INTERNAL_ERROR_MESSAGE = "Something went wrong."
INVALID_VALUE_CODE = "invalid_value"


def _internal_error_body(request_id: str) -> bytes:
    # Fixed message on purpose: str(exc) from an unhandled crash can carry
    # query fragments, file paths or learner text. The traceback goes to the
    # log; the client gets the request id to quote.
    return json.dumps(
        {
            "detail": {
                "code": INTERNAL_ERROR_CODE,
                "message": INTERNAL_ERROR_MESSAGE,
                "request_id": request_id,
            }
        }
    ).encode("utf-8")


async def _send_internal_error(send, request_id: str) -> None:
    payload = _internal_error_body(request_id)
    await send(
        {
            "type": "http.response.start",
            "status": 500,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})


class UnhandledErrorMiddleware:
    """Answer any exception the app did not handle with a coded 500.

    Register AFTER BodySizeLimitMiddleware and BEFORE CORSMiddleware: FastAPI's
    add_middleware is last-registered-outermost, so that slot puts this layer
    inside CORS (its 500 gets the CORS headers) and outside BodySizeLimit
    (whose internal control-flow exception and 413 never reach here).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        state = {"started": False}

        async def guarded_send(message):
            if message["type"] == "http.response.start":
                state["started"] = True
            await send(message)

        try:
            await self.app(scope, receive, guarded_send)
        except Exception:
            # asyncio.CancelledError derives from BaseException, so a client
            # disconnect is not swallowed here.
            request_id = request_id_var.get()
            log.exception(
                "unhandled error request_id=%s method=%s path=%s",
                request_id,
                scope.get("method", "-"),
                scope.get("path", "-"),
            )
            if state["started"]:
                # Status line already on the wire (a streaming response that
                # died mid-body). There is no way to send a 500 now; re-raise
                # and let the server tear the connection down, as today.
                raise
            await _send_internal_error(send, request_id)


async def value_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """An uncaught plain ValueError is a rejected input, not a server fault -> 422.

    Subclasses (pydantic ValidationError, json.JSONDecodeError, ...) re-raise
    so UnhandledErrorMiddleware reports them as 500 internal_error.
    """
    if type(exc) is not ValueError:
        raise exc
    request_id = request_id_var.get()
    log.warning(
        "invalid value request_id=%s method=%s path=%s: %s",
        request_id,
        request.method,
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": INVALID_VALUE_CODE,
                "message": str(exc),
                "request_id": request_id,
            }
        },
    )
