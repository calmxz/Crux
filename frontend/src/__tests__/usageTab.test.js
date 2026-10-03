import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import UsageTab from '@/components/settings/UsageTab.vue'
import * as profileApi from '@/services/profileApi.js'

// UsageSummary per docs/api/openapi.yaml.
const summary = () => ({
  daily: [{ date_utc: '2026-09-19', cost_usd: 0.3 }],
  today_spend_usd: 0.12,
  soft_cap_usd: 2,
  urgent_cap_usd: 2.5,
  hard_cap_usd: 3,
  top_sessions: [],
  resets_at: '2026-09-20T00:00:00Z',
})

// E-10: a failed read is recoverable in place, and it also has to recover when
// the learner leaves the tab and comes back (SettingsView keeps it alive).
describe('UsageTab', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  it('renders the usage panel once the read resolves', async () => {
    vi.spyOn(profileApi, 'getUsageSummary').mockResolvedValue(summary())

    const wrapper = mount(UsageTab)
    expect(wrapper.find('[data-testid="usage-tab-loading"]').exists()).toBe(true)

    await flushPromises()
    expect(wrapper.find('[data-testid="usage-tab-loading"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="usage-error"]').exists()).toBe(false)
  })

  it('offers Retry on a failed read and refetches on click', async () => {
    const spy = vi
      .spyOn(profileApi, 'getUsageSummary')
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValueOnce(summary())

    const wrapper = mount(UsageTab)
    await flushPromises()

    expect(wrapper.find('[data-testid="usage-error"]').exists()).toBe(true)
    const retry = wrapper.find('[data-testid="usage-retry"]')
    expect(retry.exists()).toBe(true)

    await retry.trigger('click')
    await flushPromises()

    expect(spy).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[data-testid="usage-error"]').exists()).toBe(false)
  })

  it('refetches on reactivation only when the previous read failed', async () => {
    const spy = vi
      .spyOn(profileApi, 'getUsageSummary')
      .mockRejectedValueOnce(new Error('boom'))
      .mockResolvedValue(summary())

    const Host = {
      components: { UsageTab },
      data: () => ({ show: true }),
      template: '<KeepAlive><UsageTab v-if="show" /></KeepAlive>',
    }

    const wrapper = mount(Host)
    await flushPromises()
    expect(spy).toHaveBeenCalledTimes(1)

    wrapper.vm.show = false
    await flushPromises()
    wrapper.vm.show = true
    await flushPromises()
    expect(spy).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[data-testid="usage-error"]').exists()).toBe(false)

    wrapper.vm.show = false
    await flushPromises()
    wrapper.vm.show = true
    await flushPromises()
    expect(spy).toHaveBeenCalledTimes(2)
  })
})
