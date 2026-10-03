import { describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { getRenderer, whenRendererReady } from '../lib/markdownRenderer.js'
import MarkdownContent from '../components/chat/MarkdownContent.vue'

// P1: KaTeX is dynamic-imported on first sight of math, so a math assertion
// waits for the plugin to land and the component to re-render.
async function settle() {
  await whenRendererReady()
  await flushPromises()
}

describe('MarkdownContent', () => {
  it('renders bold and italics', () => {
    const w = mount(MarkdownContent, { props: { text: '**bold** and *italic*' } })
    expect(w.html()).toContain('<strong>bold</strong>')
    expect(w.html()).toContain('<em>italic</em>')
  })

  it('renders fenced code with language class', () => {
    const w = mount(MarkdownContent, {
      props: { text: '```python\ndef foo():\n    pass\n```' },
    })

    expect(w.html()).toMatch(/<code class="language-python[^"]*"/)
  })

  it('renders inline math through KaTeX', async () => {
    const w = mount(MarkdownContent, { props: { text: 'cost $O(n)$ done' } })
    await settle()
    expect(w.html()).toContain('class="katex"')
  })

  it('renders display math through KaTeX', async () => {
    const w = mount(MarkdownContent, { props: { text: '$$\\int_0^1 x dx$$' } })
    await settle()
    expect(w.html()).toContain('class="katex-display"')
  })

  it('renders tables', () => {
    const w = mount(MarkdownContent, {
      props: { text: '| a | b |\n|---|---|\n| 1 | 2 |' },
    })

    expect(w.html()).toContain('<table')
  })

  // D-13: the scroll wrapper is emitted by the renderer, so it has to survive
  // DOMPurify (a div with a class attribute is in the default allowlist).
  it('wraps a rendered table in .md-table-wrap', () => {
    const w = mount(MarkdownContent, {
      props: { text: '| a | b |\n|---|---|\n| 1 | 2 |' },
    })

    expect(w.find('.md-table-wrap > table').exists()).toBe(true)
    expect(w.findAll('table')).toHaveLength(1)
  })

  it('sanitizes raw script tags via DOMPurify', () => {
    const w = mount(MarkdownContent, { props: { text: '<script>x=1</script>hello' } })
    expect(w.html()).not.toContain('<script>')
  })

  it('streaming mode: holds back unclosed math as deferred monospace', () => {
    const w = mount(MarkdownContent, {
      props: { text: 'cost is $O(log ', streaming: true },
    })

    expect(w.html()).toContain('cost is')
    expect(w.html()).toContain('class="deferred"')
    expect(w.html()).toContain('$O(log')
  })

  it('streaming mode: full render once math closes', async () => {
    const w = mount(MarkdownContent, {
      props: { text: 'cost is $O(n)$', streaming: true },
    })

    await settle()
    expect(w.html()).toContain('class="katex"')
    expect(w.html()).not.toContain('class="deferred"')
  })

  it('non-streaming mode: re-renders any open region as literal (defensive)', () => {
    const w = mount(MarkdownContent, {
      props: { text: 'cost is $O(log ', streaming: false },
    })

    // Should render the dollar literally rather than throw.
    expect(w.html()).toContain('$O(log')
  })

  it('renders empty text without throwing', () => {
    const w = mount(MarkdownContent, { props: { text: '' } })
    expect(w.exists()).toBe(true)
  })

  // F-15: the component drives the incremental renderer with a per-instance
  // cache. Two things must hold: the streamed output is byte-identical to a
  // plain full render at every frame, and the renderer sees far fewer
  // characters than a whole-prefix re-render would hand it.
  describe('F-15 incremental streaming render', () => {
    // Deliberately list-bearing: lists are the case the boundary rule has to
    // refuse. No $ and no fence, so the lazy assets stay out of the comparison.
    const FULL = [
      '# Report',
      'Intro paragraph that runs on for a while so the chunks land mid-word.',
      '- one\n- two\n- three',
      'A settled paragraph between the two lists.',
      '1. first\n\n2. second\n\n3. third',
      '| h | v |\n|---|---|\n| a | b |',
      '> a quoted aside',
      // Separate paragraphs, not one giant one: the cached head can only
      // advance to a settled block boundary, so a single 4 KB paragraph would
      // measure nothing but the fallback path.
      Array.from({ length: 16 }, (_, i) =>
        `Filler paragraph ${i} of ordinary prose that keeps the buffer growing so the cached head has settled blocks to hold onto. `.repeat(
          2,
        ),
      ).join('\n\n'),
      'End of report.',
    ].join('\n\n')

    const FRAME_ENDS = (() => {
      const ends = []

      for (let end = 40; ; end = Math.min(end + 40, FULL.length)) {
        ends.push(end)

        if (end >= FULL.length) break
      }

      return ends
    })()

    // ~100 frames x 3 mounts each: comfortably under 5 s locally, but the CI
    // runner with v8 coverage on has tripped the default. Budget, not a hint.
    it(
      'is byte-identical to a fresh render at every frame and once settled',
      { timeout: 30_000 },
      async () => {
        const w = mount(MarkdownContent, { props: { text: '', streaming: true } })
        const mismatches = []
        let coldMismatches = 0
        let compared = 0

        for (const end of FRAME_ENDS) {
          const text = FULL.slice(0, end)
          // `await` per frame: Vue batches prop writes, and the cache has to see
          // every frame the way a real stream delivers them.
          await w.setProps({ text })

          // A frame with nothing held back renders the whole buffer, so the
          // streamed HTML must equal the non-streaming render of the same text.
          if (!w.find('.deferred').exists()) {
            const plain = mount(MarkdownContent, { props: { text, streaming: false } })

            if (w.find('.md-rendered').html() !== plain.find('.md-rendered').html()) {
              mismatches.push(end)
            }

            plain.unmount()
            compared += 1
          }

          // And a long-lived cache must not drift from a cold one.
          const fresh = mount(MarkdownContent, { props: { text, streaming: true } })

          if (w.find('.md-rendered').html() !== fresh.find('.md-rendered').html()) {
            coldMismatches += 1
          }

          fresh.unmount()
        }

        expect(mismatches).toEqual([])
        expect(coldMismatches).toBe(0)
        // Guard against the splitter deferring on nearly every frame and making
        // the comparison above vacuous.
        expect(compared).toBeGreaterThan(90)

        await w.setProps({ streaming: false })
        const settled = mount(MarkdownContent, { props: { text: FULL, streaming: false } })
        expect(w.find('.md-rendered').html()).toBe(settled.find('.md-rendered').html())
        settled.unmount()
        w.unmount()
      },
    )

    it('hands the renderer far fewer characters than a whole-prefix re-render', async () => {
      const md = getRenderer()
      const real = md.render.bind(md)
      let chars = 0
      md.render = (src) => {
        chars += src.length

        return real(src)
      }

      let naive = 0
      let incremental = 0

      try {
        for (const streaming of [false, true]) {
          // streaming=false re-renders the whole prefix every frame, which is
          // exactly the pre-F-15 behaviour of the streaming branch.
          const w = mount(MarkdownContent, { props: { text: '', streaming } })
          let total = 0

          for (const end of FRAME_ENDS) {
            chars = 0
            await w.setProps({ text: FULL.slice(0, end) })
            total += chars
          }

          w.unmount()

          if (streaming) incremental = total
          else naive = total
        }
      } finally {
        md.render = real
      }

      // Whole-prefix re-rendering is quadratic in the buffer length; the cached
      // head makes the streaming path close to linear.
      // Measured 2026-09-20 on a 4092-char fixture in 40-char chunks (103
      // frames): naive 214212 chars into markdown-it, incremental 15065 (14.2x).
      expect(FULL.length).toBeGreaterThan(4000)
      expect(naive).toBeGreaterThan(150000)
      expect(incremental).toBeLessThan(naive / 8)
    })
  })
})
