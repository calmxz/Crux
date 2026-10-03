import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import RegisterView from '@/views/RegisterView.vue'
import { AUTH_CODE_COPY } from '@/lib/authErrors.js'
import { useAuthStore } from '@/stores/auth.js'

const stubs = {
  Logo: { props: ['size', 'variant'], template: '<span data-testid="logo" />' },
  InputText: {
    props: ['modelValue', 'type'],
    template:
      '<input :value="modelValue" :type="type" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
  RouterLink: { props: ['to'], template: '<a><slot /></a>' },
}

function mountView() {
  return mount(RegisterView, { global: { stubs } })
}

describe('RegisterView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('disables submit until email, an 8+ char password, and a matching confirm are present', async () => {
    const wrapper = mountView()
    const btn = wrapper.get('[data-testid="register-submit"]')
    expect(btn.attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="register-email"]').setValue('me@example.com')
    await wrapper.get('[data-testid="register-password"]').setValue('short')
    await wrapper.get('[data-testid="register-confirm"]').setValue('short')
    expect(btn.attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="register-password"]').setValue('hunter2pw')
    await wrapper.get('[data-testid="register-confirm"]').setValue('different')
    expect(btn.attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="register-confirm"]').setValue('hunter2pw')
    expect(btn.attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="register-consent"]').setValue(true)
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('submit calls register and shows the check-inbox state', async () => {
    const auth = useAuthStore()

    const spy = vi
      .spyOn(auth, 'register')
      .mockResolvedValue({ user: { id: 'u-new' }, session: null })

    const wrapper = mountView()
    await wrapper.get('[data-testid="register-email"]').setValue('me@example.com')
    await wrapper.get('[data-testid="register-password"]').setValue('hunter2pw')
    await wrapper.get('[data-testid="register-confirm"]').setValue('hunter2pw')
    await wrapper.get('[data-testid="register-consent"]').setValue(true)
    await wrapper.get('[data-testid="register-form"]').trigger('submit.prevent')
    await flushPromises()
    expect(spy).toHaveBeenCalledWith('me@example.com', 'hunter2pw')
    expect(wrapper.find('[data-testid="register-sent"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('me@example.com')
  })

  it('shows the mismatch hint only when confirm differs from password', async () => {
    const wrapper = mountView()
    await wrapper.get('[data-testid="register-password"]').setValue('hunter2pw')
    await wrapper.get('[data-testid="register-confirm"]').setValue('different')
    expect(wrapper.find('[data-testid="register-mismatch"]').exists()).toBe(true)
    await wrapper.get('[data-testid="register-confirm"]').setValue('hunter2pw')
    expect(wrapper.find('[data-testid="register-mismatch"]').exists()).toBe(false)
  })

  it('shows an error banner when register throws', async () => {
    const auth = useAuthStore()
    // E-13: our copy for the SDK code, never the SDK's prose.
    vi.spyOn(auth, 'register').mockRejectedValue(
      Object.assign(new Error('User already registered'), {
        code: 'user_already_exists',
        status: 422,
      }),
    )
    const wrapper = mountView()
    await wrapper.get('[data-testid="register-email"]').setValue('me@example.com')
    await wrapper.get('[data-testid="register-password"]').setValue('hunter2pw')
    await wrapper.get('[data-testid="register-confirm"]').setValue('hunter2pw')
    await wrapper.get('[data-testid="register-consent"]').setValue(true)
    await wrapper.get('[data-testid="register-form"]').trigger('submit.prevent')
    await flushPromises()
    expect(wrapper.find('[data-testid="register-error"]').exists()).toBe(true)
    const text = wrapper.get('[data-testid="register-error"]').text()
    expect(text).toBe(AUTH_CODE_COPY.user_already_exists)
    expect(text).not.toContain('User already registered')
  })

  it('announces the error to screen readers', async () => {
    const auth = useAuthStore()
    vi.spyOn(auth, 'register').mockRejectedValue(new Error('User already registered'))
    const wrapper = mountView()
    await wrapper.get('[data-testid="register-email"]').setValue('me@example.com')
    await wrapper.get('[data-testid="register-password"]').setValue('hunter2pw')
    await wrapper.get('[data-testid="register-confirm"]').setValue('hunter2pw')
    await wrapper.get('[data-testid="register-consent"]').setValue(true)
    await wrapper.get('[data-testid="register-form"]').trigger('submit.prevent')
    await flushPromises()
    expect(wrapper.find('[data-testid="register-error"]').attributes('role')).toBe('alert')
  })
})
