import { describe, it, expect } from 'vitest'
import {
  splitSafePrefix,
  splitSafePrefixIncremental,
  createSplitState,
} from '../lib/markdownStreamBuffer.js'

describe('splitSafePrefix', () => {
  it('returns whole text when no delimiters are open', () => {
    expect(splitSafePrefix('plain prose')).toEqual({ safe: 'plain prose', deferred: '' })
  })

  it('holds back text inside unclosed inline math', () => {
    expect(splitSafePrefix('cost is $O(log ')).toEqual({
      safe: 'cost is ',
      deferred: '$O(log ',
    })
  })

  it('emits whole text once inline math closes', () => {
    expect(splitSafePrefix('cost is $O(log n)$ here')).toEqual({
      safe: 'cost is $O(log n)$ here',
      deferred: '',
    })
  })

  it('holds back unclosed display math', () => {
    expect(splitSafePrefix('see $$ \\int_0^1 x ')).toEqual({
      safe: 'see ',
      deferred: '$$ \\int_0^1 x ',
    })
  })

  it('emits closed display math', () => {
    expect(splitSafePrefix('see $$ \\int_0^1 x \\,dx $$ done')).toEqual({
      safe: 'see $$ \\int_0^1 x \\,dx $$ done',
      deferred: '',
    })
  })

  it('holds back unclosed fenced code', () => {
    expect(splitSafePrefix('```python\ndef foo')).toEqual({
      safe: '',
      deferred: '```python\ndef foo',
    })
  })

  it('emits closed fenced code', () => {
    expect(splitSafePrefix('```python\ndef foo():\n  pass\n```\nafter')).toEqual({
      safe: '```python\ndef foo():\n  pass\n```\nafter',
      deferred: '',
    })
  })

  it('holds back unclosed inline code', () => {
    expect(splitSafePrefix('call `foo()')).toEqual({
      safe: 'call ',
      deferred: '`foo()',
    })
  })

  it('emits closed inline code', () => {
    expect(splitSafePrefix('call `foo()` now')).toEqual({
      safe: 'call `foo()` now',
      deferred: '',
    })
  })

  it('breaks inline math on newline (treats as literal $)', () => {
    expect(splitSafePrefix('$broken\nrest')).toEqual({
      safe: '$broken\nrest',
      deferred: '',
    })
  })

  it('prioritizes fenced code over inline backtick when both candidates exist', () => {
    expect(splitSafePrefix('```\n`inner` still in fence')).toEqual({
      safe: '',
      deferred: '```\n`inner` still in fence',
    })
  })

  it('handles fenced code immediately followed by math', () => {
    expect(splitSafePrefix('```py\nx=1\n```\nand $a')).toEqual({
      safe: '```py\nx=1\n```\nand ',
      deferred: '$a',
    })
  })

  it('is empty-safe', () => {
    expect(splitSafePrefix('')).toEqual({ safe: '', deferred: '' })
  })
})

describe('splitSafePrefixIncremental', () => {
  const FIXTURES = [
    'plain text with no delimiters at all',
    'before ```js\nconst x = 1\n``` after',
    'a `b` c `d` e',
    'inline $x^2$ math and $$\\sum_i x_i$$ display',
    'x ```\nfence built char by char\n``` y',
    'unclosed fence ```python\nnever closes',
    'tricky `` double backtick then ``` fence\ncode\n```',
    'mixed $a$ `b` ```\nc\n``` $$d$$ tail',
    'dollar then more $$ then close $$ then ` open',
    'x ```\nfence grown from what looked like a closed `` pair\n```',
    'a ```x``` ```` trailing backtick run after closed fence',
    '```x y``` z',
    'ends in dollars $$',
  ]

  it('matches full scan at every prefix of every fixture (char-by-char)', () => {
    for (const fixture of FIXTURES) {
      const state = createSplitState()

      for (let i = 1; i <= fixture.length; i++) {
        const text = fixture.slice(0, i)
        const inc = splitSafePrefixIncremental(text, state)
        const full = splitSafePrefix(text)
        expect({ fixture, len: i, result: inc }).toEqual({ fixture, len: i, result: full })
      }
    }
  })

  it('matches full scan under chunked appends (3-char deltas)', () => {
    for (const fixture of FIXTURES) {
      const state = createSplitState()

      for (let i = 3; i <= fixture.length + 2; i += 3) {
        const text = fixture.slice(0, Math.min(i, fixture.length))
        expect(splitSafePrefixIncremental(text, state)).toEqual(splitSafePrefix(text))
      }
    }
  })

  it('resets on non-append change', () => {
    const state = createSplitState()
    splitSafePrefixIncremental('abc `unclosed', state)
    const out = splitSafePrefixIncremental('completely different', state)
    expect(out).toEqual(splitSafePrefix('completely different'))
  })

  it('handles empty text by resetting state', () => {
    const state = createSplitState()
    splitSafePrefixIncremental('abc', state)
    expect(splitSafePrefixIncremental('', state)).toEqual({ safe: '', deferred: '' })
    expect(splitSafePrefixIncremental('new', state)).toEqual(splitSafePrefix('new'))
  })
})
