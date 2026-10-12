"""context_budget: char-based token-volume controls (roadmap P2).

Char-based on purpose: deterministic, no tokenizer in the billed turn path,
model-independent tests. 6000 chars approximates a 1.5k-token cap at ~4
chars/token.
"""

import json

from agent.context_budget import (
    MAX_MESSAGE_CHARS,
    TRUNCATION_MARKER,
    prune_superseded_excerpts,
    truncate_message,
)


def test_short_content_unchanged():
    assert truncate_message("hello") == "hello"


def test_content_at_cap_unchanged():
    s = "x" * MAX_MESSAGE_CHARS
    assert truncate_message(s) == s


def test_content_over_cap_truncated_to_cap_with_marker():
    s = "H" * 5000 + "T" * 5000
    out = truncate_message(s)
    assert len(out) == MAX_MESSAGE_CHARS
    assert TRUNCATION_MARKER in out
    assert out.startswith("H")
    assert out.endswith("T")


def test_head_tail_split_preserves_both_ends():
    s = "".join(str(i % 10) for i in range(20000))
    out = truncate_message(s, max_chars=1000)
    head, tail = out.split(TRUNCATION_MARKER)
    assert s.startswith(head)
    assert s.endswith(tail)
    assert len(head) > len(tail) > 0


def test_none_and_empty_are_safe():
    assert truncate_message(None) is None
    assert truncate_message("") == ""


def _tool_msg(call_id, chunks):
    payload = {"status": "ok", "data": {"chunks": chunks}}
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "name": "retrieve_chunks",
        "content": json.dumps(payload),
    }


def _chunk(doc_id, doc_name, text):
    return {
        "doc_id": doc_id,
        "doc_name": doc_name,
        "text": f"<document_excerpt id='{doc_id}'>{text}</document_excerpt>",
    }


def test_older_retrieval_stubbed_newest_kept():
    older = _tool_msg("c1", [_chunk("d1", "notes.pdf", "old material")])
    newer = _tool_msg("c2", [_chunk("d2", "slides.pdf", "new material")])
    msgs = [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": "q"},
        {"role": "assistant", "content": None, "tool_calls": []},
        older,
        {"role": "assistant", "content": None, "tool_calls": []},
        newer,
    ]
    prune_superseded_excerpts(msgs)
    assert "old material" not in msgs[3]["content"]
    assert msgs[3]["content"].startswith("[superseded retrieval:")
    assert "d1" in msgs[3]["content"]
    assert "notes.pdf" in msgs[3]["content"]
    # Transport fields intact so the transcript stays LiteLLM-valid.
    assert msgs[3]["role"] == "tool"
    assert msgs[3]["tool_call_id"] == "c1"
    assert msgs[3]["name"] == "retrieve_chunks"
    # Newest retrieval untouched.
    assert "new material" in msgs[5]["content"]


def test_single_retrieval_is_noop():
    only = _tool_msg("c1", [_chunk("d1", "notes.pdf", "material")])
    msgs = [{"role": "user", "content": "q"}, only]
    before = json.loads(json.dumps(msgs))
    prune_superseded_excerpts(msgs)
    assert msgs == before


def test_non_retrieval_tool_messages_untouched():
    profile_tool = {
        "role": "tool",
        "tool_call_id": "c0",
        "name": "update_topic_profile",
        "content": json.dumps({"status": "ok", "data": {}}),
    }
    older = _tool_msg("c1", [_chunk("d1", "a.pdf", "one")])
    newer = _tool_msg("c2", [_chunk("d2", "b.pdf", "two")])
    msgs = [profile_tool, older, newer]
    prune_superseded_excerpts(msgs)
    assert msgs[0]["content"] == json.dumps({"status": "ok", "data": {}})
    assert msgs[1]["content"].startswith("[superseded retrieval:")


def make_carrier(doc_id):
    return _tool_msg(f"call-{doc_id}", [_chunk(doc_id, f"{doc_id}.pdf", f"material {doc_id}")])


def test_sibling_retrievals_same_round_both_survive():
    messages = [
        {"role": "assistant", "content": "", "tool_calls": [{"id": "a"}, {"id": "b"}]},
        make_carrier(doc_id="d1"),  # sibling 1, round 0
        make_carrier(doc_id="d2"),  # sibling 2, same round
    ]
    prune_superseded_excerpts(messages)
    assert "<document_excerpt" in messages[1]["content"]
    assert "<document_excerpt" in messages[2]["content"]


def test_older_round_stubbed_newer_round_kept():
    messages = [
        {"role": "assistant", "content": "", "tool_calls": [{"id": "a"}]},
        make_carrier(doc_id="d1"),  # round 0 -> stub
        {"role": "assistant", "content": "", "tool_calls": [{"id": "b"}]},
        make_carrier(doc_id="d2"),  # round 2 -> keep
    ]
    prune_superseded_excerpts(messages)
    assert messages[1]["content"].startswith("[superseded retrieval:")
    assert "<document_excerpt" in messages[3]["content"]


def test_sibling_rounds_mixed():
    messages = [
        {"role": "assistant", "content": "", "tool_calls": [{"id": "a"}, {"id": "b"}]},
        make_carrier(doc_id="d1"),
        make_carrier(doc_id="d2"),
        {"role": "assistant", "content": "", "tool_calls": [{"id": "c"}]},
        make_carrier(doc_id="d3"),
    ]
    prune_superseded_excerpts(messages)
    assert messages[1]["content"].startswith("[superseded retrieval:")
    assert messages[2]["content"].startswith("[superseded retrieval:")
    assert "<document_excerpt" in messages[4]["content"]


def test_malformed_content_still_stubbed_without_raising():
    older = {
        "role": "tool",
        "tool_call_id": "c1",
        "name": "retrieve_chunks",
        "content": "not json <document_excerpt id='d1'>x</document_excerpt>",
    }
    newer = _tool_msg("c2", [_chunk("d2", "b.pdf", "two")])
    msgs = [older, newer]
    prune_superseded_excerpts(msgs)
    assert msgs[0]["content"].startswith("[superseded retrieval:")
    assert "<document_excerpt" not in msgs[0]["content"]
