import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import OnboardingView from '@/views/OnboardingView.vue'
import { useUserStore } from '@/stores/user.js'
import { useAuthStore } from '@/stores/auth.js'

const push = vi.fn()

vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

// F-46: completeOnboarding writes through to PATCH /me via the real
// apiClient (dynamic import) -- mock global fetch, same pattern as
// userStore.test.js / apiWrappers.test.js.
function ok(body) {
  return Promise.resolve({
    ok: true,
    status: 200,
    headers: { get: () => null },
    text: () => Promise.resolve(JSON.stringify(body)),
  })
}

const stubs = {
  InputText: {
    props: ['modelValue'],
    template:
      '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
  Button: {
    props: ['disabled', 'label'],
    template:
      '<button :disabled="disabled" @click="$emit(\'click\')"><slot>{{ label }}</slot></button>',
  },
}

describe('OnboardingView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockClear()
    globalThis.fetch = vi.fn().mockReturnValue(ok({}))
  })

  it('renders the welcome heading', () => {
    const wrapper = mount(OnboardingView, { global: { stubs } })
    expect(wrapper.text()).toContain('Welcome to')
    expect(wrapper.text()).toContain('Crux')
  })

  // A3 leftover: OnboardingView is a no-shell route (meta.sidebar: false), so
  // it needs its own main landmark like the other cover/legal views.
  it('A3: root renders as a main landmark', () => {
    const wrapper = mount(OnboardingView, { global: { stubs } })
    expect(wrapper.element.tagName).toBe('MAIN')
  })

  it('submit completes onboarding and routes home', async () => {
    const wrapper = mount(OnboardingView, { global: { stubs } })
    await wrapper.get('[data-testid="onboarding-name"]').setValue('Eddy')
    await wrapper.find('form').trigger('submit.prevent')
    // completeOnboarding's write-through chains two on-demand dynamic
    // imports (apiClient.js, then apiClient's internal supabase.js) before
    // resolving; flushPromises' single setImmediate tick isn't enough to
    // drain that in this environment, so wait a real macrotask instead.
    await new Promise((resolve) => setTimeout(resolve, 50))
    const user = useUserStore()
    expect(user.name).toBe('Eddy')
    expect(user.onboardingComplete).toBe(true)
    expect(push).toHaveBeenCalledWith({ name: 'home' })
  })

  it('feedback help copy switches with the selection', async () => {
    const wrapper = mount(OnboardingView, { global: { stubs } })
    expect(wrapper.text()).toContain('nudge')
    await wrapper.get('[data-testid="feedback-style-direct_answers"]').setValue(true)
    expect(wrapper.text()).toContain('explain')
  })

  // F-11: API failure must surface inline and re-enable the form, not leave
  // it frozen with an unhandled rejection.
  it('shows inline error and re-enables on API failure', async () => {
    const user = useUserStore()
    vi.spyOn(user, 'completeOnboarding').mockRejectedValue(new Error('down'))
    const wrapper = mount(OnboardingView, { global: { stubs } })
    await wrapper.get('[data-testid="onboarding-name"]').setValue('Eddy')
    await wrapper.find('form').trigger('submit.prevent')
    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(wrapper.find('[data-testid="onboarding-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="onboarding-submit"]').attributes('disabled')).toBeUndefined()
    expect(push).not.toHaveBeenCalled()
  })

  // E-09: onboarding used to be a dead end for a learner who cannot or does
  // not want to complete it (e.g. hydrate failed and force-routed them here
  // with no local snapshot). Same sign-out as Sidebar.vue's onSignOut: call
  // authStore.signOut(), then push to /login.
  it('sign-out button calls authStore.signOut and routes to login (E-09)', async () => {
    const auth = useAuthStore()
    const signOutSpy = vi.spyOn(auth, 'signOut').mockResolvedValue()
    const wrapper = mount(OnboardingView, { global: { stubs } })
    await wrapper.get('[data-testid="onboarding-signout"]').trigger('click')
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(signOutSpy).toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith('/login')
  })

  it('ignores double submit while in flight', async () => {
    const user = useUserStore()
    let resolveCompletion
    vi.spyOn(user, 'completeOnboarding').mockReturnValue(
      new Promise((resolve) => {
        resolveCompletion = resolve
      }),
    )
    const wrapper = mount(OnboardingView, { global: { stubs } })
    await wrapper.get('[data-testid="onboarding-name"]').setValue('Eddy')
    await wrapper.find('form').trigger('submit.prevent')
    await wrapper.find('form').trigger('submit.prevent')

    expect(user.completeOnboarding).toHaveBeenCalledTimes(1)
    resolveCompletion()
    await new Promise((resolve) => setTimeout(resolve, 50))
  })
})
