"""Deterministic LLM stub used in e2e and offline dev.

Activated when settings.llm_stub_enabled is True. Bypasses LiteLLM and tools
entirely so tests do not depend on network or model availability.

Output format is a stable, parseable marker the e2e suite asserts against:
- "[STUB:fresh] Echo: <last_user_message>"        when no prior-session summary
- "[STUB:resumed:<hash8>] Echo: <last_user_msg>"  when summary present
"""

import hashlib
import re

_SUMMARY_LINE = re.compile(r"^LAST_SESSION_SUMMARY:(.*)$", re.MULTILINE)


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
