import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import router from '@/router/index.js'
import { useAuthStore } from '@/stores/auth.js'
import { useUserStore } from '@/stores/user.js'

function setAuth(authed) {
  const auth = useAuthStore()
  auth.session = authed ? { user: { id: 'u-1' }, access_token: 'tok' } : null
  auth.ready = true
}

describe('router', () => {
  beforeEach(async () => {
    setActivePinia(createPinia())
    setAuth(true)
    await router.push('/')
    await router.isReady()
  })

  it('exposes the expected named routes', () => {
    const names = router.getRoutes().map((r) => r.name)
    expect(names).toEqual(
      expect.arrayContaining([
        'home',
        'onboarding',
        'settings',
        'account',
        'profile-aggregate',
        'new-session',
        'recall',
        'session',
        'session-profile',
        'login',
        'register',
      ]),
    )
  })

  it('has no subject routes', () => {
    const names = router.getRoutes().map((r) => r.name)
    expect(names).not.toContain('subject-new')
    expect(names).not.toContain('subject-overview')
    expect(names).not.toContain('subject-mastery')
  })

  it('redirects the old /review path to /recall', async () => {
    const user = useUserStore()
    user.onboardingComplete = true
    await router.push('/review')
    expect(router.currentRoute.value.path).toBe('/recall')
    expect(router.currentRoute.value.name).toBe('recall')
  })

  it('redirects unauthenticated user to /login', async () => {
    setAuth(false)
    const user = useUserStore()
    user.onboardingComplete = true
    await router.push({ name: 'home' })
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('/profile renders the aggregate profile page instead of redirecting (#362)', async () => {
    const user = useUserStore()
    user.onboardingComplete = true
    const rec = router.getRoutes().find((r) => r.name === 'profile-aggregate')
    expect(rec.redirect).toBeUndefined()
    expect(rec.components.default).toBeTruthy()
    await router.push('/profile')
    expect(router.currentRoute.value.name).toBe('profile-aggregate')
  })

  it('redirects unauthenticated user away from /profile to /login', async () => {
    setAuth(false)
    await router.push({ name: 'profile-aggregate' })
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/profile')
  })

  it('redirects unauthenticated user away from /account to /login', async () => {
    setAuth(false)
    await router.push({ name: 'account' })
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('login redirect preserves the intended path', async () => {
    setAuth(false)
    const user = useUserStore()
    user.onboardingComplete = true
    await router.push('/session/abc')
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/session/abc')
  })

  it('redirects authenticated user away from /login to home', async () => {
    setAuth(true)
    const user = useUserStore()
    user.onboardingComplete = true
    await router.push({ name: 'login' })
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('redirects to onboarding when authed but onboarding incomplete', async () => {
    setAuth(true)
    const user = useUserStore()
    user.onboardingComplete = false
    // Push to a non-default route to avoid hitting the "same route" no-op path
    // when a prior test or beforeEach left us on /onboarding already.
    await router.push({ name: 'settings', params: { tab: 'profile' } })
    expect(router.currentRoute.value.name).toBe('onboarding')
  })

  it('redirects away from onboarding when complete (no retake query)', async () => {
    setAuth(true)
    const user = useUserStore()
    user.onboardingComplete = true
    await router.push({ name: 'settings', params: { tab: 'profile' } })
    await router.push({ name: 'onboarding' })
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('allows onboarding when retake=1 even if complete', async () => {
    setAuth(true)
    const user = useUserStore()
    user.onboardingComplete = true
    await router.push({ name: 'onboarding', query: { retake: '1' } })
    expect(router.currentRoute.value.name).toBe('onboarding')
  })

  it('resolves an unknown path to the not-found route', () => {
    expect(router.resolve('/definitely/not/a/route').name).toBe('not-found')
  })

  it('shows not-found (not login) to an unauthenticated visitor on an unknown path', async () => {
    setAuth(false)
    const user = useUserStore()
    user.onboardingComplete = true
    await router.push('/nope')
    expect(router.currentRoute.value.name).toBe('not-found')
  })

  it('passes :id as a prop to the session route', () => {
    const route = router.getRoutes().find((r) => r.name === 'session')
    expect(route.props.default).toBe(true)
  })

  it('allows an unauthenticated user to reach /register', async () => {
    setAuth(false)
    await router.push({ name: 'register' })
    expect(router.currentRoute.value.name).toBe('register')
  })

  it('redirects an authenticated user away from /register to home', async () => {
    setAuth(true)
    const user = useUserStore()
    user.onboardingComplete = true
    await router.push({ name: 'register' })
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('guard proceeds unauthenticated when auth.init rejects', async () => {
    const auth = useAuthStore()
    auth._resetForTests()
    globalThis.__supabaseAuthStub.getSession.mockRejectedValueOnce(new Error('corrupt session'))
    // Push to a different route than the current one (beforeEach already
    // landed on '/'): a same-route push is a vue-router no-op and skips the
    // guard entirely, which would defeat this test.
    await router.push('/settings') // must not throw
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('does not block navigation on server hydrate when snapshot says onboarding complete', async () => {
    setAuth(true)
    const user = useUserStore()
    user.onboardingComplete = true
    user.hydrated = false
    // A hanging hydrate must not hang navigation: the localStorage snapshot
    // already answers the onboarding question, so the server refresh is
    // background-only.
    const spy = vi.spyOn(user, 'hydrateFromServer').mockReturnValue(new Promise(() => {}))
    const push = router.push({ name: 'settings', params: { tab: 'profile' } })
    await new Promise((r) => setTimeout(r, 0))
    expect(spy).toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('settings')
    await push.catch(() => {})
  })

  it('still awaits hydrate when no snapshot marks onboarding complete (F-46)', async () => {
    setAuth(true)
    const user = useUserStore()
    user.onboardingComplete = false
    user.hydrated = false

    const spy = vi.spyOn(user, 'hydrateFromServer').mockImplementation(async () => {
      user.onboardingComplete = true
      user.hydrated = true
    })

    await router.push({ name: 'settings', params: { tab: 'profile' } })
    expect(spy).toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('settings')
  })

  // E-09: a failed hydrate on a device with no local snapshot used to
  // force-route into onboarding with no way out (hydrateFailed did not
  // exist, so a hydrate failure looked identical to a real
  // onboardingComplete=false). Once hydrate has failed, do not redirect.
  it('does not force-route to onboarding when hydrate has failed (E-09)', async () => {
    setAuth(true)
    const user = useUserStore()
    user.onboardingComplete = false
    user.hydrated = true
    user.hydrateFailed = true
    await router.push({ name: 'home' })
    expect(router.currentRoute.value.name).toBe('home')
  })

  it('still redirects to onboarding when hydrate succeeded and onboarding is incomplete (E-09)', async () => {
    setAuth(true)
    const user = useUserStore()
    user.onboardingComplete = false
    user.hydrated = true
    user.hydrateFailed = false
    await router.push({ name: 'settings', params: { tab: 'profile' } })
    expect(router.currentRoute.value.name).toBe('onboarding')
  })

  it('focuses #main-content after push navigation', async () => {
    setAuth(true)
    const user = useUserStore()
    user.onboardingComplete = true
    const main = document.createElement('main')
    main.id = 'main-content'
    main.setAttribute('tabindex', '-1')
    document.body.appendChild(main)
    await router.push('/') // establish an initial route first
    await router.push({ name: 'settings', params: { tab: 'profile' } }) // any second authenticated route in this suite
    expect(document.activeElement).toBe(main)
    main.remove()
  })

  // D-15: a missing focus target used to fail silently, which is how the
  // chrome-less routes went unnoticed. Navigation must still succeed.
  it('warns in dev and does not throw when #main-content is missing', async () => {
    setAuth(true)
    const user = useUserStore()
    user.onboardingComplete = true
    document.getElementById('main-content')?.remove()
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    await router.push('/') // establish an initial route first
    await expect(
      router.push({ name: 'settings', params: { tab: 'profile' } }),
    ).resolves.toBeUndefined()
    expect(router.currentRoute.value.name).toBe('settings')
    expect(warn).toHaveBeenCalledWith(
      '[router] focus target #main-content not found for',
      '/settings/learning',
    )
    warn.mockRestore()
  })
})
