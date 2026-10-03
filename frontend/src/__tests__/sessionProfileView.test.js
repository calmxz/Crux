import { describe, it, expect, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import ProfileView from '@/views/ProfileView.vue'
import { TICK_PATH } from '@/components/chat/levelMark.js'
import * as profileApi from '@/services/profileApi.js'

const routerPushMock = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPushMock }),
}))

// E-08: the remove controls now ask first. Capture the confirm config so a
// test can drive accept/reject deterministically instead of rendering the
// PrimeVue dialog.
let lastConfirm = null

vi.mock('primevue/useconfirm', () => ({
  useConfirm: () => ({
    require: (cfg) => {
      lastConfirm = cfg
    },
  }),
}))

const stubs = {
  RouterLink: { template: '<a><slot /></a>', props: ['to'] },
  BackButton: { template: '<button />', props: ['label', 'fallback'] },
  teleport: true,
  Dialog: {
    props: ['visible'],
    emits: ['update:visible'],
    template: '<div v-if="visible" data-testid="dialog"><slot /></div>',
  },
}

describe('SessionProfileView (per-session)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    routerPushMock.mockClear()
    lastConfirm = null
  })

  it('renders mastered, gaps, focus, and learning events', async () => {
    vi.spyOn(profileApi, 'getSessionProfile').mockResolvedValue({
      profile: {
        knowledge_level: 'beginner',
        confirmed_gaps: [{ name: 'window-fns', evidence_type: null, last_event_at: null }],
        mastered_concepts: [
          { name: 'joins', evidence_type: 'tested', last_event_at: null },
          { name: 'select', evidence_type: 'declared', last_event_at: null },
        ],
        subtopic_levels: {},
        focus_target_gap: 'window-fns',
        last_session_summary: 'Covered joins and selects.',
      },
      recent_learning_events: [
        {
          id: 1,
          session_id: 's1',
          gap_tested: 'joins',
          question: 'Inner vs outer?',
          correct: true,
          created_at: new Date().toISOString(),
        },
      ],
    })

    const wrapper = mount(ProfileView, {
      props: { id: 's1' },
      global: { stubs },
    })

    await flushPromises()

    const mastered = wrapper.find('[data-testid="sprof-mastered"]').text()
    expect(mastered).toContain('joins')
    expect(mastered).toContain('select')
    expect(wrapper.find('[data-testid="sprof-gaps"]').text()).toContain('window-fns')
    expect(wrapper.find('[data-testid="sprof-focus"]').text()).toContain('window-fns')
    expect(wrapper.find('[data-testid="sprof-summary"]').text()).toContain('Covered joins')
    expect(wrapper.find('[data-testid="sprof-events"]').text()).toContain('Inner vs outer')
  })

  // F-53: last_session_summary may carry the "[auto] " fallback prefix from
  // an auto-generated (no-LLM) recap; strip it before display.
  it('strips the [auto] prefix from the session summary', async () => {
    vi.spyOn(profileApi, 'getSessionProfile').mockResolvedValue({
      profile: {
        knowledge_level: 'beginner',
        confirmed_gaps: [],
        mastered_concepts: [],
        subtopic_levels: {},
        last_session_summary: '[auto] recap text',
      },
      recent_learning_events: [],
    })

    const wrapper = mount(ProfileView, {
      props: { id: 's1' },
      global: { stubs },
    })

    await flushPromises()

    const summary = wrapper.find('[data-testid="sprof-summary"]')
    expect(summary.text()).toContain('recap text')
    expect(summary.text()).not.toContain('[auto]')
  })

  it('renders concept names with evidence badges', async () => {
    vi.spyOn(profileApi, 'getSessionProfile').mockResolvedValue({
      profile: {
        knowledge_level: 'beginner',
        mastered_concepts: [
          { name: 'x', evidence_type: 'tested', last_event_at: '2026-07-01T00:00:00Z' },
        ],
        confirmed_gaps: [
          { name: 'y', evidence_type: null, last_event_at: null },
          { name: 'z', evidence_type: 'declared', last_event_at: null },
        ],
        subtopic_levels: {},
      },
      recent_learning_events: [],
    })

    const wrapper = mount(ProfileView, {
      props: { id: 's1' },
      global: { stubs },
    })

    await flushPromises()

    const chips = wrapper.findAll('[data-testid="sprof-mastered"] .chip')
    expect(chips[0].text()).toContain('x')
    expect(chips[0].find('[data-testid="evidence-badge"]').text()).toBe('tested')
    expect(chips[0].get('.cue-mark--tick path').attributes('d')).toBe(TICK_PATH)
    const gapChips = wrapper.findAll('[data-testid="sprof-gaps"] .chip')
    expect(gapChips[0].find('[data-testid="evidence-badge"]').exists()).toBe(false)
    expect(gapChips[1].find('[data-testid="evidence-badge"]').text()).toBe('declared')
  })

  it('shows error when API rejects', async () => {
    vi.spyOn(profileApi, 'getSessionProfile').mockRejectedValue(new Error('nope'))

    const wrapper = mount(ProfileView, {
      props: { id: 's1' },
      global: { stubs },
    })

    await flushPromises()

    const err = wrapper.find('[data-testid="sprof-error"]')
    expect(err.exists()).toBe(true)
    expect(err.text()).toContain('nope')
  })

  async function mountProfile({ profile = {}, etag = 'e0' } = {}) {
    vi.spyOn(profileApi, 'getSessionProfile').mockResolvedValue({
      profile: {
        knowledge_level: 'beginner',
        confirmed_gaps: [],
        mastered_concepts: [],
        ...profile,
      },
      etag,
      recent_learning_events: [],
    })

    const wrapper = mount(ProfileView, {
      props: { id: 's1' },
      global: { stubs },
    })

    await flushPromises()

    return wrapper
  }

  it('adds a mastered concept and threads the etag', async () => {
    const patchProfile = vi.spyOn(profileApi, 'patchProfile').mockResolvedValue({
      profile: {
        mastered_concepts: [{ name: 'loops', evidence_type: 'declared', last_event_at: null }],
        confirmed_gaps: [],
      },
      etag: 'e1',
    })

    const wrapper = await mountProfile({ etag: 'e0' })
    await wrapper.get('[data-testid="add-mastered"]').setValue('loops')
    await wrapper.get('[data-testid="add-mastered-submit"]').trigger('click')
    await flushPromises()
    expect(patchProfile).toHaveBeenCalledWith('s1', { add_mastered: 'loops' }, 'e0')
  })

  it('adds a confirmed gap and threads the etag', async () => {
    const patchProfile = vi.spyOn(profileApi, 'patchProfile').mockResolvedValue({
      profile: {
        mastered_concepts: [],
        confirmed_gaps: [{ name: 'window-fns', evidence_type: 'declared', last_event_at: null }],
      },
      etag: 'e1',
    })

    const wrapper = await mountProfile({ etag: 'e0' })
    await wrapper.get('[data-testid="add-gap"]').setValue('window-fns')
    await wrapper.get('[data-testid="add-gap-submit"]').trigger('click')
    await flushPromises()
    expect(patchProfile).toHaveBeenCalledWith('s1', { add_gap: 'window-fns' }, 'e0')
  })

  it('removes a chip via deleteProfileItem', async () => {
    const deleteProfileItem = vi.spyOn(profileApi, 'deleteProfileItem').mockResolvedValue({
      profile: { mastered_concepts: [], confirmed_gaps: [] },
      etag: 'e1',
    })

    const wrapper = await mountProfile({
      profile: {
        mastered_concepts: [{ name: 'loops', evidence_type: 'tested', last_event_at: null }],
        confirmed_gaps: [],
      },
      etag: 'e0',
    })

    await wrapper.get('[data-testid="chip-remove"]').trigger('click')
    await flushPromises()
    // E-08: the click only opens the confirm; nothing is deleted until accept.
    expect(deleteProfileItem).not.toHaveBeenCalled()
    expect(lastConfirm).toMatchObject({
      header: 'Remove concept',
      rejectLabel: 'Cancel',
      acceptLabel: 'Remove',
      rejectClass: 'p-button-text p-button-secondary',
      acceptClass: 'p-button-danger confirm-delete-strong',
    })
    expect(lastConfirm.icon).toBeUndefined()
    lastConfirm.accept()
    await flushPromises()
    expect(deleteProfileItem).toHaveBeenCalledWith('s1', 'mastered_concepts', 'loops', 'e0')
  })

  it('a rejected remove confirm leaves the profile alone', async () => {
    const deleteProfileItem = vi.spyOn(profileApi, 'deleteProfileItem').mockResolvedValue({
      profile: { mastered_concepts: [], confirmed_gaps: [] },
      etag: 'e1',
    })

    const wrapper = await mountProfile({
      profile: {
        mastered_concepts: [{ name: 'loops', evidence_type: 'tested', last_event_at: null }],
        confirmed_gaps: [],
      },
      etag: 'e0',
    })

    await wrapper.get('[data-testid="chip-remove"]').trigger('click')
    await flushPromises()
    expect(deleteProfileItem).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="chip-remove"]').exists()).toBe(true)
  })

  it('sets the knowledge level and threads the etag', async () => {
    const patchProfile = vi.spyOn(profileApi, 'patchProfile').mockResolvedValue({
      profile: { mastered_concepts: [], confirmed_gaps: [], knowledge_level: 'advanced' },
      etag: 'e1',
    })

    const wrapper = await mountProfile({ etag: 'e0' })

    const advancedBtn = wrapper
      .get('[data-testid="level-select"]')
      .findAll('button')
      .find((b) => b.text() === 'advanced')

    await advancedBtn.trigger('click')
    await flushPromises()
    expect(patchProfile).toHaveBeenCalledWith('s1', { knowledge_level: 'advanced' }, 'e0')
  })

  // E-08: a second write issued against the etag the first one is about to
  // replace would lose to a 412. Mutating controls go disabled for the
  // duration, so the re-entrant click never reaches the handler.
  it('ignores a re-entrant write while one is in flight (E-08)', async () => {
    let resolveFirst

    const patchProfile = vi.spyOn(profileApi, 'patchProfile').mockImplementation(
      () =>
        new Promise((res) => {
          resolveFirst = res
        }),
    )

    const wrapper = await mountProfile({ etag: 'e0' })
    const buttons = wrapper.get('[data-testid="level-select"]').findAll('button')
    const advanced = buttons.find((b) => b.text() === 'advanced')
    const intermediate = buttons.find((b) => b.text() === 'intermediate')

    await advanced.trigger('click')
    await flushPromises()
    expect(patchProfile).toHaveBeenCalledTimes(1)
    expect(intermediate.attributes('disabled')).toBeDefined()

    await intermediate.trigger('click')
    await nextTick()
    expect(patchProfile).toHaveBeenCalledTimes(1)

    resolveFirst({
      profile: { mastered_concepts: [], confirmed_gaps: [], knowledge_level: 'advanced' },
      etag: 'e1',
    })
    await flushPromises()
    expect(advanced.attributes('disabled')).toBeUndefined()
  })

  // E-08: the add-item text field stays enabled (Enter is the fast path for
  // typing several concepts), so writes are serialised rather than dropped --
  // the queued write reads the etag the previous response produced.
  it('threads the previous response etag into a queued write (E-08)', async () => {
    const resolvers = []

    const patchProfile = vi
      .spyOn(profileApi, 'patchProfile')
      .mockImplementation(() => new Promise((res) => resolvers.push(res)))

    const wrapper = await mountProfile({ etag: 'e0' })
    const input = wrapper.get('[data-testid="add-gap"]')

    await input.setValue('alpha')
    await input.trigger('keydown.enter')
    await flushPromises()
    expect(patchProfile).toHaveBeenCalledTimes(1)
    expect(patchProfile).toHaveBeenNthCalledWith(1, 's1', { add_gap: 'alpha' }, 'e0')

    await input.setValue('beta')
    await input.trigger('keydown.enter')
    await flushPromises()
    // Still one call: the second write is queued behind the first.
    expect(patchProfile).toHaveBeenCalledTimes(1)

    resolvers[0]({ profile: { mastered_concepts: [], confirmed_gaps: [] }, etag: 'e1' })
    await flushPromises()
    expect(patchProfile).toHaveBeenCalledTimes(2)
    expect(patchProfile).toHaveBeenNthCalledWith(2, 's1', { add_gap: 'beta' }, 'e1')

    resolvers[1]({ profile: { mastered_concepts: [], confirmed_gaps: [] }, etag: 'e2' })
    await flushPromises()
    expect(wrapper.find('[data-testid="sprof-write-error"]').exists()).toBe(false)
  })

  it('on 412 refetches and shows a notice', async () => {
    const getSessionProfile = vi.spyOn(profileApi, 'getSessionProfile').mockResolvedValue({
      profile: { knowledge_level: 'beginner', confirmed_gaps: [], mastered_concepts: [] },
      etag: 'e0',
      recent_learning_events: [],
    })

    vi.spyOn(profileApi, 'patchProfile').mockRejectedValueOnce(
      Object.assign(new Error('x'), { status: 412 }),
    )

    const wrapper = mount(ProfileView, {
      props: { id: 's1' },
      global: { stubs },
    })

    await flushPromises()

    await wrapper.get('[data-testid="add-mastered"]').setValue('loops')
    await wrapper.get('[data-testid="add-mastered-submit"]').trigger('click')
    await flushPromises()

    expect(getSessionProfile).toHaveBeenCalledTimes(2) // initial + refetch
    expect(wrapper.get('[data-testid="sprof-conflict"]').exists()).toBe(true)
  })

  // F-05: a write failure must show an inline banner, not replace the
  // loaded profile with an error page.
  it('a failed write shows an inline banner and keeps the profile visible (F-05)', async () => {
    vi.spyOn(profileApi, 'patchProfile').mockRejectedValueOnce(
      Object.assign(new Error('boom'), { status: 500 }),
    )

    const wrapper = await mountProfile({
      profile: {
        mastered_concepts: [{ name: 'loops', evidence_type: 'tested', last_event_at: null }],
      },
      etag: 'e0',
    })

    await wrapper.get('[data-testid="add-gap"]').setValue('window-fns')
    await wrapper.get('[data-testid="add-gap-submit"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="sprof-write-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sprof-mastered"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="sprof-error"]').exists()).toBe(false)
  })

  it('the write-error banner clears on the next write attempt (F-05)', async () => {
    vi.spyOn(profileApi, 'patchProfile')
      .mockRejectedValueOnce(Object.assign(new Error('boom'), { status: 500 }))
      .mockResolvedValueOnce({
        profile: { mastered_concepts: [], confirmed_gaps: [] },
        etag: 'e1',
      })
    const wrapper = await mountProfile({ etag: 'e0' })
    await wrapper.get('[data-testid="add-gap"]').setValue('a')
    await wrapper.get('[data-testid="add-gap-submit"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="sprof-write-error"]').exists()).toBe(true)
    await wrapper.get('[data-testid="add-gap"]').setValue('b')
    await wrapper.get('[data-testid="add-gap-submit"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="sprof-write-error"]').exists()).toBe(false)
  })

  it('review-gaps button routes to the session with review_gap query', async () => {
    const wrapper = await mountProfile({
      profile: {
        confirmed_gaps: [
          { name: 'a', evidence_type: null, last_event_at: null },
          { name: 'b', evidence_type: null, last_event_at: null },
        ],
      },
    })

    await wrapper.get('[data-testid="sprof-review-gaps"]').trigger('click')
    await wrapper.get('[data-testid="gap-picker-option-0"]').trigger('click')
    expect(routerPushMock).toHaveBeenCalledWith({
      name: 'session',
      params: { id: 's1' },
      query: { review_gap: 'a' },
    })
    expect(routerPushMock).toHaveBeenCalledTimes(1)
  })

  it('review-gaps button skips the picker and routes directly for a single gap', async () => {
    const wrapper = await mountProfile({
      profile: {
        confirmed_gaps: [{ name: 'only-gap', evidence_type: null, last_event_at: null }],
      },
    })

    await wrapper.get('[data-testid="sprof-review-gaps"]').trigger('click')
    expect(wrapper.find('[data-testid="gap-picker"]').exists()).toBe(false)
    expect(routerPushMock).toHaveBeenCalledWith({
      name: 'session',
      params: { id: 's1' },
      query: { review_gap: 'only-gap' },
    })
    expect(routerPushMock).toHaveBeenCalledTimes(1)
  })

  it('does not show the review-gaps button when there are no confirmed gaps', async () => {
    const wrapper = await mountProfile({ profile: { confirmed_gaps: [] } })
    expect(wrapper.find('[data-testid="sprof-review-gaps"]').exists()).toBe(false)
  })

  it('renders subtopic levels with editable pills and remove', async () => {
    const wrapper = await mountProfile({
      profile: { subtopic_levels: { 'chain rule': 'beginner' } },
    })

    const sec = wrapper.find('[data-testid="sprof-subtopics"]')
    expect(sec.exists()).toBe(true)
    expect(sec.text()).toContain('chain rule')
    const active = sec.find('.level-opt.active')
    expect(active.text()).toBe('beginner')
  })

  it('PATCHes subtopic level on pill click and DELETEs on remove', async () => {
    const patchProfile = vi.spyOn(profileApi, 'patchProfile').mockResolvedValue({
      profile: {
        mastered_concepts: [],
        confirmed_gaps: [],
        subtopic_levels: { 'chain rule': 'advanced' },
      },
      etag: 'e1',
    })

    const deleteProfileItem = vi.spyOn(profileApi, 'deleteProfileItem').mockResolvedValue({
      profile: { mastered_concepts: [], confirmed_gaps: [], subtopic_levels: {} },
      etag: 'e2',
    })

    const wrapper = await mountProfile({
      profile: { subtopic_levels: { 'chain rule': 'beginner' } },
      etag: 'e0',
    })

    const row = wrapper.get('[data-testid="sprof-subtopics"] .subtopic-row')
    const advancedBtn = row.findAll('.level-opt').find((b) => b.text() === 'advanced')
    await advancedBtn.trigger('click')
    await flushPromises()
    expect(patchProfile).toHaveBeenCalledWith(
      's1',
      { subtopic: 'chain rule', subtopic_level: 'advanced' },
      'e0',
    )

    await wrapper.get('[data-testid="subtopic-remove"]').trigger('click')
    await flushPromises()
    expect(deleteProfileItem).not.toHaveBeenCalled()
    expect(lastConfirm.header).toBe('Remove concept')
    lastConfirm.accept()
    await flushPromises()
    expect(deleteProfileItem).toHaveBeenCalledWith('s1', 'subtopic_levels', 'chain rule', 'e1')
  })

  it('hides the subtopics section when subtopic_levels is empty', async () => {
    const wrapper = await mountProfile({ profile: { subtopic_levels: {} } })
    expect(wrapper.find('[data-testid="sprof-subtopics"]').exists()).toBe(false)
  })

  // A2: add-item inputs must have accessible names for screen readers.
  it('has accessible names on the add-mastered and add-gap inputs', async () => {
    const wrapper = await mountProfile()
    expect(wrapper.get('[data-testid="add-mastered"]').attributes('aria-label')).toBe(
      'Add a mastered concept',
    )
    expect(wrapper.get('[data-testid="add-gap"]').attributes('aria-label')).toBe('Add a gap')
  })

  // E-18: navigating from one session's profile straight to another's (no
  // remount, same route component) must reload for the new id.
  it('reloads the profile when props.id changes', async () => {
    const getSessionProfile = vi.spyOn(profileApi, 'getSessionProfile').mockResolvedValue({
      profile: { knowledge_level: 'beginner', confirmed_gaps: [], mastered_concepts: [] },
      etag: 'e0',
      recent_learning_events: [],
    })

    const wrapper = mount(ProfileView, { props: { id: 's1' }, global: { stubs } })
    await flushPromises()
    expect(getSessionProfile).toHaveBeenNthCalledWith(1, 's1')

    await wrapper.setProps({ id: 's2' })
    await flushPromises()
    expect(getSessionProfile).toHaveBeenNthCalledWith(2, 's2')
  })

  // E-18: a slow response for the id navigated away from must not overwrite
  // the newer id's data once it arrives later.
  it('discards a stale load that resolves after a newer one', async () => {
    const pending = {}
    vi.spyOn(profileApi, 'getSessionProfile').mockImplementation(
      (id) =>
        new Promise((resolve) => {
          pending[id] = resolve
        }),
    )
    const wrapper = mount(ProfileView, { props: { id: 's1' }, global: { stubs } })
    await flushPromises()

    await wrapper.setProps({ id: 's2' })
    await flushPromises()

    pending.s2({
      profile: { knowledge_level: 'advanced', confirmed_gaps: [], mastered_concepts: [] },
      etag: 'e-s2',
      recent_learning_events: [],
    })
    await flushPromises()

    pending.s1({
      profile: { knowledge_level: 'beginner', confirmed_gaps: [], mastered_concepts: [] },
      etag: 'e-s1',
      recent_learning_events: [],
    })
    await flushPromises()

    const active = wrapper.get('[data-testid="level-select"]').find('.level-opt.active')
    expect(active.text()).toBe('advanced')
    expect(wrapper.find('[data-testid="sprof-loading"]').exists()).toBe(false)
  })

  // Stale-sibling-state fix: the route component is reused across
  // session->session navigation (E-18), so a write-error banner, an unsaved
  // draft, and an open gap picker left over from session A must not still be
  // showing once the id-change watcher has loaded session B.
  it('discards a write result that resolves after props.id changed', async () => {
    const getSessionProfile = vi
      .spyOn(profileApi, 'getSessionProfile')
      .mockImplementation(async (id) => ({
        profile: { knowledge_level: 'beginner', confirmed_gaps: [], mastered_concepts: [] },
        etag: `etag-${id}`,
        recent_learning_events: [],
      }))

    let resolveWrite
    vi.spyOn(profileApi, 'patchProfile').mockReturnValueOnce(
      new Promise((r) => {
        resolveWrite = r
      }),
    )
    const wrapper = mount(ProfileView, { props: { id: 's1' }, global: { stubs } })
    await flushPromises()

    await wrapper.get('[data-testid="add-mastered"]').setValue('loops')
    await wrapper.get('[data-testid="add-mastered-submit"]').trigger('click')

    await wrapper.setProps({ id: 's2' })
    await flushPromises()
    expect(getSessionProfile).toHaveBeenLastCalledWith('s2')

    // s1's write lands late with s1's profile + etag: must not paint onto s2.
    resolveWrite({
      profile: {
        knowledge_level: 'advanced',
        confirmed_gaps: [],
        mastered_concepts: [{ name: 'loops', evidence_type: 'declared', last_event_at: null }],
      },
      etag: 'etag-s1-after-write',
    })
    await flushPromises()

    expect(wrapper.text()).not.toContain('loops')
    expect(wrapper.vm.data.etag).toBe('etag-s2')
  })

  it('keeps an unsaved draft across a 412 recovery reload', async () => {
    vi.spyOn(profileApi, 'getSessionProfile').mockResolvedValue({
      profile: { knowledge_level: 'beginner', confirmed_gaps: [], mastered_concepts: [] },
      etag: 'e0',
      recent_learning_events: [],
    })
    vi.spyOn(profileApi, 'patchProfile').mockRejectedValueOnce(
      Object.assign(new Error('x'), { status: 412 }),
    )
    const wrapper = mount(ProfileView, { props: { id: 's1' }, global: { stubs } })
    await flushPromises()

    await wrapper.get('[data-testid="add-gap"]').setValue('half-typed')
    await wrapper.get('[data-testid="add-mastered"]').setValue('loops')
    await wrapper.get('[data-testid="add-mastered-submit"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="sprof-conflict"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="add-gap"]').element.value).toBe('half-typed')
  })

  it('clears writeError, drafts, and the gap picker when props.id changes', async () => {
    vi.spyOn(profileApi, 'getSessionProfile').mockResolvedValue({
      profile: {
        knowledge_level: 'beginner',
        confirmed_gaps: [
          { name: 'a', evidence_type: null, last_event_at: null },
          { name: 'b', evidence_type: null, last_event_at: null },
        ],
        mastered_concepts: [],
      },
      etag: 'e0',
      recent_learning_events: [],
    })
    vi.spyOn(profileApi, 'patchProfile').mockRejectedValueOnce(
      Object.assign(new Error('boom'), { status: 500 }),
    )
    const wrapper = mount(ProfileView, { props: { id: 's1' }, global: { stubs } })
    await flushPromises()

    await wrapper.get('[data-testid="add-mastered"]').setValue('loops')
    await wrapper.get('[data-testid="add-mastered-submit"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="sprof-write-error"]').exists()).toBe(true)

    await wrapper.get('[data-testid="add-gap"]').setValue('unsaved-draft')
    await wrapper.get('[data-testid="sprof-review-gaps"]').trigger('click')
    expect(wrapper.find('[data-testid="gap-picker"]').exists()).toBe(true)

    await wrapper.setProps({ id: 's2' })
    await flushPromises()

    expect(wrapper.find('[data-testid="sprof-write-error"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="gap-picker"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="add-gap"]').element.value).toBe('')
  })

  // Same fix, the conflict banner: a 412 leaves conflict=true after the
  // recovery reload finishes, and that must not survive a subsequent
  // id-change navigation either.
  it('clears the conflict banner when props.id changes after a 412', async () => {
    const getSessionProfile = vi.spyOn(profileApi, 'getSessionProfile').mockResolvedValue({
      profile: { knowledge_level: 'beginner', confirmed_gaps: [], mastered_concepts: [] },
      etag: 'e0',
      recent_learning_events: [],
    })

    vi.spyOn(profileApi, 'patchProfile').mockRejectedValueOnce(
      Object.assign(new Error('x'), { status: 412 }),
    )
    const wrapper = mount(ProfileView, { props: { id: 's1' }, global: { stubs } })
    await flushPromises()

    await wrapper.get('[data-testid="add-mastered"]').setValue('loops')
    await wrapper.get('[data-testid="add-mastered-submit"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="sprof-conflict"]').exists()).toBe(true)
    expect(getSessionProfile).toHaveBeenCalledTimes(2)

    await wrapper.setProps({ id: 's2' })
    await flushPromises()

    expect(wrapper.find('[data-testid="sprof-conflict"]').exists()).toBe(false)
  })
})
