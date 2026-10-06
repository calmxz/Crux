import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'

import NotFoundView from '../views/NotFoundView.vue'

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundView },
    ],
  })
}

async function mountView() {
  const router = makeRouter()
  await router.push('/nope-404')
  await router.isReady()

  return mount(NotFoundView, { global: { plugins: [router] } })
}

describe('NotFoundView', () => {
  it('writes the title and the lede', async () => {
    const w = await mountView()
    expect(w.find('[data-testid="not-found-title"]').text()).toBe('Page not found')
    expect(w.text()).toContain('Nothing is written at this address.')
  })

  it('offers a way back to home', async () => {
    const w = await mountView()
    const link = w.find('[data-testid="not-found-home"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toContain('Back home')
    expect(link.attributes('href')).toBe('/')
  })

  it('draws the arrow rather than using an icon font', async () => {
    const w = await mountView()
    const link = w.find('[data-testid="not-found-home"]')
    expect(link.find('svg.cta-mark').exists()).toBe(true)
    expect(link.find('i').exists()).toBe(false)
  })
})
