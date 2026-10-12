def test_response_carries_request_id(client):
    r = client.get("/health")
    rid = r.headers.get("x-request-id")
    assert rid is not None
    assert len(rid) == 16


def test_request_ids_are_unique(client):
    a = client.get("/health").headers["x-request-id"]
    b = client.get("/health").headers["x-request-id"]
    assert a != b


def test_cors_exposes_request_id(client):
    r = client.get("/health", headers={"Origin": "http://localhost:5173"})
    exposed = r.headers.get("access-control-expose-headers", "")
    assert "x-request-id" in exposed.lower()
