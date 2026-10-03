"""TDD: sessions.quiz_cooldown_json column + cooldown helpers."""
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base
from db.models import Session as SessionModel
from db.models import User


def _make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_session_has_quiz_cooldown_column():
    db = _make_session()
    cols = {c["name"] for c in inspect(db.get_bind()).get_columns("sessions")}
    assert "quiz_cooldown_json" in cols


from services import check_question_service as cqs
from services import pending_check_store


def _seed_session(db, sid="s1", uid="u1"):
    db.add(User(id=uid))
    db.add(SessionModel(id=sid, user_id=uid, topic="t", topic_profile_json="{}"))
    db.commit()


def _resolved_pc(results):
    """results: list of 'correct' | 'wrong' | 'skip'."""
    items = []
    for n, r in enumerate(results):
        items.append({
            "question": f"q{n}",
            "options": ["a", "b"],
            "correct_index": 0,
            "explanation": "e",
            "status": "skipped" if r == "skip" else "answered",
            "selected_index": None if r == "skip" else (0 if r == "correct" else 1),
            "correct": None if r == "skip" else (r == "correct"),
        })
    return {"gap": "derivatives", "current_index": len(items), "asked_at_turn": "2026-06-05T00:00:00", "items": items}


def test_build_quiz_cooldown_none_when_all_correct():
    pc = _resolved_pc(["correct", "correct"])
    assert cqs.build_quiz_cooldown(pc) is None


def test_build_quiz_cooldown_set_on_miss():
    pc = _resolved_pc(["correct", "wrong"])
    cd = cqs.build_quiz_cooldown(pc)
    assert cd == {
        "gap": "derivatives",
        "last_score": "1/2",
        "missed": [{"question": "q1", "chosen": "b", "correct": "a"}],
    }


def test_build_quiz_cooldown_set_on_skip():
    pc = _resolved_pc(["correct", "skip"])
    cd = cqs.build_quiz_cooldown(pc)
    assert cd is not None
    assert cd["gap"] == "derivatives"
    assert cd["last_score"] == "1/1"  # graded excludes skips


def test_set_get_clear_quiz_cooldown_roundtrip():
    db = _make_session()
    _seed_session(db)
    assert cqs.get_quiz_cooldown(db, "s1") is None
    cqs.set_quiz_cooldown(db, "s1", {"gap": "g", "last_score": "0/1", "missed": ["q0"]})
    assert cqs.get_quiz_cooldown(db, "s1") == {"gap": "g", "last_score": "0/1", "missed": ["q0"]}
    cqs.set_quiz_cooldown(db, "s1", None)
    assert cqs.get_quiz_cooldown(db, "s1") is None


from datetime import datetime, timezone

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs


def _one_item_args(sid="s1"):
    return AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=sid,
        gap="derivatives",
        items=[{
            "question": "q0",
            "options": ["a", "b"],
            "correct_index": 0,
            "explanation": "e",
        }],
    )


def test_register_blocked_when_suppress_check():
    db = _make_session()
    _seed_session(db)
    ctx = ToolContext(
        db=db, session_id="s1", user_id="u1",
        turn_started_at=datetime.now(timezone.utc), suppress_check=True,
    )
    res = cqs.register(db, ctx, _one_item_args())
    assert res.ok is False
    assert cqs.get_pending_check(db, "s1") is None  # no batch opened


def test_register_allowed_when_not_suppressed():
    db = _make_session()
    _seed_session(db)
    ctx = ToolContext(
        db=db, session_id="s1", user_id="u1",
        turn_started_at=datetime.now(timezone.utc),
    )
    res = cqs.register(db, ctx, _one_item_args())
    assert res.ok is True
    assert cqs.get_pending_check(db, "s1") is not None


def test_get_quiz_cooldown_from_row_matches_db_variant():
    row = SessionModel(user_id="u", topic="t",
                       quiz_cooldown_json='{"gap": "g", "last_score": "1/2", "missed": []}')
    cd = cqs.get_quiz_cooldown_from_row(row)
    assert cd == {"gap": "g", "last_score": "1/2", "missed": []}


def test_get_quiz_cooldown_from_row_bad_json_returns_none():
    row = SessionModel(user_id="u", topic="t", quiz_cooldown_json="{nope")
    assert cqs.get_quiz_cooldown_from_row(row) is None


def test_get_pending_check_from_row_parses():
    row = SessionModel(user_id="u", topic="t",
                       pending_check_json='{"gap": "g", "items": []}')
    assert pending_check_store.get_pending_check_from_row(row) == {"gap": "g", "items": []}


def test_build_quiz_cooldown_missed_carries_chosen_vs_correct():
    pc = {
        "gap": "g",
        "items": [
            {"question": "Q1?", "options": ["a", "b"], "selected_index": 0,
             "correct_index": 1, "status": "answered", "correct": False},
            {"question": "Q2?", "options": ["x", "y"], "selected_index": 1,
             "correct_index": 1, "status": "answered", "correct": True},
        ],
    }
    cd = cqs.build_quiz_cooldown(pc)
    assert cd["missed"] == [{"question": "Q1?", "chosen": "a", "correct": "b"}]
