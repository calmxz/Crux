"""TDD: diagnostic_accepted flag -> DIAGNOSTIC: ACCEPTED prompt state."""

from agent import prompts
from contracts import ConceptEntry, TopicProfile
from services import prompt_state
from tests.prompt_state_factory import make_prompt_state, make_session_inputs


def _state(profile, *, accepted, review_gaps=False):
    return prompt_state.assemble(
        make_session_inputs(topic="glycolysis", profile=profile, ingestion_status="none"),
        prompt_state.TurnInputs(
            retrieval_required=False, review_gaps=review_gaps, diagnostic_accepted=accepted
        ),
    )


def test_accepted_flag_set_when_level_unknown():
    state = _state(TopicProfile(), accepted=True)
    assert state.diagnostic_required is True
    assert state.diagnostic_accepted is True


def test_accepted_ignored_when_level_known():
    state = _state(TopicProfile(knowledge_level="beginner"), accepted=True)
    assert state.diagnostic_required is False
    assert state.diagnostic_accepted is False


def test_review_gaps_wins_over_accepted():
    profile = TopicProfile(confirmed_gaps=[ConceptEntry(name="ATP yield")])
    state = _state(profile, accepted=True, review_gaps=True)
    assert state.diagnostic_required is False
    assert state.diagnostic_accepted is False


def test_prompt_renders_accepted_label():
    ctx = prompts.build_dynamic_context(
        make_prompt_state(
            topic="t", profile=TopicProfile(), diagnostic_required=True, diagnostic_accepted=True
        )
    )
    assert "DIAGNOSTIC: ACCEPTED" in ctx


def test_prompt_renders_required_without_flag():
    ctx = prompts.build_dynamic_context(
        make_prompt_state(topic="t", profile=TopicProfile(), diagnostic_required=True)
    )
    assert "DIAGNOSTIC: REQUIRED" in ctx


def test_immutable_rules_mention_accepted():
    assert "DIAGNOSTIC is ACCEPTED" in prompts.IMMUTABLE_RULES
