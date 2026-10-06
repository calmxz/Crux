from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config import settings
from db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # C-16: server_default so a row inserted outside the ORM (raw SQL, a
    # restore, a future bulk import) still gets a timestamp, and NOT NULL so
    # "when was this created" is never unanswerable. The Python-side default
    # stays: it is what writes a tz-aware UTC value on every ORM insert.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), default=_utcnow
    )
    accepted_terms_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    terms_version: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    # F-46: onboarding is account state, not per-browser localStorage. NULLs
    # mean "never onboarded on the server" (pre-0020 rows hydrate FE defaults).
    display_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    feedback_pref: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    onboarding_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    # #356: learner preferences injected into the tutor prompt. Values are
    # enforced by the MePatchRequest enums; a NULL feedback_pref reads as
    # "hints" (routes/me.py, agent/prompts.py).
    check_ins: Mapped[str] = mapped_column(
        String, nullable=False, server_default="sometimes", default="sometimes"
    )
    reply_length: Mapped[str] = mapped_column(
        String, nullable=False, server_default="balanced", default="balanced"
    )

    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user")
    usage_counters: Mapped[list["UsageCounter"]] = relationship("UsageCounter", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        # B-11: every list/library/aggregate query filters on user_id.
        Index("ix_sessions_user_id", "user_id"),
        # B-05: DB-authoritative form of the F-34 duplicate-active-topic
        # guard; the route pre-check remains for the friendly 409 payload.
        Index(
            "uq_sessions_active_topic",
            "user_id",
            text("lower(topic)"),
            unique=True,
            sqlite_where=text("ended_at IS NULL"),
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    topic: Mapped[str] = mapped_column(String, default="")
    topic_profile_json: Mapped[str] = mapped_column(Text, default="{}")
    kw_index_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    pending_check_json: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    quiz_cooldown_json: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    # #340: check-level pointer across sets; see services/pending_check_store.py.
    current_check_json: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    # #354: the once-per-session topic card. "awaiting_level" when the session
    # started without a level, "done" once suggest_topics ran, NULL otherwise.
    # See services/topic_suggest_service.py.
    topic_suggest_state: Mapped[str | None] = mapped_column(
        String(16), nullable=True, default=None
    )
    # C-16: see User.created_at.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), default=_utcnow
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    rolling_summary: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    rolling_summary_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    # F-05: lazily materialised mean of this session's chunk embeddings.
    # NULL means "not computed yet" (or invalidated by an ingest/delete);
    # retrieval_service recomputes it once and writes it back.
    chunk_centroid: Mapped[list[float] | None] = mapped_column(
        Vector(settings.embedding_dim), nullable=True, default=None
    )

    user: Mapped["User"] = relationship("User", back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="session")
    learning_events: Mapped[list["LearningEvent"]] = relationship("LearningEvent", back_populates="session")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "status IN ('complete', 'cancelled', 'error', 'partial')",
            name="chat_messages_status_check",
        ),
        # C-15: the only writers are routes/chat.py (role='user') and
        # agent/tutor.py (role='assistant', including the partial-on-abort
        # path). System and tool messages are assembled in memory for the LLM
        # call and never persisted, so anything else in this column is a bug.
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="chat_messages_role_check",
        ),
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
        # F-09: history loads order by id DESC within a session
        # (routes/sessions.py), which the (session_id, created_at) index
        # cannot serve without a sort.
        Index("ix_chat_messages_sid_id_desc", "session_id", text("id DESC")),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    citations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # C-16: see User.created_at.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), default=_utcnow
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="complete")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_batch_json: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    session: Mapped["Session"] = relationship("Session", back_populates="messages")


class UsageCounter(Base):
    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint("user_id", "date_utc", name="uq_usage_counters_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    date_utc: Mapped[str] = mapped_column(String, nullable=False)  # YYYY-MM-DD
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="usage_counters")


class LearningEvent(Base):
    __tablename__ = "learning_events"
    __table_args__ = (
        Index("ix_learning_events_session", "session_id"),
        # F-07: the review queue filters on created_at across every session a
        # user owns, so session_id alone cannot serve that scan.
        Index("ix_learning_events_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    gap_tested: Mapped[str] = mapped_column(String, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    correct: Mapped[bool] = mapped_column(nullable=False)
    # C-16: see User.created_at.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), default=_utcnow
    )
    selected_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correct_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    options_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose: Mapped[str | None] = mapped_column(String, nullable=True)

    session: Mapped["Session"] = relationship("Session", back_populates="learning_events")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        # C-15: the ingestion state machine is pending -> processing ->
        # ready|failed (worker.py, services/ingestion_service.py,
        # routes/upload.py), and the DocumentStatus contract declares exactly
        # these four. Legacy rows may still hold NULL, which a CHECK admits.
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')",
            name="documents_status_check",
        ),
        Index("ix_documents_status_id", "status", "id"),
        # C-08: re-uploading identical bytes into the same session must return
        # the existing row instead of creating a duplicate. Partial so legacy
        # NULL hashes never collide and a failed row never blocks a retry.
        Index(
            "uq_documents_session_sha",
            "session_id",
            "content_sha256",
            unique=True,
            postgresql_where=text("content_sha256 IS NOT NULL AND status <> 'failed'"),
            sqlite_where=text("content_sha256 IS NOT NULL AND status <> 'failed'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # C-08: sha256 of the uploaded bytes. NULL on rows created before 0026.
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # C-16: see User.created_at.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), default=_utcnow
    )

    session: Mapped["Session"] = relationship("Session", back_populates="documents")


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "chunk_index", name="uq_chunk_embeddings_doc_idx"
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class DailyCostLedger(Base):
    __tablename__ = "daily_cost_ledger"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    date_utc: Mapped[str] = mapped_column(String, primary_key=True)  # YYYY-MM-DD
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0.0000"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class LlmCallLog(Base):
    """Per-call LLM cost attribution. Analytics-only (roadmap R3 consumes it);
    additive to DailyCostLedger, never a substitute -- cap gating stays on the
    daily ledger. No readers exist yet in this slice."""

    __tablename__ = "llm_call_log"
    __table_args__ = (
        Index("ix_llm_call_log_user", "user_id"),
        Index("ix_llm_call_log_session", "session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("sessions.id"), nullable=True)
    purpose: Mapped[str] = mapped_column(String, nullable=False)  # chat | followup | summary
    model: Mapped[str] = mapped_column(String, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    # P1 instrumentation (slice 2): nullable per-call token counts.
    # cached_tokens = Gemini implicit-prefix-cache hit portion of prompt_tokens.
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
