"""G-11: only chunks above the cosine-similarity floor become citations.

`score` on a retrieved chunk is a pgvector cosine DISTANCE (0 = identical), so
similarity = 1 - score. The floor gates what the USER is shown as a source; the
chunks handed to the model are untouched.
"""

from config import settings
from contracts import Citation
from lib.citations import chunks_to_citations


def _chunk(**over):
    base = {
        "doc_id": "d1",
        "text": "leaves convert light",
        "page": 3,
        "doc_name": "notes.pdf",
    }
    base.update(over)
    return base


def test_chunk_below_floor_is_dropped(monkeypatch):
    monkeypatch.setattr(settings, "citation_min_similarity", 0.25)
    # distance 0.9 -> similarity 0.1 -> below the floor.
    assert chunks_to_citations([_chunk(score=0.9)]) == []


def test_chunk_above_floor_is_kept(monkeypatch):
    monkeypatch.setattr(settings, "citation_min_similarity", 0.25)
    # distance 0.2 -> similarity 0.8 -> above the floor.
    out = chunks_to_citations([_chunk(score=0.2)])
    assert len(out) == 1


def test_chunk_exactly_at_floor_is_kept(monkeypatch):
    monkeypatch.setattr(settings, "citation_min_similarity", 0.25)
    # distance 0.75 -> similarity 0.25 -> the floor is inclusive.
    assert len(chunks_to_citations([_chunk(score=0.75)])) == 1


def test_scoreless_chunk_passes(monkeypatch):
    """The sqlite fallback retrieval path reports no score; those chunks must
    never be filtered out."""
    monkeypatch.setattr(settings, "citation_min_similarity", 0.25)
    assert len(chunks_to_citations([_chunk(), _chunk(score=None)])) == 2


def test_unparseable_score_passes(monkeypatch):
    monkeypatch.setattr(settings, "citation_min_similarity", 0.25)
    assert len(chunks_to_citations([_chunk(score="n/a")])) == 1


def test_fields_match_the_previous_inline_builders(monkeypatch):
    monkeypatch.setattr(settings, "citation_min_similarity", 0.25)
    out = chunks_to_citations([_chunk(score=0.1)])
    assert out == [
        Citation(doc_id="d1", text="leaves convert light", page=3, doc_name="notes.pdf")
    ]


def test_missing_fields_default_like_the_previous_builders(monkeypatch):
    monkeypatch.setattr(settings, "citation_min_similarity", 0.25)
    out = chunks_to_citations([{"score": 0.1}])
    assert out == [Citation(doc_id="", text="", page=None, doc_name=None)]


def test_doc_id_is_stringified(monkeypatch):
    monkeypatch.setattr(settings, "citation_min_similarity", 0.25)
    out = chunks_to_citations([_chunk(doc_id=7, score=0.1)])
    assert out[0].doc_id == "7"


def test_empty_and_none_inputs(monkeypatch):
    monkeypatch.setattr(settings, "citation_min_similarity", 0.25)
    assert chunks_to_citations([]) == []
    assert chunks_to_citations(None) == []


def test_floor_is_read_at_call_time(monkeypatch):
    monkeypatch.setattr(settings, "citation_min_similarity", 0.95)
    assert chunks_to_citations([_chunk(score=0.2)]) == []
