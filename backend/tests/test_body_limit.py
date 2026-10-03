"""C-03: reject oversized non-multipart request bodies before parsing.

Two layers of test here:

* Through the app's TestClient, for the integration contract (status, detail
  shape, multipart exemption, pass-through of normal bodies).
* Against the raw ASGI interface, because Starlette's TestClient collapses
  any request body into a single `http.request` message -- it cannot express
  a chunked upload, and it cannot prove that a streaming *response* is passed
  through uncoalesced. Those two properties are the reason this middleware is
  pure ASGI rather than BaseHTTPMiddleware (SSE on /chat/stream must stay
  unbuffered), so they get direct coverage.
"""

import json

import pytest

from config import settings
from contracts import TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from lib.body_limit import BodySizeLimitMiddleware

MAX = settings.max_json_body_bytes

SESSION_ID = "sess_body_limit"
USER_ID = "u_body_limit"


def _json_body_of_size(total: int) -> bytes:
    """A syntactically valid JSON object of exactly `total` bytes."""
    envelope = b'{"message":"' + b'"}'
    filler = total - len(envelope)
    assert filler > 0
    return b'{"message":"' + b"x" * filler + b'"}'


@pytest.fixture
def seeded_session(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    return SESSION_ID


# --- through the app -------------------------------------------------------


def test_oversized_json_body_is_rejected_before_the_route_runs(
    client, db_session, seeded_session
):
    body = _json_body_of_size(MAX + 1)
    resp = client.post(
        "/api/chat/stream",
        content=body,
        headers={
            "content-type": "application/json",
            "Authorization": f"Bearer test-{USER_ID}",
        },
    )
    assert resp.status_code == 413
    assert resp.json() == {
        "detail": {"code": "body_too_large", "max_bytes": MAX}
    }
    # The handler never ran, so it persisted nothing.
    assert db_session.query(ChatMessage).count() == 0


def test_413_carries_cors_headers_for_a_browser_client(client, seeded_session):
    """C-03: the limit must sit INSIDE CORSMiddleware. Rejected from outside
    it, the 413 carries no access-control-allow-origin, so a cross-origin
    browser client (Vercel -> Render) sees an opaque CORS error instead of
    the body_too_large payload."""
    body = _json_body_of_size(MAX + 1)
    resp = client.post(
        "/api/chat/stream",
        content=body,
        headers={
            "content-type": "application/json",
            "Origin": "http://localhost:5173",
            "Authorization": f"Bearer test-{USER_ID}",
        },
    )
    assert resp.status_code == 413
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_body_of_exactly_the_limit_is_not_rejected(client, seeded_session):
    """The boundary is inclusive: max_bytes passes, max_bytes + 1 does not."""
    body = _json_body_of_size(MAX)
    resp = client.post(
        "/api/chat/stream",
        content=body,
        headers={
            "content-type": "application/json",
            "Authorization": f"Bearer test-{USER_ID}",
        },
    )
    assert resp.status_code != 413


def test_multipart_upload_is_exempt_from_this_gate(client, seeded_session):
    """Uploads are legitimately large; routes/upload.py owns their own size
    gate (and may answer 413 itself), so this middleware must not be the one
    rejecting them."""
    blob = b"x" * (MAX + 1024)
    resp = client.post(
        "/api/upload",
        data={"session_id": SESSION_ID},
        files={"file": ("ref.txt", blob, "text/plain")},
        headers={"Authorization": f"Bearer test-{USER_ID}"},
    )
    detail = resp.json().get("detail") if resp.headers.get(
        "content-type", ""
    ).startswith("application/json") else None
    if isinstance(detail, dict):
        assert detail.get("code") != "body_too_large"


def test_normal_json_body_passes_through(client, seeded_session):
    resp = client.post(
        "/api/chat/stream",
        content=json.dumps({"session_id": "nope", "message": "x" * 2048}).encode(),
        headers={
            "content-type": "application/json",
            "Authorization": f"Bearer test-{USER_ID}",
        },
    )
    assert resp.status_code != 413


def test_get_with_no_body_passes_through(client):
    resp = client.get("/health")
    assert resp.status_code == 200


# --- raw ASGI --------------------------------------------------------------


async def _drive(app, scope, chunks):
    """Feed `chunks` to `app` as http.request messages; collect sent messages."""
    pending = list(chunks)
    sent: list[dict] = []

    async def receive():
        if pending:
            body = pending.pop(0)
            return {
                "type": "http.request",
                "body": body,
                "more_body": bool(pending),
            }
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    await app(scope, receive, send)
    return sent


def _scope(headers=None, method="POST"):
    return {
        "type": "http",
        "method": method,
        "path": "/api/chat/stream",
        "headers": headers if headers is not None else [
            (b"content-type", b"application/json")
        ],
    }


@pytest.mark.asyncio
async def test_chunked_body_without_content_length_is_rejected_on_crossing():
    """No Content-Length to trust, so the middleware counts as it streams and
    cuts the request off on the chunk that crosses the limit."""
    entered = []

    async def app(scope, receive, send):
        entered.append(True)
        while True:
            msg = await receive()
            if msg["type"] != "http.request" or not msg.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    wrapped = BodySizeLimitMiddleware(app, max_bytes=MAX)
    chunk = b"x" * (MAX // 2 + 16)
    sent = await _drive(wrapped, _scope(), [chunk, chunk, chunk])

    starts = [m for m in sent if m["type"] == "http.response.start"]
    assert len(starts) == 1
    assert starts[0]["status"] == 413
    payload = b"".join(
        m.get("body", b"") for m in sent if m["type"] == "http.response.body"
    )
    assert json.loads(payload) == {
        "detail": {"code": "body_too_large", "max_bytes": MAX}
    }
    # The app was entered (it had to start reading), but nothing it sent
    # afterwards may reach the client -- exactly one response.start.
    assert entered == [True]


@pytest.mark.asyncio
async def test_overflow_after_the_response_started_does_not_double_respond():
    """If the app has already begun responding, the middleware cannot send a
    413 any more; it ends the request stream instead of raising."""

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        while True:
            msg = await receive()
            if msg["type"] == "http.disconnect":
                break
            if not msg.get("more_body"):
                break
        await send({"type": "http.response.body", "body": b"done"})

    wrapped = BodySizeLimitMiddleware(app, max_bytes=MAX)
    chunk = b"x" * (MAX // 2 + 16)
    sent = await _drive(wrapped, _scope(), [chunk, chunk, chunk])

    starts = [m for m in sent if m["type"] == "http.response.start"]
    assert len(starts) == 1
    assert starts[0]["status"] == 200


@pytest.mark.asyncio
async def test_streaming_response_chunks_are_passed_through_uncoalesced():
    """The SSE guarantee: response bodies are forwarded one message at a time,
    never buffered into a single payload."""

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        for i in range(3):
            await send(
                {
                    "type": "http.response.body",
                    "body": f"event{i}".encode(),
                    "more_body": i < 2,
                }
            )

    wrapped = BodySizeLimitMiddleware(app, max_bytes=MAX)
    sent = await _drive(wrapped, _scope(), [b"{}"])

    bodies = [m for m in sent if m["type"] == "http.response.body"]
    assert [m["body"] for m in bodies] == [b"event0", b"event1", b"event2"]


@pytest.mark.asyncio
async def test_declared_content_length_over_the_limit_short_circuits():
    """A trustworthy Content-Length is rejected without the app ever running."""
    entered = []

    async def app(scope, receive, send):
        entered.append(True)

    wrapped = BodySizeLimitMiddleware(app, max_bytes=MAX)
    scope = _scope(
        headers=[
            (b"content-type", b"application/json"),
            (b"content-length", str(MAX + 1).encode()),
        ]
    )
    sent = await _drive(wrapped, scope, [])

    assert entered == []
    assert sent[0]["status"] == 413


@pytest.mark.asyncio
async def test_unparsable_content_length_falls_through_to_counting():
    entered = []

    async def app(scope, receive, send):
        entered.append(True)
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    wrapped = BodySizeLimitMiddleware(app, max_bytes=MAX)
    scope = _scope(
        headers=[
            (b"content-type", b"application/json"),
            (b"content-length", b"not-a-number"),
        ]
    )
    sent = await _drive(wrapped, scope, [b"{}"])

    assert entered == [True]
    assert sent[0]["status"] == 200


@pytest.mark.asyncio
async def test_multipart_content_type_is_exempt_at_the_asgi_layer():
    entered = []

    async def app(scope, receive, send):
        entered.append(True)
        await send({"type": "http.response.start", "status": 202, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    wrapped = BodySizeLimitMiddleware(app, max_bytes=MAX)
    scope = _scope(
        headers=[
            (b"content-type", b"Multipart/Form-Data; boundary=abc"),
            (b"content-length", str(MAX * 4).encode()),
        ]
    )
    sent = await _drive(wrapped, scope, [b"x" * (MAX + 1)])

    assert entered == [True]
    assert sent[0]["status"] == 202


@pytest.mark.asyncio
async def test_non_http_scope_passes_straight_through():
    seen = []

    async def app(scope, receive, send):
        seen.append(scope["type"])

    wrapped = BodySizeLimitMiddleware(app, max_bytes=MAX)
    await wrapped({"type": "lifespan"}, None, None)
    assert seen == ["lifespan"]
