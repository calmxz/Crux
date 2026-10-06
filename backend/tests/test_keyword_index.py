"""TDD: lib.keyword_index — Porter-stem build, match, persist."""

import json

from contracts import TopicProfile
from db.models import Session as SessionModel
from db.models import User
from lib import keyword_index


def test_build_from_text_drops_stopwords_and_stems():
    stems = keyword_index.build_from_text(
        "The runners are running quickly along the river."
    )
    assert "run" in stems or "runner" in stems
    assert "the" not in stems
    assert "are" not in stems


def test_match_required_overlap_vs_disjoint():
    index = keyword_index.build_from_text("Database indexes accelerate queries")
    assert keyword_index.match_required("how does indexing work?", index) is True
    assert keyword_index.match_required("what is recursion?", index) is False
    assert keyword_index.match_required("any query at all", set()) is False


def test_merge_into_session_persists_union(db_session):
    db_session.add(User(id="u1"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s1",
            user_id="u1",
            topic="t",
            topic_profile_json=TopicProfile().model_dump_json(),
            kw_index_json=json.dumps(["existing"]),
        )
    )
    db_session.commit()

    keyword_index.merge_into_session(db_session, "s1", {"new_stem", "existing"})
    db_session.commit()
    row = db_session.get(SessionModel, "s1")
    stored = set(json.loads(row.kw_index_json))
    assert stored == {"existing", "new_stem"}


def test_merge_into_session_locks_row(db_session, monkeypatch):
    db_session.add(User(id="u1"))
    db_session.flush()
    db_session.add(
        SessionModel(
            id="s1",
            user_id="u1",
            topic="t",
            topic_profile_json=TopicProfile().model_dump_json(),
            kw_index_json=json.dumps(["existing"]),
        )
    )
    db_session.commit()

    seen = {}
    real_get = db_session.get
    def spy(entity, ident, **kw):
        seen.update(kw)
        return real_get(entity, ident, **kw)
    monkeypatch.setattr(db_session, "get", spy)
    keyword_index.merge_into_session(db_session, "s1", {"stem"})
    assert seen.get("with_for_update") is True


def test_acronym_and_digit_tokens_indexed():
    stems = keyword_index.build_from_text(
        "DNA replication, IPv4 subnetting, and 3NF normalization"
    )
    assert "dna" in stems
    assert "ipv4" in stems
    assert "3nf" in stems


def test_two_char_letter_tokens_indexed():
    stems = keyword_index.build_from_text("ML pipelines")
    assert "ml" in stems


def test_pure_digit_tokens_dropped():
    stems = keyword_index.build_from_text("chapter 42 written in 2026")
    assert "42" not in stems
    assert "2026" not in stems


def test_short_stopwords_not_indexed():
    stems = keyword_index.build_from_text("of it to in on at be we by no")
    assert stems == set()


def test_short_stopword_query_does_not_flip_gate():
    index = keyword_index.build_from_text("Database indexes accelerate queries")
    assert keyword_index.match_required("tell me about it", index) is False


def test_digit_query_flips_gate():
    index = keyword_index.build_from_text("IPv4 addressing and subnets")
    assert keyword_index.match_required("explain ipv4 to me", index) is True
