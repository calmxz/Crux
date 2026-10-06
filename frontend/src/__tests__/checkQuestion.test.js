import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import CheckQuestion from '../components/chat/CheckQuestion.vue'

/* global process */

function batch(overrides = {}) {
  return {
    gap: 'atp',
    total: 2,
    currentIndex: 0,
    viewIndex: 0,
    items: [
      {
        question: 'Q1',
        options: ['a', 'b'],
        status: 'pending',
        selectedIndex: null,
        correctIndex: null,
        correct: null,
        explanation: null,
      },
      {
        question: 'Q2',
        options: ['a', 'b'],
        status: 'pending',
        selectedIndex: null,
        correctIndex: null,
        correct: null,
        explanation: null,
      },
    ],
    ...overrides,
  }
}

describe('CheckQuestion batch', () => {
  it('shows N of M eyebrow when total > 1', () => {
    const w = mount(CheckQuestion, { props: { check: batch() } })
    expect(w.text()).toContain('1/2')
  })

  it('#340 Stop check emits stop while items remain', async () => {
    const w = mount(CheckQuestion, { props: { check: batch() } })
    await w.find('[data-testid="check-stop"]').trigger('click')
    expect(w.emitted('stop')).toHaveLength(1)
  })

  it('#340 Stop check is disabled during a stream', () => {
    const w = mount(CheckQuestion, { props: { check: batch(), busy: true } })
    expect(w.find('[data-testid="check-stop"]').attributes('disabled')).toBeDefined()
  })

  it('#340 Stop check is disabled while an answer is in flight', () => {
    const w = mount(CheckQuestion, { props: { check: batch(), answering: true } })
    expect(w.find('[data-testid="check-stop"]').attributes('disabled')).toBeDefined()
  })

  it('#340 Stop check is gone once every item is resolved (Done closes it)', () => {
    const done = batch({ currentIndex: 2, viewIndex: 1 })
    done.items = done.items.map((it) => ({ ...it, status: 'skipped' }))
    const w = mount(CheckQuestion, { props: { check: done } })
    expect(w.find('[data-testid="check-stop"]').exists()).toBe(false)
  })

  it('emits answer with the clicked option index', async () => {
    const w = mount(CheckQuestion, { props: { check: batch() } })
    await w.findAll('[data-testid="check-option"]')[1].trigger('click')
    expect(w.emitted('answer')[0]).toEqual([1])
  })

  it('R2: skip carries coarse-2x for a coarse-pointer two-pitch target', () => {
    const w = mount(CheckQuestion, { props: { check: batch() } })
    expect(w.find('[data-testid="check-skip"]').classes()).toContain('coarse-2x')
  })

  it('shows Next when an answered item is not the last', () => {
    const b = batch({ currentIndex: 1 })
    b.items[0] = {
      ...b.items[0],
      status: 'answered',
      selectedIndex: 0,
      correctIndex: 0,
      correct: true,
      explanation: 'a.',
    }
    const w = mount(CheckQuestion, { props: { check: b } })
    expect(w.find('[data-testid="check-next"]').exists()).toBe(true)
    expect(w.find('[data-testid="check-done"]').exists()).toBe(false)
  })

  it('shows Done on the last answered item', () => {
    const b = batch({
      total: 1,
      currentIndex: 1,
      viewIndex: 0,
      items: [
        {
          question: 'Q1',
          options: ['a', 'b'],
          status: 'answered',
          selectedIndex: 0,
          correctIndex: 0,
          correct: true,
          explanation: 'a.',
        },
      ],
    })

    const w = mount(CheckQuestion, { props: { check: b } })
    expect(w.find('[data-testid="check-done"]').exists()).toBe(true)
  })

  it('emits next / done', async () => {
    const b = batch({ currentIndex: 1 })
    b.items[0] = {
      ...b.items[0],
      status: 'answered',
      correct: true,
      correctIndex: 0,
      selectedIndex: 0,
      explanation: 'a.',
    }
    const w = mount(CheckQuestion, { props: { check: b } })
    await w.find('[data-testid="check-next"]').trigger('click')
    expect(w.emitted('next')).toBeTruthy()
  })

  // F-04: while a stream is live, Skip/Next/Done must be disabled so the
  // follow-up stream cannot be started on top of the active one.
  it('busy disables Skip and Done (F-04)', () => {
    const b = batch({
      total: 1,
      currentIndex: 1,
      viewIndex: 0,
      items: [
        {
          question: 'Q1',
          options: ['a', 'b'],
          status: 'answered',
          selectedIndex: 0,
          correctIndex: 0,
          correct: true,
          explanation: 'a.',
        },
      ],
    })

    const done = mount(CheckQuestion, { props: { check: b, busy: true } })
    expect(done.find('[data-testid="check-done"]').element.disabled).toBe(true)
    const pending = mount(CheckQuestion, { props: { check: batch(), busy: true } })
    expect(pending.find('[data-testid="check-skip"]').element.disabled).toBe(true)
  })
})

// #348: free navigation within one set. Next is always there before the last
// item, Back after the first; Done waits until every item is answered or
// skipped.
describe('CheckQuestion free navigation (#348)', () => {
  const answeredItem = (q) => ({
    question: q,
    options: ['a', 'b'],
    status: 'answered',
    selectedIndex: 0,
    correctIndex: 0,
    correct: true,
    explanation: 'a.',
  })

  const skippedItem = (q) => ({ ...answeredItem(q), status: 'skipped', correct: null })

  it('Next is shown and enabled on an unanswered, non-last item', async () => {
    const w = mount(CheckQuestion, { props: { check: batch() } })
    const next = w.get('[data-testid="check-next"]')
    expect(next.element.disabled).toBe(false)
    await next.trigger('click')
    expect(w.emitted('next')).toHaveLength(1)
  })

  it('Back is absent on the first item and emits back after it', async () => {
    const first = mount(CheckQuestion, { props: { check: batch() } })
    expect(first.find('[data-testid="check-back"]').exists()).toBe(false)
    const second = mount(CheckQuestion, { props: { check: batch({ viewIndex: 1 }) } })
    await second.get('[data-testid="check-back"]').trigger('click')
    expect(second.emitted('back')).toHaveLength(1)
  })

  it('Done is disabled on the last item while an earlier item is unanswered', () => {
    const b = batch({ viewIndex: 1 })
    b.items[1] = answeredItem('Q2')
    const w = mount(CheckQuestion, { props: { check: b } })
    expect(w.find('[data-testid="check-next"]').exists()).toBe(false)
    expect(w.get('[data-testid="check-done"]').element.disabled).toBe(true)
  })

  it('Done is disabled on an unanswered last item', () => {
    const w = mount(CheckQuestion, { props: { check: batch({ viewIndex: 1 }) } })
    expect(w.get('[data-testid="check-done"]').element.disabled).toBe(true)
  })

  it('a skipped item satisfies Done', async () => {
    const b = batch({ currentIndex: 2, viewIndex: 1 })
    b.items = [skippedItem('Q1'), answeredItem('Q2')]
    const w = mount(CheckQuestion, { props: { check: b } })
    const done = w.get('[data-testid="check-done"]')
    expect(done.element.disabled).toBe(false)
    await done.trigger('click')
    expect(w.emitted('done')).toHaveLength(1)
  })

  it('once every item is resolved, Done also shows on an earlier item', () => {
    const b = batch({ currentIndex: 2, viewIndex: 0 })
    b.items = [answeredItem('Q1'), answeredItem('Q2')]
    const w = mount(CheckQuestion, { props: { check: b } })
    expect(w.get('[data-testid="check-done"]').element.disabled).toBe(false)
    expect(w.find('[data-testid="check-next"]').exists()).toBe(true)
  })

  it('Skip stays an explicit action on an unanswered item', () => {
    const w = mount(CheckQuestion, { props: { check: batch({ viewIndex: 1 }) } })
    expect(w.find('[data-testid="check-skip"]').exists()).toBe(true)
  })

  it('busy disables Back and Next (F-04)', () => {
    const w = mount(CheckQuestion, {
      props: {
        check: batch({ viewIndex: 1, total: 3, items: [...batch().items, answeredItem('Q3')] }),
        busy: true,
      },
    })

    expect(w.get('[data-testid="check-back"]').element.disabled).toBe(true)
    expect(w.get('[data-testid="check-next"]').element.disabled).toBe(true)
  })

  it('moving the view onto an answered item does not steal focus', async () => {
    const b = batch({ viewIndex: 1 })
    b.items[0] = answeredItem('Q1')
    const w = mount(CheckQuestion, { props: { check: b }, attachTo: document.body })
    await w.setProps({ check: { ...b, viewIndex: 0 } })
    await nextTick()
    expect(document.activeElement).not.toBe(w.find('[data-testid="check-next"]').element)
    w.unmount()
  })

  it('answering the viewed item focuses Next', async () => {
    const b = batch()
    const w = mount(CheckQuestion, { props: { check: b }, attachTo: document.body })
    const items = [answeredItem('Q1'), b.items[1]]
    await w.setProps({ check: { ...b, items } })
    await nextTick()
    expect(document.activeElement).toBe(w.get('[data-testid="check-next"]').element)
    w.unmount()
  })
})

// Hidden-until-graded raise: the explanation is the reward for answering, so
// it must not be reachable in the DOM before the item is graded.
describe('CheckQuestion hidden-until-graded reveal', () => {
  it('does not render the explanation or a grading mark before answering', () => {
    const b = batch()
    b.items[0] = { ...b.items[0], explanation: 'Because X.' }
    const w = mount(CheckQuestion, { props: { check: b } })
    expect(w.find('[data-testid="check-explanation"]').exists()).toBe(false)
    expect(w.find('[data-testid="check-verdict"]').exists()).toBe(false)
    expect(w.find('.check-mark').exists()).toBe(false)
    expect(w.text()).not.toContain('Because X.')
  })

  it('reveals the explanation, the verdict and the drawn mark once graded', () => {
    const b = batch({ total: 1, currentIndex: 1, viewIndex: 0 })
    b.items = [
      {
        question: 'Q1',
        options: ['a', 'b'],
        status: 'answered',
        selectedIndex: 1,
        correctIndex: 0,
        correct: false,
        explanation: 'Because X.',
      },
    ]
    const w = mount(CheckQuestion, { props: { check: b } })
    expect(w.get('[data-testid="check-explanation"]').text()).toBe('Because X.')
    expect(w.get('[data-testid="check-verdict"]').text()).toBe('Not quite')
    const opts = w.findAll('[data-testid="check-option"]')
    expect(opts[0].classes()).toContain('is-correct')
    expect(opts[0].find('.check-mark--tick').exists()).toBe(true)
    expect(opts[1].classes()).toContain('is-incorrect')
    expect(opts[1].find('.check-mark--cross').exists()).toBe(true)
  })

  it('keeps the explanation hidden for a skipped item', () => {
    const b = batch({ total: 1, currentIndex: 1, viewIndex: 0 })
    b.items = [
      {
        question: 'Q1',
        options: ['a', 'b'],
        status: 'skipped',
        selectedIndex: null,
        correctIndex: 0,
        correct: null,
        explanation: 'Because X.',
      },
    ]
    const w = mount(CheckQuestion, { props: { check: b } })
    expect(w.find('[data-testid="check-explanation"]').exists()).toBe(false)
  })

  it('letters the options', () => {
    const w = mount(CheckQuestion, { props: { check: batch() } })
    const opts = w.findAll('[data-testid="check-option"]')
    expect(opts[0].get('.check-letter').text()).toBe('A.')
    expect(opts[1].get('.check-letter').text()).toBe('B.')
  })
})

describe('CheckQuestion accessibility (D-01)', () => {
  function mountUnanswered() {
    return mount(CheckQuestion, { props: { check: batch() } })
  }

  function mountAnswered({ correct = true, explanation = 'a.' } = {}) {
    const b = batch({
      total: 1,
      currentIndex: 1,
      viewIndex: 0,
      items: [
        {
          question: 'Q1',
          options: ['a', 'b'],
          status: 'answered',
          selectedIndex: 0,
          correctIndex: correct ? 0 : 1,
          correct,
          explanation,
        },
      ],
    })

    return mount(CheckQuestion, { props: { check: b } })
  }

  it('has an empty live region before answering', () => {
    const wrapper = mountUnanswered()
    const live = wrapper.find('[data-testid="check-live"]')
    expect(live.exists()).toBe(true)
    expect(live.attributes('role')).toBe('status')
    expect(live.attributes('aria-live')).toBe('polite')
    expect(live.attributes('aria-atomic')).toBe('true')
    expect(live.text()).toBe('')
  })

  it('announces verdict and explanation after answering', () => {
    const wrapper = mountAnswered({ correct: true, explanation: 'Because X.' })
    expect(wrapper.find('[data-testid="check-live"]').text()).toContain('Correct')
    expect(wrapper.find('[data-testid="check-live"]').text()).toContain('Because X.')
  })

  it('marks answered options aria-disabled instead of disabled', () => {
    const wrapper = mountAnswered({})
    const opt = wrapper.find('[data-testid="check-option"]')
    expect(opt.attributes('disabled')).toBeUndefined()
    expect(opt.attributes('aria-disabled')).toBe('true')
  })

  it('does not emit answer from an aria-disabled option', async () => {
    const wrapper = mountAnswered({})
    await wrapper.find('[data-testid="check-option"]').trigger('click')
    expect(wrapper.emitted('answer')).toBeUndefined()
  })
})

// #364: a check of M sets shows `set N of M` and a head rule cut into M
// segments. A single-set check keeps today's one solid rule and no set words.
describe('CheckQuestion set progress (#364)', () => {
  const segs = (w) => w.findAll('[data-testid="check-rule-seg"]')

  it.each([
    ['absent', {}],
    ['null', { setIndex: null, setTotal: null }],
    ['1 of 1', { setIndex: 1, setTotal: 1 }],
  ])('single-set (%s) renders unchanged', (_, sets) => {
    const w = mount(CheckQuestion, { props: { check: batch(sets) } })
    expect(w.find('.role-tag').text()).toBe('check')
    expect(w.text()).not.toMatch(/set \d/)
    expect(w.find('[data-testid="check-set-rule"]').exists()).toBe(false)
    expect(w.find('.check-gutter').classes()).not.toContain('is-segmented')
    expect(w.get('.check-progress').text()).toBe('1/2')
  })

  it('multi-set head line reads check · set N of M, count stays right', () => {
    const w = mount(CheckQuestion, { props: { check: batch({ setIndex: 2, setTotal: 3 }) } })
    expect(w.find('.role-tag').text().replace(/\s+/g, ' ')).toBe('check · set 2 of 3')
    expect(w.get('.check-progress').text()).toBe('1/2')
    expect(w.find('.check-gutter').classes()).toContain('is-segmented')
  })

  it('segment count equals set_total', () => {
    const w = mount(CheckQuestion, { props: { check: batch({ setIndex: 1, setTotal: 3 }) } })
    expect(segs(w)).toHaveLength(3)
  })

  it('done sets full, live set filled by resolved items, upcoming empty', () => {
    const b = batch({ setIndex: 2, setTotal: 3, currentIndex: 1 })
    b.items[0] = { ...b.items[0], status: 'answered', correct: true, correctIndex: 0 }
    const w = mount(CheckQuestion, { props: { check: b } })
    const [done, live, todo] = segs(w)
    expect(done.classes()).toContain('is-done')
    expect(live.classes()).toContain('is-live')
    expect(todo.classes()).toContain('is-todo')
    expect(done.attributes('data-fill')).toBe('1')
    expect(live.attributes('data-fill')).toBe('0.5')
    expect(todo.attributes('data-fill')).toBe('0')
  })

  it('live segment fills as answers land', async () => {
    const b = batch({ setIndex: 1, setTotal: 2 })
    const w = mount(CheckQuestion, { props: { check: b } })
    expect(segs(w)[0].attributes('data-fill')).toBe('0')
    const resolved = b.items.map((it) => ({ ...it, status: 'skipped' }))
    await w.setProps({ check: { ...b, currentIndex: 2, items: resolved } })
    expect(segs(w)[0].attributes('data-fill')).toBe('1')
  })

  it('#348 live segment counts a later item answered first', () => {
    const b = batch({ setIndex: 1, setTotal: 2, currentIndex: 0, viewIndex: 1 })
    b.items[1] = { ...b.items[1], status: 'answered', correct: true, correctIndex: 0 }
    const w = mount(CheckQuestion, { props: { check: b } })
    expect(segs(w)[0].attributes('data-fill')).toBe('0.5')
  })

  it('reduced motion drops the fill transition, so the final state shows', () => {
    const src = readFileSync(
      resolve(process.cwd(), 'src/components/chat/CheckQuestion.vue'),
      'utf8',
    )

    const block = src.match(/@media \(prefers-reduced-motion: reduce\) \{([\s\S]*?)\n\}/)
    expect(block).not.toBeNull()
    expect(block[1]).toMatch(/\.check-rule-seg::after\s*\{\s*transition:\s*none;/)
  })
})

// E-17: `answered` only flips once the POST returns, so the in-flight window
// accepted a second click that the store then dropped in silence.
describe('CheckQuestion answering window (E-17)', () => {
  it('marks the options aria-disabled and the group aria-busy while answering', () => {
    const w = mount(CheckQuestion, { props: { check: batch(), answering: true } })
    expect(w.find('.check-options').attributes('aria-busy')).toBe('true')
    const opt = w.find('[data-testid="check-option"]')
    expect(opt.attributes('aria-disabled')).toBe('true')
    // D-01 stands: still a real, focusable button.
    expect(opt.attributes('disabled')).toBeUndefined()
  })

  it('does not emit answer from a second click while answering', async () => {
    const w = mount(CheckQuestion, { props: { check: batch(), answering: true } })
    await w.findAll('[data-testid="check-option"]')[1].trigger('click')
    expect(w.emitted('answer')).toBeUndefined()
  })

  it('leaves the group idle and the options live when not answering', () => {
    const w = mount(CheckQuestion, { props: { check: batch() } })
    expect(w.find('.check-options').attributes('aria-busy')).toBeUndefined()
    expect(w.find('[data-testid="check-option"]').attributes('aria-disabled')).toBeUndefined()
  })
})
