"""make_prompt_state: a PromptState for renderer tests (#395).

Defaults are the values the renderer used to fall back to for a missing dict
key, so a test overrides only what it asserts on. `profile` may be a plain
dict (including legacy string-element lists); the renderer accepts either.
"""

from contracts import TopicProfile
from services.prompt_state import PromptState, SessionPromptInputs

_DEFAULTS = {
    "topic": "",
    "profile": {},
    "ingestion_status": None,
    "retrieval_required": False,
    "diagnostic_required": False,
    "diagnostic_accepted": False,
    "seed_mode": None,
    "last_session_summary": None,
    "rolling_summary": None,
    "pending_check": None,
    "current_check": None,
    "quiz_cooldown": None,
    "gap_accuracy": {},
    "learner_prefs": {},
    "topic_suggest_state": None,
    "review_gaps_target": None,
    "review_gaps_retention": False,
    "prefetched_excerpts": [],
}


def make_prompt_state(**overrides) -> PromptState:
    return PromptState(**{**_DEFAULTS, **overrides})


def make_session_inputs(**overrides) -> SessionPromptInputs:
    """Session inputs for prompt_state.assemble tests."""
    defaults = {
        "topic": "",
        "profile": TopicProfile(),
        "ingestion_status": None,
        "learner_prefs": {},
        "rolling_summary": None,
        "pending_check": None,
        "current_check": None,
        "quiz_cooldown": None,
        "gap_accuracy": {},
        "topic_suggest_state": None,
    }
    return SessionPromptInputs(**{**defaults, **overrides})
