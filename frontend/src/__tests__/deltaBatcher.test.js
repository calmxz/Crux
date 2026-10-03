import { describe, it, expect, vi } from 'vitest'
import { createDeltaBatcher } from '@/lib/deltaBatcher.js'

describe('createDeltaBatcher', () => {
  it('coalesces pushes into one apply per frame', () => {
    const frames = []
    const raf = (cb) => frames.push(cb)
    const apply = vi.fn()
    const b = createDeltaBatcher(apply, raf)

    b.push('a')
    b.push('b')
    b.push('c')
    expect(apply).not.toHaveBeenCalled()
    expect(frames).toHaveLength(1)

    frames[0]()
    expect(apply).toHaveBeenCalledTimes(1)
    expect(apply).toHaveBeenCalledWith('abc')
  })

  it('schedules a new frame after a flush cycle', () => {
    const frames = []
    const b = createDeltaBatcher(vi.fn(), (cb) => frames.push(cb))
    b.push('a')
    frames[0]()
    b.push('b')
    expect(frames).toHaveLength(2)
  })

  it('flush applies pending text immediately and is idempotent', () => {
    const frames = []
    const apply = vi.fn()
    const b = createDeltaBatcher(apply, (cb) => frames.push(cb))
    b.push('a')
    b.flush()
    expect(apply).toHaveBeenCalledWith('a')
    b.flush()
    frames.forEach((cb) => cb())
    expect(apply).toHaveBeenCalledTimes(1)
  })

  it('falls back to immediate apply when rAF is unavailable', () => {
    // jsdom (this project's vitest environment) defines requestAnimationFrame
    // globally, so the `raf` default-parameter would otherwise resolve to a
    // real function here. Remove it for this test so the fallback branch
    // (mirrors non-browser/SSR contexts where it is genuinely undefined) is
    // what's actually exercised. Batcher implementation is unchanged.
    const original = globalThis.requestAnimationFrame
    delete globalThis.requestAnimationFrame

    try {
      const apply = vi.fn()
      const b = createDeltaBatcher(apply, undefined)
      b.push('x')
      expect(apply).toHaveBeenCalledWith('x')
    } finally {
      globalThis.requestAnimationFrame = original
    }
  })
})
