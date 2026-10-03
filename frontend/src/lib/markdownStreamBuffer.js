// Scans a partial markdown buffer and splits it into a "safe" prefix
// (everything outside any unclosed delimited region) and a "deferred" tail
// (the unclosed region plus everything after it). Callers render the safe
// prefix through markdown-it and show the deferred tail as plain monospace
// until more text arrives.
//
// Delimiter precedence (matches markdown-it parse order):
//   fenced code (```)   - strongest, ignores everything inside until ```
//   inline code (`)     - same-line only
//   display math ($$)   - multi-line, balanced
//   inline math ($)     - same-line only, breaks on newline

const FENCE = '```'

function findOpener(text) {
  // Returns { type, index } for the earliest open delimiter, or null.
  const candidates = []
  let i = text.indexOf(FENCE)

  if (i !== -1) candidates.push({ type: 'fence', index: i, len: 3 })
  i = text.indexOf('$$')

  if (i !== -1) candidates.push({ type: 'display', index: i, len: 2 })

  // Inline math: single $, but only if not part of $$
  for (let k = 0; k < text.length; k++) {
    if (text[k] === '$' && text[k + 1] !== '$' && text[k - 1] !== '$') {
      candidates.push({ type: 'inline-math', index: k, len: 1 })
      break
    }
  }

  i = text.indexOf('`')

  if (i !== -1 && text.slice(i, i + 3) !== FENCE) {
    candidates.push({ type: 'inline-code', index: i, len: 1 })
  }

  if (!candidates.length) return null
  candidates.sort((a, b) => a.index - b.index)

  return candidates[0]
}

function findCloser(text, opener) {
  const start = opener.index + opener.len

  switch (opener.type) {
    case 'fence': {
      const idx = text.indexOf(FENCE, start)

      return idx === -1 ? -1 : idx + FENCE.length
    }

    case 'display': {
      const idx = text.indexOf('$$', start)

      return idx === -1 ? -1 : idx + 2
    }

    case 'inline-math': {
      // Closes on next $ on same line, breaks on newline
      for (let k = start; k < text.length; k++) {
        if (text[k] === '\n') return start - 1 // treat opener as literal - recurse

        if (text[k] === '$') return k + 1
      }

      return -1
    }

    case 'inline-code': {
      for (let k = start; k < text.length; k++) {
        if (text[k] === '\n') return start - 1

        if (text[k] === '`') return k + 1
      }

      return -1
    }
  }

  return -1
}

function scanSafePrefix(text, cut) {
  let stableCursor = 0
  let cursor = 0

  while (cursor < text.length) {
    if (cursor <= cut) stableCursor = cursor
    const tail = text.slice(cursor)
    const opener = findOpener(tail)

    if (!opener) {
      return { safe: text, deferred: '', stableCursor }
    }

    const absoluteOpenerIndex = cursor + opener.index
    const absoluteOpenerEndIndex = absoluteOpenerIndex + opener.len
    const localCloser = findCloser(tail, opener)

    if (localCloser === -1) {
      // Unclosed - defer from the opener onward.
      return {
        safe: text.slice(0, absoluteOpenerIndex),
        deferred: text.slice(absoluteOpenerIndex),
        stableCursor,
      }
    }

    if (localCloser < opener.index + opener.len) {
      // Inline math/code "broke" on newline - treat opener as literal and continue.
      cursor = absoluteOpenerEndIndex
      continue
    }

    cursor = cursor + localCloser
  }

  return { safe: text, deferred: '', stableCursor }
}

export function splitSafePrefix(text) {
  if (!text) return { safe: '', deferred: '' }
  const { safe, deferred } = scanSafePrefix(text, Infinity)

  return { safe, deferred }
}

// P4.3: incremental variant. A streamed buffer only grows at the end, so we
// resume scanning from a saved anchor instead of offset 0. An anchor is only
// valid if appended text can never change the interpretation of anything
// before it. Appended characters can only extend the text's TRAILING run of
// delimiter characters ('`' or '$') -- e.g. a committed closed pair "x ``"
// turns into fence opener "x ```" one backtick later. So a stable anchor is
// the largest between-region scanner cursor that is <= the position right
// after the last non-delimiter character. scanSafePrefix's `cut` parameter
// enforces exactly that bound.

function lastNonDelimiterIndex(text) {
  let i = text.length - 1

  while (i >= 0 && (text[i] === '`' || text[i] === '$')) i--

  return i
}

export function createSplitState() {
  return { lastText: '', anchor: 0 }
}

export function splitSafePrefixIncremental(text, state) {
  if (!text) {
    state.lastText = ''
    state.anchor = 0

    return { safe: '', deferred: '' }
  }

  let base = 0

  if (state.lastText && text.startsWith(state.lastText)) {
    base = state.anchor
  }

  const cut = Math.max(0, lastNonDelimiterIndex(text) + 1 - base)

  const { safe: tailSafe, deferred, stableCursor } = scanSafePrefix(
    text.slice(base),
    cut,
  )

  state.lastText = text
  state.anchor = base + stableCursor

  return { safe: text.slice(0, base) + tailSafe, deferred }
}
