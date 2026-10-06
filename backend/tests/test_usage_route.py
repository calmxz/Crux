from datetime import datetime, timezone
from decimal import Decimal

from db.models import DailyCostLedger, User


def _seed_today(db, user_id="test-user", cost="1.0000"):
    if not db.get(User, user_id):
        db.add(User(id=user_id))
    today = datetime.now(timezone.utc).date().isoformat()
    db.add(DailyCostLedger(user_id=user_id, date_utc=today, cost_usd=Decimal(cost)))
    db.commit()


def test_usage_summary_shape(client, db_session):
    _seed_today(db_session)
    r = client.get("/api/usage/summary")
    assert r.status_code == 200
    body = r.json()
    assert len(body["daily"]) == 14
    assert body["today_spend_usd"] == 1.0
    assert body["soft_cap_usd"] == 2.0
    assert body["urgent_cap_usd"] == 2.7
    assert body["hard_cap_usd"] == 3.0
    assert body["top_sessions"] == []
    resets_at = datetime.fromisoformat(body["resets_at"])
    assert resets_at.tzinfo is not None
    assert (resets_at.hour, resets_at.minute, resets_at.second) == (0, 0, 0)
    assert resets_at > datetime.now(timezone.utc)


def test_usage_summary_rejects_invalid_token(client, db_session):
    r = client.get(
        "/api/usage/summary", headers={"Authorization": "Bearer bogus"}
    )
    assert r.status_code == 401


def test_usage_summary_makes_no_llm_call(client, db_session, monkeypatch):
    import litellm

    def _boom(*args, **kwargs):
        raise AssertionError("usage path must not call the LLM")

    monkeypatch.setattr(litellm, "acompletion", _boom, raising=False)
    monkeypatch.setattr(litellm, "completion", _boom, raising=False)
    _seed_today(db_session)
    assert client.get("/api/usage/summary").status_code == 200


def test_usage_summary_user_isolation(client, db_session):
    _seed_today(db_session, user_id="other-user", cost="9.0000")
    r = client.get("/api/usage/summary")
    assert r.json()["today_spend_usd"] == 0.0
