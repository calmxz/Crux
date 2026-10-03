import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

import BackButton from '@/components/BackButton.vue'
import SessionEndedBanner from '@/components/SessionEndedBanner.vue'

const back = vi.fn()

const push = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ back, push }),
}))

describe('BackButton', () => {
  beforeEach(() => {
    back.mockClear()
    push.mockClear()
  })

  it('renders provided label', () => {
    const wrapper = mount(BackButton, { props: { label: 'Sessions' } })
    expect(wrapper.text()).toContain('Sessions')
  })

  it('calls router.back when history has a back entry', async () => {
    Object.defineProperty(window, 'history', {
      value: { length: 5, state: { back: '/x' } },
      configurable: true,
    })
    const wrapper = mount(BackButton, { props: { label: 'Back', fallback: '/' } })
    await wrapper.get('[data-testid="back-button"]').trigger('click')
    expect(back).toHaveBeenCalledOnce()
    expect(push).not.toHaveBeenCalled()
  })

  it('falls back to router.push when history has no back entry', async () => {
    Object.defineProperty(window, 'history', {
      value: { length: 1, state: null },
      configurable: true,
    })
    const wrapper = mount(BackButton, { props: { label: 'Back', fallback: '/home' } })
    await wrapper.get('[data-testid="back-button"]').trigger('click')
    expect(push).toHaveBeenCalledWith('/home')
    expect(back).not.toHaveBeenCalled()
  })
})

describe('SessionEndedBanner', () => {
  const stubs = {
    Button: {
      props: ['loading', 'label'],
      template:
        '<button :disabled="loading" @click="$emit(\'click\')"><slot>{{ label }}</slot></button>',
    },
  }

  it('renders the relative ended-at time and completion sub copy', () => {
    const wrapper = mount(SessionEndedBanner, {
      props: { endedAt: '2026-01-01T00:00:00Z' },
      global: { stubs },
    })

    // Relative-time wording is covered under fake timers in sessionEndedBanner.test.js.
    expect(wrapper.text()).toContain('Session ended')
    expect(wrapper.text()).toContain('Continue the topic in a new session')
  })

  it('emits resume on button click', async () => {
    const wrapper = mount(SessionEndedBanner, {
      props: { endedAt: '2026-01-01T00:00:00Z' },
      global: { stubs },
    })

    await wrapper.get('[data-testid="session-resume"]').trigger('click')
    expect(wrapper.emitted('resume')?.length).toBeGreaterThan(0)
  })

  it('shows Review my gaps button only when hasGaps is true', () => {
    const withGaps = mount(SessionEndedBanner, {
      props: { endedAt: '2026-07-04T00:00:00Z', hasGaps: true },
      global: { stubs },
    })

    expect(withGaps.find('[data-testid="session-resume-gaps"]').exists()).toBe(true)

    const noGaps = mount(SessionEndedBanner, {
      props: { endedAt: '2026-07-04T00:00:00Z', hasGaps: false },
      global: { stubs },
    })

    expect(noGaps.find('[data-testid="session-resume-gaps"]').exists()).toBe(false)
  })

  it('emits resume-gaps when the gaps button is clicked', async () => {
    const w = mount(SessionEndedBanner, {
      props: { endedAt: '2026-07-04T00:00:00Z', hasGaps: true },
      global: { stubs },
    })

    await w.find('[data-testid="session-resume-gaps"]').trigger('click')
    expect(w.emitted('resume-gaps')).toBeTruthy()
  })
})
