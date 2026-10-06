"""T5: LLM cost cap circuit breaker.

Unit tests for `services.cost_meter` (record/check) and integration tests
that the streaming chat route emits the right 429 envelope on a breached
hard cap. Soft-cap warnings on the streaming path are dedicated
`cost_warning` events, covered in test_tutor_stream.py.

The route-level test pre-seeds `daily_cost_ledger` rather than driving
spend through the LLM. Cost recording on the agent loop itself is
exercised by the run_streaming tests below.
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from config import settings
from contracts import TopicProfile
from db.models import DailyCostLedger, User
from db.models import Session as SessionModel
from lib.error_codes import DAILY_COST_CAP_REACHED, GLOBAL_COST_CAP_REACHED
from services import cost_meter

USER_ID = "u_cost"
SESSION_ID = "s_cost"


@pytest.fixture
def seed_user(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()


# ---------------------------------------------------------------------------
# Unit tests: cost_meter primitives
# ---------------------------------------------------------------------------


def test_current_spend_returns_zero_when_no_row(db_session, seed_user):
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0000")


def test_record_cost_creates_row(db_session, seed_user):
    total = cost_meter.record_cost(db_session, USER_ID, 0.1234)
    assert total == Decimal("0.1234")
    row = db_session.get(DailyCostLedger, (USER_ID, cost_meter._today_utc()))
    assert row is not None
    assert Decimal(str(row.cost_usd)) == Decimal("0.1234")


def test_record_cost_accumulates(db_session, seed_user):
    cost_meter.record_cost(db_session, USER_ID, Decimal("0.5"))
    total = cost_meter.record_cost(db_session, USER_ID, Decimal("0.25"))
    assert total == Decimal("0.7500")


def test_record_cost_ignores_zero_and_negative(db_session, seed_user):
    cost_meter.record_cost(db_session, USER_ID, Decimal("0"))
    cost_meter.record_cost(db_session, USER_ID, Decimal("-1.5"))
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0000")


def test_check_cap_allowed_below_soft(db_session, seed_user, monkeypatch):
    monkeypatch.setattr(settings, "llm_soft_cap_usd", 2.00)
    monkeypatch.setattr(settings, "llm_hard_cap_usd", 3.00)
    cost_meter.record_cost(db_session, USER_ID, Decimal("0.50"))
    status = cost_meter.check_cap(db_session, USER_ID)
    assert status.allowed is True
    assert status.soft_breached is False
    assert status.used == Decimal("0.5000")


def test_check_cap_soft_breached_but_allowed(db_session, seed_user, monkeypatch):
    monkeypatch.setattr(settings, "llm_soft_cap_usd", 2.00)
    monkeypatch.setattr(settings, "llm_hard_cap_usd", 3.00)
    cost_meter.record_cost(db_session, USER_ID, Decimal("2.50"))
    status = cost_meter.check_cap(db_session, USER_ID)
    assert status.allowed is True
    assert status.soft_breached is True


def test_check_cap_hard_blocks(db_session, seed_user, monkeypatch):
    monkeypatch.setattr(settings, "llm_soft_cap_usd", 2.00)
    monkeypatch.setattr(settings, "llm_hard_cap_usd", 3.00)
    cost_meter.record_cost(db_session, USER_ID, Decimal("3.00"))
    status = cost_meter.check_cap(db_session, USER_ID)
    assert status.allowed is False
    assert status.soft_breached is True


# ---------------------------------------------------------------------------
# Integration: /api/chat/stream 429 envelope
# ---------------------------------------------------------------------------


def test_chat_stream_returns_429_when_hard_cap_reached(
    client, db_session, seed_user, monkeypatch
):
    monkeypatch.setattr(settings, "llm_stub", True)  # never reach a real LLM
    monkeypatch.setattr(settings, "llm_soft_cap_usd", 2.00)
    monkeypatch.setattr(settings, "llm_hard_cap_usd", 3.00)
    db_session.add(
        DailyCostLedger(
            user_id=USER_ID,
            date_utc=cost_meter._today_utc(),
            cost_usd=Decimal("3.5000"),
        )
    )
    db_session.commit()

    r = client.post(
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "hi"},
        headers={"Authorization": f"Bearer test-{USER_ID}"},
    )
    assert r.status_code == 429
    detail = r.json()["detail"]
    assert detail["code"] == DAILY_COST_CAP_REACHED
    assert Decimal(detail["hard_cap_usd"]) == Decimal("3.00")
    assert Decimal(detail["used_usd"]) == Decimal("3.5000")
    assert "resets_at" in detail


def test_chat_rejected_when_global_ceiling_hit(
    client, db_session, seed_user, monkeypatch
):
    """B-04: even when the per-user cap has room, the optional global daily
    ceiling must independently block the turn."""
    monkeypatch.setattr(settings, "llm_stub", True)  # never reach a real LLM
    monkeypatch.setattr(
        "services.cost_meter.settings.global_daily_cost_cap_usd", 0.10
    )
    db_session.add(
        DailyCostLedger(
            user_id=USER_ID,
            date_utc=cost_meter._today_utc(),
            cost_usd=Decimal("0.2000"),
        )
    )
    db_session.commit()

    r = client.post(
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "hi"},
        headers={"Authorization": f"Bearer test-{USER_ID}"},
    )
    assert r.status_code == 429
    detail = r.json()["detail"]
    assert detail["code"] == GLOBAL_COST_CAP_REACHED
    assert "resets_at" in detail


# ---------------------------------------------------------------------------
# Streaming tutor loop: cost recording against the real ledger
# ---------------------------------------------------------------------------


def _content_chunk(token):
    delta = SimpleNamespace(content=token, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _tool_chunk_retrieve(call_id):
    fn = SimpleNamespace()
    fn.name = "retrieve_chunks"
    fn.arguments = '{"session_id":"s_cost","query":"q"}'
    frag = SimpleNamespace()
    frag.index = 0
    frag.id = call_id
    frag.function = fn
    delta = SimpleNamespace(content=None, tool_calls=[frag])
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _make_stream(*chunks):
    async def _gen():
        for c in chunks:
            yield c
    return _gen()


@pytest.mark.asyncio
async def test_tutor_records_cost_per_call(
    db_session, seed_user, monkeypatch
):
    """run_streaming's billed acompletion call must accumulate its cost to
    the per-user daily ledger (real record_cost, real ledger row)."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock

    from agent import tutor
    from agent.types import ToolContext

    # Disable stub so the real loop runs.
    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")

    monkeypatch.setattr(
        tutor.litellm, "acompletion",
        AsyncMock(side_effect=[_make_stream(_content_chunk("done."))]),
    )
    # stream_chunk_builder would choke on the SimpleNamespace fakes; pin it.
    monkeypatch.setattr(
        tutor.litellm, "stream_chunk_builder",
        MagicMock(return_value=SimpleNamespace()),
    )
    monkeypatch.setattr(
        tutor.litellm, "completion_cost", lambda completion_response=None: 0.0123
    )

    ctx = ToolContext(
        db=db_session,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc),
    )
    events = [
        ev
        async for ev in tutor.run_streaming(
            [{"role": "user", "content": "hi"}], "sys", ctx
        )
    ]
    deltas = "".join(e.data["text"] for e in events if e.type == "assistant_delta")
    assert deltas == "done."
    assert events[-1].type == "done"
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0123")


def test_end_session_sets_cost_warning_header_when_soft_breached(
    client, db_session, seed_user
):
    """I-03: soft-cap breach on end must surface an X-Cost-Warning header
    (seed_user's session has no messages, so the mechanical no_exchanges
    fallback fires and no LLM call is needed to reach the 200)."""
    cost_meter.record_cost(
        db_session, USER_ID, Decimal(str(settings.llm_soft_cap_usd)) + Decimal("0.01")
    )
    db_session.commit()

    resp = client.post(f"/api/sessions/{SESSION_ID}/end?user_id={USER_ID}")
    assert resp.status_code == 200, resp.text
    assert resp.headers["x-cost-warning"].startswith("level=")


def test_end_session_no_header_under_soft_cap(client, db_session, seed_user):
    resp = client.post(f"/api/sessions/{SESSION_ID}/end?user_id={USER_ID}")
    assert resp.status_code == 200, resp.text
    assert "x-cost-warning" not in resp.headers


@pytest.mark.asyncio
async def test_tutor_short_circuits_on_mid_turn_hard_cap(
    db_session, seed_user, monkeypatch
):
    """If `record_cost` pushes spend past `llm_hard_cap_usd` mid-loop, the
    next iteration must bail with a daily_cost_cap_reached error event
    before issuing another acompletion."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock

    from agent import tutor
    from agent.types import ToolContext
    from contracts import ToolResult

    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "real-key")
    monkeypatch.setattr(settings, "llm_soft_cap_usd", 0.50)
    monkeypatch.setattr(settings, "llm_hard_cap_usd", 1.00)

    # Every iteration returns a tool call so the loop wants to iterate again.
    acompletion = AsyncMock(
        side_effect=[_make_stream(_tool_chunk_retrieve(f"t{i}")) for i in range(4)]
    )
    monkeypatch.setattr(tutor.litellm, "acompletion", acompletion)
    monkeypatch.setattr(
        tutor.litellm, "stream_chunk_builder",
        MagicMock(return_value=SimpleNamespace()),
    )
    # First call already pushes spend past the hard cap (1.50 > 1.00).
    monkeypatch.setattr(
        tutor.litellm, "completion_cost", lambda completion_response=None: 1.5000
    )
    monkeypatch.setattr(
        "agent.tutor.tools.dispatch",
        MagicMock(return_value=ToolResult(ok=True, status="ok", error=None, data={"chunks": []})),
    )

    ctx = ToolContext(
        db=db_session,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc),
    )
    events = [
        ev
        async for ev in tutor.run_streaming(
            [{"role": "user", "content": "hi"}], "sys", ctx
        )
    ]
    # Exactly one LLM call should have fired; the next iter must short-circuit.
    assert acompletion.await_count == 1
    assert events[-1].type == "error"
    assert events[-1].data["code"] == "daily_cost_cap_reached"
