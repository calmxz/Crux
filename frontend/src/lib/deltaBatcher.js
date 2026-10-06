// P4.3: coalesce per-token SSE deltas into one reactive mutation per
// animation frame. Vue re-renders (and the markdown re-parse behind
// MarkdownContent) then run per frame instead of per token. Falls back to
// immediate apply when requestAnimationFrame is unavailable (tests, SSR).

export function createDeltaBatcher(apply, raf = globalThis.requestAnimationFrame) {
  let pending = ''
  let scheduled = false

  function flush() {
    scheduled = false

    if (!pending) return
    const text = pending
    pending = ''
    apply(text)
  }

  return {
    push(text) {
      if (typeof raf !== 'function') {
        apply(text)

        return
      }

      pending += text

      if (!scheduled) {
        scheduled = true
        raf(flush)
      }
    },
    flush,
  }
}
