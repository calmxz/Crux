import { describe, it, expect, beforeAll } from 'vitest'
import {
  createRenderCache,
  getRenderer,
  renderMarkdown,
  renderMarkdownIncremental,
  whenRendererReady,
} from '../lib/markdownRenderer.js'
import { createSplitState, splitSafePrefixIncremental } from '../lib/markdownStreamBuffer.js'

// F-15: the incremental renderer caches the HTML of the settled head of a
// streamed buffer. It is only allowed to exist if it is byte-identical to a
// full render at every frame, so these fixtures stream character-by-character
// and in realistic chunk sizes and compare the exact strings.

const FIXTURES = {
  prose: 'First paragraph with **bold**.\n\nSecond one, longer.\n\nThird and last.\n',
  headings: '# Title\n\nIntro line.\n\n## Sub\n\nBody text here.\n\n### Deep\n\nTail.\n',
  tightList: 'Intro.\n\n- one\n- two\n- three\n\nAfter the list.\n',
  looseList: 'Intro.\n\n- one\n\n- two\n\n- three\n\nAfter the list.\n',
  orderedList: 'Intro.\n\n1. one\n\n2. two\n\nAfter.\n',
  listContinuation: 'Intro.\n\n- one\n\n  continued in the item\n\nAfter.\n',
  indentedCode: 'Intro.\n\n    code one\n\n    code two\n\nAfter.\n',
  fenceWithBlankLine:
    'Intro.\n\n```python\ndef a():\n    pass\n\n\ndef b():\n    pass\n```\n\nAfter.\n',
  twoFences: '```js\nlet a = 1\n```\n\nmiddle\n\n```sql\nselect 1\n```\n\nend\n',
  // A 3-backtick line inside a 4-backtick fence is content, not a close. A
  // scanner that toggles on any 3+ run flips out of the block here and turns
  // the following blank line into a cut candidate inside the code.
  fenceInLongerFence: 'Intro.\n\n````\n```\n\nstill inside\n````\n\nAfter.\n',
  // Same trap across fence characters: ``` cannot close a ~~~ fence.
  backtickInsideTildeFence: 'Intro.\n\n~~~\n```\n\nstill inside\n~~~\n\nAfter.\n',
  table: 'Before.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\nAfter.\n',
  twoTables: '| a |\n|---|\n| 1 |\n\n| b |\n|---|\n| 2 |\n\nend\n',
  inlineMath: 'Cost is $O(n)$ here.\n\nAnd $x^2 + y^2$ there.\n\nDone.\n',
  displayMath: 'Before.\n\n$$\n\\int_0^1 x\\,dx\n$$\n\nAfter.\n',
  displayMathBlankInside: 'Before.\n\n$$\na = 1\n\nb = 2\n$$\n\nAfter.\n',
  blockquote: 'Intro.\n\n> quoted one\n\n> quoted two\n\nAfter.\n',
  refDefBefore: 'See [foo] and [bar].\n\n[foo]: /a\n[bar]: /b\n\nEnd.\n',
  refDefAfter: '[foo]: /a\n\nSee [foo] again.\n\nEnd.\n',
  hrAndInline: 'One.\n\n---\n\nTwo with `code` and a https://example.com link.\n\nThree.\n',
  mixed:
    '# Report\n\nIntro paragraph.\n\n- a\n- b\n\n```js\nconst x = 1\n```\n\n| h |\n|---|\n| v |\n\n$$\nE = mc^2\n$$\n\n> note\n\nEnd of report.\n',
}

function longProse() {
  const words = [
    'adaptive',
    'retrieval',
    'gradient',
    'threshold',
    'mastery',
    'inference',
    'sequence',
    'parameter',
    'boundary',
    'estimate',
  ]

  const paras = []
  let n = 0

  while (paras.join('\n\n').length < 4000) {
    const sentence = []

    for (let i = 0; i < 26; i += 1) {
      sentence.push(words[(n + i) % words.length])
      n += 1
    }

    paras.push(sentence.join(' ') + '.')
  }

  return paras.join('\n\n') + '\n'
}

/**
 * Streams `full` in `size`-char chunks and returns one entry per frame whose
 * incremental HTML is not byte-identical to a full render. Empty means parity.
 */
function parityMismatches(full, size) {
  const split = createSplitState()
  const cache = createRenderCache()
  const bad = []

  for (let end = size; ; end = Math.min(end + size, full.length)) {
    const text = full.slice(0, end)
    const { safe } = splitSafePrefixIncremental(text, split)
    const incremental = renderMarkdownIncremental(safe, cache)
    const expected = renderMarkdown(safe)

    if (incremental !== expected) bad.push({ end, safe, incremental, expected })

    if (end >= full.length) break
  }

  return bad
}

/**
 * Same as `parityMismatches` but without `splitSafePrefixIncremental` in front.
 * The splitter only knows 3-backtick fences, so it hides the longer-fence and
 * tilde-fence cases from the incremental renderer; parity is the renderer's own
 * contract on any prefix, so these fixtures are checked raw too.
 */
function rawParityMismatches(full, size) {
  const cache = createRenderCache()
  const bad = []

  for (let end = size; ; end = Math.min(end + size, full.length)) {
    const text = full.slice(0, end)
    const incremental = renderMarkdownIncremental(text, cache)
    const expected = renderMarkdown(text)

    if (incremental !== expected) bad.push({ end, text, incremental, expected })

    if (end >= full.length) break
  }

  return bad
}

beforeAll(async () => {
  // KaTeX and highlight.js are lazy; warm them so output is stable across
  // frames and the version-invalidation branch is not what we are measuring.
  renderMarkdown('$x$\n\n```js\nlet a = 1\n```\n')
  await whenRendererReady()
  renderMarkdown('$x$\n\n```js\nlet a = 1\n```\n')
  await whenRendererReady()
})

describe('renderMarkdownIncremental parity', () => {
  for (const [name, text] of Object.entries(FIXTURES)) {
    it(`${name}: byte-identical at 7-char chunks`, () => {
      expect(parityMismatches(text, 7)).toEqual([])
    })
    it(`${name}: byte-identical at 40-char chunks`, () => {
      expect(parityMismatches(text, 40)).toEqual([])
    })
  }

  for (const name of ['fenceInLongerFence', 'backtickInsideTildeFence']) {
    it(`${name}: byte-identical without the stream splitter at 7-char chunks`, () => {
      expect(rawParityMismatches(FIXTURES[name], 7)).toEqual([])
    })
    it(`${name}: byte-identical without the stream splitter at 40-char chunks`, () => {
      expect(rawParityMismatches(FIXTURES[name], 40)).toEqual([])
    })
  }

  // The boundary may take the paragraph close after "Intro."; what it must not
  // do is advance onto the blank line that sits INSIDE the fence.
  it('does not cut on a blank line inside a longer or differently-charred fence', () => {
    const longer = createRenderCache()
    renderMarkdownIncremental('Intro.\n\n````\n```\n\nstill inside', longer)
    expect(longer.prefixText).toBe('Intro.\n\n')

    const tilde = createRenderCache()
    renderMarkdownIncremental('Intro.\n\n~~~\n```\n\nstill inside', tilde)
    expect(tilde.prefixText).toBe('Intro.\n\n')
  })

  it('stops the boundary before an unclosed fence, blank line inside and all', () => {
    const cache = createRenderCache()
    renderMarkdownIncremental('Intro.\n\n```js\nlet a = 1\n\nlet b = 2', cache)
    expect(cache.prefixText).toBe('Intro.\n\n')
  })

  it('long prose: byte-identical at 40-char chunks', () => {
    expect(parityMismatches(longProse(), 40)).toEqual([])
  })

  it('byte-identical when a chunk boundary lands mid-heading', () => {
    expect(parityMismatches('Body.\n\n## A heading split across chunks\n\nTail.\n', 3)).toEqual([])
  })

  it('matches a plain full render when the buffer is rewound', () => {
    const cache = createRenderCache()
    renderMarkdownIncremental('One.\n\nTwo.\n\nThree', cache)
    expect(renderMarkdownIncremental('Other.\n\nText', cache)).toBe(
      renderMarkdown('Other.\n\nText'),
    )
  })

  it('returns empty string and clears the cache for empty text', () => {
    const cache = createRenderCache()
    renderMarkdownIncremental('One.\n\nTwo.', cache)
    expect(renderMarkdownIncremental('', cache)).toBe('')
    expect(cache.prefixText).toBe('')
    expect(cache.prefixHtml).toBe('')
  })

  it('disables caching outright when the buffer holds a link reference definition', () => {
    const cache = createRenderCache()
    renderMarkdownIncremental('Para one.\n\nPara two.\n\nmore', cache)
    expect(cache.prefixText.length).toBeGreaterThan(0)
    renderMarkdownIncremental('Para one.\n\nPara two.\n\n[a]: /x\n\n[a]', cache)
    expect(cache.disabled).toBe(true)
    expect(cache.prefixText).toBe('')
  })

  it('does not advance the boundary across a list or an indented code block', () => {
    const list = createRenderCache()
    renderMarkdownIncremental('- one\n\n- two\n\nmore', list)
    expect(list.prefixText).toBe('')

    const code = createRenderCache()
    renderMarkdownIncremental('    one\n\n    two\n\nmore', code)
    expect(code.prefixText).toBe('')
  })

  it('advances the boundary on settled prose', () => {
    const cache = createRenderCache()
    renderMarkdownIncremental('One.\n\nTwo.\n\nThr', cache)
    expect(cache.prefixText).toBe('One.\n\nTwo.\n\n')
    expect(cache.prefixHtml).toBe(renderMarkdown('One.\n\nTwo.\n\n'))
  })
})

describe('renderMarkdownIncremental work saved', () => {
  it('renders far fewer characters per frame than a full re-render', () => {
    const full = longProse()
    const md = getRenderer()
    const real = md.render.bind(md)
    let chars = 0
    md.render = (src) => {
      chars += src.length

      return real(src)
    }

    try {
      let before = 0
      let after = 0
      const splitA = createSplitState()
      const splitB = createSplitState()
      const cache = createRenderCache()

      for (let end = 40; ; end = Math.min(end + 40, full.length)) {
        const text = full.slice(0, end)

        chars = 0
        renderMarkdown(splitSafePrefixIncremental(text, splitA).safe)
        before += chars

        chars = 0
        renderMarkdownIncremental(splitSafePrefixIncremental(text, splitB).safe, cache)
        after += chars

        if (end >= full.length) break
      }

      // Whole-prefix re-rendering is quadratic in the buffer length; the
      // incremental path is close to linear.
      expect(before).toBeGreaterThan(150000)
      expect(after).toBeLessThan(before / 8)
    } finally {
      md.render = real
    }
  })
})
