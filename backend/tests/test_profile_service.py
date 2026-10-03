"""TDD: profile_service.apply_patch + focus-clear guard rail."""

import json
from datetime import datetime, timezone

import pytest

from agent.types import ToolContext
from contracts import ConceptEntry, TopicProfile, UpdateTopicProfileArgs
from db.models import LearningEvent, User
from db.models import Session as SessionModel
from services import profile_service
from services.profile_service import concept_names

SESSION_ID = "sess_1"
USER_ID = "u1"


@pytest.fixture
def session_row(db_session):
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="sql",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    return db_session.get(SessionModel, SESSION_ID)


@pytest.fixture
def ctx(db_session):
    return ToolContext(
        db=db_session,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def tool_ctx(db_session):
    """F-02 guard tests: a self-contained ToolContext that also creates the
    backing session row (save_profile requires the row to exist)."""
    db_session.add(User(id=USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SESSION_ID,
            user_id=USER_ID,
            topic="calculus",
            topic_profile_json=TopicProfile().model_dump_json(),
        )
    )
    db_session.commit()
    return ToolContext(
        db=db_session,
        session_id=SESSION_ID,
        user_id=USER_ID,
        turn_started_at=datetime.now(timezone.utc),
    )


SEEDED_SESSION_ID = "sess_seeded"
SEEDED_USER_ID = "u_seeded"


@pytest.fixture
def seeded_session_id(db_session):
    db_session.add(User(id=SEEDED_USER_ID))
    db_session.flush()
    db_session.add(
        SessionModel(
            id=SEEDED_SESSION_ID,
            user_id=SEEDED_USER_ID,
            topic_profile_json="{}",
        )
    )
    db_session.commit()
    return SEEDED_SESSION_ID


def _patch(**kw) -> UpdateTopicProfileArgs:
    kw.setdefault("session_id", SESSION_ID)
    kw.setdefault("evidence_type", "declared")
    return UpdateTopicProfileArgs(**kw)


def test_knowledge_level_without_evidence_rejected(session_row, ctx, db_session):
    # F-39 guard: level-only patch with no evidence_type must fail loudly and
    # leave the level unset (this untested branch was the diagnostic-repeat
    # loop's server half).
    result = profile_service.apply_patch(
        db_session,
        ctx,
        _patch(knowledge_level="beginner", evidence_type=None),
    )
    assert result.ok is False
    assert "evidence_type" in (result.error or "")
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert profile.knowledge_level is None


def test_declared_mastery_promotes(session_row, ctx, db_session):
    result = profile_service.apply_patch(
        db_session, ctx, _patch(add_mastered_concept="joins", evidence_type="declared")
    )
    assert result.ok is True
    assert result.status == "ok"
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert "joins" in concept_names(profile.mastered_concepts)


def test_apply_patch_mastery_add_removes_gap(session_row, ctx, db_session):
    profile = TopicProfile(confirmed_gaps=[ConceptEntry(name="chain rule")])
    profile_service.save_profile(db_session, SESSION_ID, profile)

    result = profile_service.apply_patch(
        db_session, ctx,
        _patch(add_mastered_concept="Chain Rule", evidence_type="declared"),
    )

    assert result.ok
    after = profile_service.load_profile(db_session, SESSION_ID)
    assert concept_names(after.confirmed_gaps) == []
    assert concept_names(after.mastered_concepts) == ["Chain Rule"]
    # Regression: no prior focus was set, so add_exclusive has nothing to
    # null and the later focus_target_gap block (args.focus_target_gap is
    # unset here, so it's not "not None" and clearing requires prior_focus
    # not None, which is False) must not spuriously set a focus.
    assert after.focus_target_gap is None


def test_apply_patch_mastery_add_removes_gap_with_dangling_focus_cleared(
    session_row, ctx, db_session
):
    """Regression: when a prior focus points at the gap being promoted,
    add_exclusive nulls it (canon-equal), and the agent's explicit
    focus_clear_reason satisfies apply_patch's own clearing guard -- the
    later focus block must not resurrect the nulled focus."""
    profile = TopicProfile(
        confirmed_gaps=[ConceptEntry(name="chain rule")],
        focus_target_gap="chain rule",
    )
    profile_service.save_profile(db_session, SESSION_ID, profile)

    result = profile_service.apply_patch(
        db_session, ctx,
        _patch(
            add_mastered_concept="Chain Rule",
            evidence_type="declared",
            focus_clear_reason="demonstrated",
        ),
    )

    assert result.ok
    after = profile_service.load_profile(db_session, SESSION_ID)
    assert concept_names(after.confirmed_gaps) == []
    assert concept_names(after.mastered_concepts) == ["Chain Rule"]
    assert after.focus_target_gap is None


def test_apply_patch_mastery_add_rejects_explicit_focus_resend_of_mastered_gap(
    session_row, ctx, db_session
):
    """F-13: add_exclusive nulls a canon-equal prior focus when a gap is
    mastered. If the same call also explicitly
    resends focus_target_gap equal to the just-mastered concept, the later
    elif branch (args.focus_target_gap is not None) must not resurrect it --
    the mastered concept is no longer in confirmed_gaps, so a focus pointing
    at it is dangling regardless of what the caller resent."""
    profile = TopicProfile(
        confirmed_gaps=[ConceptEntry(name="chain rule")],
        focus_target_gap="chain rule",
    )
    profile_service.save_profile(db_session, SESSION_ID, profile)

    result = profile_service.apply_patch(
        db_session, ctx,
        _patch(
            add_mastered_concept="Chain Rule",
            evidence_type="declared",
            focus_target_gap="chain rule",
        ),
    )

    assert result.ok
    after = profile_service.load_profile(db_session, SESSION_ID)
    assert concept_names(after.confirmed_gaps) == []
    assert concept_names(after.mastered_concepts) == ["Chain Rule"]
    assert after.focus_target_gap is None


def test_apply_patch_mastery_add_allows_unrelated_explicit_focus(
    session_row, ctx, db_session
):
    """An explicit focus_target_gap unrelated to the mastered concept must
    still be set -- only the resurrection of the just-mastered gap's own
    focus is suppressed."""
    profile = TopicProfile(
        confirmed_gaps=[
            ConceptEntry(name="chain rule"),
            ConceptEntry(name="product rule"),
        ],
        focus_target_gap="chain rule",
    )
    profile_service.save_profile(db_session, SESSION_ID, profile)

    result = profile_service.apply_patch(
        db_session, ctx,
        _patch(
            add_mastered_concept="Chain Rule",
            evidence_type="declared",
            focus_target_gap="product rule",
        ),
    )

    assert result.ok
    after = profile_service.load_profile(db_session, SESSION_ID)
    assert concept_names(after.confirmed_gaps) == ["product rule"]
    assert concept_names(after.mastered_concepts) == ["Chain Rule"]
    assert after.focus_target_gap == "product rule"


def test_inferred_mastery_ignored(session_row, ctx, db_session):
    result = profile_service.apply_patch(
        db_session, ctx, _patch(add_mastered_concept="joins", evidence_type="inferred")
    )
    assert result.ok is True
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert "joins" not in concept_names(profile.mastered_concepts)


def test_tested_mastery_promotes(session_row, ctx, db_session):
    result = profile_service.apply_patch(
        db_session, ctx, _patch(add_mastered_concept="joins", evidence_type="tested")
    )
    assert result.ok is True
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert "joins" in concept_names(profile.mastered_concepts)


def test_duplicate_gap_is_noop(session_row, ctx, db_session):
    profile_service.apply_patch(
        db_session, ctx, _patch(add_confirmed_gap="foreign_keys", evidence_type="declared")
    )
    profile_service.apply_patch(
        db_session, ctx, _patch(add_confirmed_gap="foreign_keys", evidence_type="declared")
    )
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert concept_names(profile.confirmed_gaps).count("foreign_keys") == 1


def test_knowledge_level_overwrites(session_row, ctx, db_session):
    profile_service.apply_patch(
        db_session, ctx, _patch(knowledge_level="beginner", evidence_type="declared")
    )
    profile_service.apply_patch(
        db_session, ctx, _patch(knowledge_level="intermediate", evidence_type="declared")
    )
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert profile.knowledge_level == "intermediate"


def test_focus_target_gap_set_from_none(session_row, ctx, db_session):
    result = profile_service.apply_patch(
        db_session, ctx, _patch(focus_target_gap="joins", evidence_type="inferred")
    )
    assert result.ok is True
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert profile.focus_target_gap == "joins"


def _set_focus(db_session, ctx, gap: str):
    profile_service.apply_patch(
        db_session, ctx, _patch(focus_target_gap=gap, evidence_type="inferred")
    )


def test_focus_clear_without_reason_is_not_a_clear(session_row, ctx, db_session):
    # F-23 (restored): a null focus_target_gap without focus_clear_reason is
    # indistinguishable from an omitted field, so it is NOT treated as a
    # clear -- focus is left unchanged either way. Under F-20 this specific
    # call carries no actionable field at all (only evidence_type is set),
    # so it is now rejected as an empty patch rather than silently
    # succeeding.
    _set_focus(db_session, ctx, "joins")
    result = profile_service.apply_patch(
        db_session, ctx, _patch(focus_target_gap=None, evidence_type="inferred")
    )
    assert result.ok is False
    assert result.status == "failed"
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert profile.focus_target_gap == "joins"


def test_focus_clear_tested_correct_no_event_rejected(session_row, ctx, db_session):
    # F-02 (restored, decision Q1): tested_correct is rejected when no correct
    # LearningEvent for the focused gap exists in this session.
    _set_focus(db_session, ctx, "joins")
    result = profile_service.apply_patch(
        db_session,
        ctx,
        _patch(
            focus_target_gap=None,
            focus_clear_reason="tested_correct",
            evidence_type="tested",
        ),
    )
    assert result.ok is False
    assert "tested_correct" in (result.error or "")
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert profile.focus_target_gap == "joins"


def test_focus_clear_tested_correct_ok(session_row, ctx, db_session):
    # F-02 (restored): with a correct LearningEvent recorded for the focused
    # gap in this session, the clear is accepted.
    _set_focus(db_session, ctx, "joins")
    db_session.add(LearningEvent(
        session_id=SESSION_ID, gap_tested="joins", question="q?", correct=True,
    ))
    db_session.commit()
    result = profile_service.apply_patch(
        db_session,
        ctx,
        _patch(
            focus_target_gap=None,
            focus_clear_reason="tested_correct",
            evidence_type="tested",
        ),
    )
    assert result.ok is True
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert profile.focus_target_gap is None


def test_focus_clear_user_redirected_ok(session_row, ctx, db_session):
    _set_focus(db_session, ctx, "joins")
    result = profile_service.apply_patch(
        db_session,
        ctx,
        _patch(
            focus_target_gap=None,
            focus_clear_reason="user_redirected",
            evidence_type="inferred",
        ),
    )
    assert result.ok is True
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert profile.focus_target_gap is None


def test_load_profile_tolerates_legacy_fields(session_row, db_session):
    """Regression (review #2): a topic_profile_json written under an older schema
    (carrying since-removed fields) must not raise ValidationError -> 500 on load.
    Unknown keys are dropped; known data is preserved. TopicProfile has
    extra="forbid", and load_profile re-parses the stored column, so without the
    tolerant parser this row would 500 every read (and the /profile aggregate)."""
    row = db_session.get(SessionModel, SESSION_ID)
    row.topic_profile_json = json.dumps(
        {
            "knowledge_level": "intermediate",
            "mastered_concepts": ["joins"],
            "mastered_candidates": ["legacy"],     # retired field
            "interaction_preferences": {"hints": True},  # retired field
        }
    )
    db_session.commit()

    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert profile.knowledge_level == "intermediate"
    assert concept_names(profile.mastered_concepts) == ["joins"]
    assert not hasattr(profile, "mastered_candidates")


def test_focus_only_patch_without_evidence_type_succeeds(session_row, ctx, db_session):
    args = UpdateTopicProfileArgs(
        session_id=SESSION_ID,
        focus_target_gap="calvin_cycle",
        evidence_type=None,
    )
    result = profile_service.apply_patch(db_session, ctx, args)
    assert result.ok is True
    assert profile_service.load_profile(db_session, SESSION_ID).focus_target_gap == "calvin_cycle"


def test_mastered_concept_requires_evidence_type(session_row, ctx, db_session):
    args = UpdateTopicProfileArgs(
        session_id=SESSION_ID,
        add_mastered_concept="light_reactions",
        evidence_type=None,
    )
    result = profile_service.apply_patch(db_session, ctx, args)
    assert result.ok is False
    assert "evidence_type" in (result.error or "")


def test_mastered_concept_with_declared_promotes(session_row, ctx, db_session):
    args = UpdateTopicProfileArgs(
        session_id=SESSION_ID,
        add_mastered_concept="light_reactions",
        evidence_type="declared",
    )
    result = profile_service.apply_patch(db_session, ctx, args)
    assert result.ok is True
    assert "light_reactions" in concept_names(
        profile_service.load_profile(db_session, SESSION_ID).mastered_concepts
    )


def test_load_profile_falls_back_on_unparseable_blob(session_row, db_session):
    """Regression (review #2): a non-JSON / corrupt blob degrades to an empty
    profile rather than raising."""
    row = db_session.get(SessionModel, SESSION_ID)
    row.topic_profile_json = "not valid json {"
    db_session.commit()

    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert profile == TopicProfile()


def test_save_profile_commit_false_defers_write(session_row, db_session):
    """commit=False leaves the write in the open transaction so a caller can
    batch it into one atomic commit (used by record_from_answer to close the
    double-grade window). A rollback before commit must revert it."""
    profile = profile_service.load_profile(db_session, SESSION_ID)
    profile.mastered_concepts = [ConceptEntry(name="deferred_gap")]
    profile_service.save_profile(db_session, SESSION_ID, profile, commit=False)

    # Visible within the same uncommitted transaction...
    assert "deferred_gap" in concept_names(
        profile_service.load_profile(db_session, SESSION_ID).mastered_concepts
    )
    # ...but not yet committed: a rollback drops it.
    db_session.rollback()
    assert "deferred_gap" not in concept_names(
        profile_service.load_profile(db_session, SESSION_ID).mastered_concepts or []
    )


def test_profile_etag_is_stable_and_changes_with_content():
    a = TopicProfile(mastered_concepts=[{"name": "x"}])
    b = TopicProfile(mastered_concepts=[{"name": "x"}])
    c = TopicProfile(mastered_concepts=[{"name": "y"}])
    assert profile_service.profile_etag(a) == profile_service.profile_etag(b)
    assert profile_service.profile_etag(a) != profile_service.profile_etag(c)


def test_apply_user_patch_adds_and_sets_level(db_session, seeded_session_id):
    p = profile_service.apply_user_patch(
        db_session, seeded_session_id, add_mastered="loops", knowledge_level="advanced"
    )
    assert "loops" in concept_names(p.mastered_concepts)
    assert p.knowledge_level == "advanced"
    # persisted
    assert "loops" in concept_names(
        profile_service.load_profile(db_session, seeded_session_id).mastered_concepts
    )


def test_apply_user_patch_strips_whitespace(db_session, seeded_session_id):
    profile_service.apply_user_patch(db_session, seeded_session_id, add_mastered="  loops  ")
    reloaded = profile_service.load_profile(db_session, seeded_session_id)
    names = concept_names(reloaded.mastered_concepts)
    assert "loops" in names
    assert "  loops  " not in names


def test_apply_user_patch_whitespace_only_raises_value_error(db_session, seeded_session_id):
    with pytest.raises(ValueError):
        profile_service.apply_user_patch(db_session, seeded_session_id, add_mastered="   ")


def test_apply_user_patch_mutual_exclusion_moves_item(db_session, seeded_session_id):
    profile_service.apply_user_patch(db_session, seeded_session_id, add_gap="recursion")
    p = profile_service.apply_user_patch(db_session, seeded_session_id, add_mastered="recursion")
    assert "recursion" in concept_names(p.mastered_concepts)
    assert "recursion" not in concept_names(p.confirmed_gaps)
    # persisted
    reloaded = profile_service.load_profile(db_session, seeded_session_id)
    assert "recursion" in concept_names(reloaded.mastered_concepts)
    assert "recursion" not in concept_names(reloaded.confirmed_gaps)


def test_add_mastered_nulls_focus_when_it_was_the_focused_gap(db_session, seeded_session_id):
    profile_service.save_profile(
        db_session, seeded_session_id,
        TopicProfile(confirmed_gaps=[{"name": "recursion"}], focus_target_gap="recursion"),
    )
    p = profile_service.apply_user_patch(db_session, seeded_session_id, add_mastered="recursion")
    assert p.focus_target_gap is None
    # persisted
    reloaded = profile_service.load_profile(db_session, seeded_session_id)
    assert reloaded.focus_target_gap is None


def test_remove_profile_item_removes_and_persists(db_session, seeded_session_id):
    profile_service.apply_user_patch(db_session, seeded_session_id, add_mastered="loops")
    p = profile_service.remove_profile_item(db_session, seeded_session_id, "mastered_concepts", "loops")
    assert "loops" not in concept_names(p.mastered_concepts)
    # persisted
    reloaded = profile_service.load_profile(db_session, seeded_session_id)
    assert "loops" not in concept_names(reloaded.mastered_concepts)


def test_remove_confirmed_gap_nulls_focus(db_session, seeded_session_id):
    profile_service.save_profile(
        db_session, seeded_session_id,
        TopicProfile(confirmed_gaps=[{"name": "recursion"}], focus_target_gap="recursion"),
    )
    p = profile_service.remove_profile_item(db_session, seeded_session_id, "confirmed_gaps", "recursion")
    assert "recursion" not in concept_names(p.confirmed_gaps)
    assert p.focus_target_gap is None
    # persisted
    reloaded = profile_service.load_profile(db_session, seeded_session_id)
    assert "recursion" not in concept_names(reloaded.confirmed_gaps)
    assert reloaded.focus_target_gap is None


def test_remove_missing_item_raises_keyerror(db_session, seeded_session_id):
    with pytest.raises(KeyError):
        profile_service.remove_profile_item(db_session, seeded_session_id, "mastered_concepts", "nope")


def test_apply_user_patch_missing_session_raises_value_error(db_session):
    with pytest.raises(ValueError):
        profile_service.apply_user_patch(db_session, "nonexistent-session-id", add_mastered="x")


# --- F-12: row-lock every profile read-modify-write span -------------------


def test_lock_session_row_returns_row(db_session, session_row):
    row = profile_service.lock_session_row(db_session, session_row.id)
    assert row.id == session_row.id


def test_lock_session_row_missing_session_raises(db_session):
    with pytest.raises(ValueError):
        profile_service.lock_session_row(db_session, "nope")


def test_lock_session_row_emits_for_update_on_postgres():
    # SQLite ignores FOR UPDATE, so prove intent at the SQL layer instead.
    from sqlalchemy import select
    from sqlalchemy.dialects import postgresql

    from db.models import Session as SessionModel
    stmt = select(SessionModel).where(SessionModel.id == "x").with_for_update()
    assert "FOR UPDATE" in str(stmt.compile(dialect=postgresql.dialect()))


def test_apply_user_patch_takes_the_lock(db_session, session_row, monkeypatch):
    calls = []
    real = profile_service.lock_session_row
    monkeypatch.setattr(
        profile_service, "lock_session_row",
        lambda db, sid: calls.append(sid) or real(db, sid),
    )
    profile_service.apply_user_patch(db_session, session_row.id, add_gap="x")
    assert calls == [session_row.id]


def test_apply_patch_takes_the_lock(db_session, session_row, ctx, monkeypatch):
    calls = []
    real = profile_service.lock_session_row
    monkeypatch.setattr(
        profile_service, "lock_session_row",
        lambda db, sid: calls.append(sid) or real(db, sid),
    )
    profile_service.apply_patch(
        db_session, ctx, _patch(add_confirmed_gap="x", evidence_type="declared")
    )
    assert calls == [session_row.id]


def test_profile_from_row_parses_without_db(db_session):
    row = SessionModel(user_id="u", topic="t",
                       topic_profile_json='{"knowledge_level": "beginner"}')
    profile = profile_service.profile_from_row(row)
    assert profile.knowledge_level == "beginner"


def test_profile_from_row_tolerates_null_json():
    row = SessionModel(user_id="u", topic="t", topic_profile_json=None)
    assert profile_service.profile_from_row(row) is not None


from services.profile_service import (  # noqa: E402
    _parse_profile,
    canon,
    find_entry,
    upsert_entry,
)


def test_parse_upgrades_legacy_string_elements():
    raw = '{"knowledge_level": "beginner", "mastered_concepts": ["limits"], "confirmed_gaps": ["chain rule", "u-sub"]}'
    p = _parse_profile(raw)
    assert p.mastered_concepts[0] == ConceptEntry(
        name="limits", evidence_type=None, last_event_at=None
    )
    assert concept_names(p.confirmed_gaps) == ["chain rule", "u-sub"]
    assert p.knowledge_level == "beginner"


def test_parse_accepts_mixed_legacy_and_new_elements():
    raw = (
        '{"mastered_concepts": ["limits", {"name": "derivatives",'
        ' "evidence_type": "tested", "last_event_at": null}]}'
    )
    p = _parse_profile(raw)
    assert concept_names(p.mastered_concepts) == ["limits", "derivatives"]
    assert p.mastered_concepts[1].evidence_type == "tested"


def test_parse_still_drops_unknown_keys_and_never_raises():
    raw = '{"mastered_concepts": ["limits"], "retired_field": 1}'
    p = _parse_profile(raw)
    assert concept_names(p.mastered_concepts) == ["limits"]
    assert _parse_profile("not json").mastered_concepts == []
    assert _parse_profile('{"mastered_concepts": [42]}').mastered_concepts == []


def test_parse_defaults_subtopic_levels_empty():
    assert _parse_profile("{}").subtopic_levels == {}


def test_entry_helpers():
    entries = [ConceptEntry(name="Limits")]
    assert canon("  LIMITS ") == "limits"
    assert find_entry(entries, "limits").name == "Limits"
    assert find_entry(entries, "derivatives") is None
    stamp = datetime.now(timezone.utc)
    out = upsert_entry(entries, "limits", evidence_type="tested", stamp=stamp)
    assert len(out) == 1 and out[0].evidence_type == "tested" and out[0].last_event_at == stamp
    out2 = upsert_entry(out, "chain rule", evidence_type=None, stamp=stamp)
    assert concept_names(out2) == ["Limits", "chain rule"]


def test_apply_patch_stamps_provenance(session_row, db_session):
    from agent.types import ToolContext
    from contracts import UpdateTopicProfileArgs
    from services import profile_service

    ctx = ToolContext(
        db=db_session,
        session_id=session_row.id,
        user_id=session_row.user_id,
        turn_started_at=datetime.now(timezone.utc),
    )
    res = profile_service.apply_patch(
        db_session, ctx,
        UpdateTopicProfileArgs(
            session_id=session_row.id,
            add_mastered_concept="limits",
            evidence_type="declared",
        ),
    )
    assert res.ok
    p = profile_service.load_profile(db_session, session_row.id)
    entry = p.mastered_concepts[0]
    assert entry.name == "limits"
    assert entry.evidence_type == "declared"
    assert entry.last_event_at is not None
    first_stamp = entry.last_event_at

    # repeat with tested evidence: agent-supplied "tested" is downgraded to
    # "declared" (F-21) -- "tested" provenance is reserved for the server's
    # own grading path (record_from_answer). No duplicate entry either way.
    # Assert on the second call's own result (not just re-reading state
    # after call 1) so a silent no-op on the second call would fail here,
    # and assert the re-stamp actually advanced last_event_at -- otherwise
    # this test would pass even if upsert_entry never re-stamped on repeat.
    res2 = profile_service.apply_patch(
        db_session, ctx,
        UpdateTopicProfileArgs(
            session_id=session_row.id,
            add_mastered_concept="LIMITS",
            evidence_type="tested",
        ),
    )
    assert res2.ok
    p = profile_service.load_profile(db_session, session_row.id)
    assert len(p.mastered_concepts) == 1
    assert p.mastered_concepts[0].evidence_type == "declared"
    assert p.mastered_concepts[0].last_event_at is not None
    assert p.mastered_concepts[0].last_event_at > first_stamp


def test_user_patch_and_delete_are_entry_aware(session_row, db_session):
    from services import profile_service

    profile_service.apply_user_patch(db_session, session_row.id, add_gap="chain rule")
    p = profile_service.load_profile(db_session, session_row.id)
    assert p.confirmed_gaps[0].name == "chain rule"
    assert p.confirmed_gaps[0].evidence_type is None
    assert p.confirmed_gaps[0].last_event_at is not None

    p = profile_service.remove_profile_item(
        db_session, session_row.id, "confirmed_gaps", "Chain Rule"
    )
    assert p.confirmed_gaps == []


def _ctx_args(db_session, session_row, **kw):
    from agent.types import ToolContext
    from contracts import UpdateTopicProfileArgs

    ctx = ToolContext(
        db=db_session,
        session_id=session_row.id,
        user_id=session_row.user_id,
        turn_started_at=datetime.now(timezone.utc),
    )
    return ctx, UpdateTopicProfileArgs(session_id=session_row.id, **kw)


def test_apply_patch_sets_subtopic_level(session_row, db_session):
    from services import profile_service

    ctx, args = _ctx_args(
        db_session, session_row, subtopic="  Integration BY Parts ", subtopic_level="beginner"
    )
    res = profile_service.apply_patch(db_session, ctx, args)
    assert res.ok
    p = profile_service.load_profile(db_session, session_row.id)
    assert p.subtopic_levels == {"integration by parts": "beginner"}


def test_apply_patch_subtopic_requires_pair(session_row, db_session):
    from services import profile_service

    ctx, args = _ctx_args(db_session, session_row, subtopic="chain rule")
    res = profile_service.apply_patch(db_session, ctx, args)
    assert not res.ok
    assert "together" in res.error


def test_apply_patch_subtopic_cap(session_row, db_session):
    from services import profile_service

    p = profile_service.load_profile(db_session, session_row.id)
    p.subtopic_levels = {f"topic {i}": "beginner" for i in range(20)}
    profile_service.save_profile(db_session, session_row.id, p)

    ctx, args = _ctx_args(db_session, session_row, subtopic="one more", subtopic_level="advanced")
    res = profile_service.apply_patch(db_session, ctx, args)
    assert not res.ok and "full" in res.error

    # updating an existing key is always allowed
    ctx, args = _ctx_args(db_session, session_row, subtopic="topic 3", subtopic_level="advanced")
    assert profile_service.apply_patch(db_session, ctx, args).ok


def test_apply_patch_subtopic_empty_after_strip(session_row, db_session):
    from services import profile_service

    ctx, args = _ctx_args(db_session, session_row, subtopic="   ", subtopic_level="beginner")
    res = profile_service.apply_patch(db_session, ctx, args)
    assert not res.ok
    assert "empty" in res.error


def test_null_focus_if_removed_matches_canonically():
    profile = TopicProfile(focus_target_gap="Chain Rule")
    profile_service._null_focus_if_removed(profile, "  chain rule ")
    assert profile.focus_target_gap is None


def test_null_focus_if_removed_leaves_unrelated_focus():
    profile = TopicProfile(focus_target_gap="Chain Rule")
    profile_service._null_focus_if_removed(profile, "product rule")
    assert profile.focus_target_gap == "Chain Rule"


def test_add_exclusive_is_public_and_clears_canon_focus():
    profile = TopicProfile(
        focus_target_gap="chain rule",
        confirmed_gaps=[ConceptEntry(name="Chain Rule")],
    )
    profile_service.add_exclusive(profile, "mastered_concepts", "CHAIN RULE")
    assert profile_service.concept_names(profile.confirmed_gaps) == []
    assert profile.focus_target_gap is None
    assert profile_service.concept_names(profile.mastered_concepts) == ["CHAIN RULE"]


def _clear_args(session_id, reason):
    return UpdateTopicProfileArgs(session_id=session_id, focus_clear_reason=reason)


def test_tested_correct_clear_rejected_without_event(db_session, tool_ctx):
    profile = TopicProfile(focus_target_gap="chain rule")
    profile_service.save_profile(db_session, tool_ctx.session_id, profile)

    result = profile_service.apply_patch(
        db_session, tool_ctx, _clear_args(tool_ctx.session_id, "tested_correct")
    )

    assert not result.ok
    assert "tested_correct" in (result.error or "")
    after = profile_service.load_profile(db_session, tool_ctx.session_id)
    assert after.focus_target_gap == "chain rule"


def test_tested_correct_clear_accepted_with_canon_matching_event(db_session, tool_ctx):
    profile = TopicProfile(focus_target_gap="Chain Rule")
    profile_service.save_profile(db_session, tool_ctx.session_id, profile)
    db_session.add(LearningEvent(
        session_id=tool_ctx.session_id, gap_tested="  chain rule ",
        question="q?", correct=True,
    ))
    db_session.commit()

    result = profile_service.apply_patch(
        db_session, tool_ctx, _clear_args(tool_ctx.session_id, "tested_correct")
    )

    assert result.ok
    assert profile_service.load_profile(db_session, tool_ctx.session_id).focus_target_gap is None


def test_tested_correct_clear_rejected_for_event_on_other_gap(db_session, tool_ctx):
    profile = TopicProfile(focus_target_gap="chain rule")
    profile_service.save_profile(db_session, tool_ctx.session_id, profile)
    db_session.add(LearningEvent(
        session_id=tool_ctx.session_id, gap_tested="product rule",
        question="q?", correct=True,
    ))
    db_session.commit()

    result = profile_service.apply_patch(
        db_session, tool_ctx, _clear_args(tool_ctx.session_id, "tested_correct")
    )

    assert not result.ok


def test_non_tested_reasons_clear_without_event(db_session, tool_ctx):
    for reason in ("demonstrated", "user_redirected"):
        profile = TopicProfile(focus_target_gap="chain rule")
        profile_service.save_profile(db_session, tool_ctx.session_id, profile)
        result = profile_service.apply_patch(
            db_session, tool_ctx, _clear_args(tool_ctx.session_id, reason)
        )
        assert result.ok
        assert profile_service.load_profile(db_session, tool_ctx.session_id).focus_target_gap is None


def test_omitted_focus_without_reason_is_not_a_clear(db_session, tool_ctx):
    # F-23: a non-focus patch while focus is set must neither fail nor clear.
    profile = TopicProfile(focus_target_gap="chain rule")
    profile_service.save_profile(db_session, tool_ctx.session_id, profile)

    result = profile_service.apply_patch(
        db_session, tool_ctx,
        UpdateTopicProfileArgs(session_id=tool_ctx.session_id, add_confirmed_gap="product rule"),
    )

    assert result.ok
    after = profile_service.load_profile(db_session, tool_ctx.session_id)
    assert after.focus_target_gap == "chain rule"
    assert "product rule" in profile_service.concept_names(after.confirmed_gaps)


def test_agent_tested_evidence_downgraded_to_declared(db_session, tool_ctx):
    result = profile_service.apply_patch(
        db_session, tool_ctx,
        UpdateTopicProfileArgs(
            session_id=tool_ctx.session_id,
            add_mastered_concept="chain rule",
            evidence_type="tested",
        ),
    )
    assert result.ok
    after = profile_service.load_profile(db_session, tool_ctx.session_id)
    entry = profile_service.find_entry(after.mastered_concepts, "chain rule")
    assert entry.evidence_type == "declared"


def test_agent_tested_gap_evidence_downgraded(db_session, tool_ctx):
    result = profile_service.apply_patch(
        db_session, tool_ctx,
        UpdateTopicProfileArgs(
            session_id=tool_ctx.session_id,
            add_confirmed_gap="chain rule",
            evidence_type="tested",
        ),
    )
    assert result.ok
    after = profile_service.load_profile(db_session, tool_ctx.session_id)
    entry = profile_service.find_entry(after.confirmed_gaps, "chain rule")
    assert entry.evidence_type == "declared"


def test_knowledge_level_requires_evidence(db_session, tool_ctx):
    result = profile_service.apply_patch(
        db_session, tool_ctx,
        UpdateTopicProfileArgs(session_id=tool_ctx.session_id, knowledge_level="advanced"),
    )
    assert not result.ok
    assert "evidence" in (result.error or "").lower()
    assert profile_service.load_profile(db_session, tool_ctx.session_id).knowledge_level is None


def test_knowledge_level_with_declared_evidence_accepted(db_session, tool_ctx):
    result = profile_service.apply_patch(
        db_session, tool_ctx,
        UpdateTopicProfileArgs(
            session_id=tool_ctx.session_id,
            knowledge_level="advanced",
            evidence_type="declared",
        ),
    )
    assert result.ok
    assert profile_service.load_profile(db_session, tool_ctx.session_id).knowledge_level == "advanced"


def test_empty_patch_fails(db_session, tool_ctx):
    result = profile_service.apply_patch(
        db_session, tool_ctx, UpdateTopicProfileArgs(session_id=tool_ctx.session_id)
    )
    assert not result.ok
    assert result.status == "failed"
    assert "empty patch" in (result.error or "")


def test_inferred_only_patch_returns_ignored(db_session, tool_ctx):
    result = profile_service.apply_patch(
        db_session, tool_ctx,
        UpdateTopicProfileArgs(
            session_id=tool_ctx.session_id,
            add_mastered_concept="chain rule",
            evidence_type="inferred",
        ),
    )
    assert result.ok
    assert result.status == "ignored"
    assert "inferred" in json.dumps(result.data or {})
    after = profile_service.load_profile(db_session, tool_ctx.session_id)
    assert profile_service.concept_names(after.mastered_concepts) == []


def test_inferred_mastery_alongside_real_change_is_ok_with_note(db_session, tool_ctx):
    result = profile_service.apply_patch(
        db_session, tool_ctx,
        UpdateTopicProfileArgs(
            session_id=tool_ctx.session_id,
            add_mastered_concept="chain rule",
            add_confirmed_gap="product rule",
            evidence_type="inferred",
        ),
    )
    assert result.ok
    assert result.status == "ok"
    assert "inferred" in json.dumps(result.data or {})
    after = profile_service.load_profile(db_session, tool_ctx.session_id)
    assert "product rule" in profile_service.concept_names(after.confirmed_gaps)


def test_agent_gap_add_removes_concept_from_mastered(db_session, session_row, ctx):
    profile_service.apply_patch(
        db_session, ctx, _patch(add_mastered_concept="chain rule", evidence_type="tested")
    )
    profile_service.apply_patch(
        db_session, ctx, _patch(add_confirmed_gap="chain rule", evidence_type="inferred")
    )
    profile = profile_service.load_profile(db_session, session_row.id)
    gaps = [e.name for e in (profile.confirmed_gaps or [])]
    mastered = [e.name for e in (profile.mastered_concepts or [])]
    assert "chain rule" in gaps
    assert "chain rule" not in mastered


def test_focus_clear_log_redacts_gap_name(session_row, ctx, db_session, caplog):
    """G-05: the focus_clear INFO line must not carry the raw gap string
    (learner free text is PII-adjacent). A sha256 prefix plus length keeps the
    line correlatable without leaking content."""
    import hashlib
    import logging

    gap = "photosynthesis light reactions"
    _set_focus(db_session, ctx, gap)
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="services.profile_service"):
        result = profile_service.apply_patch(
            db_session,
            ctx,
            _patch(
                focus_target_gap=None,
                focus_clear_reason="user_redirected",
                evidence_type="inferred",
            ),
        )
    assert result.ok is True

    records = [r for r in caplog.records if r.name == "services.profile_service"]
    messages = [r.getMessage() for r in records]
    assert not any(gap in m for m in messages), messages
    digest = hashlib.sha256(gap.encode()).hexdigest()[:8]
    line = next(m for m in messages if "focus_clear session=" in m)
    assert f"gap_sha={digest}" in line
    assert f"gap_len={len(gap)}" in line
    assert "reason=user_redirected" in line
