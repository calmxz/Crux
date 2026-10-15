"""#395 golden: the full rendered system prompt for representative chat turns
and a check follow-up turn, pinned byte-for-byte.

The prompt-state refactor must not change a production prompt. Each case
drives the real route entry point (`routes.chat._prepare_turn`,
`routes.sessions._complete_check_prepare`) against a seeded sqlite DB with the
clock frozen, then compares against a fixture under
tests/fixtures/prompt_golden/. Set UPDATE_PROMPT_GOLDEN=1 to rewrite the
fixtures; a diff in them is a prompt change and needs a reason.
"""

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, ChatRequest, ConceptEntry, TopicProfile
from db.models import Document, LearningEvent, User
from db.models import Session as SessionModel
from lib import keyword_index
from routes import chat as chat_route
from routes import sessions as sessions_route
from services import check_service, learning_event_service, profile_service

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "prompt_golden"
FIXED_NOW = datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)
T1 = datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc)
T2 = datetime(2026, 2, 2, 9, 0, tzinfo=timezone.utc)


class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW if tz is not None else FIXED_NOW.replace(tzinfo=None)


@pytest.fixture(autouse=True)
def _frozen_clock(monkeypatch):
    monkeypatch.setattr(profile_service, "datetime", _FrozenDatetime)
    monkeypatch.setattr(learning_event_service, "datetime", _FrozenDatetime)


def _assert_golden(name: str, text: str) -> None:
    path = GOLDEN_DIR / f"{name}.txt"
    if os.environ.get("UPDATE_PROMPT_GOLDEN") == "1":
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    assert path.exists(), f"missing golden {path}; run with UPDATE_PROMPT_GOLDEN=1"
    assert text == path.read_bytes().decode("utf-8")


def _seed(db, *, sid, uid, topic, profile, prefs=None, **row_fields):
    db.add(User(id=uid, **(prefs or {})))
    db.flush()
    db.add(
        SessionModel(
            id=sid,
            user_id=uid,
            topic=topic,
            topic_profile_json=profile.model_dump_json(),
            **row_fields,
        )
    )
    db.commit()


def _ctx(db, sid, uid, **kw):
    return ToolContext(db=db, session_id=sid, user_id=uid, turn_started_at=T1, **kw)


def _register(db, sid, uid, *, gap, set_index, set_total, items, **ctx_kw):
    result = check_service.register(
        db,
        _ctx(db, sid, uid, **ctx_kw),
        AskCheckQuestionsArgs(
            session_id=sid, gap=gap, set_index=set_index, set_total=set_total, items=items
        ),
    )
    assert result.ok, result


_ITEMS = [
    {
        "question": "Which join keeps unmatched left rows?",
        "options": ["INNER", "LEFT OUTER", "CROSS"],
        "correct_index": 1,
        "explanation": "LEFT OUTER keeps them.",
    },
    {
        "question": "What does a NULL compare equal to?",
        "options": ["NULL", "nothing"],
        "correct_index": 1,
        "explanation": "NULL is never equal to anything.",
    },
]


def _stub_retrieval(monkeypatch, *, semantic, chunks):
    async def fake_semantic(db, session_id, query, *, user_id=None):
        return semantic, None

    async def fake_prefetch(db, session_id, user_id, query, query_vec=None, **kw):
        return chunks

    monkeypatch.setattr(
        chat_route.retrieval_service, "semantic_fallback_required", fake_semantic
    )
    monkeypatch.setattr(chat_route.retrieval_service, "prefetch_for_prompt", fake_prefetch)


def test_golden_chat_turn_rich_state(db_session, monkeypatch):
    """Every per-session block populated: non-default prefs, both summaries,
    an open set with a current question, a cooldown, gap accuracy, the topic
    card due, mixed ingestion and prefetched excerpts."""
    sid, uid = "golden-chat", "golden-u1"
    message = "explain outer joins with nulls"
    _seed(
        db_session,
        sid=sid,
        uid=uid,
        topic="sql joins",
        profile=TopicProfile(
            knowledge_level="intermediate",
            subtopic_levels={"window functions": "beginner"},
            confirmed_gaps=[
                ConceptEntry(name="outer joins", evidence_type="tested", last_event_at=T1),
                ConceptEntry(name="null handling", evidence_type="declared", last_event_at=T2),
            ],
            mastered_concepts=[
                ConceptEntry(name="inner joins", evidence_type="tested", last_event_at=T1)
            ],
            focus_target_gap="outer joins",
            last_session_summary="covered inner joins and keys",
        ),
        prefs={"feedback_pref": "direct_answers", "check_ins": "often", "reply_length": "thorough"},
        rolling_summary="learner asked how LEFT JOIN treats missing rows",
        quiz_cooldown_json=(
            '{"gap": "null handling", "last_score": "1/3", "missed": '
            '[{"question": "Is NULL = NULL true?", "chosen": "yes", "correct": "no"}]}'
        ),
        topic_suggest_state="awaiting_level",
        kw_index_json='["' + '", "'.join(sorted(keyword_index.build_from_text(message))) + '"]',
    )
    db_session.add_all(
        [
            Document(session_id=sid, filename="a.pdf", status="ready"),
            Document(session_id=sid, filename="b.pdf", status="processing"),
            LearningEvent(session_id=sid, gap_tested="outer joins", question="q1", correct=True),
            LearningEvent(session_id=sid, gap_tested="outer joins", question="q2", correct=False),
            LearningEvent(session_id=sid, gap_tested="null handling", question="q3", correct=False),
        ]
    )
    db_session.commit()
    _register(db_session, sid, uid, gap="outer joins", set_index=1, set_total=2, items=_ITEMS)
    _stub_retrieval(
        monkeypatch,
        semantic=False,
        chunks=[
            {"doc_id": "doc-1", "text": "A LEFT JOIN returns all rows of the left table."},
            {"doc_id": "doc-2", "text": "NULL is not equal to NULL."},
        ],
    )

    _messages, system_prompt, ctx = asyncio.run(
        chat_route._prepare_turn(ChatRequest(session_id=sid, message=message), uid, db_session)
    )

    _assert_golden("chat_rich", system_prompt)
    assert ctx.diagnostic_required is False


def test_golden_chat_turn_review_gaps_retention(db_session, monkeypatch):
    """Unknown level plus a review-gaps request naming a mastered concept:
    review-gap target resolution forces the diagnostic off."""
    sid, uid = "golden-review", "golden-u2"
    _seed(
        db_session,
        sid=sid,
        uid=uid,
        topic="cell biology",
        profile=TopicProfile(
            confirmed_gaps=[ConceptEntry(name="atp synthase", evidence_type="declared")],
            mastered_concepts=[
                ConceptEntry(name="glycolysis", evidence_type="tested", last_event_at=T2)
            ],
        ),
        current_check_json='{"last_set_index": 1, "set_total": 3}',
    )
    _stub_retrieval(monkeypatch, semantic=False, chunks=None)

    req = ChatRequest(
        session_id=sid,
        message="let's review",
        review_gaps=True,
        review_gap="glycolysis",
        diagnostic_accepted=True,
    )
    _messages, system_prompt, ctx = asyncio.run(chat_route._prepare_turn(req, uid, db_session))

    _assert_golden("chat_review_gaps", system_prompt)
    assert ctx.diagnostic_required is False


def test_golden_chat_turn_diagnostic_accepted(db_session, monkeypatch):
    """Fresh session, unknown level, the learner accepted the quick check."""
    sid, uid = "golden-diag", "golden-u3"
    _seed(db_session, sid=sid, uid=uid, topic="linear algebra", profile=TopicProfile())
    db_session.add(Document(session_id=sid, filename="c.pdf", status="pending"))
    db_session.commit()
    _stub_retrieval(monkeypatch, semantic=True, chunks=None)

    req = ChatRequest(session_id=sid, message="quiz me", diagnostic_accepted=True)
    _messages, system_prompt, ctx = asyncio.run(chat_route._prepare_turn(req, uid, db_session))

    _assert_golden("chat_diagnostic_accepted", system_prompt)
    assert ctx.diagnostic_required is True


def test_golden_check_followup_between_sets(db_session):
    """/check/complete after set 1 of 2. The follow-up omits learner prefs,
    the rolling summary, gap accuracy and the Check pointer today, so the
    seeded values for each must NOT reach its prompt."""
    sid, uid = "golden-followup", "golden-u4"
    _seed(
        db_session,
        sid=sid,
        uid=uid,
        topic="sql joins",
        profile=TopicProfile(
            knowledge_level="beginner",
            confirmed_gaps=[
                ConceptEntry(name="outer joins", evidence_type="declared", last_event_at=T1)
            ],
            last_session_summary="covered inner joins",
        ),
        prefs={"feedback_pref": "direct_answers", "check_ins": "often", "reply_length": "brief"},
        rolling_summary="learner asked about LEFT JOIN",
        topic_suggest_state="awaiting_level",
    )
    db_session.add(Document(session_id=sid, filename="a.pdf", status="ready"))
    db_session.commit()
    _register(db_session, sid, uid, gap="outer joins", set_index=1, set_total=2, items=_ITEMS)
    check_service.answer(db_session, sid, index=0, selected_index=1)
    check_service.answer(db_session, sid, index=1, selected_index=0)

    allowed, _messages, system_prompt, ctx = sessions_route._complete_check_prepare(
        sid, uid, db_session
    )

    assert allowed is True
    _assert_golden("followup_between_sets", system_prompt)
    assert ctx.suppress_check is True
    assert ctx.diagnostic_required is False
