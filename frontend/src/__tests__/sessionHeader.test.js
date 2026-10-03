import { enableAutoUnmount, flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import SessionHeader from '../components/chat/SessionHeader.vue'

// The seam: the header calls the shared session actions (ticket 08). Mocked
// here so the test asserts which shared handler each button reaches.
const actions = {
  busy: ref(false),
  confirmEnd: vi.fn(),
  endSession: vi.fn(),
  resume: vi.fn(),
  continueTopic: vi.fn(),
  setPinned: vi.fn(),
  rename: vi.fn(() => Promise.resolve(true)),
}

vi.mock('@/composables/useSessionActions.js', () => ({
  useSessionActions: () => actions,
}))

const baseSession = {
  id: 's1',
  topic: 'Glycolysis pathway',
  created_at: '2026-09-20T10:00:00Z',
  pinned: false,
  ended_at: null,
}

const mountHeader = (props = {}) =>
  mount(SessionHeader, {
    props: { session: { ...baseSession }, ...props },
    attachTo: document.body,
    global: { stubs: { RouterLink: RouterLinkStub } },
  })

enableAutoUnmount(afterEach)

describe('SessionHeader', () => {
  beforeEach(() => {
    for (const k of [
      'confirmEnd',
      'endSession',
      'resume',
      'continueTopic',
      'setPinned',
      'rename',
    ]) {
      actions[k].mockClear()
    }

    actions.busy.value = false
  })

  it('renders the topic text', () => {
    const wrapper = mountHeader()
    expect(wrapper.text()).toContain('Glycolysis pathway')
  })

  it('links the title to the session profile page', () => {
    const wrapper = mountHeader()
    const link = wrapper.findComponent(RouterLinkStub)
    expect(link.exists()).toBe(true)
    expect(link.props('to')).toBe('/session/s1/profile')
    expect(link.text()).toContain('Glycolysis pathway')
    expect(link.attributes('data-testid')).toBe('session-topic-link')
    expect(link.attributes('title')).toContain('open session profile')
  })

  it('renders the level word and the started line', () => {
    const wrapper = mountHeader({ level: 'intermediate' })
    expect(wrapper.find('.session-level').text()).toContain('intermediate')
    expect(wrapper.find('.session-started').text()).toMatch(/^started /)
  })

  it('shows "level not set" when no level is given', () => {
    const wrapper = mountHeader()
    expect(wrapper.find('.session-level').text()).toContain('level not set')
  })

  it('renders nothing when there is no session or no topic', () => {
    expect(mountHeader({ session: null }).find('[data-testid="session-header"]').exists()).toBe(
      false,
    )
    const empty = mountHeader({ session: { ...baseSession, topic: '' } })
    expect(empty.find('[data-testid="session-header"]').exists()).toBe(false)
  })

  it('renders Rename, Pin and End with accessible names and tooltips', () => {
    const wrapper = mountHeader()
    const rename = wrapper.find('[data-testid="session-action-rename"]')
    const pin = wrapper.find('[data-testid="session-action-pin"]')
    const end = wrapper.find('[data-testid="session-action-end"]')
    expect(rename.attributes('aria-label')).toBe('Rename session')
    expect(rename.attributes('title')).toBe('Rename')
    expect(pin.attributes('aria-label')).toBe('Pin session')
    expect(pin.attributes('title')).toBe('Pin')
    expect(end.attributes('aria-label')).toBe('End session')
    expect(end.attributes('title')).toBe('End session')
    expect(wrapper.find('[data-testid="session-action-resume"]').exists()).toBe(false)
  })

  it('shows Resume instead of End on an ended session', () => {
    const wrapper = mountHeader({
      session: { ...baseSession, ended_at: '2026-09-21T10:00:00Z' },
    })

    expect(wrapper.find('[data-testid="session-action-end"]').exists()).toBe(false)
    const resume = wrapper.find('[data-testid="session-action-resume"]')
    expect(resume.exists()).toBe(true)
    expect(resume.attributes('aria-label')).toBe('Resume session')
  })

  it('flips the Pin label when the session is pinned', () => {
    const wrapper = mountHeader({ session: { ...baseSession, pinned: true } })
    const pin = wrapper.find('[data-testid="session-action-pin"]')
    expect(pin.attributes('aria-label')).toBe('Unpin session')
    expect(pin.attributes('title')).toBe('Unpin')
  })

  it('Pin calls the shared setPinned with the next state', async () => {
    const wrapper = mountHeader()
    await wrapper.find('[data-testid="session-action-pin"]').trigger('click')
    expect(actions.setPinned).toHaveBeenCalledWith(expect.objectContaining({ id: 's1' }), true)

    const pinned = mountHeader({ session: { ...baseSession, pinned: true } })
    await pinned.find('[data-testid="session-action-pin"]').trigger('click')
    expect(actions.setPinned).toHaveBeenLastCalledWith(expect.objectContaining({ id: 's1' }), false)
  })

  it('End calls the shared confirmEnd', async () => {
    const wrapper = mountHeader()
    await wrapper.find('[data-testid="session-action-end"]').trigger('click')
    expect(actions.confirmEnd).toHaveBeenCalledWith(expect.objectContaining({ id: 's1' }))
  })

  it('Resume calls the shared resume', async () => {
    const wrapper = mountHeader({
      session: { ...baseSession, ended_at: '2026-09-21T10:00:00Z' },
    })

    await wrapper.find('[data-testid="session-action-resume"]').trigger('click')
    expect(actions.resume).toHaveBeenCalledWith(expect.objectContaining({ id: 's1' }))
  })

  it('Rename shows the inline field in place of the topic; Enter commits the trimmed value', async () => {
    const wrapper = mountHeader()
    await wrapper.find('[data-testid="session-action-rename"]').trigger('click')
    await flushPromises()
    const input = wrapper.find('[data-testid="session-rename-input"]')
    expect(input.exists()).toBe(true)
    expect(wrapper.find('[data-testid="session-topic-link"]').exists()).toBe(false)
    // Captured before the input unmounts: a stray native blur firing after
    // Enter already committed must not fire a second rename (commitRename's
    // `if (!renaming.value) return` guard).
    const el = input.element
    await input.setValue('  Krebs cycle  ')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    el.dispatchEvent(new Event('blur'))
    await flushPromises()
    expect(actions.rename).toHaveBeenCalledTimes(1)
    expect(actions.rename).toHaveBeenCalledWith(
      expect.objectContaining({ id: 's1' }),
      'Krebs cycle',
    )
    expect(wrapper.find('[data-testid="session-rename-input"]').exists()).toBe(false)
    expect(document.activeElement).toBe(
      wrapper.find('[data-testid="session-action-rename"]').element,
    )
  })

  it('Escape cancels the rename without calling the shared handler', async () => {
    const wrapper = mountHeader()
    await wrapper.find('[data-testid="session-action-rename"]').trigger('click')
    await flushPromises()
    const input = wrapper.find('[data-testid="session-rename-input"]')
    // Same guard as the Enter case: a stray blur after Escape already
    // cancelled must not resurrect a commit.
    const el = input.element
    await input.setValue('Something else')
    await input.trigger('keydown', { key: 'Escape' })
    await flushPromises()
    el.dispatchEvent(new Event('blur'))
    await flushPromises()
    expect(actions.rename).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="session-rename-input"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="session-topic-link"]').exists()).toBe(true)
  })

  it('switching sessions mid-rename cancels the rename without committing', async () => {
    const wrapper = mountHeader()
    await wrapper.find('[data-testid="session-action-rename"]').trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="session-rename-input"]').setValue('half-typed')
    await wrapper.setProps({ session: { ...baseSession, id: 's2', topic: 'Other topic' } })
    await flushPromises()
    expect(actions.rename).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="session-rename-input"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="session-topic-link"]').text()).toContain('Other topic')
  })

  it('blur commits the rename', async () => {
    const wrapper = mountHeader()
    await wrapper.find('[data-testid="session-action-rename"]').trigger('click')
    await flushPromises()
    const input = wrapper.find('[data-testid="session-rename-input"]')
    await input.setValue('Krebs cycle')
    await input.trigger('blur')
    await flushPromises()
    expect(actions.rename).toHaveBeenCalledWith(
      expect.objectContaining({ id: 's1' }),
      'Krebs cycle',
    )
  })

  it('renders the reference status dot only when refStatus is set', () => {
    expect(mountHeader().find('[data-testid="session-ref-status"]').exists()).toBe(false)

    for (const state of ['processing', 'ready', 'failed']) {
      const dot = mountHeader({ refStatus: state }).find('[data-testid="session-ref-status"]')
      expect(dot.exists()).toBe(true)
      expect(dot.attributes('title')).toBe(`Reference files: ${state}`)
      expect(dot.find('.sr-only').text()).toBe(`Reference files: ${state}`)
    }
  })

  it('the four action buttons carry hit-44', () => {
    const wrapper = mountHeader()
    expect(wrapper.find('[data-testid="session-action-rename"]').classes()).toContain('hit-44')
    expect(wrapper.find('[data-testid="session-action-pin"]').classes()).toContain('hit-44')
    expect(wrapper.find('[data-testid="session-action-end"]').classes()).toContain('hit-44')
    const resume = mountHeader({ session: { ...baseSession, ended_at: '2026-09-21T10:00:00Z' } })
    expect(resume.find('[data-testid="session-action-resume"]').classes()).toContain('hit-44')
  })

  it('End is disabled while the tutor stream is active, independent of busy', async () => {
    const wrapper = mountHeader({ streaming: true })
    expect(wrapper.find('[data-testid="session-action-end"]').attributes('disabled')).toBeDefined()
    // title/aria-label stay the disable reason-agnostic copy.
    expect(wrapper.find('[data-testid="session-action-end"]').attributes('title')).toBe(
      'End session',
    )
    expect(wrapper.find('[data-testid="session-action-end"]').attributes('aria-label')).toBe(
      'End session',
    )
  })

  it('focus follows the End/Resume swap when the outgoing button had focus', async () => {
    const wrapper = mountHeader()
    wrapper.find('[data-testid="session-action-end"]').element.focus()
    await wrapper.setProps({ session: { ...baseSession, ended_at: '2026-09-21T10:00:00Z' } })
    await flushPromises()
    expect(document.activeElement).toBe(
      wrapper.find('[data-testid="session-action-resume"]').element,
    )

    await wrapper.setProps({ session: { ...baseSession, ended_at: null } })
    await flushPromises()
    expect(document.activeElement).toBe(wrapper.find('[data-testid="session-action-end"]').element)
  })

  it('does not steal focus on an ended_at flip that did not originate from End/Resume', async () => {
    // Mirrors E-11: a send fails elsewhere (e.g. because the composer's focus
    // is on the input, not the header) and the session flips to ended out of
    // band. The header must not yank focus away from whatever the user was
    // doing.
    const wrapper = mountHeader()
    document.body.focus()
    expect(document.activeElement).toBe(document.body)
    await wrapper.setProps({ session: { ...baseSession, ended_at: '2026-09-21T10:00:00Z' } })
    await flushPromises()
    expect(document.activeElement).toBe(document.body)
  })
})
