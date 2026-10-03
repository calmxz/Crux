"""GET /api/profile/aggregate — cross-session aggregate dashboard."""

import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import event as _sa_event

from contracts import TopicProfile
from db.models import ChatMessage, LearningEvent, User
from db.models import Session as SessionModel

USER_ID = "u_agg"


def _mk_session(
    db,
    sid: str,
    *,
    user_id: str = USER_ID,
    topic: str = "",
    profile: TopicProfile | None = None,
    created_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> SessionModel:
    s = SessionModel(
        id=sid,
        user_id=user_id,
        topic=topic,
        topic_profile_json=(profile or TopicProfile()).model_dump_json(),
    )
    if created_at is not None:
        s.created_at = created_at
    if ended_at is not None:
        s.ended_at = ended_at
    db.add(s)
    return s


def test_aggregate_empty_user_returns_zeros(client, db_session):
    db_session.add(User(id=USER_ID))
    db_session.commit()
    r = client.get("/api/profile/aggregate", params={"user_id": USER_ID})
    assert r.status_code == 200
    body = r.json()
    assert body["total_sessions"] == 0
    assert body["active_sessions"] == 0
    assert body["ended_sessions"] == 0
    assert body["total_learning_events"] == 0
    assert body["last_active_at"] is None
    assert body["combined_mastered_concepts"] == []
    assert body["combined_confirmed_gaps"] == []
    assert body["knowledge_level_distribution"] == {
        "beginner": 0,
        "intermediate": 0,
        "advanced": 0,
        "unknown": 0,
    }
    assert body["recent_topics"] == []


def test_aggregate_overlapping_concepts_dedupe_and_count(client, db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    t0 = datetime(2026, 5, 1, tzinfo=timezone.utc)
    _mk_session(
        db_session,
        "s1",
        topic="sql",
        created_at=t0,
        profile=TopicProfile(
            knowledge_level="beginner",
            mastered_concepts=[{"name": "joins"}, {"name": "select"}],
            confirmed_gaps=[{"name": "window-fns"}],
        ),
    )
    _mk_session(
        db_session,
        "s2",
        topic="sql-2",
        created_at=t0 + timedelta(days=1),
        profile=TopicProfile(
            knowledge_level="intermediate",
            mastered_concepts=[{"name": "joins"}, {"name": "indexes"}],
            confirmed_gaps=[{"name": "window-fns"}, {"name": "ctes"}],
        ),
    )
    _mk_session(
        db_session,
        "s3",
        topic="sql-3",
        created_at=t0 + timedelta(days=2),
        profile=TopicProfile(
            knowledge_level="intermediate",
            mastered_concepts=[{"name": "joins"}],
            confirmed_gaps=[{"name": "window-fns"}],
        ),
    )
    db_session.commit()

    r = client.get("/api/profile/aggregate", params={"user_id": USER_ID})
    assert r.status_code == 200
    body = r.json()

    assert body["total_sessions"] == 3
    assert body["active_sessions"] == 3
    assert body["ended_sessions"] == 0

    mastered = {c["concept"]: c for c in body["combined_mastered_concepts"]}
    assert mastered["joins"]["count"] == 3
    assert mastered["joins"]["first_seen_session_id"] == "s1"
    assert mastered["select"]["count"] == 1
    assert mastered["indexes"]["count"] == 1
    assert mastered["indexes"]["first_seen_session_id"] == "s2"
    # sorted by count desc
    assert body["combined_mastered_concepts"][0]["concept"] == "joins"

    gaps = {g["concept"]: g for g in body["combined_confirmed_gaps"]}
    assert gaps["window-fns"]["count"] == 3
    assert gaps["window-fns"]["first_seen_session_id"] == "s1"
    assert gaps["ctes"]["count"] == 1
    assert body["combined_confirmed_gaps"][0]["concept"] == "window-fns"


def test_aggregate_knowledge_level_distribution(client, db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    # Distinct topics: uq_sessions_active_topic forbids two simultaneously-active
    # same-topic sessions per user, and topic content is irrelevant to this test.
    _mk_session(db_session, "k1", topic="k1-topic", profile=TopicProfile(knowledge_level="beginner"))
    _mk_session(db_session, "k2", topic="k2-topic", profile=TopicProfile(knowledge_level="beginner"))
    _mk_session(db_session, "k3", topic="k3-topic", profile=TopicProfile(knowledge_level="advanced"))
    _mk_session(db_session, "k4", topic="k4-topic", profile=TopicProfile())  # unknown
    db_session.commit()

    r = client.get("/api/profile/aggregate", params={"user_id": USER_ID})
    assert r.status_code == 200
    dist = r.json()["knowledge_level_distribution"]
    assert dist == {
        "beginner": 2,
        "intermediate": 0,
        "advanced": 1,
        "unknown": 1,
    }


def test_aggregate_event_count_and_recent_topics(client, db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    base = datetime(2026, 5, 1, tzinfo=timezone.utc)
    for i in range(7):
        _mk_session(
            db_session,
            f"r{i}",
            topic=f"topic-{i}",
            created_at=base + timedelta(days=i),
            ended_at=(base + timedelta(days=i, hours=1)) if i % 2 == 0 else None,
        )
    db_session.flush()
    for i in range(4):
        db_session.add(
            LearningEvent(
                session_id="r0",
                gap_tested=f"g{i}",
                question="?",
                correct=bool(i % 2),
            )
        )
    db_session.commit()

    r = client.get("/api/profile/aggregate", params={"user_id": USER_ID})
    body = r.json()
    assert r.status_code == 200
    assert body["total_sessions"] == 7
    assert body["ended_sessions"] == 4  # i=0,2,4,6
    assert body["active_sessions"] == 3
    assert body["total_learning_events"] == 4
    topics = [t["topic"] for t in body["recent_topics"]]
    assert topics == ["topic-6", "topic-5", "topic-4", "topic-3", "topic-2"]
    assert body["last_active_at"] is not None


def test_aggregate_isolates_per_user(client, db_session):
    db_session.add(User(id="u_alpha"))
    db_session.add(User(id="u_beta"))
    db_session.flush()
    _mk_session(
        db_session,
        "a1",
        user_id="u_alpha",
        profile=TopicProfile(mastered_concepts=[{"name": "alpha-only"}]),
    )
    _mk_session(
        db_session,
        "b1",
        user_id="u_beta",
        profile=TopicProfile(mastered_concepts=[{"name": "beta-only"}]),
    )
    db_session.commit()

    r = client.get("/api/profile/aggregate", params={"user_id": "u_alpha"})
    body = r.json()
    assert body["total_sessions"] == 1
    assert [c["concept"] for c in body["combined_mastered_concepts"]] == ["alpha-only"]


def test_aggregate_recent_topics_carry_last_session_summary(client, db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    ended_profile = TopicProfile(last_session_summary="Covered Big-O; gap in log bounds.")
    _mk_session(
        db_session,
        "ended1",
        topic="Big-O",
        profile=ended_profile,
        created_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        ended_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
    )
    _mk_session(
        db_session,
        "active1",
        topic="Trees",
        profile=TopicProfile(),
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
    )
    db_session.commit()

    body = client.get("/api/profile/aggregate", params={"user_id": USER_ID}).json()
    by_id = {t["id"]: t for t in body["recent_topics"]}
    assert by_id["ended1"]["last_session_summary"] == "Covered Big-O; gap in log bounds."
    assert by_id["active1"]["last_session_summary"] is None


# Mirrors backend/tests/test_sessions_perf.py::count_queries (kept local to avoid
# cross-test-module import; dedupe into a shared helper is a future option).
@contextmanager
def _count_queries(db):
    bind = db.get_bind()
    state = {"n": 0}

    def _before(conn, cursor, statement, params, context, executemany):
        state["n"] += 1

    _sa_event.listen(bind, "before_cursor_execute", _before)
    try:
        yield state
    finally:
        _sa_event.remove(bind, "before_cursor_execute", _before)


def test_recent_topics_carry_enriched_fields(client, db_session):
    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    prof = {"focus_target_gap": "ATP yield",
            "mastered_concepts": ["a", "b", "c"], "confirmed_gaps": []}
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(SessionModel(id="s_rich", user_id=USER_ID, topic="Glycolysis",
                                created_at=base, topic_profile_json=json.dumps(prof)))
    db_session.add(ChatMessage(session_id="s_rich", role="user", content="hi",
                               created_at=base))
    db_session.add(ChatMessage(session_id="s_rich", role="assistant",
                               content="glycolysis nets 2 ATP per glucose",
                               created_at=base + timedelta(minutes=1)))
    db_session.commit()

    r = client.get("/api/profile/aggregate", params={"user_id": USER_ID})
    assert r.status_code == 200, r.text
    rt = next(t for t in r.json()["recent_topics"] if t["id"] == "s_rich")
    assert rt["message_count"] == 2
    assert rt["last_message_preview"] == "glycolysis nets 2 ATP per glucose"
    assert rt["last_activity_at"] is not None
    assert rt["progress"]["focus_target_gap"] == "ATP yield"
    assert rt["progress"]["mastered_count"] == 3


def test_recent_topics_enrichment_is_set_based(client, db_session):
    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    db_session.add(User(id=USER_ID))
    db_session.flush()
    for n in range(8):  # more than the 5-row recent window
        sid = f"s{n}"
        db_session.add(SessionModel(id=sid, user_id=USER_ID, topic=f"t{n}",
                                    created_at=base, topic_profile_json="{}"))
        db_session.add(ChatMessage(session_id=sid, role="user", content="x",
                                   created_at=base))
    db_session.commit()

    with _count_queries(db_session) as q:
        r = client.get("/api/profile/aggregate", params={"user_id": USER_ID})
    assert r.status_code == 200, r.text
    # Set-based path is ~4-5 total queries (baseline ~2 + compute_enrichment's 2);
    # a per-session preview over the 5-row recent window would clear this. Keep the
    # bound tight so the assertion actually proves "set-based", not just "not insane".
    assert q["n"] <= 6, f"aggregate enrichment not set-based: {q['n']} queries"


T0 = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)


def _seed_session_for_insights(db, session_id="s1", user_id="test-user", topic="biology"):
    if not db.get(User, user_id):
        db.add(User(id=user_id))
    db.add(SessionModel(id=session_id, user_id=user_id, topic=topic))
    db.commit()


def _seed_event_for_insights(db, session_id, gap, correct, created_at, purpose=None):
    db.add(
        LearningEvent(
            session_id=session_id,
            gap_tested=gap,
            question="q",
            correct=correct,
            created_at=created_at,
            purpose=purpose,
        )
    )
    db.commit()


def test_concept_accuracy_math_and_first_session(client, db_session):
    # s2 needs a distinct topic from s1's default "biology": both are active
    # (no ended_at) for the same user, and uq_sessions_active_topic forbids two
    # simultaneously-active same-topic sessions per user. Topic content is not
    # asserted here.
    _seed_session_for_insights(db_session, session_id="s1")
    _seed_session_for_insights(db_session, session_id="s2", topic="biology-2")
    _seed_event_for_insights(db_session, "s1", "mitosis", False, T0)
    _seed_event_for_insights(db_session, "s2", "mitosis", True, T0 + timedelta(hours=1))
    _seed_event_for_insights(db_session, "s2", "mitosis", True, T0 + timedelta(hours=2))
    body = client.get("/api/profile/aggregate").json()
    assert len(body["concept_accuracy"]) == 1
    entry = body["concept_accuracy"][0]
    assert entry["concept"] == "mitosis"
    assert entry["correct_count"] == 2
    assert entry["total_count"] == 3
    assert abs(entry["accuracy"] - 2 / 3) < 0.001
    assert entry["first_seen_session_id"] == "s1"  # earliest event, not most events


def test_concept_accuracy_excludes_diagnostic_keeps_null_purpose(client, db_session):
    _seed_session_for_insights(db_session)
    _seed_event_for_insights(db_session, "s1", "mitosis", True, T0, purpose="diagnostic")
    _seed_event_for_insights(db_session, "s1", "osmosis", True, T0, purpose=None)
    _seed_event_for_insights(db_session, "s1", "diffusion", True, T0, purpose="check")
    body = client.get("/api/profile/aggregate").json()
    concepts = {e["concept"] for e in body["concept_accuracy"]}
    assert concepts == {"osmosis", "diffusion"}


def test_last_results_capped_at_five_oldest_to_newest(client, db_session):
    _seed_session_for_insights(db_session)
    # 7 events: F F F T T T F -> last 5 = F T T T F
    pattern = [False, False, False, True, True, True, False]
    for i, ok in enumerate(pattern):
        _seed_event_for_insights(
            db_session, "s1", "mitosis", ok, T0 + timedelta(minutes=i)
        )
    body = client.get("/api/profile/aggregate").json()
    entry = body["concept_accuracy"][0]
    assert entry["last_results"] == [False, True, True, True, False]
    assert entry["total_count"] == 7


def test_concept_accuracy_empty_when_no_events(client, db_session):
    _seed_session_for_insights(db_session)
    body = client.get("/api/profile/aggregate").json()
    assert body["concept_accuracy"] == []
    assert len(body["weekly_mastery"]) == 12


def test_weekly_mastery_buckets_first_correct_only(db_session):
    from services.profile_insights import aggregate_for_user

    _seed_session_for_insights(db_session)
    # mitosis: wrong then correct in week of 2026-06-29, correct again 2 weeks later
    _seed_event_for_insights(db_session, "s1", "mitosis", False, T0)
    _seed_event_for_insights(db_session, "s1", "mitosis", True, T0 + timedelta(hours=1))
    _seed_event_for_insights(db_session, "s1", "mitosis", True, T0 + timedelta(weeks=2))
    # osmosis: first correct 1 week after T0
    _seed_event_for_insights(db_session, "s1", "osmosis", True, T0 + timedelta(weeks=1))
    # diffusion: never correct -> never counted
    _seed_event_for_insights(db_session, "s1", "diffusion", False, T0)

    now = T0 + timedelta(weeks=2)  # 2026-07-15
    resp = aggregate_for_user(db_session, "test-user", now=now)

    assert len(resp.weekly_mastery) == 12
    # oldest first, consecutive Mondays, newest bucket = Monday of `now`
    assert resp.weekly_mastery[-1].week_start.isoformat() == "2026-07-13"
    assert resp.weekly_mastery[0].week_start.isoformat() == "2026-04-27"
    by_week = {p.week_start.isoformat(): p.count for p in resp.weekly_mastery}
    assert by_week["2026-06-29"] == 1  # mitosis first correct
    assert by_week["2026-07-06"] == 1  # osmosis
    assert by_week["2026-07-13"] == 0  # mitosis retest does NOT recount
    assert sum(p.count for p in resp.weekly_mastery) == 2


def test_weekly_mastery_outside_window_dropped(db_session):
    from services.profile_insights import aggregate_for_user

    _seed_session_for_insights(db_session)
    # first correct 20 weeks before `now` -> outside the 12-week window
    _seed_event_for_insights(db_session, "s1", "ancient", True, T0)
    now = T0 + timedelta(weeks=20)
    resp = aggregate_for_user(db_session, "test-user", now=now)
    assert sum(p.count for p in resp.weekly_mastery) == 0
    assert len(resp.weekly_mastery) == 12


def test_weekly_mastery_diagnostic_correct_not_counted(db_session):
    from services.profile_insights import aggregate_for_user

    _seed_session_for_insights(db_session)
    _seed_event_for_insights(db_session, "s1", "mitosis", True, T0, purpose="diagnostic")
    resp = aggregate_for_user(db_session, "test-user", now=T0)
    assert sum(p.count for p in resp.weekly_mastery) == 0


# --- issue #288: a concept must never appear in both aggregate lists ---


def _seed_conflict_sessions(db):
    """Session A lists "osmosis" as mastered; session B lists it as a gap."""
    db.add(User(id=USER_ID))
    db.flush()
    _mk_session(
        db,
        "conf_a",
        topic="conf-a",
        created_at=T0,
        profile=TopicProfile(
            mastered_concepts=[{"name": "osmosis"}, {"name": "mitosis"}],
            confirmed_gaps=[{"name": "meiosis"}],
        ),
    )
    _mk_session(
        db,
        "conf_b",
        topic="conf-b",
        created_at=T0 + timedelta(days=1),
        profile=TopicProfile(
            mastered_concepts=[{"name": "mitosis"}],
            confirmed_gaps=[{"name": "osmosis"}],
        ),
    )
    db.commit()


def _conflict_body(client):
    r = client.get("/api/profile/aggregate", params={"user_id": USER_ID})
    assert r.status_code == 200, r.text
    body = r.json()
    return (
        {c["concept"]: c for c in body["combined_mastered_concepts"]},
        {g["concept"]: g for g in body["combined_confirmed_gaps"]},
    )


def test_conflict_newest_event_incorrect_keeps_gap_only(client, db_session):
    _seed_conflict_sessions(db_session)
    _seed_event_for_insights(db_session, "conf_a", "osmosis", True, T0)
    _seed_event_for_insights(
        db_session, "conf_b", "osmosis", False, T0 + timedelta(hours=1)
    )

    mastered, gaps = _conflict_body(client)
    assert "osmosis" in gaps
    assert "osmosis" not in mastered


def test_conflict_newest_event_correct_keeps_mastered_only(client, db_session):
    _seed_conflict_sessions(db_session)
    _seed_event_for_insights(db_session, "conf_a", "osmosis", False, T0)
    _seed_event_for_insights(
        db_session, "conf_b", "osmosis", True, T0 + timedelta(hours=1)
    )

    mastered, gaps = _conflict_body(client)
    assert "osmosis" in mastered
    assert "osmosis" not in gaps


def test_conflict_with_no_events_keeps_gap_only(client, db_session):
    _seed_conflict_sessions(db_session)

    mastered, gaps = _conflict_body(client)
    assert "osmosis" in gaps
    assert "osmosis" not in mastered


def test_conflict_resolution_leaves_non_conflicting_concepts_untouched(
    client, db_session
):
    _seed_conflict_sessions(db_session)
    _seed_event_for_insights(
        db_session, "conf_b", "osmosis", False, T0 + timedelta(hours=1)
    )

    mastered, gaps = _conflict_body(client)
    assert mastered["mitosis"]["count"] == 2
    assert mastered["mitosis"]["first_seen_session_id"] == "conf_a"
    assert "mitosis" not in gaps
    assert gaps["meiosis"]["count"] == 1
    assert "meiosis" not in mastered


def test_aggregate_makes_no_llm_call(client, db_session, monkeypatch):
    import litellm

    def _boom(*args, **kwargs):
        raise AssertionError("aggregate path must not call the LLM")

    monkeypatch.setattr(litellm, "acompletion", _boom, raising=False)
    monkeypatch.setattr(litellm, "completion", _boom, raising=False)
    _seed_session_for_insights(db_session)
    _seed_event_for_insights(db_session, "s1", "mitosis", True, T0)
    assert client.get("/api/profile/aggregate").status_code == 200


# --- F-08: bounded aggregate --------------------------------------------

AGG_NOW = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
AGG_T0 = datetime(2026, 5, 1, tzinfo=timezone.utc)
PIN_USER = "u_pin"


@contextmanager
def capture_statements(db):
    bind = db.get_bind()
    stmts: list[str] = []

    def _before(conn, cursor, statement, params, context, executemany):
        stmts.append(statement)

    _sa_event.listen(bind, "before_cursor_execute", _before)
    try:
        yield stmts
    finally:
        _sa_event.remove(bind, "before_cursor_execute", _before)


def _mk_raw(db, sid, *, user_id, topic, profile_json, created_at, ended_at=None):
    db.add(
        SessionModel(
            id=sid, user_id=user_id, topic=topic, topic_profile_json=profile_json
        )
    )
    db.flush()
    row = db.get(SessionModel, sid)
    row.created_at = created_at
    row.ended_at = ended_at


def _seed_pin_fixture(db):
    db.add(User(id=PIN_USER))
    db.flush()
    _mk_raw(
        db, "p1", user_id=PIN_USER, topic="sql", created_at=AGG_T0,
        profile_json=TopicProfile(
            knowledge_level="beginner",
            mastered_concepts=[{"name": "joins"}, {"name": "select"}],
            confirmed_gaps=[{"name": "window-fns"}],
        ).model_dump_json(),
    )
    _mk_raw(
        db, "p2", user_id=PIN_USER, topic="sql-2",
        created_at=AGG_T0 + timedelta(days=1),
        ended_at=AGG_T0 + timedelta(days=2),
        profile_json=TopicProfile(
            knowledge_level="intermediate",
            mastered_concepts=[{"name": "joins"}],
            confirmed_gaps=[{"name": "window-fns"}, {"name": "ctes"}],
        ).model_dump_json(),
    )
    # malformed blob -> tolerant parser yields an empty profile ("unknown" level)
    _mk_raw(
        db, "p3", user_id=PIN_USER, topic="broken",
        created_at=AGG_T0 + timedelta(days=3), profile_json="{not json",
    )
    # legacy bare-string concept-list elements
    _mk_raw(
        db, "p4", user_id=PIN_USER, topic="legacy",
        created_at=AGG_T0 + timedelta(days=4),
        profile_json=json.dumps(
            {
                "knowledge_level": "advanced",
                "mastered_concepts": ["joins"],
                "confirmed_gaps": ["ctes"],
            }
        ),
    )
    db.add(
        LearningEvent(
            session_id="p1", gap_tested="ctes", question="q", correct=True,
            created_at=AGG_T0 + timedelta(days=5),
        )
    )
    db.add(
        LearningEvent(
            session_id="p1", gap_tested="joins", question="q", correct=False,
            created_at=AGG_T0 + timedelta(days=5),
        )
    )
    db.commit()


# Captured from the pre-F-08 implementation on the fixture above. Any drift
# here is a behaviour change, not an optimisation.
AGGREGATE_PIN = {
    "active_sessions": 3,
    "ended_sessions": 1,
    "total_sessions": 4,
    "total_learning_events": 2,
    "last_active_at": "2026-05-05T00:00:00",
    "combined_confirmed_gaps": [
        {"concept": "ctes", "count": 2, "first_seen_session_id": "p2"},
        {"concept": "window-fns", "count": 2, "first_seen_session_id": "p1"},
    ],
    "combined_mastered_concepts": [
        {"concept": "joins", "count": 3, "first_seen_session_id": "p1"},
        {"concept": "select", "count": 1, "first_seen_session_id": "p1"},
    ],
    "concept_accuracy": [
        {
            "accuracy": 0.0, "concept": "joins", "correct_count": 0,
            "first_seen_session_id": "p1", "last_results": [False],
            "total_count": 1,
        },
        {
            "accuracy": 1.0, "concept": "ctes", "correct_count": 1,
            "first_seen_session_id": "p1", "last_results": [True],
            "total_count": 1,
        },
    ],
    "knowledge_level_distribution": {
        "advanced": 1, "beginner": 1, "intermediate": 1, "unknown": 1,
    },
    "recent_topics": [
        {
            "created_at": "2026-05-05T00:00:00", "ended_at": None, "id": "p4",
            "last_activity_at": None, "last_message_preview": None,
            "last_session_summary": None, "message_count": 0,
            "progress": {
                "focus_target_gap": None, "level": "advanced", "mastered_count": 1,
            },
            "topic": "legacy",
        },
        {
            "created_at": "2026-05-04T00:00:00", "ended_at": None, "id": "p3",
            "last_activity_at": None, "last_message_preview": None,
            "last_session_summary": None, "message_count": 0,
            "progress": {
                "focus_target_gap": None, "level": None, "mastered_count": 0,
            },
            "topic": "broken",
        },
        {
            "created_at": "2026-05-02T00:00:00",
            "ended_at": "2026-05-03T00:00:00", "id": "p2",
            "last_activity_at": None, "last_message_preview": None,
            "last_session_summary": None, "message_count": 0,
            "progress": {
                "focus_target_gap": None, "level": "intermediate",
                "mastered_count": 1,
            },
            "topic": "sql-2",
        },
        {
            "created_at": "2026-05-01T00:00:00", "ended_at": None, "id": "p1",
            "last_activity_at": None, "last_message_preview": None,
            "last_session_summary": None, "message_count": 0,
            "progress": {
                "focus_target_gap": None, "level": "beginner", "mastered_count": 2,
            },
            "topic": "sql",
        },
    ],
    "weekly_mastery": [
        {"count": 0, "week_start": "2026-03-30"},
        {"count": 0, "week_start": "2026-04-06"},
        {"count": 0, "week_start": "2026-04-13"},
        {"count": 0, "week_start": "2026-04-20"},
        {"count": 0, "week_start": "2026-04-27"},
        {"count": 1, "week_start": "2026-05-04"},
        {"count": 0, "week_start": "2026-05-11"},
        {"count": 0, "week_start": "2026-05-18"},
        {"count": 0, "week_start": "2026-05-25"},
        {"count": 0, "week_start": "2026-06-01"},
        {"count": 0, "week_start": "2026-06-08"},
        {"count": 0, "week_start": "2026-06-15"},
    ],
}


def test_aggregate_response_matches_pre_change_pin(db_session):
    """F-08 regression pin: the optimisation must not move a single field."""
    from services import profile_insights

    _seed_pin_fixture(db_session)
    result = profile_insights.aggregate_for_user(db_session, PIN_USER, now=AGG_NOW)
    assert result.model_dump(mode="json") == AGGREGATE_PIN


def test_aggregate_does_not_load_full_session_rows(db_session):
    """F-08: the sessions scan must project only the columns the aggregate
    reads. Loading whole ORM rows drags kw_index_json and the rolling summary
    for every session the user has ever created."""
    from services import profile_insights

    _seed_pin_fixture(db_session)
    with capture_statements(db_session) as stmts:
        profile_insights.aggregate_for_user(db_session, PIN_USER, now=AGG_NOW)

    session_selects = [s for s in stmts if "FROM sessions" in s]
    assert session_selects, stmts
    for s in session_selects:
        assert "sessions.kw_index_json" not in s, s
        assert "sessions.rolling_summary" not in s, s


def test_aggregate_statement_count_does_not_grow_with_sessions(db_session):
    """F-08: statement count is constant in the number of sessions."""
    from services import profile_insights

    _seed_pin_fixture(db_session)
    with capture_statements(db_session) as small:
        profile_insights.aggregate_for_user(db_session, PIN_USER, now=AGG_NOW)
    baseline = len(small)

    for i in range(50):
        _mk_raw(
            db_session, f"bulk{i}", user_id=PIN_USER, topic=f"t{i}",
            created_at=AGG_T0 - timedelta(days=i + 1),
            profile_json=TopicProfile(
                knowledge_level="beginner",
                mastered_concepts=[{"name": f"c{i}"}],
            ).model_dump_json(),
        )
    db_session.commit()

    with capture_statements(db_session) as large:
        profile_insights.aggregate_for_user(db_session, PIN_USER, now=AGG_NOW)

    assert len(large) == baseline, (baseline, len(large))
    assert baseline <= 6, baseline


# --- G-14: the insights half lives in its own module ---

MOVED_NAMES = ("aggregate_for_user", "_learning_insights", "_monday")


def test_insights_module_owns_the_moved_names():
    from services import profile_insights

    for name in MOVED_NAMES:
        assert hasattr(profile_insights, name), name


def test_profile_service_keeps_no_re_export_shim():
    """A shim would leave the old coupling in place and hide missed callers."""
    from services import profile_service

    for name in MOVED_NAMES:
        assert not hasattr(profile_service, name), name


def test_profile_service_does_not_import_profile_insights():
    """One-way dependency: insights -> service, never the reverse."""
    import ast
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "services" / "profile_service.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "profile_insights" not in alias.name, ast.dump(node)
        elif isinstance(node, ast.ImportFrom):
            assert "profile_insights" not in (node.module or ""), ast.dump(node)
            for alias in node.names:
                assert alias.name != "profile_insights", ast.dump(node)


def test_aggregate_route_calls_the_insights_module(db_session, client, monkeypatch):
    """The route is repointed, not just the tests."""
    from services import profile_insights

    calls: list[str] = []
    real = profile_insights.aggregate_for_user

    def _spy(db, user_id, now=None):
        calls.append(user_id)
        return real(db, user_id, now=now)

    monkeypatch.setattr("routes.profile.profile_insights.aggregate_for_user", _spy)
    r = client.get("/api/profile/aggregate")
    assert r.status_code == 200, r.text
    assert calls == ["test-user"]
