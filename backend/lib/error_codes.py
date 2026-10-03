"""Error-code strings carried inside HTTPException `detail.code`.

Kept in sync with frontend/src/lib/errorCodes.js so a typo on either side
fails loudly instead of silently mis-routing UI behaviour (cap banner,
toast copy).
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
