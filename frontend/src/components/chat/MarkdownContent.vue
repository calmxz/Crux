<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  createRenderCache,
  markdownAssetsVersion,
  renderMarkdown,
  renderMarkdownIncremental,
  resetRenderCache,
} from '@/lib/markdownRenderer.js'
import { splitSafePrefixIncremental, createSplitState } from '@/lib/markdownStreamBuffer.js'

const props = defineProps({
  text: { type: String, required: true },
  streaming: { type: Boolean, default: false },
})

// Per-instance scan state; plain object on purpose (mutated by the split,
// never read by the template).
const splitState = createSplitState()

// F-15: per-instance cache of the rendered HTML of the settled head of this
// bubble's stream. Streaming-only; the settled turn is always a plain full
// render.
const renderCache = createRenderCache()

const parts = computed(() => {
  // P1: KaTeX and highlight.js arrive after the first render that needs them.
  // Reading the version here (before either branch) subscribes this computed,
  // so the same text is re-rendered with the plugin once it lands.
  // renderMarkdownIncremental compares the same version against its cache, so a
  // plugin landing mid-stream invalidates the cached head too.
  void markdownAssetsVersion.value

  if (!props.streaming) {
    return { safeHtml: renderMarkdown(props.text), deferred: '' }
  }

  const { safe, deferred } = splitSafePrefixIncremental(props.text, splitState)

  return { safeHtml: renderMarkdownIncremental(safe, renderCache), deferred }
})

// Free the cached head when the turn settles: the non-streaming branch above is
// a full render, and a bubble that streams again starts from a clean cache.
watch(
  () => props.streaming,
  (now) => {
    if (!now) resetRenderCache(renderCache)
  },
)

// Blocks whose height is intrinsic (display math with fractions, images) cannot
// be snapped to the 28px pitch by CSS alone, so their bottom margin is topped up
// to the next whole pitch after render and whenever they resize. Everything else
// in the notes column is already a whole multiple, so one block never drags the
// rest of the page off the rules.
const rootEl = ref(null)

const SNAP_SELECTOR = '.katex-display, pre, table, img'

let _ro = null

function _pitch(el) {
  const v = parseFloat(getComputedStyle(el).getPropertyValue('--line-pitch'))

  return v > 0 ? v : 28
}

function snapBlocks() {
  const root = rootEl.value

  if (!root) return
  const pitch = _pitch(root)

  for (const el of root.querySelectorAll(SNAP_SELECTOR)) {
    // The applied top-up is read back from the property we wrote, never from a
    // measurement: clearing the style and re-measuring can return a mid-flight
    // value whenever anything transitions a margin here, which compounds the
    // pad on each pass.
    const applied = parseFloat(el.style.getPropertyValue('--snap-pad')) || 0
    const cs = getComputedStyle(el)

    const total =
      el.getBoundingClientRect().height +
      (parseFloat(cs.marginTop) || 0) +
      (parseFloat(cs.marginBottom) || 0)

    const natural = total - applied
    const pad = (pitch - (natural % pitch)) % pitch

    // Only write on a real change, so the observer cannot drive itself.
    if (Math.abs(pad - applied) > 0.01) {
      if (pad > 0.01) el.style.setProperty('--snap-pad', `${pad}px`)
      else el.style.removeProperty('--snap-pad')
    }
  }
}

// One pass per frame at most, and never re-entered from its own writes.
let _frame = 0

function scheduleSnap() {
  if (_frame) return
  _frame = requestAnimationFrame(() => {
    _frame = 0
    snapBlocks()
  })
}

function observeBlocks() {
  const root = rootEl.value

  if (!root || typeof ResizeObserver === 'undefined') return
  const blocks = root.querySelectorAll(SNAP_SELECTOR)
  _ro?.disconnect()

  // Most turns are prose and match nothing here, so the observer is built on
  // first need rather than once per rendered bubble. With no targets there is
  // also nothing for snapBlocks to top up.
  if (!blocks.length) return
  _ro = _ro || new ResizeObserver(() => scheduleSnap())

  for (const el of blocks) _ro.observe(el)
  snapBlocks()
}

// One re-observe per tick at most, however many watchers asked for it (the
// last streaming frame trips both of them in the same flush).
let _observeQueued = false

function scheduleObserve() {
  if (_observeQueued) return
  _observeQueued = true
  nextTick(() => {
    _observeQueued = false
    observeBlocks()
  })
}

// jsdom has no layout engine and no ResizeObserver; the snapper is a no-op there.
if (typeof ResizeObserver !== 'undefined') {
  onMounted(scheduleObserve)
  // safeHtml changes on every frame of a stream; re-walking the DOM that often
  // is pure waste, and blocks already observed keep snapping through the
  // observer anyway. Skip while streaming and do one pass when the turn settles.
  watch(
    () => parts.value.safeHtml,
    () => {
      if (props.streaming) return
      scheduleObserve()
    },
  )
  watch(
    () => props.streaming,
    (now) => {
      if (!now) scheduleObserve()
    },
  )
}

onBeforeUnmount(() => {
  _ro?.disconnect()
  _ro = null

  if (_frame) cancelAnimationFrame(_frame)
  _frame = 0
})

// F-03: the fence renderer emits a [data-copy-button] per code block, but
// v-html markup can't carry handlers (DOMPurify strips inline ones), so the
// click is delegated from the component root.
let _copyResetTimer = null

onBeforeUnmount(() => clearTimeout(_copyResetTimer))

async function onRootClick(e) {
  const btn = e.target.closest?.('[data-copy-button]')

  if (!btn) return
  const code = btn.closest('pre')?.querySelector('code')

  if (!code || !navigator.clipboard?.writeText) return

  try {
    await navigator.clipboard.writeText(code.textContent)
  } catch {
    return // clipboard permission denied; leave the label unchanged
  }

  btn.textContent = 'copied'
  clearTimeout(_copyResetTimer)
  _copyResetTimer = setTimeout(() => {
    btn.textContent = 'copy'
  }, 1500)
}
</script>

<template>
  <div class="markdown-content" @click="onRootClick">
    <div ref="rootEl" class="md-rendered" v-html="parts.safeHtml"></div>
    <span v-if="parts.deferred" class="deferred">{{ parts.deferred }}</span>
  </div>
</template>

<style scoped>
/* Every block snaps to the 28px pitch so the notes keep sitting on the rules. */
.markdown-content {
  line-height: var(--line-pitch);
}
/* Rendered markdown is real HTML; reset any inherited white-space: pre-wrap
   so inter-tag newlines don't render as blank lines. The deferred tail keeps
   pre-wrap (set below) for faithful streaming display. */
.md-rendered {
  white-space: normal;
  /* A new formatting context, so a trailing block's bottom margin -- including
     the top-up the snapper writes on display math or a table -- counts inside
     this box instead of collapsing out of it and off the pitch. */
  display: flow-root;
  /* D-13: a long URL or an unbroken token in a tutor turn must wrap rather than
     widen the notes column. */
  overflow-wrap: anywhere;
  word-break: break-word;
}
.md-rendered :deep(p) {
  margin: 0 0 var(--line-pitch);
}

/* Block rhythm on the pitch: every margin is 28px or a whole fraction of it,
   so a paragraph, a list or a heading never knocks the text off the rules. */
.md-rendered :deep(ul),
.md-rendered :deep(ol) {
  margin: 0 0 var(--line-pitch);
  padding-left: 1.35em;
}
.md-rendered :deep(li) {
  margin: 0;
}
.md-rendered :deep(li > p) {
  margin: 0;
}
.md-rendered :deep(h1),
.md-rendered :deep(h2),
.md-rendered :deep(h3),
.md-rendered :deep(h4) {
  font-family: var(--font-display);
  font-size: var(--fs-h3);
  font-weight: 600;
  line-height: var(--line-pitch);
  margin: var(--line-pitch) 0 0;
}
.md-rendered :deep(h1:first-child),
.md-rendered :deep(h2:first-child),
.md-rendered :deep(h3:first-child),
.md-rendered :deep(h4:first-child) {
  margin-top: 0;
}
/* Quoted matter is set in, not fenced by a coloured side rule. */
.md-rendered :deep(blockquote) {
  margin: 0 0 var(--line-pitch);
  padding-left: 1.5em;
  color: var(--pencil);
  font-style: italic;
}
.md-rendered :deep(> :last-child) {
  margin-bottom: 0;
}
.md-rendered :deep(pre) {
  background: var(--color-surface-soft);
  color: var(--ink);
  border: 1px solid var(--rule-strong);
  border-radius: var(--radius-sm);
  /* 13px + 1px border top and bottom = one pitch of frame, so a fence of n
     lines is exactly 28(n+1) tall. */
  padding: calc(var(--line-pitch) / 2 - 1px) 0.875rem;
  padding-bottom: calc(var(--line-pitch) / 2 - 1px + var(--snap-pad, 0px));
  margin: 0 0 var(--line-pitch);
  transition: none;
  font-family: var(--font-mono);
  font-size: 0.9375rem;
  line-height: var(--line-pitch);
  overflow-x: auto;
}
.md-rendered :deep(.code-block-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: var(--fs-label);
  line-height: var(--line-pitch);
  color: var(--pencil);
}
.md-rendered :deep(.code-block-copy) {
  border: 1px solid var(--rule-strong);
  background: transparent;
  color: var(--ink-learner);
  border-radius: var(--radius-sm);
  padding: 1px 8px;
  font: inherit;
  /* 24px of leading + 1px padding + 1px border each side = one pitch, so the
     fence header row is a single line tall. */
  line-height: calc(var(--line-pitch) - 4px);
  cursor: pointer;
}
.md-rendered :deep(.code-block-copy:hover),
.md-rendered :deep(.code-block-copy:focus-visible) {
  border-color: var(--ink-learner);
}
.md-rendered :deep(code:not(pre code)) {
  background: var(--color-surface-soft);
  color: var(--ink);
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.9em;
}
/* Display math has an intrinsic height (fractions, radicals), so the rule under
   it is painted rather than laid out and the snapper below tops the block up to
   the next whole pitch. */
.md-rendered :deep(.katex-display) {
  margin: var(--line-pitch) 0;
  /* The snapper drives --snap-pad rather than writing margin-bottom directly:
     padding never collapses out of the block and never animates, so the top-up
     lands even where a global transition-duration is in force. */
  padding-bottom: calc(var(--line-pitch) / 2 - 1px + var(--snap-pad, 0px));
  box-shadow: inset 0 -1px 0 var(--rule-strong);
  transition: none;
}
/* D-13: a table wider than the column scrolls inside this wrapper instead of
   widening the bubble. Cells opt out of the break-word above: a table is
   already free to lay its columns out, and breaking mid-word there makes the
   grid unreadable. */
.md-rendered :deep(.md-table-wrap) {
  overflow-x: auto;
  max-width: 100%;
}
.md-rendered :deep(.md-table-wrap th),
.md-rendered :deep(.md-table-wrap td) {
  overflow-wrap: normal;
  word-break: normal;
}
/* overflow-x makes the wrapper a formatting context, so a trailing table's
   bottom margin no longer collapses out of it and the bubble would gain a whole
   dead pitch. The snapper's top-up still has to land, so keep that part. */
.md-rendered :deep(.md-table-wrap:last-child > table) {
  margin-bottom: var(--snap-pad, 0px);
}
.md-rendered :deep(table) {
  border-collapse: collapse;
  /* Collapsed borders make the browser ignore padding on the table box, so this
     one block takes its top-up as margin. */
  margin: 0 0 calc(var(--line-pitch) + var(--snap-pad, 0px));
  transition: none;
}
/* Collapsed borders eat a pixel per row: 27px of leading plus the shared 1px
   rule is one pitch per row. */
.md-rendered :deep(th),
.md-rendered :deep(td) {
  border: 1px solid var(--rule-strong);
  padding: 0 0.75rem;
  line-height: calc(var(--line-pitch) - 1px);
  font-variant-numeric: tabular-nums;
}
/* Block, not inline: an inline image sits on a paragraph baseline and cannot be
   snapped to the pitch. */
.md-rendered :deep(img) {
  display: block;
  max-width: 100%;
  height: auto;
  padding-bottom: var(--snap-pad, 0px);
  transition: none;
}
.md-rendered :deep(th) {
  text-align: left;
  font-weight: 700;
}
/* Block, not inline: a mono tail inside the sans strut makes a taller line box
   and the streaming text would drift off the rules mid-turn. */
.deferred {
  display: block;
  font-family: var(--font-mono);
  white-space: pre-wrap;
  color: var(--pencil);
}
</style>
