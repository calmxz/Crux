import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { renderMarkdown, whenRendererReady } from '../lib/markdownRenderer.js'
import MarkdownContent from '../components/chat/MarkdownContent.vue'

describe('code-block chrome', () => {
  it('wraps fenced code with a header bar containing language tag and copy button', () => {
    const html = renderMarkdown('```python\nprint("hi")\n```')
    expect(html).toContain('class="code-block-header"')
    expect(html).toMatch(/class="code-block-lang"[^>]*>python/)
    expect(html).toContain('data-copy-button')
  })

  it('shows "plain" when no language is given', () => {
    const html = renderMarkdown('```\nx = 1\n```')
    expect(html).toMatch(/class="code-block-lang"[^>]*>plain/)
  })

  // R2: the copy button measured 49x28 on coarse pointer; it sits directly
  // above the code with no room to grow in layout, so it gets the invisible
  // hit-area extension rather than coarse-2x.
  it('R2: copy button carries hit-44 for a coarse-pointer hit area', () => {
    const html = renderMarkdown('```python\nprint("hi")\n```')
    expect(html).toMatch(/class="code-block-copy hit-44"/)
  })

  // P1: highlight.js is loaded on demand by the first fence, so the highlighted
  // markup lands on the render after the plugin arrives.
  it('preserves highlight.js spans inside the code block', async () => {
    renderMarkdown('```python\ndef foo(): pass\n```')
    await whenRendererReady()
    const html = renderMarkdown('```python\ndef foo(): pass\n```')
    expect(html).toContain('hljs-keyword')
  })
})

// F-03: the copy button's handler is delegated from the component root
// because v-html content cannot carry listeners.
describe('code-block copy button (F-03)', () => {
  function mountWithClipboard(writeText) {
    Object.defineProperty(globalThis.navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    })

    return mount(MarkdownContent, {
      props: { text: '```python\nprint("hi")\n```' },
    })
  }

  it('click copies the code text and flips the label to copied', async () => {
    const writeText = vi.fn().mockResolvedValue()
    const w = mountWithClipboard(writeText)
    await w.find('[data-copy-button]').trigger('click')
    await flushPromises()
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('print("hi")'))
    expect(w.find('[data-copy-button]').element.textContent).toBe('copied')
  })

  it('a rejected clipboard write leaves the label unchanged', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denied'))
    const w = mountWithClipboard(writeText)
    await w.find('[data-copy-button]').trigger('click')
    await flushPromises()
    expect(w.find('[data-copy-button]').element.textContent).toBe('copy')
  })

  it('clicks outside the copy button do not touch the clipboard', async () => {
    const writeText = vi.fn()
    const w = mountWithClipboard(writeText)
    await w.find('code').trigger('click')
    await flushPromises()
    expect(writeText).not.toHaveBeenCalled()
  })
})
