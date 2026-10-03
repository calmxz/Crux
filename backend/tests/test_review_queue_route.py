from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import event as _sa_event

from db.models import LearningEvent, User
from db.models import Session as SessionModel


@contextmanager
def count_queries(db):
    bind = db.get_bind()
    state = {"n": 0}

    def _before(conn, cursor, statement, params, context, executemany):
        state["n"] += 1

    _sa_event.listen(bind, "before_cursor_execute", _before)
    try:
        yield state
    finally:
        _sa_event.remove(bind, "before_cursor_execute", _before)

# F-07: the queue now only scans the last REVIEW_WINDOW_DAYS days, so the
# shared fixture timestamp must stay relative to "now" -- a hard-coded date
# silently falls out of the window as the calendar moves.
T0 = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=3)


def _seed_session(db, session_id="s1", user_id="test-user", topic="biology"):
    if not db.get(User, user_id):
        db.add(User(id=user_id))
    db.add(SessionModel(id=session_id, user_id=user_id, topic=topic))
    db.commit()


def _seed_event(db, session_id, gap, correct, created_at, purpose=None):
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


def test_empty_queue(client, db_session):
    r = client.get("/api/review/queue")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["limit"] == 20
    assert body["offset"] == 0


def test_due_concept_appears_with_fields(client, db_session):
    _seed_session(db_session)
    # incorrect answer 3 days ago -> streak 0 -> due 1 day later -> overdue now
    _seed_event(db_session, "s1", "mitosis", False, T0)
    r = client.get("/api/review/queue")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["concept"] == "mitosis"
    assert item["source_session_id"] == "s1"
    assert item["source_topic"] == "biology"
    assert item["streak"] == 0
    assert item["last_tested_at"].startswith(T0.date().isoformat())
    assert item["due_at"].startswith((T0 + timedelta(days=1)).date().isoformat())


def test_not_yet_due_concept_excluded(client, db_session):
    _seed_session(db_session)
    # correct answer just now -> streak 1 -> due in 1 day -> not due yet
    _seed_event(
        db_session, "s1", "osmosis", True, datetime.now(timezone.utc)
    )
    r = client.get("/api/review/queue")
    assert r.json()["total"] == 0


def test_queue_query_count_constant_in_session_count(client, db_session):
    # The evidence map must be built from one batched session fetch, not one
    # profile load per distinct session (N+1 on every sidebar boot).
    _seed_session(db_session, session_id="qc1", topic="t-qc1")
    _seed_event(db_session, "qc1", "g-qc1", False, T0)
    with count_queries(db_session) as q1:
        assert client.get("/api/review/queue").status_code == 200

    for n in range(2, 6):
        _seed_session(db_session, session_id=f"qc{n}", topic=f"t-qc{n}")
        _seed_event(db_session, f"qc{n}", f"g-qc{n}", False, T0)
    with count_queries(db_session) as q5:
        assert client.get("/api/review/queue").status_code == 200

    assert q5["n"] == q1["n"], f"N+1: 1-session={q1['n']} vs 5-session={q5['n']}"


def test_cross_session_aggregation_and_pagination(client, db_session):
    _seed_session(db_session, session_id="s1", topic="biology")
    _seed_session(db_session, session_id="s2", topic="chemistry")
    _seed_event(db_session, "s1", "older", False, T0)
    _seed_event(db_session, "s2", "newer", False, T0 + timedelta(days=1))
    r = client.get("/api/review/queue", params={"limit": 1, "offset": 0})
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["concept"] == "older"  # most overdue first
    r2 = client.get("/api/review/queue", params={"limit": 1, "offset": 1})
    assert r2.json()["items"][0]["concept"] == "newer"


def test_user_isolation(client, db_session):
    _seed_session(db_session, session_id="s1", user_id="other-user")
    _seed_event(db_session, "s1", "mitosis", False, T0)
    # default client auth resolves to "test-user"; other-user's events invisible
    r = client.get("/api/review/queue")
    assert r.json()["total"] == 0


def test_queue_rejects_invalid_token(client, db_session):
    # conftest fake auth: a bearer token not prefixed "test-" raises 401
    r = client.get(
        "/api/review/queue", headers={"Authorization": "Bearer bogus"}
    )
    assert r.status_code == 401


def test_queue_makes_no_llm_call(client, db_session, monkeypatch):
    import litellm

    def _boom(*args, **kwargs):
        raise AssertionError("queue path must not call the LLM")

    monkeypatch.setattr(litellm, "acompletion", _boom, raising=False)
    monkeypatch.setattr(litellm, "completion", _boom, raising=False)
    _seed_session(db_session)
    _seed_event(db_session, "s1", "mitosis", False, T0)
    r = client.get("/api/review/queue")
    assert r.status_code == 200
    assert r.json()["total"] == 1


def test_diagnostic_events_excluded_from_queue(client, db_session):
    """Final-review Finding 1: diagnostic probes must not appear as due concepts."""
    _seed_session(db_session)
    _seed_event(db_session, "s1", "mitosis", False, T0, purpose="diagnostic")
    assert client.get("/api/review/queue").json()["total"] == 0


def test_non_diagnostic_events_still_appear_alongside_diagnostic(client, db_session):
    _seed_session(db_session)
    _seed_event(db_session, "s1", "mitosis", False, T0, purpose="diagnostic")
    _seed_event(db_session, "s1", "osmosis", False, T0, purpose="check")
    body = client.get("/api/review/queue").json()
    assert body["total"] == 1
    assert body["items"][0]["concept"] == "osmosis"


def test_review_queue_orders_declared_before_tested(client, db_session):
    """R4.2 AC2: weakly-evidenced concepts (declared/None) surface before
    tested ones, even when the tested concept is more overdue."""
    from contracts import ConceptEntry
    from services import profile_service

    _seed_session(db_session, session_id="s1", topic="biology")
    # "alpha" more overdue (older event) but evidenced as tested
    _seed_event(db_session, "s1", "alpha", False, T0)
    # "beta" less overdue but only declared evidence
    _seed_event(db_session, "s1", "beta", False, T0 + timedelta(days=1))

    profile = profile_service.load_profile(db_session, "s1")
    profile.mastered_concepts = [
        ConceptEntry(name="alpha", evidence_type="tested"),
        ConceptEntry(name="beta", evidence_type="declared"),
    ]
    profile_service.save_profile(db_session, "s1", profile)

    body = client.get("/api/review/queue").json()
    concepts = [i["concept"] for i in body["items"]]
    assert concepts.index("beta") < concepts.index("alpha")


def test_grading_updates_schedule(client, db_session):
    """R2.2 AC3: completing a check moves due_at (via the events, no writes here)."""
    from services import learning_event_service

    _seed_session(db_session)
    # one correct answer 2 days ago -> streak 1 -> interval 1 day -> due (overdue)
    _seed_event(
        db_session,
        "s1",
        "mitosis",
        True,
        datetime.now(timezone.utc) - timedelta(days=2),
    )
    assert client.get("/api/review/queue").json()["total"] == 1

    # grade another correct answer now (same path check answers use)
    learning_event_service.record_from_answer(
        db_session, "s1", gap="mitosis", question="q2", correct=True
    )

    # streak 2 -> interval 2 days from now -> no longer due
    assert client.get("/api/review/queue").json()["total"] == 0


def test_events_outside_review_window_are_excluded(client, db_session):
    """F-07: the queue scans a bounded window. A concept last touched more
    than REVIEW_WINDOW_DAYS ago has fallen off the schedule and must not be
    returned (nor scanned)."""
    from services.review_queue_service import REVIEW_WINDOW_DAYS

    _seed_session(db_session)
    stale = datetime.now(timezone.utc) - timedelta(days=REVIEW_WINDOW_DAYS + 5)
    _seed_event(db_session, "s1", "ancient", False, stale)
    body = client.get("/api/review/queue").json()
    assert body["total"] == 0
    assert body["items"] == []


def test_total_counts_only_due_concepts_inside_window(client, db_session):
    """F-07: `total` must reflect the windowed due list, not every event."""
    from services.review_queue_service import REVIEW_WINDOW_DAYS

    _seed_session(db_session)
    stale = datetime.now(timezone.utc) - timedelta(days=REVIEW_WINDOW_DAYS + 5)
    _seed_event(db_session, "s1", "ancient", False, stale)
    _seed_event(db_session, "s1", "recent", False, T0)
    body = client.get("/api/review/queue").json()
    assert body["total"] == 1
    assert [i["concept"] for i in body["items"]] == ["recent"]


def test_streak_uses_full_in_window_history_not_just_latest_event(client, db_session):
    """F-07 regression guard: bounding the scan must not degrade into a
    latest-event-only query -- streak is the trailing run of correct answers,
    so three correct answers inside the window give streak 3 (interval 4 days)."""
    now = datetime.now(timezone.utc)
    _seed_session(db_session)
    _seed_event(db_session, "s1", "mitosis", True, now - timedelta(days=12))
    _seed_event(db_session, "s1", "mitosis", True, now - timedelta(days=9))
    _seed_event(db_session, "s1", "mitosis", True, now - timedelta(days=6))
    body = client.get("/api/review/queue").json()
    assert body["total"] == 1
    assert body["items"][0]["streak"] == 3


def test_review_window_covers_the_longest_interval():
    """The window must be at least MAX_INTERVAL_DAYS, or a concept scheduled
    far out would be dropped before it ever became due."""
    from services.review_queue_service import MAX_INTERVAL_DAYS, REVIEW_WINDOW_DAYS

    assert REVIEW_WINDOW_DAYS >= MAX_INTERVAL_DAYS
