import { describe, it, expect, afterEach, beforeEach, vi } from 'vitest'
import { nextTick, reactive } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import SessionView from '@/views/SessionView.vue'
import SessionHeader from '@/components/chat/SessionHeader.vue'
import SessionEndedBanner from '@/components/SessionEndedBanner.vue'
import CheckQuestion from '@/components/chat/CheckQuestion.vue'
import Composer from '@/components/chat/Composer.vue'
import MessageList from '@/components/chat/MessageList.vue'
import { StreamAbortedError } from '@/lib/errors.js'
import { REDUCED_MOTION_QUERY } from '@/composables/useMediaQuery.js'
import { WATCH_CEILING_MS } from '@/composables/useReferencePoll.js'
import { useSessionStore } from '@/stores/session.js'
import { getSessionProfile, patchProfile } from '@/services/profileApi.js'

const push = vi.fn()

// Writes the mutation back into the shared mock route so the query-strip
// watcher/re-trigger interaction is actually exercised (a bare vi.fn() would
// leave route.query.review_gap set, hiding a double-send regression).
let route = { query: {} }

const replace = vi.fn((to) => {
  Object.assign(route.query, to.query)
})

vi.mock('vue-router', () => ({
  useRouter: () => ({ push, replace }),
  useRoute: () => route,
  RouterLink: { template: '<a><slot /></a>' },
}))

// Ticket 10: the session action bar calls useSessionActions, which calls
// useConfirm in setup. Capture the last dialog config so a test can accept it.
let lastConfirm = null

vi.mock('primevue/useconfirm', () => ({
  useConfirm: () => ({
    require: (cfg) => {
      lastConfirm = cfg
    },
  }),
}))

const showError = vi.fn()

vi.mock('@/composables/useToast.js', () => ({
  useToast: () => ({ showError, showWarn: vi.fn(), showSuccess: vi.fn() }),
}))

const uploadDocument = vi.fn()

const validateFile = vi.fn()

// F-12: the upload chip is driven by useReferencePoll's per-document
// transitions now, so the view polls /sessions/:id/ingestion (once per session
// at setup, then with backoff) instead of /upload/:documentId.
const getSessionIngestion = vi.fn()

vi.mock('@/services/uploadApi.js', () => ({
  uploadDocument: (...args) => uploadDocument(...args),
  validateFile: (...args) => validateFile(...args),
  getSessionIngestion: (...args) => getSessionIngestion(...args),
  MAX_UPLOAD_BYTES: 25 * 1024 * 1024,
}))

vi.mock('@/services/profileApi.js', () => ({
  getSessionProfile: vi.fn(),
  patchProfile: vi.fn(),
}))

const ReferenceStatusBannerStub = {
  name: 'ReferenceStatusBanner',
  props: ['status', 'documents', 'failed'],
  template: '<div />',
}

const stubs = {
  BackButton: { template: '<button data-testid="back" />' },
  ReferenceStatusBanner: ReferenceStatusBannerStub,
  SessionEndedBanner: {
    props: ['endedAt', 'loading', 'hasGaps'],
    emits: ['resume', 'resume-gaps'],
    template:
      '<div data-testid="ended-banner"><button data-testid="resume-btn" @click="$emit(\'resume\')" /><button v-if="hasGaps" data-testid="session-resume-gaps" @click="$emit(\'resume-gaps\')" /></div>',
  },
  Button: {
    props: ['disabled', 'loading', 'label'],
    template:
      '<button :disabled="disabled" @click="$emit(\'click\')"><slot>{{ label }}</slot></button>',
  },
  Dialog: {
    props: ['visible'],
    emits: ['update:visible'],
    template: '<div v-if="visible" data-testid="dialog"><slot /><slot name="footer" /></div>',
  },
  RouterLink: { template: '<a><slot /></a>' },
}

function setupSession({
  id = 's1',
  ended = false,
  messages = [],
  dailyCap = null,
  confirmedGaps = [],
  hasMoreMessages = false,
} = {}) {
  const store = useSessionStore()
  store.currentSession = {
    id,
    topic: 'Calculus',
    ended_at: ended ? new Date().toISOString() : null,
    topic_profile: {
      confirmed_gaps: confirmedGaps.map((name) => ({
        name,
        evidence_type: null,
        last_event_at: null,
      })),
    },
  }
  store.currentSessionId = id
  store.messages = messages
  store.hasMoreMessages = hasMoreMessages

  if (dailyCap) store.dailyCapInfo = dailyCap

  return store
}

function mountView(props = { id: 's1' }) {
  return mount(SessionView, { props, global: { stubs } })
}

describe('SessionView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockClear()
    replace.mockClear()
    route.query = {}
    showError.mockClear()
    uploadDocument.mockReset()
    validateFile.mockReset()
    getSessionIngestion.mockReset()
    getSessionIngestion.mockResolvedValue({ status: null, documents: [] })
    getSessionProfile.mockReset()
    patchProfile.mockReset()
    sessionStorage.clear()
  })

  it('renders 404 state when loadSession 404s', async () => {
    const store = useSessionStore()
    const err = Object.assign(new Error('not found'), { status: 404 })
    vi.spyOn(store, 'loadSession').mockRejectedValue(err)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-testid="session-not-found"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="session-input"]').exists()).toBe(false)
  })

  it('renders chat ui when session loads', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('Calculus')
    expect(wrapper.find('[data-testid="session-input"]').exists()).toBe(true)
    // Header renders inline (no teleport); topic comes from props
    const header = wrapper.findComponent(SessionHeader)
    expect(header.exists()).toBe(true)
    expect(header.props('session').topic).toBe('Calculus')
    expect(wrapper.find('[data-testid="session-header"]').exists()).toBe(true)
  })

  it('reloads when the route id prop changes without a remount', async () => {
    const store = useSessionStore()

    const load = vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })

    const wrapper = mountView({ id: 's1' })
    await flushPromises()
    expect(load).toHaveBeenCalledWith('s1')

    load.mockClear()
    await wrapper.setProps({ id: 's2' })
    await flushPromises()
    expect(load).toHaveBeenCalledWith('s2')
  })

  it('clears a prior 404 state when navigating to a valid session', async () => {
    const store = useSessionStore()
    const err = Object.assign(new Error('not found'), { status: 404 })

    const load = vi
      .spyOn(store, 'loadSession')
      .mockRejectedValueOnce(err)
      .mockImplementationOnce(async () => {
        setupSession()
      })

    const wrapper = mountView({ id: 'gone' })
    await flushPromises()
    expect(wrapper.find('[data-testid="session-not-found"]').exists()).toBe(true)

    await wrapper.setProps({ id: 's1' })
    await flushPromises()
    expect(load).toHaveBeenLastCalledWith('s1')
    expect(wrapper.find('[data-testid="session-not-found"]').exists()).toBe(false)
  })

  it('does not flash 404 when a superseded load 404s after navigating away', async () => {
    const store = useSessionStore()
    let rejectGone
    vi.spyOn(store, 'loadSession').mockImplementation((id) => {
      if (id === 'gone') {
        return new Promise((_res, rej) => {
          rejectGone = () => rej(Object.assign(new Error('not found'), { status: 404 }))
        })
      }

      store.currentSession = { id, topic: 'Calculus', ended_at: null }
      store.currentSessionId = id
      store.messages = []

      return Promise.resolve()
    })
    const wrapper = mountView({ id: 'gone' })
    await flushPromises() // first load pending (never resolved yet)

    await wrapper.setProps({ id: 's1' }) // navigate away before 'gone' settles
    await flushPromises()

    rejectGone() // the superseded 'gone' load 404s late
    await flushPromises()

    expect(wrapper.find('[data-testid="session-not-found"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="session-header"]').exists()).toBe(true)
  })

  it('paints the optimistic header topic from the known list row while detail loads', async () => {
    const store = useSessionStore()
    // Hold the loading snapshot: loadSession never resolves.
    vi.spyOn(store, 'loadSession').mockImplementation(() => new Promise(() => {}))
    store.sessions = [{ id: 's2', topic: 'Thermodynamics' }]
    store.detailLoading = true
    const wrapper = mountView({ id: 's2' })
    await flushPromises()
    expect(wrapper.findComponent(SessionHeader).props('session')?.topic).toBe('Thermodynamics')
  })

  it('shows the message skeleton while detailLoading and hides empty-state + stale check card', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(() => new Promise(() => {}))
    store.detailLoading = true
    // Seed a pending check from the PREVIOUS session: it must NOT show over the
    // skeleton during a switch (it isn't overwritten until the await resolves).
    store.pendingCheck = { gap: 'g', total: 1, currentIndex: 0, viewIndex: 0, items: [] }
    const wrapper = mountView({ id: 's1' })
    await flushPromises()
    expect(wrapper.find('[data-testid="session-messages-skeleton"]').exists()).toBe(true)
    // ChatEmptyState (and its quick prompts) must not render behind the skeleton.
    expect(wrapper.find('[data-testid="quick-prompt-0"]').exists()).toBe(false)
    // The old session's CheckQuestion must not leak over the skeleton.
    expect(wrapper.findComponent(CheckQuestion).exists()).toBe(false)
  })

  it('swaps skeleton for messages and shows the real topic once detail resolves', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(() => new Promise(() => {}))
    store.detailLoading = true
    const wrapper = mountView({ id: 's1' })
    await flushPromises()
    expect(wrapper.find('[data-testid="session-messages-skeleton"]').exists()).toBe(true)
    // Flip state the way the real loadSession would on resolve.
    store.detailLoading = false
    store.currentSession = { id: 's1', topic: 'Calculus', ended_at: null }
    store.currentSessionId = 's1'
    store.messages = [{ role: 'assistant', content: 'hi', message_id: 'm1', citations: [] }]
    await nextTick()
    expect(wrapper.find('[data-testid="session-messages-skeleton"]').exists()).toBe(false)
    expect(wrapper.findComponent(SessionHeader).props('session')?.topic).toBe('Calculus')
  })

  it('prefers the target list row topic over a stale previous session during load', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(() => new Promise(() => {}))
    // Previous session still in currentSession; we are navigating to s2.
    store.currentSession = { id: 's1', topic: 'Old Topic', ended_at: null }
    store.sessions = [{ id: 's2', topic: 'Thermodynamics' }]
    store.detailLoading = true
    const wrapper = mountView({ id: 's2' })
    await flushPromises()
    expect(wrapper.findComponent(SessionHeader).props('session')?.topic).toBe('Thermodynamics')
  })

  it('hides the previous ended-session banner while loading a different session', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(() => new Promise(() => {}))
    // Previous session is ENDED; we navigate to a different, still-loading session.
    store.currentSession = { id: 's1', topic: 'Old', ended_at: '2026-01-01T00:00:00Z' }
    store.sessions = [{ id: 's2', topic: 'New' }]
    store.detailLoading = true
    const wrapper = mountView({ id: 's2' })
    await flushPromises()
    expect(wrapper.findComponent(SessionEndedBanner).exists()).toBe(false)
  })

  it('send dispatches sendMessageStreaming and clears draft', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="session-input"]').setValue('hello')
    await wrapper.get('[data-testid="session-send"]').trigger('click')
    await flushPromises()
    expect(sendSpy).toHaveBeenCalledWith({ text: 'hello' })
    expect(wrapper.get('[data-testid="session-input"]').element.value).toBe('')
  })

  it('send error restores draft and shows error banner', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    vi.spyOn(store, 'sendMessageStreaming').mockRejectedValue(
      Object.assign(new Error('network down'), { status: 500 }),
    )
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="session-input"]').setValue('hello')
    await wrapper.get('[data-testid="session-send"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="session-input"]').element.value).toBe('hello')
    expect(wrapper.find('[data-testid="session-error"]').exists()).toBe(true)
  })

  it('never renders raw technical details in the error banner', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    vi.spyOn(store, 'sendMessageStreaming').mockRejectedValue(
      Object.assign(new Error('cap'), { status: 429, path: '/chat/stream', body: '{}' }),
    )
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="session-input"]').setValue('hello')
    await wrapper.get('[data-testid="session-send"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="session-error"]').exists()).toBe(true)
    expect(wrapper.find('.error-details').exists()).toBe(false)
    expect(wrapper.get('[data-testid="session-error"]').text()).not.toContain('/chat/stream')
  })

  it('retry button resends last message', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })

    const sendSpy = vi
      .spyOn(store, 'sendMessageStreaming')
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce()

    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="session-input"]').setValue('retry me')
    await wrapper.get('[data-testid="session-send"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="session-error-retry"]').trigger('click')
    await flushPromises()
    expect(sendSpy).toHaveBeenCalledTimes(2)
    expect(sendSpy.mock.calls[1][0]).toEqual({ text: 'retry me' })
  })

  // F-9 (E-11): when the session was ended elsewhere, the view must keep the
  // typed text and add no lastError of its own on top of the store's error.
  it('restores the draft and skips the error chip when the session was ended elsewhere (E-11)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    vi.spyOn(store, 'sendMessageStreaming').mockRejectedValueOnce(
      new StreamAbortedError('session_ended'),
    )
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="session-input"]').setValue('my long message')
    await wrapper.get('[data-testid="session-send"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="session-input"]').element.value).toBe('my long message')
    expect(wrapper.find('[data-testid="session-error"]').exists()).toBe(false)
  })

  // Companion to the test above, driving the store's REAL 409 side effects
  // (store.error copy + ended_at) before the rejection. The user must see
  // exactly one banner carrying the store's specific "ended elsewhere" copy -
  // not a second generic chip - and no Retry button, since retrying into an
  // ended session would just fail again. The composer unmounts here (ended_at
  // flips isEnded), so the restored draft is not visible at this instant; it
  // lives in the view, not the Composer, and reappears bound to the composer
  // once the user clicks Resume and it remounts.
  it('shows only the store ended-session banner with no retry affordance (E-11)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    vi.spyOn(store, 'sendMessageStreaming').mockImplementationOnce(async () => {
      store.error = 'This session was ended elsewhere. Reopen it to continue.'
      store.currentSession.ended_at = new Date().toISOString()
      throw new StreamAbortedError('session_ended')
    })
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="session-input"]').setValue('my long message')
    await wrapper.get('[data-testid="session-send"]').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('[data-testid="session-error"]')).toHaveLength(1)
    expect(wrapper.get('[data-testid="session-error"]').text()).toContain('ended elsewhere')
    expect(wrapper.find('[data-testid="session-error-retry"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="ended-banner"]').exists()).toBe(true)
  })

  // F-9 (E-05): the 401 arm redirects to login, unmounting this view. Stash the
  // draft so the login round-trip does not eat what the user typed.
  it('stashes the draft to sessionStorage on auth expiry (E-05)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    vi.spyOn(store, 'sendMessageStreaming').mockRejectedValueOnce(
      new StreamAbortedError('auth_expired'),
    )
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="session-input"]').setValue('precious text')
    await wrapper.get('[data-testid="session-send"]').trigger('click')
    await flushPromises()
    expect(sessionStorage.getItem('crux:draft:s1')).toBe('precious text')
  })

  it('restores a stashed draft on mount and clears the stash (E-05 round-trip)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    sessionStorage.setItem('crux:draft:s1', 'from before login')
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.get('[data-testid="session-input"]').element.value).toBe('from before login')
    // One-shot: a second mount must not resurrect it.
    expect(sessionStorage.getItem('crux:draft:s1')).toBeNull()
  })

  // F-9 (E-14): retry must send what is in the composer now, not the text that
  // failed - the user may have edited it after the failure.
  it('retry sends the edited composer text, not the stale lastSentText (E-14)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })

    const sendSpy = vi
      .spyOn(store, 'sendMessageStreaming')
      .mockRejectedValueOnce(Object.assign(new Error('500'), { status: 500 }))

    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="session-input"]').setValue('original')
    await wrapper.get('[data-testid="session-send"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="session-input"]').setValue('edited')
    sendSpy.mockResolvedValueOnce(undefined)
    await wrapper.get('[data-testid="session-error-retry"]').trigger('click')
    await flushPromises()
    expect(sendSpy).toHaveBeenLastCalledWith(expect.objectContaining({ text: 'edited' }))
  })

  it('enter key sends without shift', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
    const wrapper = mountView()
    await flushPromises()
    const input = wrapper.get('[data-testid="session-input"]')
    await input.setValue('via enter')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(sendSpy).toHaveBeenCalledWith({ text: 'via enter' })
  })

  it('shift+enter does not send', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
    const wrapper = mountView()
    await flushPromises()
    const input = wrapper.get('[data-testid="session-input"]')
    await input.setValue('multi\nline')
    await input.trigger('keydown', { key: 'Enter', shiftKey: true })
    await flushPromises()
    expect(sendSpy).not.toHaveBeenCalled()
  })

  it('quick prompt fills draft when no messages', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="quick-prompt-0"]').trigger('click')
    expect(wrapper.get('[data-testid="session-input"]').element.value).toBe(
      'Where should I start with this topic?',
    )
    // Quick prompts fill the composer; they must not auto-send.
    expect(sendSpy).not.toHaveBeenCalled()
  })

  it('ended session hides composer and shows banner', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession({ ended: true })
    })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-testid="ended-banner"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="session-input"]').exists()).toBe(false)
  })

  it('opens summary dialog when store.pendingSummary targets this session', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    // Simulate the End trigger originating from the sidebar row menu —
    // it lands in pendingSummary and SessionView consumes it.
    store.pendingSummary = {
      sessionId: 's1',
      kind: 'summary',
      text: 'Great progress on derivatives.',
    }
    await flushPromises()
    expect(wrapper.get('[data-testid="session-summary-summary"]').text()).toContain(
      'Great progress on derivatives.',
    )
    expect(store.pendingSummary).toBe(null)
  })

  it('opens the summary dialog immediately when pendingSummary is already set before mount', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    // Set BEFORE mount to exercise the { immediate: true } watcher path — without
    // immediate, a pendingSummary set prior to this view mounting would be missed.
    store.pendingSummary = {
      sessionId: 's1',
      kind: 'summary',
      text: 'Pre-set summary from an off-view end.',
    }
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.get('[data-testid="session-summary-summary"]').text()).toContain(
      'Pre-set summary from an off-view end.',
    )
    expect(store.pendingSummary).toBe(null)
  })

  it('ending from the action bar still opens the summary dialog here (ticket 10)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    vi.spyOn(store, 'endSession').mockImplementation(async (id) => {
      store.currentSession.ended_at = new Date().toISOString()
      store.pendingSummary = { sessionId: id, kind: 'summary', text: 'Ended from the head.' }
    })
    route.name = 'session'
    route.params = { id: 's1' }

    try {
      lastConfirm = null
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="session-action-end"]').trigger('click')
      expect(lastConfirm?.header).toBe('End session')
      await lastConfirm.accept()
      await flushPromises()
      expect(store.endSession).toHaveBeenCalledWith('s1')
      expect(wrapper.get('[data-testid="session-summary-summary"]').text()).toContain(
        'Ended from the head.',
      )
      expect(wrapper.find('[data-testid="session-action-end"]').exists()).toBe(false)
      expect(wrapper.find('[data-testid="session-action-resume"]').exists()).toBe(true)
    } finally {
      delete route.name
      delete route.params
    }
  })

  it('passes the header the session object with pinned and ended_at', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession({ ended: true })
      store.currentSession.pinned = true
      store.currentSession.created_at = '2026-09-20T10:00:00Z'
    })
    const wrapper = mountView()
    await flushPromises()
    const session = wrapper.findComponent(SessionHeader).props('session')
    expect(session).toMatchObject({
      id: 's1',
      topic: 'Calculus',
      created_at: '2026-09-20T10:00:00Z',
      pinned: true,
    })
    expect(session.ended_at).toBeTruthy()
  })

  // The header dot reads the already-fetched aggregate (refStatus from
  // useReferencePoll, itself the backend's documents_service.aggregate_status
  // value), not a re-derivation from the raw document list -- so it always
  // agrees with ReferenceStatusBanner, which reads the same aggregate. 'ready'
  // wins even with a failed doc present in the list because the backend
  // aggregate itself already resolved to 'ready' (e.g. the failed doc was
  // since replaced); re-ranking from the documents here previously produced a
  // conflicting verdict against the banner.
  // End must not stay clickable while the tutor stream is mid-turn (ending
  // then would leave the stream running unaborted). SessionView forwards the
  // live stream state; SessionHeader's own disabled logic is covered in
  // sessionHeader.test.js.
  it('forwards the live stream state to the header as `streaming`', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.findComponent(SessionHeader).props('streaming')).toBe(false)
    store.streamState = 'streaming'
    await nextTick()
    expect(wrapper.findComponent(SessionHeader).props('streaming')).toBe(true)
    store.streamState = 'tool_running'
    await nextTick()
    expect(wrapper.findComponent(SessionHeader).props('streaming')).toBe(true)
    store.streamState = 'idle'
    await nextTick()
    expect(wrapper.findComponent(SessionHeader).props('streaming')).toBe(false)
  })

  it.each([
    ['pending', [], 'processing'],
    ['processing', [], 'processing'],
    [
      'ready',
      [
        { id: 'a', status: 'ready' },
        { id: 'c', status: 'failed' },
      ],
      'ready',
    ],
    ['failed', [{ id: 'c', status: 'failed' }], 'failed'],
    [null, [], null],
  ])(
    'derives the header refStatus from the ingestion aggregate (status=%s, docs=%j -> %s)',
    async (status, docs, want) => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionIngestion.mockResolvedValue({ status, documents: docs })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.findComponent(SessionHeader).props('refStatus')).toBe(want)
      expect(wrapper.find('[data-testid="session-ref-status"]').exists()).toBe(want !== null)
    },
  )

  it('summary dialog carries the shared dialog chrome class', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    store.pendingSummary = {
      sessionId: 's1',
      kind: 'summary',
      text: 'Great progress on derivatives.',
    }
    await flushPromises()
    expect(wrapper.get('[data-testid="session-summary-dialog"]').classes()).toContain('crux-dialog')
  })

  it('ignores pendingSummary targeting a different session', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    store.pendingSummary = { sessionId: 'other', kind: 'summary', text: 'x' }
    await flushPromises()
    expect(wrapper.find('[data-testid="session-summary-summary"]').exists()).toBe(false)
    expect(store.pendingSummary).not.toBe(null)
  })

  it('summary close routes home', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    store.pendingSummary = { sessionId: 's1', kind: 'summary', text: 'done' }
    await flushPromises()
    await wrapper.get('[data-testid="session-summary-close"]').trigger('click')
    expect(push).toHaveBeenCalledWith({ name: 'home' })
  })

  it('resume click invokes store.reopenSession', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession({ ended: true })
    })
    const reopenSpy = vi.spyOn(store, 'reopenSession').mockResolvedValue()
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="resume-btn"]').trigger('click')
    await flushPromises()
    expect(reopenSpy).toHaveBeenCalledWith('s1')
  })

  it('single confirmed gap skips the picker and sends directly', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession({ ended: true, confirmedGaps: ['limits'] })
    })
    const reopenSpy = vi.spyOn(store, 'reopenSession').mockResolvedValue()
    const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="session-resume-gaps"]').trigger('click')
    await flushPromises()
    expect(reopenSpy).toHaveBeenCalledWith('s1')
    expect(reopenSpy).toHaveBeenCalledTimes(1)
    expect(wrapper.find('[data-testid="gap-picker"]').exists()).toBe(false)
    expect(sendSpy).toHaveBeenCalledWith({
      text: 'Review my gap: limits',
      reviewGaps: true,
      reviewGap: 'limits',
    })
    expect(sendSpy).toHaveBeenCalledTimes(1)
  })

  it('resumeReviewGaps opens the picker when more than one confirmed gap', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession({ ended: true, confirmedGaps: ['a', 'b'] })
    })
    vi.spyOn(store, 'reopenSession').mockResolvedValue()
    const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="session-resume-gaps"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="gap-picker"]').exists()).toBe(true)
    expect(sendSpy).not.toHaveBeenCalled()
  })

  it('picker selection reopens then sends the targeted review seed', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession({ ended: true, confirmedGaps: ['a', 'b'] })
    })
    const reopenSpy = vi.spyOn(store, 'reopenSession').mockResolvedValue()
    const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
    const wrapper = mountView()
    await flushPromises()
    await wrapper.get('[data-testid="session-resume-gaps"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="gap-picker-option-1"]').trigger('click')
    await flushPromises()
    expect(reopenSpy).toHaveBeenCalledTimes(1)
    expect(sendSpy).toHaveBeenCalledWith({
      text: 'Review my gap: b',
      reviewGaps: true,
      reviewGap: 'b',
    })
    expect(sendSpy).toHaveBeenCalledTimes(1)
  })

  it('review_gap query param triggers the review seed then strips the query', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession({ ended: false, confirmedGaps: ['a', 'b'] })
    })
    vi.spyOn(store, 'reopenSession').mockResolvedValue()
    const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
    route.query = { review_gap: 'b' }
    mountView()
    await flushPromises()
    expect(sendSpy).toHaveBeenCalledWith({
      text: 'Review my gap: b',
      reviewGaps: true,
      reviewGap: 'b',
    })
    expect(replace).toHaveBeenCalledWith({ query: { review_gap: undefined } })
    expect(replace).toHaveBeenCalledTimes(1)
    // The mock replace above writes the strip back into route.query, so
    // route.query.review_gap is now undefined. Give the non-immediate
    // query watcher another tick to prove the strip does not re-trigger
    // a second send (a double-send regression would show up as 2 calls).
    await nextTick()
    await flushPromises()
    expect(sendSpy).toHaveBeenCalledTimes(1)
  })

  it('navigating to a different session id with review_gap query present sends into the new session only', async () => {
    const store = useSessionStore()

    const load = vi.spyOn(store, 'loadSession').mockImplementation(async (id) => {
      setupSession({ id, confirmedGaps: ['x'] })
    })

    const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
    const wrapper = mountView({ id: 's1' })
    await flushPromises()
    expect(sendSpy).not.toHaveBeenCalled()

    // Simulate navigating from s1 to s2 via a link that already carries the
    // review_gap query (e.g. ProfileView's review-gaps button), so the id
    // prop and the query change together before loadCurrent('s2') resolves.
    route.query = { review_gap: 'x' }
    await wrapper.setProps({ id: 's2' })
    await flushPromises()

    expect(load).toHaveBeenLastCalledWith('s2')
    expect(sendSpy).toHaveBeenCalledWith({
      text: 'Review my gap: x',
      reviewGaps: true,
      reviewGap: 'x',
    })
    expect(sendSpy).toHaveBeenCalledTimes(1)
  })

  it('quiz=1 sends seeded diagnostic message and strips param', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession({ ended: false })
    })
    const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
    route.query = { quiz: '1' }
    mountView()
    await flushPromises()
    expect(sendSpy).toHaveBeenCalledWith({
      text: 'Quiz me so you can pitch this at the right level.',
      diagnosticAccepted: true,
    })
    expect(replace).toHaveBeenCalledWith({ query: { quiz: undefined } })
    await nextTick()
    await flushPromises()
    expect(sendSpy).toHaveBeenCalledTimes(1)
  })

  it('quiz param ignored when session id mismatched', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      // currentSession stays unset (null) -- simulates a load that hasn't
      // populated the store yet / a superseded load.
    })
    const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
    route.query = { quiz: '1' }
    mountView()
    await flushPromises()
    expect(sendSpy).not.toHaveBeenCalled()
  })

  it('review_gap query param wins when both review_gap and quiz are present', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession({ ended: false, confirmedGaps: ['b'] })
    })
    const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
    route.query = { review_gap: 'b', quiz: '1' }
    mountView()
    await flushPromises()
    expect(sendSpy).toHaveBeenCalledWith({
      text: 'Review my gap: b',
      reviewGaps: true,
      reviewGap: 'b',
    })
    expect(sendSpy).toHaveBeenCalledTimes(1)
    // quiz must be stripped even though it lost precedence -- otherwise a
    // stale ?quiz=1 survives and fires unprompted on a later remount once
    // review_gap is gone.
    expect(replace).toHaveBeenCalledWith(
      expect.objectContaining({ query: expect.objectContaining({ quiz: undefined }) }),
    )
    expect(route.query.quiz).toBeUndefined()
  })

  it('duplicateReopen renders a go-to-active-session link targeting the conflicting session', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-testid="go-to-active-session"]').exists()).toBe(false)

    store.error = 'An active session with this topic already exists.'
    store.duplicateReopen = { sessionId: 'other1' }
    await flushPromises()

    const link = wrapper.findComponent('[data-testid="go-to-active-session"]')
    expect(link.exists()).toBe(true)
    expect(link.vm.$attrs.to).toEqual({ name: 'session', params: { id: 'other1' } })
  })

  it('daily cap banner shown when cap reached', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession({
        dailyCap: { used: 10, cap: 10, resets_at: '2026-05-24T00:00:00Z' },
      })
    })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-testid="session-cap-banner"]').exists()).toBe(true)
    expect(showError).toHaveBeenCalled()
  })

  it('upload triggers uploadDocument and drives the chip from the shared poller', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    validateFile.mockReturnValue({ ok: true })
    uploadDocument.mockResolvedValue({ document_id: 'doc-1' })
    getSessionIngestion.mockResolvedValue({
      status: 'ready',
      documents: [{ id: 'doc-1', filename: 'notes.pdf', status: 'ready' }],
    })
    const wrapper = mountView()
    await flushPromises()
    const file = new File(['pdf-bytes'], 'notes.pdf', { type: 'application/pdf' })
    const input = wrapper.get('[data-testid="session-upload-input"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()
    await flushPromises()
    expect(uploadDocument).toHaveBeenCalledWith({ sessionId: 's1', file })
    expect(getSessionIngestion).toHaveBeenCalledWith('s1', { fresh: true, silent: true })
    expect(wrapper.find('[data-testid="upload-status-ready"]').exists()).toBe(true)
    // Same poll feeds the banner, so the newly uploaded doc appears there too.
    expect(wrapper.findComponent(ReferenceStatusBannerStub).props('status')).toBe('ready')
  })

  // E-07: the first poll after an upload can throw with status still null. The
  // chip must say so rather than wait out the 90s ceiling.
  it('surfaces an unavailable chip when the ingestion poll throws', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    validateFile.mockReturnValue({ ok: true })
    uploadDocument.mockResolvedValue({ document_id: 'doc-1' })
    getSessionIngestion.mockRejectedValue(Object.assign(new Error('boom'), { status: 0 }))
    const wrapper = mountView()
    await flushPromises()
    const file = new File(['pdf-bytes'], 'notes.pdf', { type: 'application/pdf' })
    const input = wrapper.get('[data-testid="session-upload-input"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()
    await flushPromises()
    const failed = wrapper.find('[data-testid="upload-status-failed"]')
    expect(failed.exists()).toBe(true)
    expect(failed.text()).toContain('Upload status unavailable')
    // And the banner gets the failed flag so it can offer Retry.
    expect(wrapper.findComponent(ReferenceStatusBannerStub).props('failed')).toBe(true)
  })

  // E-15: still pending at the wall-clock ceiling is not a chip-worthy outcome.
  // ReferenceStatusBanner owns steady-state ingestion status, so the chip clears
  // and the banner carries it from there - nothing is left stuck.
  it('clears the upload chip at the poll ceiling and leaves the banner to it', async () => {
    vi.useFakeTimers()

    try {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      validateFile.mockReturnValue({ ok: true })
      uploadDocument.mockResolvedValue({ document_id: 'doc-1' })
      getSessionIngestion.mockResolvedValue({
        status: 'pending',
        documents: [{ id: 'doc-1', filename: 'notes.pdf', status: 'pending' }],
      })
      const wrapper = mountView()
      await flushPromises()
      const file = new File(['pdf-bytes'], 'notes.pdf', { type: 'application/pdf' })
      const input = wrapper.get('[data-testid="session-upload-input"]')
      Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
      await input.trigger('change')
      await flushPromises()
      expect(wrapper.find('[data-testid="upload-status-pending"]').text()).toContain('Uploading')

      await vi.advanceTimersByTimeAsync(WATCH_CEILING_MS)
      await flushPromises()
      expect(wrapper.find('[data-testid="upload-status-pending"]').exists()).toBe(false)
      expect(wrapper.text()).not.toContain('still processing')
    } finally {
      vi.useRealTimers()
    }
  })

  // A poll started in session A must not paint A's status into session B after
  // a sidebar switch (same route component instance, no remount), and must not
  // leave B's attach button locked behind A's in-flight upload.
  it('a session switch invalidates an in-flight upload poll', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async (id) => {
      setupSession({ id })
    })
    validateFile.mockReturnValue({ ok: true })
    uploadDocument.mockResolvedValue({ document_id: 'doc-1' })
    let resolveStatus
    getSessionIngestion.mockImplementation(
      () =>
        new Promise((res) => {
          resolveStatus = res
        }),
    )
    const wrapper = mountView({ id: 's1' })
    await flushPromises()
    const file = new File(['pdf-bytes'], 'notes.pdf', { type: 'application/pdf' })
    const input = wrapper.get('[data-testid="session-upload-input"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises() // upload resolved; first status poll still pending

    await wrapper.setProps({ id: 's2' }) // switch sessions mid-ingestion
    await flushPromises()

    // B must not inherit A's upload lock while the stale poll is still pending.
    expect(wrapper.findComponent(Composer).props('uploading')).toBe(false)

    // the superseded poll resolves late
    resolveStatus({ status: 'ready', documents: [{ id: 'doc-1', status: 'ready' }] })
    await flushPromises()

    // The stale result must not paint A's status banner into B.
    expect(wrapper.find('[data-testid="upload-status-ready"]').exists()).toBe(false)
    expect(wrapper.findComponent(Composer).props('uploading')).toBe(false)
  })

  // I-09: the 415 (and friends) carry an actionable server message - prefer
  // it over the generic friendlyError copy.
  it('upload failure surfaces the backend detail message when present', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    validateFile.mockReturnValue({ ok: true })
    uploadDocument.mockRejectedValue(
      Object.assign(new Error('415'), {
        status: 415,
        body: {
          detail: {
            code: 'CONTENT_TYPE_MISMATCH',
            message: 'file content does not match its extension',
          },
        },
      }),
    )
    const wrapper = mountView()
    await flushPromises()
    const file = new File(['pdf-bytes'], 'notes.pdf', { type: 'application/pdf' })
    const input = wrapper.get('[data-testid="session-upload-input"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()
    expect(wrapper.text()).toContain('file content does not match its extension')
  })

  it('rejects an oversize file client-side without uploading (H5)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    const file = new File(['x'], 'huge.pdf', { type: 'application/pdf' })
    Object.defineProperty(file, 'size', { value: 25 * 1024 * 1024 + 1 })
    validateFile.mockReturnValue({ ok: false, reason: 'huge.pdf is too large (max 25 MB).' })
    const input = wrapper.get('[data-testid="session-upload-input"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()
    expect(uploadDocument).not.toHaveBeenCalled()
    const failed = wrapper.find('[data-testid="upload-status-failed"]')
    expect(failed.exists()).toBe(true)
    expect(failed.text()).toContain('too large')
  })

  it('rejects an unsupported file type client-side without uploading (H5)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    // .exe is not in the accepted set (PDF/PPTX/TXT/MD); validateFile returns not-ok.
    const file = new File(['x'], 'malware.exe', { type: 'application/octet-stream' })
    validateFile.mockReturnValue({
      ok: false,
      reason: 'malware.exe is not a supported type. Use PDF, PPTX, TXT, or MD.',
    })
    const input = wrapper.get('[data-testid="session-upload-input"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()
    expect(uploadDocument).not.toHaveBeenCalled()
    expect(wrapper.find('[data-testid="upload-status-failed"]').exists()).toBe(true)
  })

  it('describes the disabled composer with the cap banner via aria-describedby (WCAG 4.1.2)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession({ dailyCap: { used: 10, cap: 10, resets_at: '2026-05-24T00:00:00Z' } })
    })
    const wrapper = mountView()
    await flushPromises()
    const textarea = wrapper.get('[data-testid="session-input"]')
    expect(textarea.attributes('aria-describedby')).toContain('cap-banner-daily')
    expect(wrapper.find('#cap-banner-daily').exists()).toBe(true)
  })

  it('disables the composer during a switch when currentSession still lags props.id', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(() => new Promise(() => {}))
    // currentSession still belongs to the PREVIOUS session (open), we navigate to s2.
    store.currentSession = { id: 's1', topic: 'Old', ended_at: null }
    store.currentSessionId = 's1'
    store.detailLoading = true
    store.sessions = [{ id: 's2', topic: 'New' }]
    const wrapper = mountView({ id: 's2' })
    await flushPromises()
    const composer = wrapper.findComponent(Composer)
    // Composer renders (isEnded is false via discriminator) but must be disabled
    // (canSend false because canEnd's discriminator fails id match).
    expect(composer.exists()).toBe(true)
    expect(composer.props('disabled')).toBe(true)
  })

  it('renders a quiet notice when store.followupNotice is set', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('[data-testid="followup-notice"]').exists()).toBe(false)
    store.followupNotice = 'Daily message limit reached - recap saved, tutor follow-up skipped.'
    await nextTick()
    const notice = wrapper.find('[data-testid="followup-notice"]')
    expect(notice.exists()).toBe(true)
    expect(notice.text()).toContain('Daily message limit reached')
    expect(notice.attributes('role')).toBe('status')
  })

  it('renders streaming bubble when store.streamingMessage is set', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    store.streamingMessage = {
      role: 'assistant',
      content: 'streaming text',
      tool_calls: [],
      citations: [],
    }
    await nextTick()
    const bubble = wrapper.find('[data-testid="msg-streaming"]')
    expect(bubble.exists()).toBe(true)
    expect(bubble.text()).toContain('streaming text')
  })

  // F-18: MessageList is no longer a live region (it spammed SRs with every
  // token mutation). A single discrete status region announces exactly the
  // start/finish transitions instead, driven off store.streamState.
  it('announces stream start and finish discretely (F-18)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    const region = wrapper.get('[data-testid="stream-status"]')
    expect(region.attributes('role')).toBe('status')
    expect(region.attributes('aria-live')).toBe('polite')
    expect(region.text()).toBe('')

    store.streamState = 'streaming'
    await nextTick()
    expect(region.text()).toBe('Tutor is replying.')

    store.streamState = 'idle'
    await nextTick()
    expect(region.text()).toBe('Reply finished.')
  })

  // The store's stream state machine has intermediate members beyond
  // idle/streaming (tool_running, stopping) — the announcement must not
  // re-fire "Tutor is replying." on every intermediate hop, only on the
  // idle -> non-idle and non-idle -> idle edges.
  it('does not re-announce start on tool_running/stopping hops (F-18)', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'loadSession').mockImplementation(async () => {
      setupSession()
    })
    const wrapper = mountView()
    await flushPromises()
    const region = wrapper.get('[data-testid="stream-status"]')

    store.streamState = 'streaming'
    await nextTick()
    expect(region.text()).toBe('Tutor is replying.')

    store.streamState = 'tool_running'
    await nextTick()
    expect(region.text()).toBe('Tutor is replying.')

    store.streamState = 'streaming'
    await nextTick()
    expect(region.text()).toBe('Tutor is replying.')

    store.streamState = 'idle'
    await nextTick()
    expect(region.text()).toBe('Reply finished.')
  })

  describe('diagnostic consent card', () => {
    it('shows the card when knowledge_level is null and no check is pending', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(true)
    })

    it('hides the card when knowledge_level is set', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: 'beginner' }, etag: 't1' })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(false)
    })

    it('hides the card while a check batch is open', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      store.pendingCheck = { gap: 'g', total: 1, currentIndex: 0, viewIndex: 0, items: [] }
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(false)
    })

    it('quiz button sends the canned message through the store', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="diag-quiz"]').trigger('click')
      await flushPromises()
      expect(sendSpy).toHaveBeenCalledWith({ text: 'Quiz me to gauge my level' })
    })

    it('level button PATCHes the profile with the etag and hides the card', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      patchProfile.mockResolvedValue({ profile: { knowledge_level: 'advanced' }, etag: 't2' })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="diag-level-advanced"]').trigger('click')
      await flushPromises()
      expect(patchProfile).toHaveBeenCalledWith('s1', { knowledge_level: 'advanced' }, 't1')
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(false)
    })

    it('level button also sends a declaration message so the tutor sees the answer', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      patchProfile.mockResolvedValue({ profile: { knowledge_level: 'advanced' }, etag: 't2' })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="diag-level-advanced"]').trigger('click')
      await flushPromises()
      expect(sendSpy).toHaveBeenCalledWith({ text: "I'd say my level is advanced." })
    })

    // #354: the topic card under the first at-level reply.
    const TOPIC_CARD = {
      mode: 'broad',
      topic: 'Calculus',
      items: [
        { label: 'Limits', hint: null },
        { label: 'Derivatives', hint: null },
        { label: 'Integrals', hint: null },
      ],
    }

    const withCard = (extra = []) => [
      { role: 'assistant', content: 'Calculus studies change.', topic_suggestions: TOPIC_CARD },
      ...extra,
    ]

    const levelSet = () =>
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: 'beginner' }, etag: 't1' })

    it('renders the topic card under the latest tutor reply that carries one', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession({ messages: withCard() })
      })
      levelSet()
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="topic-suggest-card"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(false)
    })

    it('a tapped topic line sends a learner message', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession({ messages: withCard() })
      })
      const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
      levelSet()
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="topic-line-1"]').trigger('click')
      await flushPromises()
      expect(sendSpy).toHaveBeenCalledWith({ text: "Let's start with Derivatives" })
    })

    it('closes once a learner turn follows the card (reload or tap)', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession({ messages: withCard([{ role: 'user', content: 'Limits please' }]) })
      })
      levelSet()
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="topic-suggest-card"]').exists()).toBe(false)
    })

    it('dismiss hides the card and survives a reload of the session', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession({ messages: withCard() })
      })
      levelSet()
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="topic-dismiss"]').trigger('click')
      expect(wrapper.find('[data-testid="topic-suggest-card"]').exists()).toBe(false)
      wrapper.unmount()
      const again = mountView()
      await flushPromises()
      expect(again.find('[data-testid="topic-suggest-card"]').exists()).toBe(false)
    })

    it('level button does not send a declaration message when the PATCH fails', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      const sendSpy = vi.spyOn(store, 'sendMessageStreaming').mockResolvedValue()
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      patchProfile.mockRejectedValue(new Error('network down'))
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="diag-level-beginner"]').trigger('click')
      await flushPromises()
      expect(sendSpy).not.toHaveBeenCalled()
    })

    it('412 on PATCH refetches the profile and hides the card if the level is now set', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValueOnce({ profile: { knowledge_level: null }, etag: 't1' })
      patchProfile.mockRejectedValue(Object.assign(new Error('precondition'), { status: 412 }))
      getSessionProfile.mockResolvedValueOnce({
        profile: { knowledge_level: 'beginner' },
        etag: 't2',
      })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="diag-level-beginner"]').trigger('click')
      await flushPromises()
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(false)
    })

    it('dismiss hides the card locally', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="diag-dismiss"]').trigger('click')
      await flushPromises()
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(false)
    })

    // A conversational decline ("no thanks, just teach me") writes no level, so
    // knowledge_level stays null forever and the card would otherwise render for
    // the rest of the session. Two completed tutor turns with the level still
    // null are treated as an implicit decline.
    it('soft-dismisses the card after two completed tutor turns with a still-null level', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(true)

      store.streamState = 'streaming'
      await nextTick()
      store.streamState = 'idle'
      await nextTick()
      await flushPromises()
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(true)

      store.streamState = 'streaming'
      await nextTick()
      store.streamState = 'idle'
      await nextTick()
      await flushPromises()
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(false)
    })

    it('a session switch resets the soft-dismiss turn counter', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async (id) => {
        setupSession({ id })
      })
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      const wrapper = mountView({ id: 's1' })
      await flushPromises()

      store.streamState = 'streaming'
      await nextTick()
      store.streamState = 'idle'
      await nextTick()
      await flushPromises()

      await wrapper.setProps({ id: 's2' })
      await flushPromises()

      store.streamState = 'streaming'
      await nextTick()
      store.streamState = 'idle'
      await nextTick()
      await flushPromises()
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(true)
    })

    it('X-dismissal persists across a remount of the same session', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      const first = mountView()
      await flushPromises()
      await first.get('[data-testid="diag-dismiss"]').trigger('click')
      await flushPromises()
      first.unmount()

      const second = mountView()
      await flushPromises()
      expect(second.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(false)
    })

    it('a dismissal in one session does not hide the card in another', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async (id) => {
        setupSession({ id })
      })
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      const first = mountView({ id: 's1' })
      await flushPromises()
      await first.get('[data-testid="diag-dismiss"]').trigger('click')
      await flushPromises()
      first.unmount()

      const second = mountView({ id: 's2' })
      await flushPromises()
      expect(second.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(true)
    })

    it('a session switch invalidates an in-flight level PATCH', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async (id) => {
        setupSession({ id })
      })
      getSessionProfile.mockImplementation((id) =>
        id === 's1'
          ? Promise.resolve({ profile: { knowledge_level: null }, etag: 't1' })
          : Promise.resolve({ profile: { knowledge_level: null }, etag: 't3' }),
      )
      let resolvePatch
      patchProfile.mockImplementation(
        () =>
          new Promise((res) => {
            resolvePatch = res
          }),
      )
      const wrapper = mountView({ id: 's1' })
      await flushPromises()
      await wrapper.get('[data-testid="diag-level-advanced"]').trigger('click')
      await flushPromises() // PATCH sent from s1, still pending

      await wrapper.setProps({ id: 's2' }) // switch sessions mid-PATCH
      await flushPromises()

      // s2's own fetch shows the card (its knowledge_level is null too).
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(true)

      resolvePatch({ profile: { knowledge_level: 'advanced' }, etag: 't2' }) // stale s1 PATCH resolves late
      await flushPromises()

      // The stale PATCH response must not clobber s2's freshly-fetched profile.
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(true)
    })

    // Re-review finding: onDiagLevel's finally must not clear diagLevelBusy
    // for a stale (previous-session) PATCH resolving after a same-session
    // PATCH is already in flight, else the double-PATCH window (F5) reopens.
    it('a stale PATCH resolving late does not clobber a newer same-session PATCH busy-guard', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async (id) => {
        setupSession({ id })
      })
      getSessionProfile.mockImplementation((id) =>
        id === 's1'
          ? Promise.resolve({ profile: { knowledge_level: null }, etag: 't1' })
          : Promise.resolve({ profile: { knowledge_level: null }, etag: 't3' }),
      )
      const resolvers = []
      patchProfile.mockImplementation(
        () =>
          new Promise((res, rej) => {
            resolvers.push({ res, rej })
          }),
      )
      const wrapper = mountView({ id: 's1' })
      await flushPromises()
      await wrapper.get('[data-testid="diag-level-advanced"]').trigger('click')
      await flushPromises() // PATCH_A sent from s1, still pending

      await wrapper.setProps({ id: 's2' }) // switch sessions mid-PATCH
      await flushPromises()
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(true)

      await wrapper.get('[data-testid="diag-level-advanced"]').trigger('click')
      await flushPromises() // PATCH_B sent from s2, still pending
      expect(patchProfile).toHaveBeenCalledTimes(2)

      resolvers[0].res({ profile: { knowledge_level: 'advanced' }, etag: 't2' }) // stale PATCH_A resolves late
      await flushPromises()

      // Click level again on s2 while PATCH_B is still in flight. A correctly
      // session-guarded finally must leave diagLevelBusy true (busy belongs
      // to s2's own pending PATCH_B), so this third click must be blocked.
      await wrapper.get('[data-testid="diag-level-advanced"]').trigger('click')
      await flushPromises()

      expect(patchProfile).toHaveBeenCalledTimes(2)
    })

    // F4: the card must never paint over the skeleton (or flash) before the
    // session detail has resolved, even if the best-effort profile fetch
    // (which is not gated on loadSession) comes back with a null level.
    it('does not show the card while detail is loading (F4)', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(() => new Promise(() => {}))
      store.detailLoading = true
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      const wrapper = mountView({ id: 's1' })
      await flushPromises()
      expect(wrapper.find('[data-testid="session-messages-skeleton"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(false)
    })

    // F2: a conversational level declaration (agent-side update_topic_profile
    // during the turn) is only visible to us via a refetch. Once a tutor turn
    // finishes (stream goes back to idle), refetch so the card hides itself
    // instead of lingering with a stale null level.
    it('refetches the profile when a tutor turn completes and hides the card if the level is now set (F2)', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValueOnce({ profile: { knowledge_level: null }, etag: 't1' })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(true)
      expect(getSessionProfile).toHaveBeenCalledTimes(1)

      getSessionProfile.mockResolvedValueOnce({
        profile: { knowledge_level: 'intermediate' },
        etag: 't2',
      })
      store.streamState = 'streaming'
      await nextTick()
      store.streamState = 'idle'
      await flushPromises()

      expect(getSessionProfile).toHaveBeenCalledTimes(2)
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(false)
    })

    // Cue-lands, end to end: the cue column is fed by the same per-turn
    // refetch, and a cue that arrives mid-session writes itself in.
    it('feeds the cue column from the per-turn profile refetch', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValueOnce({
        profile: {
          knowledge_level: 'beginner',
          confirmed_gaps: [],
          mastered_concepts: [],
          focus_target_gap: null,
        },
        etag: 't1',
      })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.findAll('[data-testid="cue-gap"]')).toHaveLength(0)

      getSessionProfile.mockResolvedValueOnce({
        profile: {
          knowledge_level: 'beginner',
          confirmed_gaps: [{ name: 'ATP yield', evidence_type: null, last_event_at: null }],
          mastered_concepts: [],
          focus_target_gap: null,
        },
        etag: 't2',
      })
      store.streamState = 'streaming'
      await nextTick()
      store.streamState = 'idle'
      await flushPromises()

      const gaps = wrapper.findAll('[data-testid="cue-gap"]')
      expect(gaps).toHaveLength(1)
      expect(gaps[0].text()).toContain('ATP yield')
      expect(gaps[0].classes()).toContain('is-fresh')
    })

    // Redesign 2026-09-10 (Cornell Page, phase B1): the turn-end refetch used
    // to be gated on the consent card still being live. The cue column now
    // reads the same payload, and the store only writes topic_profile on
    // loadSession, so the refetch has to run every turn or the cues go stale
    // for the rest of the session. The card must still stay dismissed.
    it('still refetches on stream idle when the card is dismissed, and stays dismissed (F2)', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValueOnce({ profile: { knowledge_level: null }, etag: 't1' })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="diag-dismiss"]').trigger('click')
      await flushPromises()
      expect(getSessionProfile).toHaveBeenCalledTimes(1)

      getSessionProfile.mockResolvedValueOnce({ profile: { knowledge_level: null }, etag: 't2' })
      store.streamState = 'streaming'
      await nextTick()
      store.streamState = 'idle'
      await flushPromises()

      expect(getSessionProfile).toHaveBeenCalledTimes(2)
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(false)
    })

    // F3: a 412 can be a stale-etag false alarm rather than a real conflict.
    // If the refetch shows the level is STILL unset, retry the PATCH once
    // with the fresh etag rather than silently dropping the user's click.
    it('412 with a still-null refetch retries the PATCH once and hides the card on success (F3)', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValueOnce({ profile: { knowledge_level: null }, etag: 't1' })
      patchProfile.mockRejectedValueOnce(Object.assign(new Error('precondition'), { status: 412 }))
      getSessionProfile.mockResolvedValueOnce({ profile: { knowledge_level: null }, etag: 't2' })
      patchProfile.mockResolvedValueOnce({ profile: { knowledge_level: 'beginner' }, etag: 't3' })
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="diag-level-beginner"]').trigger('click')
      await flushPromises()

      expect(patchProfile).toHaveBeenCalledTimes(2)
      expect(patchProfile).toHaveBeenNthCalledWith(2, 's1', { knowledge_level: 'beginner' }, 't2')
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(false)
      expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    })

    it('412 retry failure surfaces the inline save error (F3)', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValueOnce({ profile: { knowledge_level: null }, etag: 't1' })
      patchProfile.mockRejectedValueOnce(Object.assign(new Error('precondition'), { status: 412 }))
      getSessionProfile.mockResolvedValueOnce({ profile: { knowledge_level: null }, etag: 't2' })
      patchProfile.mockRejectedValueOnce(new Error('network down'))
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="diag-level-beginner"]').trigger('click')
      await flushPromises()

      expect(patchProfile).toHaveBeenCalledTimes(2)
      expect(wrapper.find('[data-testid="diagnostic-consent-card"]').exists()).toBe(true)
      expect(wrapper.get('[role="alert"]').text()).toBe('Could not save your level. Try again.')
    })

    // F5: a rapid second click before the first PATCH resolves must not fire
    // a second PATCH with the same (now-stale) etag.
    it('a rapid second level click does not fire a second PATCH (F5)', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValueOnce({ profile: { knowledge_level: null }, etag: 't1' })
      let resolvePatch
      patchProfile.mockImplementation(
        () =>
          new Promise((res) => {
            resolvePatch = res
          }),
      )
      const wrapper = mountView()
      await flushPromises()
      const btn = wrapper.get('[data-testid="diag-level-beginner"]')
      btn.trigger('click')
      btn.trigger('click')
      await flushPromises()

      expect(patchProfile).toHaveBeenCalledTimes(1)
      resolvePatch({ profile: { knowledge_level: 'beginner' }, etag: 't2' })
      await flushPromises()
    })

    // F6: quiz-start failures must surface on the card (diagError), matching
    // the level path, instead of the generic session error banner.
    it('quiz failures surface an inline card error instead of the session error banner (F6)', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValueOnce({ profile: { knowledge_level: null }, etag: 't1' })
      vi.spyOn(store, 'sendMessageStreaming').mockRejectedValue(new Error('boom'))
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="diag-quiz"]').trigger('click')
      await flushPromises()

      expect(wrapper.find('[data-testid="session-error"]').exists()).toBe(false)
      expect(wrapper.get('[data-testid="diagnostic-consent-card"] [role="alert"]').text()).toBe(
        'Could not start the quiz. Try again.',
      )
    })
  })

  describe('load earlier messages', () => {
    // setupSession() alone leaves store.detailLoading true until the real
    // (unmocked) loadSession fetch settles, which is exactly what every other
    // describe block in this file avoids by driving setupSession through a
    // loadSession spy. Do the same here so these assertions run against the
    // loaded (v-else) branch deterministically instead of racing a live fetch.
    it('shows the button only when hasMoreMessages', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession({
          id: 's1',
          messages: [{ role: 'user', content: 'hi', message_id: 9 }],
          hasMoreMessages: true,
        })
      })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="load-earlier"]').exists()).toBe(true)
    })

    it('hides the button when history is exhausted', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession({ id: 's1', messages: [{ role: 'user', content: 'hi', message_id: 9 }] })
      })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="load-earlier"]').exists()).toBe(false)
    })

    it('click calls store.loadEarlierMessages and disables while pending', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession({
          id: 's1',
          messages: [{ role: 'user', content: 'hi', message_id: 9 }],
          hasMoreMessages: true,
        })
      })
      const spy = vi.spyOn(store, 'loadEarlierMessages').mockResolvedValue()
      const wrapper = mountView()
      await flushPromises()
      await wrapper.get('[data-testid="load-earlier"]').trigger('click')
      expect(spy).toHaveBeenCalled()
    })

    it('shows retry copy when the page fetch failed', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession({
          id: 's1',
          messages: [{ role: 'user', content: 'hi', message_id: 9 }],
          hasMoreMessages: true,
        })
        store.loadEarlierError = 'boom'
      })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.get('[data-testid="load-earlier"]').text()).toMatch(/retry/i)
    })
  })

  // R2 (UI audit 2026-09-13): at 390x844 the check card pinned in the foot took
  // ~420px and left the transcript ~190px (0px with the cue strip expanded).
  // #346 made the transcript the card's only home; the width stub guards
  // against a width-dependent placement coming back.
  describe('check card placement', () => {
    const realMatchMedia = window.matchMedia

    function stubMatchMedia(matches) {
      window.matchMedia = vi.fn().mockReturnValue({
        matches,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })
    }

    function openBatch(store) {
      store.pendingCheck = {
        gap: 'ATP yield',
        total: 1,
        currentIndex: 0,
        viewIndex: 0,
        items: [{ question: 'How many ATP?', options: ['30', '38'], status: 'pending' }],
      }
    }

    afterEach(() => {
      window.matchMedia = realMatchMedia
    })

    // #346: the document is the scroller, so the card scrolls with the page at
    // every width -- the foot carries only the status slot and the composer.
    it.each([
      ['below 900px', true],
      ['at 900px and above', false],
    ])('renders the card in the transcript %s', async (_label, narrow) => {
      stubMatchMedia(narrow)
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession({ messages: [{ role: 'user', content: 'hi', message_id: 9 }] })
        openBatch(store)
      })
      const wrapper = mountView()
      await flushPromises()

      expect(wrapper.findAllComponents(CheckQuestion)).toHaveLength(1)
      expect(
        wrapper.find('[data-testid="session-messages"] [data-testid="check-card"]').exists(),
      ).toBe(true)
      expect(wrapper.find('.notes-foot [data-testid="check-card"]').exists()).toBe(false)
    })
  })

  // #346: whole-page scroll. The document scrolls, not the .messages box; the
  // level picker scrolls with the transcript and autoscroll drives the window.
  describe('whole-page scroll', () => {
    let scrollSpy

    beforeEach(() => {
      scrollSpy = vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
    })

    afterEach(() => {
      scrollSpy.mockRestore()
      delete document.documentElement.scrollHeight
      delete window.scrollY
    })

    function stubDocHeight(getHeight) {
      Object.defineProperty(document.documentElement, 'scrollHeight', {
        configurable: true,
        get: getHeight,
      })
    }

    it('does not lock document scroll while mounted', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      const wrapper = mountView()
      await flushPromises()

      expect(document.body.classList.contains('chat-locked')).toBe(false)
      expect(document.body.classList.contains('session-page')).toBe(true)
      wrapper.unmount()
      expect(document.body.classList.contains('session-page')).toBe(false)
    })

    it('resets the document scroll on leave so the next route starts at the top', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      const wrapper = mountView()
      await flushPromises()
      scrollSpy.mockClear()

      wrapper.unmount()
      expect(scrollSpy).toHaveBeenCalledWith(0, 0)
    })

    it('renders the level picker in the transcript, not the foot', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      getSessionProfile.mockResolvedValue({ profile: { knowledge_level: null }, etag: 't1' })
      const wrapper = mountView()
      await flushPromises()

      expect(
        wrapper
          .find('[data-testid="session-messages"] [data-testid="diagnostic-consent-card"]')
          .exists(),
      ).toBe(true)
      expect(wrapper.find('.notes-foot [data-testid="diagnostic-consent-card"]').exists()).toBe(
        false,
      )
    })

    it('scrolls the window to the bottom when a message lands', async () => {
      stubDocHeight(() => 1500)
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession({ messages: [{ role: 'user', content: 'hi', message_id: 9 }] })
      })
      mountView()
      await flushPromises()
      scrollSpy.mockClear()

      store.messages = [...store.messages, { role: 'assistant', content: 'yo', message_id: 10 }]
      await flushPromises()

      expect(scrollSpy).toHaveBeenCalledWith(0, 1500)
    })

    it('keeps the reading position when earlier messages are prepended', async () => {
      let height = 1000
      stubDocHeight(() => height)
      Object.defineProperty(window, 'scrollY', { configurable: true, value: 200 })
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession({
          messages: [{ role: 'user', content: 'hi', message_id: 9 }],
          hasMoreMessages: true,
        })
      })
      vi.spyOn(store, 'loadEarlierMessages').mockImplementation(async () => {
        store.messages = [{ role: 'user', content: 'older', message_id: 8 }, ...store.messages]
        height = 1600
      })
      const wrapper = mountView()
      await flushPromises()
      scrollSpy.mockClear()

      await wrapper.get('[data-testid="load-earlier"]').trigger('click')
      await flushPromises()

      expect(scrollSpy).toHaveBeenCalledTimes(1)
      expect(scrollSpy).toHaveBeenCalledWith(0, 800)
    })

    // #347: follow the stream, stop the moment the learner scrolls up, resume
    // when they return to the bottom. jsdom's innerHeight is 768, so with a
    // 1500px document the bottom is scrollY 732.
    describe('follow-the-stream autoscroll', () => {
      const realMatchMedia = window.matchMedia

      afterEach(() => {
        window.matchMedia = realMatchMedia
      })

      const BOTTOM_Y = 1500 - 768

      function setScrollY(y) {
        Object.defineProperty(window, 'scrollY', { configurable: true, value: y })
        window.dispatchEvent(new Event('scroll'))
      }

      function scrollUpFromBottom(to = 300) {
        setScrollY(BOTTOM_Y)
        setScrollY(to)
      }

      async function mountStreaming() {
        stubDocHeight(() => 1500)
        const store = useSessionStore()
        vi.spyOn(store, 'loadSession').mockImplementation(async () => {
          setupSession({ messages: [{ role: 'user', content: 'hi', message_id: 9 }] })
        })
        mountView()
        await flushPromises()
        store.streamingMessage = { role: 'assistant', content: '', tool_calls: [], citations: [] }
        await flushPromises()
        scrollSpy.mockClear()

        return store
      }

      async function growStream(store) {
        store.streamingMessage.content += 'more tokens '
        await flushPromises()
      }

      it('scrolls to the bottom as streamed text grows', async () => {
        const store = await mountStreaming()
        await growStream(store)
        expect(scrollSpy).toHaveBeenCalledWith(expect.objectContaining({ top: 1500 }))
      })

      it('follows tool calls appended mid-stream', async () => {
        const store = await mountStreaming()
        store.streamingMessage.tool_calls.push({ id: 't1', name: 'search', state: 'running' })
        await flushPromises()
        expect(scrollSpy).toHaveBeenCalledWith(expect.objectContaining({ top: 1500 }))
      })

      it('follows a tool call settling from running to done', async () => {
        const store = await mountStreaming()
        store.streamingMessage.tool_calls.push({ id: 't1', name: 'search', state: 'running' })
        await flushPromises()
        scrollSpy.mockClear()
        store.streamingMessage.tool_calls[0].state = 'done'
        await flushPromises()
        expect(scrollSpy).toHaveBeenCalledWith(expect.objectContaining({ top: 1500 }))
      })

      it('stops following on a small upward nudge within the bottom slack', async () => {
        const store = await mountStreaming()
        scrollUpFromBottom(BOTTOM_Y - 10)
        scrollSpy.mockClear()
        await growStream(store)
        expect(scrollSpy).not.toHaveBeenCalled()
      })

      it('stops following on an upward wheel before the scroll event lands', async () => {
        const store = await mountStreaming()
        setScrollY(BOTTOM_Y)
        window.dispatchEvent(new WheelEvent('wheel', { deltaY: -40 }))
        scrollSpy.mockClear()
        await growStream(store)
        expect(scrollSpy).not.toHaveBeenCalled()
      })

      it('keeps following when a shrink clamps the view to the bottom', async () => {
        let height = 1500
        stubDocHeight(() => height)
        const store = await mountStreaming()
        stubDocHeight(() => height)
        setScrollY(BOTTOM_Y)
        height = 1400
        setScrollY(BOTTOM_Y - 100)
        scrollSpy.mockClear()
        await growStream(store)
        expect(scrollSpy).toHaveBeenCalledWith(expect.objectContaining({ top: 1400 }))
      })

      it('stops following once the learner scrolls up', async () => {
        const store = await mountStreaming()
        scrollUpFromBottom()
        scrollSpy.mockClear()
        await growStream(store)
        expect(scrollSpy).not.toHaveBeenCalled()
      })

      it('resumes following when the learner returns to the bottom', async () => {
        const store = await mountStreaming()
        scrollUpFromBottom()
        setScrollY(BOTTOM_Y)
        scrollSpy.mockClear()
        await growStream(store)
        expect(scrollSpy).toHaveBeenCalledWith(expect.objectContaining({ top: 1500 }))
      })

      it('does not cancel on downward scrolling short of the bottom', async () => {
        const store = await mountStreaming()
        setScrollY(100)
        setScrollY(400)
        scrollSpy.mockClear()
        await growStream(store)
        expect(scrollSpy).toHaveBeenCalledWith(expect.objectContaining({ top: 1500 }))
      })

      it('does not yank a scrolled-up learner down when the reply lands', async () => {
        const store = await mountStreaming()
        scrollUpFromBottom()
        scrollSpy.mockClear()
        store.streamingMessage = null
        store.messages = [...store.messages, { role: 'assistant', content: 'yo', message_id: 10 }]
        await flushPromises()
        expect(scrollSpy).not.toHaveBeenCalled()
      })

      it('re-arms following when the learner sends a message', async () => {
        const store = await mountStreaming()
        store.streamingMessage = null
        scrollUpFromBottom()
        scrollSpy.mockClear()
        store.messages = [...store.messages, { role: 'user', content: 'next', message_id: 11 }]
        await flushPromises()
        expect(scrollSpy).toHaveBeenCalledWith(0, 1500)
        scrollSpy.mockClear()
        store.streamingMessage = { role: 'assistant', content: 'a', tool_calls: [], citations: [] }
        await flushPromises()
        expect(scrollSpy).toHaveBeenCalledWith(expect.objectContaining({ top: 1500 }))
      })

      it.each([
        ['smooth by default', false, 'smooth'],
        ['instant under prefers-reduced-motion', true, 'instant'],
      ])('scrolls %s', async (_label, reduce, behavior) => {
        window.matchMedia = vi.fn((query) => ({
          matches: reduce && query === REDUCED_MOTION_QUERY,
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
        }))
        const store = await mountStreaming()
        await growStream(store)
        expect(scrollSpy).toHaveBeenCalledWith({ top: 1500, behavior })
      })
    })
  })

  // D-21: SessionHeader's h1 is gated on a resolved topic, so before the detail
  // fetch lands the page had no h1 at all. A visually-hidden fallback fills the
  // gap -- and only while the gap exists, so the page never carries two h1s.
  describe('page heading (D-21)', () => {
    it('renders a visually-hidden fallback h1 before the topic resolves', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(() => new Promise(() => {}))
      const wrapper = mountView()
      await flushPromises()
      const headings = wrapper.findAll('h1')
      expect(headings).toHaveLength(1)
      expect(headings[0].text()).toBe('Session')
      expect(headings[0].classes()).toContain('sr-only')
    })

    it('drops the fallback once the topic resolves, leaving exactly one h1', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
      })
      const wrapper = mountView()
      await flushPromises()
      const headings = wrapper.findAll('h1')
      expect(headings).toHaveLength(1)
      expect(headings[0].text()).toBe('Calculus')
    })

    it('renders only the not-found h1 on the 404 branch', async () => {
      const store = useSessionStore()
      const err = Object.assign(new Error('not found'), { status: 404 })
      vi.spyOn(store, 'loadSession').mockRejectedValue(err)
      const wrapper = mountView({ id: 'gone' })
      await flushPromises()
      const headings = wrapper.findAll('h1')
      expect(headings).toHaveLength(1)
      expect(headings[0].text()).toBe('Session not found')
    })
  })

  // E-20 / D-25: the composer never locked on an open check (checkLocked was a
  // constant false), so the prop, its Skip button and the store computed went.
  // CheckQuestion owns Skip.
  describe('composer has no check lock (E-20)', () => {
    it('does not render a composer Skip button while a check batch is open', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
        store.pendingCheck = {
          gap: 'ATP yield',
          total: 1,
          currentIndex: 0,
          viewIndex: 0,
          items: [{ question: 'How many ATP?', options: ['30', '38'], status: 'pending' }],
        }
      })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('[data-testid="composer-skip"]').exists()).toBe(false)
      expect(wrapper.findComponent(Composer).props()).not.toHaveProperty('locked')
      expect(store.checkLocked).toBeUndefined()
    })
  })

  // E-17: options were gated on `answered` only, which flips after the POST
  // returns - the in-flight window accepted a second click that the store then
  // dropped silently.
  describe('check answering (E-17)', () => {
    function openBatch(store) {
      store.pendingCheck = {
        gap: 'ATP yield',
        total: 1,
        currentIndex: 0,
        viewIndex: 0,
        items: [
          {
            question: 'How many ATP?',
            options: ['30', '38'],
            status: 'pending',
            selectedIndex: null,
            correctIndex: null,
            correct: null,
            explanation: null,
          },
        ],
      }
    }

    it('passes the store answering flag down to the check card', async () => {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession()
        openBatch(store)
      })
      const wrapper = mountView()
      await flushPromises()
      const card = wrapper.findComponent(CheckQuestion)
      expect(card.props('answering')).toBe(false)
      store.checkAnswering = true
      await nextTick()
      expect(card.props('answering')).toBe(true)
    })
  })

  // #443: the blue tick on the latest tutor turn belongs to the reply that
  // filed the cue. Cues land the way they do in the app: a stream finishes and
  // the profile refetch returns an entry the real CueColumn has not seen.
  describe('cue tick (#443)', () => {
    const profile = (gaps = []) => ({
      profile: {
        knowledge_level: null,
        confirmed_gaps: gaps.map((name) => ({ name, evidence_type: null, last_event_at: null })),
      },
      etag: 't1',
    })

    // A tutor turn as the store runs it: idle -> streaming -> idle, with the
    // reply appended. The nextTick lets the stream-state watcher see both edges.
    function reply(store) {
      return async () => {
        store.streamState = 'streaming'
        await nextTick()
        store.messages = [
          ...store.messages,
          { role: 'assistant', content: `reply ${store.messages.length}` },
        ]
        store.streamState = 'idle'
      }
    }

    const landed = (wrapper) => wrapper.findComponent(MessageList).props('landed')

    // A real router route is reactive; the query cases need the watchers to see
    // a query set after mount.
    beforeEach(() => {
      route = reactive({ query: {} })
    })

    afterEach(() => {
      route = { query: {} }
    })

    async function mountWithLandedCue() {
      const store = useSessionStore()
      vi.spyOn(store, 'loadSession').mockImplementation(async () => {
        setupSession({ messages: [{ role: 'assistant', content: 'hi' }] })
      })
      vi.spyOn(store, 'sendMessageStreaming').mockImplementation(reply(store))
      getSessionProfile.mockResolvedValue(profile())
      const wrapper = mountView()
      await flushPromises()
      getSessionProfile.mockResolvedValue(profile(['joins']))
      await wrapper.get('[data-testid="session-input"]').setValue('teach me joins')
      await wrapper.get('[data-testid="session-send"]').trigger('click')
      await flushPromises()
      expect(landed(wrapper)).toBe(true)

      return { store, wrapper }
    }

    const senders = {
      'the quiz button': async ({ wrapper }) => {
        await wrapper.get('[data-testid="diag-quiz"]').trigger('click')
      },
      'the level declaration': async ({ wrapper }) => {
        patchProfile.mockResolvedValue({ ...profile(['joins']), etag: 't2' })
        await wrapper.get('[data-testid="diag-level-advanced"]').trigger('click')
      },
      'a review seed': async () => {
        route.query.review_gap = 'joins'
      },
      'a ?quiz link': async () => {
        route.query.quiz = '1'
      },
      'a check follow-up': async ({ store, wrapper }) => {
        store.pendingCheck = {
          gap: 'joins',
          total: 1,
          currentIndex: 1,
          viewIndex: 0,
          items: [
            {
              question: 'Which join keeps unmatched left rows?',
              options: ['inner', 'left'],
              status: 'answered',
              selectedIndex: 1,
              correctIndex: 1,
              correct: true,
              explanation: null,
            },
          ],
        }
        vi.spyOn(store, 'completeCheck').mockImplementation(async () => {
          store.pendingCheck = null
          await reply(store)()
        })
        await nextTick()
        wrapper.findComponent(CheckQuestion).vm.$emit('done')
      },
    }

    it.each(Object.keys(senders))(
      'a reply that lands no cue does not carry the previous tick: %s',
      async (name) => {
        const ctx = await mountWithLandedCue()
        const before = ctx.store.messages.length
        await senders[name](ctx)
        await flushPromises()
        expect(ctx.store.messages.length).toBe(before + 1)
        expect(landed(ctx.wrapper)).toBe(false)
      },
    )

    it('a reply that lands a cue gets the tick', async () => {
      const ctx = await mountWithLandedCue()
      getSessionProfile.mockResolvedValue(profile(['joins', 'subqueries']))
      await ctx.wrapper.get('[data-testid="diag-quiz"]').trigger('click')
      await flushPromises()
      expect(landed(ctx.wrapper)).toBe(true)
    })

    it('typing clears the tick', async () => {
      const { wrapper } = await mountWithLandedCue()
      await wrapper.get('[data-testid="session-input"]').setValue('and outer joins?')
      await wrapper.get('[data-testid="session-send"]').trigger('click')
      await flushPromises()
      expect(landed(wrapper)).toBe(false)
    })
  })
})
