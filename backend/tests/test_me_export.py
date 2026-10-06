"""#361: GET /api/me/export returns every learner-owned row as one JSON file."""

import json
from datetime import datetime, timedelta, timezone
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

ME = "exp-me"
OTHER = "exp-other"
H = {"Authorization": f"Bearer test-{ME}"}

T0 = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)


def _seed(db, user_id: str, *, topic_prefix: str = "") -> None:
    db.add(User(
        id=user_id, created_at=T0, display_name=f"{user_id} name",
        feedback_pref="direct_answers", check_ins="often", reply_length="brief",
        onboarding_complete=True, accepted_terms_at=T0, terms_version="v1",
    ))
    # Inserted newest first so the test proves the export sorts oldest first.
    db.add(Session(
        id=f"{user_id}-s2", user_id=user_id, topic=f"{topic_prefix}Joins",
        created_at=T0 + timedelta(days=2),
    ))
    db.add(Session(
        id=f"{user_id}-s1", user_id=user_id, topic=f"{topic_prefix}Indexes",
        created_at=T0 + timedelta(days=1), ended_at=T0 + timedelta(days=1, hours=1),
        pinned=True,
        topic_profile_json=json.dumps({
            "knowledge_level": "intermediate",
            "confirmed_gaps": ["b-trees"],
            "mastered_concepts": [{"name": "hash index", "evidence_type": "tested"}],
        }),
    ))
    db.flush()
    sid = f"{user_id}-s1"
    db.add(ChatMessage(session_id=sid, role="user", content=f"{user_id} asks"))
    db.add(ChatMessage(
        session_id=sid, role="assistant", content=f"{user_id} answers",
        citations_json=json.dumps([{"doc_id": "1", "text": "quote", "page": 3}]),
        tool_calls_json=json.dumps([{"name": "retrieve_chunks", "args": {}, "status": "ok"}]),
        status="complete",
    ))
    db.add(LearningEvent(
        session_id=sid, gap_tested="b-trees", question=f"{user_id} question?",
        correct=False, selected_index=0, correct_index=1,
        options_json=json.dumps(["a", "b"]), purpose="check",
    ))
    doc = Document(session_id=sid, filename=f"{user_id}.pdf", status="ready", page_count=12)
    db.add(doc)
    db.flush()
    db.add(ChunkEmbedding(
        session_id=sid, document_id=doc.id, chunk_index=0, page=1,
        chunk_text=f"{user_id} secret chunk", embedding=[0.0] * settings.embedding_dim,
    ))
    db.add(UsageCounter(user_id=user_id, date_utc="2026-09-02", count=4))
    db.add(UsageCounter(user_id=user_id, date_utc="2026-09-03", count=1))
    db.add(DailyCostLedger(user_id=user_id, date_utc="2026-09-02", cost_usd=Decimal("0.0125")))
    db.add(DailyCostLedger(user_id=user_id, date_utc="2026-09-04", cost_usd=Decimal("0.0030")))
    db.add(LlmCallLog(user_id=user_id, session_id=sid, purpose="chat",
                      model="internal-model-name", cost_usd=Decimal("0.0010")))
    db.commit()


def test_export_returns_the_whole_account_as_an_attachment(client, db_session):
    _seed(db_session, ME)

    resp = client.get("/api/me/export", headers=H)

    assert resp.status_code == 200
    disposition = resp.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="crux-export-')
    assert disposition.endswith('.json"')

    body = resp.json()
    assert body["format_version"] == 1
    # One clock: the filename day is exported_at's UTC day.
    assert disposition == f'attachment; filename="crux-export-{body["exported_at"][:10]}.json"'
    assert body["account"] == {
        "user_id": ME,
        "created_at": "2026-09-01T08:00:00Z",
        "display_name": f"{ME} name",
        "feedback_pref": "direct_answers",
        "check_ins": "often",
        "reply_length": "brief",
        "onboarding_complete": True,
        "accepted_terms_at": "2026-09-01T08:00:00Z",
        "terms_version": "v1",
    }

    assert [s["id"] for s in body["sessions"]] == [f"{ME}-s1", f"{ME}-s2"]
    s1 = body["sessions"][0]
    assert s1["topic"] == "Indexes"
    assert s1["pinned"] is True
    assert s1["ended_at"] == "2026-09-02T09:00:00Z"
    assert s1["topic_profile"]["knowledge_level"] == "intermediate"
    # Legacy bare-string concept entries come out in the v2 shape.
    assert s1["topic_profile"]["confirmed_gaps"][0]["name"] == "b-trees"
    assert s1["topic_profile"]["mastered_concepts"][0]["name"] == "hash index"

    assert [(m["role"], m["content"]) for m in s1["messages"]] == [
        ("user", f"{ME} asks"),
        ("assistant", f"{ME} answers"),
    ]
    assert s1["messages"][1]["citations"] == [
        {"doc_id": "1", "text": "quote", "page": 3, "doc_name": None}
    ]
    assert s1["messages"][1]["status"] == "complete"

    [answer] = s1["check_answers"]
    assert answer["question"] == f"{ME} question?"
    assert answer["options"] == ["a", "b"]
    assert answer["selected_index"] == 0
    assert answer["correct_index"] == 1
    assert answer["correct"] is False

    [doc] = s1["documents"]
    assert doc["filename"] == f"{ME}.pdf"
    assert doc["status"] == "ready"
    assert doc["page_count"] == 12

    s2 = body["sessions"][1]
    assert s2["messages"] == [] and s2["check_answers"] == [] and s2["documents"] == []

    # Counters and the cost ledger are merged per day; either side may be missing.
    assert body["usage"] == [
        {"date_utc": "2026-09-02", "messages": 4, "cost_usd": 0.0125},
        {"date_utc": "2026-09-03", "messages": 1, "cost_usd": 0.0},
        {"date_utc": "2026-09-04", "messages": 0, "cost_usd": 0.003},
    ]


def test_export_leaves_out_internal_state(client, db_session):
    _seed(db_session, ME)

    resp = client.get("/api/me/export", headers=H)
    text = resp.text

    assert resp.status_code == 200
    assert "secret chunk" not in text
    assert "internal-model-name" not in text
    assert "retrieve_chunks" not in text


def test_export_never_includes_another_learners_rows(client, db_session):
    _seed(db_session, ME)
    _seed(db_session, OTHER, topic_prefix="Other ")

    resp = client.get("/api/me/export", headers=H)
    text = resp.text

    assert resp.status_code == 200
    assert ME in text
    assert OTHER not in text
    assert "Other " not in text


def test_export_without_a_users_row_is_empty_and_creates_nothing(client, db_session):
    resp = client.get("/api/me/export", headers=H)

    assert resp.status_code == 200
    body = resp.json()
    assert body["account"] is None
    assert body["sessions"] == []
    assert body["usage"] == []
    assert db_session.get(User, ME) is None


def test_export_legacy_null_feedback_pref_reports_hints(client, db_session):
    _seed(db_session, ME)
    db_session.get(User, ME).feedback_pref = None
    db_session.commit()

    body = client.get("/api/me/export", headers=H).json()

    assert body["account"]["feedback_pref"] == "hints"


def test_export_tolerates_malformed_stored_json(client, db_session):
    _seed(db_session, ME)
    for m in db_session.query(ChatMessage).all():
        m.citations_json = "not json"
    for e in db_session.query(LearningEvent).all():
        e.options_json = json.dumps({"not": "a list"})
    db_session.query(Session).filter_by(id=f"{ME}-s1").one().topic_profile_json = "{bad"
    db_session.commit()

    resp = client.get("/api/me/export", headers=H)

    assert resp.status_code == 200
    s1 = resp.json()["sessions"][0]
    assert all(m["citations"] == [] for m in s1["messages"])
    assert s1["check_answers"][0]["options"] == []
    assert s1["topic_profile"]["confirmed_gaps"] == []


def test_export_is_not_served_from_another_token(client, db_session):
    _seed(db_session, ME)

    resp = client.get("/api/me/export", headers={"Authorization": "Bearer garbage"})

    assert resp.status_code == 401
