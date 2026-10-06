"""P3.1 statement-count budget for the chat prepare path.

Counts SQL statements issued by _prepare_turn via before_cursor_execute.
Budget (spec P3.1): <=7 happy path, <=8 when the gap-accuracy aggregate
runs (non-empty confirmed_gaps). Uses an existing user: the first-turn-ever
user-create path is excluded from the budget by design.

B-05 raised both numbers by exactly 1: the cost gate no longer reads today's
spend and compares, it reserves it (one INSERT .. ON CONFLICT DO UPDATE ..
RETURNING against daily_cost_ledger) so concurrent turns serialize on the
ledger row. The step-1 combined read still issues its single statement (it
keeps the user-existence probe), hence +1 rather than +0.
"""

import asyncio
from contextlib import contextmanager
from uuid import uuid4

import pytest
from sqlalchemy import event as _sa_event

from contracts import ChatRequest, TopicProfile
from db.models import LearningEvent, User
from db.models import Session as SessionModel
from routes.chat import _prepare_turn

# Captured at module-import time (before the autouse fixture below ever runs)
# so this is a handle on the REAL function, not whatever the autouse fixture
# has since patched services.retrieval_service.semantic_fallback_required to.
from services.retrieval_service import (
    semantic_fallback_required as _real_semantic_fallback_required,
)


@contextmanager
def count_queries(db):
    bind = db.get_bind()
    state = {"n": 0, "statements": []}

    def _before(conn, cursor, statement, params, context, executemany):
        state["n"] += 1
        state["statements"].append(statement.split("\n")[0][:120])

    _sa_event.listen(bind, "before_cursor_execute", _before)
    try:
        yield state
    finally:
        _sa_event.remove(bind, "before_cursor_execute", _before)


USER_ID = "perf-user"


@pytest.fixture(autouse=True)
def _stub_semantic_fallback(monkeypatch):
    # D2.2: this budget measures _prepare_turn's own statements. In an
    # environment where settings.llm_stub_enabled is False (e.g. a real
    # gemini_api_key in .env), the real semantic_fallback_required would add
    # one has_ready_document SELECT (lexical gate is False by default here,
    # since seeded_session has no kw_index_json entries). Pin it off so this
    # test measures _prepare_turn regardless of ambient LLM-stub config.
    async def _fake_fallback(*a, **kw):
        return False, None

    monkeypatch.setattr(
        "routes.chat.retrieval_service.semantic_fallback_required",
        _fake_fallback,
    )


@pytest.fixture
def seeded_session(db_session):
    db_session.add(User(id=USER_ID))
    sess = SessionModel(id=str(uuid4()), user_id=USER_ID, topic="algebra")
    db_session.add(sess)
    db_session.commit()
    return sess


def _run_prepare(db, session_id):
    req = ChatRequest(session_id=session_id, message="explain factoring")
    return asyncio.run(_prepare_turn(req, USER_ID, db))


def test_prepare_turn_context_leaves_no_open_transaction(db_session, seeded_session):
    """F-13: _prepare_turn_context's segment is read-only, and the two awaited
    embedding round-trips follow it. It must commit so the pooled connection
    is released while those awaits are in flight."""
    from routes.chat import _prepare_turn_context

    session_id = seeded_session.id
    sess = db_session.get(SessionModel, session_id)
    db_session.expunge(sess)
    req = ChatRequest(session_id=session_id, message="explain factoring")

    _prepare_turn_context(req, db_session, sess)

    assert db_session.in_transaction() is False


def test_prepare_turn_budget_no_gaps(db_session, seeded_session):
    # Evaluate .id BEFORE the counted block: the fixture's commit expires the
    # ORM instance (expire_on_commit=True), so accessing .id inside the block
    # would trigger an extra refresh SELECT that is test-setup overhead, not
    # part of _prepare_turn's own work. Mirrors test_sessions_perf.py's
    # pattern of using plain-string ids inside count_queries.
    session_id = seeded_session.id
    with count_queries(db_session) as q:
        _run_prepare(db_session, session_id)
    # 6 (pre-B-05 budget) + 1 (the reserve_cost upsert that replaced the plain
    # read gate; see the module docstring).
    assert q["n"] <= 7, f"prepare path used {q['n']} statements:\n" + "\n".join(q["statements"])


def test_prepare_turn_budget_with_gaps(db_session, seeded_session):
    profile = TopicProfile(knowledge_level="beginner", confirmed_gaps=[{"name": "factoring"}])
    seeded_session.topic_profile_json = profile.model_dump_json()
    db_session.add(
        LearningEvent(
            session_id=seeded_session.id,
            gap_tested="factoring",
            question="q1",
            correct=False,
        )
    )
    db_session.commit()
    session_id = seeded_session.id
    with count_queries(db_session) as q:
        messages, system_prompt, ctx = _run_prepare(db_session, session_id)
    # 7 (pre-B-05 budget) + 1 (the reserve_cost upsert; see the module docstring).
    assert q["n"] <= 8, f"prepare path used {q['n']} statements:\n" + "\n".join(q["statements"])
    # Functional proof the aggregate actually ran on this branch (not just
    # that the statement count happened to fit).
    assert "GAP_ACCURACY:" in system_prompt and "factoring" in system_prompt


def test_prepare_turn_budget_doc_bearing_semantic_fallback(db_session, seeded_session, monkeypatch):
    """D2.2 TTFT pre-flight guard: on a doc-bearing session whose query misses
    the lexical gate, _prepare_turn actually calls the REAL
    semantic_fallback_required (the file's autouse fixture above pins it to
    `lambda: False` for the other tests here; this test reverses that one
    patch so the real pre-flight cost -- awaited before StreamingResponse --
    is what gets measured).

    Sqlite path is deterministic and network-free: semantic_fallback_required
    -> has_ready_document SELECT (True) -> _session_centroid's dialect guard
    (bind dialect != "postgresql") returns None immediately -> function
    returns False. litellm.embedding is never reached on this dialect; the
    embedding call itself is Postgres-only and is covered by the owed live
    perf re-measure, not by this statement-count test.
    """
    import json as _json

    from config import settings
    from db.models import Document

    # Reverse the autouse fixture's patch for this test only: rebind
    # routes.chat's module-level reference back to the real function (the
    # one captured at module-import time, above, before the autouse fixture
    # ever ran).
    monkeypatch.setattr(
        "routes.chat.retrieval_service.semantic_fallback_required",
        _real_semantic_fallback_required,
    )
    # llm_stub_enabled is a read-only property (llm_stub OR gemini_api_key ==
    # "test"); patch its inputs directly so this test's outcome does not
    # depend on ambient .env config.
    monkeypatch.setattr(settings, "llm_stub", False)
    monkeypatch.setattr(settings, "gemini_api_key", "")

    db_session.add(
        Document(session_id=seeded_session.id, filename="notes.pdf", status="ready")
    )
    # Populated but disjoint from the "explain factoring" query issued by
    # _run_prepare below, so keyword_index.match_required is False (lexical
    # gate misses) and semantic_fallback_required is actually invoked.
    seeded_session.kw_index_json = _json.dumps(["photosynthesi", "chlorophyl"])
    db_session.commit()

    session_id = seeded_session.id
    with count_queries(db_session) as q:
        _run_prepare(db_session, session_id)
    # 7 (base no-gaps budget, see test_prepare_turn_budget_no_gaps) + 1
    # (has_ready_document SELECT inside semantic_fallback_required; on
    # sqlite, _session_centroid's dialect guard short-circuits before any
    # further query -- litellm.embedding is unreachable here -- so this is
    # the fallback's entire statement cost on this dialect). Tight, not <=:
    # this test's whole point is to prove the fallback's real SQL cost is
    # exactly one extra SELECT, not to leave headroom for it to grow.
    assert q["n"] == 8, f"prepare path used {q['n']} statements:\n" + "\n".join(q["statements"])
