"""Token-bounded chunking with page tracking (Spec §3.1, §4.2).

500 tokens per chunk with 50-token overlap (tiktoken cl100k_base). Each chunk
records the page number of its first token.
"""

from collections import deque
from dataclasses import dataclass
from itertools import islice

import tiktoken

_ENCODING = tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    text: str
    page: int
    chunk_idx: int


class ChunkLimitExceeded(Exception):
    """Raised mid-stream once the document would produce more than `limit`
    chunks (F-03). Aborting here means the remaining pages are never
    tokenised, so an oversized document cannot blow the worker's memory
    before the cap check gets a chance to reject it."""

    def __init__(self, limit: int):
        super().__init__(f"document exceeds the {limit}-chunk limit")
        self.limit = limit


def chunk_text(
    text_by_page: list[tuple[int, str]],
    chunk_tokens: int = 500,
    overlap_tokens: int = 50,
    max_chunks: int | None = None,
) -> list[Chunk]:
    """Stream text_by_page into overlapping token-bounded chunks.

    F-03: one page is tokenised at a time and only a rolling window of
    chunk_tokens is held, instead of flattening the whole document into one
    token list up front. Output is identical to the pre-streaming version:
    a chunk's page is the page of its first token, and the trailing partial
    chunk is emitted only when the previous chunk did not already end on the
    last token (buffer longer than the overlap it carried over).
    """
    if chunk_tokens <= 0:
        raise ValueError("chunk_tokens must be positive")
    if overlap_tokens < 0 or overlap_tokens >= chunk_tokens:
        raise ValueError("overlap_tokens must be in [0, chunk_tokens)")

    stride = chunk_tokens - overlap_tokens
    chunks: list[Chunk] = []
    buf: deque[int] = deque()
    buf_pages: deque[int | None] = deque()

    def _emit(size: int) -> None:
        if max_chunks is not None and len(chunks) >= max_chunks:
            raise ChunkLimitExceeded(max_chunks)
        chunks.append(
            Chunk(
                text=_ENCODING.decode(list(islice(buf, 0, size))),
                page=buf_pages[0],
                chunk_idx=len(chunks),
            )
        )

    for page, text in text_by_page:
        page_tokens = _ENCODING.encode(text)
        buf.extend(page_tokens)
        buf_pages.extend([page] * len(page_tokens))
        while len(buf) >= chunk_tokens:
            _emit(chunk_tokens)
            for _ in range(stride):
                buf.popleft()
                buf_pages.popleft()

    if buf and (not chunks or len(buf) > overlap_tokens):
        _emit(len(buf))
    return chunks
