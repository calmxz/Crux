import {
  ERR_DAILY_CAP_REACHED,
  ERR_DAILY_COST_CAP_REACHED,
  ERR_GLOBAL_COST_CAP_REACHED,
  ERR_CHUNK_LIMIT_EXCEEDED,
  ERR_TOO_MANY_REQUESTS,
  ERR_PAGE_LIMIT_EXCEEDED,
  ERR_EMPTY_MESSAGE,
  ERR_EMPTY_TOPIC,
  ERR_BODY_TOO_LARGE,
  ERR_SESSION_ENDED,
  ERR_TOOL_FAILED,
} from './errorCodes.js'

const DAILY_LIMIT_COPY = "You've hit the daily limit. Try again tomorrow."

const THROTTLED_COPY = 'Too many requests - wait a moment and retry.'

// Shared with the session store's own 409 handling so the two cannot drift.
export const SESSION_ENDED_COPY = 'This session was ended elsewhere. Reopen it to continue.'

// Last resort for an SSE `error` event with neither a known code nor a message.
export const GENERIC_STREAM_ERROR_COPY = 'The tutor hit a problem. Please try again.'

// Code-first copy. Any backend detail.code listed here wins over the
// status-based fallback below, so a new code only needs one entry.
const CODE_COPY = {
  [ERR_DAILY_CAP_REACHED]: DAILY_LIMIT_COPY,
  [ERR_DAILY_COST_CAP_REACHED]: DAILY_LIMIT_COPY,
  [ERR_GLOBAL_COST_CAP_REACHED]:
    'The service has reached its daily budget. Please try again tomorrow.',
  [ERR_CHUNK_LIMIT_EXCEEDED]:
    'This document is too large to ingest. Try splitting it into smaller files.',
  [ERR_TOO_MANY_REQUESTS]: THROTTLED_COPY,
  [ERR_PAGE_LIMIT_EXCEEDED]:
    'This document has too many pages to ingest. Try splitting it into smaller files.',
  [ERR_EMPTY_MESSAGE]: 'Type a message before sending.',
  [ERR_EMPTY_TOPIC]: 'Enter a topic to continue.',
  [ERR_BODY_TOO_LARGE]: 'That is too much text to send at once. Shorten it and try again.',
  [ERR_SESSION_ENDED]: SESSION_ENDED_COPY,
  [ERR_TOOL_FAILED]: 'The tutor could not finish that step. Try again.',
}

// Copy for an SSE `error` event payload ({ code, message }). Code-first so the
// two stream loops in stores/session.js render the same sentence for the same
// code; `message` is backend prose and only a fallback for an unknown code.
export function sseErrorCopy(data) {
  const code = data && typeof data === 'object' ? data.code : null

  if (typeof code === 'string' && Object.hasOwn(CODE_COPY, code)) return CODE_COPY[code]
  const message = data && typeof data === 'object' ? data.message : null

  if (typeof message === 'string' && message) return message

  return GENERIC_STREAM_ERROR_COPY
}

// Maps ApiError instances (and plain Errors) to user-facing copy.
// Use in any error banner so we stop leaking raw `API <status> /path: <json>`.
export function friendlyError(err) {
  if (!err) return ''
  const code = err?.body?.detail?.code

  if (typeof code === 'string' && Object.hasOwn(CODE_COPY, code)) return CODE_COPY[code]
  const status = typeof err === 'object' ? err.status : null

  if (status === 0) return "Can't reach the server. Check your connection and try again."

  if (status === 401 || status === 403) return "You're not signed in for this action."

  if (status === 404) return "We couldn't find that resource."

  if (status === 429) {
    // I-04: nginx's per-IP throttle also 429s but with a non-JSON body (no
    // detail.code). Only a coded envelope is the daily cap.
    if (err?.body?.detail?.code) return DAILY_LIMIT_COPY

    return THROTTLED_COPY
  }

  if (status === 503) return 'The tutor is temporarily unavailable. Try again in a moment.'

  if (typeof status === 'number' && status >= 500)
    return 'Something went wrong on our side. Try again shortly.'

  if (typeof status === 'number' && status >= 400)
    return 'That request was rejected. Check the details and try again.'

  if (err instanceof Error) return err.message

  return String(err)
}

// The server refused an action because the session was ended elsewhere.
export function isSessionEndedError(err) {
  return err?.status === 409 && err?.body?.detail?.code === ERR_SESSION_ENDED
}

// Thrown by the session store when a send-stream is aborted for a reason the
// view must react to (restore the draft) rather than silently swallow.
export class StreamAbortedError extends Error {
  constructor(reason, cause) {
    super(`stream aborted: ${reason}`)
    this.name = 'StreamAbortedError'
    this.reason = reason
    this.cause = cause
  }
}
