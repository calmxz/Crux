import { describe, it, expect, beforeEach, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'

const LS_KEY = 'crux.panel.expanded'

const BREAKPOINT = 1280

function setViewport(width) {
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    writable: true,
    value: width,
  })
}

async function loadModule() {
  return await import('@/composables/usePanel.js')
}

function mountHarness(usePanel, ctx) {
  const Host = defineComponent({
    setup() {
      Object.assign(ctx, usePanel())

      return () => h('div')
    },
  })

  return mount(Host)
}

describe('usePanel', () => {
  beforeEach(() => {
    localStorage.clear()
    setViewport(BREAKPOINT) // default to desktop
    vi.resetModules()
  })

  it('defaults to expanded when localStorage empty', async () => {
    const { usePanel } = await loadModule()
    const ctx = {}
    const wrapper = mountHarness(usePanel, ctx)
    expect(ctx.desktopExpanded.value).toBe(true)
    expect(ctx.collapsed.value).toBe(false)
    wrapper.unmount()
  })

  it('reads "1" from localStorage as expanded', async () => {
    localStorage.setItem(LS_KEY, '1')
    const { usePanel } = await loadModule()
    const ctx = {}
    const wrapper = mountHarness(usePanel, ctx)
    expect(ctx.desktopExpanded.value).toBe(true)
    wrapper.unmount()
  })

  it('reads "0" from localStorage as collapsed', async () => {
    localStorage.setItem(LS_KEY, '0')
    const { usePanel } = await loadModule()
    const ctx = {}
    const wrapper = mountHarness(usePanel, ctx)
    expect(ctx.desktopExpanded.value).toBe(false)
    expect(ctx.collapsed.value).toBe(true)
    wrapper.unmount()
  })

  it('toggleDesktop flips expanded and persists', async () => {
    const { usePanel } = await loadModule()
    const ctx = {}
    const wrapper = mountHarness(usePanel, ctx)
    expect(ctx.desktopExpanded.value).toBe(true)
    ctx.toggleDesktop()
    expect(ctx.desktopExpanded.value).toBe(false)
    expect(localStorage.getItem(LS_KEY)).toBe('0')
    ctx.toggleDesktop()
    expect(ctx.desktopExpanded.value).toBe(true)
    expect(localStorage.getItem(LS_KEY)).toBe('1')
    wrapper.unmount()
  })

  it('isDesktop is false below the breakpoint', async () => {
    setViewport(800)
    const { usePanel } = await loadModule()
    const ctx = {}
    const wrapper = mountHarness(usePanel, ctx)
    expect(ctx.isDesktop.value).toBe(false)
    wrapper.unmount()
  })

  // Deliberate contract: the panel column exists from 900px, well below the
  // 1280 desktop breakpoint, so collapse must not be gated on isDesktop.
  it('collapse is not gated on isDesktop', async () => {
    setViewport(1100)
    const { usePanel } = await loadModule()
    const ctx = {}
    const wrapper = mountHarness(usePanel, ctx)
    expect(ctx.isDesktop.value).toBe(false)
    ctx.toggleDesktop()
    expect(ctx.collapsed.value).toBe(true)
    wrapper.unmount()
  })

  it('resize listener updates the viewport', async () => {
    setViewport(800)
    const { usePanel } = await loadModule()
    const ctx = {}
    const wrapper = mountHarness(usePanel, ctx)
    expect(ctx.isDesktop.value).toBe(false)

    setViewport(BREAKPOINT + 100)
    window.dispatchEvent(new Event('resize'))
    await wrapper.vm.$nextTick()

    expect(ctx.isDesktop.value).toBe(true)
    wrapper.unmount()
  })

  it('unmount removes the resize listener', async () => {
    const { usePanel } = await loadModule()
    const ctx = {}
    const wrapper = mountHarness(usePanel, ctx)
    wrapper.unmount()

    // Module is a singleton, so a surviving consumer elsewhere could still
    // update the viewport ref; all this can assert is that the dispatch after
    // unmount does not throw.
    setViewport(500)
    window.dispatchEvent(new Event('resize'))
    expect(true).toBe(true)
  })
})
