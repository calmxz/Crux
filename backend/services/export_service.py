"""#361: one-file export of everything the server holds for a learner.

The counterpart of delete_user_account ("take it or destroy it"). Covers the
same tables minus internal state a learner cannot use: chunk embeddings,
open-check pointers, the rolling summary, and the per-call LLM log. Uploads
are listed by metadata; the PDF bytes are not included.

Pure read, one query per table (no per-session N+1), everything oldest first.
"""

import json
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from contracts import (
    Citation,
    DataExport,
    ExportAccount,
    ExportCheckAnswer,
    ExportDocument,
    ExportMessage,
    ExportSession,
    ExportUsageDay,
)
from db.models import (
    ChatMessage,
    DailyCostLedger,
    Document,
    LearningEvent,
    UsageCounter,
    User,
)
from db.models import Session as SessionModel
from services.profile_service import profile_from_row
from services.session_enrichment import aware_utc

FORMAT_VERSION = 1


def _citations(raw: str | None) -> list[Citation]:
    try:
        return [Citation(**c) for c in json.loads(raw or "[]")]
    except (ValueError, TypeError):
        return []


def _options(raw: str | None) -> list[str]:
    try:
        data = json.loads(raw or "[]")
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list) or not all(isinstance(o, str) for o in data):
        return []
    return data


def _account(user: User) -> ExportAccount:
    return ExportAccount(
        user_id=user.id,
        created_at=aware_utc(user.created_at),
        display_name=user.display_name,
        # NULL = never set; report the effective default, as GET /me does.
        feedback_pref=user.feedback_pref or "hints",
        check_ins=user.check_ins,
        reply_length=user.reply_length,
        onboarding_complete=bool(user.onboarding_complete),
        accepted_terms_at=aware_utc(user.accepted_terms_at),
        terms_version=user.terms_version,
    )


def _usage(db: Session, user_id: str) -> list[ExportUsageDay]:
    counts = dict(
        db.execute(
            select(UsageCounter.date_utc, UsageCounter.count).where(
                UsageCounter.user_id == user_id
            )
        ).all()
    )
    costs = dict(
        db.execute(
            select(DailyCostLedger.date_utc, DailyCostLedger.cost_usd).where(
                DailyCostLedger.user_id == user_id
            )
        ).all()
    )
    return [
        ExportUsageDay(
            date_utc=day,
            messages=counts.get(day, 0),
            cost_usd=float(costs.get(day, 0)),
        )
        for day in sorted(counts.keys() | costs.keys())
    ]


def build_export(db: Session, user_id: str) -> DataExport:
    user = db.get(User, user_id)
    sessions = db.execute(
        select(SessionModel)
        .where(SessionModel.user_id == user_id)
        .order_by(SessionModel.created_at, SessionModel.id)
    ).scalars().all()
    session_ids = select(SessionModel.id).where(SessionModel.user_id == user_id)

    messages: dict[str, list[ExportMessage]] = defaultdict(list)
    for m in db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id.in_(session_ids))
        .order_by(ChatMessage.id)
    ).scalars():
        messages[m.session_id].append(
            ExportMessage(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=aware_utc(m.created_at),
                status=m.status,
                citations=_citations(m.citations_json),
            )
        )

    answers: dict[str, list[ExportCheckAnswer]] = defaultdict(list)
    for e in db.execute(
        select(LearningEvent)
        .where(LearningEvent.session_id.in_(session_ids))
        .order_by(LearningEvent.id)
    ).scalars():
        answers[e.session_id].append(
            ExportCheckAnswer(
                id=e.id,
                gap_tested=e.gap_tested,
                question=e.question,
                correct=e.correct,
                created_at=aware_utc(e.created_at),
                options=_options(e.options_json),
                selected_index=e.selected_index,
                correct_index=e.correct_index,
                purpose=e.purpose,
            )
        )

    documents: dict[str, list[ExportDocument]] = defaultdict(list)
    for d in db.execute(
        select(Document)
        .where(Document.session_id.in_(session_ids))
        .order_by(Document.id)
    ).scalars():
        documents[d.session_id].append(
            ExportDocument(
                id=d.id,
                filename=d.filename,
                status=d.status,
                error=d.error,
                page_count=d.page_count,
                created_at=aware_utc(d.created_at),
            )
        )

    return DataExport(
        format_version=FORMAT_VERSION,
        exported_at=datetime.now(timezone.utc),
        account=_account(user) if user is not None else None,
        sessions=[
            ExportSession(
                id=s.id,
                topic=s.topic,
                created_at=aware_utc(s.created_at),
                ended_at=aware_utc(s.ended_at),
                pinned=bool(s.pinned),
                topic_profile=profile_from_row(s),
                messages=messages[s.id],
                check_answers=answers[s.id],
                documents=documents[s.id],
            )
            for s in sessions
        ],
        usage=_usage(db, user_id),
    )
