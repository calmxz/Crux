"""TDD: lib.chunking — token-bounded chunks with page tracking + overlap."""

import pytest

from lib import chunking
from lib.chunking import chunk_text


def test_single_short_page_yields_one_chunk():
    chunks = chunk_text([(1, "A short sentence about joins.")])
    assert len(chunks) == 1
    assert chunks[0].page == 1
    assert chunks[0].chunk_idx == 0
    assert "joins" in chunks[0].text


def test_multi_chunk_respects_overlap():
    long_text = " ".join(["alpha"] * 1500)
    chunks = chunk_text([(1, long_text)], chunk_tokens=500, overlap_tokens=50)
    assert len(chunks) > 1
    # Sequential chunk_idx
    assert [c.chunk_idx for c in chunks] == list(range(len(chunks)))
    # Each chunk has alpha tokens; overlap means consecutive chunks share content
    first_tokens = chunks[0].text.split()
    second_tokens = chunks[1].text.split()
    assert any(t in second_tokens for t in first_tokens[-30:])


def test_page_assignment_is_first_tokens_page():
    a = "word " * 400
    b = "term " * 400
    chunks = chunk_text([(1, a), (2, b)], chunk_tokens=500, overlap_tokens=50)
    # First chunk should start on page 1, later chunks span into page 2
    assert chunks[0].page == 1
    pages = {c.page for c in chunks}
    assert pages == {1, 2}


def _reference_chunk_text(text_by_page, chunk_tokens=500, overlap_tokens=50):
    """Verbatim copy of the pre-streaming implementation (F-03).

    The streaming rewrite must be output-identical to this for every input;
    keeping the old code here pins that rather than pasting a frozen literal.
    """
    from lib.chunking import _ENCODING, Chunk

    tokens = []
    page_of_token = []
    for page, text in text_by_page:
        page_tokens = _ENCODING.encode(text)
        tokens.extend(page_tokens)
        page_of_token.extend([page] * len(page_tokens))
    if not tokens:
        return []

    stride = chunk_tokens - overlap_tokens
    chunks = []
    start = 0
    idx = 0
    while start < len(tokens):
        end = min(start + chunk_tokens, len(tokens))
        text = _ENCODING.decode(tokens[start:end])
        chunks.append(Chunk(text=text, page=page_of_token[start], chunk_idx=idx))
        idx += 1
        if end == len(tokens):
            break
        start += stride
    return chunks


@pytest.mark.parametrize(
    "pages",
    [
        [(1, "A short sentence about joins.")],
        [(1, "word " * 400), (2, "term " * 400)],
        [(1, "alpha " * 1500)],
        # Exactly two full chunks' worth of stride: exercises the "previous
        # chunk already ended at the last token" tail case.
        [(1, "beta " * 450), (2, "beta " * 50)],
        [(1, ""), (2, "gamma " * 700), (3, "")],
        [(None, "plaintext " * 1200)],
        [(1, "")],
    ],
)
def test_streaming_chunker_matches_reference(pages):
    got = chunk_text(pages)
    want = _reference_chunk_text(pages)
    assert [(c.text, c.page, c.chunk_idx) for c in got] == [
        (c.text, c.page, c.chunk_idx) for c in want
    ]


def test_max_chunks_raises_before_tokenising_the_rest():
    """F-03: an oversized document must abort mid-stream, not materialise every
    chunk first and then fail the cap check."""
    pages = [(1, "delta " * 3000)]
    # Unbounded run establishes the input really does exceed the cap.
    assert len(chunk_text(pages)) > 3
    with pytest.raises(chunking.ChunkLimitExceeded):
        chunk_text(pages, max_chunks=3)


def test_max_chunks_none_and_under_cap_are_unaffected():
    pages = [(1, "epsilon " * 200)]
    assert chunk_text(pages, max_chunks=None) == chunk_text(pages)
    assert chunk_text(pages, max_chunks=50) == chunk_text(pages)
