import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it, beforeEach } from 'vitest'

import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'
import LegalView from '../views/LegalView.vue'
import NotFoundView from '../views/NotFoundView.vue'

// A3: LoginView, RegisterView, ForgotPasswordView, ResetPasswordView, LegalView
// (the /tos and /privacy routes) and NotFoundView all render outside App.vue's shell (their
// routes carry `meta: { sidebar: false }`), so App.vue's own <main> never
// wraps them. Each view's root element must itself be a <main> landmark.

const stubs = {
  Logo: { props: ['size', 'variant'], template: '<span data-testid="logo" />' },
  InputText: {
    props: ['modelValue', 'type'],
    template:
      '<input :value="modelValue" :type="type" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
}

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: '/:pathMatch(.*)*', name: 'catch-all', component: { template: '<div />' } },
    ],
  })
}

async function mountWithRouter(component, props) {
  const router = makeRouter()
  await router.push('/')
  await router.isReady()

  return mount(component, { props, global: { plugins: [router], stubs } })
}

describe('cover and legal-page views render a main landmark (A3)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('LoginView root is <main>', async () => {
    const wrapper = await mountWithRouter(LoginView)
    expect(wrapper.element.tagName).toBe('MAIN')
  })

  it('RegisterView root is <main>', async () => {
    const wrapper = await mountWithRouter(RegisterView)
    expect(wrapper.element.tagName).toBe('MAIN')
  })

  it('ForgotPasswordView root is <main>', async () => {
    const wrapper = await mountWithRouter(ForgotPasswordView)
    expect(wrapper.element.tagName).toBe('MAIN')
  })

  it('ResetPasswordView root is <main>', async () => {
    const wrapper = await mountWithRouter(ResetPasswordView)
    expect(wrapper.element.tagName).toBe('MAIN')
  })

  it('LegalView (tos) root is <main>', async () => {
    const wrapper = await mountWithRouter(LegalView, { doc: 'tos' })
    expect(wrapper.element.tagName).toBe('MAIN')
  })

  it('LegalView (privacy) root is <main>', async () => {
    const wrapper = await mountWithRouter(LegalView, { doc: 'privacy' })
    expect(wrapper.element.tagName).toBe('MAIN')
  })

  it('NotFoundView root is <main>', async () => {
    const wrapper = await mountWithRouter(NotFoundView)
    expect(wrapper.element.tagName).toBe('MAIN')
  })
})
