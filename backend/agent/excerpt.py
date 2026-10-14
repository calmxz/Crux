"""Wrap retrieved chunk text in <document_excerpt> guards.

Single choke point for the prompt-injection defense declared in
prompts.py (the model is told never to follow instructions inside
document_excerpt tags). Chunk text is attacker-influenced (uploaded
documents), so any embedded document_excerpt tag sequence is neutralized
before wrapping: otherwise a literal </document_excerpt> in a PDF would
close the guard early and put the remainder of the chunk OUTSIDE it.
"""

import re

# Opening or closing document_excerpt tag, tolerant of case and whitespace.
_TAG_RE = re.compile(r"<(\s*/?\s*document_excerpt)", re.IGNORECASE)


def _neutralize(text: str) -> str:
    return _TAG_RE.sub(r"&lt;\1", text)


def wrap_untrusted(tag: str, text: str) -> str:
    """Fence learner-influenced text in <tag>...</tag> for the prompt (G-01).

    Generic sibling of wrap_chunk: any embedded opening or closing `tag`
    sequence in the text is neutralized first (case/whitespace tolerant), so
    the payload cannot close the fence early and plant instructions outside
    the guarded region. The matching rule block lives in prompts.py.
    """
    pattern = re.compile(rf"<(\s*/?\s*{re.escape(tag)})", re.IGNORECASE)
    safe = pattern.sub(r"&lt;\1", str(text))
    return f"<{tag}>{safe}</{tag}>"


def _attr(value: str) -> str:
    return value.replace("<", "").replace(">", "").replace("'", "").replace('"', "")


def wrap_chunk(ch: dict) -> str:
    doc_id = _attr(str(ch.get("doc_id", "")))
    text = _neutralize(str(ch.get("text", "")))
    return f"<document_excerpt id='{doc_id}'>{text}</document_excerpt>"
