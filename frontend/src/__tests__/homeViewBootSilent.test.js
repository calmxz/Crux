import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import HomeView from '@/views/HomeView.vue'
import { useSessionStore } from '@/stores/session.js'
import { errorBus } from '@/services/errorBus.js'

// U-05: HomeView's boot-mount call to GET /sessions must fail silently.
// Unlike homeView.test.js, this file does NOT mock sessionsApi.js -- it
// exercises the real store -> sessionsApi -> apiClient chain against a
// rejecting fetch, so the assertion covers real reportApiError wiring, not
// just call-argument shape.

const push = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
}))

const stubs = {
  EmptyState: {
    props: ['tone', 'eyebrow', 'headline', 'subtext'],
    template: '<div data-testid="empty-stub"><slot name="subtext" /><slot name="cta" /></div>',
  },
  RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
}

describe('HomeView boot calls fail silently (P3 U-05)', () => {
  let listener

  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockClear()
    listener = vi.fn()
    errorBus.addEventListener('api-error', listener)
    // The boot-path GET /sessions hits this same transient 500 -- the exact
    // condition the original toast sighting matched.
    globalThis.fetch = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ detail: 'boom' }), { status: 500 }))
  })

  afterEach(() => {
    errorBus.removeEventListener('api-error', listener)
    vi.restoreAllMocks()
  })

  it('mounting Home with failing GET /sessions fires no api-error toast', async () => {
    mount(HomeView, { global: { stubs } })
    await flushPromises()
    expect(listener).not.toHaveBeenCalled()
  })

  // Both Sidebar and HomeView call store.listSessions() from their own
  // onMounted on a cold load, and the store's in-flight de-dupe
  // (session.js:listSessions -- "De-dupes the double GET /sessions on home
  // load") collapses concurrent calls into ONE request. Silencing must be
  // baked into sessionsApi.listSessions() itself rather than threaded in as
  // a per-call opts flag, or whichever caller's call wins the de-dupe race
  // decides silent/non-silent for both -- this proves it holds regardless
  // of call order.
  it('concurrent store.listSessions() callers (simulating Sidebar + HomeView racing the de-dupe) never toast on failure', async () => {
    const store = useSessionStore()
    const p1 = store.listSessions().catch(() => {})
    const p2 = store.listSessions().catch(() => {})
    await Promise.all([p1, p2])
    expect(listener).not.toHaveBeenCalled()
  })
})
