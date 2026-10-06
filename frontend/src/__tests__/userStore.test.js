import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '@/stores/user.js'
import { _resetApiCache } from '@/services/apiClient.js'

const key = (uid) => `crux:user:v1:${uid}`

// F-46: completeOnboarding/updateProfile/hydrateFromServer write through to
// the backend via the real apiClient (dynamic import), so these tests mock
// global fetch -- the same pattern used in apiWrappers.test.js -- rather
// than mocking the apiClient module directly.
function ok(body) {
  return Promise.resolve({
    ok: true,
    status: 200,
    headers: { get: () => null },
    text: () => Promise.resolve(JSON.stringify(body)),
  })
}

describe('user store', () => {
  let fetchMock

  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    // F-18: apiClient's GET cache is module state; without this a later case
    // gets an earlier case's /me body.
    _resetApiCache()
    fetchMock = vi.fn().mockReturnValue(ok({}))
    globalThis.fetch = fetchMock
  })

  it('initial state is empty', () => {
    const u = useUserStore()
    expect(u.name).toBeNull()
    expect(u.onboardingComplete).toBe(false)
    expect(u.hydrated).toBe(false)
  })

  it('loadFromLocalStorage hydrates from saved data', () => {
    localStorage.setItem(
      key('u1'),
      JSON.stringify({
        name: 'Eddy',
        interactionPreferences: { feedback: 'hints' },
        onboardingComplete: true,
      }),
    )
    const u = useUserStore()
    u.setActiveUser('u1')
    expect(u.name).toBe('Eddy')
    expect(u.onboardingComplete).toBe(true)
  })

  it('loadFromLocalStorage drops a corrupt entry', () => {
    localStorage.setItem(key('u1'), '{not json')
    const u = useUserStore()
    u.setActiveUser('u1')
    u.loadFromLocalStorage()
    expect(localStorage.getItem(key('u1'))).toBeNull()
    expect(u.name).toBeNull()
  })

  it('loadFromLocalStorage does nothing when no entry', () => {
    const u = useUserStore()
    u.setActiveUser('u1')
    expect(u.name).toBeNull()
  })

  it('completeOnboarding sets name, prefs and persists', async () => {
    const u = useUserStore()
    u.setActiveUser('u1')
    await u.completeOnboarding({ name: 'Edward', feedback: 'direct_answers' })
    expect(u.name).toBe('Edward')
    expect(u.interactionPreferences.feedback).toBe('direct_answers')
    expect(u.onboardingComplete).toBe(true)
    const raw = JSON.parse(localStorage.getItem(key('u1')))
    expect(raw.name).toBe('Edward')
    // wrote through to PATCH /me
    const call = fetchMock.mock.calls[0]
    expect(call[0]).toContain('/me')
    expect(call[1].method).toBe('PATCH')
  })

  it('completeOnboarding falls back to "Learner" when name is empty', async () => {
    const u = useUserStore()
    u.setActiveUser('u1')
    await u.completeOnboarding({ name: '   ', feedback: 'hints' })
    expect(u.name).toBe('Learner')
  })

  it('resetOnboarding clears everything', async () => {
    const u = useUserStore()
    u.setActiveUser('u1')
    await u.completeOnboarding({ name: 'A', feedback: 'hints' })
    u.resetOnboarding()
    expect(u.name).toBeNull()
    expect(u.onboardingComplete).toBe(false)
    expect(localStorage.getItem(key('u1'))).toBeNull()
  })

  // R2-25: clearForAccountDeletion is called right after DELETE /me succeeds.
  // It delegates to resetOnboarding() for the wipe -- same behavior, kept as
  // its own name so the call site reads as "account just got deleted", not
  // "onboarding restarted".
  it('clearForAccountDeletion wipes memory and removes the persisted key', async () => {
    const u = useUserStore()
    u.setActiveUser('user-a')
    await u.completeOnboarding({ name: 'Alice', feedback: 'direct' })
    expect(localStorage.getItem(key('user-a'))).not.toBeNull()

    u.clearForAccountDeletion()
    expect(u.name).toBeNull()
    expect(u.onboardingComplete).toBe(false)
    expect(localStorage.getItem(key('user-a'))).toBeNull()
  })

  it('updateProfile merges name and feedback', async () => {
    const u = useUserStore()
    u.setActiveUser('u1')
    await u.completeOnboarding({ name: 'A', feedback: 'hints' })
    await u.updateProfile({ name: 'B' })
    expect(u.name).toBe('B')
    expect(u.interactionPreferences.feedback).toBe('hints')
    await u.updateProfile({ feedback: 'direct_answers' })
    expect(u.interactionPreferences.feedback).toBe('direct_answers')
  })

  // #357: each Learning-tab control autosaves on its own, so one change is one
  // PATCH carrying only that field.
  it('updateProfile sends check_ins alone and merges it into preferences', async () => {
    const u = useUserStore()
    u.setActiveUser('u1')
    await u.completeOnboarding({ name: 'A', feedback: 'hints' })
    fetchMock.mockClear()
    await u.updateProfile({ checkIns: 'often' })
    expect(fetchMock).toHaveBeenCalledOnce()
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ check_ins: 'often' })
    expect(u.interactionPreferences).toEqual({ feedback: 'hints', checkIns: 'often' })
    expect(JSON.parse(localStorage.getItem(key('u1'))).interactionPreferences.checkIns).toBe(
      'often',
    )
  })

  it('updateProfile sends reply_length alone and merges it into preferences', async () => {
    const u = useUserStore()
    u.setActiveUser('u1')
    await u.completeOnboarding({ name: 'A', feedback: 'hints' })
    fetchMock.mockClear()
    await u.updateProfile({ replyLength: 'thorough' })
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ reply_length: 'thorough' })
    expect(u.interactionPreferences.replyLength).toBe('thorough')
    expect(u.interactionPreferences.feedback).toBe('hints')
  })

  it('completeOnboarding keeps hydrated check-ins and reply length', async () => {
    fetchMock.mockReturnValue(
      ok({
        feedback_pref: 'hints',
        check_ins: 'often',
        reply_length: 'brief',
        onboarding_complete: false,
      }),
    )
    const u = useUserStore()
    u.setActiveUser('u1')
    await u.hydrateFromServer()
    await u.completeOnboarding({ name: 'A', feedback: 'direct_answers' })
    expect(u.interactionPreferences).toEqual({
      feedback: 'direct_answers',
      checkIns: 'often',
      replyLength: 'brief',
    })
  })

  it('updateProfile trims and falls back to "Learner"', async () => {
    const u = useUserStore()
    u.setActiveUser('u1')
    await u.completeOnboarding({ name: 'A', feedback: 'hints' })
    await u.updateProfile({ name: '   ' })
    expect(u.name).toBe('Learner')
  })

  it('namespaces storage per uid — two accounts never share prefs (F-08)', async () => {
    const u = useUserStore()
    u.setActiveUser('user-a')
    await u.completeOnboarding({ name: 'Alice', feedback: 'direct' })

    u.setActiveUser('user-b')
    expect(u.name).toBeNull()
    expect(u.onboardingComplete).toBe(false)

    u.setActiveUser('user-a')
    expect(u.name).toBe('Alice')
    expect(u.onboardingComplete).toBe(true)
  })

  // F-02: sessions/messages of the previous account must not survive a uid
  // change on the same tab (Sidebar skips its fetch when sessions is
  // non-empty, so stale rows would render for the next account).
  it('setActiveUser resets the session store on a uid change (F-02)', async () => {
    const { useSessionStore } = await import('@/stores/session.js')
    const u = useUserStore()
    u.setActiveUser('user-a')
    const s = useSessionStore()
    s.sessions = [{ id: 's1', topic: 'secret topic' }]
    s.currentSessionId = 's1'
    s.messages = [{ role: 'user', content: 'private' }]
    u.setActiveUser('user-b')
    expect(s.sessions).toEqual([])
    expect(s.currentSessionId).toBeNull()
    expect(s.messages).toEqual([])
  })

  it('setActiveUser with the same uid does not reset the session store', async () => {
    const { useSessionStore } = await import('@/stores/session.js')
    const u = useUserStore()
    u.setActiveUser('user-a')
    const s = useSessionStore()
    s.sessions = [{ id: 's1' }]
    u.setActiveUser('user-a') // e.g. a token refresh re-emitting the same uid
    expect(s.sessions).toEqual([{ id: 's1' }])
  })

  it('setActiveUser(null) clears memory but preserves the persisted blob', async () => {
    const u = useUserStore()
    u.setActiveUser('user-a')
    await u.completeOnboarding({ name: 'Alice', feedback: 'direct' })

    u.setActiveUser(null)
    expect(u.name).toBeNull()
    expect(localStorage.getItem('crux:user:v1:user-a')).not.toBeNull()
  })

  it('setActiveUser(null) resets hydrated so a re-login re-hydrates', async () => {
    const u = useUserStore()
    u.setActiveUser('user-a')
    fetchMock.mockReturnValue(
      ok({ display_name: null, feedback_pref: null, onboarding_complete: false }),
    )
    await u.hydrateFromServer()
    expect(u.hydrated).toBe(true)

    u.setActiveUser(null)
    expect(u.hydrated).toBe(false)
  })

  it('persist is a no-op with no active uid', async () => {
    const u = useUserStore()
    await u.completeOnboarding({ name: 'Ghost', feedback: 'direct' })
    expect(localStorage.getItem('crux:user:v1')).toBeNull()
  })

  it('hydrateFromServer overrides local onboarding state', async () => {
    fetchMock.mockReturnValue(
      ok({ display_name: 'Ada', feedback_pref: 'direct', onboarding_complete: true }),
    )
    const u = useUserStore()
    u.setActiveUser('u1')
    await u.hydrateFromServer()
    expect(u.onboardingComplete).toBe(true)
    expect(u.name).toBe('Ada')
    expect(u.interactionPreferences.feedback).toBe('direct')
    expect(u.hydrated).toBe(true)
  })

  it('hydrateFromServer carries check_ins and reply_length', async () => {
    fetchMock.mockReturnValue(
      ok({
        display_name: 'Ada',
        feedback_pref: 'hints',
        check_ins: 'only_when_asked',
        reply_length: 'brief',
        onboarding_complete: true,
      }),
    )
    const u = useUserStore()
    u.setActiveUser('u1')
    await u.hydrateFromServer()
    expect(u.interactionPreferences).toEqual({
      feedback: 'hints',
      checkIns: 'only_when_asked',
      replyLength: 'brief',
    })
  })

  it('hydrateFromServer failure keeps local snapshot and still sets hydrated', async () => {
    localStorage.setItem(
      key('u1'),
      JSON.stringify({
        name: 'Eddy',
        interactionPreferences: { feedback: 'hints' },
        onboardingComplete: true,
      }),
    )
    fetchMock.mockReturnValue(Promise.reject(new Error('network down')))
    const u = useUserStore()
    u.setActiveUser('u1')
    expect(u.onboardingComplete).toBe(true)
    await u.hydrateFromServer()
    expect(u.hydrated).toBe(true)
    expect(u.onboardingComplete).toBe(true)
    expect(u.name).toBe('Eddy')
  })

  // E-09: a failed hydrate used to be indistinguishable from a successful one
  // that found onboardingComplete=false, which force-routed the learner into
  // onboarding with no way out. hydrateFailed lets the router guard tell the
  // two cases apart.
  it('hydrateFromServer failure sets hydrateFailed and leaves onboardingComplete unchanged (E-09)', async () => {
    fetchMock.mockReturnValue(Promise.reject(new Error('network down')))
    const u = useUserStore()
    u.setActiveUser('u1')
    expect(u.onboardingComplete).toBe(false)
    await u.hydrateFromServer()
    expect(u.hydrateFailed).toBe(true)
    expect(u.hydrated).toBe(true)
    expect(u.onboardingComplete).toBe(false)
  })

  it('hydrateFromServer success clears hydrateFailed (E-09)', async () => {
    fetchMock.mockReturnValue(
      ok({ display_name: 'Ada', feedback_pref: 'direct', onboarding_complete: true }),
    )
    const u = useUserStore()
    u.setActiveUser('u1')
    u.hydrateFailed = true
    await u.hydrateFromServer()
    expect(u.hydrateFailed).toBe(false)
  })
})
