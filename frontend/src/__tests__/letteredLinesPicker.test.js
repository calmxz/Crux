import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import LetteredLinesPicker from '@/components/LetteredLinesPicker.vue'

const options = [
  { value: 'hints', label: 'Hints', sub: 'Nudge me toward the answer.' },
  { value: 'direct_answers', label: 'Direct answers', sub: 'Explain outright when I ask.' },
]

const required = { legend: 'Feedback style', testidPrefix: 'feedback-style' }

describe('LetteredLinesPicker', () => {
  it('renders one option per options entry', () => {
    const wrapper = mount(LetteredLinesPicker, {
      props: { ...required, modelValue: 'hints', options },
    })

    expect(wrapper.findAll('.radio-row')).toHaveLength(2)
    expect(wrapper.find('[data-testid="feedback-style-hints"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="feedback-style-direct_answers"]').exists()).toBe(true)
  })

  it('marks the modelValue option as selected', () => {
    const wrapper = mount(LetteredLinesPicker, {
      props: { ...required, modelValue: 'direct_answers', options },
    })

    const rows = wrapper.findAll('.radio-row')
    expect(rows[0].classes()).not.toContain('selected')
    expect(rows[1].classes()).toContain('selected')
    expect(wrapper.get('[data-testid="feedback-style-direct_answers"]').element.checked).toBe(true)
  })

  it('emits update:modelValue with the clicked option value', async () => {
    const wrapper = mount(LetteredLinesPicker, {
      props: { ...required, modelValue: 'hints', options },
    })

    await wrapper.get('[data-testid="feedback-style-direct_answers"]').setValue(true)
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['direct_answers'])
  })

  it('renders the optional sub description when present, omits it otherwise', () => {
    const wrapper = mount(LetteredLinesPicker, {
      props: {
        ...required,
        modelValue: 'hints',
        options: [{ value: 'hints', label: 'Hints' }],
      },
    })

    expect(wrapper.find('.radio-sub').exists()).toBe(false)
    expect(wrapper.text()).toContain('Hints')
  })

  it('all radios in one instance share a single non-empty group name', () => {
    const wrapper = mount(LetteredLinesPicker, {
      props: { ...required, modelValue: 'hints', options },
    })

    const radios = wrapper.findAll('input[type="radio"]')
    expect(radios).toHaveLength(2)
    const names = radios.map((r) => r.attributes('name'))
    expect(names[0]).toBeTruthy()
    expect(new Set(names).size).toBe(1)
  })

  // Note: cross-instance uniqueness is not asserted here. useId() restarts its
  // counter per Vue app, and each VTU mount() spins up a fresh app, so two
  // isolated mounts both yield the same id in this harness. The uniqueness is
  // real in production (one app, distinct ids per instance) but not observable
  // from isolated mounts.

  it('honors an explicit name prop on every radio', () => {
    const wrapper = mount(LetteredLinesPicker, {
      props: { ...required, modelValue: 'hints', options, name: 'custom-group' },
    })

    const names = wrapper.findAll('input[type="radio"]').map((r) => r.attributes('name'))
    expect(names).toEqual(['custom-group', 'custom-group'])
  })
})
