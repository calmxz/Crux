"""C-18: the two 20-message history windows need a secondary order key.

`routes/chat.py::_prepare_turn_context` and `routes/sessions.py::_recent_history`
both take the newest 20 messages with `ORDER BY created_at DESC LIMIT 20` and
then `reversed()` the rows. With no tiebreaker, messages written inside the same
clock tick (sqlite stores microseconds, Postgres too, but a batched write or a
coarse clock collapses them) can be windowed and ordered arbitrarily, so the
prompt history can silently reorder or drop the wrong turn.

`services/session_enrichment.py` and the session library query already order by
`(created_at DESC, id DESC)`; these two sites are brought in line.

Both functions reverse their window, so the returned order is chronological
(id-ascending among ties) and the window keeps the HIGHEST ids on a tie. The
statement assertions are the load-bearing ones: sqlite may satisfy an untied
`ORDER BY created_at DESC` from ix_chat_messages_session_created by walking the
index backwards, which happens to produce id-descending ties, so the functional
assertion alone would not fail without the fix.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import event as _sa_event

from contracts import ChatRequest
from db.models import ChatMessage, User
from db.models import Session as SessionModel

USER_ID = "order-user"
SAME_TICK = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
WINDOW = 20


@contextmanager
def capture_statements(db):
    bind = db.get_bind()
    stmts: list[str] = []

    def _before(conn, cursor, statement, params, context, executemany):
        stmts.append(statement)

    _sa_event.listen(bind, "before_cursor_execute", _before)
    try:
        yield stmts
    finally:
        _sa_event.remove(bind, "before_cursor_execute", _before)


@pytest.fixture
def tied_session(db_session):
    """One session with WINDOW + 1 messages that all share a created_at."""
    db_session.add(User(id=USER_ID))
    sess = SessionModel(id=str(uuid4()), user_id=USER_ID, topic="algebra")
    db_session.add(sess)
    db_session.commit()
    for n in range(WINDOW + 1):
        db_session.add(
            ChatMessage(
                session_id=sess.id,
                role="user",
                content=f"m{n:02d}",
                created_at=SAME_TICK,
            )
        )
    db_session.commit()
    return sess


def _message_select(stmts: list[str]) -> str:
    hits = [s for s in stmts if "FROM chat_messages" in s and "ORDER BY" in s]
    assert hits, stmts
    return hits[-1]


def test_recent_history_orders_by_id_within_a_created_at_tie(db_session, tied_session):
    from routes.sessions import _recent_history

    with capture_statements(db_session) as stmts:
        rows = _recent_history(db_session, tied_session.id)

    sql = " ".join(_message_select(stmts).split())
    assert "chat_messages.id DESC" in sql, sql
    # Oldest of the 21 falls out of the window; the rest come back oldest-first.
    assert [r["content"] for r in rows] == [f"m{n:02d}" for n in range(1, WINDOW + 1)]


def test_prepare_turn_context_orders_by_id_within_a_created_at_tie(
    db_session, tied_session
):
    from routes.chat import _prepare_turn_context

    req = ChatRequest(session_id=tied_session.id, message="explain factoring")
    sess = db_session.get(SessionModel, tied_session.id)
    db_session.expunge(sess)

    with capture_statements(db_session) as stmts:
        messages, _profile, _gap_accuracy, _retrieval = _prepare_turn_context(
            req, db_session, sess
        )

    sql = " ".join(_message_select(stmts).split())
    assert "chat_messages.id DESC" in sql, sql
    # The live user message is appended after the history window.
    assert messages[-1] == {"role": "user", "content": "explain factoring"}
    assert [m["content"] for m in messages[:-1]] == [
        f"m{n:02d}" for n in range(1, WINDOW + 1)
    ]
