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

vi.mock('@/composables/useToast.js', () => ({
  useToast: () => ({ showError: vi.fn(), showWarn: vi.fn(), showSuccess: vi.fn() }),
}))

vi.mock('primevue/useconfirm', () => ({
  useConfirm: () => ({ require: (cfg) => cfg.accept?.() }),
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
import { useSessionStore } from '@/stores/session.js'
import { useAuthStore } from '@/stores/auth.js'
import { useSidebar, __test__ as sidebarTest } from '@/composables/useSidebar.js'

function setViewport(w) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: w })
  sidebarTest._setViewport(w)
}

describe('Sidebar.vue -- folded icon rail', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    routerPush.mockClear()
    localStorage.clear()
    setViewport(1400)
    sidebarTest._setExpanded(false)
    routeRef.params = {}
    routeRef.fullPath = '/'
    apiReviewQueue.mockReset()
    apiReviewQueue.mockResolvedValue({ items: [], total: 0, limit: 1, offset: 0 })
    apiGetSessionLibrary.mockReset()
    apiGetSessionLibrary.mockResolvedValue({ items: [], total: 0, limit: 15, offset: 0 })
    useAuthStore().session = { user: { id: 'u-1' }, access_token: 't' }
    vi.spyOn(useSessionStore(), 'listSessions').mockResolvedValue([])
    globalThis.requestIdleCallback = (cb) => {
      cb()

      return 1
    }

    globalThis.cancelIdleCallback = () => {}
  })
  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    delete globalThis.requestIdleCallback
    delete globalThis.cancelIdleCallback
    document.body.innerHTML = ''
  })

  it('the toggle is present in both states with the matching label', async () => {
    wrapper = mount(Sidebar)
    await flushPromises()
    const folded = wrapper.get('[data-testid="sidebar-collapse-toggle"]')
    expect(folded.attributes('aria-label')).toBe('Expand sidebar')
    expect(folded.attributes('title')).toBe('Expand sidebar')

    await folded.trigger('click')
    await flushPromises()
    const open = wrapper.get('[data-testid="sidebar-collapse-toggle"]')
    expect(open.attributes('aria-label')).toBe('Collapse sidebar')
    expect(open.attributes('title')).toBe('Collapse sidebar')
  })

  // The rail starts at the toggle: no logo above or below it.
  it('the folded head draws the toggle alone, without the mark', async () => {
    wrapper = mount(Sidebar)
    await flushPromises()
    const header = wrapper.get('.sb-header')
    expect(header.find('[data-testid="sidebar-collapse-toggle"]').exists()).toBe(true)
    expect(header.find('.sb-brand').exists()).toBe(false)
  })

  // WCAG 2.4.3: open, the toggle follows the wordmark in DOM order, matching
  // how it is drawn.
  it('the head toggle follows the wordmark in DOM order when open', async () => {
    const precedes = (a, b) =>
      Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING)

    wrapper = mount(Sidebar)
    await flushPromises()
    await wrapper.get('[data-testid="sidebar-collapse-toggle"]').trigger('click')
    await flushPromises()
    const header = wrapper.get('.sb-header')
    const toggle = header.get('[data-testid="sidebar-collapse-toggle"]').element
    const brand = header.get('.sb-brand').element
    expect(precedes(brand, toggle)).toBe(true)
  })

  // Rail order: toggle, New session, Search, then the identity foot. No
  // session row sits between the actions and the foot.
  it('the folded rail exposes only its actions, in order', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'Big-O', created_at: new Date().toISOString(), ended_at: null },
    ]
    wrapper = mount(Sidebar)
    await flushPromises()

    const ids = wrapper
      .findAll('button, a')
      .map((w) => w.attributes('data-testid'))
      .filter(Boolean)

    expect(ids.slice(0, 3)).toEqual([
      'sidebar-collapse-toggle',
      'sidebar-new-session',
      'sidebar-rail-search',
    ])
    expect(wrapper.find('[data-session-id]').exists()).toBe(false)
    // The empty list column is layout only, not a landmark.
    expect(wrapper.get('nav.sb-list-wrap').attributes('aria-hidden')).toBe('true')
  })

  // Unfolding inserts the wordmark ahead of the toggle; a keyboard user must
  // not lose focus to <body> when they fold or unfold.
  it('keeps focus on the head toggle across folding and unfolding', async () => {
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()

    for (let i = 0; i < 2; i++) {
      const toggle = wrapper.get('[data-testid="sidebar-collapse-toggle"]')
      toggle.element.focus()
      await toggle.trigger('click')
      await flushPromises()
      expect(document.activeElement).toBe(
        wrapper.get('[data-testid="sidebar-collapse-toggle"]').element,
      )
    }
  })

  it('exposes New session and Search rows with names and tooltips', async () => {
    wrapper = mount(Sidebar)
    await flushPromises()
    const newSession = wrapper.get('[data-testid="sidebar-new-session"]')
    expect(newSession.attributes('aria-label')).toBe('New session')
    expect(newSession.attributes('title')).toBe('New session')

    const search = wrapper.get('[data-testid="sidebar-rail-search"]')
    expect(search.element.tagName).toBe('BUTTON')
    expect(search.attributes('aria-label')).toBe('Search sessions')
    expect(search.attributes('title')).toBe('Search sessions')
  })

  it('shows Recall with the due count when concepts are due', async () => {
    apiReviewQueue.mockResolvedValue({ items: [], total: 4, limit: 1, offset: 0 })
    wrapper = mount(Sidebar)
    await flushPromises()
    const recall = wrapper.get('[data-testid="sidebar-recall"]')
    expect(recall.attributes('aria-label')).toBe('Recall: 4 concepts due')
    expect(recall.attributes('title')).toBe('Recall')
    expect(recall.get('.sb-rail-badge').text()).toBe('4')
  })

  it('omits Recall when nothing is due', async () => {
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-recall"]').exists()).toBe(false)
  })

  it('Search unfolds the sidebar and focuses the search field', async () => {
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-search"]').exists()).toBe(false)

    await wrapper.get('[data-testid="sidebar-rail-search"]').trigger('click')
    await flushPromises()

    expect(useSidebar().mode.value).toBe('expanded')
    const input = wrapper.get('[data-testid="sidebar-search"]')
    expect(document.activeElement).toBe(input.element)
    expect(wrapper.find('[data-testid="sidebar-rail-search"]').exists()).toBe(false)
  })

  it('the rail Search row is absent when the sidebar is expanded', async () => {
    sidebarTest._setExpanded(true)
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-rail-search"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="sidebar-search"]').exists()).toBe(true)
  })

  it('the rail Search row is not rendered on mobile', async () => {
    setViewport(390)
    wrapper = mount(Sidebar)
    await flushPromises()
    expect(wrapper.find('[data-testid="sidebar-rail-search"]').exists()).toBe(false)
  })
})
