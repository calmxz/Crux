import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import LearningTab from '@/components/settings/LearningTab.vue'
import { useUserStore } from '@/stores/user.js'
import * as profileApi from '@/services/profileApi.js'

const showSuccess = vi.fn()

const showError = vi.fn()

vi.mock('@/composables/useToast.js', () => ({
  useToast: () => ({ showSuccess, showError, showWarn: vi.fn() }),
}))

function seedUser(prefs = { feedback: 'hints', checkIns: 'sometimes', replyLength: 'balanced' }) {
  const user = useUserStore()
  user.userId = 'u_test'
  user.name = 'Eddy'
  user.interactionPreferences = prefs
  user.onboardingComplete = true

  return user
}

// One entry per control, in the order the issue (#357) fixes: the section
// test id, the picker's radio test-id prefix, the store field, a value that
// differs from the seeded one, and a second value to change to afterwards.
const CONTROLS = [
  {
    section: 'learning-feedback',
    prefix: 'feedback-style',
    field: 'feedback',
    next: 'direct_answers',
    other: 'hints',
    flash: 'learning-feedback-saved',
  },
  {
    section: 'learning-check-ins',
    prefix: 'check-ins',
    field: 'checkIns',
    next: 'often',
    other: 'only_when_asked',
    flash: 'learning-check-ins-saved',
  },
  {
    section: 'learning-reply-length',
    prefix: 'reply-length',
    field: 'replyLength',
    next: 'thorough',
    other: 'brief',
    flash: 'learning-reply-length-saved',
  },
]

describe('LearningTab', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    showSuccess.mockClear()
    showError.mockClear()
  })

  // #350: the aggregate profile stays in profileApi.js for the /profile page
  // (#358) but is no longer read here.
  it('renders the three preference sections in order and no analytics', async () => {
    seedUser()
    const spy = vi.spyOn(profileApi, 'getAggregateProfile').mockResolvedValue({})

    const wrapper = mount(LearningTab)
    await flushPromises()

    const sections = wrapper.findAll('section').map((s) => s.attributes('data-testid'))
    expect(sections).toEqual(CONTROLS.map((c) => c.section))
    expect(wrapper.findAll('.sec-title').map((t) => t.text())).toEqual([
      'Feedback style',
      'Check-ins',
      'Reply length',
    ])

    for (const id of ['learning-topics', 'learning-weekly', 'learning-accuracy', 'agg-loading']) {
      expect(wrapper.find(`[data-testid="${id}"]`).exists()).toBe(false)
    }

    expect(spy).not.toHaveBeenCalled()
  })

  it('offers the issue copy for each control', async () => {
    seedUser()
    const wrapper = mount(LearningTab)
    await flushPromises()

    const feedback = wrapper.get('[data-testid="learning-feedback"]').text()
    expect(feedback).toContain('Hints')
    expect(feedback).toContain('Nudge me toward the answer.')
    expect(feedback).toContain('Direct answers')
    expect(feedback).toContain('Explain outright when I ask.')

    const checkIns = wrapper.get('[data-testid="learning-check-ins"]')
    expect(checkIns.findAll('.radio-label').map((l) => l.text())).toEqual([
      'Often',
      'Sometimes',
      'Only when I ask',
    ])
    expect(checkIns.get('[data-testid="learning-check-ins-help"]').text()).toMatch(/quick check/)

    const reply = wrapper.get('[data-testid="learning-reply-length"]')
    expect(reply.findAll('.radio-label').map((l) => l.text())).toEqual([
      'Brief',
      'Balanced',
      'Thorough',
    ])
  })

  it('reflects the stored preferences, falling back to the server defaults', async () => {
    seedUser({ feedback: 'direct_answers' })
    const wrapper = mount(LearningTab)
    await flushPromises()

    expect(wrapper.get('[data-testid="feedback-style-direct_answers"]').element.checked).toBe(true)
    expect(wrapper.get('[data-testid="check-ins-sometimes"]').element.checked).toBe(true)
    expect(wrapper.get('[data-testid="reply-length-balanced"]').element.checked).toBe(true)
  })

  // The router runs hydrateFromServer in the background, so the tab can mount
  // on a stale local snapshot; it must follow the store when /me lands.
  it('follows the store when a background hydrate lands after mount', async () => {
    const user = seedUser()
    const wrapper = mount(LearningTab)
    await flushPromises()

    user.interactionPreferences = {
      feedback: 'direct_answers',
      checkIns: 'often',
      replyLength: 'brief',
    }
    await flushPromises()

    expect(wrapper.get('[data-testid="feedback-style-direct_answers"]').element.checked).toBe(true)
    expect(wrapper.get('[data-testid="check-ins-often"]').element.checked).toBe(true)
    expect(wrapper.get('[data-testid="reply-length-brief"]').element.checked).toBe(true)
  })

  it('a hydrate landing mid-save does not undo the pending choice', async () => {
    const user = seedUser()
    let resolveSave
    vi.spyOn(user, 'updateProfile').mockReturnValue(
      new Promise((resolve) => {
        resolveSave = resolve
      }),
    )
    const wrapper = mount(LearningTab)
    await flushPromises()
    await wrapper.get('[data-testid="check-ins-often"]').setValue(true)

    user.interactionPreferences = { ...user.interactionPreferences, replyLength: 'thorough' }
    await flushPromises()
    expect(wrapper.get('[data-testid="check-ins-often"]').element.checked).toBe(true)
    expect(wrapper.get('[data-testid="reply-length-thorough"]').element.checked).toBe(true)

    resolveSave()
    await flushPromises()
  })

  it('has no save button: changes autosave', async () => {
    seedUser()
    const wrapper = mount(LearningTab)
    await flushPromises()

    expect(wrapper.find('[data-testid="learning-feedback-save"]').exists()).toBe(false)
    expect(wrapper.find('button').exists()).toBe(false)
  })

  for (const c of CONTROLS) {
    describe(`${c.section}`, () => {
      it('one change sends one updateProfile call carrying only that field', async () => {
        const user = seedUser()
        const updateSpy = vi.spyOn(user, 'updateProfile').mockResolvedValue()

        const wrapper = mount(LearningTab)
        await flushPromises()
        await wrapper.get(`[data-testid="${c.prefix}-${c.next}"]`).setValue(true)
        await flushPromises()

        expect(updateSpy).toHaveBeenCalledExactlyOnceWith({ [c.field]: c.next })
        expect(showSuccess).not.toHaveBeenCalled()
      })

      it('flashes Saved. inline until that control changes again', async () => {
        const user = seedUser()
        let resolveSecond
        vi.spyOn(user, 'updateProfile')
          .mockResolvedValueOnce()
          .mockReturnValueOnce(
            new Promise((resolve) => {
              resolveSecond = resolve
            }),
          )

        const wrapper = mount(LearningTab)
        await flushPromises()
        await wrapper.get(`[data-testid="${c.prefix}-${c.next}"]`).setValue(true)
        await flushPromises()

        const section = wrapper.get(`[data-testid="${c.section}"]`)
        const flash = section.get(`[data-testid="${c.flash}"]`)
        expect(flash.text()).toBe('Saved.')
        expect(flash.attributes('role')).toBe('status')
        expect(flash.find('svg.tick').exists()).toBe(true)
        // Only the control that saved shows the flash.
        expect(wrapper.findAll('.saved-flash')).toHaveLength(1)

        await wrapper.get(`[data-testid="${c.prefix}-${c.other}"]`).setValue(true)
        expect(wrapper.find(`[data-testid="${c.flash}"]`).exists()).toBe(false)

        resolveSecond()
        await flushPromises()
        expect(wrapper.find(`[data-testid="${c.flash}"]`).exists()).toBe(true)
      })

      it('a failed save reverts the choice and shows the error', async () => {
        const user = seedUser()
        const before = user.interactionPreferences[c.field]
        vi.spyOn(user, 'updateProfile').mockRejectedValue(new Error('boom'))

        const wrapper = mount(LearningTab)
        await flushPromises()
        await wrapper.get(`[data-testid="${c.prefix}-${c.next}"]`).setValue(true)
        await flushPromises()

        expect(showError).toHaveBeenCalledOnce()
        expect(wrapper.find(`[data-testid="${c.flash}"]`).exists()).toBe(false)
        expect(wrapper.get(`[data-testid="${c.prefix}-${before}"]`).element.checked).toBe(true)
        expect(wrapper.get(`[data-testid="${c.prefix}-${c.next}"]`).element.checked).toBe(false)
      })
    })
  }

  // Two quick changes to one control must reach the server in order, so the
  // later choice is the one that sticks.
  it('serialises rapid changes so the last choice is written last', async () => {
    const user = seedUser()
    const calls = []
    let resolveFirst
    vi.spyOn(user, 'updateProfile').mockImplementation((body) => {
      calls.push(body)

      if (calls.length === 1) {
        return new Promise((resolve) => {
          resolveFirst = resolve
        })
      }

      return Promise.resolve()
    })

    const wrapper = mount(LearningTab)
    await flushPromises()
    await wrapper.get('[data-testid="reply-length-brief"]').setValue(true)
    await wrapper.get('[data-testid="reply-length-thorough"]').setValue(true)
    await flushPromises()
    expect(calls).toEqual([{ replyLength: 'brief' }])

    resolveFirst()
    await flushPromises()
    expect(calls).toEqual([{ replyLength: 'brief' }, { replyLength: 'thorough' }])
    expect(wrapper.get('[data-testid="reply-length-thorough"]').element.checked).toBe(true)
    expect(wrapper.find('[data-testid="learning-reply-length-saved"]').exists()).toBe(true)
  })

  it('does not render the usage panel (usage moved to its own tab)', async () => {
    seedUser()

    const wrapper = mount(LearningTab)
    await flushPromises()

    expect(wrapper.find('[data-testid="usage-panel"]').exists()).toBe(false)
  })
})
