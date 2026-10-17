"""The Check: its Sets, their grading, and their commit (#420).

Vocabulary (Check, Set, Item, Close, Recap, Diagnostic): GLOSSARY.md.

A CHECK is 1..3 Sets, one Set per turn. Three Session columns are private to
this module, as is ChatMessage.check_batch_json (the frozen Recap):

- pending_check_json: the open Set.
    {
        "gap": str,
        "set_index": int,              # 1-based Set within the Check (#340)
        "set_total": int,              # Sets in the Check, fixed on Set 1
        "purpose": "check"|"diagnostic",
        "current_index": int,          # first unresolved Item, len(items) when done
        "asked_at_turn": iso8601,
        "message_id": int|None,        # the asking assistant message
        "items": [
            {"question": str, "options": [str], "correct_index": int,
             "explanation": str, "status": "pending"|"answered"|"skipped",
             "selected_index": int|None, "correct": bool|None},
            ...
        ],
    }
- current_check_json: the Check pointer, which survives between Sets.
    {"set_total": int, "last_set_index": int, "gaps": [str],
     "purpose": "check"|"diagnostic", "diag": tally}
  last_set_index is the most recently REGISTERED Set. purpose is fixed on
  Set 1 and inherited by later Sets. diag (Diagnostics only) is the running
  score of the closed Sets; the level is graded once over all Sets.
- quiz_cooldown_json: the last closed Set's misses, for the prompt.

Transactions. Every action that gets past argument validation takes the
session row lock and commits itself,
releasing the lock on every return path, early exits included. A conflict
commits, then raises CheckError. Nothing here releases by rollback. Only an
unexpected exception leaves the transaction to the caller; for register, the
tool dispatcher rolls it back (#569). The one exception to committing itself
is abandon_in_caller_transaction, which joins the
session end's single write window (F-33) and never commits.

Every Close grades. Complete, Stop and abandon all Close through _close,
which grades a Diagnostic before the Set is cleared. Grading is idempotent:
it never overwrites a set knowledge_level.

Anti-cheat: the public view reveals correct_index / explanation /
selected_index / correct ONLY for resolved Items.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from contracts import AskCheckQuestionsArgs, ToolResult
from db.models import ChatMessage, LearningEvent
from db.models import Session as SessionModel
from lib.error_codes import CHECK_CONFLICT, NO_OPEN_CHECK, NO_RESOLVED_BATCH, SESSION_ENDED
from services import learning_event_service, profile_service

if TYPE_CHECKING:
    from agent.types import ToolContext

log = logging.getLogger(__name__)


class CheckError(Exception):
    """A Check action refused. `code` is an error_codes constant; `message`
    is set only for check_conflict (routes put it in the 409 detail)."""

    def __init__(self, code: str, message: str | None = None):
        super().__init__(message or code)
        self.code = code
        self.message = message


def _conflict(message: str) -> CheckError:
    return CheckError(CHECK_CONFLICT, message)


@contextmanager
def _locked(db: Session, session_id: str) -> Generator[SessionModel]:
    """Hold the session row lock for one action and commit on the way out,
    on a normal return and on a CheckError alike. Any other exception
    propagates with the transaction left to the caller."""
    row = profile_service.lock_session_row(db, session_id)
    try:
        yield row
    except CheckError:
        db.commit()
        raise
    db.commit()


# --- Row reads ---------------------------------------------------------------


def _json_dict(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def open_set(row: SessionModel | None) -> dict | None:
    """The open Set, answers included (the prompt reads it)."""
    return _json_dict(getattr(row, "pending_check_json", None))


def current_check(row: SessionModel | None) -> dict | None:
    """The Check pointer: lets the prompt tell "between Sets" from "no Check"."""
    return _json_dict(getattr(row, "current_check_json", None))


def quiz_cooldown(row: SessionModel | None) -> dict | None:
    return _json_dict(getattr(row, "quiz_cooldown_json", None))


def open_set_view(row: SessionModel) -> tuple[dict | None, int | None]:
    """The open Set's public view and its asking message id (None until
    stamp_message_id runs), from one read of the row."""
    pc = open_set(row)
    return _public_view(pc), (pc.get("message_id") if pc else None)


def _public_view(pc: dict | None) -> dict | None:
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
        # None for Sets registered before Sets existed.
        "set_index": pc.get("set_index"),
        "set_total": pc.get("set_total"),
        "items": items,
    }


# --- Recap -------------------------------------------------------------------


def load_session_learning_events(db: Session, session_id: str) -> list[LearningEvent]:
    """All LearningEvents for a session, oldest first. Loaded once per detail
    render so recap_for_message can match in memory instead of issuing one
    SELECT per Item."""
    return list(
        db.execute(
            select(LearningEvent)
            .where(LearningEvent.session_id == session_id)
            .order_by(LearningEvent.created_at.asc(), LearningEvent.id.asc())
        )
        .scalars()
        .all()
    )


def recap_is_frozen(msg: ChatMessage) -> bool:
    """False when recap_for_message would rebuild from LearningEvents, so a
    caller rendering many messages knows whether to preload them."""
    return _json_dict(msg.check_batch_json) is not None


def recap_for_message(db: Session, msg: ChatMessage, events: list | None = None) -> dict | None:
    """Recap payload for a message: the frozen column first, else rebuilt.

    `events` is an optional preloaded list of this session's LearningEvents
    (see load_session_learning_events) so callers rendering many messages
    avoid one SELECT per Item."""
    data = _json_dict(msg.check_batch_json)
    if data is not None:
        return data
    return _rebuild_recap(db, msg, events)


def _rebuild_recap(db: Session, msg: ChatMessage, events: list | None = None) -> dict | None:
    """Best-effort Recap for an asking message with no frozen Recap.

    Matches each Item against the session's LearningEvents by
    (gap_tested, question) for the FIRST event at or after this message's turn.
    Pulls question/options/correct_index/explanation from the message's
    ask_check_questions tool call. selected_index comes from the matched
    LearningEvent (U-03); None for pre-0013 events that never stored it.
    status = answered if an event matched, else skipped.

    Known tradeoff: if the same (gap, question) recurs in a LATER Set that
    was answered before this backfill runs, this message's Item may be
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
            (
                e
                for e in events
                if e.gap_tested == gap and e.question == question and e.created_at >= msg.created_at
            ),
            None,
        )
        if ev is not None:
            status, correct = "answered", ev.correct
            selected = ev.selected_index
        else:
            status, correct = "skipped", None
            selected = None
        items.append(
            {
                "question": question,
                "options": it.get("options", []),
                "status": status,
                "selected_index": selected,
                "correct_index": it.get("correct_index"),
                "correct": correct,
                "explanation": it.get("explanation"),
            }
        )

    return {
        "gap": gap,
        "current_index": len(items),
        "total": len(items),
        "set_index": args.get("set_index"),
        "set_total": args.get("set_total"),
        "items": items,
    }


# --- Row writes (callers hold the lock) --------------------------------------


def _write_open_set(row: SessionModel, pc: dict | None) -> None:
    row.pending_check_json = json.dumps(pc) if pc is not None else None


def _write_current_check(row: SessionModel, cc: dict | None) -> None:
    row.current_check_json = json.dumps(cc) if cc is not None else None


def _write_cooldown(row: SessionModel, cooldown: dict | None) -> None:
    row.quiz_cooldown_json = json.dumps(cooldown) if cooldown is not None else None


def _freeze_recap(db: Session, pc: dict) -> None:
    """Freeze the Set's public view onto its asking message. No-op when the
    Set was never stamped or the message is gone (read-time rebuild covers)."""
    message_id = pc.get("message_id")
    if message_id is None:
        return
    msg = db.get(ChatMessage, message_id)
    if msg is None:
        log.debug("freeze recap: message %s not found", message_id)
        return
    msg.check_batch_json = json.dumps(_public_view(pc))


# --- Set state helpers -------------------------------------------------------


def _is_done(pc: dict) -> bool:
    return pc.get("current_index", 0) >= len(pc.get("items", []))


def _is_final_set(pc: dict) -> bool:
    """Pre-#340 Sets carry no set fields and count as a 1-Set Check."""
    return pc.get("set_index", 1) >= pc.get("set_total", 1)


def _progress(pc: dict) -> dict:
    ci = pc["current_index"]
    total = len(pc["items"])
    done = ci >= total
    return {"current_index": ci, "total": total, "has_next": not done, "done": done}


def _pending_item(pc: dict, index: int) -> dict:
    """The still-pending Item at `index` (#348: any order), else a conflict."""
    items = pc["items"]
    if not (0 <= index < len(items)):
        raise _conflict(f"index {index} out of range for {len(items)} items")
    if items[index].get("status", "pending") != "pending":
        raise _conflict(f"item {index} already resolved")
    return items[index]


def _advance(pc: dict) -> None:
    """Point current_index at the first unresolved Item, or len(items) once
    every Item is resolved (_is_done keys off that)."""
    items = pc["items"]
    pc["current_index"] = next(
        (n for n, it in enumerate(items) if it.get("status", "pending") == "pending"),
        len(items),
    )


def _skip_remaining(pc: dict) -> None:
    for item in pc.get("items", []):
        if item.get("status") == "pending":
            item["status"] = "skipped"
    pc["current_index"] = len(pc.get("items", []))


def _require_live(row: SessionModel) -> None:
    """Recheck ended_at under the lock. A learner action queued behind a
    session end's claim must not write to it: the end's abandon runs only
    after its summary call, so the Set can still be open here."""
    if row.ended_at is not None:
        raise CheckError(SESSION_ENDED)


def _open_set_for_click(row: SessionModel) -> dict:
    """The open Set an answer or skip resolves."""
    _require_live(row)
    pc = open_set(row)
    if pc is None:
        raise _conflict("no open check-question batch")
    return pc


# --- Diagnostic grading ------------------------------------------------------


def _diagnostic_tally(pc: dict, prior: dict | None = None) -> dict:
    """Score of one Set added onto a prior tally. `items` counts every Item
    posed (skips included, matching _level_for_score's denominator);
    `answered` counts graded ones."""
    items = pc.get("items", [])
    prior = prior or {}
    return {
        "correct": prior.get("correct", 0)
        + sum(1 for it in items if it.get("status") == "answered" and it.get("correct")),
        "answered": prior.get("answered", 0)
        + sum(1 for it in items if it.get("status") == "answered"),
        "items": prior.get("items", 0) + len(items),
    }


def _level_for_score(n_correct: int, total: int) -> Literal["beginner", "intermediate", "advanced"]:
    """Map a Diagnostic score to a coarse knowledge level.

    Tuned for a 3-question Set: 0-1 beginner, 2 intermediate, 3 advanced.
    Generalizes by ratio for other totals (a multi-Set Diagnostic grades over
    all its Items)."""
    if total <= 0:
        return "beginner"
    ratio = n_correct / total
    if ratio >= 1.0:
        return "advanced"
    if ratio >= (2 / 3):
        return "intermediate"
    return "beginner"


def _grade_diagnostic(db: Session, row: SessionModel, pc: dict | None, *, force: bool) -> None:
    """Grade a Diagnostic into topic_profile.knowledge_level, once over every
    Item of every Set: the closed Sets' tally on the Check pointer plus the
    open Set `pc`. Normally only when the open Set is the final one and
    resolved; force=True (Stop, session end) grades whatever was answered,
    with or without an open Set.

    Reads the Check pointer's tally, so it runs before a Close folds or drops
    the pointer. The caller holds the row lock. Never overwrites a set level
    (F-39: a user PATCH mid-Check wins), which also makes re-grading a no-op."""
    cc = current_check(row)
    prior = cc.get("diag") if cc and cc.get("purpose") == "diagnostic" else None
    if pc is not None:
        if pc.get("purpose") != "diagnostic" or not _is_done(pc):
            return
        if not (force or _is_final_set(pc)):
            return
        tally = _diagnostic_tally(pc, prior)
    elif force and prior is not None:
        tally = prior
    else:
        return
    if not tally["answered"]:
        # F-25: an all-skip Check is zero evidence. Leave knowledge_level None
        # so diagnostic_required fires again next turn instead of branding the
        # learner "beginner" forever.
        return
    profile = profile_service.profile_from_row(row)
    if profile.knowledge_level is not None:
        return
    profile.knowledge_level = _level_for_score(tally["correct"], tally["items"])
    profile_service.save_profile(db, row.id, profile, commit=False)


# --- Close -------------------------------------------------------------------


def _close(db: Session, row: SessionModel, pc: dict | None, *, ends_check: bool) -> None:
    """The one Close path (Complete, Stop, abandon). Grades a Diagnostic,
    freezes the Recap and clears the open Set, then either drops the Check
    pointer or, for a non-final Diagnostic Set, folds the Set's score into it.

    ends_check (Stop, abandon) forces grading and drops the pointer even
    mid-Check. Complete ends the Check only after its final Set. The quiz
    cooldown is the caller's: abandon writes none."""
    _grade_diagnostic(db, row, pc, force=ends_check)
    if pc is not None:
        _freeze_recap(db, pc)
        _write_open_set(row, None)
    if ends_check or pc is None or _is_final_set(pc):
        _write_current_check(row, None)
        return
    cc = current_check(row)
    if cc is not None and cc.get("purpose") == "diagnostic":
        cc["diag"] = _diagnostic_tally(pc, cc.get("diag"))
        _write_current_check(row, cc)


def _score(pc: dict) -> tuple[list[dict], int]:
    """The answered Items and how many were correct. Skips do not score."""
    graded = [it for it in pc.get("items", []) if it["status"] == "answered"]
    return graded, sum(1 for it in graded if it.get("correct"))


def _results_summary(pc: dict, *, stopped: bool = False) -> str:
    """Server-built summary injected as a synthetic user turn for the
    follow-up. Reflects post-answer profile state (demotions already applied
    per answer).

    The header names the Set ("Set N of M.") or, when the learner stopped
    the Check, "learner stopped at set N of M." Pre-#340 Sets get neither."""
    items = pc.get("items", [])
    graded, n_correct = _score(pc)
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


def _build_cooldown(pc: dict) -> dict | None:
    """A quiz_cooldown record from a resolved Set.

    None when every Item was answered correctly (no miss, no skip): an
    all-correct Set means the gap is mastered and the loop should end.
    `last_score` is n_correct over GRADED (answered) Items, matching
    _results_summary; skipped Items trigger the cooldown but do not score."""
    items = pc.get("items", [])
    graded, n_correct = _score(pc)
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


def _close_with_cooldown(db: Session, row: SessionModel, pc: dict, *, ends_check: bool):
    cooldown = _build_cooldown(pc)
    _close(db, row, pc, ends_check=ends_check)
    _write_cooldown(row, cooldown)
    return cooldown


# --- Actions -----------------------------------------------------------------

_SUPPRESSED = "address the check results before quizzing again"


def _set_order_error(args: AskCheckQuestionsArgs, cc: dict | None) -> str | None:
    """Why a set_index > 1 call does not continue the current Check, or None.

    Only a Check whose last registered Set is short of its set_total can be
    continued; the pointer is dropped once the Check ends."""
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


def _refuse(error: str | None) -> ToolResult:
    return ToolResult(ok=False, status="failed", error=error)


def _args_error(ctx: "ToolContext", args: AskCheckQuestionsArgs) -> str | None:
    """Why the tool call is malformed, checked before taking the lock."""
    if args.session_id != ctx.session_id:
        return f"session_id mismatch: args={args.session_id} ctx={ctx.session_id}"
    if not (1 <= len(args.items) <= 5):
        return f"items count {len(args.items)} out of range 1..5"
    for n, it in enumerate(args.items):
        if not (0 <= it.correct_index < len(it.options)):
            return (
                f"item {n}: correct_index {it.correct_index} out of range "
                f"for {len(it.options)} options"
            )
    if args.set_index > args.set_total:
        return f"set_index {args.set_index} exceeds set_total {args.set_total}"
    return None


def register(db: Session, ctx: "ToolContext", args: AskCheckQuestionsArgs) -> ToolResult:
    """The ask_check_questions tool handler: open a Set."""
    # suppress_check marks the /check/complete follow-up turn. The only quiz
    # it may pose is the NEXT Set of the current Check (#340); that case is
    # validated against the pointer under the row lock below.
    if getattr(ctx, "suppress_check", False) and args.set_index == 1:
        return _refuse(_SUPPRESSED)
    err = _args_error(ctx, args)
    if err is not None:
        return _refuse(err)

    # B-12: serialize the open-Set guard with answer()/skip() (F-24); two
    # concurrent streams otherwise both read None and the second write
    # silently overwrites the first Set.
    with _locked(db, ctx.session_id) as row:
        # A turn still streaming when the session ended must not open a Set
        # the end's abandon has already passed over.
        if row.ended_at is not None:
            return _refuse("the session has ended; do not quiz")
        if open_set(row) is not None:
            return _refuse("a check-question batch is already open; resolve it first")

        if args.set_index == 1:
            # F-59: purpose is the turn's prepared decision, not a re-read of
            # live knowledge_level (which races with grading and misclassifies
            # review quizzes posed while level is None).
            purpose = "diagnostic" if ctx.diagnostic_required else "check"
            # Set 1 always starts a fresh Check; any stale pointer is replaced.
            cc = {
                "set_total": args.set_total,
                "last_set_index": 1,
                "gaps": [args.gap],
                "purpose": purpose,
            }
        else:
            cc = current_check(row)
            err = _set_order_error(args, cc)
            if cc is None or err is not None:
                return _refuse(err)
            # Later Sets inherit Set 1's purpose: a Diagnostic stays a
            # Diagnostic whatever the follow-up turn's own ctx says.
            purpose = cc.get("purpose", "check")
            cc = {**cc, "last_set_index": args.set_index, "gaps": [*cc.get("gaps", []), args.gap]}

        _write_current_check(row, cc)
        _write_open_set(
            row,
            {
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
            },
        )
    return ToolResult(
        ok=True,
        status="ok",
        data={
            "gap": args.gap,
            "total": len(args.items),
            "set_index": args.set_index,
            "set_total": args.set_total,
            "items": [{"question": it.question, "options": list(it.options)} for it in args.items],
        },
    )


def stamp_message_id(db: Session, session_id: str, message_id: int) -> None:
    """Stamp the asking assistant message id onto the open Set. No-op when
    no Set is open (read-time rebuild covers an unlinked message)."""
    # B-04: serialize with answer()/skip(); unlocked, this whole-blob write
    # could re-save pre-answer state over a concurrent grade.
    with _locked(db, session_id) as row:
        pc = open_set(row)
        if pc is None:
            return
        pc["message_id"] = message_id
        _write_open_set(row, pc)


def answer(db: Session, session_id: str, index: int, selected_index: int) -> dict:
    """Grade pending Item `index`, record its LearningEvent and profile
    effect, and grade a Diagnostic whose final Set this resolves, in one
    commit. Does not Close the Set (#419)."""
    # F-24: serialize concurrent submits; the loser sees the Item resolved.
    with _locked(db, session_id) as row:
        pc = _open_set_for_click(row)
        item = _pending_item(pc, index)
        if not (0 <= selected_index < len(item["options"])):
            raise _conflict("selected_index out of range")

        correct = selected_index == item["correct_index"]
        purpose = pc.get("purpose", "check")
        learning_event_service.record_from_answer(
            db,
            session_id,
            gap=pc["gap"],
            question=item["question"],
            correct=correct,
            apply_profile_effects=purpose != "diagnostic",
            selected_index=selected_index,
            correct_index=item["correct_index"],
            options=item["options"],
            purpose=purpose,
        )
        item["status"] = "answered"
        item["selected_index"] = selected_index
        item["correct"] = correct
        _advance(pc)
        _write_open_set(row, pc)
        _grade_diagnostic(db, row, pc, force=False)

    return {
        "correct": correct,
        "explanation": item["explanation"],
        "correct_index": item["correct_index"],
        **_progress(pc),
    }


def skip(db: Session, session_id: str, index: int) -> dict:
    """Mark pending Item `index` skipped and grade a Diagnostic whose final
    Set this resolves, in one commit. No LearningEvent; no Close (#419)."""
    with _locked(db, session_id) as row:
        pc = _open_set_for_click(row)
        _pending_item(pc, index)["status"] = "skipped"
        _advance(pc)
        _write_open_set(row, pc)
        _grade_diagnostic(db, row, pc, force=False)
    return _progress(pc)


def complete(db: Session, session_id: str) -> tuple[str, dict | None]:
    """Close the resolved open Set (POST /check/complete). Returns the
    results summary for the follow-up turn and the quiz cooldown. Between
    Sets the Check pointer survives, so the follow-up turn may pose the next
    Set. B-02: a concurrent second call re-reads no resolved Set after this
    commit and gets no_resolved_batch."""
    with _locked(db, session_id) as row:
        _require_live(row)
        pc = open_set(row)
        if pc is None or not _is_done(pc):
            raise CheckError(NO_RESOLVED_BATCH)
        summary = _results_summary(pc)
        cooldown = _close_with_cooldown(db, row, pc, ends_check=False)
    return summary, cooldown


def stop(db: Session, session_id: str) -> tuple[str, dict | None]:
    """The learner ended the Check with the Stop button (#340 "early stop =
    skip"). The open Set's remaining Items are skipped and the Set Closes
    with Skip-button semantics; the Check ends even mid-Check. Returns the
    results summary for the follow-up turn and the quiz cooldown.

    Between Sets there is nothing to grade per Item; the summary records
    where the learner stopped so untested gaps are not mistaken for tested
    ones. Raises no_open_check when no Check is in progress, or when the
    open Set is fully answered (that Set is complete()'s to Close)."""
    with _locked(db, session_id) as row:
        _require_live(row)
        pc = open_set(row)
        if pc is None:
            cc = current_check(row)
            if cc is None:
                raise CheckError(NO_OPEN_CHECK)
            _close(db, row, None, ends_check=True)
            summary = (
                f"[check results] learner stopped at set {cc['last_set_index']} of "
                f"{cc['set_total']}."
            )
            return summary, quiz_cooldown(row)
        if _is_done(pc):
            raise CheckError(NO_OPEN_CHECK)
        _skip_remaining(pc)
        summary = _results_summary(pc, stopped=True)
        cooldown = _close_with_cooldown(db, row, pc, ends_check=True)
    return summary, cooldown


def abandon_in_caller_transaction(db: Session, session_id: str) -> bool:
    """Close any open Set at session end. JOINS THE CALLER'S TRANSACTION and
    never commits: the session end persists it in its single write window
    (F-33, summary_service.generate_and_persist).

    Still-pending Items become skipped and the Recap freezes for honest
    history. No LearningEvents and no mastery effects; a Diagnostic is
    graded from its answered Items, so a learner who ends between Sets keeps
    the level they earned. The Check pointer drops, so a later Set 2+ cannot
    continue a Check from an ended session. No quiz cooldown is written.

    Any non-null open Set blocks register's "already open" guard, so a fully
    answered but unclosed Set is cleared here too. Returns True when a Set
    was cleared."""
    row = profile_service.lock_session_row(db, session_id)
    pc = open_set(row)
    if pc is not None:
        _skip_remaining(pc)
    _close(db, row, pc, ends_check=True)
    return pc is not None
