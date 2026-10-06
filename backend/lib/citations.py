"""G-11: build Citation objects from retrieved chunks, behind a similarity floor.

`score` on a retrieved chunk is a pgvector cosine DISTANCE (0 = identical), so
similarity = 1 - score. Chunks whose similarity falls below
`settings.citation_min_similarity` are still handed to the model as context --
weak context is better than none -- they are simply not surfaced to the user as
a source, where a barely-related excerpt reads as a wrong citation.

A chunk with no score (the sqlite fallback retrieval path, which has no vector
index) always passes: there is nothing to judge it on.
"""

import logging

from config import settings
from contracts import Citation

log = logging.getLogger(__name__)


def _passes_floor(chunk: dict) -> bool:
    score = chunk.get("score")
    if score is None:
        return True
    try:
        similarity = 1.0 - float(score)
    except (TypeError, ValueError):
        # Unparseable score: fall back to surfacing the chunk rather than
        # silently hiding a retrieval hit.
        return True
    return similarity >= float(settings.citation_min_similarity)


def chunks_to_citations(chunks) -> list[Citation]:
    """Convert retrieved chunks into Citations, dropping the ones below the
    similarity floor. Reads the floor per call so it stays configurable."""
    out: list[Citation] = []
    dropped = 0
    for ch in chunks or []:
        if not _passes_floor(ch):
            dropped += 1
            continue
        out.append(
            Citation(
                doc_id=str(ch.get("doc_id", "")),
                text=ch.get("text", ""),
                page=ch.get("page"),
                doc_name=ch.get("doc_name"),
            )
        )
    if dropped:
        log.debug(
            "citation floor dropped %d of %d chunks", dropped, dropped + len(out)
        )
    return out
