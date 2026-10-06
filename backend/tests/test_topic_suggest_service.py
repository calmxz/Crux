"""TDD: topic_suggest_service -- the once-per-session topic card (#354)."""

import json
from datetime import datetime, timezone

import pytest

from agent.types import ToolContext
from contracts import SuggestTopicsArgs, TopicProfile
from db.models import Session as SessionModel
from db.models import User
from services import topic_suggest_service as ts

SESSION_ID = "sess_ts"
USER_ID = "u_ts"
_T0 = datetime(2026, 9, 25, 0, 0, tzinfo=timezone.utc)


def _make_session(db, *, level=None, state=ts.AWAITING_LEVEL):
    db.add(User(id=USER_ID))
    db.flush()
    row = SessionModel(
        id=SESSION_ID,
        user_id=USER_ID,
        topic="Thermodynamics",
        topic_profile_json=TopicProfile(knowledge_level=level).model_dump_json(),
        topic_suggest_state=state,
    )
    db.add(row)
    db.commit()
    return row


def _ctx(db):
    return ToolContext(db=db, session_id=SESSION_ID, user_id=USER_ID, turn_started_at=_T0)


def _args(mode="broad", n=3, **over):
    data = {
        "session_id": SESSION_ID,
        "mode": mode,
        "topic": "Thermodynamics",
        "items": [{"label": f"Subtopic {i}"} for i in range(n)],
    }
    data.update(over)
    return SuggestTopicsArgs.model_validate(data)


# --- initial_state ---------------------------------------------------------


def test_initial_state_awaits_level_when_level_unknown():
    assert ts.initial_state(None) == ts.AWAITING_LEVEL


@pytest.mark.parametrize("level", ["beginner", "intermediate", "advanced"])
def test_initial_state_none_when_session_starts_with_level(level):
    # Seeded/resumed/declared-at-create sessions never get the card.
    assert ts.initial_state(level) is None


# --- register --------------------------------------------------------------


def test_register_ok_marks_done_and_returns_card(db_session):
    _make_session(db_session, level="beginner")
    res = ts.register(db_session, _ctx(db_session), _args(n=4))
    assert res.ok, res.error
    assert res.data == {
        "mode": "broad",
        "topic": "Thermodynamics",
        "items": [{"label": f"Subtopic {i}", "hint": None} for i in range(4)],
    }
    db_session.expire_all()
    assert db_session.get(SessionModel, SESSION_ID).topic_suggest_state == ts.DONE


def test_register_fails_before_level_is_known(db_session):
    _make_session(db_session, level=None)
    res = ts.register(db_session, _ctx(db_session), _args())
    assert not res.ok
    assert "level" in res.error
    db_session.expire_all()
    assert db_session.get(SessionModel, SESSION_ID).topic_suggest_state == ts.AWAITING_LEVEL


@pytest.mark.parametrize("state", [None, ts.DONE])
def test_register_fails_when_not_due(db_session, state):
    # None: the session started with a level. DONE: already offered once.
    _make_session(db_session, level="beginner", state=state)
    res = ts.register(db_session, _ctx(db_session), _args())
    assert not res.ok
    assert "not due" in res.error


@pytest.mark.parametrize("mode,n", [("broad", 2), ("specific", 5)])
def test_register_enforces_per_mode_item_counts(db_session, mode, n):
    _make_session(db_session, level="beginner")
    res = ts.register(db_session, _ctx(db_session), _args(mode=mode, n=n))
    assert not res.ok
    assert "items" in res.error


@pytest.mark.parametrize("mode,n", [("broad", 3), ("broad", 5), ("specific", 2), ("specific", 4)])
def test_register_accepts_per_mode_bounds(db_session, mode, n):
    _make_session(db_session, level="advanced")
    assert ts.register(db_session, _ctx(db_session), _args(mode=mode, n=n)).ok


# --- from_tool_calls -------------------------------------------------------


def _call(name="suggest_topics", status="ok", args=None):
    return {
        "name": name,
        "args": args if args is not None else {
            "mode": "specific",
            "topic": "Carnot cycle",
            "items": [{"label": "Entropy", "hint": "why Carnot is the ceiling"}, {"label": "Otto cycle"}],
        },
        "status": status,
        "error": None,
    }


def test_from_tool_calls_reads_the_ok_call():
    card = ts.from_tool_calls(json.dumps([_call(name="update_topic_profile", args={}), _call()]))
    assert card.model_dump() == {
        "mode": "specific",
        "topic": "Carnot cycle",
        "items": [
            {"label": "Entropy", "hint": "why Carnot is the ceiling"},
            {"label": "Otto cycle", "hint": None},
        ],
    }


@pytest.mark.parametrize("raw", [
    "[]",
    None,
    "not json",
    json.dumps([_call(status="failed")]),
    json.dumps([_call(args={"mode": "sideways"})]),
])
def test_from_tool_calls_none_without_a_valid_ok_call(raw):
    assert ts.from_tool_calls(raw) is None


# --- tool registration -----------------------------------------------------


def test_suggest_topics_is_registered_with_its_contract_schema():
    from agent import tools

    fn = next(t["function"] for t in tools.TOOLS if t["function"]["name"] == "suggest_topics")
    params = fn["parameters"]
    assert set(params["required"]) == {"session_id", "mode", "topic", "items"}
    assert params["properties"]["mode"]["enum"] == ["broad", "specific"]
    items = params["properties"]["items"]
    assert (items["minItems"], items["maxItems"]) == (2, 5)
    assert "ends the turn" in fn["description"]


def test_dispatch_routes_suggest_topics_and_injects_session_id(db_session):
    from agent import tools

    _make_session(db_session, level="beginner")
    args = _args().model_dump()
    args["session_id"] = "hallucinated"
    res = tools.dispatch("suggest_topics", args, _ctx(db_session))
    assert res.ok, res.error
    assert res.data["mode"] == "broad"
