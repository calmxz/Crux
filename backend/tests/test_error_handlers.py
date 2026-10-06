"""C-14: process-wide error handling, and the CORS layering it depends on.

The layering is the whole point. Starlette's ServerErrorMiddleware -- what
`app.add_exception_handler(Exception, ...)` feeds -- sits OUTSIDE every user
middleware, so a 500 written there skips CORSMiddleware and a browser reports
an opaque CORS failure instead of showing the body. The catch-all therefore has
to be a middleware registered inside CORS, and these tests assert the
`access-control-allow-origin` header on the error responses, not just the body.

Deliberately not the shared `client` fixture: these need
`raise_server_exceptions=False` and their own dependency overrides. The
overrides are installed on the real `main.app` so the real middleware stack is
what gets exercised, and removed again in the finally.
"""

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from contracts import ErrorResponse
from db.database import get_db
from lib.error_handlers import INTERNAL_ERROR_MESSAGE
from main import app
from services.auth import current_user_id

ORIGIN = "http://localhost:5173"
# Any authenticated GET works; this one resolves current_user_id before it
# touches the database.
PATH = "/api/sessions/library"
SECRET = "kaboom-internal-detail"


@contextmanager
def _client_whose_auth_raises(exc: Exception):
    def _boom():
        raise exc

    def _unused_db():
        yield None

    app.dependency_overrides[current_user_id] = _boom
    app.dependency_overrides[get_db] = _unused_db
    try:
        # raise_server_exceptions=False so a regression that stops the
        # middleware answering surfaces as a test failure, not a raised
        # exception from the client call.
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(current_user_id, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def unhandled_response():
    with _client_whose_auth_raises(RuntimeError(SECRET)) as c:
        yield c.get(PATH, headers={"Origin": ORIGIN})


@pytest.fixture
def value_error_response():
    with _client_whose_auth_raises(ValueError("topic must not be blank")) as c:
        yield c.get(PATH, headers={"Origin": ORIGIN})


def test_unhandled_exception_returns_coded_500(unhandled_response):
    assert unhandled_response.status_code == 500, unhandled_response.text
    detail = unhandled_response.json()["detail"]
    assert detail["code"] == "internal_error"
    assert detail["message"] == INTERNAL_ERROR_MESSAGE


def test_unhandled_500_body_matches_the_error_contract(unhandled_response):
    ErrorResponse.model_validate(unhandled_response.json())


def test_unhandled_500_does_not_leak_the_exception_text(unhandled_response):
    assert SECRET not in unhandled_response.text


def test_unhandled_500_carries_cors_headers(unhandled_response):
    """The layering guard: registered outside CORSMiddleware this is absent."""
    assert unhandled_response.headers.get("access-control-allow-origin") == ORIGIN


def test_unhandled_500_request_id_matches_the_header(unhandled_response):
    header_id = unhandled_response.headers.get("x-request-id")
    assert header_id
    assert unhandled_response.json()["detail"]["request_id"] == header_id


def test_value_error_subclass_is_a_500_not_a_422():
    """json.JSONDecodeError is a ValueError subclass but signals corrupt stored
    data, not a rejected input: it must fall through to internal_error."""
    import json

    exc = json.JSONDecodeError("corrupt kw_index_json", SECRET, 0)
    with _client_whose_auth_raises(exc) as c:
        resp = c.get(PATH, headers={"Origin": ORIGIN})
    assert resp.status_code == 500, resp.text
    assert resp.json()["detail"]["code"] == "internal_error"
    assert SECRET not in resp.text
    assert resp.headers.get("access-control-allow-origin") == ORIGIN


def test_value_error_returns_422_with_the_message(value_error_response):
    assert value_error_response.status_code == 422, value_error_response.text
    detail = value_error_response.json()["detail"]
    assert detail["code"] == "invalid_value"
    assert detail["message"] == "topic must not be blank"


def test_value_error_422_body_matches_the_error_contract(value_error_response):
    ErrorResponse.model_validate(value_error_response.json())


def test_value_error_422_carries_cors_headers(value_error_response):
    assert value_error_response.headers.get("access-control-allow-origin") == ORIGIN


def test_value_error_422_request_id_matches_the_header(value_error_response):
    header_id = value_error_response.headers.get("x-request-id")
    assert header_id
    assert value_error_response.json()["detail"]["request_id"] == header_id


def test_catch_all_is_registered_inside_cors():
    """add_middleware is last-registered-outermost, so the catch-all must sit
    at a LOWER index than CORSMiddleware in user_middleware."""
    from starlette.middleware.cors import CORSMiddleware

    from lib.body_limit import BodySizeLimitMiddleware
    from lib.error_handlers import UnhandledErrorMiddleware

    names = [mw.cls for mw in app.user_middleware]
    # user_middleware is ordered outermost-first.
    assert names.index(UnhandledErrorMiddleware) > names.index(CORSMiddleware)
    assert names.index(UnhandledErrorMiddleware) < names.index(BodySizeLimitMiddleware)


def test_healthy_request_is_unaffected(client):
    r = client.get("/health", headers={"Origin": ORIGIN})
    assert r.status_code == 200, r.text


# --- direct ASGI tests for the branches a route cannot reach ---


async def _never_receives():  # pragma: no cover - never awaited by these apps
    raise AssertionError("receive() should not be called")


async def test_exception_after_response_start_is_reraised():
    """A stream that dies mid-body already has its status line on the wire, so
    there is no way to answer 500. Re-raise rather than write a second
    response (an ASGI protocol violation) or silently truncate."""
    from lib.error_handlers import UnhandledErrorMiddleware

    sent = []

    async def collect(message):
        sent.append(message)

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"partial", "more_body": True})
        raise RuntimeError("died mid-stream")

    mw = UnhandledErrorMiddleware(app)
    with pytest.raises(RuntimeError, match="died mid-stream"):
        await mw(
            {"type": "http", "method": "GET", "path": "/api/chat/stream"},
            _never_receives,
            collect,
        )
    assert [m["type"] for m in sent] == ["http.response.start", "http.response.body"]


async def test_non_http_scope_passes_straight_through():
    from lib.error_handlers import UnhandledErrorMiddleware

    seen = []

    async def app(scope, receive, send):
        seen.append(scope["type"])

    async def collect(message):  # pragma: no cover - app never sends
        seen.append(message)

    await UnhandledErrorMiddleware(app)({"type": "lifespan"}, _never_receives, collect)
    assert seen == ["lifespan"]
