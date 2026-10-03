// frontend/src/__tests__/useSessionGroups.test.js
import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useSessionGroups } from '@/composables/useSessionGroups.js'

const iso = (d) => new Date(d).toISOString()

function sess(over = {}) {
  return {
    id: over.id || 'x',
    topic: over.topic ?? 'Topic',
    created_at: over.created_at ?? iso('2026-05-30T09:00:00Z'),
    last_activity_at: over.last_activity_at ?? null,
    ended_at: over.ended_at ?? null,
    pinned: over.pinned ?? false,
  }
}

describe('useSessionGroups', () => {
  it('orders active sessions most-recently-active first', () => {
    const sessions = ref([
      sess({ id: 'older', created_at: iso('2026-05-01T08:00:00Z') }),
      sess({ id: 'today', created_at: iso('2026-05-30T08:00:00Z') }),
      sess({ id: 'week', created_at: iso('2026-05-27T08:00:00Z') }),
    ])

    const { activeRows } = useSessionGroups(sessions, ref(''))
    expect(activeRows.value.map((r) => r.id)).toEqual(['today', 'week', 'older'])
  })

  it('floats pinned active sessions into pinnedActive, out of activeRows', () => {
    const sessions = ref([
      sess({ id: 'p', pinned: true, created_at: iso('2026-05-01T08:00:00Z') }),
      sess({ id: 'today', created_at: iso('2026-05-30T08:00:00Z') }),
    ])

    const { pinnedActive, activeRows } = useSessionGroups(sessions, ref(''))
    expect(pinnedActive.value.map((r) => r.id)).toEqual(['p'])
    expect(activeRows.value.map((r) => r.id)).not.toContain('p')
  })

  it('sorts pinned active sessions most-recently-active first', () => {
    const sessions = ref([
      sess({ id: 'p-old', pinned: true, last_activity_at: iso('2026-05-30T06:00:00Z') }),
      sess({ id: 'p-new', pinned: true, last_activity_at: iso('2026-05-30T11:00:00Z') }),
    ])

    const { pinnedActive } = useSessionGroups(sessions, ref(''))
    expect(pinnedActive.value.map((r) => r.id)).toEqual(['p-new', 'p-old'])
  })

  it('keeps ended sessions separate and never pins them', () => {
    const sessions = ref([
      sess({ id: 'e', ended_at: iso('2026-05-29T08:00:00Z'), pinned: true }),
      sess({ id: 'a', created_at: iso('2026-05-30T08:00:00Z') }),
    ])

    const { endedRows, pinnedActive, activeRows } = useSessionGroups(sessions, ref(''))
    expect(endedRows.value.map((r) => r.id)).toEqual(['e'])
    expect(pinnedActive.value).toEqual([])
    expect(activeRows.value.map((r) => r.id)).toEqual(['a'])
  })

  it('suppresses every list while a search query is in force', () => {
    const sessions = ref([
      sess({ id: 'a', topic: 'Photosynthesis', pinned: true }),
      sess({ id: 'b', topic: 'Big-O notation', ended_at: iso('2026-05-29T08:00:00Z') }),
    ])

    const { searching, activeRows, pinnedActive, endedRows } = useSessionGroups(
      sessions,
      ref('big'),
    )

    expect(searching.value).toBe(true)
    expect(activeRows.value).toEqual([])
    expect(pinnedActive.value).toEqual([])
    expect(endedRows.value).toEqual([])
  })

  it('is not searching for an empty or whitespace-only query', () => {
    const sessions = ref([sess({ id: 'a' })])
    expect(useSessionGroups(sessions, ref('')).searching.value).toBe(false)
    expect(useSessionGroups(sessions, ref('   ')).searching.value).toBe(false)
  })

  it('sorts by last_activity_at, not created_at, when both are present', () => {
    const sessions = ref([
      sess({
        id: 'touched',
        created_at: iso('2026-05-01T08:00:00Z'), // old
        last_activity_at: iso('2026-05-30T08:00:00Z'), // newest activity
      }),
      sess({ id: 'made-later', created_at: iso('2026-05-20T08:00:00Z') }),
    ])

    const { activeRows } = useSessionGroups(sessions, ref(''))
    expect(activeRows.value.map((r) => r.id)).toEqual(['touched', 'made-later'])
  })

  it('falls back to created_at when last_activity_at is null', () => {
    const sessions = ref([
      sess({ id: 'noact', created_at: iso('2026-05-30T08:00:00Z'), last_activity_at: null }),
      sess({ id: 'older', created_at: iso('2026-05-02T08:00:00Z'), last_activity_at: null }),
    ])

    const { activeRows } = useSessionGroups(sessions, ref(''))
    expect(activeRows.value.map((r) => r.id)).toEqual(['noact', 'older'])
  })

  it('sorts ended rows by last activity, most recent first', () => {
    const sessions = ref([
      sess({
        id: 'e-old',
        ended_at: iso('2026-05-02T08:00:00Z'),
        last_activity_at: iso('2026-05-01T08:00:00Z'),
      }),
      sess({
        id: 'e-today',
        ended_at: iso('2026-05-29T08:00:00Z'),
        last_activity_at: iso('2026-05-30T08:00:00Z'),
      }),
    ])

    const { endedRows } = useSessionGroups(sessions, ref(''))
    expect(endedRows.value.map((r) => r.id)).toEqual(['e-today', 'e-old'])
  })
})
