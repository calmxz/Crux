"""Every error code the backend sends (#464).

Each constant is a `code` carried in an HTTPException `detail.code`, an SSE
`error` event, or (TOOL_FAILED only) a `tool_call_done.error`. The list's home
is the `x-error-codes` block in docs/api/openapi.yaml; tests/test_error_codes.py
fails if this module and that block differ, or if backend code spells a code
inline instead of using a constant here. Spellings are API: do not rename.
"""

DAILY_CAP_REACHED = "daily_cap_reached"
DAILY_COST_CAP_REACHED = "daily_cost_cap_reached"
GLOBAL_COST_CAP_REACHED = "global_cost_cap_reached"
CHUNK_LIMIT_EXCEEDED = "chunk_limit_exceeded"
TOO_MANY_REQUESTS = "too_many_requests"
# Upload-time page-count gate (PDF/PPTX), see routes/upload.py.
PAGE_LIMIT_EXCEEDED = "page_limit_exceeded"
# G-04: coarse tool-dispatch failure handed to the LLM. The real exception
# text stays in the server WARNING log.
TOOL_FAILED = "tool_failed"

# Request guards.
SESSION_ENDED = "session_ended"
EMPTY_MESSAGE = "empty_message"
EMPTY_TOPIC = "empty_topic"
BODY_TOO_LARGE = "body_too_large"
DUPLICATE_TOPIC = "duplicate_topic"

# Check-question routes.
CHECK_CONFLICT = "check_conflict"
NO_RESOLVED_BATCH = "no_resolved_batch"
NO_OPEN_CHECK = "no_open_check"

# Upload intake. UPPERCASE for historical reasons; renaming changes the API.
FILE_TOO_LARGE = "FILE_TOO_LARGE"
UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
INVALID_FILENAME = "INVALID_FILENAME"
CONTENT_TYPE_MISMATCH = "CONTENT_TYPE_MISMATCH"
STORAGE_WRITE_FAILED = "STORAGE_WRITE_FAILED"

# lib/error_handlers.py.
INTERNAL_ERROR = "internal_error"
INVALID_VALUE = "invalid_value"

# Tutor stream (SSE `error` event).
MAX_ITERS_REACHED = "max_iters_reached"
LLM_FAILED = "llm_failed"
