import { formatRelative } from '@/utils/formatDate.js'

// One divider per source session. The queue arrives most overdue first, and
// insertion order keeps that both across groups (the group of the most
// overdue concept leads) and within them. Keyed by session id, not topic:
// two sessions can share a topic and each is its own divider.
export function groupBySource(items) {
  const groups = new Map()

  for (const item of items) {
    let group = groups.get(item.source_session_id)

    if (!group) {
      group = { id: item.source_session_id, topic: item.source_topic, items: [] }
      groups.set(item.source_session_id, group)
    }

    group.items.push(item)
  }

  return [...groups.values()]
}

// The streak in words, never tally strokes (#351 resolution).
export function streakLabel(streak) {
  return streak ? `${streak} correct in a row` : 'not yet held'
}

// A card's pencil head line: "due 3 days ago".
export function dueSince(dueAt) {
  return dueAt ? `due ${formatRelative(dueAt)}` : ''
}
