import { describe, it, expect } from 'vitest'
import { mapCapError } from '@/lib/capErrors.js'
import {
  ERR_DAILY_CAP_REACHED,
  ERR_DAILY_COST_CAP_REACHED,
  ERR_GLOBAL_COST_CAP_REACHED,
} from '@/lib/errorCodes.js'

describe('mapCapError', () => {
  it('maps a daily-cap envelope to kind=daily with cap/used/resets_at', () => {
    const r = mapCapError({
      code: ERR_DAILY_CAP_REACHED,
      cap: 50,
      used: 50,
      resets_at: '2026-07-08T00:00:00+00:00',
    })

    expect(r.kind).toBe('daily')
    expect(r.info).toEqual({ cap: 50, used: 50, resets_at: '2026-07-08T00:00:00+00:00' })
  })

  it('maps a cost-cap envelope to kind=cost with the four cost fields', () => {
    const r = mapCapError({
      code: ERR_DAILY_COST_CAP_REACHED,
      used_usd: '3.0100',
      soft_cap_usd: '2.0',
      hard_cap_usd: '3.0',
      resets_at: '2026-07-08T00:00:00+00:00',
    })

    expect(r.kind).toBe('cost')
    expect(r.info).toEqual({
      used_usd: '3.0100',
      soft_cap_usd: '2.0',
      hard_cap_usd: '3.0',
      resets_at: '2026-07-08T00:00:00+00:00',
      scope: 'user',
    })
  })

  it('fills missing fields with null (mid-turn SSE shape has no resets_at)', () => {
    const r = mapCapError({
      code: ERR_DAILY_COST_CAP_REACHED,
      used_usd: '3.0100',
      soft_cap_usd: '2.0',
      hard_cap_usd: '3.0',
    })

    expect(r.kind).toBe('cost')
    expect(r.info.resets_at).toBeNull()
  })

  it('maps a global-cap envelope to kind=cost with scope=global and null spend fields', () => {
    const r = mapCapError({
      code: ERR_GLOBAL_COST_CAP_REACHED,
      resets_at: '2026-07-08T00:00:00+00:00',
    })

    expect(r.kind).toBe('cost')
    expect(r.info).toEqual({
      used_usd: null,
      soft_cap_usd: null,
      hard_cap_usd: null,
      resets_at: '2026-07-08T00:00:00+00:00',
      scope: 'global',
    })
  })

  it('returns kind=null for unknown codes and never throws on garbage', () => {
    expect(mapCapError({ code: 'max_iters_reached' })).toEqual({ kind: null, info: null })
    expect(mapCapError(null)).toEqual({ kind: null, info: null })
    expect(mapCapError(undefined)).toEqual({ kind: null, info: null })
    expect(mapCapError('nonsense')).toEqual({ kind: null, info: null })
  })
})
