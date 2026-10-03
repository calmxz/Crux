import { describe, it, expect, vi, afterEach } from 'vitest'
import { runWhenIdle } from '@/utils/idle.js'

describe('runWhenIdle', () => {
  afterEach(() => {
    delete globalThis.requestIdleCallback
    delete globalThis.cancelIdleCallback
    vi.useRealTimers()
  })

  it('uses requestIdleCallback when available', () => {
    const cb = vi.fn()
    globalThis.requestIdleCallback = vi.fn((fn) => {
      fn()

      return 7
    })
    globalThis.cancelIdleCallback = vi.fn()
    runWhenIdle(cb)
    expect(cb).toHaveBeenCalled()
  })

  it('cancel prevents the idle callback', () => {
    globalThis.requestIdleCallback = vi.fn(() => 7)
    globalThis.cancelIdleCallback = vi.fn()
    const cancel = runWhenIdle(vi.fn())
    cancel()
    expect(globalThis.cancelIdleCallback).toHaveBeenCalledWith(7)
  })

  it('falls back to setTimeout when requestIdleCallback is missing', () => {
    vi.useFakeTimers()
    const cb = vi.fn()
    runWhenIdle(cb)
    expect(cb).not.toHaveBeenCalled()
    vi.advanceTimersByTime(200)
    expect(cb).toHaveBeenCalled()
  })

  it('cancel clears the fallback timer', () => {
    vi.useFakeTimers()
    const cb = vi.fn()
    const cancel = runWhenIdle(cb)
    cancel()
    vi.runAllTimers()
    expect(cb).not.toHaveBeenCalled()
  })
})
