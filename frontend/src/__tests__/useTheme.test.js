import { describe, it, expect, beforeEach, vi } from 'vitest'

const STORAGE_KEY = 'crux:theme:v1'

describe('useTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    vi.resetModules()
  })

  it('defaults to auto when nothing stored', async () => {
    const { useTheme } = await import('@/composables/useTheme.js')
    const { override } = useTheme()
    expect(override.value).toBe('auto')
  })

  it('loads valid stored value', async () => {
    localStorage.setItem(STORAGE_KEY, 'dark')
    const { useTheme } = await import('@/composables/useTheme.js')
    const { override } = useTheme()
    expect(override.value).toBe('dark')
  })

  it('rejects invalid stored value', async () => {
    localStorage.setItem(STORAGE_KEY, 'pink')
    const { useTheme } = await import('@/composables/useTheme.js')
    const { override } = useTheme()
    expect(override.value).toBe('auto')
  })

  it('setTheme persists and applies data-theme attribute', async () => {
    const { useTheme } = await import('@/composables/useTheme.js')
    const { setTheme, resolved } = useTheme()
    setTheme('light')
    expect(localStorage.getItem(STORAGE_KEY)).toBe('light')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    expect(resolved.value).toBe('light')
  })

  it('setTheme ignores invalid values', async () => {
    const { useTheme } = await import('@/composables/useTheme.js')
    const { setTheme, override } = useTheme()
    setTheme('rainbow')
    expect(override.value).toBe('auto')
  })

  it('setTheme to auto keeps data-theme in sync with the resolved value', async () => {
    // Auto must NOT strip the attribute: PrimeVue overlays (ConfirmDialog,
    // teleported to body) only go dark via the [data-theme="dark"] selector.
    // Removing it desyncs the dialog from the app tokens. matchMedia is
    // unstubbed here so the system resolves light.
    const { useTheme } = await import('@/composables/useTheme.js')
    const { setTheme } = useTheme()
    setTheme('dark')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    setTheme('auto')
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('auto + system dark sets data-theme="dark" so PrimeVue overlays adapt', async () => {
    const listeners = {}
    window.matchMedia = vi.fn(() => ({
      matches: true,
      addEventListener: (ev, cb) => {
        listeners[ev] = cb
      },
      removeEventListener: vi.fn(),
    }))
    const { useTheme } = await import('@/composables/useTheme.js')
    const { init } = useTheme()
    init()
    // override stays 'auto' but the attribute must be present and "dark"
    // so darkModeSelector '[data-theme="dark"]' matches the teleported dialog.
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')

    // Tracks live system changes too.
    listeners.change?.({ matches: false })
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('toggle flips dark<->light', async () => {
    const { useTheme } = await import('@/composables/useTheme.js')
    const { setTheme, toggle, resolved } = useTheme()
    setTheme('dark')
    toggle()
    expect(resolved.value).toBe('light')
    toggle()
    expect(resolved.value).toBe('dark')
  })

  it('isDark reflects resolved', async () => {
    const { useTheme } = await import('@/composables/useTheme.js')
    const { setTheme, isDark } = useTheme()
    setTheme('dark')
    expect(isDark.value).toBe(true)
    setTheme('light')
    expect(isDark.value).toBe(false)
  })

  it('init reads matchMedia and applies attribute', async () => {
    const listeners = {}
    window.matchMedia = vi.fn(() => ({
      matches: true,
      addEventListener: (ev, cb) => {
        listeners[ev] = cb
      },
      removeEventListener: vi.fn(),
    }))
    const { useTheme } = await import('@/composables/useTheme.js')
    const { init, resolved } = useTheme()
    init()
    expect(resolved.value).toBe('dark')

    listeners.change?.({ matches: false })
    expect(resolved.value).toBe('light')
  })

  it('init falls back to addListener when addEventListener missing', async () => {
    const addListener = vi.fn()
    window.matchMedia = vi.fn(() => ({
      matches: false,
      addListener,
    }))
    const { useTheme } = await import('@/composables/useTheme.js')
    const { init } = useTheme()
    init()
    expect(addListener).toHaveBeenCalled()
  })

  // F-20: init() has no removal path today, so it must not attach a second
  // matchMedia listener if called again (e.g. a second component mount).
  it('calling init() twice only adds one listener', async () => {
    const mq = {
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }

    window.matchMedia = vi.fn(() => mq)
    const { useTheme } = await import('@/composables/useTheme.js')
    const { init } = useTheme()
    init()
    init()
    expect(window.matchMedia).toHaveBeenCalledTimes(1)
    expect(mq.addEventListener).toHaveBeenCalledTimes(1)
  })

  // F-20: dispose() removes the exact listener init() added (module-scope
  // handler, not a fresh closure) and clears mediaQuery so init() can re-arm.
  it('dispose() removes the listener added by init() and allows re-init', async () => {
    const mq = {
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }

    window.matchMedia = vi.fn(() => mq)
    const { useTheme } = await import('@/composables/useTheme.js')
    const { init, dispose } = useTheme()
    init()
    dispose()
    expect(mq.removeEventListener.mock.calls[0][1]).toBe(mq.addEventListener.mock.calls[0][1])

    init()
    expect(window.matchMedia).toHaveBeenCalledTimes(2)
    expect(mq.addEventListener).toHaveBeenCalledTimes(2)
  })
})
