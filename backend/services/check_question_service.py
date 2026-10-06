"""Pending check-question BATCH state machine.

A pending_check lives on the Session row as JSON:
    {
        "gap": str,
        "set_index": int,              # 1-based set within the check (#340)
        "set_total": int,              # sets in the check, fixed on set 1
        "current_index": int,          # first unresolved item, len(items) when done
        "asked_at_turn": iso8601,
        "items": [
            {"question": str, "options": [str], "correct_index": int,
             "explanation": str, "status": "pending"|"answered"|"skipped",
             "selected_index": int|None, "correct": bool|None},
            ...
        ],
    }

Anti-cheat: public_view() reveals correct_index / explanation / selected_index /
correct ONLY for items whose status != "pending". Pending items leak only
question + options.

Items resolve in any order (#348): answer()/skip() take any still-pending
index, and current_index tracks the first unresolved item.

A CHECK is 1..3 sets, one set (batch) per turn. The pending_check above is the
open set only; the check-level pointer that survives between sets lives in
pending_check_store (get/set_current_check). register() enforces the set
order against it, close_set() clears it after the final set, and
stop_open_check() / abandon_open_batch() clear it when the learner stops or
the session ends.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from contracts import AskCheckQuestionsArgs, ToolResult
from db.models import ChatMessage, LearningEvent
from db.models import Session as SessionModel

# Low-level pending_check state accessors live in a leaf module so
# learning_event_service can use them without importing this module (which
# would create a cyclic import). Only the ones this module calls internally
# are imported; callers wanting parse_asked_at / get_pending_check_from_row
# import them from services.pending_check_store directly.
from services import diagnostic_service
from services.pending_check_store import (
    _save,
    clear_pending_check,
    diagnostic_tally,
    get_current_check,
    get_pending_check,
    is_done,
    is_final_set,
    set_current_check,
)

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from agent.types import ToolContext


class CheckStateError(Exception):
    """Raised on an out-of-order or no-batch answer/skip."""


def public_view(pc: dict | None) -> dict | None:
    if not pc:
        return None
    items = []
    for it in pc.get("items", []):
        revealed = it.get("status") != "pending"
        items.append(
            {
                "question": it["question"],
                "options": it.get("options", []),
                "status": it.get("status", "pending"),
                "selected_index": it.get("selected_index") if revealed else None,
                "correct_index": it.get("correct_index") if revealed else None,
                "correct": it.get("correct") if revealed else None,
                "explanation": it.get("explanation") if revealed else None,
            }
        )
    return {
        "gap": pc["gap"],
        "current_index": pc.get("current_index", 0),
        "total": len(items),
        # None for batches registered before sets existed.
        "set_index": pc.get("set_index"),
        "set_total": pc.get("set_total"),
        "items": items,
    }


def attach_message_id(db: Session, session_id: str, message_id: int) -> None:
    """Stamp the asking assistant message id onto the open pending_check.

    No-op when there is no open batch (older flow / race). Read-time backfill
    covers messages whose batch was never linked."""
    from services import profile_service  # local import avoids circular

    # B-04: serialize with answer()/skip() (F-24 convention). Unlocked, this
    # whole-blob save could re-save pre-answer state over a concurrent grade.
    profile_service.lock_session_row(db, session_id)
    pc = get_pending_check(db, session_id)
    if pc is None:
        return
    pc["message_id"] = message_id
    _save(db, session_id, pc)


def write_check_batch(db: Session, pc: dict | None, commit: bool = True) -> None:
    """Persist public_view(pc) JSON onto the linked ChatMessage.

    No-op when pc is falsy, carries no message_id, or the message is gone.
    commit=False leaves the write pending for the caller's transaction (F-33)."""
    if not pc:
        return
    message_id = pc.get("message_id")
    if message_id is None:
        return
    msg = db.get(ChatMessage, message_id)
    if msg is None:
        log.debug("write_check_batch: message %s not found", message_id)
        return
    msg.check_batch_json = json.dumps(public_view(pc))
    if commit:
        db.commit()


_SUPPRESSED = "address the check results before quizzing again"


def _set_order_error(args: AskCheckQuestionsArgs, cc: dict | None) -> str | None:
    """Why a set_index > 1 call does not continue the current check, or None.

    Only a check whose last registered set is short of its set_total can be
    continued; close_set() drops the pointer once the final set closes."""
    if cc is None or cc.get("last_set_index", 0) >= cc.get("set_total", 0):
        return (
            f"set_index {args.set_index} has no check in progress to continue; "
            "start a new check with set_index=1"
        )
    if args.set_total != cc["set_total"]:
        return (
            f"set_total {args.set_total} does not match the current check's "
            f"set_total {cc['set_total']}"
        )
    expected = cc["last_set_index"] + 1
    if args.set_index != expected:
        return f"set_index {args.set_index} out of order: expected {expected}"
    return None


def register(db: Session, ctx: "ToolContext", args: AskCheckQuestionsArgs) -> ToolResult:
    # suppress_check marks the /check/complete follow-up turn. The only quiz
    # it may pose is the NEXT set of the current check (#340); that case is
    # validated against the pointer under the row lock below.
    suppressed = getattr(ctx, "suppress_check", False)
    if suppressed and args.set_index == 1:
        return ToolResult(ok=False, status="failed", error=_SUPPRESSED)
    if args.session_id != ctx.session_id:
        return ToolResult(
            ok=False, status="failed",
            error=f"session_id mismatch: args={args.session_id} ctx={ctx.session_id}",
        )
    if not (1 <= len(args.items) <= 5):
        return ToolResult(
            ok=False, status="failed",
            error=f"items count {len(args.items)} out of range 1..5",
        )
    for n, it in enumerate(args.items):
        if not (0 <= it.correct_index < len(it.options)):
            return ToolResult(
                ok=False, status="failed",
                error=(
                    f"item {n}: correct_index {it.correct_index} out of range "
                    f"for {len(it.options)} options"
                ),
            )
    if args.set_index > args.set_total:
        return ToolResult(
            ok=False, status="failed",
            error=f"set_index {args.set_index} exceeds set_total {args.set_total}",
        )

    from services import profile_service  # local import avoids circular

    # B-12: serialize the open-batch guard with answer()/skip() (F-24
    # convention); two concurrent streams otherwise both read None and the
    # second _save silently overwrites the first batch.
    profile_service.lock_session_row(db, ctx.session_id)

    if get_pending_check(db, ctx.session_id) is not None:
        return ToolResult(
            ok=False, status="failed",
            error="a check-question batch is already open; resolve it first",
        )

    if args.set_index == 1:
        # F-59: purpose is the turn's prepared decision, not a re-read of live
        # knowledge_level (which races with grading and misclassifies review
        # quizzes posed while level is None).
        purpose = "diagnostic" if ctx.diagnostic_required else "check"
        # Set 1 always starts a fresh check; any stale pointer is replaced.
        cc = {
            "set_total": args.set_total, "last_set_index": 1, "gaps": [args.gap],
            "purpose": purpose,
        }
    else:
        cc = get_current_check(db, ctx.session_id)
        err = _set_order_error(args, cc)
        if cc is None or err is not None:
            return ToolResult(ok=False, status="failed", error=err)
        # Later sets inherit set 1's purpose: a diagnostic stays a diagnostic
        # whatever the follow-up turn's own ctx says.
        purpose = cc.get("purpose", "check")
        cc = {**cc, "last_set_index": args.set_index, "gaps": [*cc.get("gaps", []), args.gap]}

    pc = {
        "gap": args.gap,
        "set_index": args.set_index,
        "set_total": args.set_total,
        "purpose": purpose,
        "current_index": 0,
        "asked_at_turn": ctx.turn_started_at.isoformat(),
        "message_id": None,
        "items": [
            {
                "question": it.question,
                "options": list(it.options),
                "correct_index": it.correct_index,
                "explanation": it.explanation,
                "status": "pending",
                "selected_index": None,
                "correct": None,
            }
            for it in args.items
        ],
    }
    set_current_check(db, ctx.session_id, cc, commit=False)
    _save(db, ctx.session_id, pc)
    return ToolResult(
        ok=True, status="ok",
        data={
            "gap": args.gap,
            "total": len(args.items),
            "set_index": args.set_index,
            "set_total": args.set_total,
            "items": [{"question": it.question, "options": list(it.options)} for it in args.items],
        },
    )


def _progress(pc: dict) -> dict:
    ci = pc["current_index"]
    total = len(pc["items"])
    done = ci >= total
    return {"current_index": ci, "total": total, "has_next": not done, "done": done}


def _pending_item(pc: dict, index: int) -> dict:
    """The still-pending item at `index`, else CheckStateError (#348: any
    pending item may be resolved, in any order)."""
    items = pc["items"]
    if not (0 <= index < len(items)):
        raise CheckStateError(f"index {index} out of range for {len(items)} items")
    if items[index].get("status", "pending") != "pending":
        raise CheckStateError(f"item {index} already resolved")
    return items[index]


def _advance(pc: dict) -> None:
    """Point current_index at the first unresolved item, or len(items) once
    every item is resolved (is_done keys off that)."""
    items = pc["items"]
    pc["current_index"] = next(
        (n for n, it in enumerate(items) if it.get("status", "pending") == "pending"),
        len(items),
    )


def answer(db: Session, session_id: str, index: int, selected_index: int) -> dict:
    """Grade pending item `index`, record the LearningEvent + profile effect,
    mark the item answered, move current_index to the first unresolved item,
    persist - all in ONE commit. Does NOT clear the batch."""
    from services import learning_event_service, profile_service  # local import avoids circular

    # F-24: serialize concurrent submits on the session row; the loser then
    # sees the item already resolved and raises CheckStateError -> 409.
    profile_service.lock_session_row(db, session_id)

    pc = get_pending_check(db, session_id)
    if pc is None:
        raise CheckStateError("no open check-question batch")
    item = _pending_item(pc, index)
    if not (0 <= selected_index < len(item["options"])):
        raise CheckStateError("selected_index out of range")

    correct = selected_index == item["correct_index"]
    batch_purpose = pc.get("purpose", "check")
    apply_effects = batch_purpose != "diagnostic"
    # Profile effect + LearningEvent, deferred into our single commit; does not clear.
    learning_event_service.record_from_answer(
        db, session_id, gap=pc["gap"], question=item["question"],
        correct=correct, clear_pending=False, commit=False,
        apply_profile_effects=apply_effects,
        selected_index=selected_index, correct_index=item["correct_index"],
        options=item["options"], purpose=batch_purpose,
    )
    item["status"] = "answered"
    item["selected_index"] = selected_index
    item["correct"] = correct
    _advance(pc)
    _save(db, session_id, pc, commit=False)
    db.commit()

    prog = _progress(pc)
    return {
        "correct": correct,
        "explanation": item["explanation"],
        "correct_index": item["correct_index"],
        **prog,
    }


def skip(db: Session, session_id: str, index: int) -> dict:
    from services import profile_service  # local import avoids circular

    # F-24: serialize concurrent submits on the session row; the loser then
    # sees the item already resolved and raises CheckStateError -> 409.
    profile_service.lock_session_row(db, session_id)

    pc = get_pending_check(db, session_id)
    if pc is None:
        raise CheckStateError("no open check-question batch")
    item = _pending_item(pc, index)
    item["status"] = "skipped"
    _advance(pc)
    _save(db, session_id, pc)
    return _progress(pc)


def abandon_open_batch(db: Session, session_id: str, commit: bool = True) -> bool:
    """Clear any lingering pending check batch: mark still-pending items
    "skipped", freeze the batch onto its message for honest history, and clear
    the pending pointer. Logs no learning events and applies no mastery
    effects; the one profile write is grading an in-progress diagnostic
    check from its answered items, so a learner who ends the session between
    diagnostic sets keeps the level they earned. Returns True when a batch
    was cleared.

    Called on session end so a later review-gaps resume can pose a fresh check
    instead of hitting the "a batch is already open" guard. That guard blocks on
    ANY non-null pending_check, so a fully-answered-but-uncleared batch blocks
    just as a half-answered one does -- both must be cleared here, hence no
    is_done() short-circuit.

    Also drops the current-check pointer (#340), so a set-2+ call cannot
    continue a check from an ended session.

    commit=False defers all writes to the caller's single commit (F-33).
    """
    pc = get_pending_check(db, session_id)
    if pc is not None:
        _skip_remaining(pc)
        _save(db, session_id, pc, commit=False)
    diagnostic_service.grade_if_diagnostic(db, session_id, force=True, commit=False)
    set_current_check(db, session_id, None, commit=commit)
    if pc is None:
        return False
    write_check_batch(db, pc, commit=commit)
    clear_pending_check(db, session_id, commit=commit)
    return True


def _skip_remaining(pc: dict) -> None:
    for item in pc.get("items", []):
        if item.get("status") == "pending":
            item["status"] = "skipped"
    pc["current_index"] = len(pc.get("items", []))


def close_set(db: Session, session_id: str, pc: dict) -> dict | None:
    """Close a resolved set in one commit: freeze it onto its asking message,
    clear the pending batch, record the quiz cooldown, and drop the
    current-check pointer once the final set has closed. Returns the cooldown.
    A non-final diagnostic set's score is folded into the pointer so the level
    can be graded over the whole check.

    Callers hold the session row lock and have already graded a diagnostic
    (diagnostic_service.grade_if_diagnostic reads the still-pending batch)."""
    cooldown = build_quiz_cooldown(pc)
    write_check_batch(db, pc, commit=False)
    clear_pending_check(db, session_id, commit=False)
    set_quiz_cooldown(db, session_id, cooldown, commit=False)
    if is_final_set(pc):
        set_current_check(db, session_id, None, commit=False)
    else:
        cc = get_current_check(db, session_id)
        if cc is not None and cc.get("purpose") == "diagnostic":
            cc["diag"] = diagnostic_tally(pc, cc.get("diag"))
            set_current_check(db, session_id, cc, commit=False)
    db.commit()
    return cooldown


def stop_open_check(db: Session, session_id: str) -> str | None:
    """The learner ended the check early with the Stop button (#340 "early
    stop = skip"; POST /check/stop). Chat messages never stop a check. Grade the open set's remaining items as skipped, with
    Skip-button semantics (results summary, cooldown), close it, and end the
    check. Returns the [check results] text for the follow-up turn, or None
    when no check is in progress or the open set is fully answered (that set
    is /check/complete's to close).

    Between sets (no open batch, pointer still short of set_total) there is
    nothing to grade; the summary only records where the learner stopped so
    the untested gaps are not mistaken for tested ones. Either way a
    diagnostic check is graded from whatever was answered."""
    from services import profile_service  # local import avoids circular

    profile_service.lock_session_row(db, session_id)
    pc = get_pending_check(db, session_id)
    if pc is None:
        cc = get_current_check(db, session_id)
        if cc is None:
            db.commit()  # release the row lock
            return None
        diagnostic_service.grade_if_diagnostic(db, session_id, force=True, commit=False)
        set_current_check(db, session_id, None)
        return (
            f"[check results] learner stopped at set {cc['last_set_index']} "
            f"of {cc['set_total']}."
        )

    if is_done(pc):
        # Every item is answered and /check/complete owns closing the set;
        # closing it here would 409 the frontend's complete call.
        db.commit()  # release the row lock
        return None
    _skip_remaining(pc)
    _save(db, session_id, pc, commit=False)
    summary = build_results_summary(pc, stopped=True)
    diagnostic_service.grade_if_diagnostic(db, session_id, force=True, commit=False)
    # A stop ends the check even when this set was not the final one;
    # close_set only drops the pointer after the final set.
    set_current_check(db, session_id, None, commit=False)
    close_set(db, session_id, pc)
    return summary


def build_results_summary(pc: dict, stopped: bool = False) -> str:
    """Server-built summary injected as a synthetic user turn for the follow-up.
    Reflects post-answer profile state (demotions already applied per-answer).

    The header names the set ("Set N of M.") or, when the learner stopped the
    check, "learner stopped at set N of M." Pre-#340 batches get neither."""
    items = pc.get("items", [])
    graded = [it for it in items if it["status"] == "answered"]
    n_correct = sum(1 for it in graded if it.get("correct"))
    header = f"[check results] gap={pc['gap']}: {n_correct}/{len(graded)} correct."
    set_index, set_total = pc.get("set_index"), pc.get("set_total")
    if set_index and set_total:
        if stopped:
            header += f" learner stopped at set {set_index} of {set_total}."
        else:
            header += f" Set {set_index} of {set_total}."
    lines = [header]
    for n, it in enumerate(items):
        if it["status"] == "skipped":
            lines.append(f"  Q{n + 1} skipped.")
        elif it["status"] == "answered" and not it.get("correct"):
            chose = it["options"][it["selected_index"]]
            right = it["options"][it["correct_index"]]
            lines.append(f'  Q{n + 1} missed: learner chose "{chose}", correct "{right}".')
    return "\n".join(lines)


def build_quiz_cooldown(pc: dict) -> dict | None:
    """Derive a quiz_cooldown record from a resolved batch.

    Returns None when every item was answered correctly (no miss, no skip) -
    an all-correct batch means the gap is mastered and the loop should end.
    `last_score` is n_correct over GRADED (answered) items, matching
    build_results_summary; skipped items count toward triggering the cooldown
    but not toward the score."""
    items = pc.get("items", [])
    graded = [it for it in items if it["status"] == "answered"]
    n_correct = sum(1 for it in graded if it.get("correct"))
    has_miss = any(it["status"] == "skipped" for it in items) or n_correct < len(graded)
    if not has_miss:
        return None
    missed = [
        {
            "question": it["question"],
            "chosen": it["options"][it["selected_index"]],
            "correct": it["options"][it["correct_index"]],
        }
        for it in graded
        if not it.get("correct")
    ]
    return {
        "gap": pc["gap"],
        "last_score": f"{n_correct}/{len(graded)}",
        "missed": missed,
    }


def get_quiz_cooldown_from_row(row: SessionModel | None) -> dict | None:
    if row is None or not row.quiz_cooldown_json:
        return None
    try:
        data = json.loads(row.quiz_cooldown_json)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def get_quiz_cooldown(db: Session, session_id: str) -> dict | None:
    return get_quiz_cooldown_from_row(db.get(SessionModel, session_id))


def set_quiz_cooldown(db: Session, session_id: str, cd: dict | None, commit: bool = True) -> None:
    row = db.get(SessionModel, session_id)
    if row is None:
        raise ValueError(f"session not found: {session_id}")
    row.quiz_cooldown_json = json.dumps(cd) if cd is not None else None
    if commit:
        db.commit()


def load_session_learning_events(db: Session, session_id: str) -> list[LearningEvent]:
    """All LearningEvents for a session, oldest first. Loaded once per detail
    render so reconstruct_check_batch can match in memory instead of issuing one
    SELECT per check item (the former N+1)."""
    return db.execute(
        select(LearningEvent)
        .where(LearningEvent.session_id == session_id)
        .order_by(LearningEvent.created_at.asc(), LearningEvent.id.asc())
    ).scalars().all()


def reconstruct_check_batch(db: Session, msg: ChatMessage, events: list | None = None) -> dict | None:
    """Best-effort recap for an asking message with no persisted check_batch_json.

    Matches each item against the session's LearningEvents by
    (gap_tested, question) for the FIRST event at or after this message's turn.
    `events` may be preloaded (load_session_learning_events) to avoid N+1; when
    None it is loaded once here (single query, not per item).

    Pulls question/options/correct_index/explanation from the message's
    ask_check_questions tool call. selected_index comes from the matched
    LearningEvent (U-03); None for pre-0013 events that never stored it.
    status = answered if an event matched, else skipped.

    Known tradeoff: if the same (gap, question) recurs in a LATER batch that
    was answered before this backfill runs, this message's item may be
    mis-marked "answered". Accepted as best-effort only."""
    try:
        tcs = json.loads(msg.tool_calls_json or "[]")
    except (ValueError, TypeError):
        return None
    ask = next((t for t in tcs if t.get("name") == "ask_check_questions"), None)
    if ask is None:
        return None
    args = ask.get("args") or {}
    gap = args.get("gap", "")
    raw_items = args.get("items", [])
    if not raw_items:
        return None

    if events is None:
        events = load_session_learning_events(db, msg.session_id)

    items = []
    for it in raw_items:
        question = it.get("question", "")
        # events are oldest-first; first match is the earliest at/after this turn.
        ev = next(
            (e for e in events
             if e.gap_tested == gap
             and e.question == question
             and e.created_at >= msg.created_at),
            None,
        )
        if ev is not None:
            status, correct = "answered", ev.correct
            selected = ev.selected_index
        else:
            status, correct = "skipped", None
            selected = None
        items.append({
            "question": question,
            "options": it.get("options", []),
            "status": status,
            "selected_index": selected,
            "correct_index": it.get("correct_index"),
            "correct": correct,
            "explanation": it.get("explanation"),
        })

    return {
        "gap": gap,
        "current_index": len(items),
        "total": len(items),
        "set_index": args.get("set_index"),
        "set_total": args.get("set_total"),
        "items": items,
    }


def load_check_batch(db: Session, msg: ChatMessage, events: list | None = None) -> dict | None:
    """Recap payload for a message: persisted column first, else reconstruct.

    `events` is an optional preloaded list of this session's LearningEvents
    (see load_session_learning_events) so callers rendering many messages avoid
    one SELECT per item.
    """
    if msg.check_batch_json:
        try:
            data = json.loads(msg.check_batch_json)
        except (ValueError, TypeError):
            data = None
        if isinstance(data, dict):
            return data
    return reconstruct_check_batch(db, msg, events)
