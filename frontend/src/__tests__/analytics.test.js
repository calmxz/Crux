import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { Analytics } from '@vercel/analytics/vue'
import { scrubAnalyticsEvent } from '@/lib/analytics.js'

const ID = '3f2a9c1e-7b4d-4e8a-9f10-2c3d4e5f6a7b'

describe('scrubAnalyticsEvent', () => {
  it('replaces a session UUID in the path with [id]', () => {
    const event = { type: 'pageview', url: `https://crux.app/session/${ID}/profile` }
    expect(scrubAnalyticsEvent(event)).toEqual({
      type: 'pageview',
      url: 'https://crux.app/session/[id]/profile',
    })
  })

  it('drops the query string and hash', () => {
    const event = { type: 'pageview', url: 'https://crux.app/reset-password?token=abc#x' }
    expect(scrubAnalyticsEvent(event).url).toBe('https://crux.app/reset-password')
  })

  it('leaves ID-free paths unchanged', () => {
    const event = { type: 'pageview', url: 'https://crux.app/settings/appearance' }
    expect(scrubAnalyticsEvent(event).url).toBe('https://crux.app/settings/appearance')
  })
})

// The package's peer range is vue-router ^4; package.json overrides it onto
// v5. This mounts the real component against a real v5 router so a break in
// that pairing fails here instead of silently dropping page views.
describe('Analytics with vue-router 5', () => {
  let wrapper

  beforeEach(() => {
    delete window.va
    delete window.vaq
  })
  afterEach(() => {
    wrapper?.unmount()
    document.head.querySelectorAll('script[src*="insights"]').forEach((s) => s.remove())
  })

  it('reports the parameterized route on navigation', async () => {
    const Stub = { template: '<div />' }

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: Stub },
        { path: '/session/:id', component: Stub },
      ],
    })

    router.push('/')
    await router.isReady()

    wrapper = mount(Analytics, { global: { plugins: [router] } })
    await router.push(`/session/${ID}`)
    await flushPromises()

    const pageviews = window.vaq.filter(([name]) => name === 'pageview').map(([, p]) => p)
    expect(pageviews.at(-1)).toEqual({ route: '/session/[id]', path: `/session/${ID}` })
  })
})
