"""#605: a cost-cap refusal streamed to an eval script's tutor turn stops the
eval the way a --max-cost stop does, instead of scoring the run."""

import importlib
import sys
from decimal import Decimal

import pytest

from agent.stream_events import StreamEvent
from db.database import SessionLocal
from db.database import engine as default_engine
from lib import error_codes
from services.cost_meter import record_cost

CAP = error_codes.GLOBAL_COST_CAP_REACHED
CALL_COST = Decimal("0.10")
# Script name -> (CLI args, tutor calls in each of the first two runs). The
# first run of each is a pattern or fixture of at least two chat turns.
ARGS = {
    "eval_subtopic_levels": (["--pattern", "declared_level"], 2),
    "reliability_focus_clear": ([], 4),
}


@pytest.fixture(params=sorted(ARGS))
def script(request, monkeypatch):
    # The script hard-assigns DATABASE_URL on import; setenv first so
    # monkeypatch restores the caller's value at teardown.
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    module = importlib.import_module(f"scripts.{request.param}")
    assert SessionLocal.kw["bind"] is default_engine, (
        "SessionLocal leaked a binding from an earlier test"
    )
    yield module
    script_engine = SessionLocal.kw["bind"]
    SessionLocal.configure(bind=default_engine)
    if script_engine is not default_engine:
        script_engine.dispose()


def _name(module) -> str:
    return module.__name__.rsplit(".", 1)[-1]


def _stub_stream(module, monkeypatch, codes: list[str | None]):
    """Replace tutor.run_streaming: call N books CALL_COST and streams a
    reply when codes[N] is None, else streams an `error` event with that
    code. Calls past the list repeat its last entry. Returns the calls made."""
    calls: list[int] = []

    async def run_streaming(messages, system_prompt, ctx):
        code = codes[min(len(calls), len(codes) - 1)]
        calls.append(len(calls))
        if code is None:
            record_cost(ctx.db, ctx.user_id, CALL_COST)
            ctx.db.commit()
            yield StreamEvent("assistant_delta", {"text": "Sure."})
            yield StreamEvent("done", {"message_id": "m"})
        else:
            yield StreamEvent("error", {"code": code, "message": "refused"})

    monkeypatch.setattr(module.tutor, "run_streaming", run_streaming)
    return calls


def _main(module, monkeypatch, *extra: str, args: list[str] | None = None) -> int:
    base = ARGS[_name(module)][0] if args is None else args
    monkeypatch.setattr(sys, "argv", [module.__name__, *base, *extra])
    return module.main()


def _assert_cap_stop(out: str, code: int, module, *, completed: int, accepted: int) -> None:
    spend = CALL_COST * accepted
    assert code == module.COST_STOP_EXIT
    assert f"Cost cap refused a call ({CAP}): spent ${spend:.4f}." in out
    assert f"Completed {completed} of " in out
    assert "No verdict over partial results." in out
    assert "PASS" not in out and "FAIL" not in out
    assert "limit $" not in out
    assert out.rstrip().endswith(f"Total spend: ${spend:.4f}")


def test_a_refusal_on_a_runs_first_turn_stops_the_eval(script, monkeypatch, capsys):
    first_run = ARGS[_name(script)][1]
    calls = _stub_stream(script, monkeypatch, [None] * first_run + [CAP])
    code = _main(script, monkeypatch, "--runs", "2")

    # No call after the refused one: no later turn or run started.
    assert len(calls) == first_run + 1
    _assert_cap_stop(capsys.readouterr().out, code, script, completed=1, accepted=first_run)


def test_a_refusal_mid_run_stops_without_counting_the_run(script, monkeypatch, capsys):
    first_run = ARGS[_name(script)][1]
    calls = _stub_stream(script, monkeypatch, [None] * (first_run + 1) + [CAP])
    code = _main(script, monkeypatch, "--runs", "2")

    assert len(calls) == first_run + 2
    _assert_cap_stop(capsys.readouterr().out, code, script, completed=1, accepted=first_run + 1)


def test_a_daily_cap_refusal_also_stops(script, monkeypatch, capsys):
    calls = _stub_stream(script, monkeypatch, [error_codes.DAILY_COST_CAP_REACHED])
    code = _main(script, monkeypatch, "--runs", "2")

    assert len(calls) == 1
    assert code == script.COST_STOP_EXIT
    assert "Cost cap refused a call (daily_cost_cap_reached)" in capsys.readouterr().out


def test_a_non_cap_error_is_still_scored(script, monkeypatch, capsys):
    calls = _stub_stream(script, monkeypatch, ["llm_unavailable"])
    code = _main(script, monkeypatch, "--runs", "1")

    assert len(calls) > 1
    assert code in (0, 1)
    out = capsys.readouterr().out
    assert "Cost cap refused" not in out
    assert "[PASS]" in out or "[FAIL]" in out


@pytest.mark.parametrize("script", ["eval_subtopic_levels"], indirect=True)
def test_a_cap_stop_prints_no_miss_trace(script, monkeypatch, capsys):
    _stub_stream(script, monkeypatch, [None, CAP])
    code = _main(script, monkeypatch, "--runs", "1")

    assert code == script.COST_STOP_EXIT
    err = capsys.readouterr().err
    assert "miss (" not in err
    assert "] fail" not in err and "] error" not in err


@pytest.mark.parametrize("script", ["eval_subtopic_levels"], indirect=True)
def test_a_refusal_in_a_check_follow_up_stops_the_eval(script, monkeypatch, capsys):
    # tested_progression's turn 2 answers the open Set. An empty Set stands in
    # for the Check the stubbed tutor never poses: open once turn 1's call has
    # run (prompt assembly reads it too), until the answer step Closes it.
    closed: list[str] = []

    def complete(db, session_id):
        closed.append(session_id)
        return "0/0 correct", None

    calls = _stub_stream(script, monkeypatch, [None, CAP])
    monkeypatch.setattr(
        script.check_service,
        "open_set",
        lambda row: {"items": []} if calls and not closed else None,
    )
    monkeypatch.setattr(script.check_service, "complete", complete)
    code = _main(script, monkeypatch, "--runs", "2", args=["--pattern", "tested_progression"])

    # Turn 1's chat call, then the refused follow-up; turn 3 never ran.
    assert len(calls) == 2
    assert len(closed) == 1
    captured = capsys.readouterr()
    _assert_cap_stop(captured.out, code, script, completed=0, accepted=1)
    assert "answer step skipped" not in captured.err
    assert "miss (" not in captured.err
