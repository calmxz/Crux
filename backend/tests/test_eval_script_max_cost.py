"""#600: the live eval scripts stop starting runs once the spend recorded in
their own database reaches --max-cost, and report what they spent."""

import importlib
import json
import sys
from decimal import Decimal

import pytest

from db.database import SessionLocal
from db.database import engine as default_engine
from db.models import User
from services.cost_meter import record_cost

# Script name -> the per-run coroutine its loop awaits once per run.
RUNNERS = {
    "eval_subtopic_levels": "_run_pattern_once",
    "reliability_focus_clear": "_run_fixture",
}


@pytest.fixture(params=sorted(RUNNERS))
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


def _planned_runs(module, runs: int) -> int:
    if module.__name__.endswith("reliability_focus_clear"):
        per_round = sum(
            len(json.loads((module.PATTERN_DIR / f"{p}.json").read_text(encoding="utf-8")))
            for p in module.PATTERNS
        )
    else:
        per_round = len(module.PATTERNS)
    return runs * per_round


def _stub_runs(module, monkeypatch, *, cost: str, ok: bool, date_utc: str | None = None):
    """Replace the per-run coroutine with one that makes no LLM call, books
    `cost` to a fresh user's ledger row in the script's database, and records
    the run."""
    calls: list[dict] = []

    async def run(session_factory, item):
        calls.append(item)
        with session_factory() as db:
            user_id = f"u-{len(calls)}"
            db.add(User(id=user_id))
            db.flush()
            record_cost(db, user_id, Decimal(cost), date_utc=date_utc)
            db.commit()
        return ok

    monkeypatch.setattr(module, RUNNERS[module.__name__.rsplit(".", 1)[-1]], run)
    return calls


def _main(module, monkeypatch, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", [module.__name__, *args])
    return module.main()


def test_help_shows_the_default_limit(script, monkeypatch, capsys):
    # argparse wraps help to the terminal width; a wide one keeps the
    # default on one line.
    monkeypatch.setenv("COLUMNS", "200")
    with pytest.raises(SystemExit) as exc:
        _main(script, monkeypatch, "--help")
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--max-cost" in out
    assert "default 5" in out


@pytest.mark.parametrize("value", ["0", "-1", "abc", "inf", "nan"])
def test_a_non_positive_limit_fails_parsing(script, monkeypatch, capsys, value):
    calls = _stub_runs(script, monkeypatch, cost="0.01", ok=True)
    with pytest.raises(SystemExit) as exc:
        _main(script, monkeypatch, "--max-cost", value)
    assert exc.value.code == 2
    assert "--max-cost" in capsys.readouterr().err
    assert calls == []


def test_reaching_the_limit_stops_before_the_next_run(script, monkeypatch, capsys):
    calls = _stub_runs(script, monkeypatch, cost="0.60", ok=True)
    code = _main(script, monkeypatch, "--runs", "1", "--max-cost", "0.50")

    assert len(calls) == 1
    assert code == script.COST_STOP_EXIT
    assert code not in (0, 1)
    out = capsys.readouterr().out
    assert "spent $0.6000, limit $0.5000" in out
    assert f"Completed 1 of {_planned_runs(script, 1)} planned runs" in out
    assert "PASS" not in out and "FAIL" not in out
    assert out.rstrip().endswith("Total spend: $0.6000")


def test_an_interrupted_run_still_reports_spend(script, monkeypatch, capsys):
    calls = _stub_runs(script, monkeypatch, cost="0.25", ok=True)
    booked = getattr(script, RUNNERS[script.__name__.rsplit(".", 1)[-1]])

    async def interrupted(session_factory, item):
        await booked(session_factory, item)
        raise KeyboardInterrupt

    monkeypatch.setattr(script, RUNNERS[script.__name__.rsplit(".", 1)[-1]], interrupted)
    with pytest.raises(KeyboardInterrupt):
        _main(script, monkeypatch, "--runs", "1")

    assert len(calls) == 1
    assert capsys.readouterr().out.rstrip().endswith("Total spend: $0.2500")


def test_spend_dated_before_today_counts_toward_the_limit(script, monkeypatch, capsys):
    calls = _stub_runs(script, monkeypatch, cost="0.50", ok=True, date_utc="2000-01-01")
    code = _main(script, monkeypatch, "--runs", "1", "--max-cost", "0.50")

    assert len(calls) == 1
    assert code == script.COST_STOP_EXIT


@pytest.mark.parametrize(("ok", "expected_code"), [(True, 0), (False, 1)])
def test_below_the_limit_every_run_completes_and_reports_spend(
    script, monkeypatch, capsys, ok, expected_code
):
    calls = _stub_runs(script, monkeypatch, cost="0.01", ok=ok)
    code = _main(script, monkeypatch, "--runs", "1")

    planned = _planned_runs(script, 1)
    assert len(calls) == planned
    assert code == expected_code
    out = capsys.readouterr().out
    assert ("PASS" if ok else "FAIL") in out
    assert out.rstrip().endswith(f"Total spend: ${Decimal('0.01') * planned:.4f}")
