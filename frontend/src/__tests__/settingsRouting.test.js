import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import router from '../router/index.js'
import { useAuthStore } from '../stores/auth.js'
import { useUserStore } from '../stores/user.js'

// Route-level redirect tests. Auth/onboarding guards are made green so only
// the redirect logic under test decides the destination.
function setAuth(authed) {
  const auth = useAuthStore()
  auth.session = authed ? { user: { id: 'u-1' }, access_token: 'tok' } : null
  auth.ready = true
}

beforeEach(async () => {
  setActivePinia(createPinia())
  setAuth(true)
  const user = useUserStore()
  user.hydrated = true
  user.onboardingComplete = true
  await router.push('/')
  await router.isReady()
})

describe('unified settings routing', () => {
  it('/settings redirects to /settings/learning', async () => {
    await router.push('/settings')
    expect(router.currentRoute.value.fullPath).toBe('/settings/learning')
  })

  it('/profile is its own page now, not a redirect to Settings (#362)', async () => {
    await router.push({ name: 'profile-aggregate' })
    expect(router.currentRoute.value.fullPath).toBe('/profile')
    expect(router.currentRoute.value.name).toBe('profile-aggregate')
    expect(router.currentRoute.value.matched.at(-1).components.default).toBeTruthy()
  })

  it('invalid tab slug redirects to /settings/learning', async () => {
    await router.push('/settings/bogus')
    expect(router.currentRoute.value.fullPath).toBe('/settings/learning')
  })

  it('the old profile tab param redirects to learning', async () => {
    await router.push('/settings/profile')
    expect(router.currentRoute.value.fullPath).toBe('/settings/learning')
  })

  it('the old account tab param redirects to the Account page', async () => {
    await router.push('/settings/account')
    expect(router.currentRoute.value.name).toBe('account')
    expect(router.currentRoute.value.fullPath).toBe('/account')
  })

  it('each valid tab resolves to the settings route with the tab param', async () => {
    for (const tab of ['learning', 'usage', 'appearance']) {
      await router.push(`/settings/${tab}`)
      expect(router.currentRoute.value.name).toBe('settings')
      expect(router.currentRoute.value.params.tab).toBe(tab)
    }
  })
})
