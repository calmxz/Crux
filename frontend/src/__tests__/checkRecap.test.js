import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CheckRecap from '../components/chat/CheckRecap.vue'

const batch = (overrides = {}) => ({
  gap: 'glycolysis',
  total: 1,
  items: [
    {
      question: 'Which enzyme catalyzes the rate-limiting step?',
      options: ['PFK-1', 'Pyruvate kinase', 'Hexokinase'],
      status: 'answered',
      selectedIndex: 0,
      correctIndex: 0,
      correct: true,
      explanation: 'PFK-1 catalyzes the committed step.',
      ...overrides,
    },
  ],
})

describe('CheckRecap', () => {
  it('marks the chosen-correct option as your answer + correct', () => {
    const w = mount(CheckRecap, { props: { batch: batch() } })
    const opts = w.findAll('[data-testid="recap-option"]')
    expect(opts[0].classes()).toContain('is-correct')
    expect(opts[0].text()).toMatch(/your answer/i)
  })

  it('marks wrong pick incorrect and the correct option correct', () => {
    const w = mount(CheckRecap, {
      props: { batch: batch({ selectedIndex: 1, correct: false }) },
    })

    const opts = w.findAll('[data-testid="recap-option"]')
    expect(opts[1].classes()).toContain('is-incorrect')
    expect(opts[0].classes()).toContain('is-correct')
  })

  it('shows "answer not recorded" when selectedIndex is null', () => {
    const w = mount(CheckRecap, {
      props: { batch: batch({ selectedIndex: null, correct: null, status: 'answered' }) },
    })

    expect(w.text()).toMatch(/answer not recorded/i)
    const opts = w.findAll('[data-testid="recap-option"]')
    expect(opts.some((o) => o.classes().includes('is-incorrect'))).toBe(false)
  })

  it('shows "answer not recorded" for a skipped item', () => {
    const w = mount(CheckRecap, {
      props: { batch: batch({ status: 'skipped', selectedIndex: null, correct: null }) },
    })

    expect(w.text()).toMatch(/answer not recorded/i)
    const opts = w.findAll('[data-testid="recap-option"]')
    expect(opts.some((o) => o.classes().includes('is-incorrect'))).toBe(false)
    // The correct option is still highlighted so the learner sees the answer.
    expect(opts[0].classes()).toContain('is-correct')
  })

  it('renders explanation and a score header', () => {
    const w = mount(CheckRecap, { props: { batch: batch() } })
    expect(w.text()).toContain('PFK-1 catalyzes the committed step.')
    expect(w.text()).toMatch(/1\s*\/\s*1/)
  })
})

// #364: the recap of set N of M names the set beside the gap and repeats the
// segmented rule with sets 1..N done. No "next set follows" signpost.
describe('CheckRecap set progress (#364)', () => {
  const withSets = (setIndex, setTotal) => ({ ...batch(), setIndex, setTotal })
  const segs = (w) => w.findAll('[data-testid="recap-rule-seg"]')

  it.each([
    ['absent', batch()],
    ['null', withSets(null, null)],
    ['1 of 1', withSets(1, 1)],
  ])('single-set (%s) renders unchanged', (_, b) => {
    const w = mount(CheckRecap, { props: { batch: b } })
    expect(w.get('.recap-gap').text()).toBe('glycolysis')
    expect(w.text()).not.toMatch(/set \d/)
    expect(w.find('[data-testid="recap-set-rule"]').exists()).toBe(false)
    expect(w.find('.recap-header').classes()).not.toContain('is-segmented')
  })

  it('multi-set head line reads gap · set N of M after the score', () => {
    const w = mount(CheckRecap, { props: { batch: withSets(2, 3) } })
    // The flex gap spaces the name from the set phrase, not a text space.
    expect(w.get('.recap-gap').text()).toMatch(/^glycolysis\s*· set 2 of 3$/)
    expect(w.find('.recap-header').classes()).toContain('is-segmented')
  })

  it('segment count equals set_total, sets 1..N done, the rest upcoming', () => {
    const w = mount(CheckRecap, { props: { batch: withSets(2, 3) } })
    expect(segs(w).map((s) => s.classes().includes('is-done'))).toEqual([true, true, false])
    expect(segs(w)[2].classes()).toContain('is-todo')
  })

  it('does not signpost the next set', () => {
    const w = mount(CheckRecap, { props: { batch: withSets(1, 3) } })
    expect(w.text()).not.toMatch(/follows/i)
  })
})
