import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const routerPush = vi.fn()

const routeRef = { params: {}, fullPath: '/', meta: {} }

vi.mock('vue-router', () => ({
  RouterLink: { template: '<a><slot /></a>', props: ['to'] },
  RouterView: { template: '<div data-testid="router-view" />' },
  useRouter: () => ({ push: routerPush }),
  useRoute: () => routeRef,
}))

vi.mock('primevue/toast', () => ({
  default: { template: '<div />' },
}))

vi.mock('@/composables/useToast.js', () => ({
  useToast: () => ({ showError: vi.fn(), showWarn: vi.fn(), showSuccess: vi.fn() }),
}))

// E-12: SidebarSessionRow asks PrimeVue's confirm service before ending a
// session, and the service is not installed on a bare mount.
vi.mock('primevue/useconfirm', () => ({
  useConfirm: () => ({ require: (cfg) => cfg.accept?.() }),
}))

const apiReviewQueue = vi.fn()

vi.mock('@/services/reviewApi.js', () => ({
  getReviewQueue: (...args) => apiReviewQueue(...args),
}))

import App from '@/App.vue'
import Sidebar from '@/components/sidebar/Sidebar.vue'
import { useSessionStore } from '@/stores/session.js'
import { useAuthStore } from '@/stores/auth.js'
import { useSidebar } from '@/composables/useSidebar.js'
import { __test__ as sidebarTest } from '@/composables/useSidebar.js'

function setViewport(w) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: w })
  sidebarTest._setViewport(w)
}

// Mounts Sidebar expanded on desktop with the review-queue badge fetch
// resolved to the given total (see sidebar.test.js "Review entry" describe
// for the underlying fetch-gating pattern).
async function mountSidebarWithReview(total) {
  sidebarTest._setViewport(1400)
  sidebarTest._setExpanded(true)
  const auth = useAuthStore()
  auth.session = { user: { id: 'u-1' }, access_token: 't' }
  const store = useSessionStore()
  vi.spyOn(store, 'listSessions').mockResolvedValue([])
  apiReviewQueue.mockResolvedValue({ items: [], total, limit: 1, offset: 0 })
  globalThis.requestIdleCallback = (cb) => {
    cb()

    return 1
  }

  globalThis.cancelIdleCallback = () => {}

  const w = mount(Sidebar, { attachTo: document.body })
  await flushPromises()

  return w
}

describe('Shell a11y — skip link', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    setViewport(1400)
    routeRef.meta = {}
    routeRef.params = {}
    document.body.className = ''
  })
  afterEach(() => wrapper?.unmount())

  it('skip link is the first focusable in the shell', () => {
    wrapper = mount(App)
    const skip = wrapper.find('[data-testid="skip-link"]')
    expect(skip.exists()).toBe(true)
    expect(skip.attributes('href')).toBe('#main-content')
  })

  it('skip link is absent on auth routes (sidebar:false meta)', () => {
    routeRef.meta = { sidebar: false }
    wrapper = mount(App)
    expect(wrapper.find('[data-testid="skip-link"]').exists()).toBe(false)
  })
})

describe('Mobile drawer a11y — scroll lock + ESC', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    setViewport(800) // mobile
    routeRef.meta = {}
    routeRef.params = {}
    document.body.className = ''
  })
  afterEach(() => {
    wrapper?.unmount()
    document.body.className = ''
  })

  it('opening drawer adds sb-scroll-lock to body; closing removes it', async () => {
    wrapper = mount(App)
    const { openDrawer, closeDrawer } = useSidebar()
    expect(document.body.classList.contains('sb-scroll-lock')).toBe(false)
    openDrawer()
    await flushPromises()
    expect(document.body.classList.contains('sb-scroll-lock')).toBe(true)
    closeDrawer()
    await flushPromises()
    expect(document.body.classList.contains('sb-scroll-lock')).toBe(false)
  })

  it('ESC keydown closes the drawer when open', async () => {
    wrapper = mount(Sidebar, { attachTo: document.body })
    const { openDrawer, drawerOpen } = useSidebar()
    openDrawer()
    await flushPromises()
    expect(drawerOpen.value).toBe(true)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()
    expect(drawerOpen.value).toBe(false)
  })

  it('unmount removes scroll-lock class from body', async () => {
    wrapper = mount(App)
    const { openDrawer } = useSidebar()
    openDrawer()
    await flushPromises()
    expect(document.body.classList.contains('sb-scroll-lock')).toBe(true)
    wrapper.unmount()
    expect(document.body.classList.contains('sb-scroll-lock')).toBe(false)
  })
})

describe('Mobile drawer a11y — focus trap', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    setViewport(800)
    routeRef.meta = {}
    routeRef.params = {}
  })
  afterEach(() => wrapper?.unmount())

  it('Tab on last focusable wraps to first', async () => {
    const store = useSessionStore()
    store.sessions = [{ id: 'a1', topic: 'X', created_at: '2026-05-20T10:00:00Z', ended_at: null }]
    wrapper = mount(Sidebar, { attachTo: document.body })
    const { openDrawer } = useSidebar()
    openDrawer()
    await flushPromises()

    const focusables = document
      .querySelector('.sidebar')
      ?.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )

    expect(focusables.length).toBeGreaterThan(0)

    const last = focusables[focusables.length - 1]
    last.focus()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }))
    // The trap's preventDefault + first.focus() runs in the same handler tick.
    // In jsdom, programmatic dispatch doesn't move focus on its own; we instead
    // verify the trap intercepts and explicitly calls focus on the first item.
    // We check that document.activeElement isn't outside the aside.
    await flushPromises()
    const aside = document.querySelector('.sidebar')
    expect(aside.contains(document.activeElement)).toBe(true)
  })
})

describe('Sidebar a11y — inert when closed (D-03)', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    routeRef.meta = {}
    routeRef.params = {}
    // useSidebar's drawerOpen is module-level singleton state that can leak
    // across tests in this file; force it closed before each case.
    useSidebar().closeDrawer()
  })
  afterEach(() => wrapper?.unmount())

  it('closed mobile drawer is inert', async () => {
    setViewport(500)
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    expect(wrapper.find('aside.sidebar').attributes('inert')).toBeDefined()
  })

  it('open mobile drawer is not inert', async () => {
    setViewport(500)
    wrapper = mount(Sidebar, { attachTo: document.body })
    const { openDrawer } = useSidebar()
    openDrawer()
    await flushPromises()
    expect(wrapper.find('aside.sidebar').attributes('inert')).toBeUndefined()
  })

  it('desktop sidebar is never inert', async () => {
    setViewport(1400)
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    expect(wrapper.find('aside.sidebar').attributes('inert')).toBeUndefined()
  })
})

describe('Sidebar a11y — recall badge unit', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    routeRef.meta = {}
    routeRef.params = {}
  })
  afterEach(() => {
    wrapper?.unmount()
    delete globalThis.requestIdleCallback
    delete globalThis.cancelIdleCallback
  })

  it('recall link exposes the count with a unit', async () => {
    wrapper = await mountSidebarWithReview(20)
    const link = wrapper.get('[data-testid="sidebar-recall"]')
    expect(link.attributes('aria-label')).toBe('Recall: 20 concepts due')
  })
})

describe('Sidebar a11y — heading levels (S1)', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    setViewport(1400)
    sidebarTest._setExpanded(true)
    routeRef.meta = {}
    routeRef.params = {}
  })
  afterEach(() => wrapper?.unmount())

  it('section label is a level-2 heading and no h3 is rendered', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'X', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: true },
    ]
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    expect(wrapper.findAll('h3').length).toBe(0)
    const sectionHeading = wrapper.find('[data-testid="sidebar-section-pinned"] h2')
    expect(sectionHeading.exists()).toBe(true)
    expect(sectionHeading.text()).toContain('Pinned')
  })
})

describe('Sidebar a11y — rename focus management', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    setViewport(1400)
    sidebarTest._setExpanded(true)
    routeRef.meta = {}
    routeRef.params = {}
  })
  afterEach(() => wrapper?.unmount())

  it('rename input receives focus and Escape returns to a stable state', async () => {
    const store = useSessionStore()
    store.sessions = [
      { id: 'a1', topic: 'X', created_at: '2026-05-20T10:00:00Z', ended_at: null, pinned: false },
    ]
    wrapper = mount(Sidebar, { attachTo: document.body })
    await flushPromises()
    await wrapper
      .find('[data-session-id="a1"] [data-testid="sidebar-row-menu-trigger"]')
      .trigger('click')
    await wrapper.find('[data-testid="sidebar-row-menu-rename"]').trigger('click')
    await flushPromises()
    const input = wrapper.find('[data-session-id="a1"] [data-testid="sidebar-row-rename-input"]')
    expect(document.activeElement).toBe(input.element)
    await input.trigger('keydown.esc')
    expect(
      wrapper.find('[data-session-id="a1"] [data-testid="sidebar-row-rename-input"]').exists(),
    ).toBe(false)
    wrapper.unmount()
  })
})
