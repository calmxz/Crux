import { describe, it, expect } from 'vitest'
import { costCapToastMessage } from '@/lib/capToast.js'

describe('costCapToastMessage', () => {
  it('renders a budget message with no dollar figures for global scope', () => {
    const r = costCapToastMessage(
      { used_usd: null, hard_cap_usd: null, scope: 'global' },
      '5:00 PM',
    )

    expect(r.message).not.toContain('$null')
    expect(r.message).toContain('Service daily budget')
    expect(r.message).toBe('Service daily budget reached. Resets at 5:00 PM.')
    expect(r.summary).toBe('Service budget reached')
  })

  it('renders used/hard cap figures for user scope', () => {
    const r = costCapToastMessage(
      { used_usd: '3.01', hard_cap_usd: '3.00', scope: 'user' },
      '5:00 PM',
    )

    expect(r.message).toBe('Daily cost limit reached ($3.01 / $3.00). Resets at 5:00 PM.')
    expect(r.summary).toBe('Cost cap reached')
  })

  it('uses the caller-supplied fallback text when resets_at was unavailable', () => {
    const r = costCapToastMessage(
      { used_usd: '1.50', hard_cap_usd: '2.00', scope: 'user' },
      'midnight UTC',
    )

    expect(r.message).toBe('Daily cost limit reached ($1.50 / $2.00). Resets at midnight UTC.')
  })
})
