"""Bounded exponential-backoff retry for idempotent LiteLLM calls.

Only the retrieve tool's _embed_query still uses this; #412 moves it onto
the LLM adapter (services/llm.py), which has its own retry, and deletes it.

Retries only provider/transport faults that are transient by nature.
Anything else (bad request, auth, context window, our own ValueError) is
raised immediately. Delays: base, 2*base, 4*base, ...
"""

import time
from collections.abc import Callable
from typing import TypeVar

import litellm

from config import settings

T = TypeVar("T")

RETRYABLE: tuple[type[BaseException], ...] = (
    litellm.APIConnectionError,
    litellm.Timeout,
    litellm.ServiceUnavailableError,
    litellm.InternalServerError,
    litellm.RateLimitError,
)


def retry_sync(fn: Callable[[], T]) -> T:
    attempts = max(0, settings.llm_retry_attempts)
    base = max(0.0, settings.llm_retry_base_delay_s)
    for i in range(attempts + 1):
        try:
            return fn()
        except RETRYABLE:
            if i == attempts:
                raise
            time.sleep(base * (2**i))
    raise RuntimeError("unreachable: retry_sync exited loop without returning or raising")
