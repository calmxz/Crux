"""#601: a subtopic-level pattern's answer step answers the open check Set
through the app's grading path, then Closes it and runs the follow-up turn
the way the learner's Done click does."""

import importlib
import json
import sys
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


def _quiz_turn(set_index=1, set_total=1, correct=CORRECT, prefix="Q"):
    return [
        "Questions on u-substitution.",
        tool_call(
            "ask_check_questions",
            args={
                "session_id": SESSION_ID,
                "set_index": set_index,
                "set_total": set_total,
                "gap": "u-substitution",
                "items": [
                    {
                        "question": f"{prefix}{n}?",
                        "options": ["a", "b", "c"],
                        "correct_index": c,
                        "explanation": f"E{n}.",
                    }
                    for n, c in enumerate(correct)
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
async def test_the_answer_step_answers_every_set_of_the_check(script, fake_llm):
    set2 = [1, 2]
    fake_llm.streams = [
        _quiz_turn(1, 2),
        ["Good. Set 2:", *_quiz_turn(2, 2, set2, prefix="R")],
        ["All five right."],
        ["Next up: parts."],
    ]

    factory, _ok = await _run(script, ["Quiz me on u-sub.", ANSWER, "What's next?"])

    with factory() as db:
        events = db.scalars(select(LearningEvent).order_by(LearningEvent.id)).all()
        assert check_service.open_set(db.get(SessionModel, SESSION_ID)) is None
    assert [(e.question, e.correct, e.selected_index) for e in events] == [
        *[(f"Q{n}?", True, c) for n, c in enumerate(CORRECT)],
        *[(f"R{n}?", True, c) for n, c in enumerate(set2)],
    ]
    summaries = [c["messages"][-1]["content"] for c in fake_llm.stream_calls[1:3]]
    assert summaries[0].endswith("3/3 correct. Set 1 of 2.")
    assert summaries[1].endswith("2/2 correct. Set 2 of 2.")
    turn3 = fake_llm.stream_calls[3]["messages"]
    assert [m["content"] for m in turn3 if m["role"] == "user"] == [
        "Quiz me on u-sub.",
        "What's next?",
    ]


@pytest.mark.asyncio
async def test_a_follow_up_without_the_next_set_ends_the_step(script, fake_llm):
    fake_llm.streams = [_quiz_turn(1, 2), ["Good. More later."], ["Next up: parts."]]

    factory, _ok = await _run(script, ["Quiz me on u-sub.", ANSWER, "What's next?"])

    assert len(fake_llm.stream_calls) == 3
    with factory() as db:
        row = db.get(SessionModel, SESSION_ID)
        assert check_service.open_set(row) is None
        assert check_service.current_check(row)["last_set_index"] == 1
        assert len(db.scalars(select(LearningEvent)).all()) == len(CORRECT)


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


def _stub_runs(script, monkeypatch):
    """Replace the per-run coroutine with one that makes no LLM call and
    records which pattern ran."""
    runs = []

    async def run(session_factory, pattern):
        runs.append(pattern["name"])
        return True

    monkeypatch.setattr(script, "_run_pattern_once", run)
    return runs


def _main(script, monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["eval_subtopic_levels", *args])
    return script.main()


def test_pattern_runs_only_the_named_pattern(script, monkeypatch, capsys):
    runs = _stub_runs(script, monkeypatch)

    code = _main(script, monkeypatch, "--pattern", "tested_progression", "--runs", "2")

    assert code == 0
    assert runs == ["tested_progression", "tested_progression"]
    out = capsys.readouterr().out
    assert "declared_level" not in out
    assert "All 1 patterns" in out


def test_an_unknown_pattern_fails_parsing(script, monkeypatch, capsys):
    runs = _stub_runs(script, monkeypatch)

    with pytest.raises(SystemExit) as exc:
        _main(script, monkeypatch, "--pattern", "tested_progresion")

    assert exc.value.code == 2
    assert "--pattern" in capsys.readouterr().err
    assert runs == []


def test_an_unknown_turn_action_fails_at_load(script, tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(_pattern(["Hi.", {"action": "answer_checks_wrongly"}])))
    with pytest.raises(ValueError, match="answer_checks_wrongly"):
        script._load_pattern(path)


@pytest.mark.asyncio
async def test_an_unknown_turn_action_fails_the_run_unvalidated(script, fake_llm):
    fake_llm.streams = [_quiz_turn()]

    with pytest.raises(ValueError, match="answer_checks_wrongly"):
        await _run(script, ["Quiz me.", {"action": "answer_checks_wrongly"}])

    assert len(fake_llm.stream_calls) == 1


@pytest.mark.parametrize(
    "bad",
    [
        _pattern([{"action": "nope"}]),
        {**_pattern(["Hi."]), "expected": {"subtopic": "u-sub", "levels": ["advanced"]}},
    ],
)
def test_a_bad_later_pattern_exits_before_the_first_run(script, monkeypatch, tmp_path, capsys, bad):
    (tmp_path / "good.json").write_text(json.dumps(_pattern(["Hi."])))
    (tmp_path / "bad.json").write_text(json.dumps(bad))
    monkeypatch.setattr(script, "PATTERN_DIR", tmp_path)
    monkeypatch.setattr(script, "PATTERNS", ("good", "bad"))
    runs = _stub_runs(script, monkeypatch)

    code = _main(script, monkeypatch)

    assert code == script.BAD_PATTERN_EXIT
    assert code not in (0, 1, 2, script.COST_STOP_EXIT)
    assert runs == []
    assert "bad.json" in capsys.readouterr().err
    assert SessionLocal.kw["bind"] is default_engine


def test_tested_progression_answers_with_a_structured_turn(script):
    pattern = script._load_pattern(script.PATTERN_DIR / "tested_progression.json")
    assert pattern["turns"][1] == ANSWER
    assert "[simulate" not in json.dumps(pattern)


def _patch_level(subtopic, level="advanced"):
    args = {"session_id": SESSION_ID, "subtopic": subtopic, "evidence_type": "declared"}
    if level is not None:
        args["subtopic_level"] = level
    return tool_call("update_topic_profile", args=args)


async def _run_by(script, turns, by_turn):
    factory = script._make_session_factory()
    pattern = {**_pattern(turns), "expected": {**_pattern(turns)["expected"], "by_turn": by_turn}}
    return await script._run_pattern_once(factory, pattern)


@pytest.mark.asyncio
async def test_a_miss_prints_the_profile_grading_and_tool_calls(
    script, fake_llm, monkeypatch, capsys
):
    # #612: a failed run says what the tutor did, so a 0% can be diagnosed.
    # One wrong answer, so the graded count is not the Item count.
    real_answer = check_service.answer

    def answer_first_wrong(db, session_id, index, selected_index):
        if index == 0:
            selected_index = (selected_index + 1) % 3
        return real_answer(db, session_id, index, selected_index)

    monkeypatch.setattr(check_service, "answer", answer_first_wrong)
    fake_llm.streams = [
        _quiz_turn(),
        [_patch_level("u substitution")],
        ["Nice work."],
        [_patch_level("u-substitution", level=None)],
        ["Next up: parts."],
    ]

    _factory, ok = await _run(script, ["Quiz me on u-sub.", ANSWER, "What's next?"])

    assert ok is False
    err = capsys.readouterr().err
    assert (
        "[probe] miss (no match): subtopic_levels={'u substitution': 'advanced'}; "
        "graded 2/3 correct"
    ) in err
    assert "turn 1 ask_check_questions {'gap': 'u-substitution'} ok" in err
    assert (
        "turn 2 update_topic_profile {'subtopic': 'u substitution', "
        "'evidence_type': 'declared', 'subtopic_level': 'advanced'} ok"
    ) in err
    assert (
        "turn 3 update_topic_profile {'subtopic': 'u-substitution', "
        "'evidence_type': 'declared'} error: subtopic and subtopic_level must be provided together"
    ) in err


@pytest.mark.asyncio
async def test_a_pass_prints_no_miss(script, fake_llm, capsys):
    fake_llm.streams = [
        _quiz_turn(),
        [_patch_level("u-substitution")],
        ["Nice work."],
        ["Next up: parts."],
    ]

    _factory, ok = await _run(script, ["Quiz me on u-sub.", ANSWER, "What's next?"])

    assert ok is True
    assert "miss" not in capsys.readouterr().err


@pytest.mark.asyncio
async def test_a_late_match_says_when_it_matched(script, fake_llm, capsys):
    fake_llm.streams = [["Sure."], ["Noted."], [_patch_level("u-substitution")], ["Done."]]

    ok = await _run_by(script, ["Hi.", "More.", "Set it."], by_turn=2)

    assert ok is False
    assert "[probe] miss (matched at turn 3, expected by turn 2)" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_a_turn_that_aborts_still_shows_its_calls(script, fake_llm, capsys):
    # Refused calls with no text until max_iters: the tutor persists nothing.
    fake_llm.streams = [[_patch_level("u-substitution", level=None)] for _ in range(8)]

    _factory, ok = await _run(script, ["Set it."])

    assert ok is False
    err = capsys.readouterr().err
    assert err.count("turn 1 update_topic_profile") == 8
    assert "turn 1 turn ended with error {'code': 'max_iters_reached'}" in err


@pytest.mark.asyncio
async def test_a_run_that_raises_shows_its_trace(script, fake_llm, monkeypatch, capsys):
    def boom(db, session_id):
        raise RuntimeError("complete failed")

    monkeypatch.setattr(check_service, "complete", boom)
    fake_llm.streams = [_quiz_turn()]

    with pytest.raises(RuntimeError, match="complete failed"):
        await _run(script, ["Quiz me.", ANSWER])

    err = capsys.readouterr().err
    assert "[probe] miss (no match)" in err
    assert "turn 1 ask_check_questions {'gap': 'u-substitution'} ok" in err


@pytest.mark.asyncio
async def test_the_trace_escapes_non_ascii(script, fake_llm, capsys):
    fake_llm.streams = [[_patch_level("u\u2192sub")], ["Done."]]

    await _run(script, ["Set it."])

    err = capsys.readouterr().err
    assert "u\\u2192sub" in err
    assert err.isascii()
