// Run a callback when the browser is idle, off the boot critical path.
// Falls back to a short setTimeout where requestIdleCallback is missing
// (older Safari, jsdom). Returns a cancel function.
export function runWhenIdle(cb, { timeout = 1500 } = {}) {
  if (typeof globalThis.requestIdleCallback === 'function') {
    const id = globalThis.requestIdleCallback(cb, { timeout })

    return () => globalThis.cancelIdleCallback(id)
  }

  const id = setTimeout(cb, 200)

  return () => clearTimeout(id)
}
