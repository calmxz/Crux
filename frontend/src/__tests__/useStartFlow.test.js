import { describe, it, expect, beforeEach, vi } from 'vitest'

import { useStartFlow } from '@/composables/useStartFlow.js'

function makeStore(overrides = {}) {
  return {
    lookupTopic: vi.fn().mockResolvedValue({ active_match: null, ended_match: null }),
    createSession: vi.fn().mockResolvedValue({ id: 'new1' }),
    continueTopic: vi.fn().mockResolvedValue({ id: 'res1' }),
    ...overrides,
  }
}

const router = { push: vi.fn() }

beforeEach(() => router.push.mockClear())

describe('useStartFlow', () => {
  it('no match: begin creates a session directly and navigates', async () => {
    const store = makeStore()
    const flow = useStartFlow({ store, router })
    await flow.begin('new topic')
    expect(store.createSession).toHaveBeenCalledWith(
      expect.objectContaining({ topic: 'new topic', seedMode: 'fresh' }),
    )
    expect(router.push).toHaveBeenCalledWith({ name: 'session', params: { id: 'new1' } })
  })

  it('lookup failure (null) falls through to direct create', async () => {
    const store = makeStore({ lookupTopic: vi.fn().mockResolvedValue(null) })
    const flow = useStartFlow({ store, router })
    await flow.begin('t')
    expect(store.createSession).toHaveBeenCalled()
    expect(router.push).toHaveBeenCalledWith({ name: 'session', params: { id: 'new1' } })
  })

  it('active match: intercept stage, openExisting navigates', async () => {
    const store = makeStore({
      lookupTopic: vi.fn().mockResolvedValue({
        active_match: { session_id: 'a1', title: 'CSS' },
        ended_match: null,
      }),
    })

    const flow = useStartFlow({ store, router })
    await flow.begin('css')
    expect(flow.stage.value).toBe('intercept')
    expect(flow.interceptKind.value).toBe('active')
    expect(store.createSession).not.toHaveBeenCalled()
    flow.openExisting()
    expect(router.push).toHaveBeenCalledWith({ name: 'session', params: { id: 'a1' } })
  })

  it('ended match: continuePrior resumes and navigates', async () => {
    const store = makeStore({
      lookupTopic: vi.fn().mockResolvedValue({
        active_match: null,
        ended_match: {
          session_id: 'e1',
          title: 'CSS',
          gap_count: 2,
          ended_at: '2026-07-29T00:00:00Z',
        },
      }),
    })

    const flow = useStartFlow({ store, router })
    await flow.begin('css')
    expect(flow.interceptKind.value).toBe('ended')
    await flow.continuePrior()
    expect(store.continueTopic).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'e1', topic: 'CSS', ended_at: '2026-07-29T00:00:00Z' }),
    )
    expect(router.push).toHaveBeenCalledWith({ name: 'session', params: { id: 'res1' } })
  })

  it('startFresh from intercept creates a session and navigates', async () => {
    const store = makeStore({
      lookupTopic: vi.fn().mockResolvedValue({
        active_match: null,
        ended_match: { session_id: 'e1', title: 'CSS' },
      }),
    })

    const flow = useStartFlow({ store, router })
    await flow.begin('css')
    await flow.startFresh()
    expect(store.createSession).toHaveBeenCalledWith(
      expect.objectContaining({ topic: 'css', seedMode: 'fresh' }),
    )
    expect(router.push).toHaveBeenCalledWith({ name: 'session', params: { id: 'new1' } })
  })

  it('409 duplicate on create shows active intercept instead of navigating', async () => {
    const err = Object.assign(new Error('dup'), {
      status: 409,
      body: { detail: { code: 'duplicate_topic', session_id: 'a9' } },
    })

    const store = makeStore({ createSession: vi.fn().mockRejectedValue(err) })
    const flow = useStartFlow({ store, router })
    await flow.begin('t')
    expect(router.push).not.toHaveBeenCalled()
    expect(flow.stage.value).toBe('intercept')
    expect(flow.interceptKind.value).toBe('active')
    expect(flow.interceptMatch.value.session_id).toBe('a9')
  })

  it('awaits beforeNavigate hook between create and push', async () => {
    const order = []

    const store = makeStore({
      createSession: vi.fn().mockImplementation(async () => {
        order.push('create')

        return { id: 'n1' }
      }),
    })

    const beforeNavigate = vi.fn().mockImplementation(async () => order.push('hook'))
    const flow = useStartFlow({ store, router, beforeNavigate })
    await flow.begin('t')
    expect(order).toEqual(['create', 'hook'])
    expect(router.push).toHaveBeenCalled()
  })

  it('cancel returns to idle', async () => {
    const store = makeStore({
      lookupTopic: vi.fn().mockResolvedValue({
        active_match: { session_id: 'a1', title: 'CSS' },
        ended_match: null,
      }),
    })

    const flow = useStartFlow({ store, router })
    await flow.begin('t')
    flow.cancel()
    expect(flow.stage.value).toBe('idle')
  })

  it('cancel during an in-flight begin() prevents the stale lookup from creating a session', async () => {
    let resolveLookup

    const lookupPromise = new Promise((resolve) => {
      resolveLookup = resolve
    })

    const store = makeStore({ lookupTopic: vi.fn().mockReturnValue(lookupPromise) })
    const flow = useStartFlow({ store, router })
    const beginPromise = flow.begin('old topic')
    flow.cancel()
    resolveLookup({ active_match: null, ended_match: null })
    await beginPromise
    expect(store.createSession).not.toHaveBeenCalled()
    expect(router.push).not.toHaveBeenCalled()
    expect(flow.stage.value).toBe('idle')
  })
})
