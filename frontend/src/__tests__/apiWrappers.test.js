import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import * as sessionsApi from '@/services/sessionsApi.js'
import { getSessionProfile } from '@/services/profileApi.js'
import { errorBus } from '@/services/errorBus.js'

describe('api wrappers', () => {
  let fetchMock
  let listener
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchMock = vi.fn()
    globalThis.fetch = fetchMock
    listener = vi.fn()
    errorBus.addEventListener('api-error', listener)
  })
  afterEach(() => {
    errorBus.removeEventListener('api-error', listener)
    vi.restoreAllMocks()
  })

  function ok(body) {
    return Promise.resolve({
      ok: true,
      status: 200,
      text: () => Promise.resolve(JSON.stringify(body)),
    })
  }

  // Phase 7: user_id is no longer carried in any payload — the backend
  // resolves it from the Authorization header.

  it('createSession posts topic + seed_mode (no user_id)', async () => {
    fetchMock.mockReturnValueOnce(ok({ id: 's1' }))
    await sessionsApi.createSession({ topic: 't', seedMode: 'm' })
    const init = fetchMock.mock.calls[0][1]
    const body = JSON.parse(init.body)
    expect(body.user_id).toBeUndefined()
    expect(body.topic).toBe('t')
    expect(body.seed_mode).toBe('m')
    expect(body.prior_session_id).toBeNull()
  })

  it('listSessions hits /sessions without user_id query', async () => {
    fetchMock.mockReturnValueOnce(ok([]))
    await sessionsApi.listSessions()
    expect(fetchMock.mock.calls[0][0]).not.toContain('user_id=')
    expect(fetchMock.mock.calls[0][0]).not.toContain('limit=')
    expect(fetchMock.mock.calls[0][0]).not.toContain('offset=')
  })

  it('listSessions forwards limit/offset when given (F-06)', async () => {
    fetchMock.mockReturnValueOnce(ok([]))
    await sessionsApi.listSessions({ limit: 5, offset: 10 })
    expect(fetchMock.mock.calls[0][0]).toContain('limit=5')
    expect(fetchMock.mock.calls[0][0]).toContain('offset=10')
  })

  it('getSession hits /sessions/:id without user_id query', async () => {
    fetchMock.mockReturnValueOnce(ok({ id: 's1' }))
    await sessionsApi.getSession('s1')
    expect(fetchMock.mock.calls[0][0]).toContain('/sessions/s1')
    expect(fetchMock.mock.calls[0][0]).not.toContain('user_id=')
  })

  it('endSession POSTs to /end without user_id query', async () => {
    fetchMock.mockReturnValueOnce(ok({ ended_at: 'x' }))
    await sessionsApi.endSession('s1')
    expect(fetchMock.mock.calls[0][0]).toContain('/sessions/s1/end')
    expect(fetchMock.mock.calls[0][0]).not.toContain('user_id=')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
  })

  it('reopenSession POSTs to /reopen without user_id query', async () => {
    fetchMock.mockReturnValueOnce(ok({ ok: true }))
    await sessionsApi.reopenSession('s1')
    expect(fetchMock.mock.calls[0][0]).toContain('/sessions/s1/reopen')
    expect(fetchMock.mock.calls[0][0]).not.toContain('user_id=')
  })

  it('getSessionProfile hits /profile/:id without user_id query', async () => {
    fetchMock.mockReturnValueOnce(ok({}))
    await getSessionProfile('s1')
    expect(fetchMock.mock.calls[0][0]).toContain('/profile/s1')
    expect(fetchMock.mock.calls[0][0]).not.toContain('user_id=')
  })
})
