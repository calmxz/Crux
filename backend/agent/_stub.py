"""Deterministic tutor reply for stub mode, used in e2e and offline dev.

The stub provider (services/llm.py StubProvider) streams this text in place
of a model reply, so tests do not depend on network or model availability.

Output format is a stable, parseable marker the e2e suite asserts against:
- "[STUB:fresh] Echo: <last_user_message>"        when no prior-session summary
- "[STUB:resumed:<hash8>] Echo: <last_user_msg>"  when summary present

The summary is read from the rendered system prompt on purpose: the e2e
`[STUB:resumed:` assertion proves the summary reached the assembled prompt.
"""

import hashlib
import re

from agent.prompts import LAST_SESSION_SUMMARY_LABEL

_SUMMARY_LINE = re.compile(rf"^{re.escape(LAST_SESSION_SUMMARY_LABEL)}:(.*)$", re.MULTILINE)


def _last_user_message(messages: list[dict]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content")
            if isinstance(content, str):
                return content.strip()
    return ""


def _extract_summary(system_prompt: str) -> str | None:
    match = _SUMMARY_LINE.search(system_prompt or "")
    if not match:
        return None
    raw = match.group(1).strip()
    if not raw or raw.lower() == "none":
        return None
    return raw


def stub_response(messages: list[dict], system_prompt: str) -> str:
    summary = _extract_summary(system_prompt)
    last_user = _last_user_message(messages) or "(empty)"
    if summary:
        digest = hashlib.sha256(summary.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
        return f"[STUB:resumed:{digest}] Echo: {last_user}"
    return f"[STUB:fresh] Echo: {last_user}"


def chunk_text(text: str, parts: int = 3) -> list[str]:
    """Split text into ~`parts` word-boundary chunks, so stub streaming still
    exercises the delta path."""
    words = text.split(" ")
    if len(words) <= 1:
        return [text]
    parts = max(1, min(parts, len(words)))
    size = -(-len(words) // parts)  # ceil division
    out: list[str] = []
    for i in range(0, len(words), size):
        group = words[i : i + size]
        sep = " " if (i + size) < len(words) else ""
        out.append(" ".join(group) + sep)
    return out
