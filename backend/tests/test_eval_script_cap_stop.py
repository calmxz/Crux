"""#605: a cost-cap refusal streamed to an eval script's tutor turn stops the
eval the way a --max-cost stop does, instead of scoring the run."""

import importlib
import sys

import pytest

from agent.stream_events import StreamEvent
from db.database import SessionLocal
from db.database import engine as default_engine
from lib import error_codes

CAP = error_codes.GLOBAL_COST_CAP_REACHED
# Script name -> the CLI args that make its first run a pattern or fixture
# with at least two chat turns.
ARGS = {
    "eval_subtopic_levels": ["--pattern", "declared_level"],
    "reliability_focus_clear": [],
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


def _stub_stream(module, monkeypatch, codes: list[str | None]):
    """Replace tutor.run_streaming: call N streams a reply when codes[N] is
    None, else an `error` event with that code. Calls past the list repeat
    its last entry. Returns the list of calls made."""
    calls: list[int] = []

    async def run_streaming(messages, system_prompt, ctx):
        code = codes[min(len(calls), len(codes) - 1)]
        calls.append(len(calls))
        if code is None:
            yield StreamEvent("assistant_delta", {"text": "Sure."})
            yield StreamEvent("done", {"message_id": "m"})
        else:
            yield StreamEvent("error", {"code": code, "message": "refused"})

    monkeypatch.setattr(module.tutor, "run_streaming", run_streaming)
    return calls


def _main(module, monkeypatch, *extra: str) -> int:
    name = module.__name__.rsplit(".", 1)[-1]
    monkeypatch.setattr(sys, "argv", [module.__name__, *ARGS[name], *extra])
    return module.main()


def _assert_cap_stop(out: str, code: int, module) -> None:
    assert code == module.COST_STOP_EXIT
    assert f"Cost cap refused a call ({CAP})" in out
    assert "Completed 0 of " in out
    assert "No verdict over partial results." in out
    assert "PASS" not in out and "FAIL" not in out
    assert "limit $" not in out
    assert out.rstrip().endswith("Total spend: $0.0000")


def test_a_refusal_on_the_first_turn_stops_the_eval(script, monkeypatch, capsys):
    calls = _stub_stream(script, monkeypatch, [CAP])
    code = _main(script, monkeypatch, "--runs", "2")

    assert len(calls) == 1
    _assert_cap_stop(capsys.readouterr().out, code, script)


def test_a_refusal_mid_run_stops_without_counting_the_run(script, monkeypatch, capsys):
    calls = _stub_stream(script, monkeypatch, [None, CAP])
    code = _main(script, monkeypatch, "--runs", "2")

    assert len(calls) == 2
    _assert_cap_stop(capsys.readouterr().out, code, script)


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
