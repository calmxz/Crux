"""F-35: profile lists are capped at write time; the prompt renders only the
newest PROMPT_LIST_MAX entries per list with an older-count marker."""
import json
from datetime import datetime, timezone

from agent import prompts
from config import settings
from contracts import ConceptEntry, TopicProfile
from db.models import Session as SessionModel
from services import profile_service


def _entries(n, prefix):
    return [
        ConceptEntry(name=f"{prefix}-{i}", evidence_type="declared",
                     last_event_at=datetime.now(timezone.utc))
        for i in range(n)
    ]


def _make_session(db):
    # Brief-bug fix: SessionModel.id is a String PK with no default
    # (see backend/db/models.py); tests must supply id= explicitly.
    s = SessionModel(id="s1", user_id="u1", topic="t")
    db.add(s)
    db.commit()
    return s


def test_save_profile_evicts_oldest_past_cap(db_session):
    s = _make_session(db_session)
    profile = TopicProfile(
        confirmed_gaps=_entries(settings.max_profile_list + 3, "gap"),
    )
    profile_service.save_profile(db_session, s.id, profile)
    saved = profile_service.load_profile(db_session, s.id)
    assert len(saved.confirmed_gaps) == settings.max_profile_list
    # Oldest (front) evicted, newest kept.
    assert saved.confirmed_gaps[-1].name == f"gap-{settings.max_profile_list + 2}"
    assert saved.confirmed_gaps[0].name == "gap-3"


def test_cap_never_evicts_focused_gap(db_session):
    s = _make_session(db_session)
    profile = TopicProfile(
        confirmed_gaps=_entries(settings.max_profile_list + 1, "gap"),
        focus_target_gap="gap-0",
    )
    profile_service.save_profile(db_session, s.id, profile)
    saved = profile_service.load_profile(db_session, s.id)
    names = [e.name for e in saved.confirmed_gaps]
    assert "gap-0" in names          # focus survived
    assert "gap-1" not in names      # next-oldest evicted instead


def test_prompt_renders_newest_with_older_count():
    profile = TopicProfile(confirmed_gaps=_entries(prompts.PROMPT_LIST_MAX + 7, "gap"))
    out = prompts.build_dynamic_context({"profile": profile})
    line = next(ln for ln in out.splitlines() if ln.startswith("CURRENT TOPIC PROFILE:"))
    rendered = json.loads(line[len("CURRENT TOPIC PROFILE: "):])
    assert len(rendered["confirmed_gaps"]) == prompts.PROMPT_LIST_MAX
    assert rendered["confirmed_gaps_older_count"] == 7
    # Newest entries kept.
    assert rendered["confirmed_gaps"][-1]["name"] == f"gap-{prompts.PROMPT_LIST_MAX + 6}"
