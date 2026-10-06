from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from config import settings
from contracts import TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from lib.error_codes import DAILY_CAP_REACHED
from routes.chat import _build_prompt_state

SESSION_ID = "s1"
USER_ID = "u1"
AUTH_HEADERS = {"Authorization": f"Bearer test-{USER_ID}"}


@pytest.fixture(autouse=True)
def seed_session(db_session):
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


def _post_stream(client, session_id=SESSION_ID, message="hello"):
    """POST /api/chat/stream and drain the SSE body. Returns (status, body)."""
    lines = []
    with client.stream(
        "POST",
        "/api/chat/stream",
        json={"session_id": session_id, "message": message},
        headers=AUTH_HEADERS,
    ) as resp:
        status = resp.status_code
        if status == 200:
            for line in resp.iter_lines():
                lines.append(line)
    return status, "\n".join(lines)


def test_chat_stream_stub_persists_both_roles(client, db_session, monkeypatch):
    """Integration through the real run_streaming (stub mode): _prepare_turn
    persists the user message and the agent persists the assistant message."""
    monkeypatch.setattr(settings, "llm_stub", True)

    status, body = _post_stream(client, message="hi")
    assert status == 200
    assert "event: assistant_delta" in body
    assert "event: done" in body

    msgs = db_session.execute(
        select(ChatMessage).where(ChatMessage.session_id == SESSION_ID)
    ).scalars().all()
    roles = {m.role for m in msgs}
    assert roles == {"user", "assistant"}
    assistant = next(m for m in msgs if m.role == "assistant")
    assert assistant.content.startswith("[STUB:")


def test_gap_accuracy_failure_does_not_kill_turn(client, db_session, monkeypatch):
    """gap_accuracy is best-effort (D1.2): a failure must not kill the turn."""
    monkeypatch.setattr(settings, "llm_stub", True)

    sess = db_session.get(SessionModel, SESSION_ID)
    sess.topic_profile_json = TopicProfile(confirmed_gaps=[{"name": "frac"}]).model_dump_json()
    db_session.commit()

    def _boom(db, sid):
        raise RuntimeError("db exploded")

    monkeypatch.setattr("routes.chat.learning_event_service.gap_accuracy", _boom)

    status, body = _post_stream(client, message="hi")
    assert status == 200
    assert "event: assistant_delta" in body
    assert "event: done" in body


def test_prompt_build_failure_still_persists_user_message(client, db_session, monkeypatch):
    """An unexpected crash while assembling the prompt must not lose the
    user's message: it is persisted before the exception propagates."""
    monkeypatch.setattr(settings, "llm_stub", True)

    def _boom(prompt_state):
        raise RuntimeError("prompt build exploded")

    monkeypatch.setattr("routes.chat.prompts.build_system_prompt", _boom)

    # C-14: the crash is now answered by UnhandledErrorMiddleware instead of
    # propagating out of the TestClient. The persist behaviour under test is
    # unchanged; only the shape of the client-visible failure moved.
    status, _ = _post_stream(client, message="save me")
    assert status == 500

    user_msgs = db_session.execute(
        select(ChatMessage).where(
            ChatMessage.session_id == SESSION_ID, ChatMessage.role == "user"
        )
    ).scalars().all()
    assert [m.content for m in user_msgs] == ["save me"]


def test_prepare_turn_failure_rerecords_embedding_spend(client, db_session, monkeypatch):
    """B-08: when _prepare_turn crashes after retrieval already metered and
    flushed embedding spend, db.rollback() in the except arm must not discard
    that real vendor cost. The retrieval call reports what it spent via
    cost_holder; the except arm re-records the total on the fresh transaction."""
    monkeypatch.setattr(settings, "llm_stub", True)

    from decimal import Decimal

    async def fake_fallback(db, sid, msg, *, user_id=None, cost_holder=None):
        if cost_holder is not None:
            cost_holder.append(Decimal("0.5"))
        return False, None

    monkeypatch.setattr(
        "routes.chat.retrieval_service.semantic_fallback_required", fake_fallback
    )

    def _boom(prompt_state):
        raise RuntimeError("boom")

    monkeypatch.setattr("routes.chat.prompts.build_system_prompt", _boom)

    # C-14: answered as a coded 500 rather than propagating; see
    # test_prompt_build_failure_still_persists_user_message.
    status, _ = _post_stream(client, message="hi")
    assert status == 500

    from services import cost_meter

    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.5")


def test_chat_stream_429_on_cap(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "llm_stub", True)

    for _ in range(settings.daily_cap):
        status, _body = _post_stream(client, message="x")
        assert status == 200

    r = client.post(
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "x"},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 429
    detail = r.json()["detail"]
    assert detail["code"] == DAILY_CAP_REACHED
    assert detail["cap"] == settings.daily_cap
    assert detail["used"] == settings.daily_cap
    assert "resets_at" in detail
    # B-05: every admitted turn released its reserve, and the rate-limit
    # reject arm (which runs after check_and_increment's commit published the
    # reserve) released its own. No residue.
    from services import cost_meter

    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0000")


def test_reserved_spend_blocks_the_next_turn_before_any_real_cost(
    db_session, monkeypatch
):
    """B-05: a turn that has reserved but not yet spent must already count
    against the cap, so a second concurrent turn at cap-minus-epsilon is
    rejected instead of both running an LLM call."""
    import asyncio

    from fastapi import HTTPException

    from contracts import ChatRequest
    from lib.error_codes import DAILY_COST_CAP_REACHED
    from routes.chat import _prepare_turn
    from services import cost_meter

    monkeypatch.setattr(settings, "llm_hard_cap_usd", 3.00)
    cost_meter.record_cost(db_session, USER_ID, Decimal("2.99"))
    db_session.commit()

    req = ChatRequest(session_id=SESSION_ID, message="first")
    asyncio.run(_prepare_turn(req, USER_ID, db_session))
    # No real LLM cost recorded yet -- only the reservation.
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("3.0100")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            _prepare_turn(ChatRequest(session_id=SESSION_ID, message="second"), USER_ID, db_session)
        )
    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == DAILY_COST_CAP_REACHED


def test_completed_turn_leaves_no_reserve_residue(client, db_session, monkeypatch):
    """B-05: the per-turn reservation is handed back when the stream ends, so
    the ledger carries only real recorded cost."""
    monkeypatch.setattr(settings, "llm_stub", True)

    from services import cost_meter

    status, _body = _post_stream(client, message="hi")
    assert status == 200
    # The stub records no vendor cost, so the ledger must be back at zero.
    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0000")


def test_prepare_turn_failure_releases_the_reserve(client, db_session, monkeypatch):
    """B-05: a crash after the guards (where the reserve is already committed)
    must still hand the reservation back."""
    monkeypatch.setattr(settings, "llm_stub", True)

    from services import cost_meter

    def _boom(prompt_state):
        raise RuntimeError("prompt build exploded")

    monkeypatch.setattr("routes.chat.prompts.build_system_prompt", _boom)

    # C-14: answered as a coded 500 rather than propagating; see
    # test_prompt_build_failure_still_persists_user_message.
    status, _ = _post_stream(client, message="save me")
    assert status == 500

    assert cost_meter.current_spend(db_session, USER_ID) == Decimal("0.0000")


def test_whitespace_only_message_rejected_with_422(client, db_session, monkeypatch):
    """C-10: minLength=1 in the contract stops "" but not "   ". The route
    rejects whitespace-only input before any guard side effect."""
    monkeypatch.setattr(settings, "llm_stub", True)

    r = client.post(
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": "   "},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "empty_message"

    msgs = db_session.execute(
        select(ChatMessage).where(ChatMessage.session_id == SESSION_ID)
    ).scalars().all()
    assert msgs == []


def test_empty_message_rejected_by_contract(client, db_session):
    r = client.post(
        "/api/chat/stream",
        json={"session_id": SESSION_ID, "message": ""},
        headers=AUTH_HEADERS,
    )
    assert r.status_code == 422
    msgs = db_session.execute(
        select(ChatMessage).where(ChatMessage.session_id == SESSION_ID)
    ).scalars().all()
    assert msgs == []


def _fake_session(topic="sql"):
    return SimpleNamespace(topic=topic)


def _fake_profile(**overrides):
    defaults = {"knowledge_level": "intermediate", "confirmed_gaps": []}
    defaults.update(overrides)
    for key in ("confirmed_gaps", "mastered_concepts"):
        if defaults.get(key):
            defaults[key] = [
                {"name": v} if isinstance(v, str) else v for v in defaults[key]
            ]
    return TopicProfile(**defaults)


def _call_build_prompt_state(profile, review_gaps, review_gap=None):
    return _build_prompt_state(
        session=_fake_session(),
        profile=profile,
        ingestion_status="none",
        retrieval_required=False,
        review_gaps=review_gaps,
        review_gap=review_gap,
        pending_check=None,
        quiz_cooldown=None,
    )


def test_build_prompt_state_carries_learner_prefs():
    prefs = {"feedback_pref": "direct_answers", "check_ins": "often",
             "reply_length": "brief"}
    state = _build_prompt_state(
        session=_fake_session(),
        profile=_fake_profile(),
        ingestion_status="none",
        retrieval_required=False,
        review_gaps=False,
        pending_check=None,
        quiz_cooldown=None,
        learner_prefs=prefs,
    )
    assert state["learner_prefs"] == prefs


def test_prepare_turn_prompt_uses_users_row_preferences(db_session):
    # #356: the prompt reads the learner's saved preferences, not defaults.
    import asyncio

    from contracts import ChatRequest
    from routes.chat import _prepare_turn

    user = db_session.get(User, USER_ID)
    user.feedback_pref = "direct_answers"
    user.check_ins = "only_when_asked"
    user.reply_length = "thorough"
    db_session.commit()

    _, system_prompt, _ = asyncio.run(
        _prepare_turn(ChatRequest(session_id=SESSION_ID, message="hi"), USER_ID, db_session)
    )
    assert "- feedback style: direct_answers" in system_prompt
    assert "- check-ins: only_when_asked" in system_prompt
    assert "- reply length: thorough" in system_prompt


def test_build_prompt_state_review_gaps_picks_first_gap():
    profile = _fake_profile(confirmed_gaps=["photosynthesis", "krebs cycle"])
    state = _call_build_prompt_state(profile, review_gaps=True)
    assert state["review_gaps_target"] == "photosynthesis"


def test_build_prompt_state_review_gaps_suppresses_diagnostic():
    profile = _fake_profile(knowledge_level=None, confirmed_gaps=["a"])
    state = _call_build_prompt_state(profile, review_gaps=True)
    assert state["review_gaps_target"] == "a"
    assert state["diagnostic_required"] is False


def test_build_prompt_state_review_gaps_off_when_no_gaps():
    profile = _fake_profile(confirmed_gaps=[])
    state = _call_build_prompt_state(profile, review_gaps=True)
    assert "review_gaps_target" not in state


def test_build_prompt_state_review_gaps_off_when_flag_false():
    profile = _fake_profile(confirmed_gaps=["photosynthesis"])
    state = _call_build_prompt_state(profile, review_gaps=False)
    assert "review_gaps_target" not in state


def test_build_prompt_state_preserves_other_keys():
    profile = _fake_profile(confirmed_gaps=[], last_session_summary="summary text")
    state = _call_build_prompt_state(profile, review_gaps=False)
    assert state["topic"] == "sql"
    assert state["profile"] is profile
    assert state["ingestion_status"] == "none"
    assert state["retrieval_required"] is False
    assert state["diagnostic_required"] is False
    assert state["seed_mode"] is None
    assert state["last_session_summary"] == "summary text"
    assert state["pending_check"] is None
    assert state["quiz_cooldown"] is None


def test_review_gap_targets_named_gap():
    profile = _fake_profile(confirmed_gaps=["gap-a", "gap-b", "gap-c"])
    state = _call_build_prompt_state(profile, review_gaps=True, review_gap="gap-b")
    assert state["review_gaps_target"] == "gap-b"


def test_review_gap_invalid_falls_back_to_first():
    profile = _fake_profile(confirmed_gaps=["gap-a", "gap-b", "gap-c"])
    state = _call_build_prompt_state(profile, review_gaps=True, review_gap="not-a-gap")
    assert state["review_gaps_target"] == "gap-a"


def test_review_gap_none_falls_back_to_first():
    profile = _fake_profile(confirmed_gaps=["gap-a", "gap-b", "gap-c"])
    state = _call_build_prompt_state(profile, review_gaps=True, review_gap=None)
    assert state["review_gaps_target"] == "gap-a"


def test_build_prompt_state_carries_rolling_summary():
    """P2 AC3: rolling_summary flows from the session onto the prompt state
    so build_dynamic_context can render it."""
    session = _fake_session()
    session.rolling_summary = "covered limits and continuity"
    profile = _fake_profile()
    state = _build_prompt_state(
        session=session,
        profile=profile,
        ingestion_status="none",
        retrieval_required=False,
        review_gaps=False,
        pending_check=None,
        quiz_cooldown=None,
    )
    assert state["rolling_summary"] == "covered limits and continuity"


def test_build_prompt_state_rolling_summary_defaults_none():
    state = _call_build_prompt_state(_fake_profile(), review_gaps=False)
    assert state["rolling_summary"] is None


def test_build_prompt_state_prefetched_chunks_wraps_excerpts():
    """F-56: prefetched_chunks (server force-retrieve, Task 11) is wrapped
    via agent.excerpt.wrap_chunk into prefetched_excerpts on the prompt
    state, which prompts.build_dynamic_context renders as PROVIDED."""
    state = _build_prompt_state(
        session=_fake_session(),
        profile=_fake_profile(),
        ingestion_status="ready",
        retrieval_required=True,
        review_gaps=False,
        pending_check=None,
        quiz_cooldown=None,
        prefetched_chunks=[{"doc_id": "d1", "text": "leaves convert light"}],
    )
    assert len(state["prefetched_excerpts"]) == 1
    excerpt = state["prefetched_excerpts"][0]
    assert "leaves convert light" in excerpt
    assert "document_excerpt" in excerpt


def test_build_prompt_state_no_prefetched_chunks_omits_key():
    state = _call_build_prompt_state(_fake_profile(), review_gaps=False)
    assert "prefetched_excerpts" not in state


def test_review_gap_mastered_target_accepted():
    profile = _fake_profile(
        confirmed_gaps=["gap-a"], mastered_concepts=["photosynthesis"]
    )
    state = _call_build_prompt_state(
        profile, review_gaps=True, review_gap="photosynthesis"
    )
    assert state["review_gaps_target"] == "photosynthesis"
    assert state["review_gaps_retention"] is True


def test_review_gap_gap_target_not_retention():
    profile = _fake_profile(
        confirmed_gaps=["gap-a"], mastered_concepts=["photosynthesis"]
    )
    state = _call_build_prompt_state(profile, review_gaps=True, review_gap="gap-a")
    assert state["review_gaps_target"] == "gap-a"
    assert state["review_gaps_retention"] is False


def test_review_gaps_activates_with_only_mastered():
    profile = _fake_profile(confirmed_gaps=[], mastered_concepts=["photosynthesis"])
    state = _call_build_prompt_state(profile, review_gaps=True)
    assert state["review_gaps_target"] == "photosynthesis"
    assert state["review_gaps_retention"] is True
    assert state["diagnostic_required"] is False


def test_review_gap_invalid_still_falls_back_to_first_gap():
    profile = _fake_profile(
        confirmed_gaps=["gap-a"], mastered_concepts=["photosynthesis"]
    )
    state = _call_build_prompt_state(profile, review_gaps=True, review_gap="junk")
    assert state["review_gaps_target"] == "gap-a"
    assert state["review_gaps_retention"] is False


def test_review_gaps_off_when_both_lists_empty():
    profile = _fake_profile(confirmed_gaps=[], mastered_concepts=[])
    state = _call_build_prompt_state(profile, review_gaps=True)
    assert "review_gaps_target" not in state
    assert "review_gaps_retention" not in state


def test_resumed_profile_skips_diagnostic():
    """R1.1 AC2: a resume-seeded profile carries a non-null knowledge_level,
    so the 3Q diagnostic branch must not be taken."""
    profile = _fake_profile(knowledge_level="intermediate", confirmed_gaps=["gap-a"])
    state = _call_build_prompt_state(profile, review_gaps=False)
    assert state["diagnostic_required"] is False
