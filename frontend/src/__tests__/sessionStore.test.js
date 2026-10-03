import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/services/sessionsApi.js', () => ({
  listSessions: vi.fn(),
  createSession: vi.fn(),
  getSession: vi.fn(),
  getSessionMessages: vi.fn(),
  endSession: vi.fn(),
  reopenSession: vi.fn(),
  getSessionLibrary: vi.fn(),
  renameSession: vi.fn(),
  setPinned: vi.fn(),
  lookupTopic: vi.fn(),
}))

import { useSessionStore } from '@/stores/session.js'
import * as sessionsApi from '@/services/sessionsApi.js'
import { getSessionLibrary } from '@/services/sessionsApi.js'
import * as streamSvc from '@/services/chatStreamService.js'
import { ERR_DAILY_CAP_REACHED, ERR_DAILY_COST_CAP_REACHED } from '@/lib/errorCodes.js'
import { StreamAbortedError } from '@/lib/errors.js'

class ApiErrorLike extends Error {
  constructor(status, body) {
    super('api error')
    this.status = status
    this.body = body
  }
}

describe('session store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('listSessions populates and clears loading/error', async () => {
    sessionsApi.getSessionLibrary
      .mockResolvedValueOnce({ items: [{ id: 's1' }], total: 1, limit: 20, offset: 0 })
      .mockResolvedValueOnce({ items: [], total: 0, limit: 20, offset: 0 })
    const s = useSessionStore()
    const out = await s.listSessions('u1')
    expect(out).toEqual([{ id: 's1' }])
    expect(s.sessions).toEqual([{ id: 's1' }])
    expect(s.loading).toBe(false)
  })

  it('listSessions surfaces error and rethrows', async () => {
    sessionsApi.getSessionLibrary.mockRejectedValueOnce(new Error('nope'))
    const s = useSessionStore()
    await expect(s.listSessions('u1')).rejects.toThrow('nope')
    expect(s.error).toBe('nope')
  })

  it('createSession sets currentSession and resets messages', async () => {
    sessionsApi.createSession.mockResolvedValueOnce({ id: 's2', topic: 't' })
    const s = useSessionStore()
    s.messages = [{ role: 'user', content: 'old' }]
    const out = await s.createSession({ userId: 'u', topic: 't' })
    expect(out.id).toBe('s2')
    expect(s.currentSessionId).toBe('s2')
    expect(s.messages).toEqual([])
  })

  it('loadSession maps API messages to flat list', async () => {
    sessionsApi.getSession.mockResolvedValueOnce({
      id: 's1',
      messages: [
        { id: 'm1', role: 'user', content: 'hi', citations: [], created_at: '2026-01-01' },
        { id: 'm2', role: 'assistant', content: 'hey', created_at: '2026-01-02' },
      ],
    })
    const s = useSessionStore()
    await s.loadSession('s1')
    expect(s.messages).toHaveLength(2)
    expect(s.messages[0].message_id).toBe('m1')
    expect(s.messages[1].citations).toEqual([])
  })

  // F-14 follow-up: reload must carry `status` through so a 'partial' row
  // renders its "(interrupted)" marker after a page refresh, not just live.
  it('loadSession maps status through so partial rows render on reload', async () => {
    sessionsApi.getSession.mockResolvedValueOnce({
      id: 's1',
      messages: [
        {
          id: 'm1',
          role: 'user',
          content: 'hi',
          citations: [],
          created_at: '2026-01-01',
          status: 'complete',
        },
        {
          id: 'm2',
          role: 'assistant',
          content: 'draft',
          created_at: '2026-01-02',
          status: 'partial',
        },
      ],
    })
    const s = useSessionStore()
    await s.loadSession('s1')
    expect(s.messages[1]).toMatchObject({ content: 'draft', status: 'partial' })
  })

  it('endSession updates currentSession ended_at', async () => {
    sessionsApi.createSession.mockResolvedValueOnce({ id: 's1', topic: 't' })
    sessionsApi.endSession.mockResolvedValueOnce({
      ended_at: '2026-01-01',
      summary: { text: 'recap' },
    })
    const s = useSessionStore()
    await s.createSession({ userId: 'u', topic: 't' })
    const resp = await s.endSession()
    expect(resp.summary.text).toBe('recap')
    expect(s.currentSession.ended_at).toBe('2026-01-01')
  })

  // F-54: 'no_exchanges' summary.text is UI display copy for the closing
  // dialog, not a real recap -- it must not be written into topic_profile.
  it('endSession writes the profile summary when kind is summary', async () => {
    sessionsApi.createSession.mockResolvedValueOnce({
      id: 's1',
      topic: 't',
      topic_profile: { last_session_summary: 'old' },
    })
    sessionsApi.endSession.mockResolvedValueOnce({
      ended_at: '2026-01-01',
      summary: { kind: 'summary', text: 'display copy' },
    })
    const s = useSessionStore()
    await s.createSession({ userId: 'u', topic: 't' })
    await s.endSession()
    expect(s.currentSession.topic_profile.last_session_summary).toBe('display copy')
  })

  it('endSession does NOT write the profile summary when kind is no_exchanges', async () => {
    sessionsApi.createSession.mockResolvedValueOnce({
      id: 's1',
      topic: 't',
      topic_profile: { last_session_summary: 'old' },
    })
    sessionsApi.endSession.mockResolvedValueOnce({
      ended_at: '2026-01-01',
      summary: { kind: 'no_exchanges', text: 'display copy' },
    })
    const s = useSessionStore()
    await s.createSession({ userId: 'u', topic: 't' })
    await s.endSession()
    expect(s.currentSession.topic_profile.last_session_summary).toBe('old')
  })

  it('reopenSession clears ended_at when ids match', async () => {
    sessionsApi.createSession.mockResolvedValueOnce({
      id: 's1',
      topic: 't',
      ended_at: '2026-01-01',
    })
    sessionsApi.reopenSession.mockResolvedValueOnce({ ok: true })
    const s = useSessionStore()
    await s.createSession({ userId: 'u', topic: 't' })
    await s.reopenSession('s1')
    expect(s.currentSession.ended_at).toBeNull()
  })

  it('createSession increments activeTotal (a fresh session is always active)', async () => {
    sessionsApi.createSession.mockResolvedValueOnce({ id: 's2', topic: 't' })
    const s = useSessionStore()
    s.activeTotal = 3
    await s.createSession({ topic: 't', seedMode: 'fresh' })
    expect(s.activeTotal).toBe(4)
  })

  it('endSession moves the total from active to ended unconditionally, even when the session is outside the loaded window', async () => {
    sessionsApi.endSession.mockResolvedValueOnce({ ended_at: '2026-01-01', summary: null })
    const s = useSessionStore()
    s.activeTotal = 5
    s.endedTotal = 2
    s.sessions = [] // session not in the loaded 20+20 window
    await s.endSession('outside-window-1')
    expect(s.activeTotal).toBe(4)
    expect(s.endedTotal).toBe(3)
  })

  it('endSession clamps activeTotal at zero instead of going negative', async () => {
    sessionsApi.endSession.mockResolvedValueOnce({ ended_at: '2026-01-01', summary: null })
    const s = useSessionStore()
    s.activeTotal = 0
    s.endedTotal = 0
    await s.endSession('s1')
    expect(s.activeTotal).toBe(0)
    expect(s.endedTotal).toBe(1)
  })

  it('reopenSession moves the total from ended to active unconditionally, even when the session is outside the loaded window', async () => {
    sessionsApi.reopenSession.mockResolvedValueOnce({ ok: true })
    const s = useSessionStore()
    s.activeTotal = 2
    s.endedTotal = 5
    s.sessions = [] // session not in the loaded 20+20 window
    await s.reopenSession('outside-window-1')
    expect(s.activeTotal).toBe(3)
    expect(s.endedTotal).toBe(4)
  })

  it('reopenSession clamps endedTotal at zero instead of going negative', async () => {
    sessionsApi.reopenSession.mockResolvedValueOnce({ ok: true })
    const s = useSessionStore()
    s.activeTotal = 0
    s.endedTotal = 0
    await s.reopenSession('s1')
    expect(s.activeTotal).toBe(1)
    expect(s.endedTotal).toBe(0)
  })

  it('reopen 409 duplicate_topic exposes the conflicting session id', async () => {
    const store = useSessionStore()
    sessionsApi.reopenSession.mockRejectedValue(
      new ApiErrorLike(409, { detail: { code: 'duplicate_topic', session_id: 'other1' } }),
    )
    await store.reopenSession('s1').catch(() => {})
    expect(store.duplicateReopen).toEqual({ sessionId: 'other1' })
    expect(store.error).toMatch(/active session with this topic/i)
  })

  it('setError and reset work', () => {
    const s = useSessionStore()
    s.setError('boom')
    expect(s.error).toBe('boom')
    s.reset()
    expect(s.error).toBeNull()
    expect(s.currentSessionId).toBeNull()
  })

  it('reset clears duplicateReopen so it cannot survive a sign-out', () => {
    const s = useSessionStore()
    s.duplicateReopen = { sessionId: 'other1' }
    s.reset()
    expect(s.duplicateReopen).toBeNull()
  })

  it('listSessions de-dupes concurrent calls into one network request', async () => {
    let resolveActive, resolveEnded
    sessionsApi.getSessionLibrary
      .mockImplementationOnce(
        () =>
          new Promise((r) => {
            resolveActive = r
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise((r) => {
            resolveEnded = r
          }),
      )
    const s = useSessionStore()
    const p1 = s.listSessions()
    const p2 = s.listSessions()
    resolveActive({ items: [{ id: 's1' }], total: 1, limit: 20, offset: 0 })
    resolveEnded({ items: [], total: 0, limit: 20, offset: 0 })
    const [r1, r2] = await Promise.all([p1, p2])
    expect(sessionsApi.getSessionLibrary).toHaveBeenCalledTimes(2)
    expect(r1).toEqual([{ id: 's1' }])
    expect(r2).toEqual([{ id: 's1' }])
    expect(s.detailLoading).toBe(false)
  })

  it('listSessions refetches after a failed request (error path clears inflight key)', async () => {
    sessionsApi.getSessionLibrary
      .mockRejectedValueOnce(new Error('network'))
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({ items: [{ id: 'b' }], total: 1, limit: 20, offset: 0 })
      .mockResolvedValueOnce({ items: [], total: 0, limit: 20, offset: 0 })
    const s = useSessionStore()
    await expect(s.listSessions()).rejects.toThrow('network')
    const out = await s.listSessions()
    expect(sessionsApi.getSessionLibrary).toHaveBeenCalledTimes(4)
    expect(out).toEqual([{ id: 'b' }])
  })

  it('listSessions refetches after the in-flight request settles (no retained cache)', async () => {
    sessionsApi.getSessionLibrary
      .mockResolvedValueOnce({ items: [{ id: 'a' }], total: 1, limit: 20, offset: 0 })
      .mockResolvedValueOnce({ items: [], total: 0, limit: 20, offset: 0 })
      .mockResolvedValueOnce({ items: [{ id: 'b' }], total: 1, limit: 20, offset: 0 })
      .mockResolvedValueOnce({ items: [], total: 0, limit: 20, offset: 0 })
    const s = useSessionStore()
    await s.listSessions()
    await s.listSessions()
    expect(sessionsApi.getSessionLibrary).toHaveBeenCalledTimes(4)
    expect(s.sessions).toEqual([{ id: 'b' }])
  })

  it('loadSession de-dupes concurrent same-id calls and toggles detailLoading', async () => {
    let resolve
    sessionsApi.getSession.mockImplementationOnce(
      () =>
        new Promise((r) => {
          resolve = r
        }),
    )
    const s = useSessionStore()
    const p1 = s.loadSession('s1')
    const p2 = s.loadSession('s1')
    expect(s.detailLoading).toBe(true)
    resolve({ id: 's1', messages: [] })
    await Promise.all([p1, p2])
    expect(sessionsApi.getSession).toHaveBeenCalledTimes(1)
    expect(s.detailLoading).toBe(false)
  })

  it('loadSession does not de-dupe different ids', async () => {
    sessionsApi.getSession.mockResolvedValue({ id: 'x', messages: [] })
    const s = useSessionStore()
    await Promise.all([s.loadSession('s1'), s.loadSession('s2')])
    expect(sessionsApi.getSession).toHaveBeenCalledTimes(2)
  })

  it('drops a superseded out-of-order load (A->B->A, B resolves last)', async () => {
    const resolvers = {}
    sessionsApi.getSession.mockImplementation(
      (id) =>
        new Promise((r) => {
          resolvers[id] = () => r({ id, messages: [] })
        }),
    )
    const s = useSessionStore()
    const pA1 = s.loadSession('A')
    const pB = s.loadSession('B')
    const pA2 = s.loadSession('A') // deduped onto the still-pending A load; re-stamps latest='A'
    resolvers['A']()
    resolvers['B']() // B resolves AFTER A, but A is the latest requested -> B must not clobber
    await Promise.all([pA1, pB, pA2])
    expect(s.currentSessionId).toBe('A')
    expect(s.currentSession.id).toBe('A')
  })

  it('a superseded load that 404s does not clobber the current session error', async () => {
    const slots = {}
    sessionsApi.getSession.mockImplementation(
      (id) =>
        new Promise((res, rej) => {
          slots[id] = { res, rej }
        }),
    )
    const s = useSessionStore()
    const pA = s.loadSession('A')
    const pB = s.loadSession('B') // latest requested -> B
    slots['B'].res({ id: 'B', messages: [] })
    // A 404s AFTER navigating to B; it must not surface an error over B.
    slots['A'].rej(Object.assign(new Error('gone'), { status: 404 }))
    await Promise.allSettled([pA, pB])
    expect(s.currentSession.id).toBe('B')
    expect(s.error).toBeNull()
  })

  it('a non-superseded 404 still surfaces the error (guard does not over-suppress)', async () => {
    sessionsApi.getSession.mockRejectedValueOnce(Object.assign(new Error('gone'), { status: 404 }))
    const s = useSessionStore()
    await expect(s.loadSession('gone')).rejects.toBeTruthy()
    expect(s.error).toBeTruthy()
  })

  it('fetchLibrary returns the page and toggles libraryLoading', async () => {
    const page = { items: [{ id: 's1' }], total: 1, limit: 20, offset: 0 }
    sessionsApi.getSessionLibrary.mockResolvedValueOnce(page)
    const s = useSessionStore()
    const out = await s.fetchLibrary({ status: 'all', limit: 20, offset: 0 })
    // E-06: silent, because the library page owns its own failure copy and
    // retry control. A toast on top of that would say the same thing twice.
    expect(sessionsApi.getSessionLibrary).toHaveBeenCalledWith(
      {
        status: 'all',
        limit: 20,
        offset: 0,
      },
      { silent: true },
    )
    expect(out).toEqual(page)
    expect(s.libraryLoading).toBe(false)
  })

  // E-06: the store no longer holds a libraryError ref -- it was rendered
  // nowhere. The failure reaches the page by rethrow only.
  it('fetchLibrary rethrows without recording any store error', async () => {
    sessionsApi.getSessionLibrary.mockRejectedValueOnce(new Error('boom'))
    const s = useSessionStore()
    await expect(s.fetchLibrary({})).rejects.toThrow('boom')
    expect(s.libraryLoading).toBe(false)
    expect(s.error).toBeNull()
    expect('libraryError' in s).toBe(false)
  })

  // F-07: renameSession/setPinned are background sidebar actions -- a failure
  // must roll back local state and rethrow for the caller to toast, but must
  // never write the store's global `error` (that unmounts unrelated screens,
  // e.g. Home, which treats a non-empty error as fatal).
  it('renameSession failure rolls back but does not write global error', async () => {
    const store = useSessionStore()
    store.sessions = [{ id: 's1', topic: 'Old' }]
    sessionsApi.renameSession.mockRejectedValue(new ApiErrorLike(500, {}))
    await expect(store.renameSession('s1', 'New')).rejects.toBeTruthy()
    expect(store.sessions[0].topic).toBe('Old')
    expect(store.error).toBeNull()
  })

  it('setPinned failure rolls back but does not write global error', async () => {
    const store = useSessionStore()
    store.sessions = [{ id: 's1', topic: 'Old', pinned: false }]
    sessionsApi.setPinned.mockRejectedValue(new ApiErrorLike(500, {}))
    await expect(store.setPinned('s1', true)).rejects.toBeTruthy()
    expect(store.sessions[0].pinned).toBe(false)
    expect(store.error).toBeNull()
  })

  it('superseded load settling first does not clear loading flags', async () => {
    const store = useSessionStore()
    let resolveB, resolveC
    sessionsApi.getSession
      .mockReturnValueOnce(
        new Promise((r) => {
          resolveB = r
        }),
      )
      .mockReturnValueOnce(
        new Promise((r) => {
          resolveC = r
        }),
      )
    const pB = store.loadSession('B')
    const pC = store.loadSession('C')
    resolveB({ id: 'B', messages: [] })
    await pB
    expect(store.detailLoading).toBe(true) // C still in flight
    resolveC({ id: 'C', messages: [] })
    await pC
    expect(store.detailLoading).toBe(false)
  })
})

describe('listSessions via library endpoint', () => {
  let store

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    store = useSessionStore()
  })

  it('fetches active (pinned_activity) and ended (last_activity) pages, silent, merged in order', async () => {
    getSessionLibrary
      .mockResolvedValueOnce({
        items: [{ id: 'a1' }, { id: 'a2' }],
        total: 30,
        limit: 20,
        offset: 0,
      })
      .mockResolvedValueOnce({ items: [{ id: 'e1' }], total: 25, limit: 20, offset: 0 })
    await store.listSessions()
    expect(getSessionLibrary).toHaveBeenCalledWith(
      { status: 'active', sort: 'pinned_activity', limit: 40, offset: 0 },
      { silent: true },
    )
    expect(getSessionLibrary).toHaveBeenCalledWith(
      { status: 'ended', sort: 'last_activity', limit: 40, offset: 0 },
      { silent: true },
    )
    expect(store.sessions.map((s) => s.id)).toEqual(['a1', 'a2', 'e1'])
    expect(store.activeTotal).toBe(30)
    expect(store.endedTotal).toBe(25)
  })

  it('dedupes by id when a session appears in both pages', async () => {
    getSessionLibrary
      .mockResolvedValueOnce({ items: [{ id: 'x' }], total: 1, limit: 20, offset: 0 })
      .mockResolvedValueOnce({ items: [{ id: 'x' }, { id: 'e1' }], total: 2, limit: 20, offset: 0 })
    await store.listSessions()
    expect(store.sessions.map((s) => s.id)).toEqual(['x', 'e1'])
  })

  it('de-dupes concurrent calls through the same in-flight promise', async () => {
    getSessionLibrary.mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 })
    const p1 = store.listSessions()
    const p2 = store.listSessions()
    // Pinia wraps every promise-returning action in a fresh .then() chain
    // (pinia 3.0.4 wrapAction), so p1 !== p2 by construction even when both
    // callers share one in-flight fetch. Assert the shared resolution instead.
    expect(await p1).toBe(await p2)
    expect(getSessionLibrary).toHaveBeenCalledTimes(2) // one active + one ended, not four
  })

  it('reset() clears totals', async () => {
    getSessionLibrary
      .mockResolvedValueOnce({ items: [], total: 7, limit: 20, offset: 0 })
      .mockResolvedValueOnce({ items: [], total: 3, limit: 20, offset: 0 })
    await store.listSessions()
    store.reset()
    expect(store.activeTotal).toBe(0)
    expect(store.endedTotal).toBe(0)
  })
})

describe('session store — streaming', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('starts in idle stream state with no streaming message', () => {
    const s = useSessionStore()
    expect(s.streamState).toBe('idle')
    expect(s.streamingMessage).toBeNull()
  })

  it('appendAssistantDelta accumulates text on streamingMessage', () => {
    const s = useSessionStore()
    s.streamingMessage = { role: 'assistant', content: '', tool_calls: [], citations: [] }
    s.appendAssistantDelta('Hello ')
    s.appendAssistantDelta('world')
    expect(s.streamingMessage.content).toBe('Hello world')
  })

  it('recordToolCall (start) appends to tool_calls and flips state', () => {
    const s = useSessionStore()
    s.streamingMessage = { role: 'assistant', content: '', tool_calls: [], citations: [] }
    s.streamState = 'streaming'
    s.recordToolCall({ kind: 'start', tool_call: { id: 't1', name: 'retrieve_chunks' } })
    expect(s.streamState).toBe('tool_running')
    expect(s.streamingMessage.tool_calls).toHaveLength(1)
    expect(s.streamingMessage.tool_calls[0].state).toBe('running')
  })

  it('recordToolCall (done) marks chip done and returns to streaming', () => {
    const s = useSessionStore()
    s.streamingMessage = {
      role: 'assistant',
      content: '',
      citations: [],
      tool_calls: [{ id: 't1', name: 'retrieve_chunks', state: 'running' }],
    }
    s.streamState = 'tool_running'
    s.recordToolCall({ kind: 'done', tool_call: { id: 't1', summary: '5 found' } })
    expect(s.streamingMessage.tool_calls[0].state).toBe('done')
    expect(s.streamingMessage.tool_calls[0].summary).toBe('5 found')
    expect(s.streamState).toBe('streaming')
  })

  it('finalizeMessage moves streamingMessage to messages[] and clears state', () => {
    const s = useSessionStore()
    s.streamingMessage = { role: 'assistant', content: 'done', tool_calls: [], citations: [] }
    s.streamState = 'streaming'
    s.finalizeMessage('msg_xyz')
    expect(s.streamingMessage).toBeNull()
    expect(s.streamState).toBe('idle')
    expect(s.messages.at(-1)).toMatchObject({
      role: 'assistant',
      content: 'done',
      message_id: 'msg_xyz',
      status: 'complete',
    })
  })

  it('handleCancelled persists partial as status=cancelled', () => {
    const s = useSessionStore()
    s.streamingMessage = { role: 'assistant', content: 'partial', tool_calls: [], citations: [] }
    s.streamState = 'stopping'
    s.handleCancelled('msg_x', 7, '0.0019')
    expect(s.streamingMessage).toBeNull()
    expect(s.streamState).toBe('idle')
    expect(s.messages.at(-1)).toMatchObject({ status: 'cancelled', content: 'partial' })
  })

  // F-14 follow-up: the max_iters / mid-turn cost-cap abort arms persist
  // 'partial' on the backend; a generic agent-loop failure persists 'error'.
  // The live handler must match so reload doesn't show something different
  // from what was on screen mid-stream.
  it('handleAbortError pushes streamed text as status=partial for a cost-cap abort', () => {
    const s = useSessionStore()
    s.streamingMessage = { role: 'assistant', content: 'draft', tool_calls: [], citations: [] }
    s.streamState = 'streaming'
    s.handleAbortError('daily_cost_cap_reached')
    expect(s.streamingMessage).toBeNull()
    expect(s.streamState).toBe('idle')
    expect(s.messages.at(-1)).toMatchObject({ status: 'partial', content: 'draft' })
  })

  // F-16: an unbounded transcript grows for the life of the page. The cap is
  // enforced on live append only, and the eviction must leave the
  // load-earlier cursor (oldest retained SERVER id) intact.
  describe('F-16 retained-history cap', () => {
    const server = (n) => ({
      role: n % 2 ? 'user' : 'assistant',
      content: `m${n}`,
      message_id: `m${n}`,
      citations: [],
      tool_calls: [],
    })

    it('evicts from the top and flags hasMoreMessages once past 200', () => {
      const s = useSessionStore()
      s.messages = Array.from({ length: 200 }, (_, i) => server(i + 1))
      s.hasMoreMessages = false
      s.streamingMessage = { role: 'assistant', content: 'new', tool_calls: [], citations: [] }
      s.streamState = 'streaming'
      s.finalizeMessage('m201')
      expect(s.messages).toHaveLength(200)
      expect(s.messages[0].message_id).toBe('m2')
      expect(s.messages.at(-1)).toMatchObject({ message_id: 'm201', content: 'new' })
      expect(s.hasMoreMessages).toBe(true)
    })

    it('does not evict at exactly 200', () => {
      const s = useSessionStore()
      s.messages = Array.from({ length: 199 }, (_, i) => server(i + 1))
      s.hasMoreMessages = false
      s.streamingMessage = { role: 'assistant', content: 'new', tool_calls: [], citations: [] }
      s.finalizeMessage('m200')
      expect(s.messages).toHaveLength(200)
      expect(s.messages[0].message_id).toBe('m1')
      expect(s.hasMoreMessages).toBe(false)
    })

    it('trims extra off the top so the oldest retained message carries a server id', () => {
      const s = useSessionStore()
      const seeded = Array.from({ length: 200 }, (_, i) => server(i + 1))
      // A live-appended user bubble (no server id yet) sitting where the
      // plain 200-wide window would start.
      delete seeded[1].message_id
      s.messages = seeded
      s.streamingMessage = { role: 'assistant', content: 'new', tool_calls: [], citations: [] }
      s.finalizeMessage('m201')
      expect(s.messages).toHaveLength(199)
      expect(s.messages[0].message_id).toBe('m3')
      expect(s.hasMoreMessages).toBe(true)
    })

    it('pages back from the oldest retained id after an eviction, and the prepend is exempt', async () => {
      const s = useSessionStore()
      s.messages = Array.from({ length: 200 }, (_, i) => server(i + 1))
      s.streamingMessage = { role: 'assistant', content: 'new', tool_calls: [], citations: [] }
      s.finalizeMessage('m201')
      expect(s.messages[0].message_id).toBe('m2')
      s.currentSessionId = 's1'

      sessionsApi.getSessionMessages.mockResolvedValueOnce({
        items: Array.from({ length: 50 }, (_, i) => ({
          id: `old${i}`,
          role: 'user',
          content: 'old',
          citations: [],
          created_at: '2026-01-01',
        })),
        has_more: true,
      })
      await s.loadEarlierMessages()
      // The cursor is the oldest RETAINED server id, so the page the server
      // returns is exactly the turns that were evicted -- no gap, no dupes.
      expect(sessionsApi.getSessionMessages).toHaveBeenCalledWith('s1', { before: 'm2' })
      // The manual prepend is deliberately not capped: the user just asked
      // for that history.
      expect(s.messages).toHaveLength(250)
      expect(s.messages[0].message_id).toBe('old0')
    })

    it('uses the oldest retained SERVER id, not messages[0], as the cursor', async () => {
      const s = useSessionStore()
      s.currentSessionId = 's1'
      s.hasMoreMessages = true
      s.messages = [
        { role: 'assistant', content: 'retained partial', status: 'error' },
        { role: 'user', content: 'local', message_id: 'pending' },
        server(7),
      ]
      sessionsApi.getSessionMessages.mockResolvedValueOnce({ items: [], has_more: false })
      await s.loadEarlierMessages()
      expect(sessionsApi.getSessionMessages).toHaveBeenCalledWith('s1', { before: 'm7' })
    })
  })

  it('handleAbortError pushes streamed text as status=partial for max_iters_reached', () => {
    const s = useSessionStore()
    s.streamingMessage = { role: 'assistant', content: 'draft', tool_calls: [], citations: [] }
    s.streamState = 'streaming'
    s.handleAbortError('max_iters_reached')
    expect(s.messages.at(-1)).toMatchObject({ status: 'partial', content: 'draft' })
  })

  it('handleAbortError pushes streamed text as status=error for a generic llm failure', () => {
    const s = useSessionStore()
    s.streamingMessage = { role: 'assistant', content: 'draft', tool_calls: [], citations: [] }
    s.streamState = 'streaming'
    s.handleAbortError('llm_failed')
    expect(s.messages.at(-1)).toMatchObject({ status: 'error', content: 'draft' })
  })

  it('handleAbortError does not push an empty bubble when nothing streamed yet', () => {
    const s = useSessionStore()
    s.streamingMessage = { role: 'assistant', content: '', tool_calls: [], citations: [] }
    s.streamState = 'streaming'
    const before = s.messages.length
    s.handleAbortError('daily_cost_cap_reached')
    expect(s.messages.length).toBe(before)
    expect(s.streamingMessage).toBeNull()
    expect(s.streamState).toBe('idle')
  })

  it('sendMessageStreaming wires through streamChat and dispatches events', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'

    const spy = vi.spyOn(streamSvc, 'streamChat').mockImplementation(async ({ onEvent }) => {
      onEvent({ event: 'assistant_delta', data: { text: 'Hi' } })
      onEvent({ event: 'done', data: { message_id: 'm1' } })
    })

    await s.sendMessageStreaming({ text: 'q' })
    expect(spy).toHaveBeenCalled()
    expect(s.messages.at(-1)).toMatchObject({ message_id: 'm1' })
  })

  // #354: live stream and reload converge on the same message field.
  const TOPIC_CARD = {
    mode: 'broad',
    topic: 'Thermodynamics',
    items: [{ label: 'Entropy', hint: null }],
  }

  it('carries a topic_suggestions event onto the finalized message', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(async ({ onEvent }) => {
      onEvent({ event: 'assistant_delta', data: { text: 'Energy moves.' } })
      onEvent({ event: 'topic_suggestions', data: TOPIC_CARD })
      onEvent({ event: 'done', data: { message_id: 'm1' } })
    })
    await s.sendMessageStreaming({ text: 'I am a beginner' })
    expect(s.messages.at(-1)).toMatchObject({
      role: 'assistant',
      message_id: 'm1',
      topic_suggestions: TOPIC_CARD,
    })
  })

  it('carries a topic_suggestions event from the check follow-up stream', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    s.handleCheckQuestion({ gap: 'g', total: 1, items: [{ question: 'Q', options: ['a'] }] })
    vi.spyOn(streamSvc, 'streamCheckComplete').mockImplementation(async ({ onEvent }) => {
      onEvent({ event: 'assistant_delta', data: { text: 'You are intermediate.' } })
      onEvent({ event: 'topic_suggestions', data: TOPIC_CARD })
      onEvent({ event: 'done', data: { message_id: 'm2' } })
    })
    await s.completeCheck()
    expect(s.messages.at(-1)).toMatchObject({ message_id: 'm2', topic_suggestions: TOPIC_CARD })
  })

  it('maps topic_suggestions from session detail on reload', async () => {
    sessionsApi.getSession.mockResolvedValueOnce({
      id: 's1',
      messages: [
        {
          id: 'm1',
          role: 'assistant',
          content: 'Energy moves.',
          created_at: '2026-01-01',
          topic_suggestions: TOPIC_CARD,
        },
        { id: 'm2', role: 'user', content: 'hi', created_at: '2026-01-02' },
      ],
    })
    const s = useSessionStore()
    await s.loadSession('s1')
    expect(s.messages[0].topic_suggestions).toEqual(TOPIC_CARD)
    expect(s.messages[1].topic_suggestions).toBeNull()
  })

  it('forwards reviewGaps to streamChat as review_gaps', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    const spy = vi.spyOn(streamSvc, 'streamChat').mockResolvedValue(undefined)
    await s.sendMessageStreaming({ text: 'Review my gaps', reviewGaps: true })
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({ reviewGaps: true, message: 'Review my gaps' }),
    )
  })

  it('forwards reviewGap to streamChat as review_gap', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    const spy = vi.spyOn(streamSvc, 'streamChat').mockResolvedValue(undefined)
    await s.sendMessageStreaming({
      text: 'Review my gap: recursion',
      reviewGaps: true,
      reviewGap: 'recursion',
    })
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ reviewGap: 'recursion' }))
  })

  it('continueTopic creates a resume session and marks the prior ended locally', async () => {
    sessionsApi.createSession.mockResolvedValueOnce({ id: 'new-1', topic: 'Calculus' })
    const s = useSessionStore()
    s.sessions = [{ id: 'old-1', topic: 'Calculus', ended_at: null }]
    const created = await s.continueTopic({ id: 'old-1', topic: 'Calculus' })
    expect(sessionsApi.createSession).toHaveBeenCalledWith({
      topic: 'Calculus',
      seedMode: 'resume',
      priorSessionId: 'old-1',
    })
    expect(created.id).toBe('new-1')
    expect(s.sessions.find((x) => x.id === 'old-1').ended_at).toBeTruthy()
  })

  it('continueTopic moves the prior total from active to ended when the prior was locally known active', async () => {
    sessionsApi.createSession.mockResolvedValueOnce({ id: 'new-1', topic: 'Calculus' })
    const s = useSessionStore()
    s.sessions = [{ id: 'old-1', topic: 'Calculus', ended_at: null }]
    s.activeTotal = 3 // includes old-1
    s.endedTotal = 1
    await s.continueTopic({ id: 'old-1', topic: 'Calculus' })
    // net: +1 for the new session, -1 for the prior leaving active = unchanged
    expect(s.activeTotal).toBe(3)
    expect(s.endedTotal).toBe(2)
  })

  it('continueTopic only counts the new session when the prior row is observably already ended (the normal case)', async () => {
    sessionsApi.createSession.mockResolvedValueOnce({ id: 'new-1', topic: 'Calculus' })
    const s = useSessionStore()
    // Prior is outside the loaded window, but the caller hands over the row it
    // rendered (library page / sidebar ended tab) and that row says "ended" --
    // an observation, so no active->ended transition is counted.
    s.sessions = []
    s.activeTotal = 3
    s.endedTotal = 1
    await s.continueTopic({ id: 'old-1', topic: 'Calculus', ended_at: '2026-01-01T00:00:00Z' })
    expect(s.activeTotal).toBe(4)
    expect(s.endedTotal).toBe(1)
  })

  it('continueTopic counts the prior transition when the caller-held row is observably still active, even outside the window', async () => {
    sessionsApi.createSession.mockResolvedValueOnce({ id: 'new-1', topic: 'Calculus' })
    const s = useSessionStore()
    s.sessions = [] // outside the loaded 20+20 window
    s.activeTotal = 3
    s.endedTotal = 1
    const prior = { id: 'old-1', topic: 'Calculus', ended_at: null }
    await s.continueTopic(prior)
    // net: +1 for the new session, -1 for the prior leaving active = unchanged
    expect(s.activeTotal).toBe(3)
    expect(s.endedTotal).toBe(2)
    // the caller's row is patched too, so whatever rendered it shows ended
    expect(prior.ended_at).toBeTruthy()
  })

  it('sendMessageStreaming rejects without an active session', async () => {
    const s = useSessionStore()
    await expect(s.sendMessageStreaming({ text: 'x' })).rejects.toThrow('no active session')
  })

  it('sendMessageStreaming returns null when text is empty', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    const out = await s.sendMessageStreaming({ text: '  ' })
    expect(out).toBeNull()
  })

  it('sendMessageStreaming appends citations and tool_calls from stream events on success', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(async ({ onEvent }) => {
      onEvent({ event: 'tool_call_start', data: { id: 't1', name: 'retrieve_chunks' } })
      onEvent({ event: 'tool_call_done', data: { id: 't1', summary: '5 found' } })
      onEvent({ event: 'assistant_delta', data: { text: 'hi' } })
      onEvent({ event: 'citations', data: [{ doc_id: 'd1', text: 't' }] })
      onEvent({ event: 'done', data: { message_id: 'm1' } })
    })
    await s.sendMessageStreaming({ text: 'hello' })
    expect(s.messages).toHaveLength(2)
    expect(s.messages[1].role).toBe('assistant')
    expect(s.messages[1].citations[0].doc_id).toBe('d1')
    expect(s.messages[1].tool_calls[0].summary).toBe('5 found')
  })

  // Streaming path now maps the 429 envelope into dailyCapInfo via
  // lib/capErrors.js (slice 2) -- parity with the removed non-streaming chain.
  it('sendMessageStreaming maps a daily-cap 429 into dailyCapInfo and store error', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockRejectedValueOnce(
      new ApiErrorLike(429, {
        detail: { code: ERR_DAILY_CAP_REACHED, cap: 10, used: 10, resets_at: '2026-01-02' },
      }),
    )
    await expect(s.sendMessageStreaming({ text: 'x' })).rejects.toThrow('api error')
    expect(s.error).toBeTruthy()
    expect(s.dailyCapInfo).toEqual({ cap: 10, used: 10, resets_at: '2026-01-02' })
    expect(s.dailyCapReached).toBe(true)
    expect(s.streamState).toBe('idle')
    expect(s.streamingMessage).toBeNull()
  })

  // I-10: a send rejected before the stream starts must not strand the
  // optimistic user bubble in the transcript.
  it('pops the optimistic user bubble on pre-stream HTTP failure', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockRejectedValueOnce(
      new ApiErrorLike(422, { detail: 'too long' }),
    )
    await s.sendMessageStreaming({ text: 'hi' }).catch(() => {})
    expect(s.messages.filter((m) => m.role === 'user' && m.content === 'hi')).toHaveLength(0)
  })

  // F-21: the optimistic row carried no id at all, so MessageList keyed it on
  // its array index - two sends in a row shared a key until the server ids
  // landed, and the failure pop matched "the last row with no message_id".
  describe('optimistic user row client_id (F-21)', () => {
    it('gives every optimistic user row a distinct client_id and no message_id', async () => {
      const s = useSessionStore()
      s.currentSessionId = 's1'
      vi.spyOn(streamSvc, 'streamChat').mockImplementation(async ({ onEvent }) => {
        onEvent({ event: 'done', data: { message_id: 'a1' } })
      })
      await s.sendMessageStreaming({ text: 'one' })
      await s.sendMessageStreaming({ text: 'two' })
      const users = s.messages.filter((m) => m.role === 'user')
      expect(users).toHaveLength(2)
      expect(users[0].client_id).toBeTruthy()
      expect(users[1].client_id).toBeTruthy()
      expect(users[0].client_id).not.toBe(users[1].client_id)
      // The cursor guard (_hasServerId) reads message_id, so a client value
      // must never be written there.
      expect(users[0].message_id).toBeUndefined()
      expect(users[1].message_id).toBeUndefined()
    })

    // The discriminating case: the old "last user row with no message_id" rule
    // pops whatever happens to be last, which is not necessarily this send's
    // row once anything else has landed behind it.
    it('pops this send row, not the last id-less row', async () => {
      const s = useSessionStore()
      s.currentSessionId = 's1'
      vi.spyOn(streamSvc, 'streamChat').mockImplementationOnce(async () => {
        s.messages.push({ role: 'user', content: 'other' })
        throw new ApiErrorLike(422, { detail: 'too long' })
      })
      await s.sendMessageStreaming({ text: 'dropped' }).catch(() => {})
      expect(s.messages.filter((m) => m.role === 'user').map((m) => m.content)).toEqual(['other'])
    })

    it('pops the failed row by client_id and leaves earlier rows alone', async () => {
      const s = useSessionStore()
      s.currentSessionId = 's1'
      vi.spyOn(streamSvc, 'streamChat').mockImplementationOnce(async ({ onEvent }) => {
        onEvent({ event: 'done', data: { message_id: 'a1' } })
      })
      await s.sendMessageStreaming({ text: 'kept' })
      const keptId = s.messages.find((m) => m.role === 'user').client_id
      vi.spyOn(streamSvc, 'streamChat').mockRejectedValueOnce(
        new ApiErrorLike(422, { detail: 'too long' }),
      )
      await s.sendMessageStreaming({ text: 'dropped' }).catch(() => {})
      const users = s.messages.filter((m) => m.role === 'user')
      expect(users).toHaveLength(1)
      expect(users[0].content).toBe('kept')
      expect(users[0].client_id).toBe(keptId)
    })
  })

  it('maps a session_ended 409 to a friendly error and marks the session ended', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    s.currentSession = { id: 's1', ended_at: null }
    vi.spyOn(streamSvc, 'streamChat').mockRejectedValueOnce(
      Object.assign(new Error('conflict'), {
        status: 409,
        body: { detail: { code: 'session_ended' } },
      }),
    )
    await expect(s.sendMessageStreaming({ text: 'hello' })).rejects.toBeInstanceOf(
      StreamAbortedError,
    )
    expect(s.error).toMatch(/ended/i)
    expect(s.streamState).toBe('idle')
    expect(s.currentSession.ended_at).not.toBeNull()
  })

  // I-10 follow-up: a session_ended 409 is a pre-stream failure and must
  // drop the stranded optimistic bubble, not leave an unpersisted message.
  it('pops the optimistic user bubble on a pre-stream session_ended 409', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    s.currentSession = { id: 's1', ended_at: null }
    vi.spyOn(streamSvc, 'streamChat').mockRejectedValueOnce(
      Object.assign(new Error('conflict'), {
        status: 409,
        body: { detail: { code: 'session_ended' } },
      }),
    )
    await expect(s.sendMessageStreaming({ text: 'hello' })).rejects.toBeInstanceOf(
      StreamAbortedError,
    )
    expect(s.messages.filter((m) => m.role === 'user' && m.content === 'hello')).toHaveLength(0)
  })

  // E-05: sign-out on a 401 resets the store mid-stream, which makes the
  // stream look superseded. The store must still reject so the view can stash
  // the draft before the login redirect unmounts it.
  it('sendMessageStreaming throws StreamAbortedError(auth_expired) on 401, even after store reset', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(async () => {
      s.reset() // simulates _onAuthExpired -> signOut -> reset() nulling currentSessionId
      throw Object.assign(new Error('API 401'), { status: 401 })
    })
    await expect(s.sendMessageStreaming({ text: 'long draft' })).rejects.toSatisfy(
      (e) => e instanceof StreamAbortedError && e.reason === 'auth_expired',
    )
  })

  // E-11: the 409 arm keeps its cleanup but now rethrows so the view restores
  // the draft instead of running its success path.
  it('sendMessageStreaming throws StreamAbortedError(session_ended) on 409 and keeps the banner', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    s.currentSession = { id: 's1', ended_at: null }
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(async () => {
      throw Object.assign(new Error('API 409'), {
        status: 409,
        body: { detail: { code: 'session_ended' } },
      })
    })
    await expect(s.sendMessageStreaming({ text: 'q' })).rejects.toSatisfy(
      (e) => e instanceof StreamAbortedError && e.reason === 'session_ended',
    )
    expect(s.error).toMatch(/ended elsewhere/)
    expect(s.currentSession.ended_at).toBeTruthy()
    expect(s.streamState).toBe('idle')
  })

  it('sendMessageStreaming stays silent on genuine navigation supersede', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(async () => {
      s.currentSessionId = 's2' // user opened another session mid-stream
      throw Object.assign(new Error('boom'), { status: 500 })
    })
    await expect(s.sendMessageStreaming({ text: 'q' })).resolves.toBeUndefined()
    expect(s.error).toBeNull()
  })

  it('sendMessageStreaming maps a mid-turn SSE cost-cap error event into costCapInfo', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(async ({ onEvent }) => {
      onEvent({ event: 'assistant_delta', data: { text: 'partial' } })
      onEvent({
        event: 'error',
        data: {
          code: ERR_DAILY_COST_CAP_REACHED,
          used_usd: '3.0100',
          soft_cap_usd: '2.0',
          hard_cap_usd: '3.0',
        },
      })
    })
    await s.sendMessageStreaming({ text: 'x' })
    expect(s.costCapInfo).toEqual({
      used_usd: '3.0100',
      soft_cap_usd: '2.0',
      hard_cap_usd: '3.0',
      resets_at: null,
      scope: 'user',
    })
    expect(s.costCapReached).toBe(true)
    expect(s.streamState).toBe('idle')
    // F-14 follow-up: the streamed text must survive onto the transcript,
    // not just clear the cap banner state.
    expect(s.messages.at(-1)).toMatchObject({ status: 'partial', content: 'partial' })
    // E-04: CapBanners already renders this failure, so the generic error
    // banner must stay quiet rather than say the same thing twice.
    expect(s.error).toBeNull()
  })

  // E-04: the non-cap arm of the same handler. Both stream loops route their
  // SSE `error` event through it, so a bare code can no longer reach the
  // banner verbatim (it used to render `data.message || data.code`).
  it('sendMessageStreaming renders coded copy for a non-cap SSE error event', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(async ({ onEvent }) => {
      onEvent({ event: 'assistant_delta', data: { text: 'half a thought' } })
      onEvent({ event: 'error', data: { code: 'tool_failed' } })
    })
    await s.sendMessageStreaming({ text: 'x' })
    expect(s.error).toMatch(/could not finish that step/i)
    expect(s.error).not.toMatch(/tool_failed/)
    expect(s.dailyCapInfo).toBeNull()
    expect(s.costCapInfo).toBeNull()
    expect(s.streamState).toBe('idle')
    expect(s.streamingMessage).toBeNull()
    // Not a PARTIAL_ABORT_CODE, so the retained text lands on 'error'.
    expect(s.messages.at(-1)).toMatchObject({ status: 'error', content: 'half a thought' })
  })

  // E-04: the check-complete loop shares the same handler; asserting it here
  // is what stops the two `case 'error'` blocks from drifting apart again.
  it('completeCheck renders coded copy for a non-cap SSE error event', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    s.pendingCheck = { gap: 'g', total: 1, currentIndex: 1, viewIndex: 0, items: [] }
    vi.spyOn(streamSvc, 'streamCheckComplete').mockImplementation(async ({ onEvent }) => {
      onEvent({ event: 'assistant_delta', data: { text: 'half a thought' } })
      onEvent({ event: 'error', data: { code: 'tool_failed' } })
    })
    await s.completeCheck()
    expect(s.error).toMatch(/could not finish that step/i)
    expect(s.streamState).toBe('idle')
    expect(s.messages.at(-1)).toMatchObject({ status: 'error', content: 'half a thought' })
  })

  // E-03: a transport failure mid-stream used to discard text the learner had
  // already watched stream, while the same text survived an SSE-reported
  // failure. Both now go through _settleWithError.
  it('sendMessageStreaming retains the streamed partial on a transport failure', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(async ({ onEvent }) => {
      onEvent({ event: 'assistant_delta', data: { text: 'half a thought' } })
      throw Object.assign(new Error('boom'), { status: 500 })
    })
    await expect(s.sendMessageStreaming({ text: 'q' })).rejects.toMatchObject({ status: 500 })
    expect(s.messages.at(-1)).toMatchObject({ status: 'error', content: 'half a thought' })
    expect(s.error).toBeTruthy()
    expect(s.streamingMessage).toBeNull()
    expect(s.streamState).toBe('idle')
  })

  it('sendMessageStreaming retains the streamed partial on a status-0 network drop', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(async ({ onEvent }) => {
      onEvent({ event: 'assistant_delta', data: { text: 'half a thought' } })
      throw new ApiErrorLike(0, { detail: 'network error' })
    })
    await expect(s.sendMessageStreaming({ text: 'q' })).rejects.toMatchObject({ status: 0 })
    expect(s.messages.at(-1)).toMatchObject({ status: 'error', content: 'half a thought' })
    expect(s.error).toMatch(/can't reach the server/i)
  })

  it('sendMessageStreaming appends nothing when the transport dies before any delta', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(async () => {
      throw new ApiErrorLike(0, { detail: 'network error' })
    })
    await expect(s.sendMessageStreaming({ text: 'q' })).rejects.toMatchObject({ status: 0 })
    expect(s.messages.some((m) => m.role === 'assistant')).toBe(false)
  })

  it('resets stream state when the stream ends without a terminal event', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(async ({ onEvent }) => {
      onEvent({ event: 'assistant_delta', data: { text: 'partial' } })
      // resolves without emitting done/cancelled/error -- simulates a dropped connection
    })
    await s.sendMessageStreaming({ text: 'hello' })
    expect(s.streamState).toBe('idle')
    expect(s.streamingMessage).toBeNull()
    expect(s.error).toBeTruthy()
  })

  it('stopStream invokes abortController.abort() and transitions to stopping', () => {
    const s = useSessionStore()
    const abort = vi.fn()
    s.abortController = { abort }
    s.streamState = 'streaming'
    s.stopStream()
    expect(abort).toHaveBeenCalled()
    expect(s.streamState).toBe('stopping')
  })

  // F-04: both stream starters write through the shared streamingMessage /
  // abortController, so a second start while one is live would interleave
  // two SSE streams into a single bubble.
  it('completeCheck does not start while another stream is live (F-04)', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    s.pendingCheck = { gap: 'g', total: 1, currentIndex: 1, viewIndex: 0, items: [] }
    s.streamingMessage = { role: 'assistant', content: 'live', tool_calls: [], citations: [] }
    s.streamState = 'streaming'
    const spy = vi.spyOn(streamSvc, 'streamCheckComplete').mockResolvedValue(undefined)
    await s.completeCheck()
    expect(spy).not.toHaveBeenCalled()
    expect(s.pendingCheck).not.toBeNull()
    expect(s.streamingMessage.content).toBe('live')
  })

  it('sendMessageStreaming refuses to start while another stream is live (F-04)', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    s.streamState = 'streaming'
    const spy = vi.spyOn(streamSvc, 'streamChat').mockResolvedValue(undefined)
    const out = await s.sendMessageStreaming({ text: 'x' })
    expect(out).toBeNull()
    expect(spy).not.toHaveBeenCalled()
  })

  // F-01: a stream that outlives a session switch must not deliver its
  // output, errors, or notices into the session now being viewed.
  it('a stream that emits done after a session switch delivers nothing (F-01)', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    let emit, finish
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(
      ({ onEvent }) =>
        new Promise((resolve) => {
          emit = onEvent
          finish = resolve
        }),
    )
    const p = s.sendMessageStreaming({ text: 'q' })
    emit({ event: 'assistant_delta', data: { text: 'late reply' } })
    s.currentSessionId = 's2' // user switched sessions mid-stream
    emit({ event: 'done', data: { message_id: 'm-late' } })
    finish()
    await p
    expect(s.messages.some((m) => m.message_id === 'm-late')).toBe(false)
    expect(s.messages.some((m) => m.role === 'assistant')).toBe(false)
    expect(s.streamingMessage).toBeNull()
    expect(s.streamState).toBe('idle')
  })

  it('a superseded stream error does not surface over the new session (F-01)', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    let emit, finish
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(
      ({ onEvent }) =>
        new Promise((resolve) => {
          emit = onEvent
          finish = resolve
        }),
    )
    const p = s.sendMessageStreaming({ text: 'q' })
    s.currentSessionId = 's2'
    emit({ event: 'error', data: { code: 'llm_failed', message: 'boom' } })
    finish()
    await p
    expect(s.error).toBeNull()
    expect(s.messages.some((m) => m.role === 'assistant')).toBe(false)
    expect(s.streamState).toBe('idle')
  })

  // Dup-key fix: the local AbortError path appends a row with the literal
  // message_id 'pending'. MessageList falls back to client_id when
  // message_id is 'pending', so this row must carry one (two Stop clicks in
  // one session would otherwise produce duplicate keys).
  it('the local-cancel path (AbortError) appends a row with a client_id (dup-key fix)', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(
      ({ signal }) =>
        new Promise((_res, rej) => {
          signal.addEventListener('abort', () =>
            rej(Object.assign(new Error('aborted'), { name: 'AbortError' })),
          )
        }),
    )
    const p = s.sendMessageStreaming({ text: 'q' })
    s.stopStream()
    await p
    const row = s.messages.find((m) => m.role === 'assistant')
    expect(row).toBeDefined()
    expect(row.message_id).toBe('pending')
    expect(row.client_id).toMatch(/^c-/)
  })

  it('abandonStream aborts silently without persisting a cancelled bubble (F-01)', async () => {
    const s = useSessionStore()
    s.currentSessionId = 's1'
    vi.spyOn(streamSvc, 'streamChat').mockImplementation(
      ({ signal }) =>
        new Promise((_res, rej) => {
          signal.addEventListener('abort', () =>
            rej(Object.assign(new Error('aborted'), { name: 'AbortError' })),
          )
        }),
    )
    const p = s.sendMessageStreaming({ text: 'q' })
    s.abandonStream()
    await p
    expect(s.messages.some((m) => m.role === 'assistant')).toBe(false)
    expect(s.messages.some((m) => m.status === 'cancelled')).toBe(false)
    expect(s.error).toBeNull()
    expect(s.streamState).toBe('idle')
    expect(s.streamingMessage).toBeNull()
  })

  it('loadSession to a different id abandons the in-flight stream (F-01)', async () => {
    sessionsApi.getSession.mockResolvedValueOnce({ id: 's2', messages: [] })
    const s = useSessionStore()
    s.currentSessionId = 's1'
    const abort = vi.fn()
    s.abortController = { abort }
    s.streamingMessage = { role: 'assistant', content: 'x', tool_calls: [], citations: [] }
    s.streamState = 'streaming'
    await s.loadSession('s2')
    expect(abort).toHaveBeenCalled()
    expect(s.streamingMessage).toBeNull()
    expect(s.messages.some((m) => m.role === 'assistant')).toBe(false)
  })

  it('loadSession with the same id does not abort the in-flight stream', async () => {
    sessionsApi.getSession.mockResolvedValueOnce({ id: 's1', messages: [] })
    const s = useSessionStore()
    s.currentSessionId = 's1'
    const abort = vi.fn()
    s.abortController = { abort }
    await s.loadSession('s1')
    expect(abort).not.toHaveBeenCalled()
  })
})

// The sidebar renders `searchRows` directly, and those rows routinely
// describe sessions outside the 20+20 `sessions` window. A mutating action
// that patched only `sessions` would leave the rendered row untouched -- and
// since the server treats end/reopen as idempotent (200 on replay), the user
// would re-fire the action and skew the totals mirror on every retry.
describe('session store - search rows are first-class mutation targets', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('endSession patches a search row for a session outside the loaded window', async () => {
    sessionsApi.endSession.mockResolvedValueOnce({ ended_at: '2026-01-01', summary: null })
    const s = useSessionStore()
    s.sessions = []
    s.searchRows = [{ id: 'out-1', topic: 'Glycolysis', ended_at: null }]
    await s.endSession('out-1')
    expect(s.searchRows[0].ended_at).toBe('2026-01-01')
  })

  it('a replayed endSession on an already-ended search row does not move the totals twice', async () => {
    sessionsApi.endSession.mockResolvedValue({ ended_at: '2026-01-01', summary: null })
    const s = useSessionStore()
    s.sessions = []
    s.searchRows = [{ id: 'out-1', topic: 'Glycolysis', ended_at: null }]
    s.activeTotal = 5
    s.endedTotal = 2
    await s.endSession('out-1')
    expect(s.activeTotal).toBe(4)
    expect(s.endedTotal).toBe(3)
    // Replay: the server answers 200 again (F-30 idempotent end), but the row
    // is now observably ended, so the transition must not be counted again.
    await s.endSession('out-1')
    expect(s.activeTotal).toBe(4)
    expect(s.endedTotal).toBe(3)
  })

  it('reopenSession patches a search row and does not move the totals twice on replay', async () => {
    sessionsApi.reopenSession.mockResolvedValue({ ok: true })
    const s = useSessionStore()
    s.sessions = []
    s.searchRows = [{ id: 'out-1', topic: 'Glycolysis', ended_at: '2026-01-01' }]
    s.activeTotal = 2
    s.endedTotal = 5
    await s.reopenSession('out-1')
    expect(s.searchRows[0].ended_at).toBeNull()
    expect(s.activeTotal).toBe(3)
    expect(s.endedTotal).toBe(4)
    await s.reopenSession('out-1')
    expect(s.activeTotal).toBe(3)
    expect(s.endedTotal).toBe(4)
  })

  it('renameSession patches a search row and rolls it back on failure', async () => {
    const s = useSessionStore()
    s.sessions = []
    s.searchRows = [{ id: 'out-1', topic: 'Old name', ended_at: null }]
    let reject
    sessionsApi.renameSession.mockReturnValue(
      new Promise((_, r) => {
        reject = r
      }),
    )
    const p = s.renameSession('out-1', 'New name').catch(() => {})
    // Optimistic patch must land on the search row BEFORE the API settles --
    // this is what proves the row a user sees actually updates, not just that
    // a failure rolls back to a value indistinguishable from untouched.
    expect(s.searchRows[0].topic).toBe('New name')
    reject(new Error('nope'))
    await p
    expect(s.searchRows[0].topic).toBe('Old name')
  })

  it('renameSession rolls each held copy back to its own previous value', async () => {
    const s = useSessionStore()
    // The window copy and the search copy can legitimately disagree (the search
    // response is fresher). A single shared `prev` would corrupt one of them.
    s.sessions = [{ id: 'out-1', topic: 'Window name', ended_at: null }]
    s.searchRows = [{ id: 'out-1', topic: 'Search name', ended_at: null }]
    let reject
    sessionsApi.renameSession.mockReturnValue(
      new Promise((_, r) => {
        reject = r
      }),
    )
    const p = s.renameSession('out-1', 'New name').catch(() => {})
    expect(s.sessions[0].topic).toBe('New name')
    expect(s.searchRows[0].topic).toBe('New name')
    reject(new Error('nope'))
    await p
    expect(s.sessions[0].topic).toBe('Window name')
    expect(s.searchRows[0].topic).toBe('Search name')
  })

  it('setPinned patches a search row and rolls it back on failure', async () => {
    const s = useSessionStore()
    s.sessions = []
    s.searchRows = [{ id: 'out-1', topic: 'X', ended_at: null, pinned: false }]
    let reject
    sessionsApi.setPinned.mockReturnValue(
      new Promise((_, r) => {
        reject = r
      }),
    )
    const p = s.setPinned('out-1', true).catch(() => {})
    expect(s.searchRows[0].pinned).toBe(true)
    reject(new Error('nope'))
    await p
    expect(s.searchRows[0].pinned).toBe(false)
  })

  it('reset() clears searchRows', () => {
    const s = useSessionStore()
    s.searchRows = [{ id: 'out-1', topic: 'X', ended_at: null }]
    s.reset()
    expect(s.searchRows).toEqual([])
  })

  describe('loadEarlierMessages', () => {
    it('prepends the older page and updates hasMoreMessages', async () => {
      sessionsApi.getSession.mockResolvedValue({
        id: 's1',
        messages: [
          {
            id: 50,
            role: 'user',
            content: 'newest',
            citations: [],
            created_at: 'now',
            status: null,
            check_batch: null,
          },
        ],
        has_more_messages: true,
        pending_check: null,
      })
      const store = useSessionStore()
      await store.loadSession('s1')
      expect(store.hasMoreMessages).toBe(true)

      sessionsApi.getSessionMessages.mockResolvedValue({
        items: [
          {
            id: 20,
            role: 'assistant',
            content: 'older',
            citations: [],
            created_at: 'then',
            status: null,
            check_batch: null,
          },
        ],
        has_more: false,
      })
      await store.loadEarlierMessages()

      expect(sessionsApi.getSessionMessages).toHaveBeenCalledWith('s1', { before: 50 })
      expect(store.messages.map((m) => m.message_id)).toEqual([20, 50])
      expect(store.hasMoreMessages).toBe(false)
      expect(store.loadingEarlier).toBe(false)
    })

    it('is a no-op when hasMoreMessages is false', async () => {
      const store = useSessionStore()
      await store.loadEarlierMessages()
      expect(sessionsApi.getSessionMessages).not.toHaveBeenCalled()
    })

    it('records an inline error and keeps messages on failure', async () => {
      sessionsApi.getSession.mockResolvedValue({
        id: 's1',
        messages: [
          {
            id: 50,
            role: 'user',
            content: 'newest',
            citations: [],
            created_at: 'now',
            status: null,
            check_batch: null,
          },
        ],
        has_more_messages: true,
        pending_check: null,
      })
      const store = useSessionStore()
      await store.loadSession('s1')

      sessionsApi.getSessionMessages.mockRejectedValue(new Error('boom'))
      await store.loadEarlierMessages()

      expect(store.loadEarlierError).toBeTruthy()
      expect(store.messages).toHaveLength(1)
      expect(store.hasMoreMessages).toBe(true)
    })
  })

  describe('lookupTopic', () => {
    it('returns lookup payload', async () => {
      sessionsApi.lookupTopic.mockResolvedValue({
        active_match: null,
        ended_match: { session_id: 'e1' },
      })
      const store = useSessionStore()
      const res = await store.lookupTopic('css')
      expect(sessionsApi.lookupTopic).toHaveBeenCalledWith('css')
      expect(res.ended_match.session_id).toBe('e1')
    })

    it('returns null on failure without setting store error', async () => {
      sessionsApi.lookupTopic.mockRejectedValue(new Error('boom'))
      const store = useSessionStore()
      const res = await store.lookupTopic('css')
      expect(res).toBeNull()
      expect(store.error).toBeNull()
    })
  })

  describe('createSession declaredLevel', () => {
    it('passes declared_level through', async () => {
      sessionsApi.createSession.mockResolvedValue({ id: 'n1' })
      const store = useSessionStore()
      await store.createSession({
        topic: 't',
        seedMode: 'fresh',
        priorSessionId: null,
        declaredLevel: 'advanced',
      })
      expect(sessionsApi.createSession).toHaveBeenCalledWith(
        expect.objectContaining({ declaredLevel: 'advanced' }),
      )
    })
  })
})
