import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount, flushPromises } from '@vue/test-utils'

import { apiGet, _resetApiCache } from '@/services/apiClient.js'
import { costBus } from '@/services/costBus.js'
import { useSessionStore } from '@/stores/session.js'
import { ERR_DAILY_COST_CAP_REACHED } from '@/lib/errorCodes.js'
import SessionView from '@/views/SessionView.vue'

// ---------------------------------------------------------------------------
// apiClient: dispatches cost-warning when X-Cost-Warning header is set on a
// successful response.
// ---------------------------------------------------------------------------

describe('apiClient cost-warning bus', () => {
  let fetchMock
  let listener
  beforeEach(() => {
    setActivePinia(createPinia())
    // F-18: apiClient's GET cache is module state -- without this the second
    // GET /x is served from cache and never sees the new header.
    _resetApiCache()
    fetchMock = vi.fn()
    globalThis.fetch = fetchMock
    listener = vi.fn()
    costBus.addEventListener('cost-warning', listener)
  })
  afterEach(() => {
    costBus.removeEventListener('cost-warning', listener)
    vi.restoreAllMocks()
  })

  function okWithHeader(body, header) {
    const headers = new Headers()

    if (header) headers.set('x-cost-warning', header)

    return Promise.resolve({
      ok: true,
      status: 200,
      headers,
      text: () => Promise.resolve(JSON.stringify(body)),
    })
  }

  it('does not fire when header absent', async () => {
    fetchMock.mockReturnValueOnce(okWithHeader({ ok: true }, null))
    await apiGet('/x')
    expect(listener).not.toHaveBeenCalled()
  })

  it('fires once with detail.header when X-Cost-Warning is present', async () => {
    fetchMock.mockReturnValueOnce(
      okWithHeader({ ok: true }, 'soft_cap_breached;used_usd=2.5;soft_cap_usd=2'),
    )
    await apiGet('/x')
    expect(listener).toHaveBeenCalledTimes(1)
    expect(listener.mock.calls[0][0].detail.header).toContain('soft_cap_breached')
  })

  it('fires with detail.header containing level=urgent when the cap is urgent', async () => {
    fetchMock.mockReturnValueOnce(
      okWithHeader(
        { ok: true },
        'soft_cap_breached;level=urgent;used_usd=2.9;urgent_cap_usd=2.8;hard_cap_usd=3.0',
      ),
    )
    await apiGet('/x')
    expect(listener).toHaveBeenCalledTimes(1)
    expect(listener.mock.calls[0][0].detail.header).toContain('level=urgent')
  })
})

// Slice 2: the streaming catch maps the 429 envelope into costCapInfo.

describe('session store cost-cap envelope (streaming)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('maps a cost-cap 429 from streamChat into costCapInfo and store error', async () => {
    // mock streamChat to throw an ApiError-shaped object with the envelope
    vi.doMock('@/services/chatStreamService.js', () => ({
      streamChat: vi.fn().mockRejectedValue(
        Object.assign(new Error('api'), {
          status: 429,
          body: {
            detail: {
              code: ERR_DAILY_COST_CAP_REACHED,
              used_usd: '3.5000',
              soft_cap_usd: '2.0',
              hard_cap_usd: '3.0',
              resets_at: '2026-05-24T00:00:00Z',
            },
          },
        }),
      ),
      streamCheckComplete: vi.fn(),
    }))
    vi.doMock('@/services/sessionsApi.js', () => ({
      listSessions: vi.fn(),
      createSession: vi.fn().mockResolvedValue({ id: 's1', topic: 't' }),
      getSession: vi.fn(),
      endSession: vi.fn(),
      reopenSession: vi.fn(),
    }))
    vi.resetModules()
    const { useSessionStore: useStore } = await import('@/stores/session.js')
    setActivePinia(createPinia())
    const s = useStore()
    await s.createSession({ topic: 't' })
    await expect(s.sendMessageStreaming({ text: 'hi' })).rejects.toThrow('api')
    expect(s.costCapReached).toBe(true)
    expect(s.costCapInfo).toEqual({
      used_usd: '3.5000',
      soft_cap_usd: '2.0',
      hard_cap_usd: '3.0',
      resets_at: '2026-05-24T00:00:00Z',
      scope: 'user',
    })
    expect(s.error).toBeTruthy()
    expect(s.streamState).toBe('idle')
  })
})

// ---------------------------------------------------------------------------
// SessionView: renders the cost-cap banner when the store reports it
// reached. Composer must also be disabled.
// ---------------------------------------------------------------------------

const stubs = {
  // ChatHeader teleports to the navbar slot; stub Teleport so it renders inline.
  teleport: true,
  BackButton: { template: '<button data-testid="back" />' },
  ReferenceStatusBanner: { template: '<div />' },
  SessionEndedBanner: { template: '<div />' },
  Button: {
    props: ['disabled', 'loading', 'label'],
    template: '<button :disabled="disabled"><slot>{{ label }}</slot></button>',
  },
  Dialog: {
    props: ['visible'],
    template: '<div v-if="visible"><slot /><slot name="footer" /></div>',
  },
  Textarea: {
    props: ['modelValue', 'disabled'],
    template: '<textarea :value="modelValue" :disabled="disabled" />',
  },
  RouterLink: { template: '<a><slot /></a>' },
}

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useRoute: () => ({ query: {} }),
  RouterLink: { template: '<a><slot /></a>' },
}))

// The session action bar calls useSessionActions, which calls useConfirm in
// setup; jsdom has no ConfirmationService installed.
vi.mock('primevue/useconfirm', () => ({
  useConfirm: () => ({ require: vi.fn() }),
}))

vi.mock('@/services/uploadApi.js', () => ({
  uploadDocument: vi.fn().mockResolvedValue({ document_id: 1 }),
  validateFile: vi.fn(() => ({ ok: true })),
  // useReferencePoll (owned by SessionView) calls this at setup.
  getSessionIngestion: vi.fn().mockResolvedValue({ status: null, documents: [] }),
  MAX_UPLOAD_BYTES: 25 * 1024 * 1024,
}))

const showError = vi.fn()

const showWarn = vi.fn()

vi.mock('@/composables/useToast.js', () => ({
  useToast: () => ({ showError, showWarn, showSuccess: vi.fn() }),
}))

describe('SessionView cost-cap UX', () => {
  let lastWrapper = null
  beforeEach(() => {
    setActivePinia(createPinia())
    showError.mockClear()
    showWarn.mockClear()
  })
  afterEach(() => {
    if (lastWrapper) {
      lastWrapper.unmount()
      lastWrapper = null
    }
  })

  function seedActive(store) {
    store.currentSession = { id: 's1', topic: 'X', ended_at: null }
    store.currentSessionId = 's1'
    store.messages = []
  }

  it('renders cost-cap banner when costCapReached', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      seedActive(store)
      store.costCapInfo = {
        used_usd: '3.50',
        soft_cap_usd: '2.00',
        hard_cap_usd: '3.00',
        resets_at: '2026-05-24T00:00:00Z',
      }
    })
    const wrapper = (lastWrapper = mount(SessionView, { props: { id: 's1' }, global: { stubs } }))
    await flushPromises()
    expect(wrapper.find('[data-testid="session-cost-cap-banner"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="session-cost-cap-banner"]').text()).toContain('$3.50')
    expect(showError).toHaveBeenCalled()
  })

  it('shows soft-warning toast once on cost-warning event', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      seedActive(store)
    })
    lastWrapper = mount(SessionView, { props: { id: 's1' }, global: { stubs } })
    await flushPromises()
    costBus.dispatchEvent(new CustomEvent('cost-warning', { detail: { header: 'x' } }))
    costBus.dispatchEvent(new CustomEvent('cost-warning', { detail: { header: 'x' } }))
    await flushPromises()
    expect(showWarn).toHaveBeenCalledTimes(1)
    expect(showError).not.toHaveBeenCalled()
  })

  it('surfaces an urgent cost warning distinctly from a soft one (stream shape)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      seedActive(store)
    })
    lastWrapper = mount(SessionView, { props: { id: 's1' }, global: { stubs } })
    await flushPromises()
    costBus.dispatchEvent(
      new CustomEvent('cost-warning', {
        detail: { level: 'urgent', used_usd: 2.9, urgent_cap_usd: 2.8, hard_cap_usd: 3.0 },
      }),
    )
    await flushPromises()
    expect(showError).toHaveBeenCalledTimes(1)
    expect(showWarn).not.toHaveBeenCalled()
  })

  it('surfaces an urgent cost warning distinctly from a soft one (header shape)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      seedActive(store)
    })
    lastWrapper = mount(SessionView, { props: { id: 's1' }, global: { stubs } })
    await flushPromises()
    costBus.dispatchEvent(
      new CustomEvent('cost-warning', {
        detail: { header: 'soft_cap_breached;level=urgent;used_usd=2.9;urgent_cap_usd=2.8' },
      }),
    )
    await flushPromises()
    expect(showError).toHaveBeenCalledTimes(1)
    expect(showWarn).not.toHaveBeenCalled()
  })

  it('still shows urgent warning even if a soft warning already fired this mount', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      seedActive(store)
    })
    lastWrapper = mount(SessionView, { props: { id: 's1' }, global: { stubs } })
    await flushPromises()
    costBus.dispatchEvent(new CustomEvent('cost-warning', { detail: { level: 'soft' } }))
    await flushPromises()
    expect(showWarn).toHaveBeenCalledTimes(1)
    costBus.dispatchEvent(new CustomEvent('cost-warning', { detail: { level: 'urgent' } }))
    await flushPromises()
    expect(showError).toHaveBeenCalledTimes(1)
    // soft does not fire again
    expect(showWarn).toHaveBeenCalledTimes(1)
  })
})
