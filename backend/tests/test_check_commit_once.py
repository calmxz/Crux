"""#419: an answer or skip click commits once, and only a Close freezes the Recap."""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import event

from agent.stream_events import StreamEvent
from agent.types import ToolContext
from contracts import AskCheckQuestionsArgs, TopicProfile
from db.models import ChatMessage, User
from db.models import Session as SessionModel
from services import check_question_service, profile_service

USER_ID = "u_commit_once"
SID = "s_commit_once"

ITEMS = [
    {"question": "Q1?", "options": ["a", "b"], "correct_index": 0, "explanation": "a."},
    {"question": "Q2?", "options": ["a", "b"], "correct_index": 1, "explanation": "b."},
]


def _seed(db, knowledge_level):
    db.add(User(id=USER_ID))
    db.add(
        SessionModel(
            id=SID,
            user_id=USER_ID,
            topic="bio",
            topic_profile_json=TopicProfile(knowledge_level=knowledge_level).model_dump_json(),
        )
    )
    db.commit()


def _open_set(db, *, diagnostic):
    ctx = ToolContext(
        db=db,
        session_id=SID,
        user_id=USER_ID,
        turn_started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        diagnostic_required=diagnostic,
    )
    result = check_question_service.register(
        db,
        ctx,
        AskCheckQuestionsArgs(set_index=1, set_total=1, session_id=SID, gap="atp", items=ITEMS),
    )
    assert result.ok
    m = ChatMessage(session_id=SID, role="assistant", content="")
    db.add(m)
    db.commit()
    db.refresh(m)
    check_question_service.attach_message_id(db, SID, m.id)
    db.commit()
    return m


@pytest.fixture
def check_set(db_session):
    _seed(db_session, "intermediate")
    return _open_set(db_session, diagnostic=False)


@pytest.fixture
def diagnostic_set(db_session):
    _seed(db_session, None)
    return _open_set(db_session, diagnostic=True)


@pytest.fixture
def commits(db_session):
    seen = []

    def on_commit(_session):
        seen.append(1)

    event.listen(db_session, "after_commit", on_commit)
    yield seen
    event.remove(db_session, "after_commit", on_commit)


def test_answer_commits_once(client, db_session, check_set, commits):
    r = client.post(
        f"/api/sessions/{SID}/check/answer",
        json={"index": 0, "selected_index": 0, "user_id": USER_ID},
    )
    assert r.status_code == 200
    assert r.json()["done"] is False
    assert len(commits) == 1


def test_final_diagnostic_answer_commits_once_and_grades(
    client, db_session, diagnostic_set, commits
):
    check_question_service.answer(db_session, SID, index=0, selected_index=0)
    commits.clear()
    r = client.post(
        f"/api/sessions/{SID}/check/answer",
        json={"index": 1, "selected_index": 1, "user_id": USER_ID},
    )
    assert r.status_code == 200
    assert r.json()["done"] is True
    assert len(commits) == 1
    db_session.expire_all()
    assert profile_service.load_profile(db_session, SID).knowledge_level == "advanced"


def test_skip_commits_once(client, db_session, check_set, commits):
    r = client.post(f"/api/sessions/{SID}/check/skip", json={"index": 0, "user_id": USER_ID})
    assert r.status_code == 200
    assert len(commits) == 1


def test_click_leaves_recap_unfrozen_until_close(client, db_session, check_set, monkeypatch):
    m = check_set
    for index, choice in ((0, 0), (1, 0)):
        r = client.post(
            f"/api/sessions/{SID}/check/answer",
            json={"index": index, "selected_index": choice, "user_id": USER_ID},
        )
        assert r.status_code == 200
    db_session.refresh(m)
    assert m.check_batch_json is None

    resolved = check_question_service.public_view(
        check_question_service.get_pending_check(db_session, SID)
    )

    async def fake(messages, system_prompt, ctx):
        reply = ChatMessage(session_id=SID, role="assistant", content="ok")
        ctx.db.add(reply)
        ctx.db.commit()
        yield StreamEvent("assistant_delta", {"text": "ok"})
        yield StreamEvent("done", {"message_id": str(reply.id)})

    monkeypatch.setattr("agent.tutor.run_streaming", fake)
    r = client.post(f"/api/sessions/{SID}/check/complete", json={"user_id": USER_ID})
    assert r.status_code == 200
    db_session.refresh(m)
    assert m.check_batch_json is not None
    assert json.loads(m.check_batch_json) == resolved
