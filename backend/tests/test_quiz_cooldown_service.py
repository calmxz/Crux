"""TDD: sessions.quiz_cooldown_json column + cooldown helpers."""

from sqlalchemy import inspect

from db.models import Session as SessionModel
from db.models import User


def test_session_has_quiz_cooldown_column(db_session):
    cols = {c["name"] for c in inspect(db_session.get_bind()).get_columns("sessions")}
    assert "quiz_cooldown_json" in cols


from services import check_service as cqs


def _seed_session(db, sid="s1", uid="u1"):
    db.add(User(id=uid))
    db.add(SessionModel(id=sid, user_id=uid, topic="t", topic_profile_json="{}"))
    db.commit()


def _resolved_pc(results):
    """results: list of 'correct' | 'wrong' | 'skip'."""
    items = []
    for n, r in enumerate(results):
        items.append(
            {
                "question": f"q{n}",
                "options": ["a", "b"],
                "correct_index": 0,
                "explanation": "e",
                "status": "skipped" if r == "skip" else "answered",
                "selected_index": None if r == "skip" else (0 if r == "correct" else 1),
                "correct": None if r == "skip" else (r == "correct"),
            }
        )
    return {
        "gap": "derivatives",
        "current_index": len(items),
        "asked_at_turn": "2026-06-05T00:00:00",
        "items": items,
    }


def test_build_quiz_cooldown_none_when_all_correct():
    pc = _resolved_pc(["correct", "correct"])
    assert cqs._build_cooldown(pc) is None


def test_build_quiz_cooldown_set_on_miss():
    pc = _resolved_pc(["correct", "wrong"])
    cd = cqs._build_cooldown(pc)
    assert cd == {
        "gap": "derivatives",
        "last_score": "1/2",
        "missed": [{"question": "q1", "chosen": "b", "correct": "a"}],
    }


def test_build_quiz_cooldown_set_on_skip():
    pc = _resolved_pc(["correct", "skip"])
    cd = cqs._build_cooldown(pc)
    assert cd is not None
    assert cd["gap"] == "derivatives"
    assert cd["last_score"] == "1/1"  # graded excludes skips


from datetime import datetime, timezone

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs


def _one_item_args(sid="s1"):
    return AskCheckQuestionsArgs(
        set_index=1,
        set_total=1,
        session_id=sid,
        gap="derivatives",
        items=[
            {
                "question": "q0",
                "options": ["a", "b"],
                "correct_index": 0,
                "explanation": "e",
            }
        ],
    )


def test_register_blocked_when_suppress_check(db_session):
    db = db_session
    _seed_session(db)
    ctx = ToolContext(
        db=db,
        session_id="s1",
        user_id="u1",
        turn_started_at=datetime.now(timezone.utc),
        suppress_check=True,
    )
    res = cqs.register(db, ctx, _one_item_args())
    assert res.ok is False
    assert cqs.open_set(db.get(SessionModel, "s1")) is None  # no batch opened


def test_register_allowed_when_not_suppressed(db_session):
    db = db_session
    _seed_session(db)
    ctx = ToolContext(
        db=db,
        session_id="s1",
        user_id="u1",
        turn_started_at=datetime.now(timezone.utc),
    )
    res = cqs.register(db, ctx, _one_item_args())
    assert res.ok is True
    assert cqs.open_set(db.get(SessionModel, "s1")) is not None


def test_quiz_cooldown_matches_db_variant():
    row = SessionModel(
        user_id="u", topic="t", quiz_cooldown_json='{"gap": "g", "last_score": "1/2", "missed": []}'
    )
    cd = cqs.quiz_cooldown(row)
    assert cd == {"gap": "g", "last_score": "1/2", "missed": []}


def test_quiz_cooldown_bad_json_returns_none():
    row = SessionModel(user_id="u", topic="t", quiz_cooldown_json="{nope")
    assert cqs.quiz_cooldown(row) is None


def test_open_set_parses_the_row():
    row = SessionModel(user_id="u", topic="t", pending_check_json='{"gap": "g", "items": []}')
    assert cqs.open_set(row) == {"gap": "g", "items": []}


def test_build_quiz_cooldown_missed_carries_chosen_vs_correct():
    pc = {
        "gap": "g",
        "items": [
            {
                "question": "Q1?",
                "options": ["a", "b"],
                "selected_index": 0,
                "correct_index": 1,
                "status": "answered",
                "correct": False,
            },
            {
                "question": "Q2?",
                "options": ["x", "y"],
                "selected_index": 1,
                "correct_index": 1,
                "status": "answered",
                "correct": True,
            },
        ],
    }
    cd = cqs._build_cooldown(pc)
    assert cd["missed"] == [{"question": "Q1?", "chosen": "a", "correct": "b"}]
