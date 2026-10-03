import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import HomeView from '@/views/HomeView.vue'
import { useSessionStore } from '@/stores/session.js'

const push = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
}))

const apiEndSession = vi.fn()

vi.mock('@/services/sessionsApi.js', () => ({
  endSession: (...args) => apiEndSession(...args),
}))

const stubs = {
  EmptyState: {
    props: ['tone', 'eyebrow', 'headline', 'subtext'],
    template: '<div data-testid="empty-stub"><slot name="subtext" /><slot name="cta" /></div>',
  },
  RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
}

function makeSession(id, topic, ended = false, createdOffset = 0) {
  const created = new Date(Date.now() + createdOffset).toISOString()

  return {
    id,
    topic,
    created_at: created,
    ended_at: ended ? created : null,
  }
}

function mountView() {
  return mount(HomeView, { global: { stubs } })
}

describe('HomeView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockClear()
    apiEndSession.mockReset()
  })

  it('calls listSessions on mount', async () => {
    const store = useSessionStore()
    const spy = vi.spyOn(store, 'listSessions').mockResolvedValue([])
    mountView()
    await flushPromises()
    expect(spy).toHaveBeenCalledWith()
  })

  it('does not render bare Loading text while the store is loading', () => {
    const store = useSessionStore()
    store.loading = true
    store.sessions = []
    const w = mountView()
    expect(w.text()).not.toContain('Loading...')
    expect(w.find('[data-testid="home-mode-quick"]').exists()).toBe(true)
  })

  it('shows error from store', () => {
    const store = useSessionStore()
    store.error = 'list failed'
    const wrapper = mountView()
    expect(wrapper.get('[data-testid="home-error"]').text()).toBe('list failed')
  })

  // F-07: a background sidebar action failure (rename/pin) writing store.error
  // must not nuke an already-loaded Home screen -- the fatal error branch is
  // scoped to Home's own load (no sessions yet).
  it('keeps the mode cards mounted when a background error arrives but sessions are already loaded', () => {
    const store = useSessionStore()
    store.error = 'boom'
    store.sessions = [{ id: 's1' }]
    const wrapper = mountView()
    expect(wrapper.find('[data-testid="home-mode-quick"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="home-error"]').exists()).toBe(false)
  })

  it('shows the fatal error branch when there are no sessions to render', () => {
    const store = useSessionStore()
    store.error = 'boom'
    store.sessions = []
    const wrapper = mountView()
    expect(wrapper.find('[data-testid="home-error"]').exists()).toBe(true)
  })

  // E-01: a boot-time list failure with zero sessions used to hide the start
  // form entirely (v-if/v-else on store.error), leaving the learner with no
  // way to start a session. The form must stay mounted regardless.
  it('does not hide the start form when store.error is set and there are no sessions (E-01)', () => {
    const store = useSessionStore()
    store.error = 'boom'
    store.sessions = []
    const wrapper = mountView()
    expect(wrapper.find('[data-testid="home-quick-topic"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="home-quick-go"]').exists()).toBe(true)
  })

  // E-01: a failed createSession used to throw out of an unawaited handler
  // (unhandled rejection) and leave the learner stuck with no feedback. The
  // form must stay mounted and the failure must surface inline.
  it('keeps the start form mounted and shows an inline error when create fails (E-01)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'listSessions').mockResolvedValue([])
    vi.spyOn(store, 'lookupTopic').mockResolvedValue({ active_match: null, ended_match: null })
    vi.spyOn(store, 'createSession').mockRejectedValue(new Error('boom'))
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="home-quick-topic"]').setValue('Recursion')
    await wrapper.get('[data-testid="home-quick-go"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="home-quick-topic"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="home-quick-go"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="home-error"]').text()).toBe('boom')
  })

  it('shows a single New lesson card, no Build a subject', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'listSessions').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-testid="home-quick-topic"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Build a subject')
    expect(wrapper.find('[data-testid="home-mode-quick"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="home-mode-subject"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="home-build-start"]').exists()).toBe(false)
  })

  it('renders no review card', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'listSessions').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-testid="home-mode-review"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Due for review')
  })

  it('New lesson: no match creates a session immediately and navigates', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'listSessions').mockResolvedValue([])
    vi.spyOn(store, 'lookupTopic').mockResolvedValue({ active_match: null, ended_match: null })
    vi.spyOn(store, 'createSession').mockResolvedValue({ id: 'sess1' })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="home-quick-topic"]').setValue('Recursion')
    await wrapper.get('[data-testid="home-quick-go"]').trigger('click')
    await flushPromises()
    expect(store.createSession).toHaveBeenCalledWith(
      expect.objectContaining({
        topic: 'Recursion',
        seedMode: 'fresh',
        priorSessionId: null,
      }),
    )
    expect(push).toHaveBeenCalledWith({ name: 'session', params: { id: 'sess1' } })
  })

  it('active match shows intercept with open-existing', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'listSessions').mockResolvedValue([])
    vi.spyOn(store, 'lookupTopic').mockResolvedValue({
      active_match: { session_id: 'a1', title: 'CSS' },
      ended_match: null,
    })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="home-quick-topic"]').setValue('CSS')
    await wrapper.get('[data-testid="home-quick-go"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="intercept-open-existing"]').exists()).toBe(true)
    await wrapper.get('[data-testid="intercept-open-existing"]').trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'session', params: { id: 'a1' } })
  })

  it('ended match continue resumes', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'listSessions').mockResolvedValue([])
    vi.spyOn(store, 'lookupTopic').mockResolvedValue({
      active_match: null,
      ended_match: { session_id: 'e1', title: 'CSS', gap_count: 1 },
    })
    vi.spyOn(store, 'continueTopic').mockResolvedValue({ id: 'r1' })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="home-quick-topic"]').setValue('CSS')
    await wrapper.get('[data-testid="home-quick-go"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="intercept-continue"]').trigger('click')
    await flushPromises()
    expect(store.continueTopic).toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith({ name: 'session', params: { id: 'r1' } })
  })

  it('double-invoking start-quick while lookup is pending only calls lookupTopic once', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'listSessions').mockResolvedValue([])
    let resolveLookup

    const lookupSpy = vi.spyOn(store, 'lookupTopic').mockReturnValue(
      new Promise((resolve) => {
        resolveLookup = resolve
      }),
    )

    vi.spyOn(store, 'createSession').mockResolvedValue({ id: 'sess1' })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="home-quick-topic"]').setValue('Recursion')
    await wrapper.get('[data-testid="home-quick-go"]').trigger('click')
    await wrapper.get('[data-testid="home-quick-go"]').trigger('click')
    expect(lookupSpy).toHaveBeenCalledTimes(1)
    resolveLookup({ active_match: null, ended_match: null })
    await flushPromises()
    expect(store.createSession).toHaveBeenCalledTimes(1)
  })

  // Redesign: recent sessions now live in the sidebar only. Home keeps only
  // the prompt, so this guard narrows to the dupe banner staying gone.
  it('does not render the dupe banner', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'listSessions').mockResolvedValue([])
    store.sessions = [makeSession('a1', 'Calc', false, -1), makeSession('a2', 'Calc', false, 0)]
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-testid="home-dupe-banner"]').exists()).toBe(false)
  })

  it('does not render a file-attach control', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'listSessions').mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-testid="home-file-add"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="home-file-input"]').exists()).toBe(false)
  })
})
