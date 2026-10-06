import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SessionChips from '@/components/SessionChips.vue'

const FOCUS = { type: 'focus', label: 'ATP yield' }

const MASTERED = { type: 'mastered', label: '3 mastered', count: 3 }

describe('SessionChips', () => {
  it('card variant: visible Focus prefix and full mastered label', () => {
    const w = mount(SessionChips, { props: { chips: [FOCUS, MASTERED], variant: 'card' } })
    const focus = w.get('[data-testid="chip-focus"]')
    expect(focus.text()).toContain('Focus:')
    expect(focus.text()).toContain('ATP yield')
    expect(w.get('[data-testid="chip-mastered"]').text()).toContain('3 mastered')
  })

  it('rail variant: sr-only focus prefix; count-only mastered with sr-only suffix', () => {
    const w = mount(SessionChips, { props: { chips: [FOCUS, MASTERED], variant: 'rail' } })
    const focus = w.get('[data-testid="chip-focus"]')
    expect(focus.find('.chip-text').text()).toBe('ATP yield')
    expect(focus.find('.sr-only').text()).toContain('Focus:')
    const mastered = w.get('[data-testid="chip-mastered"]')
    expect(mastered.find('.chip-text').text()).toBe('3')
    expect(mastered.find('.sr-only').text()).toContain('mastered')
  })

  it('marks glyphs aria-hidden', () => {
    const w = mount(SessionChips, { props: { chips: [FOCUS, MASTERED] } })
    const glyphs = w.findAll('.chip-glyph')
    expect(glyphs.length).toBe(2)

    for (const g of glyphs) expect(g.attributes('aria-hidden')).toBe('true')
  })

  it('renders no chip elements for an empty array', () => {
    const w = mount(SessionChips, { props: { chips: [] } })
    expect(w.findAll('.chip')).toHaveLength(0)
  })
})
