// frontend/src/__tests__/chatStreamService.test.js
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { streamChat } from '@/services/chatStreamService.js'
import { useAuthStore } from '@/stores/auth.js'

// Build a Response whose body is a ReadableStream containing the given SSE text.
function mockResponse(sseBody) {
  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(sseBody))
      controller.close()
    },
  })

  return new Response(stream, {
    status: 200,
    headers: { 'content-type': 'text/event-stream' },
  })
}

// Build a 401 Response with a JSON body, matching the shape apiClient's
// F-09 tests use for the same scenario.
function mock401Response() {
  return new Response(JSON.stringify({ detail: 'invalid_token' }), { status: 401 })
}

// Build a Response whose body is a ReadableStream that emits one SSE frame
// and then never closes -- used to simulate an idle (hung) stream.
function sseResponseThatHangsAfterOneEvent() {
  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode('event: assistant_delta\ndata: {"delta":"hi"}\n\n'))
      // deliberately never close/enqueue again
    },
  })

  return new Response(stream, {
    status: 200,
    headers: { 'content-type': 'text/event-stream' },
  })
}

// Build a Response whose body emits one SSE frame and then errors the stream
// with `err` -- how a connection that dies mid-body surfaces to the reader.
function sseResponseThatErrorsMidBody(err) {
  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode('event: assistant_delta\ndata: {"delta":"hi"}\n\n'))
      controller.error(err)
    },
  })

  return new Response(stream, {
    status: 200,
    headers: { 'content-type': 'text/event-stream' },
  })
}

describe('chatStreamService', () => {
  let fetchMock

  beforeEach(() => {
    setActivePinia(createPinia())
    fetchMock = vi.fn()
    globalThis.fetch = fetchMock
    // Seed the auth store so accessToken is non-null
    const auth = useAuthStore()
    auth.session = { access_token: 'tok-123', user: { id: 'u1' } }
  })

  afterEach(() => vi.restoreAllMocks())

  it('POSTs to the chat-stream URL with bearer token and JSON body', async () => {
    const sseBody = 'event: done\ndata: {}\n\n'
    fetchMock.mockResolvedValueOnce(mockResponse(sseBody))

    const events = []
    await streamChat({ sessionId: 's1', message: 'hi', onEvent: (e) => events.push(e) })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toContain('/chat/stream')
    expect(init.method).toBe('POST')
    expect(init.headers['authorization']).toBe('Bearer tok-123')
    expect(JSON.parse(init.body)).toEqual({ session_id: 's1', message: 'hi', review_gaps: false })
  })

  it('invokes onEvent for each parsed SSE event', async () => {
    const sseBody = 'event: assistant_delta\ndata: {"delta":"hello"}\n\nevent: done\ndata: {}\n\n'
    fetchMock.mockResolvedValueOnce(mockResponse(sseBody))

    const events = []
    await streamChat({ sessionId: 's1', message: 'hi', onEvent: (e) => events.push(e) })

    expect(events).toEqual([
      { event: 'assistant_delta', data: { delta: 'hello' } },
      { event: 'done', data: {} },
    ])
  })

  it('passes signal through to fetch and aborts cleanly', async () => {
    const ctrl = new AbortController()
    const sseBody = 'event: done\ndata: {}\n\n'
    fetchMock.mockResolvedValueOnce(mockResponse(sseBody))

    await streamChat({
      sessionId: 's1',
      message: 'hi',
      onEvent: () => {},
      signal: ctrl.signal,
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const init = fetchMock.mock.calls[0][1]
    // The service wires the caller's signal into an internal controller (needed
    // to layer header/idle timeouts on top), so it is no longer literally the
    // same object -- assert it is a live AbortSignal that tracks the caller's.
    expect(init.signal).toBeInstanceOf(AbortSignal)
    expect(init.signal.aborted).toBe(false)
  })

  it('rejects with a timeout ApiError when headers never arrive', async () => {
    vi.useFakeTimers()
    fetchMock.mockImplementationOnce(() => new Promise(() => {})) // never resolves
    const p = streamChat({ sessionId: 's1', message: 'hi', onEvent: vi.fn() })
    await Promise.all([
      expect(p).rejects.toMatchObject({
        status: 0,
        body: { detail: 'request timed out' },
      }),
      vi.advanceTimersByTimeAsync(30000),
    ])
    vi.useRealTimers()
  })

  it('rejects with a timeout ApiError when the stream goes idle', async () => {
    vi.useFakeTimers()
    // A stream that emits one event then hangs forever.
    fetchMock.mockResolvedValueOnce(sseResponseThatHangsAfterOneEvent())
    const onEvent = vi.fn()
    const p = streamChat({ sessionId: 's1', message: 'hi', onEvent })
    await Promise.all([
      expect(p).rejects.toMatchObject({
        status: 0,
        body: { detail: 'stream timed out' },
      }),
      vi.advanceTimersByTimeAsync(61000),
    ])
    vi.useRealTimers()
  })

  it('a caller abort propagates as an abort, not an ApiError', async () => {
    const ctrl = new AbortController()
    fetchMock.mockImplementationOnce(
      (url, init) =>
        new Promise((_, reject) => {
          // F-47 made the pre-fetch token lookup async, so by the time fetch()
          // is invoked the caller's abort may already have propagated to
          // init.signal -- mirror real fetch's synchronous-check-then-reject
          // behavior instead of relying solely on a future 'abort' event.
          if (init.signal.aborted) {
            reject(init.signal.reason ?? new DOMException('aborted', 'AbortError'))

            return
          }

          init.signal.addEventListener('abort', () =>
            reject(init.signal.reason ?? new DOMException('aborted', 'AbortError')),
          )
        }),
    )
    const p = streamChat({ sessionId: 's1', message: 'hi', onEvent: vi.fn(), signal: ctrl.signal })
    ctrl.abort()
    await expect(p).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('a caller abort MID-STREAM (after headers + at least one event) propagates as an AbortError, not a generic Error or ApiError', async () => {
    const ctrl = new AbortController()
    // Headers arrive fine; the stream then emits one event and hangs -- the
    // caller (e.g. a Stop button) aborts once it has seen that first event,
    // simulating a genuine mid-stream user cancel.
    fetchMock.mockResolvedValueOnce(sseResponseThatHangsAfterOneEvent())

    const onEvent = vi.fn(() => {
      ctrl.abort()
    })

    const p = streamChat({ sessionId: 's1', message: 'hi', onEvent, signal: ctrl.signal })

    await expect(p).rejects.toMatchObject({ name: 'AbortError' })
    expect(onEvent).toHaveBeenCalledTimes(1)
  })

  // E-02: a connection that dies mid-body rejects the read with a bare
  // TypeError. Before, that leaked out raw and friendlyError could only render
  // its own message; now it matches the header phase's status-0 contract.
  it('normalizes a mid-body TypeError into a status-0 ApiError (E-02)', async () => {
    fetchMock.mockResolvedValueOnce(sseResponseThatErrorsMidBody(new TypeError('network error')))
    const onEvent = vi.fn()
    await expect(streamChat({ sessionId: 's1', message: 'hi', onEvent })).rejects.toMatchObject({
      status: 0,
      body: { detail: 'network error' },
    })
  })

  it('passes a non-TypeError mid-body failure through unchanged (E-02)', async () => {
    const boom = new Error('parser blew up')
    fetchMock.mockResolvedValueOnce(sseResponseThatErrorsMidBody(boom))
    await expect(streamChat({ sessionId: 's1', message: 'hi', onEvent: vi.fn() })).rejects.toBe(
      boom,
    )
  })

  it('streamChat puts review_gaps in the request body when reviewGaps is true', async () => {
    const sseBody = 'event: done\ndata: {}\n\n'
    fetchMock.mockResolvedValueOnce(mockResponse(sseBody))

    await streamChat({
      sessionId: 's1',
      message: 'Review my gaps',
      reviewGaps: true,
      onEvent: () => {},
    })

    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body).toEqual({ session_id: 's1', message: 'Review my gaps', review_gaps: true })
  })

  it('streamChat puts review_gap in the request body when provided', async () => {
    const sseBody = 'event: done\ndata: {}\n\n'
    fetchMock.mockResolvedValueOnce(mockResponse(sseBody))

    await streamChat({
      sessionId: 's1',
      message: 'Review my gap: recursion',
      reviewGaps: true,
      reviewGap: 'recursion',
      onEvent: () => {},
    })

    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body.review_gap).toBe('recursion')
  })

  it('streamChat omits review_gap when not provided', async () => {
    const sseBody = 'event: done\ndata: {}\n\n'
    fetchMock.mockResolvedValueOnce(mockResponse(sseBody))

    await streamChat({ sessionId: 's1', message: 'hi', onEvent: () => {} })

    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect('review_gap' in body).toBe(false)
  })

  it('throws ApiError on non-2xx with parsed body', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'bad' }), { status: 400 }),
    )

    await expect(
      streamChat({ sessionId: 's1', message: 'hi', onEvent: () => {} }),
    ).rejects.toMatchObject({ status: 400 })
  })

  it('retries the SSE POST once with a refreshed token on 401 (F-09)', async () => {
    // First call is the pre-request getFreshAccessToken() lookup (F-47);
    // second is _refreshAccessToken() on the 401 retry.
    globalThis.__supabaseAuthStub.getSession
      .mockResolvedValueOnce({ data: { session: null } })
      .mockResolvedValueOnce({
        data: { session: { access_token: 'fresh-token', user: { id: 'u1' } } },
      })
    const events = []
    fetchMock
      .mockResolvedValueOnce(mock401Response())
      .mockResolvedValueOnce(mockResponse('event: done\ndata: {}\n\n'))

    await streamChat({ sessionId: 's1', message: 'hi', onEvent: (e) => events.push(e) })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[1][1].headers.authorization).toBe('Bearer fresh-token')
  })

  it('signs out after a second 401 on the SSE POST', async () => {
    globalThis.__supabaseAuthStub.getSession.mockResolvedValue({
      data: { session: { access_token: 'still-dead', user: { id: 'u1' } } },
    })
    fetchMock.mockResolvedValue(mock401Response())

    await expect(
      streamChat({ sessionId: 's1', message: 'hi', onEvent: () => {} }),
    ).rejects.toMatchObject({ status: 401 })
    expect(globalThis.__supabaseAuthStub.signOut).toHaveBeenCalled()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  // F-18 review finding: the SSE POST is a raw fetch, so it must drop the
  // session tree from the short GET cache itself or a re-open within the TTL
  // would show the pre-turn transcript.
  it('invalidates the cached session GET once the stream settles', async () => {
    const { apiGet, _resetApiCache } = await import('@/services/apiClient.js')
    _resetApiCache()

    const json = (body) =>
      new Response(JSON.stringify(body), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })

    fetchMock.mockResolvedValueOnce(json({ n: 1 }))
    await apiGet('/sessions/s1/messages')
    fetchMock.mockResolvedValueOnce(mockResponse('event: done\ndata: {}\n\n'))
    await streamChat({ sessionId: 's1', message: 'hi', onEvent: () => {} })
    fetchMock.mockResolvedValueOnce(json({ n: 2 }))
    await expect(apiGet('/sessions/s1/messages')).resolves.toEqual({ n: 2 })
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('invalidates the cached session GET even when the stream fails', async () => {
    const { apiGet, _resetApiCache } = await import('@/services/apiClient.js')
    _resetApiCache()

    const json = (body) =>
      new Response(JSON.stringify(body), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })

    fetchMock.mockResolvedValueOnce(json({ n: 1 }))
    await apiGet('/sessions/s1')
    fetchMock.mockRejectedValueOnce(new TypeError('network error'))
    await expect(
      streamChat({ sessionId: 's1', message: 'hi', onEvent: () => {} }),
    ).rejects.toMatchObject({ status: 0 })
    fetchMock.mockResolvedValueOnce(json({ n: 2 }))
    await expect(apiGet('/sessions/s1')).resolves.toEqual({ n: 2 })
  })
})
