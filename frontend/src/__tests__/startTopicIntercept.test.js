import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

import StartTopicIntercept from '@/components/start/StartTopicIntercept.vue'

const activeMatch = {
  session_id: 'a1',
  title: 'CSS',
  ended_at: null,
  gap_count: 0,
  knowledge_level: null,
}

const endedMatch = {
  session_id: 'e1',
  title: 'CSS',
  ended_at: '2026-07-01T00:00:00Z',
  gap_count: 3,
  knowledge_level: 'intermediate',
}

function mountActive(opts = {}) {
  const { attachTo, ...rest } = opts
  const mountOptions = { props: { match: activeMatch, kind: 'active', ...rest.props } }

  if (attachTo) mountOptions.attachTo = attachTo

  return mount(StartTopicIntercept, mountOptions)
}

describe('StartTopicIntercept', () => {
  it('active kind offers open-existing and start-fresh', async () => {
    const w = mount(StartTopicIntercept, { props: { match: activeMatch, kind: 'active' } })
    expect(w.find('[data-testid="intercept-continue"]').exists()).toBe(false)
    await w.get('[data-testid="intercept-open-existing"]').trigger('click')
    await w.get('[data-testid="intercept-fresh"]').trigger('click')
    expect(w.emitted('open-existing')).toHaveLength(1)
    expect(w.emitted('start-fresh')).toHaveLength(1)
  })

  it('ended kind offers continue and start-fresh, shows gap count', async () => {
    const w = mount(StartTopicIntercept, { props: { match: endedMatch, kind: 'ended' } })
    expect(w.find('[data-testid="intercept-open-existing"]').exists()).toBe(false)
    expect(w.text()).toContain('3 gaps open')
    await w.get('[data-testid="intercept-continue"]').trigger('click')
    expect(w.emitted('continue-topic')).toHaveLength(1)
  })

  it('ended kind with zero gaps hides gap copy', () => {
    const w = mount(StartTopicIntercept, {
      props: { match: { ...endedMatch, gap_count: 0 }, kind: 'ended' },
    })

    expect(w.text()).not.toContain('gaps open')
  })

  it('emits cancel', async () => {
    const w = mount(StartTopicIntercept, { props: { match: activeMatch, kind: 'active' } })
    await w.get('[data-testid="intercept-cancel"]').trigger('click')
    expect(w.emitted('cancel')).toHaveLength(1)
  })

  it('is a polite live region', () => {
    const wrapper = mountActive()
    const root = wrapper.find('[data-testid="start-intercept"]')
    expect(root.attributes('role')).toBe('status')
    expect(root.attributes('aria-live')).toBe('polite')
  })

  it('focuses the primary action on mount', async () => {
    const wrapper = mountActive({ attachTo: document.body })
    await nextTick()
    await nextTick()
    expect(document.activeElement?.dataset?.testid).toBe('intercept-open-existing')
    wrapper.unmount()
  })
})
