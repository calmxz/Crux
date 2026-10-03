import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import UsagePanel from '../components/profile/UsagePanel.vue'
import { formatTime } from '../utils/formatDate.js'

const usage = (overrides = {}) => ({
  daily: [
    { date_utc: '2026-07-09', cost_usd: 0.5 },
    { date_utc: '2026-07-10', cost_usd: 1.0 },
  ],
  today_spend_usd: 1.0,
  soft_cap_usd: 2.0,
  urgent_cap_usd: 2.7,
  hard_cap_usd: 3.0,
  top_sessions: [],
  resets_at: '2026-07-11T00:00:00Z',
  ...overrides,
})

const factory = (u = usage()) =>
  mount(UsagePanel, {
    props: { usage: u },
    global: { stubs: { RouterLink: RouterLinkStub } },
  })

describe('UsagePanel', () => {
  it("renders only today's figure and the daily cap in the glance", () => {
    const w = factory()
    const glance = w.find('[data-testid="usage-glance"]')
    expect(glance.find('.glance-figure').text()).toBe('$1.00')
    expect(glance.find('.glance-caption').text()).toBe('today · $3.00 daily cap')
    expect(glance.element.children).toHaveLength(1)
    expect(w.text()).not.toContain('Last 7 days')
  })

  it('says when the cap resets, in local time, under the meter', () => {
    // formatTime uses the runner's zone and locale, so the expected hour is
    // derived the same way rather than hardcoded.
    const w = factory(usage({ resets_at: '2026-07-11T00:00:00Z' }))
    const note = w.find('[data-testid="usage-reset"]')
    expect(note.text()).toBe(
      `Resets at ${formatTime('2026-07-11T00:00:00Z')}. At the limit, chat pauses until then.`,
    )
    expect(w.find('.meter-wrap + [data-testid="usage-reset"]').exists()).toBe(true)
  })

  it('shows the meter tier labels with soft/urgent amounts and the cap in the glance caption', () => {
    const w = factory(usage({ hard_cap_usd: 4.0, soft_cap_usd: 1.0, urgent_cap_usd: 3.6 }))
    expect(w.find('.meter-label-soft').text()).toBe('soft $1.00')
    expect(w.find('.meter-label-urgent').text()).toBe('urgent $3.60')
    expect(w.find('.glance-caption').text()).toContain('$4.00 daily cap')
  })

  it('renders the "$x.xx of $y.yy today" figure in tabular figures beside the meter', () => {
    const w = factory(usage({ today_spend_usd: 1.0, hard_cap_usd: 3.0 }))
    const figure = w.find('.meter-figure')
    expect(figure.text()).toBe('$1.00 of $3.00 today')
    expect(figure.attributes('data-tabular')).toBeDefined()
  })

  it('names the meter once, by percentage of cap, with no duplicate hidden text', () => {
    const w = factory(usage({ today_spend_usd: 1.0, hard_cap_usd: 4.0 }))
    const meter = w.find('.meter')
    expect(meter.attributes('role')).toBe('img')
    expect(meter.attributes('aria-label')).toBe('25% of daily cap spent')
    expect(w.find('.meter-wrap .sr-only').exists()).toBe(false)
    expect(w.text()).not.toContain('25% of daily cap spent')
  })

  it('keeps the tier labels in the same column as the meter so they line up with the ticks', () => {
    const w = factory()
    const col = w.find('.meter-col')
    expect(col.find('.meter').exists()).toBe(true)
    expect(col.find('.meter-labels').exists()).toBe(true)
    expect(col.find('.meter-figure').exists()).toBe(false)
  })

  it('positions three ticks (soft, urgent, hard) as a fraction of the hard cap', () => {
    const w = factory(usage({ hard_cap_usd: 4.0, soft_cap_usd: 1.0, urgent_cap_usd: 3.6 }))
    const soft = w.find('[data-testid="usage-tick-soft"]')
    const urgent = w.find('[data-testid="usage-tick-urgent"]')
    const hard = w.find('[data-testid="usage-tick-hard"]')
    expect(soft.attributes('style')).toContain('left: 25%') // 1.0 / 4.0
    expect(urgent.attributes('style')).toContain('left: 90%') // 3.6 / 4.0
    expect(hard.attributes('style')).toContain('left: 100%')
  })

  it('fills the meter to today/hard ratio and stays blue under the urgent cap', () => {
    const w = factory() // 1.0 / 3.0, urgent cap 2.7 -- not reached
    const fill = w.find('.meter-fill')
    expect(fill.attributes('style')).toContain('width: 33%')
    expect(fill.classes()).not.toContain('meter-fill--over-urgent')
  })

  it('turns the meter fill text-safe red once spend passes the urgent cap', () => {
    const w = factory(usage({ today_spend_usd: 2.8, urgent_cap_usd: 2.7, hard_cap_usd: 3.0 }))
    expect(w.find('.meter-fill').classes()).toContain('meter-fill--over-urgent')
  })

  it('shows empty state when there is no spend at all', () => {
    const w = factory(
      usage({
        daily: [
          { date_utc: '2026-07-09', cost_usd: 0 },
          { date_utc: '2026-07-10', cost_usd: 0 },
        ],
        today_spend_usd: 0,
      }),
    )

    expect(w.find('[data-testid="usage-empty"]').exists()).toBe(true)
    expect(w.find('[data-testid="usage-glance"]').exists()).toBe(false)
  })

  it('does not show the empty-state copy when top_sessions has rows', () => {
    const w = factory(
      usage({
        daily: [],
        today_spend_usd: 0,
        top_sessions: [{ session_id: 's1', topic: 'CSS', cost_usd: 0.02 }],
      }),
    )

    expect(w.find('[data-testid="usage-empty"]').exists()).toBe(false)
    expect(w.find('[data-testid="usage-glance"]').exists()).toBe(true)
  })

  it('shows the empty-state copy only when there is no spend anywhere', () => {
    const w = factory(usage({ daily: [], today_spend_usd: 0, top_sessions: [] }))
    expect(w.find('[data-testid="usage-empty"]').exists()).toBe(true)
  })

  it('shows no week chart, day ledger, or top sessions', () => {
    const w = factory(
      usage({
        top_sessions: [{ session_id: 's9', topic: 'algebra', cost_usd: 0.42 }],
      }),
    )

    expect(w.find('[data-testid="usage-week"]').exists()).toBe(false)
    expect(w.find('[data-testid="usage-ledger"]').exists()).toBe(false)
    expect(w.find('[data-testid="usage-top-session"]').exists()).toBe(false)
    expect(w.text()).not.toContain('This week')
    expect(w.text()).not.toContain('Most expensive sessions')
    expect(w.text()).not.toContain('algebra')
    expect(w.findComponent(RouterLinkStub).exists()).toBe(false)
    // Daily only: no model name, month-to-date, or message cap either.
    expect(w.text()).not.toMatch(/\b(model|month|messages)\b/i)
  })
})
