import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  ApiError,
  apiGet,
  apiPost,
  apiPatch,
  apiDelete,
  setUnauthorizedHandler,
  _resetApiCache,
  invalidateGetCache,
  GET_RETRY_ATTEMPTS,
  GET_RETRY_DELAYS_MS,
  GET_CACHE_TTL_MS,
} from '../services/apiClient.js'
import { errorBus } from '../services/errorBus.js'
import { useAuthStore } from '../stores/auth.js'

describe('apiClient', () => {
  let listener
  let fetchMock
  let unauthorizedHandler
  beforeEach(() => {
    setActivePinia(createPinia())
    // F-18: the GET cache is module state and would leak between cases.
    _resetApiCache()
    listener = vi.fn()
    errorBus.addEventListener('api-error', listener)
    fetchMock = vi.fn()
    globalThis.fetch = fetchMock
    // F-16: apiClient no longer imports the router (see the comment on
    // setUnauthorizedHandler in apiClient.js) -- main.js wires the redirect
    // at boot, so tests supply their own handler stub.
    unauthorizedHandler = vi.fn()
    setUnauthorizedHandler(unauthorizedHandler)
  })
  afterEach(() => {
    errorBus.removeEventListener('api-error', listener)
    setUnauthorizedHandler(null)
    vi.restoreAllMocks()
  })

  function jsonResp(status, body) {
    return Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      text: () => Promise.resolve(JSON.stringify(body)),
    })
  }

  it('apiGet parses JSON on 200', async () => {
    fetchMock.mockReturnValueOnce(jsonResp(200, { ok: true }))
    const out = await apiGet('/x')
    expect(out).toEqual({ ok: true })
    expect(listener).not.toHaveBeenCalled()
  })

  it('apiGet appends query string from params', async () => {
    fetchMock.mockReturnValueOnce(jsonResp(200, []))
    await apiGet('/x', { a: 1, b: null, c: 'k' })
    const url = fetchMock.mock.calls[0][0]
    expect(url).toContain('a=1')
    expect(url).toContain('c=k')
    expect(url).not.toContain('b=')
  })

  it('apiPost sends JSON body', async () => {
    fetchMock.mockReturnValueOnce(jsonResp(201, { id: 1 }))
    await apiPost('/x', { a: 1 })
    const init = fetchMock.mock.calls[0][1]
    expect(init.method).toBe('POST')
    expect(init.headers['content-type']).toBe('application/json')
    expect(JSON.parse(init.body)).toEqual({ a: 1 })
  })

  it('throws ApiError and fires bus on non-2xx', async () => {
    fetchMock.mockReturnValueOnce(jsonResp(500, { detail: 'boom' }))
    await expect(apiGet('/x')).rejects.toBeInstanceOf(ApiError)
    expect(listener).toHaveBeenCalledTimes(1)
    expect(listener.mock.calls[0][0].detail.status).toBe(500)
  })

  it('throws ApiError(0) and fires bus on network error', async () => {
    fetchMock.mockRejectedValueOnce(new Error('offline'))
    const err = await apiGet('/x').catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(0)
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('silent: true suppresses bus on non-2xx', async () => {
    fetchMock.mockReturnValueOnce(jsonResp(404, { detail: 'nope' }))
    await expect(apiGet('/x', null, { silent: true })).rejects.toBeInstanceOf(ApiError)
    expect(listener).not.toHaveBeenCalled()
  })

  it('silent: true suppresses bus on network error', async () => {
    fetchMock.mockRejectedValueOnce(new Error('offline'))
    await expect(apiPost('/x', {}, { silent: true })).rejects.toBeInstanceOf(ApiError)
    expect(listener).not.toHaveBeenCalled()
  })

  it('returns null for empty body', async () => {
    fetchMock.mockReturnValueOnce(
      Promise.resolve({ ok: true, status: 204, text: () => Promise.resolve('') }),
    )
    const out = await apiGet('/x')
    expect(out).toBeNull()
  })

  it('returns raw text in ApiError.body when response is not JSON', async () => {
    fetchMock.mockReturnValueOnce(
      Promise.resolve({ ok: false, status: 500, text: () => Promise.resolve('plain text') }),
    )
    const err = await apiGet('/x').catch((e) => e)
    expect(err.body).toBe('plain text')
  })

  it('sends an abort signal with each request', async () => {
    fetchMock.mockReturnValueOnce(jsonResp(200, {}))
    await apiGet('/ping')
    const init = fetchMock.mock.calls[0][1]
    expect(init.signal).toBeInstanceOf(AbortSignal)
  })

  it('maps a timeout abort to a friendly ApiError without retrying', async () => {
    // A TimeoutError is deliberately NOT retryable: each attempt mints a fresh
    // 30s AbortSignal.timeout, so retrying a hung (not down) backend would push
    // the error out to ~91s instead of 30s.
    fetchMock.mockRejectedValue(new DOMException('signal timed out', 'TimeoutError'))
    await expect(apiGet('/slow', undefined, { silent: true })).rejects.toMatchObject({
      status: 0,
      body: { detail: 'request timed out' },
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('retries once with a refreshed token on 401 (F-09)', async () => {
    // First call is the pre-request getFreshAccessToken() lookup (F-47);
    // second is _refreshAccessToken() on the 401 retry.
    globalThis.__supabaseAuthStub.getSession
      .mockResolvedValueOnce({ data: { session: null } })
      .mockResolvedValueOnce({
        data: { session: { access_token: 'fresh-token', user: { id: 'u1' } } },
      })

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response('{"detail":"invalid_token"}', { status: 401 }))
      .mockResolvedValueOnce(new Response('{"ok":true}', { status: 200 }))

    vi.stubGlobal('fetch', fetchMock)

    const result = await apiGet('/whatever')
    expect(result).toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[1][1].headers.authorization).toBe('Bearer fresh-token')
  })

  it('sends the getSession token, not the stale store token', async () => {
    const store = useAuthStore()
    store.session = { access_token: 'store-tok', user: { id: 'u1' } }
    globalThis.__supabaseAuthStub.getSession.mockResolvedValueOnce({
      data: { session: { access_token: 'fresh-tok', user: { id: 'u1' } } },
    })
    fetchMock.mockResolvedValue(new Response('{}', { status: 200 }))
    await apiGet('/ping')
    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers['authorization']).toBe('Bearer fresh-tok')
  })

  function makeJwt(expSeconds) {
    const b64 = (obj) =>
      btoa(JSON.stringify(obj)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')

    return `${b64({ alg: 'none' })}.${b64({ exp: expSeconds })}.sig`
  }

  it('reuses the cached store token without getSession when far from expiry', async () => {
    const store = useAuthStore()
    const tok = makeJwt(Math.floor(Date.now() / 1000) + 3600)
    store.session = { access_token: tok, user: { id: 'u1' } }
    fetchMock.mockResolvedValue(new Response('{}', { status: 200 }))
    await apiGet('/ping')
    expect(globalThis.__supabaseAuthStub.getSession).not.toHaveBeenCalled()
    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers['authorization']).toBe(`Bearer ${tok}`)
  })

  it('goes through getSession when the cached token is near expiry', async () => {
    const store = useAuthStore()
    const tok = makeJwt(Math.floor(Date.now() / 1000) + 10) // inside 60s margin
    store.session = { access_token: tok, user: { id: 'u1' } }
    globalThis.__supabaseAuthStub.getSession.mockResolvedValueOnce({
      data: { session: { access_token: 'fresh-tok', user: { id: 'u1' } } },
    })
    fetchMock.mockResolvedValue(new Response('{}', { status: 200 }))
    await apiGet('/ping')
    expect(globalThis.__supabaseAuthStub.getSession).toHaveBeenCalled()
    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers['authorization']).toBe('Bearer fresh-tok')
  })

  it('falls back to the store token when getSession fails', async () => {
    const store = useAuthStore()
    store.session = { access_token: 'store-tok', user: { id: 'u1' } }
    globalThis.__supabaseAuthStub.getSession.mockRejectedValueOnce(new Error('offline'))
    fetchMock.mockResolvedValue(new Response('{}', { status: 200 }))
    await apiGet('/ping')
    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers['authorization']).toBe('Bearer store-tok')
  })

  it('signs out and calls the unauthorized handler after a second 401', async () => {
    globalThis.__supabaseAuthStub.getSession.mockResolvedValue({
      data: { session: { access_token: 'still-dead', user: { id: 'u1' } } },
    })
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('{"detail":"invalid_token"}', { status: 401 })),
    )

    await expect(apiGet('/whatever')).rejects.toMatchObject({ status: 401 })
    expect(globalThis.__supabaseAuthStub.signOut).toHaveBeenCalled()
    expect(unauthorizedHandler).toHaveBeenCalledTimes(1)
    expect(fetch).toHaveBeenCalledTimes(2) // hard cap: one retry
  })

  it('_onAuthExpired invokes the registered unauthorized handler', async () => {
    const { _onAuthExpired } = await import('../services/apiClient.js')
    await _onAuthExpired()
    expect(unauthorizedHandler).toHaveBeenCalledTimes(1)
  })

  it('_onAuthExpired is a no-op when no handler is registered', async () => {
    setUnauthorizedHandler(null)
    const { _onAuthExpired } = await import('../services/apiClient.js')
    await expect(_onAuthExpired()).resolves.toBeUndefined()
  })

  // F-18: bounded GET retry. Non-GETs are never retried -- a POST may have
  // landed before the connection dropped.
  describe('GET retry (F-18)', () => {
    beforeEach(() => {
      // Pin the jitter to the midpoint so the delays are exactly 300/900.
      vi.spyOn(Math, 'random').mockReturnValue(0.5)
    })

    it('retries a GET on a network TypeError and returns the eventual success', async () => {
      fetchMock
        .mockRejectedValueOnce(new TypeError('Failed to fetch'))
        .mockReturnValueOnce(jsonResp(200, { ok: true }))
      await expect(apiGet('/x')).resolves.toEqual({ ok: true })
      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(listener).not.toHaveBeenCalled()
    })

    it.each([502, 503, 504])('retries a GET on %i', async (status) => {
      fetchMock
        .mockReturnValueOnce(jsonResp(status, {}))
        .mockReturnValueOnce(jsonResp(200, { n: 1 }))
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('does not retry other statuses', async () => {
      fetchMock.mockReturnValue(jsonResp(500, { detail: 'boom' }))
      await expect(apiGet('/x', null, { silent: true })).rejects.toMatchObject({ status: 500 })
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('does not retry a TimeoutError', async () => {
      // Every attempt gets a fresh 30s AbortSignal.timeout, so 3 attempts on a
      // hung backend would take ~91s to surface. Fail on the first one.
      fetchMock.mockRejectedValue(new DOMException('signal timed out', 'TimeoutError'))
      await expect(apiGet('/x', null, { silent: true })).rejects.toMatchObject({
        status: 0,
        body: { detail: 'request timed out' },
      })
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('does not retry a non-retryable network error', async () => {
      fetchMock.mockRejectedValue(new Error('offline'))
      await expect(apiGet('/x', null, { silent: true })).rejects.toMatchObject({ status: 0 })
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('never retries a non-GET', async () => {
      fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
      await expect(apiPost('/x', {}, { silent: true })).rejects.toMatchObject({ status: 0 })
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('gives up after 3 attempts and reports the error exactly once', async () => {
      fetchMock.mockReturnValue(jsonResp(503, {}))
      await expect(apiGet('/x')).rejects.toMatchObject({ status: 503 })
      expect(fetchMock).toHaveBeenCalledTimes(GET_RETRY_ATTEMPTS)
      expect(listener).toHaveBeenCalledTimes(1)
    })

    it('waits the jittered 300ms/900ms backoff between attempts', async () => {
      const delays = []
      const realSetTimeout = globalThis.setTimeout
      vi.spyOn(globalThis, 'setTimeout').mockImplementation((fn, ms) => {
        delays.push(ms)

        return realSetTimeout(fn, 0)
      })
      fetchMock.mockReturnValue(jsonResp(503, {}))
      await expect(apiGet('/x', null, { silent: true })).rejects.toMatchObject({ status: 503 })
      expect(delays).toEqual(GET_RETRY_DELAYS_MS)
    })

    it('builds a fresh AbortSignal for every attempt', async () => {
      fetchMock
        .mockRejectedValueOnce(new TypeError('Failed to fetch'))
        .mockReturnValueOnce(jsonResp(200, {}))
      await apiGet('/x')
      const [first, second] = fetchMock.mock.calls.map(([, init]) => init.signal)
      expect(first).toBeInstanceOf(AbortSignal)
      expect(second).toBeInstanceOf(AbortSignal)
      expect(second).not.toBe(first)
    })

    it('does not interfere with the 401 refresh-once path', async () => {
      globalThis.__supabaseAuthStub.getSession
        .mockResolvedValueOnce({ data: { session: null } })
        .mockResolvedValueOnce({
          data: { session: { access_token: 'fresh-token', user: { id: 'u1' } } },
        })
      fetchMock
        .mockResolvedValueOnce(new Response('{"detail":"invalid_token"}', { status: 401 }))
        .mockResolvedValueOnce(new Response('{"ok":true}', { status: 200 }))
      await expect(apiGet('/whatever')).resolves.toEqual({ ok: true })
      // One 401 + one refreshed retry: the F-18 loop must not add attempts.
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })
  })

  // F-18: short TTL GET cache.
  describe('GET cache (F-18)', () => {
    it('serves a second identical GET from cache within the TTL', async () => {
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 1 }))
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('keys the cache on the full url including params', async () => {
      fetchMock
        .mockReturnValueOnce(jsonResp(200, { n: 1 }))
        .mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await expect(apiGet('/x', { a: 1 })).resolves.toEqual({ n: 1 })
      await expect(apiGet('/x', { a: 2 })).resolves.toEqual({ n: 2 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('re-fetches once the TTL has elapsed', async () => {
      const now = Date.now()
      const clock = vi.spyOn(Date, 'now').mockReturnValue(now)
      fetchMock
        .mockReturnValueOnce(jsonResp(200, { n: 1 }))
        .mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      clock.mockReturnValue(now + GET_CACHE_TTL_MS + 1)
      await expect(apiGet('/x')).resolves.toEqual({ n: 2 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('bypasses the cache with { fresh: true }', async () => {
      fetchMock
        .mockReturnValueOnce(jsonResp(200, { n: 1 }))
        .mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      await expect(apiGet('/x', null, { fresh: true })).resolves.toEqual({ n: 2 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('never caches a failed GET', async () => {
      fetchMock.mockReturnValueOnce(jsonResp(500, {})).mockReturnValueOnce(jsonResp(200, { n: 1 }))
      await expect(apiGet('/x', null, { silent: true })).rejects.toMatchObject({ status: 500 })
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
    })

    it('does not cache non-GET responses', async () => {
      fetchMock
        .mockReturnValueOnce(jsonResp(200, { n: 1 }))
        .mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await expect(apiPost('/x', {})).resolves.toEqual({ n: 1 })
      await expect(apiPost('/x', {})).resolves.toEqual({ n: 2 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('invalidates a cached GET when a write hits a deeper path', async () => {
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 1 }))
      await apiGet('/sessions/abc')
      fetchMock.mockReturnValueOnce(jsonResp(200, {})).mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await apiPost('/sessions/abc/end', {})
      await expect(apiGet('/sessions/abc')).resolves.toEqual({ n: 2 })
    })

    it('invalidates a cached list GET when a write hits its parent path', async () => {
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 1 }))
      await apiGet('/sessions', { cursor: 'c1' })
      fetchMock.mockReturnValueOnce(jsonResp(201, {})).mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await apiPost('/sessions', {})
      await expect(apiGet('/sessions', { cursor: 'c1' })).resolves.toEqual({ n: 2 })
    })

    it('leaves an unrelated cached GET alone', async () => {
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 1 }))
      await apiGet('/profile/abc')
      fetchMock.mockReturnValueOnce(jsonResp(200, {}))
      await apiDelete('/documents/7')
      await expect(apiGet('/profile/abc')).resolves.toEqual({ n: 1 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    // Root-scoped on purpose: a write to any session changes the sibling lists
    // (/sessions, /sessions/library), so everything under /sessions is dropped,
    // sibling ids included. Cross-root entries survive (next describe).
    it('a write to a sibling id still drops the whole resource root', async () => {
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 1 }))
      await apiGet('/sessions/abc')
      fetchMock.mockReturnValueOnce(jsonResp(200, {}))
      await apiPost('/sessions/abcdef/end', {})
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await expect(apiGet('/sessions/abc')).resolves.toEqual({ n: 2 })
      expect(fetchMock).toHaveBeenCalledTimes(3)
    })

    // Sign out and back in as someone else inside the TTL: a url-only key would
    // hand the second account the first one's body.
    it('never serves a cached GET to a different access token', async () => {
      globalThis.__supabaseAuthStub.getSession
        .mockResolvedValueOnce({
          data: { session: { access_token: 'tok-a', user: { id: 'a' } } },
        })
        .mockResolvedValueOnce({
          data: { session: { access_token: 'tok-b', user: { id: 'b' } } },
        })
      fetchMock.mockReturnValueOnce(jsonResp(200, { who: 'a' }))
      await expect(apiGet('/sessions')).resolves.toEqual({ who: 'a' })
      fetchMock.mockReturnValueOnce(jsonResp(200, { who: 'b' }))
      await expect(apiGet('/sessions')).resolves.toEqual({ who: 'b' })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('_onAuthExpired clears the cache', async () => {
      const { _onAuthExpired } = await import('../services/apiClient.js')
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 1 }))
      await apiGet('/x')
      await _onAuthExpired()
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await expect(apiGet('/x')).resolves.toEqual({ n: 2 })
    })

    it('invalidateGetCache drops a matching cached GET for raw-fetch writers', async () => {
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 1 }))
      await apiGet('/sessions/abc')
      invalidateGetCache('/sessions/abc')
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await expect(apiGet('/sessions/abc')).resolves.toEqual({ n: 2 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    // A GET already in flight when an invalidation lands must not write its
    // now-stale body into the cache on settle.
    it('does not cache a GET whose response lost a race with an invalidation', async () => {
      let release
      fetchMock.mockReturnValueOnce(
        new Promise((resolve) => {
          release = () => resolve(jsonResp(200, { n: 1 }))
        }),
      )
      const inFlight = apiGet('/sessions/abc')
      // getFreshAccessToken() is async, so wait until fetch has actually been
      // called -- otherwise the epoch would be captured after the bump below
      // and this test would pass without the fix.
      await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
      invalidateGetCache('/sessions/abc')
      release()
      await expect(inFlight).resolves.toEqual({ n: 1 })

      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await expect(apiGet('/sessions/abc')).resolves.toEqual({ n: 2 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('invalidates even when the write fails, since it may still have landed', async () => {
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 1 }))
      await apiGet('/sessions/abc')
      fetchMock.mockReturnValueOnce(jsonResp(409, {})).mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await expect(apiPost('/sessions/abc/end', {}, { silent: true })).rejects.toMatchObject({
        status: 409,
      })
      await expect(apiGet('/sessions/abc')).resolves.toEqual({ n: 2 })
    })

    it('a write under a resource root drops sibling list GETs (library, sidebar)', async () => {
      fetchMock.mockReturnValueOnce(jsonResp(200, { items: [1] }))
      await apiGet('/sessions/library', { limit: 20 })
      fetchMock.mockReturnValueOnce(jsonResp(200, { items: [1] }))
      await apiGet('/sessions', { limit: 15 })
      fetchMock.mockReturnValueOnce(jsonResp(200, {}))
      await apiPatch('/sessions/abc', { pinned: true })
      fetchMock
        .mockReturnValueOnce(jsonResp(200, { items: [2] }))
        .mockReturnValueOnce(jsonResp(200, { items: [3] }))
      await expect(apiGet('/sessions/library', { limit: 20 })).resolves.toEqual({ items: [2] })
      await expect(apiGet('/sessions', { limit: 15 })).resolves.toEqual({ items: [3] })
      expect(fetchMock).toHaveBeenCalledTimes(5)
    })

    it('a write under one root leaves another root cached', async () => {
      fetchMock.mockReturnValueOnce(jsonResp(200, { me: 1 }))
      await apiGet('/me')
      fetchMock.mockReturnValueOnce(jsonResp(200, {}))
      await apiPost('/sessions/abc/end', {})
      await expect(apiGet('/me')).resolves.toEqual({ me: 1 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })
  })

  // F-18 backend half: conditional revalidation via ETag / If-None-Match.
  describe('GET cache conditional revalidation (F-18)', () => {
    function etagResp(status, body, etag) {
      return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { etag } }))
    }

    it('stores the ETag from a 200 GET and sends If-None-Match once the entry expires', async () => {
      const now = Date.now()
      const clock = vi.spyOn(Date, 'now').mockReturnValue(now)
      fetchMock
        .mockReturnValueOnce(etagResp(200, { n: 1 }, '"v1"'))
        .mockReturnValueOnce(jsonResp(200, { n: 1 }))
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      clock.mockReturnValue(now + GET_CACHE_TTL_MS + 1)
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      const secondInit = fetchMock.mock.calls[1][1]
      expect(secondInit.headers['if-none-match']).toBe('"v1"')
    })

    it('a 304 resolves to the cached value and refreshes the TTL', async () => {
      const now = Date.now()
      const clock = vi.spyOn(Date, 'now').mockReturnValue(now)
      fetchMock
        .mockReturnValueOnce(etagResp(200, { n: 1 }, '"v1"'))
        .mockReturnValueOnce(Promise.resolve(new Response(null, { status: 304 })))
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      clock.mockReturnValue(now + GET_CACHE_TTL_MS + 1)
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
      // TTL was refreshed by the 304: a read shortly after is served from cache.
      clock.mockReturnValue(now + GET_CACHE_TTL_MS + 1 + 1000)
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })

    it('a 304 raced by a mid-flight invalidation still returns the cached value but does not refresh the TTL', async () => {
      const now = Date.now()
      const clock = vi.spyOn(Date, 'now').mockReturnValue(now)
      fetchMock.mockReturnValueOnce(etagResp(200, { n: 1 }, '"v1"'))
      await expect(apiGet('/sessions/abc')).resolves.toEqual({ n: 1 })

      clock.mockReturnValue(now + GET_CACHE_TTL_MS + 1)
      let release
      fetchMock.mockReturnValueOnce(
        new Promise((resolve) => {
          release = () => resolve(new Response(null, { status: 304 }))
        }),
      )
      const inFlight = apiGet('/sessions/abc')
      await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
      invalidateGetCache('/sessions/abc')
      release()
      await expect(inFlight).resolves.toEqual({ n: 1 })

      // Entry was dropped by the invalidation, so the next GET fetches again.
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await expect(apiGet('/sessions/abc')).resolves.toEqual({ n: 2 })
      expect(fetchMock).toHaveBeenCalledTimes(3)
    })

    it('fresh: true against an expired entry still sends If-None-Match', async () => {
      const now = Date.now()
      const clock = vi.spyOn(Date, 'now').mockReturnValue(now)
      fetchMock
        .mockReturnValueOnce(etagResp(200, { n: 1 }, '"v1"'))
        .mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      clock.mockReturnValue(now + GET_CACHE_TTL_MS + 1)
      await expect(apiGet('/x', null, { fresh: true })).resolves.toEqual({ n: 2 })
      const secondInit = fetchMock.mock.calls[1][1]
      expect(secondInit.headers['if-none-match']).toBe('"v1"')
    })

    it('fresh: true within the TTL revalidates with If-None-Match instead of a plain fetch', async () => {
      const now = Date.now()
      const clock = vi.spyOn(Date, 'now').mockReturnValue(now)
      fetchMock
        .mockReturnValueOnce(etagResp(200, { n: 1 }, '"v1"'))
        .mockReturnValueOnce(new Response(null, { status: 304 }))
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      clock.mockReturnValue(now + 1000)
      await expect(apiGet('/x', null, { fresh: true })).resolves.toEqual({ n: 1 })
      expect(fetchMock).toHaveBeenCalledTimes(2)
      expect(fetchMock.mock.calls[1][1].headers['if-none-match']).toBe('"v1"')
    })

    it('a 304 does not overwrite a newer entry stored by a concurrent GET', async () => {
      const now = Date.now()
      const clock = vi.spyOn(Date, 'now').mockReturnValue(now)
      fetchMock.mockReturnValueOnce(etagResp(200, { n: 1 }, '"v1"'))
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      clock.mockReturnValue(now + GET_CACHE_TTL_MS + 1)
      // GET-A revalidates and is answered 304 late; GET-B (also fresh) lands a
      // 200 with a newer body first. Server-side write: the epoch never moves.
      let resolveA
      fetchMock
        .mockReturnValueOnce(new Promise((r) => (resolveA = r)))
        .mockReturnValueOnce(etagResp(200, { n: 2 }, '"v2"'))
      const a = apiGet('/x', null, { fresh: true })
      await expect(apiGet('/x', null, { fresh: true })).resolves.toEqual({ n: 2 })
      resolveA(new Response(null, { status: 304 }))
      await expect(a).resolves.toEqual({ n: 1 })
      // Next plain read within the TTL is served from cache: must be v2.
      clock.mockReturnValue(now + GET_CACHE_TTL_MS + 2)
      await expect(apiGet('/x')).resolves.toEqual({ n: 2 })
      expect(fetchMock).toHaveBeenCalledTimes(3)
    })

    it('sends no If-None-Match after a write drops the cache entry', async () => {
      fetchMock.mockReturnValueOnce(etagResp(200, { n: 1 }, '"v1"'))
      await expect(apiGet('/sessions/abc')).resolves.toEqual({ n: 1 })
      fetchMock.mockReturnValueOnce(jsonResp(200, {}))
      await apiPost('/sessions/abc/end', {})
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 2 }))
      await expect(apiGet('/sessions/abc')).resolves.toEqual({ n: 2 })
      const thirdInit = fetchMock.mock.calls[2][1]
      expect(thirdInit.headers['if-none-match']).toBeUndefined()
    })

    it('a cached entry under a different token is never used for If-None-Match', async () => {
      globalThis.__supabaseAuthStub.getSession
        .mockResolvedValueOnce({
          data: { session: { access_token: 'tok-a', user: { id: 'a' } } },
        })
        .mockResolvedValueOnce({
          data: { session: { access_token: 'tok-b', user: { id: 'b' } } },
        })
      fetchMock.mockReturnValueOnce(etagResp(200, { who: 'a' }, '"v1"'))
      await expect(apiGet('/sessions')).resolves.toEqual({ who: 'a' })
      fetchMock.mockReturnValueOnce(jsonResp(200, { who: 'b' }))
      await expect(apiGet('/sessions')).resolves.toEqual({ who: 'b' })
      const secondInit = fetchMock.mock.calls[1][1]
      expect(secondInit.headers['if-none-match']).toBeUndefined()
    })

    it('a fresh 200 response replaces the stored ETag', async () => {
      const now = Date.now()
      const clock = vi.spyOn(Date, 'now').mockReturnValue(now)
      fetchMock
        .mockReturnValueOnce(etagResp(200, { n: 1 }, '"v1"'))
        .mockReturnValueOnce(etagResp(200, { n: 2 }, '"v2"'))
      await expect(apiGet('/x')).resolves.toEqual({ n: 1 })
      clock.mockReturnValue(now + GET_CACHE_TTL_MS + 1)
      await expect(apiGet('/x')).resolves.toEqual({ n: 2 })
      clock.mockReturnValue(now + 2 * (GET_CACHE_TTL_MS + 1))
      fetchMock.mockReturnValueOnce(jsonResp(200, { n: 3 }))
      await expect(apiGet('/x')).resolves.toEqual({ n: 3 })
      const thirdInit = fetchMock.mock.calls[2][1]
      expect(thirdInit.headers['if-none-match']).toBe('"v2"')
    })
  })
})
