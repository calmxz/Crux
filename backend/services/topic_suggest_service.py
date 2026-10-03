"""The start-flow topic card (#354, decided in #341).

Once per session, on the first reply after the learner's level becomes known
(declared, picked on the level card, or graded by the diagnostic), the tutor
calls suggest_topics. The card lists subtopics (broad topic) or adjacent
topics (specific topic); a tap is just a learner message.

Gating lives on sessions.topic_suggest_state:
    None              the session started with a level (seeded, resumed, or
                      declared at create): never offered
    "awaiting_level"  the session started without one: due once the level is set
    "done"            already offered

The card itself is not stored separately: the ok suggest_topics call in the
assistant message's tool_calls_json is the persisted record, and
from_tool_calls() reads it back for the transcript.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from pydantic import ValidationError
from sqlalchemy.orm import Session

from contracts import SuggestTopicsArgs, ToolResult, TopicSuggestions

if TYPE_CHECKING:
    from agent.types import ToolContext

log = logging.getLogger(__name__)

TOOL_NAME = "suggest_topics"
AWAITING_LEVEL = "awaiting_level"
DONE = "done"

# Per-mode item counts from the #341 resolution. The contract only bounds the
# union (2..5); the mode-dependent range is enforced here.
_ITEM_RANGE = {"broad": (3, 5), "specific": (2, 4)}


def initial_state(knowledge_level: str | None) -> str | None:
    """The state a new session starts in, from its initial profile level."""
    return AWAITING_LEVEL if knowledge_level is None else None


def register(db: Session, ctx: "ToolContext", args: SuggestTopicsArgs) -> ToolResult:
    if args.session_id != ctx.session_id:
        return ToolResult(
            ok=False, status="failed",
            error=f"session_id mismatch: args={args.session_id} ctx={ctx.session_id}",
        )
    lo, hi = _ITEM_RANGE[args.mode]
    if not (lo <= len(args.items) <= hi):
        return ToolResult(
            ok=False, status="failed",
            error=f"{args.mode} mode takes {lo}-{hi} items, got {len(args.items)}",
        )

    from services import profile_service  # local import avoids circular

    # Serialize with concurrent turns so the card is offered at most once.
    row = profile_service.lock_session_row(db, ctx.session_id)
    if row.topic_suggest_state != AWAITING_LEVEL:
        db.commit()  # release the row lock
        return ToolResult(
            ok=False, status="failed",
            error="topic suggestions are not due in this session; do not call suggest_topics",
        )
    if profile_service.profile_from_row(row).knowledge_level is None:
        db.commit()  # release the row lock
        return ToolResult(
            ok=False, status="failed",
            error="the learner's level is not known yet; record it first",
        )
    row.topic_suggest_state = DONE
    db.commit()
    card = TopicSuggestions(mode=args.mode, topic=args.topic, items=args.items)
    return ToolResult(ok=True, status="ok", data=card.model_dump())


def from_tool_calls(tool_calls_json: str | None) -> TopicSuggestions | None:
    """The card an assistant message offered, read from its persisted tool
    calls; None when it made no successful suggest_topics call."""
    try:
        calls = json.loads(tool_calls_json or "[]")
    except (ValueError, TypeError):
        return None
    if not isinstance(calls, list):
        return None
    call = next(
        (
            c for c in calls
            if isinstance(c, dict) and c.get("name") == TOOL_NAME and c.get("status") == "ok"
        ),
        None,
    )
    if call is None:
        return None
    args = call.get("args") or {}
    try:
        return TopicSuggestions.model_validate({
            "mode": args.get("mode"),
            "topic": args.get("topic"),
            "items": args.get("items") or [],
        })
    except ValidationError:
        log.debug("unreadable suggest_topics args on a persisted message")
        return None
