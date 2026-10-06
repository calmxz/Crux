import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TopicSuggestCard from '@/components/TopicSuggestCard.vue'

const BROAD = {
  mode: 'broad',
  topic: 'Thermodynamics',
  items: [
    { label: 'Laws of thermodynamics', hint: null },
    { label: 'Heat engines', hint: 'efficiency limits' },
    { label: 'Entropy', hint: null },
  ],
}

const SPECIFIC = {
  mode: 'specific',
  topic: 'Carnot cycle',
  items: [
    { label: 'Entropy and the second law', hint: 'why Carnot is the ceiling' },
    { label: 'Otto and Diesel cycles', hint: null },
  ],
}

function lineTexts(w) {
  return w.findAll('[data-testid^="topic-line-"]').map((b) => b.text())
}

describe('TopicSuggestCard', () => {
  it('broad: titles the card for subtopics and lists them in order', () => {
    const w = mount(TopicSuggestCard, { props: { card: BROAD } })
    expect(w.text()).toContain('Here is what we would cover. Where do you want to start?')
    expect(lineTexts(w)).toEqual([
      'A.Laws of thermodynamics',
      'B.Heat enginesefficiency limits',
      'C.Entropy',
    ])
  })

  it('specific: leads with "Keep going on <topic>", then the adjacent topics', () => {
    const w = mount(TopicSuggestCard, { props: { card: SPECIFIC } })
    expect(w.text()).toContain('Nearby ground I can teach. Want to widen out?')
    expect(lineTexts(w)).toEqual([
      'A.Keep going on Carnot cycle',
      'B.Entropy and the second lawwhy Carnot is the ceiling',
      'C.Otto and Diesel cycles',
    ])
  })

  it('both modes carry the free-text line and the upload nudge, no upload control', () => {
    for (const card of [BROAD, SPECIFIC]) {
      const w = mount(TopicSuggestCard, { props: { card } })
      expect(w.get('[data-testid="topic-other-input"]').attributes('placeholder')).toBe(
        'Something else...',
      )
      expect(w.text()).toContain('clip in the composer')
      expect(w.find('input[type="file"]').exists()).toBe(false)
    }
  })

  it('a tapped subtopic emits the learner message to send', async () => {
    const w = mount(TopicSuggestCard, { props: { card: BROAD } })
    await w.get('[data-testid="topic-line-1"]').trigger('click')
    expect(w.emitted('pick')).toEqual([["Let's start with Heat engines"]])
  })

  it('the keep-going line emits "Keep going on <topic>"', async () => {
    const w = mount(TopicSuggestCard, { props: { card: SPECIFIC } })
    await w.get('[data-testid="topic-line-0"]').trigger('click')
    expect(w.emitted('pick')).toEqual([['Keep going on Carnot cycle']])
  })

  it('"Something else" sends the typed text, ignoring blanks', async () => {
    const w = mount(TopicSuggestCard, { props: { card: BROAD } })
    const input = w.get('[data-testid="topic-other-input"]')
    await input.setValue('   ')
    await w.get('form').trigger('submit')
    expect(w.emitted('pick')).toBeUndefined()
    await input.setValue('  Phase diagrams ')
    await w.get('form').trigger('submit')
    expect(w.emitted('pick')).toEqual([['Phase diagrams']])
  })

  it('emits dismiss, and disables the lines (not dismiss) while busy', async () => {
    const w = mount(TopicSuggestCard, { props: { card: BROAD, busy: true } })
    expect(w.get('[data-testid="topic-line-0"]').attributes('disabled')).toBeDefined()
    expect(w.get('[data-testid="topic-dismiss"]').attributes('disabled')).toBeUndefined()
    await w.get('[data-testid="topic-dismiss"]').trigger('click')
    expect(w.emitted('dismiss')).toHaveLength(1)
  })
})
