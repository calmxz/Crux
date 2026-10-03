"""User-row lifecycle helper.

User rows are created lazily on the first authenticated backend call. Terms
consent is stamped ONLY when the verified JWT carries the accepted_terms
metadata claim set by the register form (F-52): Supabase signUp is callable
directly, bypassing the client-side checkbox, so row-existence alone does
not evidence consent.
"""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from db.models import (
    ChatMessage,
    ChunkEmbedding,
    DailyCostLedger,
    Document,
    LearningEvent,
    LlmCallLog,
    UsageCounter,
    User,
)
from db.models import Session as SessionModel
from lib.terms import CURRENT_TERMS_VERSION
from services import object_store
from services.sql_dialect import dialect_insert


def ensure_user(db: Session, user_id: str, *, accepted_terms: bool = False) -> User:
    """Return the users row for user_id, creating it if absent.

    On create, stamp accepted_terms_at (server-owned, tz-aware) and
    terms_version ONLY when accepted_terms is True; the caller derives this
    from the verified JWT's accepted_terms metadata claim, not from
    row-existence (F-52). Existing rows are returned unchanged (no
    re-stamp). Race-safe: INSERT ... ON CONFLICT DO NOTHING so two
    concurrent first-requests cannot IntegrityError, and the loser
    re-selects the winner's row (F-37). Writes stay pending until the
    caller's commit.

    After the insert we still re-select (needed either way to get an ORM
    row); on the winning path we then patch accepted_terms_at back to the
    exact tz-aware value we wrote, via set_committed_value (marks it as
    loaded, not dirty -- no spurious UPDATE on next flush). SQLite's
    DateTime(timezone=True) has no native timestamptz and returns a naive
    datetime on read-back (see the round-trip note in
    test_ensure_user_is_idempotent_and_does_not_restamp), so without this
    patch a freshly created row would lose tzinfo on the common path. The
    losing side of a genuine race does not need this: it only asserts on
    the winner's identity/terms fields, not tzinfo fidelity.
    """
    user = db.get(User, user_id)
    if user is not None:
        return user
    now = datetime.now(timezone.utc)
    stamp = now if accepted_terms else None
    insert = dialect_insert(db)
    result = db.execute(
        insert(User)
        .values(
            id=user_id,
            accepted_terms_at=stamp,
            terms_version=CURRENT_TERMS_VERSION if accepted_terms else None,
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    created = db.execute(select(User).where(User.id == user_id)).scalar_one()
    if result.rowcount == 1 and accepted_terms:
        set_committed_value(created, "accepted_terms_at", now)
    return created


def delete_user_account(db: Session, user_id: str) -> list[str]:
    """Delete every row belonging to user_id, children before parents.

    Returns the object-store keys of the user's uploads; the caller deletes
    them best-effort AFTER committing. Does not commit. Idempotent: a user
    with no rows (or no users row) is a no-op.

    Order is explicit rather than cascade-reliant: SQLite (tests) does not
    enforce FK cascades, and chunk_embeddings.session_id has no ON DELETE
    CASCADE in Postgres either.
    """
    session_ids = select(SessionModel.id).where(SessionModel.user_id == user_id)
    docs = db.execute(
        select(Document.id, Document.filename).where(Document.session_id.in_(session_ids))
    ).all()
    keys = [object_store.key_for(doc_id, Path(filename).name) for doc_id, filename in docs]

    # Delete documents by the ids we just read, not by a live subquery: a
    # document uploaded between the read and the delete would otherwise lose
    # its row while its blob survives. Left in place, that late row makes the
    # sessions delete below fail on its FK, rolling the whole transaction
    # back -- the safe outcome (the learner retries).
    doc_ids = [doc_id for doc_id, _ in docs]
    db.execute(
        delete(ChunkEmbedding).where(
            or_(
                ChunkEmbedding.session_id.in_(session_ids),
                ChunkEmbedding.document_id.in_(doc_ids),
            )
        ),
        execution_options={"synchronize_session": False},
    )
    db.execute(
        delete(Document).where(Document.id.in_(doc_ids)),
        execution_options={"synchronize_session": False},
    )
    db.execute(
        delete(LearningEvent).where(LearningEvent.session_id.in_(session_ids)),
        execution_options={"synchronize_session": False},
    )
    db.execute(
        delete(ChatMessage).where(ChatMessage.session_id.in_(session_ids)),
        execution_options={"synchronize_session": False},
    )
    db.execute(
        delete(LlmCallLog).where(
            or_(LlmCallLog.user_id == user_id, LlmCallLog.session_id.in_(session_ids))
        ),
        execution_options={"synchronize_session": False},
    )
    db.execute(
        delete(UsageCounter).where(UsageCounter.user_id == user_id),
        execution_options={"synchronize_session": False},
    )
    db.execute(
        delete(DailyCostLedger).where(DailyCostLedger.user_id == user_id),
        execution_options={"synchronize_session": False},
    )
    db.execute(
        delete(SessionModel).where(SessionModel.user_id == user_id),
        execution_options={"synchronize_session": False},
    )
    db.execute(
        delete(User).where(User.id == user_id),
        execution_options={"synchronize_session": False},
    )
    return keys
