"""TDD: learning_event_service.record_from_answer + demotion/mastery side effects."""

from datetime import datetime, timezone

import pytest

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, ConceptEntry, TopicProfile
from db.models import Session as SessionModel
from db.models import User
from services import check_question_service as cq
from services import learning_event_service, profile_service
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
            topic_profile_json=TopicProfile(
                mastered_concepts=[{"name": "joins"}]
            ).model_dump_json(),
        )
    )
    db_session.commit()
    return db_session.get(SessionModel, SESSION_ID)


# --- record_from_answer tests (Task 3: deterministic click path) ---


def test_record_from_answer_correct_adds_mastered_and_clears(session_row, db_session):
    seed_ctx = ToolContext(
        db=db_session, session_id=SESSION_ID, user_id=USER_ID,
        turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    cq.register(db_session, seed_ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=SESSION_ID, gap="atp",
        items=[{"question": "q?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "e"}],
    ))
    event = learning_event_service.record_from_answer(
        db_session, SESSION_ID, gap="atp", question="q?", correct=True,
    )
    assert event.correct is True
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert "atp" in concept_names(profile.mastered_concepts)
    assert cq.get_pending_check(db_session, SESSION_ID) is None


def test_record_from_answer_incorrect_demotes_mastered(session_row, db_session):
    profile = profile_service.load_profile(db_session, SESSION_ID)
    profile.mastered_concepts = [ConceptEntry(name="atp")]
    profile_service.save_profile(db_session, SESSION_ID, profile)
    seed_ctx = ToolContext(
        db=db_session, session_id=SESSION_ID, user_id=USER_ID,
        turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    cq.register(db_session, seed_ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=SESSION_ID, gap="atp",
        items=[{"question": "q?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "e"}],
    ))
    learning_event_service.record_from_answer(
        db_session, SESSION_ID, gap="atp", question="q?", correct=False,
    )
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert "atp" not in concept_names(profile.mastered_concepts)


def test_record_from_answer_incorrect_demotes_into_confirmed_gaps(session_row, db_session):
    """Final-review Finding 2: server-side demotion is confirmed-gap evidence."""
    profile = profile_service.load_profile(db_session, SESSION_ID)
    profile.mastered_concepts = [ConceptEntry(name="atp")]
    profile_service.save_profile(db_session, SESSION_ID, profile)
    learning_event_service.record_from_answer(
        db_session, SESSION_ID, gap="atp", question="q?", correct=False,
        clear_pending=False,
    )
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert "atp" not in concept_names(profile.mastered_concepts)
    assert "atp" in concept_names(profile.confirmed_gaps)


def test_record_from_answer_repeated_demotion_does_not_duplicate_gap(session_row, db_session):
    profile = profile_service.load_profile(db_session, SESSION_ID)
    profile.mastered_concepts = [ConceptEntry(name="atp")]
    profile_service.save_profile(db_session, SESSION_ID, profile)
    learning_event_service.record_from_answer(
        db_session, SESSION_ID, gap="atp", question="q?", correct=False,
        clear_pending=False,
    )
    learning_event_service.record_from_answer(
        db_session, SESSION_ID, gap="atp", question="q2?", correct=False,
        clear_pending=False,
    )
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert concept_names(profile.confirmed_gaps).count("atp") == 1


def test_record_from_answer_diagnostic_incorrect_leaves_profile_untouched(db, session_id):
    """apply_profile_effects=False (diagnostic path) must not touch confirmed_gaps either."""
    learning_event_service.record_from_answer(
        db, session_id, gap="atp", question="q?", correct=False,
        clear_pending=False, apply_profile_effects=False,
    )
    profile = profile_service.load_profile(db, session_id)
    assert "atp" not in (profile.confirmed_gaps or [])
    assert "atp" not in (profile.mastered_concepts or [])


def test_record_from_answer_incorrect_non_mastered_is_noop_on_profile(session_row, db_session):
    seed_ctx = ToolContext(
        db=db_session, session_id=SESSION_ID, user_id=USER_ID,
        turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    cq.register(db_session, seed_ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=SESSION_ID, gap="krebs",
        items=[{"question": "q?", "options": ["a", "b"],
                "correct_index": 0, "explanation": "e"}],
    ))
    learning_event_service.record_from_answer(
        db_session, SESSION_ID, gap="krebs", question="q?", correct=False,
    )
    profile = profile_service.load_profile(db_session, SESSION_ID)
    assert "krebs" not in (profile.mastered_concepts or [])


# --- Task 3 new tests: clear_pending / commit opt-out ---


def test_record_from_answer_clear_pending_false_keeps_pending(session_row, db_session):
    from datetime import datetime, timezone

    from agent.types import ToolContext
    from contracts import AskCheckQuestionsArgs
    from services import check_question_service as cq

    ctx = ToolContext(db=db_session, session_id=session_row.id,
                      user_id=session_row.user_id,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    cq.register(db_session, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=session_row.id, gap="g",
        items=[{"question": "q", "options": ["a", "b"],
                "correct_index": 0, "explanation": "e"}]))
    learning_event_service.record_from_answer(
        db_session, session_row.id, gap="g", question="q",
        correct=True, clear_pending=False, commit=False)
    db_session.commit()
    assert cq.get_pending_check(db_session, session_row.id) is not None


def test_record_from_answer_defaults_still_clear(session_row, db_session):
    from datetime import datetime, timezone

    from agent.types import ToolContext
    from contracts import AskCheckQuestionsArgs
    from services import check_question_service as cq

    ctx = ToolContext(db=db_session, session_id=session_row.id,
                      user_id=session_row.user_id,
                      turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    cq.register(db_session, ctx, AskCheckQuestionsArgs(
        set_index=1, set_total=1,
        session_id=session_row.id, gap="g",
        items=[{"question": "q", "options": ["a", "b"],
                "correct_index": 0, "explanation": "e"}]))
    learning_event_service.record_from_answer(
        db_session, session_row.id, gap="g", question="q", correct=True)
    assert cq.get_pending_check(db_session, session_row.id) is None


# --- Task 5: apply_profile_effects bypass (diagnostic profile-pollution guard) ---


@pytest.fixture
def db(db_session):
    """Alias mirroring this file's db_session fixture under the brief's name."""
    return db_session


@pytest.fixture
def session_id(session_row):
    """Alias mirroring this file's session_row fixture under the brief's name."""
    return session_row.id


def test_record_from_answer_skips_mastery_when_disabled(db, session_id):
    from services import learning_event_service as les
    from services import profile_service
    les.record_from_answer(db, session_id, gap="warmup", question="q",
                           correct=True, clear_pending=False,
                           apply_profile_effects=False)
    prof = profile_service.load_profile(db, session_id)
    assert "warmup" not in (prof.mastered_concepts or [])


def test_record_from_answer_applies_mastery_by_default(db, session_id):
    from services import learning_event_service as les
    from services import profile_service
    les.record_from_answer(db, session_id, gap="loops", question="q",
                           correct=True, clear_pending=False)
    prof = profile_service.load_profile(db, session_id)
    assert "loops" in concept_names(prof.mastered_concepts)


# --- Task 9: gap_accuracy aggregate (D1.2) ---


def test_gap_accuracy_groups_by_gap(db, session_id):
    for gap, correct in [("frac", True), ("frac", False), ("frac", False), ("alg", True)]:
        learning_event_service.record_from_answer(
            db, session_id, gap=gap, question="q", correct=correct,
            clear_pending=False, apply_profile_effects=False,
        )
    acc = learning_event_service.gap_accuracy(db, session_id)
    assert acc == {"frac": {"attempts": 3, "correct": 1}, "alg": {"attempts": 1, "correct": 1}}


def test_gap_accuracy_empty_session(db, session_id):
    assert learning_event_service.gap_accuracy(db, session_id) == {}


def test_correct_answer_promotes_out_of_confirmed_gaps(db_session, session_row):
    profile = TopicProfile(
        confirmed_gaps=[ConceptEntry(name="Chain Rule")],
        focus_target_gap="chain rule",
    )
    profile_service.save_profile(db_session, session_row.id, profile)

    learning_event_service.record_from_answer(
        db_session, session_row.id,
        gap="Chain Rule", question="q?", correct=True,
    )

    after = profile_service.load_profile(db_session, session_row.id)
    assert profile_service.concept_names(after.confirmed_gaps) == []
    assert profile_service.concept_names(after.mastered_concepts) == ["Chain Rule"]
    entry = profile_service.find_entry(after.mastered_concepts, "Chain Rule")
    assert entry.evidence_type == "tested"
    assert entry.last_event_at is not None
    assert after.focus_target_gap is None


def test_record_from_answer_stamps_tested_evidence(session_row, db_session):
    from services import learning_event_service, profile_service

    learning_event_service.record_from_answer(
        db_session, session_row.id, gap="limits", question="q?", correct=True
    )
    p = profile_service.load_profile(db_session, session_row.id)
    m = profile_service.find_entry(p.mastered_concepts, "limits")
    assert m.evidence_type == "tested" and m.last_event_at is not None

    learning_event_service.record_from_answer(
        db_session, session_row.id, gap="limits", question="q?", correct=False
    )
    p = profile_service.load_profile(db_session, session_row.id)
    assert profile_service.find_entry(p.mastered_concepts, "limits") is None
    g = profile_service.find_entry(p.confirmed_gaps, "limits")
    assert g.evidence_type == "tested"


# --- F-12: row-lock every profile read-modify-write span -------------------


def test_record_from_answer_takes_the_lock_when_applying_profile_effects(
    session_row, db_session, monkeypatch
):
    calls = []
    real = profile_service.lock_session_row
    monkeypatch.setattr(
        profile_service, "lock_session_row",
        lambda db, sid: calls.append(sid) or real(db, sid),
    )
    learning_event_service.record_from_answer(
        db_session, session_row.id, gap="atp", question="q?", correct=True,
        clear_pending=False, apply_profile_effects=True,
    )
    assert calls == [session_row.id]


def test_record_from_answer_skips_lock_when_profile_effects_disabled(
    session_row, db_session, monkeypatch
):
    calls = []
    real = profile_service.lock_session_row
    monkeypatch.setattr(
        profile_service, "lock_session_row",
        lambda db, sid: calls.append(sid) or real(db, sid),
    )
    learning_event_service.record_from_answer(
        db_session, session_row.id, gap="atp", question="q?", correct=True,
        clear_pending=False, apply_profile_effects=False,
    )
    assert calls == []
