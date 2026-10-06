"""F-46: onboarding state is server-persisted on the users row."""

import pytest

import routes.me as me_routes

H = {"Authorization": "Bearer test-me-user"}


def test_get_me_defaults(client):
    resp = client.get("/api/me", headers=H)
    assert resp.status_code == 200
    body = resp.json()
    assert body["onboarding_complete"] is False
    assert body["display_name"] is None


def test_get_me_existing_row_does_not_commit(client, monkeypatch):
    # Perf: GET /me sits on the frontend's render-blocking boot path. Once the
    # users row exists the read must not round-trip a COMMIT to the database.
    from sqlalchemy.orm import Session as OrmSession

    client.get("/api/me", headers=H)  # first call may create + commit

    calls = []
    orig = OrmSession.commit

    def counting(self):
        calls.append(1)
        return orig(self)

    monkeypatch.setattr(OrmSession, "commit", counting)
    resp = client.get("/api/me", headers=H)
    assert resp.status_code == 200
    assert calls == []


def test_get_me_learner_preference_defaults(client):
    # #356: a fresh account reports the effective defaults the tutor uses.
    body = client.get("/api/me", headers=H).json()
    assert body["feedback_pref"] == "hints"
    assert body["check_ins"] == "sometimes"
    assert body["reply_length"] == "balanced"


def test_patch_me_roundtrip(client):
    resp = client.patch(
        "/api/me",
        json={"display_name": "Ada", "feedback_pref": "direct_answers",
              "check_ins": "only_when_asked", "reply_length": "brief",
              "onboarding_complete": True},
        headers=H,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"display_name": "Ada", "feedback_pref": "direct_answers",
                    "check_ins": "only_when_asked", "reply_length": "brief",
                    "onboarding_complete": True}
    again = client.get("/api/me", headers=H)
    assert again.json()["onboarding_complete"] is True
    assert again.json()["check_ins"] == "only_when_asked"


@pytest.mark.parametrize("field", ["check_ins", "reply_length"])
def test_patch_me_single_preference_is_not_empty(client, field):
    value = {"check_ins": "often", "reply_length": "thorough"}[field]
    resp = client.patch("/api/me", json={field: value}, headers=H)
    assert resp.status_code == 200
    assert resp.json()[field] == value


@pytest.mark.parametrize(
    "field,value",
    [("feedback_pref", "direct"), ("check_ins", "always"), ("reply_length", "long")],
)
def test_patch_me_rejects_values_outside_enum(client, field, value):
    resp = client.patch("/api/me", json={field: value}, headers=H)
    assert resp.status_code == 422


def test_get_me_legacy_null_feedback_pref_reports_hints(client, db_session):
    # Pre-0020 rows keep feedback_pref NULL ("never set"); the effective
    # preference is still the default.
    from db.models import User

    client.get("/api/me", headers=H)
    user = db_session.get(User, "me-user")
    user.feedback_pref = None
    db_session.commit()
    assert client.get("/api/me", headers=H).json()["feedback_pref"] == "hints"


def test_patch_me_partial_keeps_other_fields(client):
    client.patch("/api/me", json={"display_name": "Ada"}, headers=H)
    client.patch("/api/me", json={"onboarding_complete": True}, headers=H)
    body = client.get("/api/me", headers=H).json()
    assert body["display_name"] == "Ada"
    assert body["onboarding_complete"] is True


def test_patch_me_empty_body_rejected(client):
    resp = client.patch("/api/me", json={}, headers=H)
    assert resp.status_code == 422


# --- DELETE /api/me (ticket 04) -------------------------------------------


VICTIM = "del-me"
OTHER = "del-other"
HV = {"Authorization": f"Bearer test-{VICTIM}"}


def _seed_user(db, user_id: str, store) -> dict:
    """Seed one row in every user-owned table; returns ids + the stored key."""
    from datetime import datetime, timezone
    from decimal import Decimal

    from config import settings
    from db.models import (
        ChatMessage,
        ChunkEmbedding,
        DailyCostLedger,
        Document,
        LearningEvent,
        LlmCallLog,
        Session,
        UsageCounter,
        User,
    )
    from services.object_store import key_for

    sid = f"s-{user_id}"
    db.add(User(id=user_id, created_at=datetime.now(timezone.utc)))
    db.add(Session(id=sid, user_id=user_id, topic=f"topic {user_id}"))
    db.flush()
    db.add(ChatMessage(session_id=sid, role="user", content="hi"))
    db.add(LearningEvent(session_id=sid, gap_tested="g", question="q", correct=True))
    doc = Document(session_id=sid, filename=f"{user_id}.pdf", status="ready")
    db.add(doc)
    db.flush()
    db.add(ChunkEmbedding(
        session_id=sid, document_id=doc.id, chunk_index=0, page=1,
        chunk_text="c", embedding=[0.0] * settings.embedding_dim,
    ))
    db.add(UsageCounter(user_id=user_id, date_utc="2026-09-23", count=3))
    db.add(DailyCostLedger(user_id=user_id, date_utc="2026-09-23",
                           cost_usd=Decimal("0.0100")))
    db.add(LlmCallLog(user_id=user_id, session_id=sid, purpose="chat",
                      model="m", cost_usd=Decimal("0.0010")))
    db.commit()
    key = key_for(doc.id, doc.filename)
    store.put(key, b"%PDF-fake")
    return {"sid": sid, "doc_id": doc.id, "key": key}


def _counts(db, user_id: str) -> dict:
    from sqlalchemy import func, select

    from db.models import (
        ChatMessage,
        ChunkEmbedding,
        DailyCostLedger,
        Document,
        LearningEvent,
        LlmCallLog,
        Session,
        UsageCounter,
        User,
    )

    sids = select(Session.id).where(Session.user_id == user_id)

    def n(stmt):
        return db.execute(stmt).scalar_one()

    return {
        "users": n(select(func.count()).select_from(User).where(User.id == user_id)),
        "sessions": n(select(func.count()).select_from(Session)
                      .where(Session.user_id == user_id)),
        "messages": n(select(func.count()).select_from(ChatMessage)
                      .where(ChatMessage.session_id.in_(sids))),
        "events": n(select(func.count()).select_from(LearningEvent)
                    .where(LearningEvent.session_id.in_(sids))),
        "documents": n(select(func.count()).select_from(Document)
                       .where(Document.session_id.in_(sids))),
        "chunks": n(select(func.count()).select_from(ChunkEmbedding)
                    .where(ChunkEmbedding.session_id == f"s-{user_id}")),
        "usage": n(select(func.count()).select_from(UsageCounter)
                   .where(UsageCounter.user_id == user_id)),
        "cost": n(select(func.count()).select_from(DailyCostLedger)
                  .where(DailyCostLedger.user_id == user_id)),
        "llm_log": n(select(func.count()).select_from(LlmCallLog)
                     .where(LlmCallLog.user_id == user_id)),
    }



@pytest.fixture
def store(tmp_path, monkeypatch):
    from config import settings
    from services.object_store import LocalDiskStore

    monkeypatch.setattr(settings, "uploads_store", "local")
    monkeypatch.setattr(settings, "uploads_path", str(tmp_path))
    return LocalDiskStore(str(tmp_path))


@pytest.fixture
def admin(monkeypatch):
    """Mock the Supabase admin boundary as imported by routes/me.py."""
    state = {"configured": True, "fail": False, "deleted": []}

    def fake_delete(user_id):
        if state["fail"]:
            raise me_routes.AuthAdminError("boom")
        state["deleted"].append(user_id)

    monkeypatch.setattr(me_routes, "admin_configured", lambda: state["configured"])
    monkeypatch.setattr(me_routes, "delete_auth_user", fake_delete)
    return state


def test_delete_me_503_when_admin_not_configured_touches_nothing(
    client, db_session, store, admin
):
    admin["configured"] = False
    seeded = _seed_user(db_session, VICTIM, store)
    before = _counts(db_session, VICTIM)

    resp = client.delete("/api/me", headers=HV)

    assert resp.status_code == 503
    assert resp.json()["detail"] == "auth admin not configured"
    db_session.expire_all()
    assert _counts(db_session, VICTIM) == before
    assert all(v == 1 for v in before.values())
    assert store.get(seeded["key"]) == b"%PDF-fake"
    assert admin["deleted"] == []


def test_delete_me_removes_all_caller_rows_and_objects_only(
    client, db_session, store, admin
):
    from services.object_store import ObjectNotFound

    victim = _seed_user(db_session, VICTIM, store)
    other = _seed_user(db_session, OTHER, store)

    resp = client.delete("/api/me", headers=HV)

    assert resp.status_code == 204
    assert resp.content == b""
    db_session.expire_all()
    assert all(v == 0 for v in _counts(db_session, VICTIM).values())
    assert all(v == 1 for v in _counts(db_session, OTHER).values())
    with pytest.raises(ObjectNotFound):
        store.get(victim["key"])
    assert store.get(other["key"]) == b"%PDF-fake"
    assert admin["deleted"] == [VICTIM]


def test_delete_me_503_names_auth_step_when_admin_call_fails(
    client, db_session, store, admin
):
    from services.object_store import ObjectNotFound

    admin["fail"] = True
    seeded = _seed_user(db_session, VICTIM, store)

    resp = client.delete("/api/me", headers=HV)

    assert resp.status_code == 503
    assert "auth user removal failed" in resp.json()["detail"]
    db_session.expire_all()
    assert all(v == 0 for v in _counts(db_session, VICTIM).values())
    with pytest.raises(ObjectNotFound):
        store.get(seeded["key"])


def test_delete_me_idempotent_for_user_with_no_rows(client, db_session, store, admin):
    resp = client.delete("/api/me", headers=HV)
    assert resp.status_code == 204
    again = client.delete("/api/me", headers=HV)
    assert again.status_code == 204
    assert admin["deleted"] == [VICTIM, VICTIM]


def test_delete_me_409_when_a_row_lands_mid_delete(client, db_session, store, admin, monkeypatch):
    # A streamed reply or chunk embedding written between the child deletes
    # and the sessions/users delete fails the FK; the whole transaction rolls
    # back and the learner is told to retry, not shown a 500.
    from sqlalchemy.exc import IntegrityError

    _seed_user(db_session, VICTIM, store)
    before = _counts(db_session, VICTIM)

    def boom(db, user_id):
        raise IntegrityError("insert", {}, Exception("fk"))

    monkeypatch.setattr(me_routes, "delete_user_account", boom)
    resp = client.delete("/api/me", headers=HV)
    assert resp.status_code == 409
    assert "try again" in resp.json()["detail"]
    assert _counts(db_session, VICTIM) == before
    assert admin["deleted"] == []


def test_delete_me_rejects_invalid_token(client, admin):
    resp = client.delete("/api/me", headers={"Authorization": "Bearer not-a-test-token"})
    assert resp.status_code == 401
    assert admin["deleted"] == []
