"""#601: a subtopic-level pattern's answer step answers the open check Set
through the app's grading path, then Closes it and runs the follow-up turn
the way the learner's Done click does."""

import importlib
import json
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from db.database import SessionLocal
from db.database import engine as default_engine
from db.models import LearningEvent
from db.models import Session as SessionModel
from services import check_service
from tests.conftest import tool_call

FIXED = uuid.UUID("6f1c2d3e-4a5b-4c6d-8e7f-0123456789ab")
SESSION_ID = str(FIXED)
ANSWER = {"action": "answer_checks_correctly"}
# Distinct, and not the item's position, so neither "always option 0" nor
# "option = item index" answers them all correctly.
CORRECT = [2, 0, 1]


@pytest.fixture
def script(monkeypatch):
    # The script hard-assigns DATABASE_URL on import; setenv first so
    # monkeypatch restores the caller's value at teardown.
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    module = importlib.import_module("scripts.eval_subtopic_levels")
    assert SessionLocal.kw["bind"] is default_engine, (
        "SessionLocal leaked a binding from an earlier test"
    )
    # A known session id, so the scripted tool call can name it.
    monkeypatch.setattr(module, "uuid", SimpleNamespace(uuid4=lambda: FIXED))
    yield module
    script_engine = SessionLocal.kw["bind"]
    SessionLocal.configure(bind=default_engine)
    if script_engine is not default_engine:
        script_engine.dispose()


def _pattern(turns):
    return {
        "name": "probe",
        "topic": "calculus",
        "turns": turns,
        "expected": {"subtopic": "u-substitution", "levels": ["advanced"], "by_turn": 3},
    }


def _quiz_turn():
    return [
        "Three questions on u-substitution.",
        tool_call(
            "ask_check_questions",
            args={
                "session_id": SESSION_ID,
                "set_index": 1,
                "set_total": 1,
                "gap": "u-substitution",
                "items": [
                    {
                        "question": f"Q{n}?",
                        "options": ["a", "b", "c"],
                        "correct_index": c,
                        "explanation": f"E{n}.",
                    }
                    for n, c in enumerate(CORRECT)
                ],
            },
        ),
    ]


async def _run(script, turns):
    factory = script._make_session_factory()
    ok = await script._run_pattern_once(factory, _pattern(turns))
    return factory, ok


@pytest.mark.asyncio
async def test_the_answer_step_grades_every_item_through_check_service(
    script, fake_llm, monkeypatch
):
    answered = []
    real_answer = check_service.answer

    def spy(db, session_id, index, selected_index):
        answered.append((session_id, index, selected_index))
        return real_answer(db, session_id, index, selected_index)

    monkeypatch.setattr(check_service, "answer", spy)
    fake_llm.streams = [_quiz_turn(), ["Nice work, 3 for 3."], ["Next up: parts."]]

    factory, _ok = await _run(script, ["Quiz me on u-sub.", ANSWER, "What's next?"])

    assert answered == [(SESSION_ID, n, c) for n, c in enumerate(CORRECT)]
    with factory() as db:
        events = db.scalars(select(LearningEvent).order_by(LearningEvent.id)).all()
        row = db.get(SessionModel, SESSION_ID)
        assert check_service.open_set(row) is None
    assert [(e.question, e.correct, e.selected_index, e.correct_index) for e in events] == [
        (f"Q{n}?", True, c, c) for n, c in enumerate(CORRECT)
    ]


@pytest.mark.asyncio
async def test_the_follow_up_sees_the_results_and_the_next_turn_does_not(script, fake_llm):
    fake_llm.streams = [_quiz_turn(), ["Nice work, 3 for 3."], ["Next up: parts."]]

    await _run(script, ["Quiz me on u-sub.", ANSWER, "What's next?"])

    assert len(fake_llm.stream_calls) == 3
    followup = fake_llm.stream_calls[1]["messages"]
    assert followup[-1]["role"] == "user"
    assert followup[-1]["content"].startswith("[check results] gap=u-substitution: 3/3 correct.")

    turn3 = [m for m in fake_llm.stream_calls[2]["messages"] if m["role"] != "system"]
    assert [m["content"] for m in turn3 if m["role"] == "user"] == [
        "Quiz me on u-sub.",
        "What's next?",
    ]
    assert "Nice work, 3 for 3." in [m["content"] for m in turn3 if m["role"] == "assistant"]


@pytest.mark.asyncio
async def test_the_follow_up_cannot_start_a_new_check(script, fake_llm):
    # The Done click's follow-up is suppressed: a fresh Set 1 is refused.
    fake_llm.streams = [_quiz_turn(), _quiz_turn(), ["Fine, moving on."]]

    factory, _ok = await _run(script, ["Quiz me on u-sub.", ANSWER])

    with factory() as db:
        assert check_service.open_set(db.get(SessionModel, SESSION_ID)) is None


@pytest.mark.asyncio
async def test_with_no_open_set_the_answer_step_is_skipped_and_logged(script, fake_llm, capsys):
    fake_llm.streams = [["Sure, here is u-sub."], ["Next up: parts."]]

    factory, _ok = await _run(script, ["Quiz me on u-sub.", ANSWER, "What's next?"])

    assert len(fake_llm.stream_calls) == 2
    with factory() as db:
        assert db.scalars(select(LearningEvent)).all() == []
    err = capsys.readouterr().err
    assert "[probe] turn 2: no open check Set; answer step skipped" in err


@pytest.mark.asyncio
async def test_string_turns_go_to_the_tutor_as_chat_messages(script, fake_llm):
    fake_llm.streams = [["One."], ["Two."]]

    await _run(script, ["First message.", "Second message."])

    last = [m for m in fake_llm.stream_calls[1]["messages"] if m["role"] != "system"]
    assert [(m["role"], m["content"]) for m in last] == [
        ("user", "First message."),
        ("assistant", "One."),
        ("user", "Second message."),
    ]


def test_an_unknown_turn_action_fails_at_load(script, tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(_pattern(["Hi.", {"action": "answer_checks_wrongly"}])))
    with pytest.raises(ValueError, match="answer_checks_wrongly"):
        script._load_pattern(path)


def test_tested_progression_answers_with_a_structured_turn(script):
    pattern = script._load_pattern(script.PATTERN_DIR / "tested_progression.json")
    assert pattern["turns"][1] == ANSWER
    assert "[simulate" not in json.dumps(pattern)
