// frontend/src/composables/useSessionGroups.js
import { computed, unref } from 'vue'

// Activity timestamp drives sorting. Falls back to created_at when a session
// has no messages (last_activity_at is null). Returns ms, 0 if neither.
function activityMs(session) {
  const ts = session.last_activity_at || session.created_at

  return ts ? new Date(ts).getTime() : 0
}

// Most-recently-active first.
function byActivityDesc(a, b) {
  return activityMs(b) - activityMs(a)
}

// The sidebar renders flat, recency-ordered lists: a pinned mini-group, the
// remaining active rows, and the ended rows. Search is served server-side by
// Sidebar.vue itself (the store only holds a windowed slice), so all three
// lists go empty while a query is in force.
export function useSessionGroups(sessions, searchQuery) {
  const rows = computed(() => unref(sessions) || [])
  const query = computed(() => (unref(searchQuery) || '').trim().toLowerCase())

  const searching = computed(() => query.value.length > 0)

  const active = computed(() => rows.value.filter((s) => !s.ended_at))

  const pinnedActive = computed(() =>
    searching.value
      ? []
      : active.value
          .filter((s) => s.pinned)
          .slice()
          .sort(byActivityDesc),
  )

  const activeRows = computed(() =>
    searching.value
      ? []
      : active.value
          .filter((s) => !s.pinned)
          .slice()
          .sort(byActivityDesc),
  )

  const endedRows = computed(() =>
    searching.value
      ? []
      : rows.value
          .filter((s) => Boolean(s.ended_at))
          .slice()
          .sort(byActivityDesc),
  )

  return {
    searching,
    pinnedActive,
    activeRows,
    endedRows,
  }
}
