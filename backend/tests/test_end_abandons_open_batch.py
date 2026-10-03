"""TDD: ending a session abandons any dangling (unanswered) check-batch.

Bug found in the WS-F F2 live smoke (2026-07-05): a session ended while a
check-question batch was still open. On resume via "Review my gaps", the tutor
called ask_check_questions, hit the "a batch is already open" guard, and
surfaced a confusing "Could not ask questions" on a read-only ended session.

abandon_open_batch resolves the dangling batch on end: remaining pending items
become "skipped", the batch is frozen onto its message for honest history, and
the pending pointer is cleared -- no learning events and no mastery effects
(the only profile write is grading an in-progress diagnostic, #340). A later
ask_check_questions then succeeds.
"""

import json
from datetime import datetime, timezone

import pytest

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from services import check_question_service, pending_check_store

USER_ID = "u_abandon_1"


@pytest.fixture
def seeded_session(db_session):
    db_session.add(User(id=USER_ID))
    session = SessionModel(
        id="s_abandon_1", user_id=USER_ID, topic="bio",
        topic_profile_json=TopicProfile().model_dump_json(),
    )
    db_session.add(session)
    db_session.commit()
    return session


def _open_batch(db, session_id, n=2):
    ctx = ToolContext(db=db, session_id=session_id, user_id=USER_ID,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    return check_question_service.register(db, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=session_id, gap="g",
        items=[{"question": f"Q{i}?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "a."} for i in range(n)]))


def test_abandon_clears_pending_pointer(db_session, seeded_session):
    sid = seeded_session.id
    _open_batch(db_session, sid)
    assert pending_check_store.get_pending_check(db_session, sid) is not None

    assert check_question_service.abandon_open_batch(db_session, sid) is True
    assert pending_check_store.get_pending_check(db_session, sid) is None


def test_abandon_unblocks_a_fresh_batch(db_session, seeded_session):
    """The actual bug: a second register must fail while a batch is open, then
    succeed once the dangling batch has been abandoned."""
    sid = seeded_session.id
    _open_batch(db_session, sid)

    blocked = _open_batch(db_session, sid)
    assert blocked.ok is False and "already open" in (blocked.error or "")

    check_question_service.abandon_open_batch(db_session, sid)

    unblocked = _open_batch(db_session, sid)
    assert unblocked.ok is True


def test_abandon_freezes_pending_items_as_skipped(db_session, seeded_session):
    sid = seeded_session.id
    _open_batch(db_session, sid)
    msg = ChatMessage(session_id=sid, role="assistant", content="q")
    db_session.add(msg)
    db_session.commit()
    check_question_service.attach_message_id(db_session, sid, msg.id)

    check_question_service.abandon_open_batch(db_session, sid)

    db_session.refresh(msg)
    frozen = json.loads(msg.check_batch_json)
    # Frozen batch is resolved (current_index past the end) with every item skipped.
    assert frozen["current_index"] == frozen["total"] == 2
    assert [it["status"] for it in frozen["items"]] == ["skipped", "skipped"]


def test_abandon_is_noop_without_a_batch(db_session, seeded_session):
    sid = seeded_session.id
    assert check_question_service.abandon_open_batch(db_session, sid) is False


def test_end_route_abandons_open_batch(
    client, db_session, seeded_session, mock_litellm, llm_text, monkeypatch
):
    """End-to-end: POST /end clears a dangling batch so review-gaps resume works."""
    async def fake_acompletion(**kwargs):
        return llm_text("wrapped up")

    monkeypatch.setattr("services.summary_service.litellm.acompletion", fake_acompletion)

    sid = seeded_session.id
    _open_batch(db_session, sid)
    assert pending_check_store.get_pending_check(db_session, sid) is not None

    r = client.post(f"/api/sessions/{sid}/end?user_id={USER_ID}")
    assert r.status_code == 200, r.text
    assert pending_check_store.get_pending_check(db_session, sid) is None


def test_abandon_clears_a_done_but_uncleared_batch(db_session, seeded_session):
    """Regression (live smoke 2026-07-05): a fully-answered batch whose pending
    pointer was never cleared still blocks review-gaps (the register guard
    blocks on ANY non-null pending_check). End must clear it too, not skip it."""
    sid = seeded_session.id
    _open_batch(db_session, sid)
    # Resolve the whole batch so it is done, but leave the pointer dangling.
    check_question_service.skip(db_session, sid, 0)
    check_question_service.skip(db_session, sid, 1)
    pc_done = pending_check_store.get_pending_check(db_session, sid)
    assert pending_check_store.is_done(pc_done) is True

    assert check_question_service.abandon_open_batch(db_session, sid) is True
    assert pending_check_store.get_pending_check(db_session, sid) is None
    # And a fresh batch can now be opened (the actual unblock).
    assert _open_batch(db_session, sid).ok is True
