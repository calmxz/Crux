import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import HomeView from '@/views/HomeView.vue'

describe('frontend smoke', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('boots Vitest', () => {
    expect(1 + 1).toBe(2)
  })

  it('renders HomeView heading', () => {
    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
          Button: { template: '<button><slot /></button>' },
        },
      },
    })

    expect(wrapper.text()).toContain('What do you want to learn?')
  })
})
