// Backend error codes the frontend handles: a subset of the `x-error-codes`
// block in docs/api/openapi.yaml (the full list). errorCodes.test.js fails if
// a value here is not listed there.
export const ERR_DAILY_CAP_REACHED = 'daily_cap_reached'

export const ERR_DAILY_COST_CAP_REACHED = 'daily_cost_cap_reached'

// Copy: "The service has reached its daily budget. Please try again tomorrow."
export const ERR_GLOBAL_COST_CAP_REACHED = 'global_cost_cap_reached'

// Copy: "This document is too large to ingest. Try splitting it into smaller files."
export const ERR_CHUNK_LIMIT_EXCEEDED = 'chunk_limit_exceeded'

// Velocity (burst) limiter, see backend/services/velocity_limit.py.
// Copy: "Too many requests - wait a moment and retry."
export const ERR_TOO_MANY_REQUESTS = 'too_many_requests'

// Copy: "This document has too many pages to ingest. Try splitting it into smaller files."
export const ERR_PAGE_LIMIT_EXCEEDED = 'page_limit_exceeded'

// 422 from backend/routes/chat.py - the message was blank after trimming.
export const ERR_EMPTY_MESSAGE = 'empty_message'

// 422 from backend/routes/sessions.py (create + rename).
export const ERR_EMPTY_TOPIC = 'empty_topic'

// 413 from backend/lib/body_limit.py; the envelope also carries max_bytes.
export const ERR_BODY_TOO_LARGE = 'body_too_large'

// 409 from routes/chat.py, routes/sessions.py, routes/upload.py - the session
// was ended (possibly in another tab) before this action reached the server.
export const ERR_SESSION_ENDED = 'session_ended'

// 409 from backend/routes/sessions.py (create, reopen, rename); the envelope
// also carries the open session's session_id.
export const ERR_DUPLICATE_TOPIC = 'duplicate_topic'

// G-04: coarse tool-dispatch failure. Arrives as `tool_call_done.error`, not
// as an SSE `error` event code.
export const ERR_TOOL_FAILED = 'tool_failed'

// SSE `error` event: the LLM call failed mid-turn; the partial reply is kept.
export const ERR_LLM_FAILED = 'llm_failed'

// SSE `error` event: the tutor ran out of tool-loop iterations; the partial
// reply is kept. Retrying the same question tends to hit the same limit.
export const ERR_MAX_ITERS_REACHED = 'max_iters_reached'
