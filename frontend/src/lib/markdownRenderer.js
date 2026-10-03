import { ref } from 'vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'

// P1: markdown-it and DOMPurify are eager (every tutor turn and both legal
// pages need them). KaTeX and highlight.js are ~154 KB gzip between them and
// are only needed when a reply actually contains math or a fenced block, so
// they are dynamic-imported on first sight of one. Until a plugin lands the
// content renders in its plain fallback; `markdownAssetsVersion` bumps when it
// arrives so MarkdownContent.vue re-renders the same text with it.
//
// NOTE: @mdit/plugin-katex replaces @vscode/markdown-it-katex (itself a
// replacement for markdown-it-katex@2 and its unfixable XSS,
// GHSA-5ff8-jcf9-fw62). The vscode fork is CJS-only and pins katex ^0.16;
// both Vite's dev prebundle and the rolldown prod build mis-convert it so
// KaTeX's macro table ends up empty in the browser and every \command renders
// as literal "undefined control sequence" text (node/vitest render fine,
// which is why CI missed it). @mdit/plugin-katex is ESM-native and peers on
// markdown-it 15 + katex 0.18.
//
// Rendered HTML is always passed through DOMPurify below, lazy plugins
// included: the KaTeX chunk arriving later does not widen the sanitizer.

// Bumped each time a lazy plugin lands. Consumers read it to re-render.
export const markdownAssetsVersion = ref(0)

let _md = null

let _mdKatex = null

let _hljs = null

// 'idle' | 'loading' | 'ready' | 'failed'. A failed load stays failed: the
// plain fallback is correct output, not an error state, and retrying on every
// keystroke of a streaming reply would hammer a dead network.
let _katexState = 'idle'

let _hljsState = 'idle'

// Promises still in flight, so tests and callers can await the settle point.
let _pending = []

function _track(p) {
  // Never rejects: a failed asset degrades to the fallback, it does not throw
  // out of a render or leave `whenRendererReady()` hanging.
  _pending.push(p)
}

/**
 * Resolves once every lazy asset load started so far has settled (loaded or
 * failed). Loads started while awaiting are awaited too.
 */
export async function whenRendererReady() {
  while (_pending.length) {
    const batch = _pending
    _pending = []
    await Promise.all(batch)
  }
}

function _landed() {
  _md = null
  markdownAssetsVersion.value += 1
}

function ensureKatex() {
  if (_katexState !== 'idle') return
  _katexState = 'loading'
  _track(
    Promise.all([
      import('@mdit/plugin-katex'),
      // The stylesheet rides the same chunk boundary as the plugin, so the
      // KaTeX webfonts are never referenced on a page without math.
      import('katex/dist/katex.min.css'),
    ])
      .then(([mod]) => {
        _mdKatex = mod.katex
        _katexState = 'ready'
        _landed()
      })
      .catch(() => {
        _katexState = 'failed'
      }),
  )
}

function ensureHljs() {
  if (_hljsState !== 'idle') return
  _hljsState = 'loading'
  _track(
    Promise.all([
      import('highlight.js/lib/core'),
      import('highlight.js/lib/languages/python'),
      import('highlight.js/lib/languages/javascript'),
      import('highlight.js/lib/languages/typescript'),
      import('highlight.js/lib/languages/sql'),
      import('highlight.js/lib/languages/bash'),
      import('highlight.js/lib/languages/json'),
      import('highlight.js/lib/languages/yaml'),
      import('highlight.js/lib/languages/markdown'),
    ])
      .then(([core, ...langs]) => {
        const hljs = core.default

        const names = [
          'python',
          'javascript',
          'typescript',
          'sql',
          'bash',
          'json',
          'yaml',
          'markdown',
        ]

        names.forEach((name, i) => hljs.registerLanguage(name, langs[i].default))
        _hljs = hljs
        _hljsState = 'ready'
        _landed()
      })
      .catch(() => {
        _hljsState = 'failed'
      }),
  )
}

// Cheap pre-parse sniffs. A false positive costs one extra chunk fetch; a
// false negative only means the plain fallback stands, which is why they are
// deliberately loose.
const FENCE_RE = /(^|\n)[ \t]{0,3}(```|~~~)/

function requestAssets(text) {
  if (text.includes('$')) ensureKatex()

  if (FENCE_RE.test(text)) ensureHljs()
}

function escapeAttr(s) {
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')
}

function build() {
  const md = new MarkdownIt({
    html: false,
    linkify: true,
    breaks: false,
    highlight: (str, lang) => {
      if (_hljs && lang && _hljs.getLanguage(lang)) {
        try {
          return _hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
        } catch {
          return ''
        }
      }

      return ''
    },
  })

  if (_mdKatex) {
    md.use(_mdKatex, { throwOnError: false, errorColor: 'var(--math-accent, #ff6b5b)' })
  }

  // Harden generated/linkified anchors: add rel="noopener nofollow".
  // No target is added (links open in place); html:false is unchanged.
  const defaultLinkOpen =
    md.renderer.rules.link_open ||
    ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

  md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
    const existing = tokens[idx].attrGet('rel') || ''

    const merged = [
      ...new Set([...existing.split(/\s+/), 'noopener', 'nofollow'].filter(Boolean)),
    ].join(' ')

    tokens[idx].attrSet('rel', merged)

    return defaultLinkOpen(tokens, idx, options, env, self)
  }

  // D-13: a wide table must scroll inside the bubble instead of widening it.
  // The wrapper is emitted by the renderer (not a post-render DOM pass) so the
  // markup that reaches DOMPurify is the markup we sanitize.
  md.renderer.rules.table_open = () => '<div class="md-table-wrap"><table>'
  md.renderer.rules.table_close = () => '</table></div>'

  md.renderer.rules.fence = (tokens, idx) => {
    const token = tokens[idx]
    const langRaw = token.info.trim().split(/\s+/)[0] || ''
    const lang = langRaw || 'plain'
    let body

    if (_hljs && langRaw && _hljs.getLanguage(langRaw)) {
      body = _hljs.highlight(token.content, { language: langRaw, ignoreIllegals: true }).value
    } else {
      // Plain fallback: escaped source, identical chrome and classes, so the
      // copy button and the pitch snapper behave the same before and after
      // highlight.js lands.
      body = md.utils.escapeHtml(token.content)
    }

    const langClass = langRaw ? `language-${escapeAttr(langRaw)} hljs` : 'hljs'

    return (
      `<pre class="code-block">` +
      `<div class="code-block-header">` +
      `<span class="code-block-lang">${escapeAttr(lang)}</span>` +
      `<button type="button" class="code-block-copy hit-44" data-copy-button>copy</button>` +
      `</div>` +
      `<code class="${langClass}">${body}</code>` +
      `</pre>`
    )
  }

  return md
}

export function getRenderer() {
  if (!_md) _md = build()

  return _md
}

const PURIFY_CONFIG = {
  ADD_TAGS: ['math', 'semantics', 'annotation', 'mrow', 'mi', 'mn', 'mo', 'mtext', 'msup', 'msub'],
  ADD_ATTR: ['target', 'rel'],
}

export function renderMarkdown(text) {
  if (!text) return ''
  requestAssets(text)
  const md = getRenderer()
  const raw = md.render(text)

  return DOMPurify.sanitize(raw, PURIFY_CONFIG)
}

// ---------------------------------------------------------------------------
// F-15: incremental render of a growing streamed buffer.
//
// A streamed reply re-rendered whole on every frame is O(n^2) work: a 4 KB
// answer arriving in 40-char chunks renders ~200 KB of markdown. Instead the
// already-settled head of the buffer is rendered once and its HTML cached, and
// each frame only renders the tail after the cached boundary.
//
// Correctness is the whole game here: `renderMarkdown(head) + renderMarkdown(tail)`
// must be byte-identical to `renderMarkdown(head + tail)`. That only holds when
// the cut sits between two blocks that cannot influence each other, so the
// boundary rule is deliberately narrow and every case it cannot prove is sent
// down the plain full-render path:
//
//   * the cut is always immediately after a blank-line run, at top level
//     (never inside a fenced block or a multi-line $$ block);
//   * the block that closes just before the cut may not be a list or an
//     indented code block -- both of those swallow whatever follows a blank
//     line ("- a\n\n- b" is one loose list, "    a\n\n    b" is one <pre>);
//   * a link reference definition anywhere in the buffer disables caching
//     entirely, since a definition resolves references on the other side of
//     any cut.
//
// DOMPurify runs on each part with the same config; the sanitizer is not
// relaxed anywhere.

// Top-level link reference definition, e.g. "[foo]: /url".
const REFDEF_RE = /^ {0,3}\[[^\]\n]+\]:/m

// Capture the run of fence characters plus whatever trails it, so the scanner
// can apply the CommonMark closing rule (same char, at least as long, nothing
// but whitespace after) instead of treating any 3+ run as a toggle.
const FENCE_LINE_RE = /^ {0,3}(`{3,}|~{3,})(.*)$/

const BLANK_LINE_RE = /^[ \t]*$/

// Last top-level token types that must not sit immediately before a cut.
//
//   * a bullet or ordered list swallows the next block after a blank line
//     ("- a\n\n- b" is one loose list, and cutting it would also restart the
//     ordered-list counter with a spurious start= on the tail);
//   * an indented code block does the same ("    a\n\n    b" is one <pre>).
const UNSAFE_CLOSE = new Set(['bullet_list_close', 'ordered_list_close', 'code_block'])

// Per frame at most this many candidate boundaries are parse-checked, so a
// pathological buffer (a long blank-separated list) cannot make the boundary
// search itself quadratic.
const MAX_BOUNDARY_TRIES = 4

export function createRenderCache() {
  return { prefixText: '', prefixHtml: '', version: -1, disabled: false }
}

export function resetRenderCache(cache) {
  cache.prefixText = ''
  cache.prefixHtml = ''
  cache.version = markdownAssetsVersion.value
  cache.disabled = false
}

function _lineEnd(text, i) {
  const nl = text.indexOf('\n', i)

  return nl === -1 ? text.length : nl
}

/**
 * Single line scan of `text` from `from`. Returns the candidate cut offsets
 * (immediately after a blank-line run at top level, with real content
 * following, ascending) and whether the scan ended inside a fenced block.
 *
 * Fences follow the CommonMark rule: an opening run of 3+ backticks or tildes
 * is closed only by a run of the SAME character, at least as long, with nothing
 * but whitespace after it. A plain 3+ toggle would let an inner ``` line inside
 * a ```` or ~~~ fence flip the scanner out of the block, and the next blank
 * line would then become a cut candidate inside code.
 */
function scanBlocks(text, from) {
  const out = []
  let fenceChar = null
  let fenceLen = 0
  let inMath = false
  let sawContent = false
  let i = from

  while (i < text.length) {
    const eol = _lineEnd(text, i)
    const line = text.slice(i, eol)
    const next = eol === text.length ? text.length : eol + 1

    if (BLANK_LINE_RE.test(line)) {
      if (!fenceChar && !inMath && sawContent) {
        // Swallow the whole blank run; the boundary is the first content line.
        let j = next

        while (j < text.length) {
          const e2 = _lineEnd(text, j)

          if (!BLANK_LINE_RE.test(text.slice(j, e2))) break
          j = e2 === text.length ? text.length : e2 + 1
        }

        if (j < text.length) out.push(j)
        i = j
        continue
      }
    } else {
      sawContent = true
      const fence = FENCE_LINE_RE.exec(line)

      if (fenceChar) {
        // CommonMark: a closing fence uses the same character, is at least as
        // long as the opener, and carries nothing but whitespace after it. A
        // shorter or differently-charred run inside the block is content.
        if (
          fence &&
          fence[1][0] === fenceChar &&
          fence[1].length >= fenceLen &&
          fence[2].trim() === ''
        ) {
          fenceChar = null
          fenceLen = 0
        }
      } else if (fence) {
        fenceChar = fence[1][0]
        fenceLen = fence[1].length
      } else if ((line.match(/\$\$/g) || []).length % 2 === 1) {
        // An odd number of $$ on a line opens or closes a display block. A
        // false positive (a $$ inside inline code) only suppresses caching.
        inMath = !inMath
      }
    }

    i = next
  }

  return { boundaries: out, inFence: fenceChar !== null }
}

/**
 * Offsets in `text` (all > `from`) that sit immediately after a blank-line run
 * at top level, with real content following. Ascending.
 */
function topLevelBlankBoundaries(text, from) {
  return scanBlocks(text, from).boundaries
}

/** True when `segment` ends on a block that cannot absorb what follows it. */
function segmentClosesSafely(segment) {
  let tokens

  try {
    tokens = getRenderer().parse(segment, {})
  } catch {
    return false
  }

  let last = null

  for (const t of tokens) if (t.level === 0) last = t

  if (!last || UNSAFE_CLOSE.has(last.type)) return false

  // markdown-it renders an unterminated fence as a complete <pre>, so the head
  // would look closed while the tail got parsed as markdown rather than code.
  // `fence` is safe only once its closing run has actually arrived.
  if (last.type === 'fence' && scanBlocks(segment, 0).inFence) return false

  return true
}

/**
 * Renders `text` reusing the cached HTML of its settled head.
 * Byte-identical to `renderMarkdown(text)`; see the note above.
 */
export function renderMarkdownIncremental(text, cache) {
  if (!text) {
    resetRenderCache(cache)

    return ''
  }

  if (cache.version !== markdownAssetsVersion.value || !text.startsWith(cache.prefixText)) {
    resetRenderCache(cache)
  }

  if (cache.disabled) return renderMarkdown(text)

  if (REFDEF_RE.test(text)) {
    resetRenderCache(cache)
    cache.disabled = true

    return renderMarkdown(text)
  }

  const boundary = cache.prefixText.length
  const candidates = topLevelBlankBoundaries(text, boundary)
  const floor = Math.max(0, candidates.length - MAX_BOUNDARY_TRIES)

  for (let i = candidates.length - 1; i >= floor; i -= 1) {
    const segment = text.slice(boundary, candidates[i])

    if (segmentClosesSafely(segment)) {
      cache.prefixText = text.slice(0, candidates[i])
      cache.prefixHtml += renderMarkdown(segment)
      break
    }
  }

  const tail = text.slice(cache.prefixText.length)

  return cache.prefixHtml + (tail ? renderMarkdown(tail) : '')
}
