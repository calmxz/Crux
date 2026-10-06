import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import SessionEndedBanner from '@/components/SessionEndedBanner.vue'

afterEach(() => vi.useRealTimers())

describe('SessionEndedBanner', () => {
  it('uses relative time and completion copy', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-09-10T00:00:00Z'))
    const w = mount(SessionEndedBanner, { props: { endedAt: '2026-08-20T00:00:00Z' } })
    const text = w.text()
    expect(text).toMatch(/Session ended \d+ (weeks|months) ago/)
    expect(text).not.toContain('GMT')
    expect(text).not.toContain('Read-only')
    expect(text).toContain('Continue the topic in a new session')
  })

  it('emits resume and resume-gaps', async () => {
    const w = mount(SessionEndedBanner, {
      props: { endedAt: '2026-07-30T03:45:00Z', hasGaps: true },
    })

    await w.get('[data-testid="session-resume"]').trigger('click')
    await w.get('[data-testid="session-resume-gaps"]').trigger('click')
    expect(w.emitted('resume')).toHaveLength(1)
    expect(w.emitted('resume-gaps')).toHaveLength(1)
  })
})
