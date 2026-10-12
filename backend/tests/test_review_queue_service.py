from datetime import datetime, timedelta, timezone

from services.review_queue_service import (
    BASE_INTERVAL_DAYS,
    MAX_INTERVAL_DAYS,
    EventRow,
    compute_schedule,
)

T0 = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)


def _ev(concept, correct, at, session_id="s1", topic="biology"):
    return EventRow(
        concept=concept,
        correct=correct,
        created_at=at,
        session_id=session_id,
        topic=topic,
    )


def test_empty_events_yield_empty_schedule():
    assert compute_schedule([], now=T0) == []


def test_incorrect_answer_due_after_base_interval():
    events = [_ev("mitosis", False, T0)]
    not_yet = compute_schedule(events, now=T0 + timedelta(hours=23))
    assert not_yet == []
    due = compute_schedule(events, now=T0 + timedelta(days=BASE_INTERVAL_DAYS))
    assert len(due) == 1
    assert due[0].concept == "mitosis"
    assert due[0].streak == 0
    assert due[0].due_at == T0 + timedelta(days=BASE_INTERVAL_DAYS)


def test_streak_doubles_interval():
    # three consecutive corrects -> streak 3 -> interval 2^(3-1) = 4 days
    events = [
        _ev("mitosis", True, T0),
        _ev("mitosis", True, T0 + timedelta(days=1)),
        _ev("mitosis", True, T0 + timedelta(days=3)),
    ]
    last = T0 + timedelta(days=3)
    assert compute_schedule(events, now=last + timedelta(days=3)) == []
    due = compute_schedule(events, now=last + timedelta(days=4))
    assert len(due) == 1
    assert due[0].streak == 3
    assert due[0].due_at == last + timedelta(days=4)


def test_incorrect_resets_streak():
    # correct, correct, incorrect -> streak 0 -> due after base interval
    events = [
        _ev("osmosis", True, T0),
        _ev("osmosis", True, T0 + timedelta(days=1)),
        _ev("osmosis", False, T0 + timedelta(days=2)),
    ]
    due = compute_schedule(events, now=T0 + timedelta(days=3))
    assert len(due) == 1
    assert due[0].streak == 0
    assert due[0].due_at == T0 + timedelta(days=2) + timedelta(days=BASE_INTERVAL_DAYS)


def test_interval_capped_at_max():
    # 8 consecutive corrects -> raw 2^7 = 128 days -> capped at MAX_INTERVAL_DAYS
    events = [_ev("photosynthesis", True, T0 + timedelta(days=i)) for i in range(8)]
    last = T0 + timedelta(days=7)
    assert compute_schedule(events, now=last + timedelta(days=MAX_INTERVAL_DAYS - 1)) == []
    due = compute_schedule(events, now=last + timedelta(days=MAX_INTERVAL_DAYS))
    assert len(due) == 1
    assert due[0].due_at == last + timedelta(days=MAX_INTERVAL_DAYS)


def test_concepts_group_by_casefolded_stripped_key():
    events = [
        _ev("Bayes Theorem", False, T0, session_id="s1"),
        _ev("  bayes theorem ", True, T0 + timedelta(days=1), session_id="s2", topic="stats"),
    ]
    due = compute_schedule(events, now=T0 + timedelta(days=3))
    assert len(due) == 1
    # display string and source come from the most recent event in the group
    assert due[0].concept == "  bayes theorem "
    assert due[0].source_session_id == "s2"
    assert due[0].source_topic == "stats"
    assert due[0].streak == 1


def test_blank_concepts_are_skipped():
    events = [_ev("   ", False, T0)]
    assert compute_schedule(events, now=T0 + timedelta(days=2)) == []


def test_sorted_most_overdue_first():
    events = [
        _ev("newer", False, T0 + timedelta(days=5), session_id="s2"),
        _ev("older", False, T0, session_id="s1"),
    ]
    due = compute_schedule(events, now=T0 + timedelta(days=10))
    assert [e.concept for e in due] == ["older", "newer"]


def test_unsorted_input_is_handled():
    # events arrive out of order; scheduler must sort within the group
    events = [
        _ev("mitosis", True, T0 + timedelta(days=2)),
        _ev("mitosis", False, T0),
    ]
    due = compute_schedule(events, now=T0 + timedelta(days=10))
    assert len(due) == 1
    assert due[0].streak == 1
    assert due[0].last_tested_at == T0 + timedelta(days=2)


def test_due_sort_puts_weak_evidence_first():
    now = datetime(2026, 7, 12, tzinfo=timezone.utc)
    old = now - timedelta(days=30)
    older = now - timedelta(days=31)
    events = [
        # "alpha" due earlier (more overdue) but tested evidence
        EventRow(concept="alpha", correct=True, created_at=older, session_id="s1", topic="t"),
        # "beta" due later but declared-only evidence
        EventRow(concept="beta", correct=True, created_at=old, session_id="s1", topic="t"),
    ]
    emap = {"alpha": "tested", "beta": "declared"}
    due = compute_schedule(events, now=now, evidence_map=emap)
    assert [e.concept for e in due] == ["beta", "alpha"]

    # without a map, ordering falls back to due_at (alpha more overdue)
    due_plain = compute_schedule(events, now=now)
    assert [e.concept for e in due_plain] == ["alpha", "beta"]
