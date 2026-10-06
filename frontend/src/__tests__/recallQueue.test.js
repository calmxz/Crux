import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

import { dueSince, groupBySource, streakLabel } from '@/utils/recallQueue.js'

function item(concept, sessionId, topic) {
  return { concept, source_session_id: sessionId, source_topic: topic }
}

describe('groupBySource', () => {
  it('returns no groups for an empty queue', () => {
    expect(groupBySource([])).toEqual([])
  })

  it('groups by source session in queue order, across and within groups', () => {
    const groups = groupBySource([
      item('calvin', 's1', 'Photosynthesis'),
      item('limit', 's2', 'Limits'),
      item('stomata', 's1', 'Photosynthesis'),
      item('squeeze', 's2', 'Limits'),
    ])

    expect(groups.map((g) => g.id)).toEqual(['s1', 's2'])
    expect(groups[0].topic).toBe('Photosynthesis')
    expect(groups[0].items.map((i) => i.concept)).toEqual(['calvin', 'stomata'])
    expect(groups[1].items.map((i) => i.concept)).toEqual(['limit', 'squeeze'])
  })

  // Two sessions can share a topic; each is its own divider.
  it('keys groups by session id, not topic', () => {
    const groups = groupBySource([item('a', 's1', 'Cells'), item('b', 's2', 'Cells')])
    expect(groups).toHaveLength(2)
  })
})

describe('streakLabel', () => {
  it('says "not yet held" for a zero or missing streak', () => {
    expect(streakLabel(0)).toBe('not yet held')
    expect(streakLabel(undefined)).toBe('not yet held')
  })

  it('writes the streak in words', () => {
    expect(streakLabel(1)).toBe('1 correct in a row')
    expect(streakLabel(4)).toBe('4 correct in a row')
  })
})

describe('dueSince', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-10T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('reads as "due <relative time>"', () => {
    expect(dueSince('2026-07-07T12:00:00Z')).toBe('due 3 days ago')
    expect(dueSince('2026-07-10T07:00:00Z')).toBe('due 5 hours ago')
  })

  it('is empty when the item has no due date', () => {
    expect(dueSince(null)).toBe('')
  })
})
