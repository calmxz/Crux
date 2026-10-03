import { useAuthStore } from '../stores/auth.js'
import { reportCostWarning } from './costBus.js'
import { reportApiError } from './errorBus.js'

// Set VITE_API_BASE_URL in frontend/.env or frontend/.env.local to override.
// Default mirrors uploadApi.js — backend routers all mount under /api.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

// F-06: a hung backend must not spin the UI forever. 30s covers the slowest
// legitimate JSON call (end-session runs a 20s-capped summary LLM call).
export const REQUEST_TIMEOUT_MS = 30000

// F-18: a flaky link or a load balancer cycling a pod turns one GET into a red
// banner. GETs are idempotent, so retry them a bounded number of times; nothing
// else is retried (a POST could have landed before the connection dropped).
export const GET_RETRY_ATTEMPTS = 3

// Delay before attempt 2 and attempt 3. Jittered +/-20% so a backend restart
// does not get every open tab back in lockstep.
export const GET_RETRY_DELAYS_MS = [300, 900]

const RETRY_JITTER = 0.2

// Only transient upstream failures. 500 is a real bug and 429 has its own copy;
// retrying either just delays the error the user needs to see.
const RETRYABLE_STATUS = new Set([502, 503, 504])

// F-18: a short read-through cache for GETs. Several views mount at once and
// ask for the same session/profile; 5s is long enough to collapse that burst
// and short enough that no mutation of ours is invisible for a whole beat.
// An expired entry (or a `fresh: true` read) that still has a stored ETag is
// revalidated with If-None-Match rather than dropped outright -- a 304 means
// the cached body is still current and just refreshes the TTL.
export const GET_CACHE_TTL_MS = 5000

// url -> { at, value, token, etag }
const _getCache = new Map()

// Bumped by every invalidation/reset. A GET captures it before its fetch and
// skips the cache write if it moved meanwhile -- otherwise a GET that was
// already in flight when a write landed would store its stale body on settle.
let _cacheEpoch = 0

// Test hook: the Map is module state and would leak between cases.
export function _resetApiCache() {
  _getCache.clear()
  _cacheEpoch += 1
}

function _pathOfUrl(url) {
  return (url.startsWith(BASE_URL) ? url.slice(BASE_URL.length) : url).split('?')[0]
}

// Segment prefix, so `/sessions/abc` matches `/sessions/abc/end` but never
// `/sessions/abcdef`.
function _isSegmentPrefix(prefix, path) {
  if (!prefix || prefix === '/') return true

  return path === prefix || path.startsWith(prefix.endsWith('/') ? prefix : `${prefix}/`)
}

// Any write drops cached GETs on the same resource, in both directions:
// POST /sessions invalidates GET /sessions?cursor=..., and DELETE
// /sessions/abc/end invalidates GET /sessions/abc.
//
// Exported because not every write goes through request(): chatStreamService
// (SSE POST) and uploadApi.uploadDocument (multipart POST) use raw fetch and
// must invalidate the session tree themselves once their call settles.
export function invalidateGetCache(path) {
  // Unconditional, even when nothing matched: a GET that is still in flight is
  // not in the Map yet, and the epoch is what stops it writing a stale body.
  _cacheEpoch += 1
  const target = path.split('?')[0]
  // Sibling lists: POST /sessions/abc/end changes what GET /sessions/library
  // and GET /sessions return, and neither is a prefix of the other. Any write
  // under a resource root therefore also drops every cached GET under that
  // root. Coarse, but a 5 s cache gains nothing from being clever here.
  const root = `/${target.split('/').filter(Boolean)[0] ?? ''}`

  for (const url of _getCache.keys()) {
    const cached = _pathOfUrl(url)

    if (
      _isSegmentPrefix(cached, target) ||
      _isSegmentPrefix(target, cached) ||
      _isSegmentPrefix(root, cached)
    ) {
      _getCache.delete(url)
    }
  }
}

function _jittered(ms) {
  return Math.round(ms * (1 + (Math.random() * 2 - 1) * RETRY_JITTER))
}

function _isRetryableError(e) {
  // TypeError is what fetch throws for a dropped/blocked connection -- cheap to
  // re-try and usually transient. A TimeoutError is deliberately NOT retryable:
  // every attempt mints a fresh REQUEST_TIMEOUT_MS AbortSignal, so a hung (as
  // opposed to down) backend would take 30 + 0.3 + 30 + 0.9 + 30 = ~91s to
  // surface instead of 30s.
  return e instanceof TypeError || e?.name === 'TypeError'
}

// buildInit is called per attempt so each gets its own AbortSignal.timeout --
// a shared signal would already be spent when attempt 2 starts.
async function _fetchWithRetry(url, buildInit, retryable) {
  const attempts = retryable ? GET_RETRY_ATTEMPTS : 1

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (attempt > 0) {
      const delay = _jittered(GET_RETRY_DELAYS_MS[attempt - 1])
      await new Promise((r) => setTimeout(r, delay))
    }

    const last = attempt === attempts - 1

    try {
      const resp = await fetch(url, buildInit())

      if (!last && RETRYABLE_STATUS.has(resp.status)) continue

      return resp
    } catch (e) {
      // reportApiError stays in request(), so it fires once after the final
      // failure rather than once per attempt.
      if (last || !_isRetryableError(e)) throw e
    }
  }

  /* c8 ignore next -- the loop either returns or throws on the last attempt */
  throw new Error('unreachable')
}

export class ApiError extends Error {
  constructor(status, body, path) {
    super(`API ${status} ${path}: ${typeof body === 'string' ? body : JSON.stringify(body)}`)
    this.name = 'ApiError'
    this.status = status
    this.body = body
    this.path = path
  }
}

// getSession() takes a navigator.locks lock inside supabase-js, so calling it
// per request serializes otherwise-parallel fetches. Reuse the cached store
// token while its exp is comfortably in the future; anything ambiguous (no
// token, opaque token, near/past expiry) falls through to the SDK.
const TOKEN_REFRESH_MARGIN_MS = 60000

function _tokenExpMs(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))

    return typeof payload.exp === 'number' ? payload.exp * 1000 : 0
  } catch {
    return 0
  }
}

// F-47: read the token from the SDK, not the Pinia snapshot -- getSession()
// refreshes an expired token, and after wake-from-sleep the store can hold a
// stale (already-past-exp) one that would burn the single F-09 retry on a
// guaranteed 401. Falls back to the store token (tests without a supabase
// env), then null.
export async function getFreshAccessToken() {
  try {
    const cached = useAuthStore().accessToken

    if (cached && _tokenExpMs(cached) - Date.now() > TOKEN_REFRESH_MARGIN_MS) {
      return cached
    }
  } catch {
    // no active pinia -- fall through to the SDK path
  }

  try {
    const { getSupabase } = await import('./supabase.js')
    const { data } = await getSupabase().auth.getSession()
    const tok = data?.session?.access_token

    if (tok) return tok
  } catch {
    // fall through to the store snapshot
  }

  try {
    const store = useAuthStore()

    return store.accessToken ?? null
  } catch {
    return null
  }
}

// F-09: one refresh-then-retry on 401. getSession() refreshes an expired
// access token via the SDK; a second 401 means the session is truly dead --
// sign out and land on login instead of stranding a signed-in-looking UI.
export async function _refreshAccessToken() {
  try {
    const { getSupabase } = await import('./supabase.js')
    const { data } = await getSupabase().auth.getSession()

    return data?.session?.access_token ?? null
  } catch {
    return null
  }
}

// F-16: apiClient must not statically import the router -- router/index.js
// statically imports stores/auth.js and stores/user.js, and apiClient
// statically imports stores/auth.js, so a static router import here would
// close a real cycle (also made the router's own dynamic-import-based
// cycle-break ineffective, since apiClient was already in its chunk).
// main.js wires the redirect handler once at boot instead.
let _unauthorizedHandler = null

export function setUnauthorizedHandler(fn) {
  _unauthorizedHandler = fn
}

export async function _onAuthExpired() {
  // Belt to the per-entry token check in request(): nothing cached under the
  // dead session should outlive it.
  _resetApiCache()

  try {
    const store = useAuthStore()

    try {
      await store.signOut()
    } catch {
      // Supabase signOut failure must not block the local redirect.
    }
  } catch {
    // No active pinia (unit tests) -- nothing to sign out.
  }

  try {
    _unauthorizedHandler?.()
  } catch {
    // Handler unavailable / threw outside the app shell.
  }
}

async function request(
  method,
  path,
  { body, params, silent = false, headers, fresh = false } = {},
  _retried = false,
) {
  let url = `${BASE_URL}${path}`

  if (params) {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null),
    ).toString()

    if (qs) url += `?${qs}`
  }

  const isGet = method === 'GET'

  const baseHeaders = { ...headers }

  if (body !== undefined) baseHeaders['content-type'] = 'application/json'

  const token = _retried ? await _refreshAccessToken() : await getFreshAccessToken()

  if (token) baseHeaders['authorization'] = `Bearer ${token}`

  // Read the cache only after the token is known: the url alone is not a
  // sufficient key. Sign out and straight back in as someone else inside the
  // TTL and a url-keyed hit would render the previous account's data.
  //
  // A fresh-within-TTL hit (and not `fresh: true`) returns straight from
  // cache. An expired hit, or a `fresh: true` read, is instead revalidated
  // with If-None-Match when an ETag was stored -- `fresh` means "always ask
  // the server", not "always download the body". A hit under a different
  // token is dropped outright: that account's ETag must never be sent as ours.
  let revalidate = null

  if (isGet) {
    const hit = _getCache.get(url)

    if (hit && hit.token === token) {
      if (!fresh && Date.now() - hit.at < GET_CACHE_TTL_MS) return hit.value

      if (hit.etag) {
        revalidate = hit
        baseHeaders['if-none-match'] = hit.etag
      }
    } else if (hit) {
      _getCache.delete(url)
    }
  }

  const buildInit = () => {
    const init = { method, headers: { ...baseHeaders } }

    if (body !== undefined) init.body = JSON.stringify(body)

    if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
      init.signal = AbortSignal.timeout(REQUEST_TIMEOUT_MS)
    }

    return init
  }

  // Captured before the first attempt: any invalidation from here on means this
  // response is already potentially stale and must not be cached.
  const epochAtFetch = _cacheEpoch

  let resp

  try {
    resp = await _fetchWithRetry(url, buildInit, isGet)
  } catch (e) {
    if (!isGet) invalidateGetCache(path)
    const detail = e?.name === 'TimeoutError' ? 'request timed out' : e.message
    const err = new ApiError(0, { detail }, path)

    if (!silent) reportApiError(err)
    throw err
  }

  // Before the status checks: a write that 409s may still have changed state,
  // and a stale cached GET is worse than a re-fetch.
  if (!isGet) invalidateGetCache(path)

  if (resp.status === 401 && !_retried) {
    // F-09: silent first 401 -- refresh and retry once before surfacing.
    return request(method, path, { body, params, silent, headers, fresh }, true)
  }

  // F-18: a 304 only ever comes back for a GET that sent If-None-Match, i.e.
  // one with a `revalidate` entry -- the cached body is still current, so
  // return it and refresh the TTL. Skip the refresh (but still return the
  // cached body) if an invalidation landed mid-flight: the server's answer is
  // current as of its response, but extending the TTL now would hide a write
  // that happened after, or if a concurrent GET for the same url already
  // stored a newer entry (server-side writes move the body without moving the
  // epoch; the identity check keeps this 304 from overwriting that 200).
  // resp.ok is false for 304, so this must run before the resp.text() /
  // !resp.ok block below.
  if (resp.status === 304) {
    if (revalidate) {
      if (epochAtFetch === _cacheEpoch && _getCache.get(url) === revalidate) {
        _getCache.set(url, { ...revalidate, at: Date.now() })
      }

      return revalidate.value
    }
    // Nothing sent If-None-Match, so the server should not have answered 304
    // -- fall through to the generic error path below rather than guessing.
  }

  const text = await resp.text()
  const parsed = text ? safeJson(text) : null

  if (!resp.ok) {
    if (resp.status === 401 && _retried) await _onAuthExpired()
    const err = new ApiError(resp.status, parsed ?? text, path)

    if (!silent) reportApiError(err)
    throw err
  }

  const warn = resp.headers?.get?.('x-cost-warning')

  if (warn) reportCostWarning({ header: warn, path })

  // Written even for fresh: true -- the response is current either way, and a
  // poller's fresh read is exactly what a following cached read should see.
  // Skipped when an invalidation landed while this GET was in flight: the body
  // may predate the write, and a stale hit for a full TTL is worse than a miss.
  if (isGet && epochAtFetch === _cacheEpoch) {
    const etag = resp.headers?.get?.('etag') ?? null
    _getCache.set(url, { at: Date.now(), value: parsed, token, etag })
  }

  return parsed
}

function safeJson(text) {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

export const apiGet = (path, params, opts = {}) => request('GET', path, { params, ...opts })

export const apiPost = (path, body, opts = {}) => request('POST', path, { body, ...opts })

export const apiPatch = (path, body, opts = {}) => request('PATCH', path, { body, ...opts })

export const apiDelete = (path, opts = {}) => request('DELETE', path, { ...opts })
