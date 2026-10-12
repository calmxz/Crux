import { describe, it, expect } from 'vitest'
import { renderMarkdown } from '../lib/markdownRenderer.js'

describe('markdownRenderer link rel', () => {
  it('adds rel="noopener nofollow" to rendered links', () => {
    const html = renderMarkdown('[x](https://example.com)')
    const anchor = html.match(/<a\b[^>]*>/)
    expect(anchor).not.toBeNull()
    expect(anchor[0]).toMatch(/rel="[^"]*\bnoopener\b[^"]*"/)
    expect(anchor[0]).toMatch(/rel="[^"]*\bnofollow\b[^"]*"/)
  })

  it('adds rel to autolinked (linkify) urls', () => {
    const html = renderMarkdown('see https://example.com for more')
    const anchor = html.match(/<a\b[^>]*>/)
    expect(anchor).not.toBeNull()
    expect(anchor[0]).toMatch(
      /rel="[^"]*noopener[^"]*nofollow[^"]*"|rel="[^"]*nofollow[^"]*noopener[^"]*"/,
    )
  })

  it('emits rel tokens without duplicates (merge dedups)', () => {
    const html = renderMarkdown('[x](https://example.com)')
    const anchor = html.match(/<a\b[^>]*>/)
    expect(anchor).not.toBeNull()
    const relMatch = anchor[0].match(/rel="([^"]*)"/)
    expect(relMatch).not.toBeNull()
    const tokens = relMatch[1].split(/\s+/).filter(Boolean)
    expect(new Set(tokens).size).toBe(tokens.length)
    expect(relMatch[1]).toBe('noopener nofollow')
  })
})
