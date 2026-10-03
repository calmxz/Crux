# backend/tests/test_token_budget.py
"""P2 AC4: fixture-based token-budget tripwire.

Assembles a canonical 3-turn conversation with a superseded and a current
retrieval through the REAL truncation/pruning helpers and asserts the token
total stays under TOKEN_BUDGET. The budget is a measured baseline plus
slack, not a spec number -- its job is to break loudly if prompt/window
assembly regresses (e.g. someone removes truncation or starts resending
full excerpts).
"""
import json

import litellm

from agent import context_budget, prompts
from config import settings

# Set in Step 2 from the measured baseline (printed value * 1.10, rounded up
# to the nearest 100). Do not raise casually: an increase here means every
# turn got more expensive.
# Re-baselined 2026-07-30 (smart-start Task 4): IMMUTABLE_RULES grew by the
# DIAGNOSTIC ACCEPTED bullet (spec-required). Measured 6829 -> 6829*1.10 ->
# 7600.
# Re-baselined 2026-09-24 (#340 check sets): IMMUTABLE_RULES grew by the set
# rules, the between-sets continuation, the learner-stop and ask-why-once
# POST-QUIZ bullets, and the 3-sets diagnostic (all spec-required, #339
# resolution). Measured 7873 -> 7873*1.10 -> 8700.
# Re-baselined 2026-09-25 (#354 topic card): IMMUTABLE_RULES grew by the
# TOPIC SUGGESTIONS block and the LEVEL WORDING / clarify-when-unsure rule
# (spec-required and owner-requested), plus the TOPIC_SUGGEST context line.
# Measured 8741 in CI -> 8741*1.10 -> 9700.
TOKEN_BUDGET = 9700


def _assembled_turn():
    state = {
        "topic": "photosynthesis",
        "profile": {"knowledge_level": "beginner", "confirmed_gaps": ["light reactions"]},
        "ingestion_status": "ready",
        "retrieval_required": True,
    }
    system_prompt = prompts.build_system_prompt(state)
    long_answer = "The light-dependent reactions occur in the thylakoid membrane. " * 150
    history = [
        {"role": "user", "content": "What is photosynthesis?"},
        {"role": "assistant", "content": long_answer},
        {"role": "user", "content": "Where do the light reactions happen?"},
        {"role": "assistant", "content": long_answer},
    ]
    messages = [
        {"role": m["role"], "content": context_budget.truncate_message(m["content"])}
        for m in history
    ]
    messages.append({"role": "user", "content": "Quiz me on the Calvin cycle."})
    chunk_text = "Chunk sentence about the Calvin cycle and carbon fixation. " * 40
    chunks = [
        {"doc_id": f"d{i}", "doc_name": "bio-notes.pdf",
         "text": f"<document_excerpt id='d{i}'>{chunk_text}</document_excerpt>"}
        for i in range(5)
    ]
    full = [{"role": "system", "content": system_prompt}] + messages
    # Round 1: an older retrieval that pruning must stub as superseded.
    full.append({
        "role": "assistant", "content": None,
        "tool_calls": [{"id": "c1", "type": "function",
                        "function": {"name": "retrieve_chunks", "arguments": "{}"}}],
    })
    full.append({
        "role": "tool", "tool_call_id": "c1", "name": "retrieve_chunks",
        "content": json.dumps({"status": "ok", "data": {"chunks": chunks}}),
    })
    # Round 2: the current retrieval that pruning must keep intact.
    full.append({
        "role": "assistant", "content": None,
        "tool_calls": [{"id": "c2", "type": "function",
                        "function": {"name": "retrieve_chunks", "arguments": "{}"}}],
    })
    full.append({
        "role": "tool", "tool_call_id": "c2", "name": "retrieve_chunks",
        "content": json.dumps({"status": "ok", "data": {"chunks": chunks}}),
    })
    context_budget.prune_superseded_excerpts(full)
    return full


def test_canonical_turn_stays_under_token_budget():
    full = _assembled_turn()
    total = litellm.token_counter(model=settings.model, messages=full)
    print(f"measured canonical-turn tokens: {total}")
    assert 0 < total <= TOKEN_BUDGET, (
        f"canonical turn measured {total} tokens against budget {TOKEN_BUDGET}; "
        "if this is an intentional prompt/window change, re-baseline the budget "
        "constant with the same *1.10 slack rule and record why in the commit."
    )
