import { parseSSEStream } from '@/lib/sseParser.js'
import {
  ApiError,
  _onAuthExpired,
  _refreshAccessToken,
  getFreshAccessToken,
  invalidateGetCache,
} from './apiClient.js'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

// F-06: bound time-to-headers and inter-event silence, NOT total stream
// duration -- multi-tool turns legitimately run long, and the backend's
// per-iteration llm_timeout_s bounds each silent gap well under 60s.
export const SSE_HEADER_TIMEOUT_MS = 30000

export const SSE_IDLE_TIMEOUT_MS = 60000

function _timeoutError() {
  return new DOMException('timed out', 'TimeoutError')
}

async function _fetchSse(url, payload, { onEvent, signal, path }, _retried = false) {
  const headers = { 'content-type': 'application/json' }
  const token = _retried ? await _refreshAccessToken() : await getFreshAccessToken()

  if (token) headers['authorization'] = `Bearer ${token}`

  // Internal controller: layers the header/idle timeouts on top of whatever
  // signal the caller passed in (e.g. the "stop" button), without mutating
  // or replacing the caller's own AbortController.
  const ctrl = new AbortController()

  if (signal) {
    if (signal.aborted) ctrl.abort(signal.reason)
    else signal.addEventListener('abort', () => ctrl.abort(signal.reason), { once: true })
  }

  // Race the fetch against an explicit timeout promise rather than relying
  // solely on the abort signal reaching fetch -- guarantees the 30s cap
  // fires even against fetch implementations/mocks that don't act on abort.
  let headerTimer

  const headerTimeout = new Promise((_, reject) => {
    headerTimer = setTimeout(() => {
      ctrl.abort(_timeoutError())
      reject(new ApiError(0, { detail: 'request timed out' }, path))
    }, SSE_HEADER_TIMEOUT_MS)
  })

  let resp

  try {
    // Race the ORIGINAL fetch promise, not a .catch()-wrapped copy (that
    // would return a new promise and leave this one un-raced). When the
    // timeout wins, ctrl.abort() below makes the real fetch eventually
    // reject with AbortError; nothing else observes that rejection since
    // the race already settled, which would surface as an unhandled
    // promise rejection in production. Attach a no-op handler to the same
    // promise object so its eventual rejection is observed either way.
    const fetchPromise = fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      signal: ctrl.signal,
    })

    fetchPromise.catch(() => {})
    resp = await Promise.race([fetchPromise, headerTimeout])
  } catch (e) {
    if (e instanceof ApiError) throw e

    if (e?.name === 'TimeoutError') throw new ApiError(0, { detail: 'request timed out' }, path)
    throw e instanceof TypeError ? new ApiError(0, { detail: e.message }, path) : e
  } finally {
    clearTimeout(headerTimer)
  }

  if (!resp.ok) {
    if (resp.status === 401 && !_retried) {
      // F-09: refresh-then-retry once. Safe pre-stream: no SSE bytes have
      // been consumed yet, so the whole POST can simply be re-issued.
      return _fetchSse(url, payload, { onEvent, signal, path }, true)
    }

    if (resp.status === 401) await _onAuthExpired()
    const text = await resp.text().catch(() => '')
    let body

    try {
      body = text ? JSON.parse(text) : null
    } catch {
      body = text
    }

    throw new ApiError(resp.status, body, path)
  }

  const timedOut = () => ctrl.signal.aborted && ctrl.signal.reason?.name === 'TimeoutError'

  let idleTimer = setTimeout(() => ctrl.abort(_timeoutError()), SSE_IDLE_TIMEOUT_MS)

  const wrappedOnEvent = (evt) => {
    clearTimeout(idleTimer)
    idleTimer = setTimeout(() => ctrl.abort(_timeoutError()), SSE_IDLE_TIMEOUT_MS)
    onEvent(evt)
  }

  try {
    await parseSSEStream(resp.body, wrappedOnEvent, { signal: ctrl.signal })
  } catch (e) {
    if (timedOut()) throw new ApiError(0, { detail: 'stream timed out' }, path)

    // Not a timeout: if the internal controller was aborted, it's because the
    // caller's own signal aborted (a mid-stream user cancel). sseParser's
    // reader.cancel() resolves the pending read() with {done: true} and then
    // throws a GENERIC Error('aborted') -- not the original AbortError -- so
    // normalize back to the caller's abort reason here rather than leaking
    // that generic Error past the AbortError contract callers rely on.
    if (ctrl.signal.aborted) {
      const reason = ctrl.signal.reason
      throw reason?.name === 'AbortError' ? reason : new DOMException('aborted', 'AbortError')
    }

    // E-02: a connection that dies mid-body rejects the read with a bare
    // TypeError ("network error"). Normalize it the same way the header phase
    // does (see :61) so callers get the status-0 ApiError contract instead of
    // a raw TypeError that friendlyError can only render as its own message.
    throw e instanceof TypeError ? new ApiError(0, { detail: e.message }, path) : e
  } finally {
    clearTimeout(idleTimer)
  }
}

export async function streamChat({
  sessionId,
  message,
  reviewGaps = false,
  reviewGap = null,
  diagnosticAccepted = false,
  onEvent,
  signal,
}) {
  const payload = { session_id: sessionId, message, review_gaps: reviewGaps }

  if (reviewGap) payload.review_gap = reviewGap

  if (diagnosticAccepted) payload.diagnostic_accepted = true

  try {
    await _fetchSse(`${BASE_URL}/chat/stream`, payload, { onEvent, signal, path: '/chat/stream' })
  } finally {
    // Raw fetch bypasses request(), so the session tree (messages, profile,
    // pending check) must be dropped from the GET cache here, success or not.
    invalidateGetCache(`/sessions/${sessionId}`)
  }
}

export async function streamCheckComplete({ sessionId, onEvent, signal }) {
  try {
    await _fetchSse(
      `${BASE_URL}/sessions/${sessionId}/check/complete`,
      {},
      { onEvent, signal, path: '/check/complete' },
    )
  } finally {
    invalidateGetCache(`/sessions/${sessionId}`)
  }
}

// #340 Stop button: end the check early; streams the same follow-up
// vocabulary as streamCheckComplete.
export async function streamCheckStop({ sessionId, onEvent, signal }) {
  try {
    await _fetchSse(
      `${BASE_URL}/sessions/${sessionId}/check/stop`,
      {},
      { onEvent, signal, path: '/check/stop' },
    )
  } finally {
    invalidateGetCache(`/sessions/${sessionId}`)
  }
}
