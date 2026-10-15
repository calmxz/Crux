"""Refusals raised by the LLM adapter (services/llm.py) before the model is
called. A leaf module so services/cost_meter.py can re-parent its
CostCapExceeded here without importing the adapter (which imports it)."""


class CallRefused(Exception):
    """The adapter refused the call; the model was not called. Callers catch
    this base class."""


class LlmUnavailable(CallRefused):
    """No provider can serve the call (raised by the stub provider, #413)."""
