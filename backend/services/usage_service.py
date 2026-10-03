"""Read-side spend transparency (roadmap R3.2). First reader of llm_call_log.

Pure SQL + Python, zero LLM calls. Cap tiers come exclusively from
cost_meter.check_cap_from_spend (config-backed; urgent derived there) so the
thresholds have a single source of truth.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from contracts import DailySpend, SessionSpend, UsageSummaryResponse
from db.models import DailyCostLedger, LlmCallLog
from db.models import Session as SessionModel
from services.cost_meter import check_cap_from_spend, next_midnight_utc

WINDOW_DAYS = 14
TOP_SESSIONS = 3


def usage_summary(
    db: Session, user_id: str, now: datetime | None = None
) -> UsageSummaryResponse:
    now = now or datetime.now(timezone.utc)
    today = now.date()
    window = [today - timedelta(days=i) for i in range(WINDOW_DAYS - 1, -1, -1)]
    keys = [d.isoformat() for d in window]

    rows = db.execute(
        select(DailyCostLedger.date_utc, DailyCostLedger.cost_usd)
        .where(DailyCostLedger.user_id == user_id)
        .where(DailyCostLedger.date_utc.in_(keys))
    ).all()
    by_date = {date_utc: float(cost) for date_utc, cost in rows}
    daily = [
        DailySpend(date_utc=d, cost_usd=by_date.get(d.isoformat(), 0.0))
        for d in window
    ]

    caps = check_cap_from_spend(Decimal(str(by_date.get(today.isoformat(), 0.0))))

    top_rows = db.execute(
        select(
            LlmCallLog.session_id,
            SessionModel.topic,
            func.sum(LlmCallLog.cost_usd).label("total"),
        )
        .join(SessionModel, LlmCallLog.session_id == SessionModel.id)
        .where(LlmCallLog.user_id == user_id)
        .group_by(LlmCallLog.session_id, SessionModel.topic)
        .order_by(func.sum(LlmCallLog.cost_usd).desc(), LlmCallLog.session_id.asc())
        .limit(TOP_SESSIONS)
    ).all()
    top_sessions = [
        SessionSpend(session_id=sid, topic=topic or "", cost_usd=float(total))
        for sid, topic, total in top_rows
    ]

    return UsageSummaryResponse(
        daily=daily,
        today_spend_usd=float(caps.used),
        soft_cap_usd=float(caps.soft_cap),
        urgent_cap_usd=float(caps.urgent_cap),
        hard_cap_usd=float(caps.hard_cap),
        top_sessions=top_sessions,
        resets_at=next_midnight_utc(now),
    )
