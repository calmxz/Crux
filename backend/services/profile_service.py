"""Profile patch service. Spec §3.4 v1 simplified rules.

Scope: the per-session topic profile only. The cross-session rollup behind
/api/profile/aggregate lives in `services/profile_insights.py` (G-14), which
imports from here. This module must never import that one.

Rules:
- Declared / tested mastery -> directly to mastered_concepts.
- Inferred mastery -> ignored (no-op, ok=True).
- Duplicate gap or concept additions -> no-op.
- knowledge_level overwrites.
- focus_target_gap clearing requires focus_clear_reason; omitting the focus
  field without a reason leaves focus unchanged (F-23). Reason
  "tested_correct" is server-verified against a correct LearningEvent for the
  focused gap in this session (F-02).
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Literal

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent.types import ToolContext
from config import settings
from contracts import (
    ConceptEntry,
    ToolResult,
    TopicProfile,
    UpdateTopicProfileArgs,
)
from db.models import LearningEvent
from db.models import Session as SessionModel

log = logging.getLogger(__name__)

MAX_SUBTOPICS = 20


def canon(name: str) -> str:
    return name.strip().casefold()


def _has_correct_event_for(db: Session, session_id: str, gap: str) -> bool:
    """F-02 guard (decision Q1): session-scoped proof that a correct
    check-question answer was recorded for this gap. canon-compared in Python
    because gap_tested is stored raw."""
    key = canon(gap)
    rows = db.execute(
        select(LearningEvent.gap_tested)
        .where(
            LearningEvent.session_id == session_id,
            LearningEvent.correct.is_(True),
        )
    ).scalars().all()
    return any(canon(g) == key for g in rows)


def concept_names(entries: list | None) -> list[str]:
    return [e.name for e in (entries or [])]


def find_entry(entries: list, name: str):
    key = canon(name)
    for e in entries or []:
        if canon(e.name) == key:
            return e
    return None


def upsert_entry(
    entries: list, name: str, *, evidence_type: str | None, stamp: datetime | None
) -> list:
    """Append a ConceptEntry if name (casefolded) is absent; otherwise update
    the existing entry's provenance in place. Returns the (new) list."""
    out = list(entries or [])
    existing = find_entry(out, name)
    if existing is None:
        out.append(
            ConceptEntry(name=name, evidence_type=evidence_type, last_event_at=stamp)
        )
        return out
    if evidence_type is not None:
        existing.evidence_type = evidence_type
    if stamp is not None:
        existing.last_event_at = stamp
    return out


def _upgrade_concept_lists(data: dict) -> dict:
    """Element-level legacy upgrade: bare-string concepts become ConceptEntry
    dicts. Permanent, not a transition shim: seed_from_prior copies raw JSON
    forward on resume, so pre-slice-8 blobs can arrive indefinitely."""
    for key in ("mastered_concepts", "confirmed_gaps"):
        items = data.get(key)
        if isinstance(items, list):
            data[key] = [
                {"name": it, "evidence_type": None, "last_event_at": None}
                if isinstance(it, str)
                else it
                for it in items
            ]
    return data


def _parse_profile(raw: str | None) -> TopicProfile:
    """Tolerantly deserialize a stored topic_profile_json blob.

    TopicProfile is codegen'd with extra="forbid" (correct for validating tool
    args the model sends), but the same model deserializes persisted state that
    may have been written under an older schema. During an iterative build the
    profile shape sheds fields, and resume copies a prior session's raw JSON
    forward (sessions.py / seed_from_prior); a retired field left in an old row
    would otherwise raise ValidationError and 500 every read of that session
    (and the whole /profile aggregate). So: try strict parse, then drop unknown
    keys and re-validate, then fall back to an empty profile. Never raises.
    Also upgrades legacy bare-string concept-list elements to ConceptEntry
    dicts before validation (see _upgrade_concept_lists).
    """
    raw = raw or "{}"
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        log.warning("unparseable topic_profile_json; using empty profile")
        return TopicProfile()
    if not isinstance(data, dict):
        return TopicProfile()
    data = _upgrade_concept_lists(data)
    try:
        return TopicProfile.model_validate(data)
    except ValidationError:
        # Strict parse failed - retry below with unknown keys dropped.
        log.debug("topic_profile strict validation failed; retrying on known fields")
    known = {k: v for k, v in data.items() if k in TopicProfile.model_fields}
    dropped = sorted(set(data) - set(known))
    try:
        profile = TopicProfile.model_validate(known)
    except ValidationError:
        log.warning("topic_profile failed strict reparse; using empty profile")
        return TopicProfile()
    if dropped:
        log.warning("dropped legacy topic_profile fields on load: %s", dropped)
    return profile


def profile_from_row(row: SessionModel | None) -> TopicProfile:
    if row is None:
        return TopicProfile()
    return _parse_profile(row.topic_profile_json)


def load_profile(db: Session, session_id: str) -> TopicProfile:
    return profile_from_row(db.get(SessionModel, session_id))


def _enforce_list_caps(profile: TopicProfile) -> None:
    """F-35: profiles copy forward across resumes forever; without a cap the
    lists (and therefore the per-turn prompt) grow monotonically. Evict oldest
    (front-of-list) entries past settings.max_profile_list. The focused gap is
    never evicted -- dropping it would dangle focus_target_gap (F-22)."""
    cap = settings.max_profile_list
    focus_key = canon(profile.focus_target_gap) if profile.focus_target_gap else None
    for attr in ("confirmed_gaps", "mastered_concepts"):
        entries = list(getattr(profile, attr) or [])
        if len(entries) <= cap:
            continue
        keep: list = []
        overflow = len(entries) - cap
        for e in entries:
            if overflow > 0 and not (
                attr == "confirmed_gaps" and focus_key and canon(e.name) == focus_key
            ):
                overflow -= 1
                continue
            keep.append(e)
        setattr(profile, attr, keep)


def save_profile(
    db: Session, session_id: str, profile: TopicProfile, commit: bool = True
) -> None:
    _enforce_list_caps(profile)
    row = db.get(SessionModel, session_id)
    if row is None:
        raise ValueError(f"session not found: {session_id}")
    row.topic_profile_json = profile.model_dump_json()
    if commit:
        db.commit()


def lock_session_row(db: Session, session_id: str) -> SessionModel:
    """F-12: SELECT ... FOR UPDATE on the session row, serializing profile
    read-modify-write spans on Postgres (blind whole-blob writes were losing
    concurrent updates). No-op on SQLite (single-writer). The lock releases at
    the transaction's commit/rollback -- callers must commit promptly and must
    NEVER hold it across an LLM await. Raises ValueError when missing.

    #417: the returned row is fresh as of the lock (populate_existing), not
    the identity-map copy. Flushes first so the refresh keeps the caller's
    own pending edits (sessions run autoflush=False)."""
    db.flush()
    row = db.get(
        SessionModel, session_id, with_for_update=True, populate_existing=True
    )
    if row is None:
        raise ValueError(f"session not found: {session_id}")
    return row


def seed_from_prior(db: Session, new_session: SessionModel, prior: SessionModel) -> None:
    new_session.topic_profile_json = prior.topic_profile_json
    db.commit()


def profile_etag(profile: TopicProfile) -> str:
    return hashlib.sha256(profile.model_dump_json().encode("utf-8")).hexdigest()


def _null_focus_if_removed(profile: TopicProfile, item: str) -> None:
    # F-22: removal matches by canon(), so the dangling-focus check must too.
    if profile.focus_target_gap is not None and canon(profile.focus_target_gap) == canon(item):
        profile.focus_target_gap = None


def add_exclusive(
    profile: TopicProfile,
    target: str,
    item: str,
    *,
    evidence_type: str | None = None,
    stamp: datetime | None = None,
) -> None:
    """Single choke point for the exclusivity invariant (F-13, decision Q2):
    adding a concept to one list removes it from the other; removing it from
    confirmed_gaps also clears a (canon-equal) dangling focus."""
    other = "confirmed_gaps" if target == "mastered_concepts" else "mastered_concepts"
    setattr(
        profile,
        target,
        upsert_entry(
            getattr(profile, target) or [], item,
            evidence_type=evidence_type, stamp=stamp,
        ),
    )
    key = canon(item)
    setattr(
        profile, other,
        [e for e in (getattr(profile, other) or []) if canon(e.name) != key],
    )
    if other == "confirmed_gaps":
        _null_focus_if_removed(profile, item)


def apply_user_patch(
    db: Session,
    session_id: str,
    *,
    add_mastered: str | None = None,
    add_gap: str | None = None,
    knowledge_level: str | None = None,
    subtopic: str | None = None,
    subtopic_level: str | None = None,
) -> TopicProfile:
    lock_session_row(db, session_id)
    if add_mastered is not None:
        add_mastered = add_mastered.strip()
        if not add_mastered:
            raise ValueError("item cannot be empty after stripping whitespace")
    if add_gap is not None:
        add_gap = add_gap.strip()
        if not add_gap:
            raise ValueError("item cannot be empty after stripping whitespace")
    profile = load_profile(db, session_id)
    if add_mastered is not None:
        add_exclusive(
            profile, "mastered_concepts", add_mastered,
            stamp=datetime.now(timezone.utc),
        )
    if add_gap is not None:
        add_exclusive(
            profile, "confirmed_gaps", add_gap,
            stamp=datetime.now(timezone.utc),
        )
    if knowledge_level is not None:
        profile.knowledge_level = knowledge_level
    if (subtopic is None) != (subtopic_level is None):
        raise ValueError("subtopic and subtopic_level must be provided together")
    if subtopic is not None:
        key = canon(subtopic)
        if not key:
            raise ValueError("item cannot be empty after stripping whitespace")
        levels = dict(profile.subtopic_levels or {})
        if key not in levels:
            raise ValueError("unknown subtopic; subtopics are created by the tutor")
        levels[key] = subtopic_level
        profile.subtopic_levels = levels
    save_profile(db, session_id, profile)
    return profile


def remove_profile_item(
    db: Session,
    session_id: str,
    list_name: Literal["mastered_concepts", "confirmed_gaps"],
    item: str,
) -> TopicProfile:
    lock_session_row(db, session_id)
    profile = load_profile(db, session_id)
    current = list(getattr(profile, list_name) or [])
    if find_entry(current, item) is None:
        raise KeyError(item)
    key = canon(item)
    setattr(profile, list_name, [e for e in current if canon(e.name) != key])
    if list_name == "confirmed_gaps":
        _null_focus_if_removed(profile, item)
    save_profile(db, session_id, profile)
    return profile


def remove_subtopic(db: Session, session_id: str, subtopic: str) -> TopicProfile:
    lock_session_row(db, session_id)
    profile = load_profile(db, session_id)
    levels = dict(profile.subtopic_levels or {})
    key = canon(subtopic)
    if key not in levels:
        raise KeyError(subtopic)
    del levels[key]
    profile.subtopic_levels = levels
    save_profile(db, session_id, profile)
    return profile


def apply_patch(
    db: Session, ctx: ToolContext, args: UpdateTopicProfileArgs
) -> ToolResult:
    if args.session_id != ctx.session_id:
        return ToolResult(
            ok=False,
            status="failed",
            error=f"session_id mismatch: args={args.session_id} ctx={ctx.session_id}",
        )

    # F-21: "tested" provenance is reserved for the server's own grading path
    # (record_from_answer). An agent-supplied "tested" is a self-attested
    # claim, so it is recorded as "declared".
    evidence = "declared" if args.evidence_type == "tested" else args.evidence_type

    if (
        args.knowledge_level is None
        and not args.add_confirmed_gap
        and not args.add_mastered_concept
        and args.focus_target_gap is None
        and args.focus_clear_reason is None
        and args.subtopic is None
    ):
        # F-20: a no-op patch (e.g. reconstructed from malformed args) must
        # not be reported to the model as "Profile updated".
        return ToolResult(ok=False, status="failed", error="empty patch: no fields provided")

    # F-12: lock before the read so the load-mutate-save span is one atomic
    # unit; taken after the pure-arg checks above so a patch that fails
    # validation never takes the lock.
    lock_session_row(db, ctx.session_id)
    profile = load_profile(db, ctx.session_id)

    if (args.subtopic is None) != (args.subtopic_level is None):
        return ToolResult(
            ok=False,
            status="failed",
            error="subtopic and subtopic_level must be provided together",
        )
    if args.subtopic is not None:
        key = canon(args.subtopic)
        if not key:
            return ToolResult(ok=False, status="failed", error="subtopic is empty")
        levels = dict(profile.subtopic_levels or {})
        if key not in levels and len(levels) >= MAX_SUBTOPICS:
            return ToolResult(
                ok=False,
                status="failed",
                error=(
                    f"subtopic_levels is full ({MAX_SUBTOPICS}); update an "
                    "existing subtopic instead"
                ),
            )
        levels[key] = args.subtopic_level
        profile.subtopic_levels = levels

    prior_focus = profile.focus_target_gap

    if args.knowledge_level is not None:
        if evidence not in ("declared", "tested"):
            # F-39: level changes need the same evidence standard as mastery.
            # (The knowledge diagnostic sets level server-side and does not
            # pass through this function.)
            return ToolResult(
                ok=False,
                status="failed",
                error=(
                    "knowledge_level change requires evidence_type 'declared' "
                    "or 'tested'"
                ),
            )
        profile.knowledge_level = args.knowledge_level

    if args.add_confirmed_gap:
        gap_evidence = evidence if evidence in ("declared", "tested") else None
        # Route through the exclusivity choke point, like the user PATCH path,
        # so a concept never sits in both lists (B-03/F-13).
        add_exclusive(
            profile, "confirmed_gaps", args.add_confirmed_gap,
            evidence_type=gap_evidence, stamp=datetime.now(timezone.utc),
        )

    ignored_notes: list[str] = []
    mastered_this_call = False
    if args.add_mastered_concept:
        if args.evidence_type is None:
            return ToolResult(
                ok=False,
                status="failed",
                error=(
                    "evidence_type must be 'declared' or 'tested' when "
                    "add_mastered_concept is set"
                ),
            )
        if evidence in ("declared", "tested"):
            add_exclusive(
                profile, "mastered_concepts", args.add_mastered_concept,
                evidence_type=evidence,
                stamp=datetime.now(timezone.utc),
            )
            mastered_this_call = True
        else:
            # F-48: ignoring inferred mastery is policy (spec v1 rules), but
            # the model must be told it was a no-op, not "Profile updated".
            ignored_notes.append(
                "inferred mastery ignored: only 'declared' or 'tested' "
                "evidence promotes to mastered_concepts"
            )

    # focus_target_gap handling.
    # F-23: an omitted focus field is indistinguishable from an explicit null
    # after JSON parsing, so clearing is treated as INTENT only when a reason
    # accompanies it; a patch that merely omits focus leaves focus unchanged.
    clearing = (
        prior_focus is not None
        and args.focus_target_gap is None
        and args.focus_clear_reason is not None
    )
    if clearing:
        if args.focus_clear_reason == "tested_correct" and not _has_correct_event_for(
            db, ctx.session_id, prior_focus
        ):
            # F-02 (decision Q1): the flagship guard rail. "tested_correct" is
            # accepted only when a correct LearningEvent for the focused gap
            # exists in this session (record_from_answer writes one on the
            # human-click grading path). Known limit: other reason labels are
            # accepted on the agent's word.
            return ToolResult(
                ok=False,
                status="failed",
                error=(
                    "focus_clear_reason 'tested_correct' rejected: no correct "
                    f"check answer recorded for '{prior_focus}' in this session"
                ),
            )
        # G-05: gap strings are learner free text and can carry personal
        # detail, so the audit line logs a sha256 prefix plus length instead
        # of the raw name. Still correlatable across turns, no PII at rest.
        log.info(
            "focus_clear session=%s gap_sha=%s gap_len=%d reason=%s",
            ctx.session_id,
            hashlib.sha256(prior_focus.encode()).hexdigest()[:8],
            len(prior_focus),
            args.focus_clear_reason,
        )
        profile.focus_target_gap = None
    elif args.focus_target_gap is not None:
        profile.focus_target_gap = args.focus_target_gap

    # F-13 review: if this call just mastered a concept, an explicit
    # focus_target_gap resend (canon-equal to that concept) in the elif
    # above must not resurrect a focus that add_exclusive already cleared.
    if mastered_this_call:
        _null_focus_if_removed(profile, args.add_mastered_concept)

    save_profile(db, ctx.session_id, profile)

    if ignored_notes:
        only_ignored = (
            args.knowledge_level is None
            and not args.add_confirmed_gap
            and args.focus_target_gap is None
            and args.focus_clear_reason is None
            and args.subtopic is None
        )
        return ToolResult(
            ok=True,
            status="ignored" if only_ignored else "ok",
            data={"notes": ignored_notes},
        )
    return ToolResult(ok=True, status="ok")
