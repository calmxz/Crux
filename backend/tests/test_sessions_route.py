"""TDD: POST/GET sessions, GET single, POST end."""

from datetime import datetime, timedelta, timezone

import pytest

from agent.types import ToolContext
from config import settings
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, Document, UsageCounter, User
from db.models import Session as SessionModel
from lib.error_codes import TOO_MANY_REQUESTS
from services import check_question_service, summary_service, velocity_limit

USER_ID = "u1"


@pytest.fixture
def seeded_user(db_session):
    db_session.add(User(id=USER_ID))
    db_session.commit()


def test_post_fresh_creates_session(client):
    r = client.post(
        "/api/sessions",
        json={"user_id": USER_ID, "topic": "sql joins", "seed_mode": "fresh"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user_id"] == USER_ID
    assert body["topic"] == "sql joins"
    assert body["topic_profile"]["confirmed_gaps"] == []
    assert body["topic_profile"]["mastered_concepts"] == []
    assert body["topic_profile"]["last_session_summary"] is None
    assert body["ended_at"] is None


def test_post_sessions_velocity_limited(client, seeded_user, monkeypatch):
    """FIX A: POST /sessions can trigger a full-transcript summary LLM call
    on the resume path (see create_session), so it must carry the same
    velocity_limit guard as the other paid routes."""
    velocity_limit.reset()
    monkeypatch.setattr(settings, "burst_limit_per_minute", 1)
    try:
        r1 = client.post(
            "/api/sessions",
            json={"user_id": USER_ID, "topic": "sql joins", "seed_mode": "fresh"},
        )
        assert r1.status_code == 201, r1.text

        r2 = client.post(
            "/api/sessions",
            json={"user_id": USER_ID, "topic": "sql outer joins", "seed_mode": "fresh"},
        )
        assert r2.status_code == 429, r2.text
        assert r2.json()["detail"]["code"] == TOO_MANY_REQUESTS
        assert int(r2.headers["Retry-After"]) >= 1
    finally:
        velocity_limit.reset()


def test_post_resume_without_prior_400(client, seeded_user):
    r = client.post(
        "/api/sessions",
        json={"user_id": USER_ID, "topic": "sql", "seed_mode": "resume"},
    )
    assert r.status_code == 400


def test_post_resume_with_ended_prior_copies_profile(client, db_session, seeded_user):
    prior = SessionModel(
        id="prior_1",
        user_id=USER_ID,
        topic="sql",
        topic_profile_json=TopicProfile(
            knowledge_level="beginner",
            confirmed_gaps=[{"name": "joins"}],
            mastered_concepts=[{"name": "select"}],
            last_session_summary="covered selects",
        ).model_dump_json(),
        ended_at=datetime.now(timezone.utc),
    )
    db_session.add(prior)
    db_session.commit()

    r = client.post(
        "/api/sessions",
        json={
            "user_id": USER_ID,
            "topic": "sql",
            "seed_mode": "resume",
            "prior_session_id": "prior_1",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert [g["name"] for g in body["topic_profile"]["confirmed_gaps"]] == ["joins"]
    assert [c["name"] for c in body["topic_profile"]["mastered_concepts"]] == ["select"]
    assert body["topic_profile"]["last_session_summary"] == "covered selects"


def test_post_resume_with_unended_prior_generates_summary(
    client, db_session, seeded_user, mock_litellm, llm_text, monkeypatch
):
    # Stub summary_service.acompletion call inside async path
    async def fake_acompletion(**kwargs):
        return llm_text("auto summary about joins")

    monkeypatch.setattr("services.summary_service.litellm.acompletion", fake_acompletion)

    prior = SessionModel(
        id="prior_2",
        user_id=USER_ID,
        topic="sql",
        topic_profile_json=TopicProfile(mastered_concepts=[{"name": "select"}]).model_dump_json(),
    )
    db_session.add(prior)
    db_session.flush()
    # F-32: generate_and_persist short-circuits zero-message sessions to the
    # mechanical fallback and never calls the LLM, so a message is required
    # here to exercise the LLM-summary path this test targets.
    db_session.add(ChatMessage(session_id="prior_2", role="user", content="what is a join"))
    db_session.commit()

    r = client.post(
        "/api/sessions",
        json={
            "user_id": USER_ID,
            "topic": "sql",
            "seed_mode": "resume",
            "prior_session_id": "prior_2",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["topic_profile"]["last_session_summary"] == "auto summary about joins"


def test_resume_409_when_second_active_session_exists_leaves_prior_untouched(
    client, db_session, seeded_user, mock_litellm, llm_text, monkeypatch
):
    """B-05: a pre-existing active session on the same topic must 409 on
    resume without ending or summarizing the session being resumed, and must
    leave both rows untouched.
    """
    called = {"summary": False}

    async def fake_acompletion(**kwargs):
        called["summary"] = True
        return llm_text("should not be generated")

    monkeypatch.setattr("services.summary_service.litellm.acompletion", fake_acompletion)

    prior_ended_at = datetime(2026, 7, 1, tzinfo=timezone.utc)
    active_other = SessionModel(
        id="active_other",
        user_id=USER_ID,
        topic="sql",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    prior = SessionModel(
        id="prior_dup",
        user_id=USER_ID,
        topic="sql",
        topic_profile_json=TopicProfile(mastered_concepts=[{"name": "select"}]).model_dump_json(),
        ended_at=prior_ended_at,
    )
    db_session.add_all([active_other, prior])
    db_session.flush()
    db_session.add(ChatMessage(session_id="prior_dup", role="user", content="hi"))
    db_session.commit()

    r = client.post(
        "/api/sessions",
        json={
            "user_id": USER_ID,
            "topic": "sql",
            "seed_mode": "resume",
            "prior_session_id": "prior_dup",
        },
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == "duplicate_topic"
    assert r.json()["detail"]["session_id"] == "active_other"

    db_session.expire_all()
    refreshed_prior = db_session.get(SessionModel, "prior_dup")
    refreshed_active = db_session.get(SessionModel, "active_other")
    # SQLite drops tzinfo on read (see test_list_returns_tz_aware_timestamps
    # above); compare naive values.
    assert refreshed_prior.ended_at == prior_ended_at.replace(tzinfo=None), (
        "aborted resume must not touch the prior"
    )
    assert refreshed_active.ended_at is None, "pre-existing active session must be untouched"
    assert called["summary"] is False, "no summary LLM call must fire before the 409"


def test_get_list_filters_by_user_desc(client, db_session, seeded_user):
    older = SessionModel(
        id="s_old",
        user_id=USER_ID,
        topic="x",
        topic_profile_json=TopicProfile().model_dump_json(),
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    newer = SessionModel(
        id="s_new",
        user_id=USER_ID,
        topic="y",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    other = SessionModel(
        id="s_other",
        user_id="u2",
        topic="z",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add_all([older, newer, other])
    db_session.add(User(id="u2"))
    db_session.commit()

    r = client.get(f"/api/sessions?user_id={USER_ID}")
    assert r.status_code == 200
    rows = r.json()
    assert [row["id"] for row in rows] == ["s_new", "s_old"]


def _seed_n_sessions(db_session, n):
    """n sessions with strictly decreasing created_at so ordering is
    deterministic on sqlite (default timestamps can collide)."""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(n):
        db_session.add(
            SessionModel(
                id=f"p{i}",
                user_id=USER_ID,
                topic=f"topic {i}",
                topic_profile_json=TopicProfile().model_dump_json(),
                created_at=base + timedelta(hours=i),
            )
        )
    db_session.commit()
    # newest first
    return [f"p{i}" for i in reversed(range(n))]


def test_list_rejects_limit_over_max(client, db_session, seeded_user):
    r = client.get(f"/api/sessions?user_id={USER_ID}&limit=201")
    assert r.status_code == 422, r.text


def test_list_rejects_limit_zero(client, db_session, seeded_user):
    r = client.get(f"/api/sessions?user_id={USER_ID}&limit=0")
    assert r.status_code == 422, r.text


def test_list_rejects_negative_offset(client, db_session, seeded_user):
    r = client.get(f"/api/sessions?user_id={USER_ID}&offset=-1")
    assert r.status_code == 422, r.text


def test_list_limit_offset_slices_newest_first(client, db_session, seeded_user):
    order = _seed_n_sessions(db_session, 5)
    r = client.get(f"/api/sessions?user_id={USER_ID}&limit=2&offset=2")
    assert r.status_code == 200, r.text
    assert [row["id"] for row in r.json()] == order[2:4]


def test_list_default_returns_up_to_100(client, db_session, seeded_user):
    order = _seed_n_sessions(db_session, 5)
    r = client.get(f"/api/sessions?user_id={USER_ID}")
    assert r.status_code == 200, r.text
    assert [row["id"] for row in r.json()] == order


def test_list_returns_tz_aware_timestamps(client, db_session, seeded_user):
    # SQLite drops tzinfo on read; the route must re-attach UTC so the wire format
    # includes an offset and the frontend can parse it as an absolute instant.
    db_session.add(
        SessionModel(
            id="s_tz",
            user_id=USER_ID,
            topic="x",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()

    r = client.get(f"/api/sessions?user_id={USER_ID}")
    assert r.status_code == 200
    rows = r.json()
    assert rows, "expected at least one session"
    iso = rows[0]["created_at"]
    assert iso.endswith("+00:00") or iso.endswith("Z"), iso


def test_get_single_404_missing(client):
    r = client.get(f"/api/sessions/does_not_exist?user_id={USER_ID}")
    assert r.status_code == 404


def test_get_single_404_for_wrong_user(client, db_session, seeded_user):
    db_session.add(User(id="other"))
    db_session.add(
        SessionModel(
            id="s_owned",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    r = client.get("/api/sessions/s_owned?user_id=other")
    assert r.status_code == 404


def test_get_single_ingestion_status_null_when_no_documents(
    client, db_session, seeded_user
):
    db_session.add(
        SessionModel(
            id="s1",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    r = client.get(f"/api/sessions/s1?user_id={USER_ID}")
    assert r.status_code == 200
    assert r.json()["ingestion_status"] is None


def test_post_end_404_for_wrong_user(client, db_session, seeded_user):
    """H-4 regression: POST /sessions/{id}/end must 404 when ?user_id does
    not match the session owner (no silent cross-user session termination)."""
    db_session.add(User(id="other"))
    db_session.add(
        SessionModel(
            id="s_end_other",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    r = client.post("/api/sessions/s_end_other/end?user_id=other")
    assert r.status_code == 404


def test_post_end_idempotent_when_already_ended(client, db_session, seeded_user):
    ended_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.add(
        SessionModel(
            id="s1",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile(
                last_session_summary="existing summary"
            ).model_dump_json(),
            ended_at=ended_at,
        )
    )
    db_session.commit()

    r = client.post(f"/api/sessions/s1/end?user_id={USER_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"] == {"kind": "summary", "text": "existing summary"}


def test_post_end_returns_no_exchanges_kind_for_empty_session(
    client, db_session, seeded_user, mock_litellm, llm_text, monkeypatch
):
    async def fake_acompletion(**kwargs):
        return llm_text("")

    monkeypatch.setattr("services.summary_service.litellm.acompletion", fake_acompletion)

    db_session.add(
        SessionModel(
            id="s_empty",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()

    r = client.post(f"/api/sessions/s_empty/end?user_id={USER_ID}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["kind"] == "no_exchanges"
    assert "without any exchanges" in body["summary"]["text"].lower()


def test_get_session_returns_messages_array(client, db_session, seeded_user):
    from db.models import ChatMessage

    db_session.add(
        SessionModel(
            id="s_msgs",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.add(ChatMessage(session_id="s_msgs", role="user", content="hi"))
    db_session.add(ChatMessage(session_id="s_msgs", role="assistant", content="hello back"))
    db_session.commit()

    r = client.get(f"/api/sessions/s_msgs?user_id={USER_ID}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == "s_msgs"
    assert [(m["role"], m["content"]) for m in body["messages"]] == [
        ("user", "hi"),
        ("assistant", "hello back"),
    ]


def test_get_session_messages_round_trip_status(client, db_session, seeded_user):
    """F-14 follow-up: GET-session messages must carry `status` through so the
    FE can render the '(interrupted)' marker for partial rows on reload."""
    from db.models import ChatMessage

    db_session.add(
        SessionModel(
            id="s_msg_status",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.add(ChatMessage(session_id="s_msg_status", role="user", content="hi"))
    db_session.add(
        ChatMessage(session_id="s_msg_status", role="assistant", content="draft", status="partial")
    )
    db_session.commit()

    r = client.get(f"/api/sessions/s_msg_status?user_id={USER_ID}")
    assert r.status_code == 200, r.text
    body = r.json()
    statuses = [m["status"] for m in body["messages"]]
    assert statuses == ["complete", "partial"]


def test_reopen_flips_ended_at_to_null(client, db_session, seeded_user):
    db_session.add(
        SessionModel(
            id="s_re",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
            ended_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    r = client.post(f"/api/sessions/s_re/reopen?user_id={USER_ID}")
    assert r.status_code == 200, r.text
    assert r.json()["ended_at"] is None
    # idempotent: reopening an already-active session is a no-op
    r2 = client.post(f"/api/sessions/s_re/reopen?user_id={USER_ID}")
    assert r2.status_code == 200
    assert r2.json()["ended_at"] is None


def test_reopen_404_when_missing(client):
    r = client.post(f"/api/sessions/no_such/reopen?user_id={USER_ID}")
    assert r.status_code == 404


def test_reopen_404_for_wrong_user(client, db_session, seeded_user):
    db_session.add(User(id="other"))
    db_session.add(
        SessionModel(
            id="s_re_other",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
            ended_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()
    r = client.post("/api/sessions/s_re_other/reopen?user_id=other")
    assert r.status_code == 404


def test_post_end_generates_summary(
    client, db_session, seeded_user, mock_litellm, llm_text, monkeypatch
):
    async def fake_acompletion(**kwargs):
        return llm_text("learner covered joins")

    monkeypatch.setattr("services.summary_service.litellm.acompletion", fake_acompletion)

    db_session.add(
        SessionModel(
            id="s1",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    # F-32: generate_and_persist short-circuits zero-message sessions to the
    # mechanical fallback and never calls the LLM, so a message is required
    # here to exercise the LLM-summary path this test targets.
    db_session.add(ChatMessage(session_id="s1", role="user", content="what is a join"))
    db_session.commit()

    r = client.post(f"/api/sessions/s1/end?user_id={USER_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"] == {"kind": "summary", "text": "learner covered joins"}
    assert body["ended_at"] is not None


# ---------------------------------------------------------------------------
# F-03: end/resume summary trigger consumes a daily rate-limit slot
# ---------------------------------------------------------------------------


def _create_active_session_with_messages(db_session, sid="s_rate"):
    """Active (unended) session with a couple of exchanges, so the mechanical
    fallback summary is non-empty and lands in the "summary" kind, not
    "no_exchanges". Creates the owning user too."""
    db_session.add(User(id=USER_ID))
    db_session.add(
        SessionModel(
            id=sid,
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.add(ChatMessage(session_id=sid, role="user", content="what are joins"))
    db_session.add(ChatMessage(session_id=sid, role="assistant", content="joins combine tables"))
    db_session.commit()
    return sid


def _usage_count(db_session, user_id=USER_ID):
    row = db_session.query(UsageCounter).filter_by(user_id=user_id).one_or_none()
    return row.count if row else 0


def test_end_session_at_rate_cap_returns_mechanical_summary(client, db_session, monkeypatch):
    # F-03: end must never 429, but a rate-capped user must not trigger LLM spend.
    # Force the non-stub branch (mirrors Task 4's pattern) so a rate-gate bypass
    # would actually reach litellm.acompletion instead of being masked by stub mode.
    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "real")
    monkeypatch.setattr(settings, "daily_cap", 0)

    called = []

    async def fake_acompletion(**kwargs):
        called.append(1)

    monkeypatch.setattr("services.summary_service.litellm.acompletion", fake_acompletion)

    session_id = _create_active_session_with_messages(db_session)
    resp = client.post(f"/api/sessions/{session_id}/end?user_id={USER_ID}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert called == []  # rate cap must short-circuit before any LLM call
    assert body["summary"]["kind"] == "summary"
    assert "joins combine tables" in body["summary"]["text"]


def test_end_session_consumes_rate_limit_slot(
    client, db_session, monkeypatch, llm_text
):
    async def fake_acompletion(**kwargs):
        return llm_text("a fresh summary")

    monkeypatch.setattr("services.summary_service.litellm.acompletion", fake_acompletion)

    session_id = _create_active_session_with_messages(db_session)
    before = _usage_count(db_session)
    resp = client.post(f"/api/sessions/{session_id}/end?user_id={USER_ID}")
    assert resp.status_code == 200, resp.text
    assert _usage_count(db_session) == before + 1


# ---------------------------------------------------------------------------
# PATCH /sessions/{session_id} — rename + pin (Task 8)
# ---------------------------------------------------------------------------


def _make_session(db_session, sid, pinned=False, ended=False):
    s = SessionModel(
        id=sid,
        user_id=USER_ID,
        topic="orig",
        topic_profile_json=TopicProfile().model_dump_json(),
        pinned=pinned,
        ended_at=datetime.now(timezone.utc) if ended else None,
    )
    db_session.add(s)
    db_session.commit()
    return s


def test_patch_renames_session(client, db_session, seeded_user):
    _make_session(db_session, "s_rename")
    r = client.patch(f"/api/sessions/s_rename?user_id={USER_ID}", json={"topic": "new name"})
    assert r.status_code == 200, r.text
    assert r.json()["topic"] == "new name"


def test_patch_pins_active_session(client, db_session, seeded_user):
    _make_session(db_session, "s_pin")
    r = client.patch(f"/api/sessions/s_pin?user_id={USER_ID}", json={"pinned": True})
    assert r.status_code == 200, r.text
    assert r.json()["pinned"] is True


def test_patch_pin_on_ended_session_400(client, db_session, seeded_user):
    _make_session(db_session, "s_ended", ended=True)
    r = client.patch(f"/api/sessions/s_ended?user_id={USER_ID}", json={"pinned": True})
    assert r.status_code == 400


def test_patch_rename_allowed_on_ended_session(client, db_session, seeded_user):
    _make_session(db_session, "s_ended2", ended=True)
    r = client.patch(f"/api/sessions/s_ended2?user_id={USER_ID}", json={"topic": "renamed ended"})
    assert r.status_code == 200, r.text
    assert r.json()["topic"] == "renamed ended"


def test_patch_404_for_other_user(client, db_session, seeded_user):
    other = SessionModel(
        id="s_other_patch",
        user_id="someone_else",
        topic="x",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(other)
    db_session.commit()
    r = client.patch(f"/api/sessions/s_other_patch?user_id={USER_ID}", json={"topic": "hijack"})
    assert r.status_code == 404


def test_list_and_detail_include_pinned(client, db_session, seeded_user):
    _make_session(db_session, "s_list", pinned=True)
    list_items = client.get(f"/api/sessions?user_id={USER_ID}").json()
    s_list_item = next((item for item in list_items if item["id"] == "s_list"), None)
    assert s_list_item is not None, "s_list not found in list response"
    assert s_list_item["pinned"] is True
    assert client.get(f"/api/sessions/s_list?user_id={USER_ID}").json()["pinned"] is True


def test_patch_empty_body_400(client, db_session, seeded_user):
    _make_session(db_session, "s_empty")
    r = client.patch(f"/api/sessions/s_empty?user_id={USER_ID}", json={})
    assert r.status_code == 400


def test_get_session_ingestion_aggregates_documents(client, db_session, seeded_user):
    db_session.add(
        SessionModel(
            id="s_ing",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.flush()
    db_session.add(Document(session_id="s_ing", filename="a.pdf", status="ready"))
    db_session.add(Document(session_id="s_ing", filename="b.pptx", status="pending"))
    db_session.commit()

    r = client.get(f"/api/sessions/s_ing/ingestion?user_id={USER_ID}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert len(body["documents"]) == 2
    assert {d["filename"] for d in body["documents"]} == {"a.pdf", "b.pptx"}


def test_get_session_ingestion_404_for_wrong_user(client, db_session, seeded_user):
    db_session.add(User(id="other2"))
    db_session.add(
        SessionModel(
            id="s_ing_owned",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    r = client.get("/api/sessions/s_ing_owned/ingestion?user_id=other2")
    assert r.status_code == 404


def test_get_session_ingestion_empty_when_no_documents(client, db_session, seeded_user):
    db_session.add(
        SessionModel(
            id="s_ing_empty",
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    r = client.get(f"/api/sessions/s_ing_empty/ingestion?user_id={USER_ID}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] is None


# ---------------------------------------------------------------------------
# F-30/F-31/F-33: claim-first end + single-commit summary + resume abandon
# ---------------------------------------------------------------------------


@pytest.fixture
def seeded_session(db_session, seeded_user):
    session = SessionModel(
        id="s_claim_1",
        user_id=USER_ID,
        topic="sql",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(session)
    db_session.commit()
    return session


def _open_batch(db, session_id, user_id=USER_ID, n=2):
    ctx = ToolContext(
        db=db, session_id=session_id, user_id=user_id,
        turn_started_at=datetime.now(timezone.utc),
    )
    return check_question_service.register(
        db, ctx,
        AskCheckQuestionsArgs(
            set_index=1, set_total=1,
            session_id=session_id,
            gap="g",
            items=[
                {"question": f"Q{i}?", "options": ["a", "b"], "correct_index": 0, "explanation": "a."}
                for i in range(n)
            ],
        ),
    )


@pytest.fixture
def session_with_open_batch(db_session, seeded_user):
    session = SessionModel(
        id="s_open_batch_1",
        user_id=USER_ID,
        topic="sql",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(session)
    db_session.commit()
    _open_batch(db_session, session.id)
    return session


def test_double_end_pays_one_summary(client, db_session, seeded_session, monkeypatch):
    """F-30: the second end takes the idempotent path -- generate_and_persist
    runs exactly once."""
    calls = {"n": 0}
    real = summary_service.generate_and_persist

    async def counting(db, session, *, allow_llm=True):
        calls["n"] += 1
        return await real(db, session, allow_llm=allow_llm)

    monkeypatch.setattr(summary_service, "generate_and_persist", counting)
    # Route module does `from services import summary_service` (the module, not
    # the function), so patching the attribute on the module object above is
    # visible through routes.sessions.summary_service.generate_and_persist too.

    r1 = client.post(f"/api/sessions/{seeded_session.id}/end?user_id={USER_ID}")
    r2 = client.post(f"/api/sessions/{seeded_session.id}/end?user_id={USER_ID}")
    assert r1.status_code == 200 and r2.status_code == 200
    assert calls["n"] == 1
    assert r2.json()["summary"] is not None


def test_claim_end_is_single_winner(db_session, seeded_session):
    from routes.sessions import _claim_end

    assert _claim_end(db_session, seeded_session.id) is True
    assert _claim_end(db_session, seeded_session.id) is False
    db_session.refresh(seeded_session)
    assert seeded_session.ended_at is not None


def test_resume_create_abandons_prior_open_batch(client, db_session, session_with_open_batch):
    """F-31: continue-topic must force-skip the prior's open quiz so reopening
    the prior doesn't render a zombie batch or deadlock new quizzes."""
    prior = session_with_open_batch
    resp = client.post(
        "/api/sessions",
        json={
            "user_id": USER_ID,
            "topic": prior.topic,
            "seed_mode": "resume",
            "prior_session_id": prior.id,
        },
    )
    assert resp.status_code == 201, resp.text
    db_session.expire_all()
    assert check_question_service.get_pending_check(db_session, prior.id) is None
    db_session.refresh(prior)
    assert prior.ended_at is not None


def _seed_session_with_messages(db_session, session_id, count):
    from db.models import ChatMessage

    db_session.add(
        SessionModel(
            id=session_id,
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    for i in range(count):
        db_session.add(ChatMessage(session_id=session_id, role="user", content=f"m{i}"))
    db_session.commit()


def test_get_session_caps_messages_to_last_30(client, db_session, seeded_user):
    _seed_session_with_messages(db_session, "s_window", 31)

    r = client.get(f"/api/sessions/s_window?user_id={USER_ID}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["messages"]) == 30
    assert body["has_more_messages"] is True
    # Oldest message (m0) dropped; order stays ascending.
    assert body["messages"][0]["content"] == "m1"
    assert body["messages"][-1]["content"] == "m30"


def test_get_session_small_transcript_returns_all_and_has_more_false(client, db_session, seeded_user):
    _seed_session_with_messages(db_session, "s_small", 2)

    r = client.get(f"/api/sessions/s_small?user_id={USER_ID}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["messages"]) == 2
    assert body["has_more_messages"] is False


def test_get_session_exactly_30_has_more_false(client, db_session, seeded_user):
    _seed_session_with_messages(db_session, "s_exact", 30)

    r = client.get(f"/api/sessions/s_exact?user_id={USER_ID}")
    body = r.json()
    assert len(body["messages"]) == 30
    assert body["has_more_messages"] is False


def test_post_fresh_with_declared_level_seeds_profile(client, seeded_user):
    r = client.post(
        "/api/sessions",
        json={
            "user_id": USER_ID,
            "topic": "sql joins",
            "seed_mode": "fresh",
            "declared_level": "advanced",
        },
    )
    assert r.status_code == 201, r.text
    profile = TopicProfile.model_validate(r.json()["topic_profile"])
    assert profile.knowledge_level == "advanced"


def test_post_resume_with_declared_level_is_422(client, seeded_user, db_session):
    from db.models import Session as SessionModel

    db_session.add(
        SessionModel(
            id="prior1",
            user_id=USER_ID,
            topic="sql joins",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    r = client.post(
        "/api/sessions",
        json={
            "user_id": USER_ID,
            "topic": "sql joins",
            "seed_mode": "resume",
            "prior_session_id": "prior1",
            "declared_level": "beginner",
        },
    )
    assert r.status_code == 422, r.text


def test_post_fresh_without_declared_level_unchanged(client, seeded_user):
    r = client.post(
        "/api/sessions",
        json={"user_id": USER_ID, "topic": "plain topic", "seed_mode": "fresh"},
    )
    assert r.status_code == 201, r.text
    profile = TopicProfile.model_validate(r.json()["topic_profile"])
    assert profile.knowledge_level is None


# --- C-09: whitespace-only topics ---


def test_post_sessions_whitespace_topic_is_422(client, seeded_user, db_session):
    from db.models import Session as SessionModel

    r = client.post(
        "/api/sessions",
        json={"user_id": USER_ID, "topic": "   ", "seed_mode": "fresh"},
    )
    assert r.status_code == 422, r.text
    assert r.json()["detail"] == {"code": "empty_topic"}
    assert db_session.query(SessionModel).count() == 0


def test_post_sessions_empty_topic_is_422(client, seeded_user):
    r = client.post(
        "/api/sessions",
        json={"user_id": USER_ID, "topic": "", "seed_mode": "fresh"},
    )
    assert r.status_code == 422, r.text


def test_patch_session_whitespace_topic_is_422(client, seeded_user, db_session):
    from db.models import Session as SessionModel

    db_session.add(
        SessionModel(
            id="s-ws",
            user_id=USER_ID,
            topic="sql joins",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    r = client.patch("/api/sessions/s-ws", json={"topic": "  "})
    assert r.status_code == 422, r.text
    assert r.json()["detail"] == {"code": "empty_topic"}
    db_session.expire_all()
    assert db_session.get(SessionModel, "s-ws").topic == "sql joins"


def test_patch_session_empty_topic_is_422(client, seeded_user, db_session):
    from db.models import Session as SessionModel

    db_session.add(
        SessionModel(
            id="s-ws2",
            user_id=USER_ID,
            topic="sql joins",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    r = client.patch("/api/sessions/s-ws2", json={"topic": ""})
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_followup_disconnect_during_tool_call_keeps_partial_reply(
    db_session, seeded_user, monkeypatch
):
    """#421: on a disconnect the ambient cancel is level-triggered, so an
    unshielded drain of the follow-up producer forwards the cancel into the
    tutor's cancel arm and kills it at its first suspension (the drain of an
    in-flight tool call), before the partial reply is committed. The drain
    must run shielded, as in chat_stream.
    """
    import asyncio
    from types import SimpleNamespace

    import anyio
    from sqlalchemy import func, select

    from agent.stream_events import StreamEvent
    from routes import sessions as sessions_route

    sid = "s-followup-cancel"
    db_session.add(SessionModel(id=sid, user_id=USER_ID, topic="sql"))
    db_session.commit()

    arm_done = asyncio.Event()
    started = asyncio.Event()

    async def fake_run_streaming(messages, system_prompt, ctx):
        try:
            yield StreamEvent("assistant_delta", {"text": "partial"})
            started.set()
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            # Mirrors tutor.py's cancel arm with a tool call in flight: stage
            # the row, suspend on the dispatch drain, then commit.
            ctx.db.add(
                ChatMessage(
                    session_id=sid,
                    role="assistant",
                    content="partial",
                    status="cancelled",
                    cancelled_at=datetime.now(timezone.utc),
                )
            )
            await asyncio.sleep(0.05)
            ctx.db.commit()
            arm_done.set()
            raise

    monkeypatch.setattr(sessions_route.tutor, "run_streaming", fake_run_streaming)

    async def _not_disconnected():
        return False

    request = SimpleNamespace(headers={}, is_disconnected=_not_disconnected)
    ctx = ToolContext(
        db=db_session,
        session_id=sid,
        user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc),
    )
    resp = sessions_route._followup_response(request, True, [], "", ctx)

    async def consume():
        async for _chunk in resp.body_iterator:
            pass

    async with anyio.create_task_group() as tg:
        tg.start_soon(consume)
        await started.wait()
        # Simulate Starlette's disconnect handling: cancel the scope the
        # response body iterator runs in.
        tg.cancel_scope.cancel()
    assert arm_done.is_set(), (
        "the pump returned while the tutor's cancel arm was still unwinding"
    )
    # get_db teardown stand-in; the assert above is what proves the drain.
    db_session.close()

    cancelled = db_session.execute(
        select(func.count())
        .select_from(ChatMessage)
        .where(ChatMessage.session_id == sid, ChatMessage.status == "cancelled")
    ).scalar_one()
    assert cancelled == 1, "the partial follow-up reply was not persisted"
