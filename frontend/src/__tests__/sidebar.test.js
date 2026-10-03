import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const routerPush = vi.fn()

const routeRef = { params: {}, fullPath: '/' }

vi.mock('vue-router', () => ({
  RouterLink: { template: '<a><slot /></a>', props: ['to'] },
  useRouter: () => ({ push: routerPush }),
  useRoute: () => routeRef,
}))

const showSuccess = vi.fn()

const showError = vi.fn()

const showWarn = vi.fn()

vi.mock('@/composables/useToast.js', () => ({
  useToast: () => ({ showError, showWarn, showSuccess }),
}))

// E-12: the row's End action goes through PrimeVue's confirm service, which is
// not installed on a bare mount. The stub captures the config and accepts
// straight away so the existing End assertions keep reading the same way; the
// cancel path is covered in sidebarSessionRow.test.js.
let lastConfirm = null

vi.mock('primevue/useconfirm', () => ({
  useConfirm: () => ({
    require: (cfg) => {
      lastConfirm = cfg
      cfg.accept?.()
    },
  }),
}))

const apiReviewQueue = vi.fn()

vi.mock('@/services/reviewApi.js', () => ({
  getReviewQueue: (...args) => apiReviewQueue(...args),
}))

const apiGetSessionLibrary = vi.fn()

vi.mock('@/services/sessionsApi.js', async (importOriginal) => {
  const actual = await importOriginal()

  return {
    ...actual,
    getSessionLibrary: (...args) => apiGetSessionLibrary(...args),
  }
})

import Sidebar from '@/components/sidebar/Sidebar.vue'
import Logo from '@/components/Logo.vue'
import { useSessionStore } from '@/stores/session.js'
import { useAuthStore } from '@/stores/auth.js'
import { useUserStore } from '@/stores/user.js'
import { useSidebar, __test__ as sidebarTest } from '@/composables/useSidebar.js'
import { RouterLink as MockRouterLink } from 'vue-router'

function setViewport(w) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: w })
  sidebarTest._setViewport(w)
}

// File-wide default so every describe block that mounts Sidebar while
// authenticated (triggering the review-queue fetch in onMounted) gets a
// resolved promise instead of an unmocked vi.fn() undefined return.
// Individual review-entry tests override this per case.
beforeEach(() => {
  apiReviewQueue.mockReset()
  apiReviewQueue.mockResolvedValue({ items: [], total: 0, limit: 1, offset: 0 })
  apiGetSessionLibrary.mockReset()
  apiGetSessionLibrary.mockResolvedValue({ items: [], total: 0, limit: 15, offset: 0 })
})

describe('Sidebar.vue — session list rendering', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    routerPush.mockClear()
    localStorage.clear()
    setViewport(1400) // desktop expanded
    sidebarTest._setExpanded(true)
    routeRef.params = {}
    routeRef.fullPath = '/'
  })
  afterEach(() => wrapper?.unmount())

  it('shows skeleton while loading and no sessions yet', async () => {
    const store = useSessionStore()
    store.loading = true
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('.sb-skel-list').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-empty-hint"]').exists()).toBe(false)
  })

  it('shows empty hint when not loading and zero sessions', async () => {
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-empty-hint"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('No sessions yet')
  })

  it('renders Active section with rows; no Ended section when empty', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
      { id: 'a2', topic: 'Trees', created_at: new Date().toISOString(), ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-section-active"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-section-ended"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="sidebar-row-a1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-row-a2"]').exists()).toBe(true)
  })

  it('shows an Ended tab with a count when ended sessions exist', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: '2026-05-20T10:00:00Z', ended_at: null },
      {
        id: 'e1',
        topic: 'Recursion',
        created_at: '2026-05-15T10:00:00Z',
        ended_at: '2026-05-18T10:00:00Z',
      },
    ]
    // Badge reads the store's server-side total, not the loaded row count.
    store.endedTotal = 1
    wrapper = mount(Sidebar)
    await flushPromises()
    // Default view is Active: the ended row is behind the Ended tab, not visible yet.
    expect(wrapper.find('[data-testid="sidebar-row-e1"]').exists()).toBe(false)
    const endedTab = wrapper.find('[data-testid="sidebar-status-ended"]')
    expect(endedTab.exists()).toBe(true)
    expect(endedTab.text()).toContain('1')
  })

  it('Active/Ended toggle switches which sessions are shown', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Active one', created_at: '2026-05-20T10:00:00Z', ended_at: null },
      {
        id: 'e1',
        topic: 'Ended one',
        created_at: '2026-05-15T10:00:00Z',
        ended_at: '2026-05-18T10:00:00Z',
      },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    // Active view by default.
    expect(wrapper.find('[data-testid="sidebar-status-active"]').attributes('aria-pressed')).toBe(
      'true',
    )
    expect(wrapper.find('[data-testid="sidebar-row-a1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-row-e1"]').exists()).toBe(false)
    // Switch to Ended.
    await wrapper.find('[data-testid="sidebar-status-ended"]').trigger('click')
    expect(wrapper.find('[data-testid="sidebar-status-ended"]').attributes('aria-pressed')).toBe(
      'true',
    )
    expect(wrapper.find('[data-testid="sidebar-row-e1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-row-a1"]').exists()).toBe(false)
  })

  it('keeps the pinned mini-group under the Active view only', async () => {
    const store = useSessionStore()
    store.sessions = [
      {
        id: 'p1',
        topic: 'Pinned',
        created_at: '2026-05-20T10:00:00Z',
        ended_at: null,
        pinned: true,
      },
      {
        id: 'e1',
        topic: 'Ended',
        created_at: '2026-05-15T10:00:00Z',
        ended_at: '2026-05-18T10:00:00Z',
      },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-section-pinned"]').exists()).toBe(true)
    await wrapper.find('[data-testid="sidebar-status-ended"]').trigger('click')
    expect(wrapper.find('[data-testid="sidebar-section-pinned"]').exists()).toBe(false)
  })

  it('marks current session row with aria-current=page', async () => {
    routeRef.params = { id: 'a1' }
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: '2026-05-20T10:00:00Z', ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    const btn = wrapper.find('[data-session-id="a1"] [data-testid="sidebar-row-open"]')
    expect(btn.attributes('aria-current')).toBe('page')
  })

  it('the collapsed rail renders no session rows; they return on unfold', async () => {
    sidebarTest._setExpanded(false)
    const store = useSessionStore()
    store.sessions = [
      {
        id: 'a1',
        topic: 'Glycolysis',
        created_at: new Date().toISOString(),
        last_activity_at: new Date().toISOString(),
        ended_at: null,
      },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-session-id]').exists()).toBe(false)

    await wrapper.get('[data-testid="sidebar-collapse-toggle"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-row-a1"]').exists()).toBe(true)
  })

  it('highlights the current session row', async () => {
    routeRef.params = { id: 'a1' }
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Glycolysis', created_at: new Date().toISOString(), ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    // Closes clause (b) of the spec's first WS2 test bullet (current session highlighted)
    // with an automated check rather than deferring entirely to live smoke.
    expect(wrapper.find('[data-testid="sidebar-row-a1"]').classes()).toContain('sb-row--current')
  })

  it('filters sessions via the search input and shows a match count', async () => {
    vi.useFakeTimers()

    try {
      const store = useSessionStore()
      store.sessions = [
        {
          id: 'a1',
          topic: 'Photosynthesis',
          created_at: new Date().toISOString(),
          ended_at: null,
        },
        { id: 'a2', topic: 'Big-O notation', created_at: new Date().toISOString(), ended_at: null },
      ]
      apiGetSessionLibrary.mockResolvedValue({
        items: [{ id: 'a1', topic: 'Photosynthesis', ended_at: null }],
        total: 1,
      })
      wrapper = mount(Sidebar)
      await flushPromises()
      await wrapper.find('[data-testid="sidebar-search"]').setValue('photo')
      await vi.advanceTimersByTimeAsync(250)
      await flushPromises()
      expect(wrapper.find('[data-testid="sidebar-row-a1"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="sidebar-row-a2"]').exists()).toBe(false)
      expect(wrapper.find('[data-testid="sidebar-search-count"]').text()).toContain('1')
    } finally {
      vi.useRealTimers()
    }
  })

  it('shows a no-match hint when search matches nothing', async () => {
    vi.useFakeTimers()

    try {
      const store = useSessionStore()
      store.sessions = [
        { id: 'a1', topic: 'Photosynthesis', created_at: new Date().toISOString(), ended_at: null },
      ]
      apiGetSessionLibrary.mockResolvedValue({ items: [], total: 0 })
      wrapper = mount(Sidebar)
      await flushPromises()
      await wrapper.find('[data-testid="sidebar-search"]').setValue('zzz')
      await vi.advanceTimersByTimeAsync(250)
      await flushPromises()
      expect(wrapper.find('[data-testid="sidebar-search-empty"]').exists()).toBe(true)
    } finally {
      vi.useRealTimers()
    }
  })

  it('renders active sessions as one flat list without date group labels', async () => {
    const store = useSessionStore()
    const now = new Date()
    const weekAgo = new Date(now.getTime() - 3 * 86400000)
    const older = new Date(now.getTime() - 20 * 86400000)
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: now.toISOString(), ended_at: null },
      { id: 'a2', topic: 'Trees', created_at: weekAgo.toISOString(), ended_at: null },
      { id: 'a3', topic: 'Graphs', created_at: older.toISOString(), ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid^="sidebar-group-"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('This week')
    expect(wrapper.text()).not.toContain('Older')
    // all rows still present
    expect(wrapper.findAll('[data-testid="sidebar-row-open"]').length).toBeGreaterThan(0)
    expect(wrapper.find('[data-testid="sidebar-row-a1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-row-a2"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-row-a3"]').exists()).toBe(true)
  })

  it('renders the pinned mini-group when a session is pinned', async () => {
    const store = useSessionStore()
    store.sessions = [
      {
        id: 'p1',
        topic: 'Pinned',
        created_at: new Date().toISOString(),
        ended_at: null,
        pinned: true,
      },
      { id: 'a1', topic: 'Normal', created_at: new Date().toISOString(), ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-section-pinned"]').exists()).toBe(true)
    expect(
      wrapper
        .find('[data-testid="sidebar-section-pinned"] [data-testid="sidebar-row-p1"]')
        .exists(),
    ).toBe(true)
  })

  it('clears the search query when the sidebar collapses so unfolding shows the full list', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Photosynthesis', created_at: new Date().toISOString(), ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    await wrapper.find('[data-testid="sidebar-search"]').setValue('photo')
    await flushPromises()
    // collapse the sidebar
    await wrapper.find('[data-testid="sidebar-collapse-toggle"]').trigger('click')
    await flushPromises()
    // search input is gone (v-if on isExpanded)
    expect(wrapper.find('[data-testid="sidebar-search"]').exists()).toBe(false)
    // unfold: the query is gone and the plain list is back, not a stale search
    await wrapper.find('[data-testid="sidebar-collapse-toggle"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="sidebar-search"]').element.value).toBe('')
    expect(wrapper.find('[data-testid="sidebar-search-count"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="sidebar-row-a1"]').exists()).toBe(true)
  })
})

describe('sidebar server-side search', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    routerPush.mockClear()
    showSuccess.mockClear()
    showError.mockClear()
    showWarn.mockClear()
    localStorage.clear()
    setViewport(1400) // desktop expanded
    sidebarTest._setExpanded(true)
    routeRef.params = {}
    routeRef.fullPath = '/'
    vi.useFakeTimers()
  })
  afterEach(() => {
    wrapper?.unmount()
    vi.useRealTimers()
  })

  it('debounces 250ms then queries the library endpoint scoped to the current tab', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    await wrapper.find('[data-testid="sidebar-search"]').setValue('gly')
    await vi.advanceTimersByTimeAsync(249)
    expect(apiGetSessionLibrary).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1)
    expect(apiGetSessionLibrary).toHaveBeenCalledWith(
      { status: 'active', q: 'gly', sort: 'last_activity', limit: 15, offset: 0 },
      { silent: true },
    )
  })

  it('renders server results and total; store sessions array untouched', async () => {
    const store = useSessionStore()

    const seeded = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
    ]

    store.sessions = seeded
    apiGetSessionLibrary.mockResolvedValue({
      items: [
        { id: 'r1', topic: 'Glycolysis', ended_at: null },
        { id: 'r2', topic: 'Glycogen', ended_at: null },
      ],
      total: 12,
    })
    wrapper = mount(Sidebar)
    await flushPromises()
    await wrapper.find('[data-testid="sidebar-search"]').setValue('gly')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-row-r1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-row-r2"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-search-count"]').text()).toContain('12')
    // Content (not identity, since Vue wraps assigned arrays in a reactive
    // proxy) must still equal the original seeded value -- search must never
    // write the store's `sessions` array.
    expect(store.sessions).toEqual(seeded)
  })

  it('shows View all with the query when total exceeds results', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
    ]
    apiGetSessionLibrary.mockResolvedValue({
      items: [
        { id: 'r1', topic: 'Glycolysis', ended_at: null },
        { id: 'r2', topic: 'Glycogen', ended_at: null },
      ],
      total: 12,
    })
    wrapper = mount(Sidebar)
    await flushPromises()
    await wrapper.find('[data-testid="sidebar-search"]').setValue('gly')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    const viewAll = wrapper.find('[data-testid="sidebar-view-all-search"]')
    expect(viewAll.exists()).toBe(true)

    const viewAllComponent = wrapper
      .findAllComponents(MockRouterLink)
      .find((c) => c.attributes('data-testid') === 'sidebar-view-all-search')

    expect(viewAllComponent.props('to')).toEqual({
      name: 'sessions-library',
      query: { status: 'active', q: 'gly' },
    })
  })

  it('hides View all while a newer query is in flight, so the stale total never pairs with the fresh query', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
    ]
    let resolveA
    let resolveAb
    apiGetSessionLibrary.mockImplementation((params) => {
      if (params.q === 'a') return new Promise((resolve) => (resolveA = resolve))

      if (params.q === 'ab') return new Promise((resolve) => (resolveAb = resolve))

      return Promise.resolve({ items: [], total: 0 })
    })
    wrapper = mount(Sidebar)
    await flushPromises()

    // Settle the first query: total 5, 2 rows -> View all is visible.
    await wrapper.find('[data-testid="sidebar-search"]').setValue('a')
    await vi.advanceTimersByTimeAsync(250)
    resolveA({
      items: [
        { id: 'r1', topic: 'Apple', ended_at: null },
        { id: 'r2', topic: 'Ant', ended_at: null },
      ],
      total: 5,
    })
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-view-all-search"]').exists()).toBe(true)

    // Type a further character -- a newer query is now in flight.
    await wrapper.find('[data-testid="sidebar-search"]').setValue('ab')
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-search-count"]').text()).toContain('Searching')
    // The stale total (5) must not render a link -- it would pair "View all 5
    // matches" with a route query.q of 'ab', describing two different searches.
    expect(wrapper.find('[data-testid="sidebar-view-all-search"]').exists()).toBe(false)
    // Previous query's rows stay visible underneath the loading state.
    expect(wrapper.find('[data-testid="sidebar-row-r1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-row-r2"]').exists()).toBe(true)

    // Resolve the new query: the link returns paired with the correct total and q.
    await vi.advanceTimersByTimeAsync(250)
    resolveAb({ items: [{ id: 'r3', topic: 'Ability', ended_at: null }], total: 9 })
    await flushPromises()
    const viewAll = wrapper.find('[data-testid="sidebar-view-all-search"]')
    expect(viewAll.exists()).toBe(true)
    expect(viewAll.text()).toContain('9')

    const viewAllComponent = wrapper
      .findAllComponents(MockRouterLink)
      .find((c) => c.attributes('data-testid') === 'sidebar-view-all-search')

    expect(viewAllComponent.props('to')).toEqual({
      name: 'sessions-library',
      query: { status: 'active', q: 'ab' },
    })
  })

  it('drops stale responses (later query wins)', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
    ]
    let resolveAa
    let resolveBb
    apiGetSessionLibrary.mockImplementation((params) => {
      if (params.q === 'aa') return new Promise((resolve) => (resolveAa = resolve))

      if (params.q === 'bb') return new Promise((resolve) => (resolveBb = resolve))

      return Promise.resolve({ items: [], total: 0 })
    })
    wrapper = mount(Sidebar)
    await flushPromises()
    // Type 'aa' and advance a full debounce cycle so its request genuinely
    // fires and is in flight BEFORE 'bb' is typed. If both were typed
    // back-to-back, the watch's own clearTimeout on every keystroke would
    // mean 'aa' is never issued at all -- this test would then pass with the
    // _searchSeq guards deleted, proving nothing about the guard.
    await wrapper.find('[data-testid="sidebar-search"]').setValue('aa')
    await vi.advanceTimersByTimeAsync(250)
    await wrapper.find('[data-testid="sidebar-search"]').setValue('bb')
    await vi.advanceTimersByTimeAsync(250)
    expect(apiGetSessionLibrary).toHaveBeenCalledTimes(2)

    // Resolve 'aa' (the stale request) AFTER 'bb' (the current request).
    resolveBb({ items: [{ id: 'bb1', topic: 'bb result', ended_at: null }], total: 1 })
    await flushPromises()
    resolveAa({ items: [{ id: 'aa1', topic: 'aa result', ended_at: null }], total: 1 })
    await flushPromises()

    expect(wrapper.find('[data-testid="sidebar-row-bb1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-row-aa1"]').exists()).toBe(false)
  })

  it('clearing the query restores the tab view without a fetch', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    await wrapper.find('[data-testid="sidebar-search"]').setValue('gly')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    apiGetSessionLibrary.mockClear()
    await wrapper.find('[data-testid="sidebar-search"]').setValue('')
    await flushPromises()
    expect(apiGetSessionLibrary).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="sidebar-section-active"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-row-a1"]').exists()).toBe(true)
  })

  it('renders zero matches silently (no toast) when the library fetch errors', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
    ]
    apiGetSessionLibrary.mockRejectedValue(new Error('boom'))
    wrapper = mount(Sidebar)
    await flushPromises()
    await wrapper.find('[data-testid="sidebar-search"]').setValue('gly')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-search-empty"]').exists()).toBe(true)
    // A failed sidebar search must raise no toast at all (not success, not
    // error, not warn) -- errors render silently as zero matches.
    expect(showSuccess).not.toHaveBeenCalled()
    expect(showError).not.toHaveBeenCalled()
    expect(showWarn).not.toHaveBeenCalled()
  })

  // Search results describe sessions that are routinely OUTSIDE the store's
  // 15+15 window. A row action must still be visible on the rendered row --
  // otherwise nothing appears to happen, the user retries, and the server's
  // idempotent end/reopen replays 200 while the totals mirror skews again.
  it('reflects an End taken on a search row for a session outside the loaded window', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
    ]
    store.activeTotal = 40
    store.endedTotal = 0
    apiGetSessionLibrary.mockResolvedValue({
      items: [{ id: 'out1', topic: 'Glycolysis', ended_at: null, pinned: false }],
      total: 1,
    })
    const api = await import('@/services/sessionsApi.js')

    const endSpy = vi
      .spyOn(api, 'endSession')
      .mockResolvedValue({ ended_at: '2026-05-21T10:00:00Z', summary: null })

    try {
      wrapper = mount(Sidebar, { attachTo: document.body })
      await flushPromises()
      await wrapper.find('[data-testid="sidebar-search"]').setValue('gly')
      await vi.advanceTimersByTimeAsync(250)
      await flushPromises()
      expect(store.sessions.some((s) => s.id === 'out1')).toBe(false)
      expect(wrapper.find('[data-session-id="out1"]').classes()).not.toContain('sb-row--ended')

      await wrapper
        .find('[data-session-id="out1"] [data-testid="sidebar-row-menu-trigger"]')
        .trigger('click')
      await wrapper.find('[data-testid="sidebar-row-menu-end"]').trigger('click')
      await flushPromises()

      expect(endSpy).toHaveBeenCalledWith('out1')
      expect(wrapper.find('[data-session-id="out1"]').classes()).toContain('sb-row--ended')
      expect(store.activeTotal).toBe(39)
      expect(store.endedTotal).toBe(1)
      // End is no longer offered on a row the user can see is ended, so the
      // repeat-click loop is closed at the UI as well as in the store.
      await wrapper
        .find('[data-session-id="out1"] [data-testid="sidebar-row-menu-trigger"]')
        .trigger('click')
      expect(wrapper.find('[data-testid="sidebar-row-menu-end"]').exists()).toBe(false)
    } finally {
      endSpy.mockRestore()
    }
  })

  // Search is scoped to the current tab (status: statusFilter), so the tab
  // toggle is the only control that widens the scope. Hiding it while
  // searching leaves "No sessions match" with no way to look elsewhere.
  it('keeps the status toggle visible while searching and re-fires the search when the tab changes', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    await wrapper.find('[data-testid="sidebar-search"]').setValue('gly')
    await vi.advanceTimersByTimeAsync(250)
    await flushPromises()
    const endedTab = wrapper.find('[data-testid="sidebar-status-ended"]')
    expect(endedTab.exists()).toBe(true)

    apiGetSessionLibrary.mockClear()
    await endedTab.trigger('click')
    // The re-fire goes through the same debounce as a keystroke, not an
    // unguarded immediate fetch.
    await vi.advanceTimersByTimeAsync(249)
    expect(apiGetSessionLibrary).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1)
    expect(apiGetSessionLibrary).toHaveBeenCalledWith(
      { status: 'ended', q: 'gly', sort: 'last_activity', limit: 15, offset: 0 },
      { silent: true },
    )
  })

  it('switching tabs with an empty query does not fire a search', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    apiGetSessionLibrary.mockClear()
    await wrapper.find('[data-testid="sidebar-status-ended"]').trigger('click')
    await vi.advanceTimersByTimeAsync(250)
    expect(apiGetSessionLibrary).not.toHaveBeenCalled()
  })

  it('does not throw when unmounted mid-debounce', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    await wrapper.find('[data-testid="sidebar-search"]').setValue('gly')
    wrapper.unmount()
    wrapper = null
    // The pending debounce timer must be cleared on unmount; advancing past
    // it must not call the (now-orphaned) endpoint or throw.
    await vi.advanceTimersByTimeAsync(250)
    expect(apiGetSessionLibrary).not.toHaveBeenCalled()
  })
})

describe('Sidebar.vue — row interactions', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    routerPush.mockClear()
    showSuccess.mockClear()
    localStorage.clear()
    setViewport(1400)
    sidebarTest._setExpanded(true)
    routeRef.params = {}
    routeRef.fullPath = '/'
    routeRef.name = undefined
  })
  afterEach(() => wrapper?.unmount())

  it('clicking a row navigates to its session', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: '2026-05-20T10:00:00Z', ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    await wrapper.find('[data-session-id="a1"] [data-testid="sidebar-row-open"]').trigger('click')
    expect(routerPush).toHaveBeenCalledWith({ name: 'session', params: { id: 'a1' } })
  })

  it('row menu opens then closes on action', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: '2026-05-20T10:00:00Z', ended_at: null },
    ]
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-row-menu-popover"]').exists()).toBe(false)
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    expect(wrapper.find('[data-testid="sidebar-row-menu-popover"]').exists()).toBe(true)
  })

  it('popover uses honest group semantics, not role=menu', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: '2026-05-20T10:00:00Z', ended_at: null },
    ]
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    const pop = wrapper.get('[data-testid="sidebar-row-menu-popover"]')
    expect(pop.attributes('role')).toBe('group')
    expect(pop.attributes('aria-label')).toBeTruthy()
    expect(wrapper.findAll('[role="menuitem"]')).toHaveLength(0)
    expect(
      wrapper
        .get('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
        .attributes('aria-haspopup'),
    ).toBeUndefined()
  })

  it('End session menu item confirms first, then calls store.endSession with row id', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: '2026-05-20T10:00:00Z', ended_at: null },
    ]
    const endSpy = vi.spyOn(store, 'endSession').mockResolvedValue({})
    lastConfirm = null
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-end"]').trigger('click')
    expect(lastConfirm).toMatchObject({ header: 'End session' })
    expect(endSpy).toHaveBeenCalledWith('a1')
  })

  it("End session toasts the pending summary when ending from off that session's view (F-44)", async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: '2026-05-20T10:00:00Z', ended_at: null },
    ]
    vi.spyOn(store, 'endSession').mockImplementation(async (id) => {
      store.pendingSummary = { sessionId: id, kind: 'summary', text: 'Great progress on Big-O.' }

      return {}
    })
    // Not on that session's own view — SessionView isn't mounted to consume it.
    routeRef.name = 'home'
    routeRef.params = {}
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-end"]').trigger('click')
    await flushPromises()
    expect(showSuccess).toHaveBeenCalledWith('Great progress on Big-O.')
    expect(store.pendingSummary).toBe(null)
  })

  it("End session does not toast when this session's own view is active", async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: '2026-05-20T10:00:00Z', ended_at: null },
    ]
    vi.spyOn(store, 'endSession').mockImplementation(async (id) => {
      store.pendingSummary = { sessionId: id, kind: 'summary', text: 'Great progress on Big-O.' }

      return {}
    })
    routeRef.name = 'session'
    routeRef.params = { id: 'a1' }
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-end"]').trigger('click')
    await flushPromises()
    expect(showSuccess).not.toHaveBeenCalled()
    expect(store.pendingSummary).not.toBe(null)
  })

  it('Resume menu item calls store.reopenSession and navigates', async () => {
    const store = useSessionStore()
    store.sessions = [{ id: 'e1', topic: 'X', ended_at: '2026-05-18T10:00:00Z' }]
    const reopenSpy = vi.spyOn(store, 'reopenSession').mockResolvedValue({})
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    // Ended rows now live behind the Ended tab (default view is Active).
    await wrapper.find('[data-testid="sidebar-status-ended"]').trigger('click')
    await wrapper
      .find('[data-session-id="e1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-resume"]').trigger('click')
    await flushPromises()
    expect(reopenSpy).toHaveBeenCalledWith('e1')
    expect(routerPush).toHaveBeenCalledWith({ name: 'session', params: { id: 'e1' } })
  })

  it('ended row menu offers Continue topic which calls store.continueTopic and routes', async () => {
    const store = useSessionStore()
    store.sessions = [{ id: 'e1', topic: 'X', ended_at: '2026-05-18T10:00:00Z' }]
    const continueTopicSpy = vi.spyOn(store, 'continueTopic').mockResolvedValue({ id: 'new-1' })
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    // Ended rows now live behind the Ended tab (default view is Active).
    await wrapper.find('[data-testid="sidebar-status-ended"]').trigger('click')
    await wrapper
      .find('[data-session-id="e1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-continue-topic"]').trigger('click')
    await flushPromises()
    expect(continueTopicSpy).toHaveBeenCalled()
    expect(routerPush).toHaveBeenCalledWith({ name: 'session', params: { id: 'new-1' } })
  })

  it('Ended row still offers Resume alongside Continue topic', async () => {
    const store = useSessionStore()
    store.sessions = [{ id: 'e1', topic: 'X', ended_at: '2026-05-18T10:00:00Z' }]
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper.find('[data-testid="sidebar-status-ended"]').trigger('click')
    await wrapper
      .find('[data-session-id="e1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    expect(wrapper.find('[data-testid="sidebar-row-menu-resume"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-row-menu-continue-topic"]').exists()).toBe(true)
  })

  it('Ended row does not offer End menu item', async () => {
    const store = useSessionStore()
    store.sessions = [{ id: 'e1', topic: 'X', ended_at: '2026-05-18T10:00:00Z' }]
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    // Ended rows now live behind the Ended tab (default view is Active).
    await wrapper.find('[data-testid="sidebar-status-ended"]').trigger('click')
    await wrapper
      .find('[data-session-id="e1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    expect(wrapper.find('[data-testid="sidebar-row-menu-end"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="sidebar-row-menu-resume"]').exists()).toBe(true)
  })

  it('active row menu offers Rename and Pin', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'X', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
    ]
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    expect(wrapper.find('[data-testid="sidebar-row-menu-rename"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-row-menu-pin"]').exists()).toBe(true)
  })

  it('Pin menu item calls store.setPinned(true)', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'X', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
    ]
    const pinSpy = vi.spyOn(store, 'setPinned').mockResolvedValue({})
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-pin"]').trigger('click')
    expect(pinSpy).toHaveBeenCalledWith('a1', true)
  })

  it('Pin keeps focus on the row trigger after the row moves to the pinned section', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'X', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
      { id: 'a2', topic: 'Y', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
    ]
    // spy flips real store state so the row relocates across sections
    vi.spyOn(store, 'setPinned').mockImplementation(async (id, pinned) => {
      const s = store.sessions.find((x) => x.id === id)

      if (s) s.pinned = pinned

      return {}
    })
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-pin"]').trigger('click')
    await flushPromises()
    const active = document.activeElement

    const a1Trigger = wrapper.find(
      '[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]',
    ).element

    expect(active).toBe(a1Trigger)
  })

  it('Rename enters inline edit and commits on Enter via store.renameSession', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Old', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
    ]
    const renameSpy = vi.spyOn(store, 'renameSession').mockResolvedValue({})
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-rename"]').trigger('click')
    const input = wrapper.find('[data-session-id="a1"] [data-testid="sidebar-row-rename-input"]')
    expect(input.exists()).toBe(true)
    await input.setValue('New name')
    await input.trigger('keydown.enter')
    expect(renameSpy).toHaveBeenCalledWith('a1', 'New name')
  })

  it('Rename cancels on Escape without calling the store', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Old', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
    ]
    const renameSpy = vi.spyOn(store, 'renameSession').mockResolvedValue({})
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-rename"]').trigger('click')
    const input = wrapper.find('[data-session-id="a1"] [data-testid="sidebar-row-rename-input"]')
    await input.setValue('Discard me')
    await input.trigger('keydown.esc')
    expect(renameSpy).not.toHaveBeenCalled()
    expect(
      wrapper.find('[data-session-id="a1"] [data-testid="sidebar-row-rename-input"]').exists(),
    ).toBe(false)
  })

  it('Rename Enter with unchanged topic does not call the store', async () => {
    const store = useSessionStore()
    store.sessions = [
      {
        id: 'a1',
        topic: 'Same',
        created_at: '2026-05-20T10:00:00Z',
        ended_at: null,
        pinned: false,
      },
    ]
    const renameSpy = vi.spyOn(store, 'renameSession').mockResolvedValue({})
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-rename"]').trigger('click')
    const input = wrapper.find('[data-session-id="a1"] [data-testid="sidebar-row-rename-input"]')
    await input.setValue('Same')
    await input.trigger('keydown.enter')
    expect(renameSpy).not.toHaveBeenCalled()
  })

  it('Rename Enter with empty topic does not call the store', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Old', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
    ]
    const renameSpy = vi.spyOn(store, 'renameSession').mockResolvedValue({})
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-rename"]').trigger('click')
    const input = wrapper.find('[data-session-id="a1"] [data-testid="sidebar-row-rename-input"]')
    await input.setValue('   ')
    await input.trigger('keydown.enter')
    expect(renameSpy).not.toHaveBeenCalled()
  })

  it('does not show the pin glyph on an ended (but pinned) session', async () => {
    const store = useSessionStore()
    store.sessions = [
      {
        id: 'e1',
        topic: 'EndedPinned',
        created_at: '2026-05-20T10:00:00Z',
        ended_at: '2026-05-21T10:00:00Z',
        pinned: true,
      },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    // Ended view is v-if-gated behind the Ended tab; switch to it first.
    await wrapper.find('[data-testid="sidebar-status-ended"]').trigger('click')
    expect(wrapper.find('[data-session-id="e1"]').exists()).toBe(true)
    expect(wrapper.find('[data-session-id="e1"] .sb-row-pin').exists()).toBe(false)
  })

  it('shows the pin glyph on an active pinned session', async () => {
    const store = useSessionStore()
    store.sessions = [
      {
        id: 'a1',
        topic: 'ActivePinned',
        created_at: '2026-05-20T10:00:00Z',
        ended_at: null,
        pinned: true,
      },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-session-id="a1"] .sb-row-pin').exists()).toBe(true)
  })

  it('Rename commits exactly once on Enter even though blur also fires', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Old', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
    ]
    const renameSpy = vi.spyOn(store, 'renameSession').mockResolvedValue({})
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-rename"]').trigger('click')
    const input = wrapper.find('[data-session-id="a1"] [data-testid="sidebar-row-rename-input"]')
    await input.setValue('New')
    await input.trigger('keydown.enter')

    try {
      await input.trigger('blur')
    } catch {
      /* input may be detached after rename exits */
    }

    await flushPromises()
    expect(renameSpy).toHaveBeenCalledTimes(1)
    expect(renameSpy).toHaveBeenCalledWith('a1', 'New')
  })
})

describe('Sidebar.vue — footer', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    routerPush.mockClear()
    localStorage.clear()
    setViewport(1400)
    sidebarTest._setExpanded(true)
    routeRef.params = {}
    routeRef.fullPath = '/'
  })
  afterEach(() => wrapper?.unmount())

  // Settings is reached through the identity row's account menu; the foot
  // carries no Settings link of its own in either state.
  it.each([
    ['expanded', true],
    ['collapsed', false],
  ])('footer carries the identity row alone, no Settings link, when %s', async (_s, expanded) => {
    sidebarTest._setExpanded(expanded)
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1', email: 'ada@example.com' }, access_token: 't' }
    wrapper = mount(Sidebar)
    await flushPromises()
    const footer = wrapper.get('footer.sb-rail')
    expect(footer.find('a').exists()).toBe(false)
    expect(footer.findAll('button').map((b) => b.attributes('data-testid'))).toEqual([
      'sidebar-user-trigger',
    ])
    expect(footer.classes().includes('sb-rail--column')).toBe(!expanded)
  })

  // With no identity row to hold, the ruled foot would be an empty strip.
  it('renders no footer when unauthenticated', async () => {
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('footer.sb-rail').exists()).toBe(false)
  })

  it('footer rail no longer renders a theme control', async () => {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1' }, access_token: 't' }
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-theme-toggle"]').exists()).toBe(false)
  })

  // Profile lives beside Recall at the top (#362); the foot stays identity only.
  it('footer has no Profile entry', async () => {
    useAuthStore().session = { user: { id: 'u-1', email: 'a@b.c' }, access_token: 't' }
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.get('footer').find('[data-testid="sidebar-profile"]').exists()).toBe(false)
  })
})

// The foot's identity row opens the account menu: the sign-in email as a
// head, then Settings, Usage and Account, a rule, and Sign out.
describe('Sidebar.vue — identity row and account menu', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    routerPush.mockClear()
    showError.mockClear()
    localStorage.clear()
    setViewport(1400)
    sidebarTest._setExpanded(true)
    routeRef.params = {}
    routeRef.fullPath = '/'
  })
  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    document.body.innerHTML = ''
  })

  function signIn({ name = 'ada lovelace', email = 'ada@example.com' } = {}) {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1', email }, access_token: 't' }
    useUserStore().name = name
  }

  async function openMenu() {
    await wrapper.get('[data-testid="sidebar-user-trigger"]').trigger('click')
    await flushPromises()
  }

  it('is hidden when unauthenticated', async () => {
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-user-trigger"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="sidebar-sign-out"]').exists()).toBe(false)
  })

  it('shows the upper-cased initial and the display name', async () => {
    signIn()
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.get('[data-testid="sidebar-user-initial"]').text()).toBe('A')
    expect(wrapper.get('[data-testid="sidebar-user-name"]').text()).toBe('ada lovelace')
    const trigger = wrapper.get('[data-testid="sidebar-user-trigger"]')
    expect(trigger.attributes('aria-label')).toBe('Account menu for ada lovelace')
    expect(trigger.attributes('title')).toBe('ada lovelace')
    expect(trigger.attributes('aria-haspopup')).toBe('menu')
    expect(trigger.attributes('aria-expanded')).toBe('false')
    // No dangling id reference while the menu is closed.
    expect(trigger.attributes('aria-controls')).toBeUndefined()
  })

  it('never shows the full email in the row itself', async () => {
    signIn()
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.text()).not.toContain('ada@example.com')
  })

  // stores/user.js writes 'Learner' when the name is left blank; the row
  // treats that placeholder as unset and falls back to the email's local part.
  it("treats the store's 'Learner' placeholder as no name", async () => {
    signIn({ name: 'Learner', email: 'zed@example.com' })
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.get('[data-testid="sidebar-user-initial"]').text()).toBe('Z')
    expect(wrapper.get('[data-testid="sidebar-user-name"]').text()).toBe('zed')
  })

  it("falls back to the email's local part when no name is set", async () => {
    signIn({ name: null, email: 'zed@example.com' })
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.get('[data-testid="sidebar-user-initial"]').text()).toBe('Z')
    expect(wrapper.get('[data-testid="sidebar-user-name"]').text()).toBe('zed')
    expect(wrapper.get('[data-testid="sidebar-user-trigger"]').attributes('title')).toBe('zed')
  })

  it('treats a whitespace-only name as no name', async () => {
    signIn({ name: '   ', email: 'zed@example.com' })
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.get('[data-testid="sidebar-user-name"]').text()).toBe('zed')
  })

  it('keeps Sign out inside the closed menu until the row is opened', async () => {
    signIn()
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-sign-out"]').exists()).toBe(false)
    await openMenu()
    expect(wrapper.find('[data-testid="sidebar-sign-out"]').exists()).toBe(true)
  })

  it('opens a labelled menu with the email head, Settings, Usage, Account and Sign out', async () => {
    signIn()
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await openMenu()
    const trigger = wrapper.get('[data-testid="sidebar-user-trigger"]')
    const menu = wrapper.get('[data-testid="sidebar-user-menu"]')
    // role=menu sits on the inner list, which holds only the menuitems; the
    // email head stays outside it.
    const list = menu.get('[role="menu"]')
    expect(list.attributes('data-testid')).toBe('sidebar-user-menu-list')
    expect(trigger.attributes('aria-expanded')).toBe('true')
    expect(trigger.attributes('aria-controls')).toBe(list.attributes('id'))
    expect(menu.attributes('role')).toBeUndefined()
    expect(list.attributes('aria-label')).toBe('Account menu for ada lovelace')
    const head = menu.get('[data-testid="sidebar-user-menu-email"]')
    expect(head.text()).toBe('ada@example.com')
    expect(list.element.contains(head.element)).toBe(false)
    const items = list.findAll('[role="menuitem"]')
    expect(items.map((i) => i.text())).toEqual(['Settings', 'Usage', 'Account', 'Sign out'])

    // Every item carries a drawn icon, hidden from assistive tech.
    for (const item of items) {
      expect(item.get('svg').attributes('aria-hidden')).toBe('true')
    }

    // A rule sets Sign out apart from the navigation items.
    expect(list.findAll('[role="separator"]')).toHaveLength(1)
    // Focus moves into the menu on open.
    expect(document.activeElement).toBe(items[0].element)
  })

  it('ArrowDown and Enter on the trigger open the menu on the first item', async () => {
    signIn()
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    const trigger = wrapper.get('[data-testid="sidebar-user-trigger"]')

    for (const key of ['ArrowDown', 'Enter']) {
      trigger.element.focus()
      await trigger.trigger('keydown', { key })
      await flushPromises()
      expect(trigger.attributes('aria-expanded')).toBe('true')
      expect(document.activeElement).toBe(
        wrapper.get('[data-testid="sidebar-user-menu-settings"]').element,
      )
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
      await flushPromises()
      expect(wrapper.find('[data-testid="sidebar-user-menu"]').exists()).toBe(false)
    }
  })

  it('ArrowUp on the trigger opens the menu on the last item', async () => {
    signIn()
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    const trigger = wrapper.get('[data-testid="sidebar-user-trigger"]')
    trigger.element.focus()
    await trigger.trigger('keydown', { key: 'ArrowUp' })
    await flushPromises()
    expect(document.activeElement).toBe(wrapper.get('[data-testid="sidebar-sign-out"]').element)
  })

  it('ArrowDown and ArrowUp cycle the menu items, Home and End jump', async () => {
    signIn()
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await openMenu()
    const menu = wrapper.get('[data-testid="sidebar-user-menu"]')
    const [settings, usage, , signOut] = menu.findAll('[role="menuitem"]')
    await menu.trigger('keydown', { key: 'ArrowDown' })
    expect(document.activeElement).toBe(usage.element)
    await menu.trigger('keydown', { key: 'ArrowUp' })
    await menu.trigger('keydown', { key: 'ArrowUp' })
    expect(document.activeElement).toBe(signOut.element)
    await menu.trigger('keydown', { key: 'ArrowDown' })
    expect(document.activeElement).toBe(settings.element)
    await menu.trigger('keydown', { key: 'End' })
    expect(document.activeElement).toBe(signOut.element)
    await menu.trigger('keydown', { key: 'Home' })
    expect(document.activeElement).toBe(settings.element)
  })

  it('Tab closes the menu and leaves focus on the trigger', async () => {
    signIn()
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await openMenu()
    const menu = wrapper.get('[data-testid="sidebar-user-menu"]')
    const ev = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
    menu.element.dispatchEvent(ev)
    await flushPromises()
    expect(ev.defaultPrevented).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-user-menu"]').exists()).toBe(false)
    expect(document.activeElement).toBe(wrapper.get('[data-testid="sidebar-user-trigger"]').element)
  })

  it.each([
    ['settings', '/settings'],
    ['usage', { name: 'settings', params: { tab: 'usage' } }],
    ['account', { name: 'account' }],
  ])('%s routes, closes, and refocuses the trigger', async (slug, to) => {
    signIn()
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await openMenu()
    await wrapper.get(`[data-testid="sidebar-user-menu-${slug}"]`).trigger('click')
    await flushPromises()
    expect(routerPush).toHaveBeenCalledWith(to)
    expect(wrapper.find('[data-testid="sidebar-user-menu"]').exists()).toBe(false)
    expect(document.activeElement).toBe(wrapper.get('[data-testid="sidebar-user-trigger"]').element)
  })

  it('a menu item in the mobile drawer closes the drawer as it routes', async () => {
    setViewport(390)
    signIn()
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    useSidebar().openDrawer()
    await flushPromises()
    await openMenu()
    await wrapper.get('[data-testid="sidebar-user-menu-settings"]').trigger('click')
    await flushPromises()
    expect(routerPush).toHaveBeenCalledWith('/settings')
    expect(useSidebar().mode.value).not.toBe('drawer-open')
  })

  it('Escape closes the menu and returns focus to the trigger', async () => {
    signIn()
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await openMenu()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()
    const trigger = wrapper.get('[data-testid="sidebar-user-trigger"]')
    expect(wrapper.find('[data-testid="sidebar-user-menu"]').exists()).toBe(false)
    expect(trigger.attributes('aria-expanded')).toBe('false')
    expect(document.activeElement).toBe(trigger.element)
  })

  it('Escape in the mobile drawer closes only the menu, not the drawer', async () => {
    setViewport(390)
    signIn()
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    useSidebar().openDrawer()
    await flushPromises()
    await openMenu()
    expect(wrapper.find('[data-testid="sidebar-user-menu"]').exists()).toBe(true)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-user-menu"]').exists()).toBe(false)
    expect(wrapper.get('aside').attributes('data-mode')).toBe('drawer-open')
    expect(document.activeElement).toBe(wrapper.get('[data-testid="sidebar-user-trigger"]').element)
  })

  it('an outside pointerdown closes the menu', async () => {
    signIn()
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await openMenu()
    document.body.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-user-menu"]').exists()).toBe(false)
  })

  it('folding the sidebar with the menu open closes it and refocuses the trigger', async () => {
    signIn()
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await openMenu()
    expect(document.activeElement).toBe(
      wrapper.get('[data-testid="sidebar-user-menu-settings"]').element,
    )
    useSidebar().toggleDesktop()
    await flushPromises()
    expect(useSidebar().mode.value).toBe('collapsed')
    expect(document.querySelector('[data-testid="sidebar-user-menu"]')).toBeNull()
    expect(document.activeElement).toBe(wrapper.get('[data-testid="sidebar-user-trigger"]').element)
  })

  it('signs out and redirects to /login', async () => {
    signIn()
    wrapper = mount(Sidebar)
    await flushPromises()
    await openMenu()
    await wrapper.get('[data-testid="sidebar-sign-out"]').trigger('click')
    await flushPromises()
    expect(globalThis.__supabaseAuthStub.signOut).toHaveBeenCalled()
    expect(routerPush).toHaveBeenCalledWith('/login')
  })

  it('surfaces an error toast and still leaves the protected route on failure', async () => {
    globalThis.__supabaseAuthStub.signOut.mockResolvedValueOnce({
      error: new Error('network down'),
    })
    signIn()
    wrapper = mount(Sidebar)
    await flushPromises()
    await openMenu()
    await wrapper.get('[data-testid="sidebar-sign-out"]').trigger('click')
    await flushPromises()
    expect(showError).toHaveBeenCalledWith('network down')
    // The store clears the local session in its finally, so the shell is
    // already signed out; staying on a protected route would strand the
    // learner behind a toast.
    expect(routerPush).toHaveBeenCalledWith('/login')
  })

  it('the folded rail shows the initial alone, the name as tooltip, and still opens the menu', async () => {
    sidebarTest._setExpanded(false)
    signIn()
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    expect(wrapper.get('[data-testid="sidebar-user-initial"]').text()).toBe('A')
    expect(wrapper.find('[data-testid="sidebar-user-name"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="sidebar-user-trigger"]').attributes('title')).toBe(
      'ada lovelace',
    )
    await openMenu()
    // Folded, the card lifts out of the clipped rail onto <body>.
    const menu = document.querySelector('[data-testid="sidebar-user-menu"]')
    expect(menu).not.toBeNull()
    expect(wrapper.element.contains(menu)).toBe(false)
    expect(menu.querySelector('[data-testid="sidebar-sign-out"]')).not.toBeNull()
    expect(document.activeElement).toBe(
      menu.querySelector('[data-testid="sidebar-user-menu-settings"]'),
    )
  })

  // Folded, the menu opens where it does unfolded: directly above the avatar,
  // its left edge on the avatar's, not out beside the rail.
  it('the folded menu opens above the avatar, left-aligned with it', async () => {
    sidebarTest._setExpanded(false)
    const savedHeight = window.innerHeight
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 })

    try {
      signIn()
      wrapper = mount(Sidebar, { attachTo: document.body })
      await flushPromises()
      // Folded, the 36px trigger centres the 28px avatar, 4px in from its edge.
      const trigger = wrapper.get('[data-testid="sidebar-user-trigger"]').element
      const avatar = wrapper.get('[data-testid="sidebar-user-initial"]').element
      vi.spyOn(trigger, 'getBoundingClientRect').mockReturnValue({
        left: 6,
        right: 42,
        top: 700,
        bottom: 736,
        width: 36,
        height: 36,
      })
      vi.spyOn(avatar, 'getBoundingClientRect').mockReturnValue({
        left: 10,
        right: 38,
        top: 704,
        bottom: 732,
        width: 28,
        height: 28,
      })
      await openMenu()
      const menu = document.querySelector('[data-testid="sidebar-user-menu"]')
      expect(menu.style.left).toBe('10px')
      // 0.25rem (4px) gap above the trigger's top edge, as unfolded.
      expect(menu.style.bottom).toBe('104px')
    } finally {
      Object.defineProperty(window, 'innerHeight', { configurable: true, value: savedHeight })
    }
  })

  it('the mobile drawer shows the identity row with the name', async () => {
    setViewport(390)
    signIn()
    wrapper = mount(Sidebar)
    await flushPromises()
    useSidebar().openDrawer()
    await flushPromises()
    expect(wrapper.get('[data-testid="sidebar-user-initial"]').text()).toBe('A')
    expect(wrapper.get('[data-testid="sidebar-user-name"]').text()).toBe('ada lovelace')
  })
})

describe('Sidebar.vue — mount fetch', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    routerPush.mockClear()
    localStorage.clear()
    setViewport(1400)
    sidebarTest._setExpanded(true)
    routeRef.params = {}
  })
  afterEach(() => wrapper?.unmount())

  it('calls store.listSessions on mount when authenticated and empty', async () => {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1' }, access_token: 't' }
    const store = useSessionStore()
    const listSpy = vi.spyOn(store, 'listSessions').mockResolvedValue([])
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(listSpy).toHaveBeenCalled()
  })

  it('skips list fetch when sessions already populated', async () => {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1' }, access_token: 't' }
    const store = useSessionStore()
    store.sessions = [{ id: 'a1', topic: 'X', created_at: '2026-05-20T10:00:00Z', ended_at: null }]
    const listSpy = vi.spyOn(store, 'listSessions').mockResolvedValue([])
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(listSpy).not.toHaveBeenCalled()
  })

  it('skips list fetch when unauthenticated', async () => {
    const store = useSessionStore()
    const listSpy = vi.spyOn(store, 'listSessions').mockResolvedValue([])
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(listSpy).not.toHaveBeenCalled()
  })
})

describe('Sidebar.vue — recall entry', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    routerPush.mockClear()
    localStorage.clear()
    setViewport(1400)
    sidebarTest._setExpanded(true)
    routeRef.params = {}
    routeRef.fullPath = '/'
    // Review-queue badge fetch is gated on isAuthenticated, same signal the
    // sessions fetch already uses (see "mount fetch" describe above).
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1' }, access_token: 't' }
    // Sessions fetch runs before the review-queue fetch in onMounted; stub it
    // so the unrelated real network call doesn't delay/interfere with the
    // review assertions (mirrors the "mount fetch" describe's pattern).
    const store = useSessionStore()
    vi.spyOn(store, 'listSessions').mockResolvedValue([])
    // Badge fetch is deferred via runWhenIdle; stub requestIdleCallback to
    // run synchronously so the existing badge assertions still hold.
    globalThis.requestIdleCallback = (cb) => {
      cb()

      return 1
    }

    globalThis.cancelIdleCallback = () => {}
  })
  afterEach(() => {
    wrapper?.unmount()
    delete globalThis.requestIdleCallback
    delete globalThis.cancelIdleCallback
  })

  it('shows the recall entry with a count when concepts are due', async () => {
    apiReviewQueue.mockResolvedValue({ items: [], total: 13, limit: 1, offset: 0 })
    wrapper = mount(Sidebar)
    await flushPromises()
    const entry = wrapper.get('[data-testid="sidebar-recall"]')
    expect(entry.text()).toContain('Recall')
    expect(entry.text()).toContain('13')
    expect(apiReviewQueue).toHaveBeenCalledWith({ limit: 1, offset: 0 }, { silent: true })
  })

  it('hides the recall entry when nothing is due', async () => {
    apiReviewQueue.mockResolvedValue({ items: [], total: 0, limit: 1, offset: 0 })
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-recall"]').exists()).toBe(false)
  })

  it('hides the recall entry when the fetch fails', async () => {
    apiReviewQueue.mockRejectedValue(new Error('boom'))
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-recall"]').exists()).toBe(false)
  })

  it('keeps the recall entry in the icon rail (collapsed) with the due count', async () => {
    sidebarTest._setExpanded(false)
    apiReviewQueue.mockResolvedValue({ items: [], total: 13, limit: 1, offset: 0 })
    wrapper = mount(Sidebar)
    await flushPromises()
    const entry = wrapper.get('[data-testid="sidebar-recall"]')
    expect(entry.text()).toContain('13')
    expect(entry.attributes('aria-label')).toBe('Recall: 13 concepts due')
  })

  it('hides the rail recall entry when nothing is due', async () => {
    sidebarTest._setExpanded(false)
    apiReviewQueue.mockResolvedValue({ items: [], total: 0, limit: 1, offset: 0 })
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-recall"]').exists()).toBe(false)
  })

  it('does not fetch the badge before the idle callback runs', async () => {
    let idleCb
    globalThis.requestIdleCallback = (cb) => {
      idleCb = cb

      return 1
    }

    wrapper = mount(Sidebar)
    await flushPromises()
    expect(apiReviewQueue).not.toHaveBeenCalled()
    idleCb()
    await flushPromises()
    expect(apiReviewQueue).toHaveBeenCalledWith({ limit: 1, offset: 0 }, { silent: true })
  })

  it('unmount cancels the pending idle badge fetch', async () => {
    globalThis.requestIdleCallback = () => 1
    const cancelSpy = vi.fn()
    globalThis.cancelIdleCallback = cancelSpy
    wrapper = mount(Sidebar)
    await flushPromises()
    wrapper.unmount()
    expect(cancelSpy).toHaveBeenCalledWith(1)
  })
})

// The desktop collapse toggle is a drawn sidebar icon in the head (the old
// right-edge half-tab overlapped the mark in the rail), and the collapsed rail
// marks sessions as dots instead of strokes.
describe('Sidebar.vue — collapse toggle and empty rail', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    routerPush.mockClear()
    localStorage.clear()
    setViewport(1400)
    routeRef.params = {}
    routeRef.fullPath = '/'
  })
  afterEach(() => wrapper?.unmount())

  it('the head sidebar-icon toggle carries hit-44 and a descriptive aria-label', async () => {
    sidebarTest._setExpanded(true)
    wrapper = mount(Sidebar)
    await flushPromises()
    const toggle = wrapper.get('[data-testid="sidebar-collapse-toggle"]')
    expect(toggle.classes()).toContain('hit-44')
    expect(toggle.classes()).toContain('sb-toggle--head')
    expect(toggle.classes()).not.toContain('sb-toggle--edge')
    expect(toggle.element.closest('.sb-header')).not.toBeNull()
    expect(toggle.attributes('aria-label')).toBe('Collapse sidebar')

    await toggle.trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="sidebar-collapse-toggle"]').attributes('aria-label')).toBe(
      'Expand sidebar',
    )
  })

  it('the collapsed rail draws no session markers, even for the current session', async () => {
    sidebarTest._setExpanded(false)
    routeRef.params = { id: 'a1' }
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
      { id: 'a2', topic: 'Trees', created_at: new Date().toISOString(), ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('.sb-row-mark').exists()).toBe(false)
    expect(wrapper.find('.sb-session-list').exists()).toBe(false)
    expect(wrapper.find('[data-session-id]').exists()).toBe(false)
  })
})

describe('session store — rename + pin actions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renameSession optimistically updates the row and calls the API', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'old', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
    ]
    const api = await import('@/services/sessionsApi.js')
    vi.spyOn(api, 'renameSession').mockResolvedValue({ id: 'a1', topic: 'new', pinned: false })
    await store.renameSession('a1', 'new')
    expect(store.sessions[0].topic).toBe('new')
    expect(api.renameSession).toHaveBeenCalledWith('a1', 'new')
  })

  it('setPinned applies optimistic update then rolls back on API error', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'x', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
    ]
    const api = await import('@/services/sessionsApi.js')
    let reject
    vi.spyOn(api, 'setPinned').mockReturnValue(
      new Promise((_, r) => {
        reject = r
      }),
    )
    const p = store.setPinned('a1', true).catch(() => {})
    expect(store.sessions[0].pinned).toBe(true) // optimistic applied
    reject(new Error('boom'))
    await p
    expect(store.sessions[0].pinned).toBe(false) // rolled back
  })

  it('setPinned syncs currentSession.pinned and rolls it back on error', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'X', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
    ]
    store.currentSession = { id: 'a1', topic: 'X', ended_at: null, pinned: false }
    const api = await import('@/services/sessionsApi.js')
    let reject
    vi.spyOn(api, 'setPinned').mockReturnValue(
      new Promise((_, r) => {
        reject = r
      }),
    )
    const p = store.setPinned('a1', true).catch(() => {})
    expect(store.currentSession.pinned).toBe(true)
    reject(new Error('boom'))
    await p
    expect(store.currentSession.pinned).toBe(false)
  })

  it('renameSession rolls back topic on API error', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'old', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
    ]
    const api = await import('@/services/sessionsApi.js')
    let reject
    vi.spyOn(api, 'renameSession').mockReturnValue(
      new Promise((_, r) => {
        reject = r
      }),
    )
    const p = store.renameSession('a1', 'new').catch(() => {})
    expect(store.sessions[0].topic).toBe('new') // optimistic applied
    reject(new Error('boom'))
    await p
    expect(store.sessions[0].topic).toBe('old') // rolled back
  })
})

describe('Sidebar.vue — header states', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    routerPush.mockClear()
    localStorage.clear()
    setViewport(1400)
    sidebarTest._setExpanded(true)
    routeRef.params = {}
    routeRef.fullPath = '/'
  })
  afterEach(() => {
    wrapper?.unmount()
    useSidebar().closeDrawer()
  })

  it('expanded desktop header shows the logo and a collapse toggle', async () => {
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('.sb-brand').exists()).toBe(true)
    const toggle = wrapper.find('[data-testid="sidebar-collapse-toggle"]')
    expect(toggle.exists()).toBe(true)
    expect(toggle.attributes('aria-label')).toBe('Collapse sidebar')
  })

  // The collapsed rail carries no logo: it starts at the expand toggle.
  it('collapsed desktop header shows only the expand toggle, no logo', async () => {
    sidebarTest._setExpanded(false)
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('.sb-brand').exists()).toBe(false)
    expect(wrapper.find('.sb-header').findComponent(Logo).exists()).toBe(false)
    const toggle = wrapper.find('[data-testid="sidebar-collapse-toggle"]')
    expect(toggle.exists()).toBe(true)
    expect(toggle.attributes('aria-label')).toBe('Expand sidebar')
  })

  it('mobile drawer header shows the logo and a right-aligned close button', async () => {
    setViewport(600)
    const { openDrawer } = useSidebar()
    openDrawer()
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('.sb-brand').exists()).toBe(true)
    const close = wrapper.find('[data-testid="sidebar-drawer-close"]')
    expect(close.exists()).toBe(true)
    expect(close.classes()).toContain('sb-toggle--end')
  })
})

// Builds N active sessions with descending activity so ordering is deterministic
// (most-recent first) when the component slices down to the cap.
function makeActiveSessions(count, { pinned = false, prefix = 'u' } = {}) {
  const now = Date.now()

  return Array.from({ length: count }, (_, i) => ({
    id: `${prefix}${i}`,
    topic: `${prefix}${i}`,
    created_at: new Date(now - i * 1000).toISOString(),
    last_activity_at: new Date(now - i * 1000).toISOString(),
    ended_at: null,
    pinned,
  }))
}

function makeEndedSessions(count) {
  const now = Date.now()

  return Array.from({ length: count }, (_, i) => ({
    id: `e${i}`,
    topic: `e${i}`,
    created_at: new Date(now - i * 1000).toISOString(),
    last_activity_at: new Date(now - i * 1000).toISOString(),
    ended_at: new Date(now - i * 1000).toISOString(),
  }))
}

// jsdom ships no ResizeObserver and reports clientHeight 0, so the component's
// fit-to-height measurement is unreachable by default. This installs a stub
// that reports `height` for the observed element and fires the callback once,
// synchronously, on observe() -- i.e. the first measurement the browser makes.
function installResizeObserverStub(height) {
  globalThis.ResizeObserver = class {
    constructor(cb) {
      this._cb = cb
    }
    observe(el) {
      Object.defineProperty(el, 'clientHeight', { configurable: true, value: height })
      this._cb([{ target: el }], this)
    }
    unobserve() {}
    disconnect() {}
  }
}

describe('sidebar row cap and View all links', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    routerPush.mockClear()
    localStorage.clear()
    setViewport(1400) // desktop expanded
    sidebarTest._setExpanded(true)
    routeRef.params = {}
    routeRef.fullPath = '/'
  })
  afterEach(() => wrapper?.unmount())

  it('renders at most 15 active rows (pinned count toward the cap)', async () => {
    const store = useSessionStore()
    const pinnedRows = makeActiveSessions(3, { pinned: true, prefix: 'p' })
    const unpinnedRows = makeActiveSessions(25, { pinned: false, prefix: 'u' })
    store.sessions = [...pinnedRows, ...unpinnedRows]
    store.activeTotal = 28
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(
      wrapper.findAll('[data-testid="sidebar-section-pinned"] [data-session-id]'),
    ).toHaveLength(3)
    expect(wrapper.findAll('[data-testid="sidebar-quick-group"] [data-session-id]')).toHaveLength(
      12,
    )
    const viewAll = wrapper.find('[data-testid="sidebar-view-all-active"]')
    expect(viewAll.exists()).toBe(true)
    expect(viewAll.text()).toContain('View all 28 sessions')

    const viewAllComponent = wrapper
      .findAllComponents(MockRouterLink)
      .find((c) => c.attributes('data-testid') === 'sidebar-view-all-active')

    expect(viewAllComponent.props('to')).toEqual({
      name: 'sessions-library',
      query: { status: 'active' },
    })
  })

  it('caps pinned rows themselves at 15, leaving no room for unpinned rows', async () => {
    const store = useSessionStore()
    const pinnedRows = makeActiveSessions(25, { pinned: true, prefix: 'p' })
    const unpinnedRows = makeActiveSessions(5, { pinned: false, prefix: 'u' })
    store.sessions = [...pinnedRows, ...unpinnedRows]
    store.activeTotal = 30
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(
      wrapper.findAll('[data-testid="sidebar-section-pinned"] [data-session-id]'),
    ).toHaveLength(15)
    expect(wrapper.findAll('[data-testid="sidebar-quick-group"] [data-session-id]')).toHaveLength(0)
  })

  it('caps the ended tab at 15 and links with status=ended', async () => {
    const store = useSessionStore()
    store.sessions = makeEndedSessions(22)
    store.endedTotal = 40
    wrapper = mount(Sidebar)
    await flushPromises()
    await wrapper.find('[data-testid="sidebar-status-ended"]').trigger('click')
    expect(wrapper.findAll('[data-testid="sidebar-section-ended"] [data-session-id]')).toHaveLength(
      15,
    )
    const viewAll = wrapper.find('[data-testid="sidebar-view-all-ended"]')
    expect(viewAll.exists()).toBe(true)
    expect(viewAll.text()).toContain('40')

    const viewAllComponent = wrapper
      .findAllComponents(MockRouterLink)
      .find((c) => c.attributes('data-testid') === 'sidebar-view-all-ended')

    expect(viewAllComponent.props('to')).toEqual({
      name: 'sessions-library',
      query: { status: 'ended' },
    })
  })

  it('shows View all as the last line even when every session is rendered', async () => {
    const store = useSessionStore()
    store.sessions = makeActiveSessions(5)
    store.activeTotal = 5
    wrapper = mount(Sidebar)
    await flushPromises()
    const viewAll = wrapper.find('[data-testid="sidebar-view-all-active"]')
    expect(viewAll.exists()).toBe(true)
    expect(viewAll.text()).toContain('View all 5 sessions')
  })

  it('ended tab badge shows the server total, not the loaded count', async () => {
    const store = useSessionStore()
    store.sessions = makeEndedSessions(20)
    store.endedTotal = 40
    wrapper = mount(Sidebar)
    await flushPromises()
    const endedTab = wrapper.find('[data-testid="sidebar-status-ended"]')
    expect(endedTab.text()).toContain('(40)')
  })

  it('ending a session from the sidebar updates the Ended badge and View all counts immediately, without a refetch', async () => {
    const store = useSessionStore()
    store.sessions = [
      {
        id: 'a1',
        topic: 'Big-O',
        created_at: '2026-05-20T10:00:00Z',
        ended_at: null,
        pinned: false,
      },
    ]
    store.activeTotal = 1
    store.endedTotal = 0
    const api = await import('@/services/sessionsApi.js')
    vi.spyOn(api, 'endSession').mockResolvedValue({
      ended_at: '2026-05-21T10:00:00Z',
      summary: null,
    })
    const listSpy = vi.spyOn(store, 'listSessions')
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-end"]').trigger('click')
    await flushPromises()
    expect(listSpy).not.toHaveBeenCalled()
    expect(store.activeTotal).toBe(0)
    expect(store.endedTotal).toBe(1)
    const endedTab = wrapper.find('[data-testid="sidebar-status-ended"]')
    expect(endedTab.text()).toContain('(1)')
  })

  it('the pinned section header reports the capped rendered count, not the uncapped list length', async () => {
    const store = useSessionStore()
    store.sessions = makeActiveSessions(25, { pinned: true, prefix: 'p' })
    store.activeTotal = 25
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(
      wrapper.findAll('[data-testid="sidebar-section-pinned"] [data-session-id]'),
    ).toHaveLength(15)
    expect(
      wrapper.find('[data-testid="sidebar-section-pinned"] .sb-section-count').text(),
    ).toContain('15')
  })

  // The totals are a local mirror: createSession bumps activeTotal without
  // pushing into the (windowed) `sessions` array, so a brand-new account sits
  // at activeTotal=1 with zero rows. Offering "View all 1 sessions" directly
  // under "No sessions yet" is the first-run path, and the two statements
  // contradict each other.
  it('never offers the active View all link while no rows are rendered', async () => {
    const store = useSessionStore()
    wrapper = mount(Sidebar)
    await flushPromises()
    // Exactly what createSession does on a fresh account.
    store.activeTotal = 1
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-empty-hint"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-view-all-active"]').exists()).toBe(false)
  })

  // Fit-to-height: with a real ResizeObserver the cap grows to whatever the
  // list column has room for (one pitch reserved for the View all line),
  // clamped to [15, 40]. jsdom has no ResizeObserver, which is exactly why
  // every case above still sees the 15-row floor.
  it('renders as many rows as the measured list height allows, up to 40', async () => {
    installResizeObserverStub(28 * 31)

    try {
      const store = useSessionStore()
      store.sessions = makeActiveSessions(40)
      store.activeTotal = 40
      wrapper = mount(Sidebar)
      await flushPromises()
      expect(wrapper.findAll('[data-testid="sidebar-quick-group"] [data-session-id]')).toHaveLength(
        30,
      )
    } finally {
      delete globalThis.ResizeObserver
    }
  })

  it('keeps the 15-row floor when the measured height fits fewer rows', async () => {
    installResizeObserverStub(100)

    try {
      const store = useSessionStore()
      store.sessions = makeActiveSessions(40)
      store.activeTotal = 40
      wrapper = mount(Sidebar)
      await flushPromises()
      expect(wrapper.findAll('[data-testid="sidebar-quick-group"] [data-session-id]')).toHaveLength(
        15,
      )
    } finally {
      delete globalThis.ResizeObserver
    }
  })

  it('never offers the ended View all link while no ended rows are rendered', async () => {
    const store = useSessionStore()
    wrapper = mount(Sidebar)
    await flushPromises()
    // e.g. ending a session that was outside the loaded ended window.
    store.endedTotal = 1
    await flushPromises()
    await wrapper.find('[data-testid="sidebar-status-ended"]').trigger('click')
    expect(wrapper.find('[data-testid="sidebar-ended-empty"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sidebar-view-all-ended"]').exists()).toBe(false)
  })
})

describe('Sidebar.vue — profile entry (#362)', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    routerPush.mockClear()
    localStorage.clear()
    setViewport(1400)
    sidebarTest._setExpanded(true)
    routeRef.params = {}
    routeRef.fullPath = '/'
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1' }, access_token: 't' }
    const store = useSessionStore()
    vi.spyOn(store, 'listSessions').mockResolvedValue([])
    globalThis.requestIdleCallback = (cb) => {
      cb()

      return 1
    }

    globalThis.cancelIdleCallback = () => {}
  })
  afterEach(() => {
    wrapper?.unmount()
    delete globalThis.requestIdleCallback
    delete globalThis.cancelIdleCallback
  })

  const profileLink = () =>
    wrapper
      .findAllComponents(MockRouterLink)
      .find((l) => l.attributes('data-testid') === 'sidebar-profile')

  it('shows a Profile line to /profile even when nothing is due for recall', async () => {
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-recall"]').exists()).toBe(false)
    const link = profileLink()
    expect(link).toBeTruthy()
    expect(link.props('to')).toEqual({ name: 'profile-aggregate' })
    expect(link.text()).toContain('Profile')
    expect(link.find('svg').exists()).toBe(true)
  })

  it('sits directly beside Recall when Recall is shown', async () => {
    apiReviewQueue.mockResolvedValue({ items: [], total: 2, limit: 1, offset: 0 })
    wrapper = mount(Sidebar)
    await flushPromises()
    const profile = wrapper.get('[data-testid="sidebar-profile"]').element
    expect(profile.nextElementSibling?.getAttribute('data-testid')).toBe('sidebar-recall')
  })

  it('keeps Profile in the folded rail as a titled icon, beside Recall', async () => {
    sidebarTest._setExpanded(false)
    apiReviewQueue.mockResolvedValue({ items: [], total: 2, limit: 1, offset: 0 })
    wrapper = mount(Sidebar)
    await flushPromises()
    const el = wrapper.get('[data-testid="sidebar-profile"]')
    expect(el.attributes('title')).toBe('Profile')
    expect(el.attributes('aria-label')).toBe('Profile')
    expect(el.text()).toBe('')
    expect(el.element.nextElementSibling?.getAttribute('data-testid')).toBe('sidebar-recall')
  })

  it('shows Profile in the mobile drawer and closes the drawer on click', async () => {
    setViewport(390)
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    useSidebar().openDrawer()
    await flushPromises()
    const el = wrapper.get('[data-testid="sidebar-profile"]')
    expect(el.text()).toContain('Profile')
    await el.trigger('click')
    expect(useSidebar().mode.value).not.toBe('drawer-open')
  })
})
