"""Refusals raised by the LLM adapter (services/llm.py) before the model is
called. A leaf module so services/cost_meter.py can re-parent its
CostCapExceeded here without importing the adapter (which imports it)."""

from lib.error_codes import LLM_UNAVAILABLE


class CallRefused(Exception):
    """The adapter refused the call; the model was not called. Callers catch
    this base class and report `code`; `cap` is set only for a cost cap."""

    code: str
    cap = None


class LlmUnavailable(CallRefused):
    """No provider can serve the call (raised by the stub provider, #413)."""

    code = LLM_UNAVAILABLE
