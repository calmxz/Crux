"""F-18 backend half (#331): ETag / If-None-Match on hot GETs.

Route-level coverage through TestClient, plus direct ASGI drives for the two
properties a route test cannot observe: that a non-matching path is forwarded
message-by-message (never buffered, so SSE stays live) and that a multi-chunk
body hashes as one whole.
"""

import hashlib
from datetime import datetime, timezone
from decimal import Decimal

from starlette.middleware.cors import CORSMiddleware

from db.models import DailyCostLedger, User
from lib.etag import ETagMiddleware, _path_matches
from main import app

ORIGIN = "http://localhost:5173"
HOT_PREFIXES = ("/api/sessions", "/api/profile", "/api/review/queue", "/api/usage/summary")


def _seed_usage(db, user_id="test-user", cost="1.0000"):
    if not db.get(User, user_id):
        db.add(User(id=user_id))
    today = datetime.now(timezone.utc).date().isoformat()
    db.add(DailyCostLedger(user_id=user_id, date_utc=today, cost_usd=Decimal(cost)))
    db.commit()


def _new_session(client, topic="sql joins"):
    r = client.post("/api/sessions", json={"topic": topic, "seed_mode": "fresh"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# --- tagging -------------------------------------------------------------


def test_hot_get_carries_strong_etag_and_no_cache(client, db_session):
    _seed_usage(db_session)
    r = client.get("/api/usage/summary")
    assert r.status_code == 200
    etag = r.headers["etag"]
    assert etag.startswith('"') and etag.endswith('"')
    assert not etag.startswith("W/")
    assert len(etag) == 66  # 64 hex chars plus the two quotes
    assert r.headers["cache-control"] == "no-cache"


def test_same_body_yields_same_etag(client, db_session):
    _seed_usage(db_session)
    first = client.get("/api/usage/summary")
    second = client.get("/api/usage/summary")
    assert first.json() == second.json()
    assert first.headers["etag"] == second.headers["etag"]


def test_session_detail_and_profile_are_tagged(client, db_session):
    session_id = _new_session(client)
    assert client.get(f"/api/sessions/{session_id}").headers.get("etag")
    assert client.get(f"/api/profile/{session_id}").headers.get("etag")
    assert client.get("/api/sessions/library").headers.get("etag")
    assert client.get("/api/review/queue").headers.get("etag")


# --- conditional requests ------------------------------------------------


def test_matching_if_none_match_returns_304_with_no_body(client, db_session):
    _seed_usage(db_session)
    etag = client.get("/api/usage/summary").headers["etag"]
    r = client.get("/api/usage/summary", headers={"If-None-Match": etag})
    assert r.status_code == 304
    assert r.content == b""
    assert r.headers["etag"] == etag
    assert r.headers["cache-control"] == "no-cache"
    assert "content-length" not in r.headers
    assert "content-type" not in r.headers


def test_weak_prefixed_tag_matches(client, db_session):
    _seed_usage(db_session)
    etag = client.get("/api/usage/summary").headers["etag"]
    r = client.get("/api/usage/summary", headers={"If-None-Match": f"W/{etag}"})
    assert r.status_code == 304


def test_tag_in_comma_separated_list_matches(client, db_session):
    _seed_usage(db_session)
    etag = client.get("/api/usage/summary").headers["etag"]
    header = f'"deadbeef", W/"cafe", {etag}, "f00d"'
    r = client.get("/api/usage/summary", headers={"If-None-Match": header})
    assert r.status_code == 304


def test_star_matches(client, db_session):
    _seed_usage(db_session)
    r = client.get("/api/usage/summary", headers={"If-None-Match": "*"})
    assert r.status_code == 304


def test_non_matching_tag_returns_200_with_body(client, db_session):
    _seed_usage(db_session)
    r = client.get("/api/usage/summary", headers={"If-None-Match": '"not-the-tag"'})
    assert r.status_code == 200
    assert r.json()["today_spend_usd"] == 1.0
    assert r.headers.get("etag")


def test_mutation_changes_the_etag_and_stale_tag_gets_200(client, db_session):
    session_id = _new_session(client)
    before = client.get(f"/api/sessions/{session_id}").headers["etag"]
    assert client.get(
        f"/api/sessions/{session_id}", headers={"If-None-Match": before}
    ).status_code == 304

    r = client.patch(f"/api/sessions/{session_id}", json={"topic": "window functions"})
    assert r.status_code == 200, r.text

    after = client.get(f"/api/sessions/{session_id}")
    assert after.status_code == 200
    assert after.headers["etag"] != before

    stale = client.get(f"/api/sessions/{session_id}", headers={"If-None-Match": before})
    assert stale.status_code == 200
    assert stale.json()["topic"] == "window functions"


# --- scope ---------------------------------------------------------------


def test_non_allowlisted_path_is_untagged(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert "etag" not in r.headers


def test_404_on_an_allowlisted_prefix_is_untagged(client):
    r = client.get("/api/sessions/does-not-exist")
    assert r.status_code == 404
    assert "etag" not in r.headers
    assert r.json()["detail"] == "session not found"


def test_prefix_match_is_segment_wise():
    assert _path_matches("/api/sessions", HOT_PREFIXES)
    assert _path_matches("/api/sessions/abc", HOT_PREFIXES)
    assert _path_matches("/api/sessions/library", HOT_PREFIXES)
    assert not _path_matches("/api/sessionsx", HOT_PREFIXES)
    assert not _path_matches("/api/chat/stream", HOT_PREFIXES)
    assert not _path_matches("/api/usage/summary-extra", HOT_PREFIXES)


def test_post_is_never_buffered_or_tagged(client):
    r = client.post("/api/sessions", json={"topic": "graph theory", "seed_mode": "fresh"})
    assert r.status_code == 201
    assert "etag" not in r.headers


# --- CORS ----------------------------------------------------------------


def _cors_options():
    for mw in app.user_middleware:
        if mw.cls is CORSMiddleware:
            return mw.kwargs
    raise AssertionError("CORSMiddleware is not configured")


def test_cors_config_allows_if_none_match_and_exposes_etag():
    assert "If-None-Match" in _cors_options()["allow_headers"]
    assert "ETag" in _cors_options()["expose_headers"]


def test_cors_exposes_etag_header(client, db_session):
    _seed_usage(db_session)
    r = client.get("/api/usage/summary", headers={"Origin": ORIGIN})
    assert "etag" in r.headers.get("access-control-expose-headers", "").lower()


def test_cors_preflight_allows_if_none_match(client):
    r = client.options(
        "/api/sessions",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "if-none-match",
        },
    )
    assert r.status_code == 200, r.text
    assert "if-none-match" in r.headers.get("access-control-allow-headers", "").lower()


# --- direct ASGI drives --------------------------------------------------


async def _receive():  # pragma: no cover - never awaited by these apps
    raise AssertionError("receive() should not be called")


async def test_non_matching_path_is_forwarded_message_by_message():
    """The streaming guarantee: on a path outside the allowlist the app's own
    `send` is handed through, so each message reaches the server as it is
    produced rather than being held until the last chunk."""
    sent: list[dict] = []

    async def collecting_send(message):
        sent.append(message)

    async def streaming_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        assert len(sent) == 1, "start was buffered"
        await send({"type": "http.response.body", "body": b"a", "more_body": True})
        assert len(sent) == 2, "first chunk was buffered"
        await send({"type": "http.response.body", "body": b"b", "more_body": False})
        assert len(sent) == 3, "last chunk was buffered"

    scope = {"type": "http", "method": "GET", "path": "/api/chat/stream", "headers": []}
    await ETagMiddleware(streaming_app, prefixes=HOT_PREFIXES)(
        scope, _receive, collecting_send
    )
    assert len(sent) == 3


async def test_multi_chunk_body_hashes_as_one_whole():
    sent: list[dict] = []

    async def collecting_send(message):
        sent.append(message)

    async def chunked_app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": b'{"a":', "more_body": True})
        await send({"type": "http.response.body", "body": b"1}", "more_body": False})

    scope = {"type": "http", "method": "GET", "path": "/api/usage/summary", "headers": []}
    await ETagMiddleware(chunked_app, prefixes=HOT_PREFIXES)(
        scope, _receive, collecting_send
    )

    assert len(sent) == 2, "the tagged body must be coalesced into one message"
    headers = dict(sent[0]["headers"])
    expected = '"' + hashlib.sha256(b'{"a":1}').hexdigest() + '"'
    assert headers[b"etag"].decode() == expected
    assert headers[b"cache-control"] == b"no-cache"
    assert sent[1]["body"] == b'{"a":1}'


async def test_repeated_if_none_match_headers_are_joined():
    sent: list[dict] = []

    async def collecting_send(message):
        sent.append(message)

    async def app_200(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain"), (b"content-length", b"2")],
            }
        )
        await send({"type": "http.response.body", "body": b"hi", "more_body": False})

    etag = '"' + hashlib.sha256(b"hi").hexdigest() + '"'
    # Trailing empty entries and repeated headers are both legal on the wire.
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/profile/abc",
        "headers": [
            (b"if-none-match", b'"other", '),
            (b"if-none-match", etag.encode()),
        ],
    }
    await ETagMiddleware(app_200, prefixes=HOT_PREFIXES)(scope, _receive, collecting_send)

    assert sent[0]["status"] == 304
    headers = dict(sent[0]["headers"])
    assert b"content-length" not in headers
    assert b"content-type" not in headers
    assert headers[b"etag"].decode() == etag
    assert sent[1]["body"] == b""


async def test_existing_cache_control_is_not_overwritten():
    sent: list[dict] = []

    async def collecting_send(message):
        sent.append(message)

    async def app_with_cache_control(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"cache-control", b"private, max-age=30")],
            }
        )
        await send({"type": "http.response.body", "body": b"x", "more_body": False})

    scope = {"type": "http", "method": "GET", "path": "/api/review/queue", "headers": []}
    await ETagMiddleware(app_with_cache_control, prefixes=HOT_PREFIXES)(
        scope, _receive, collecting_send
    )
    values = [v for k, v in sent[0]["headers"] if k == b"cache-control"]
    assert values == [b"private, max-age=30"]


async def test_unknown_response_message_types_pass_through():
    """Anything that is neither a start nor a body message (HTTP trailers, for
    instance) is forwarded as-is rather than swallowed by the buffer."""
    sent: list[dict] = []

    async def collecting_send(message):
        sent.append(message)

    async def app_with_trailers(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"trailer", b"x-checksum")],
            }
        )
        await send({"type": "http.response.body", "body": b"z", "more_body": False})
        # ASGI trailers follow the final body message.
        await send({"type": "http.response.trailers", "headers": [(b"x-checksum", b"1")]})

    scope = {"type": "http", "method": "GET", "path": "/api/sessions", "headers": []}
    await ETagMiddleware(app_with_trailers, prefixes=HOT_PREFIXES)(
        scope, _receive, collecting_send
    )
    assert [m["type"] for m in sent] == [
        "http.response.start",
        "http.response.body",
        "http.response.trailers",
    ]


async def test_non_http_scope_passes_through():
    seen: list[str] = []

    async def ws_app(scope, receive, send):
        seen.append(scope["type"])

    await ETagMiddleware(ws_app, prefixes=HOT_PREFIXES)(
        {"type": "websocket", "path": "/api/sessions"}, _receive, None
    )
    assert seen == ["websocket"]
