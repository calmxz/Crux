"""The update_topic_profile parameter schema must not contradict the service.

profile_service.apply_patch rejects a knowledge_level or subtopic_level change without
evidence_type declared/tested (F-39). The schema description the LLM sees is
generated from docs/api/openapi.yaml; if it claims evidence_type is only
needed for add_mastered_concept, the model omits it on level-only patches,
the write silently fails, and the diagnostic offer repeats every turn.
"""

from agent.tools import TOOLS


def _update_profile_fn():
    return next(t["function"] for t in TOOLS if t["function"]["name"] == "update_topic_profile")


def test_schema_description_states_level_needs_evidence():
    params = _update_profile_fn()["parameters"]
    desc = params.get("description") or ""
    # Whitespace-normalized: the YAML block wraps the sentence across lines.
    flat = " ".join(desc.split())
    assert (
        "required whenever `knowledge_level`, `add_mastered_concept` or "
        "`subtopic_level` is present" in flat
    ), desc
