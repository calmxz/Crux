"""#420: the check module owns the Set lifecycle, its row lock and its commit.

Module-level, no HTTP and no LLM. Each action commits exactly once and
releases the session row lock on every return path, early exits and
conflicts included. Abandon joins the caller's transaction and never commits.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import event

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, LearningEvent, User
from db.models import Session as SessionModel
from lib.error_codes import CHECK_CONFLICT, NO_OPEN_CHECK, NO_RESOLVED_BATCH, SESSION_ENDED
from services import check_service, profile_service

USER_ID = "u_check_service"
SID = "s_check_service"


def _items(n=2):
    return [
        {"question": f"Q{i}?", "options": ["a", "b"], "correct_index": 0, "explanation": "a."}
        for i in range(n)
    ]


def _ctx(db, *, diagnostic=False, suppress=False):
    return ToolContext(
        db=db,
        session_id=SID,
        user_id=USER_ID,
        turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        diagnostic_required=diagnostic,
        suppress_check=suppress,
    )


def _args(set_index=1, set_total=1, gap="atp", n=2):
    return AskCheckQuestionsArgs(
        session_id=SID, gap=gap, set_index=set_index, set_total=set_total, items=_items(n)
    )


@pytest.fixture
def db(db_session):
    db_session.add(User(id=USER_ID))
    db_session.add(
        SessionModel(
            id=SID,
            user_id=USER_ID,
            topic="bio",
            topic_profile_json=TopicProfile(knowledge_level="intermediate").model_dump_json(),
        )
    )
    db_session.commit()
    return db_session


@pytest.fixture
def commits(db):
    seen = []

    def on_commit(session):
        seen.append(session)

    event.listen(db, "after_commit", on_commit)
    yield seen
    event.remove(db, "after_commit", on_commit)


def _row(db):
    db.expire_all()
    return db.get(SessionModel, SID)


def _open(db, *, set_total=1, diagnostic=False, n=2):
    assert check_service.register(db, _ctx(db, diagnostic=diagnostic), _args(1, set_total, n=n)).ok
    msg = ChatMessage(session_id=SID, role="assistant", content="")
    db.add(msg)
    db.commit()
    check_service.stamp_message_id(db, SID, msg.id)
    return msg


def _set_level(db, level):
    profile = profile_service.load_profile(db, SID)
    profile.knowledge_level = level
    profile_service.save_profile(db, SID, profile)


# --- 1. Each action: state and one commit -----------------------------------


def test_register_opens_a_set_in_one_commit(db, commits):
    result = check_service.register(db, _ctx(db), _args())
    assert result.ok
    assert len(commits) == 1
    pc = check_service.open_set(_row(db))
    assert pc["gap"] == "atp" and [it["status"] for it in pc["items"]] == ["pending", "pending"]
    assert check_service.current_check(_row(db))["last_set_index"] == 1


def test_stamp_links_the_open_set_in_one_commit(db, commits):
    check_service.register(db, _ctx(db), _args())
    commits.clear()
    check_service.stamp_message_id(db, SID, 42)
    assert len(commits) == 1
    assert check_service.open_set_message_id(db, SID) == 42


def test_answer_records_the_event_in_one_commit(db, commits):
    _open(db)
    commits.clear()
    result = check_service.answer(db, SID, 0, 0)
    assert result["correct"] is True and result["done"] is False
    assert len(commits) == 1
    assert check_service.open_set(_row(db))["items"][0]["status"] == "answered"
    assert db.query(LearningEvent).count() == 1


def test_skip_marks_the_item_in_one_commit(db, commits):
    _open(db)
    commits.clear()
    assert check_service.skip(db, SID, 1)["current_index"] == 0
    assert len(commits) == 1
    assert check_service.open_set(_row(db))["items"][1]["status"] == "skipped"
    assert db.query(LearningEvent).count() == 0


def test_complete_closes_the_set_in_one_commit(db, commits):
    msg = _open(db)
    check_service.answer(db, SID, 0, 0)
    check_service.answer(db, SID, 1, 1)
    commits.clear()
    summary, cooldown = check_service.complete(db, SID)
    assert len(commits) == 1
    assert summary.startswith("[check results] gap=atp: 1/2 correct.")
    assert cooldown["last_score"] == "1/2"
    row = _row(db)
    assert check_service.open_set(row) is None
    assert check_service.current_check(row) is None
    assert check_service.quiz_cooldown(row) == cooldown
    assert check_service.recap_for_message(db, db.get(ChatMessage, msg.id))["current_index"] == 2


def test_complete_of_a_non_final_diagnostic_set_keeps_the_pointer(db, commits):
    _set_level(db, None)
    _open(db, set_total=2, diagnostic=True)
    check_service.answer(db, SID, 0, 0)
    check_service.answer(db, SID, 1, 0)
    commits.clear()
    check_service.complete(db, SID)
    assert len(commits) == 1
    cc = check_service.current_check(_row(db))
    assert cc["diag"] == {"correct": 2, "answered": 2, "items": 2}
    assert profile_service.load_profile(db, SID).knowledge_level is None


def test_stop_closes_the_open_set_in_one_commit(db, commits):
    msg = _open(db, set_total=2)
    check_service.answer(db, SID, 0, 0)
    commits.clear()
    summary, cooldown = check_service.stop(db, SID)
    assert len(commits) == 1
    assert "learner stopped at set 1 of 2." in summary
    assert "Q2 skipped." in summary
    assert cooldown["last_score"] == "1/1"
    row = _row(db)
    assert check_service.open_set(row) is None and check_service.current_check(row) is None
    recap = check_service.recap_for_message(db, db.get(ChatMessage, msg.id))
    assert [it["status"] for it in recap["items"]] == ["answered", "skipped"]


def test_stop_between_sets_ends_the_check_in_one_commit(db, commits):
    _open(db, set_total=2)
    check_service.answer(db, SID, 0, 0)
    check_service.answer(db, SID, 1, 1)
    _, cooldown = check_service.complete(db, SID)
    commits.clear()
    summary, stop_cooldown = check_service.stop(db, SID)
    assert len(commits) == 1
    assert summary == "[check results] learner stopped at set 1 of 2."
    assert stop_cooldown == cooldown
    assert check_service.current_check(_row(db)) is None


def test_stop_grades_a_diagnostic_from_what_was_answered(db):
    _set_level(db, None)
    _open(db, set_total=2, diagnostic=True, n=3)
    check_service.answer(db, SID, 0, 0)
    check_service.answer(db, SID, 1, 0)
    check_service.stop(db, SID)
    db.expire_all()
    assert profile_service.load_profile(db, SID).knowledge_level == "intermediate"


def test_abandon_freezes_the_set_and_grades_without_committing(db, commits):
    _set_level(db, None)
    msg = _open(db, diagnostic=True, n=3)
    check_service.answer(db, SID, 0, 0)
    commits.clear()
    assert check_service.abandon_in_caller_transaction(db, SID) is True
    assert commits == []
    db.commit()
    row = _row(db)
    assert check_service.open_set(row) is None and check_service.current_check(row) is None
    assert check_service.quiz_cooldown(row) is None
    recap = check_service.recap_for_message(db, db.get(ChatMessage, msg.id))
    assert [it["status"] for it in recap["items"]] == ["answered", "skipped", "skipped"]
    assert profile_service.load_profile(db, SID).knowledge_level == "beginner"


# --- 2. Every action releases the lock on early exit ------------------------


def test_stamp_with_no_open_set_releases_the_lock(db, commits):
    check_service.stamp_message_id(db, SID, 42)
    assert not db.in_transaction()
    assert len(commits) == 1


def test_register_refused_with_a_set_open_releases_the_lock(db):
    _open(db)
    result = check_service.register(db, _ctx(db), _args())
    assert not result.ok
    assert not db.in_transaction()


def test_register_refused_out_of_order_releases_the_lock(db):
    result = check_service.register(db, _ctx(db), _args(set_index=2, set_total=2))
    assert not result.ok
    assert not db.in_transaction()


@pytest.mark.parametrize(
    "action",
    [
        lambda db: check_service.answer(db, SID, 0, 0),
        lambda db: check_service.answer(db, SID, 5, 0),
        lambda db: check_service.answer(db, SID, 1, 9),
        lambda db: check_service.skip(db, SID, 0),
        lambda db: check_service.skip(db, SID, -1),
    ],
    ids=[
        "answer-resolved",
        "answer-out-of-range",
        "answer-bad-option",
        "skip-resolved",
        "skip-out-of-range",
    ],
)
def test_answer_or_skip_conflict_releases_the_lock(db, action):
    _open(db)
    check_service.answer(db, SID, 0, 0)
    with pytest.raises(check_service.CheckError) as exc:
        action(db)
    assert exc.value.code == CHECK_CONFLICT
    assert exc.value.message
    assert not db.in_transaction()


def test_answer_with_no_open_set_releases_the_lock(db):
    with pytest.raises(check_service.CheckError) as exc:
        check_service.answer(db, SID, 0, 0)
    assert exc.value.code == CHECK_CONFLICT
    assert not db.in_transaction()


def test_complete_with_an_unresolved_set_releases_the_lock(db):
    _open(db)
    with pytest.raises(check_service.CheckError) as exc:
        check_service.complete(db, SID)
    assert exc.value.code == NO_RESOLVED_BATCH
    assert exc.value.message is None
    assert not db.in_transaction()
    assert check_service.open_set(_row(db)) is not None


def test_stop_with_no_check_releases_the_lock(db):
    with pytest.raises(check_service.CheckError) as exc:
        check_service.stop(db, SID)
    assert exc.value.code == NO_OPEN_CHECK
    assert exc.value.message is None
    assert not db.in_transaction()


def test_stop_on_a_fully_answered_set_releases_the_lock(db):
    _open(db)
    check_service.answer(db, SID, 0, 0)
    check_service.answer(db, SID, 1, 0)
    with pytest.raises(check_service.CheckError) as exc:
        check_service.stop(db, SID)
    assert exc.value.code == NO_OPEN_CHECK
    assert not db.in_transaction()
    assert check_service.open_set(_row(db)) is not None


@pytest.mark.parametrize(
    ("action", "resolved"),
    [
        (lambda db: check_service.answer(db, SID, 0, 0), False),
        (lambda db: check_service.skip(db, SID, 0), False),
        (lambda db: check_service.complete(db, SID), True),
        (lambda db: check_service.stop(db, SID), False),
    ],
    ids=["answer", "skip", "complete", "stop"],
)
def test_learner_action_after_session_end_is_refused_under_the_lock(db, action, resolved):
    """Carried from #418: an action queued behind a session end's claim
    rechecks ended_at under the lock instead of writing to an ended session
    (the end's abandon has not run yet, so the Set is still open)."""
    _open(db)
    if resolved:
        check_service.answer(db, SID, 0, 0)
        check_service.answer(db, SID, 1, 0)
    before = check_service.open_set(_row(db))
    events = db.query(LearningEvent).count()
    _row(db).ended_at = datetime.now(timezone.utc)
    db.commit()
    with pytest.raises(check_service.CheckError) as exc:
        action(db)
    assert exc.value.code == SESSION_ENDED
    assert exc.value.message is None
    assert not db.in_transaction()
    assert db.query(LearningEvent).count() == events
    row = _row(db)
    assert check_service.open_set(row) == before
    assert check_service.quiz_cooldown(row) is None


# --- 3. Abandon never commits -----------------------------------------------


@pytest.mark.parametrize("state", ["none", "open-set", "between-sets"])
def test_abandon_never_commits(db, commits, state):
    if state != "none":
        _open(db, set_total=2)
    if state == "between-sets":
        check_service.answer(db, SID, 0, 0)
        check_service.answer(db, SID, 1, 0)
        check_service.complete(db, SID)
    commits.clear()
    _row(db)  # open the caller's transaction
    assert db.in_transaction()
    check_service.abandon_in_caller_transaction(db, SID)
    assert commits == []
    assert db.in_transaction()
    db.rollback()
