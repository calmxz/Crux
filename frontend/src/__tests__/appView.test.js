import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const showError = vi.fn()

vi.mock('@/composables/useToast.js', () => ({
  useToast: () => ({ showError, showWarn: vi.fn(), showSuccess: vi.fn() }),
}))

const routerPush = vi.fn()

vi.mock('vue-router', () => ({
  RouterLink: { template: '<a><slot /></a>', props: ['to'] },
  RouterView: { template: '<div />' },
  useRouter: () => ({ push: routerPush }),
  useRoute: () => ({ fullPath: '/', params: {}, meta: routeMeta }),
}))

// D-15: showShell reads route.meta.sidebar, so the chrome-less branch needs a
// mutable meta. An empty object keeps the shell branch (sidebar !== false).
let routeMeta = {}

vi.mock('primevue/toast', () => ({
  default: { template: '<div data-testid="toast" />' },
}))

vi.mock('@vercel/analytics/vue', () => ({
  Analytics: { template: '<div data-testid="vercel-analytics" />' },
}))

// Tests run outside a Vercel build, where the flag is off; force it on so the
// mount point is covered.
vi.mock('@/lib/analytics.js', () => ({
  analyticsEnabled: true,
  scrubAnalyticsEvent: (event) => event,
}))

import App from '@/App.vue'
import { reportApiError } from '@/services/errorBus.js'

describe('App.vue error listener', () => {
  let wrapper
  beforeEach(() => {
    setActivePinia(createPinia())
    showError.mockClear()
    routerPush.mockClear()
    wrapper = mount(App)
  })
  afterEach(() => wrapper.unmount())

  // F-51: raw backend detail strings (internal error codes, stack fragments)
  // must never reach the toast -- friendlyError() maps by status instead.
  it('shows a friendly toast for a generic API error, not the raw detail', async () => {
    reportApiError({ status: 500, body: { detail: 'raw_internal_code' } })
    await flushPromises()
    expect(showError).toHaveBeenCalledWith('Something went wrong on our side. Try again shortly.')
  })

  it('maps a 503 to the tutor-unavailable message regardless of err.message', async () => {
    reportApiError({ status: 503, message: 'gateway' })
    await flushPromises()
    expect(showError).toHaveBeenCalledWith(
      'The tutor is temporarily unavailable. Try again in a moment.',
    )
  })

  it('maps a bare 500 (no body, no message) to the same friendly copy', async () => {
    reportApiError({ status: 500 })
    await flushPromises()
    expect(showError).toHaveBeenCalledWith('Something went wrong on our side. Try again shortly.')
  })

  it('skips 429 (daily-cap has dedicated UI)', async () => {
    reportApiError({ status: 429, body: { detail: 'cap' } })
    await flushPromises()
    expect(showError).not.toHaveBeenCalled()
  })

  it('skips 404 (inline-handled by consumers)', async () => {
    reportApiError({ status: 404, body: { detail: 'gone' } })
    await flushPromises()
    expect(showError).not.toHaveBeenCalled()
  })

  it('unmount removes the listener', async () => {
    wrapper.unmount()
    reportApiError({ status: 500, body: { detail: 'boom' } })
    await flushPromises()
    expect(showError).not.toHaveBeenCalled()
  })

  it('maps a non-string body.detail to friendly copy instead of stringifying it', async () => {
    reportApiError({ status: 500, body: { detail: { code: 'x' } } })
    await flushPromises()
    expect(showError).toHaveBeenCalledWith('Something went wrong on our side. Try again shortly.')
  })
})

describe('shell keyboard shortcuts', () => {
  let wrapper
  let sidebarTest
  let panelTest

  beforeEach(async () => {
    setActivePinia(createPinia())
    localStorage.clear()
    sidebarTest = (await import('@/composables/useSidebar.js')).__test__
    panelTest = (await import('@/composables/usePanel.js')).__test__
    // jsdom reports innerWidth 1024 and both composables snapshot it at module
    // load, so force the desktop branch and a known starting state.
    sidebarTest._setViewport(1280)
    sidebarTest._setExpanded(true)
    panelTest._setViewport(1280)
    panelTest._setExpanded(true)
    wrapper = mount(App)
  })
  afterEach(() => wrapper.unmount())

  const press = (key, target = window, init = {}) => {
    const e = new KeyboardEvent('keydown', { key, ctrlKey: true, bubbles: true, ...init })
    const spy = vi.spyOn(e, 'preventDefault')
    target.dispatchEvent(e)

    return spy
  }

  it('Ctrl+B toggles the sidebar and prevents the default', () => {
    const spy = press('b')
    expect(localStorage.getItem('crux.sidebar.expanded')).toBe('0')
    expect(spy).toHaveBeenCalled()
  })

  it('Ctrl+. toggles the profile panel and prevents the default', () => {
    const spy = press('.')
    expect(localStorage.getItem('crux.panel.expanded')).toBe('0')
    expect(spy).toHaveBeenCalled()
  })

  it('ignores Ctrl+Shift+B (browser bookmarks bar)', () => {
    const spy = press('b', window, { shiftKey: true })
    expect(localStorage.getItem('crux.sidebar.expanded')).toBe(null)
    expect(spy).not.toHaveBeenCalled()
  })

  it('ignores both shortcuts while the target is a text field', () => {
    const input = document.createElement('input')
    document.body.appendChild(input)
    press('b', input)
    press('.', input)
    expect(localStorage.getItem('crux.sidebar.expanded')).toBe(null)
    expect(localStorage.getItem('crux.panel.expanded')).toBe(null)
    input.remove()
  })

  it('ignores both shortcuts while a PrimeVue overlay is open', () => {
    const overlay = document.createElement('div')
    overlay.className = 'p-dialog'
    document.body.appendChild(overlay)
    press('b')
    press('.')
    expect(localStorage.getItem('crux.sidebar.expanded')).toBe(null)
    expect(localStorage.getItem('crux.panel.expanded')).toBe(null)
    overlay.remove()
  })

  it('unbinds the listener on unmount', () => {
    wrapper.unmount()
    press('b')
    expect(localStorage.getItem('crux.sidebar.expanded')).toBe(null)
  })
})

/* global process */
// Source-text assertions: what is under test is the CSS the SFC ships, and
// jsdom neither applies stylesheets nor runs animations, so mounting cannot
// see it. Same file-read approach as tokenContrast.test.js.
const readSrc = (p) => readFileSync(resolve(process.cwd(), p), 'utf8')

describe('P2: sidebar collapse is not a layout animation', () => {
  const appSrc = readSrc('src/App.vue')
  const sidebarSrc = readSrc('src/components/sidebar/Sidebar.vue')

  // Animating grid-template-columns relayouts the whole shell every frame
  // (ruled ground + session list). The column must snap.
  it('App.vue never transitions grid-template-columns', () => {
    const transitions = appSrc.match(/transition:[^;}]*/g) || []

    for (const decl of transitions) {
      expect(decl).not.toMatch(/grid-template-columns/)
      expect(decl).not.toMatch(/\ball\b/)
    }
  })

  it('App.vue .shell declares no transition at all', () => {
    const shellRule = appSrc.slice(appSrc.indexOf('.shell {'))
    const body = shellRule.slice(0, shellRule.indexOf('}'))
    expect(body).toContain('grid-template-columns')
    expect(body).not.toContain('transition')
  })

  // The softening moved to the sidebar's own ink: its contents fade in
  // whenever the mode flips, per DESIGN.md ("motion is opacity ... nothing
  // slides").
  it('Sidebar.vue fades its contents in on a mode change, in opacity only', () => {
    expect(sidebarSrc).toMatch(/@keyframes sb-mode-fade\s*\{[^}]*opacity:\s*0/)
    expect(sidebarSrc).toMatch(/animation:\s*sb-mode-fade var\(--motion-fast\)/)
    expect(sidebarSrc).not.toMatch(/will-change/)
  })

  it('Sidebar.vue disables the mode fade under reduced motion', () => {
    const rm = sidebarSrc.slice(sidebarSrc.lastIndexOf('@media (prefers-reduced-motion: reduce)'))
    expect(rm).toMatch(/sb-mode-fade|sidebar--expanded|sidebar--collapsed/)
    expect(rm).toMatch(/animation:\s*none/)
  })
})

// D-15: the router's afterEach moves focus to #main-content. Both App branches
// must carry that target, or chrome-less routes (login, legal, 404) silently
// keep focus wherever the previous page left it.
describe('D-15: both App branches carry a focusable #main-content', () => {
  let wrapper

  beforeEach(() => {
    setActivePinia(createPinia())
    routeMeta = {}
  })
  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    routeMeta = {}
  })

  it('the shell branch focus target is the main landmark', async () => {
    wrapper = mount(App, { attachTo: document.body })
    const el = document.getElementById('main-content')
    expect(el).not.toBeNull()
    expect(el.tagName).toBe('MAIN')
    expect(el.getAttribute('tabindex')).toBe('-1')
    el.focus()
    expect(document.activeElement).toBe(el)
  })

  it('the chrome-less branch root is focusable too', async () => {
    routeMeta = { sidebar: false }
    wrapper = mount(App, { attachTo: document.body })
    expect(wrapper.find('.shell').exists()).toBe(false)
    const el = document.getElementById('main-content')
    expect(el).not.toBeNull()
    expect(el.getAttribute('tabindex')).toBe('-1')
    el.focus()
    expect(document.activeElement).toBe(el)
  })
})

// Vercel Web Analytics mounts once at the app root, outside the shell branch,
// so chrome-less routes (login, legal, 404) report page views too.
describe('Vercel Web Analytics', () => {
  let wrapper

  beforeEach(() => {
    setActivePinia(createPinia())
    routeMeta = {}
  })
  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    routeMeta = {}
  })

  it('mounts on shell routes', () => {
    wrapper = mount(App)
    expect(wrapper.findAll('[data-testid="vercel-analytics"]')).toHaveLength(1)
  })

  it('mounts on chrome-less routes', () => {
    routeMeta = { sidebar: false }
    wrapper = mount(App)
    expect(wrapper.findAll('[data-testid="vercel-analytics"]')).toHaveLength(1)
  })
})
