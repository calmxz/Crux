<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session.js'
import { friendlyError } from '@/lib/errors.js'
import { cardStory, cardChips, cardMeta } from '@/utils/sessionCard.js'
import EmptyState from '@/components/EmptyState.vue'
import SessionChips from '@/components/SessionChips.vue'
import { TICK_PATH } from '@/components/chat/levelMark.js'
import LibrarySkeletonGrid from '@/components/LibrarySkeletonGrid.vue'

const router = useRouter()

const route = useRoute()

const store = useSessionStore()

// F-06: same guard/catch shape as HomeView.startReview (F-45) -- without
// the busy guard a double-click issues two resume-creates, and without the
// catch the store's rethrow escapes as an unhandled rejection (store.error
// and the errorBus toast already surface the failure).
const continueBusy = ref(false)

async function continueSession(s) {
  if (continueBusy.value) return
  continueBusy.value = true

  try {
    const created = await store.continueTopic(s)

    if (created) router.push({ name: 'session', params: { id: created.id } })
  } catch {
    // surfaced via store.error / errorBus
  } finally {
    continueBusy.value = false
  }
}

const items = ref([])

const total = ref(0)

const limit = ref(20)

const offset = ref(0)

const loading = ref(false)

const error = ref(null)

// Row label cells, the same three-cell label Home and the sidebar carry:
// topic + mastered count on line one, the focus cue underneath. The mastered
// chip is dropped from the chip row so the count is written once per row.
// Status is no longer a word beside the topic; under the All filter it reads
// off the pencil meta line instead.
//
// Derived once per row per list change rather than per template reference:
// the template read each of these two or three times, and cardStory alone is
// fifteen regex passes.
const rows = computed(() =>
  items.value.map((s) => {
    const story = cardStory(s)

    return {
      s,
      story,
      chips: cardChips(s).filter((c) => c.type !== 'mastered'),
      meta: s.ended_at ? `${cardMeta(s)} · ended` : cardMeta(s),
      mastered: s?.progress?.mastered_count || 0,
      descClass: {
        'library-desc-muted': !story,
        'library-desc-quote': !s.ended_at && !!story,
      },
    }
  }),
)

// Controls, seeded from the route query (produced by the sidebar's "View
// all" links -- Tasks 3-4). Vue Router does not remount this component on
// a query-only navigation to the same route, so the same validation is
// re-run by the watcher below whenever the query changes post-mount.
const VALID_STATUSES = ['all', 'active', 'ended']

function statusFromQuery(query) {
  return VALID_STATUSES.includes(query.status) ? query.status : 'all'
}

// Clamped to the backend's 200-char cap on `q` (C-17) so a long bookmarked
// ?q= cannot turn the first load into a 422.
const Q_MAX = 200

function qFromQuery(query) {
  return typeof query.q === 'string' ? query.q.slice(0, Q_MAX) : ''
}

const status = ref(statusFromQuery(route.query))

const q = ref(qFromQuery(route.query))

const sort = ref('last_activity')

let _loadSeq = 0

async function load({ append = false } = {}) {
  // F-15: discard out-of-order settles - same discriminator idiom as the
  // session store's _latestRequestedId.
  const seq = ++_loadSeq
  loading.value = true
  error.value = null

  try {
    const page = await store.fetchLibrary({
      status: status.value,
      q: q.value || undefined,
      sort: sort.value,
      limit: limit.value,
      offset: offset.value,
    })

    if (seq !== _loadSeq) return
    items.value = append ? [...items.value, ...page.items] : page.items
    total.value = page.total
    limit.value = page.limit
    offset.value = page.offset
  } catch (e) {
    if (seq !== _loadSeq) return
    // friendlyError keeps a raw `API 500 /sessions: {...}` off the page; a
    // rejection with no message at all still gets the generic line.
    error.value = e?.message ? friendlyError(e) : 'Failed to load sessions'
  } finally {
    if (seq === _loadSeq) loading.value = false
  }
}

const STATUSES = [
  { key: 'all', label: 'All' },
  { key: 'active', label: 'Active' },
  { key: 'ended', label: 'Ended' },
]

// Keeps the URL in sync with the in-page controls so a stale URL can never
// mask a later sidebar link whose target query happens to match it (see
// the route-query watcher below). `sort` is deliberately excluded -- it is
// not a route query param.
function syncRouteQuery() {
  const nextQuery = { ...route.query, status: status.value }

  if (q.value) nextQuery.q = q.value
  else delete nextQuery.q
  Promise.resolve(router.replace({ query: nextQuery })).catch(() => {})
}

function setStatus(next) {
  status.value = next
  offset.value = 0
  load()
  syncRouteQuery()
}

function onSortChange() {
  offset.value = 0
  load()
}

let searchTimer = null

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    offset.value = 0
    load()
    syncRouteQuery()
  }, 250)
}

// Re-seeds status/q when the query changes on an already-mounted instance
// (e.g. a sidebar "View all" link clicked while already on this page --
// Vue Router does not remount on a query-only navigation to the same
// route). Guarded so that syncRouteQuery() above -- which changes the same
// query keys -- never triggers a redundant second load.
watch(
  () => [route.query.status, route.query.q],
  () => {
    const nextStatus = statusFromQuery(route.query)
    const nextQ = qFromQuery(route.query)

    if (nextStatus === status.value && nextQ === q.value) return
    status.value = nextStatus
    q.value = nextQ
    offset.value = 0
    load()
  },
)

function loadMore() {
  if (loading.value || error.value) return

  if (items.value.length >= total.value) return
  offset.value = items.value.length
  load({ append: true })
}

function retryLoad() {
  error.value = null
  loadMore()
}

// E-06: the first-load failure needs its own retry. retryLoad() above resumes
// an append, and loadMore() bails while items.length >= total (0 >= 0), so it
// would never re-issue the first page.
function retryFirstLoad() {
  offset.value = 0
  load()
}

const sentinelEl = ref(null)

let observer = null

onMounted(() => {
  load()
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((e) => e.isIntersecting)) loadMore()
    },
    { rootMargin: '200px' },
  )
})

// The sentinel is v-if'd with the list; (un)observe as it (un)mounts.
watch(sentinelEl, (el, prev) => {
  if (!observer) return

  if (prev) observer.unobserve(prev)

  if (el) observer.observe(el)
})

onUnmounted(() => {
  clearTimeout(searchTimer)

  if (observer) observer.disconnect()
  observer = null
})
</script>

<template>
  <section class="library" aria-labelledby="library-title">
    <header class="library-head">
      <RouterLink to="/" class="library-back hit-44" data-testid="library-back">
        <svg
          class="library-back-mark"
          viewBox="0 0 20 20"
          width="16"
          height="16"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M15 10 L5 10 M9.5 5.5 L5 10 L9.5 14.5" />
        </svg>
        Back to home
      </RouterLink>
      <h1 id="library-title" class="library-title">All sessions</h1>
    </header>

    <div class="library-controls">
      <div class="library-filter" role="group" aria-label="Filter by status">
        <button
          v-for="opt in STATUSES"
          :key="opt.key"
          type="button"
          class="library-filter-btn"
          :class="{ active: status === opt.key }"
          :data-testid="`library-filter-${opt.key}`"
          :aria-pressed="status === opt.key"
          @click="setStatus(opt.key)"
        >
          {{ opt.label }}
        </button>
      </div>

      <input
        v-model="q"
        type="search"
        class="library-search coarse-2x"
        data-testid="library-search"
        maxlength="200"
        placeholder="Search topics..."
        aria-label="Search sessions by topic"
        @input="onSearchInput"
      />

      <span class="library-sort-field">
        <select
          v-model="sort"
          class="library-sort coarse-2x"
          data-testid="library-sort"
          aria-label="Sort sessions"
          @change="onSortChange"
        >
          <option value="last_activity">Last active</option>
          <option value="created">Newest</option>
          <option value="topic">Topic</option>
        </select>
        <svg
          class="library-sort-mark"
          viewBox="0 0 12 12"
          width="12"
          height="12"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M3 4.75 L6 7.75 L9 4.75" />
        </svg>
      </span>
    </div>

    <LibrarySkeletonGrid v-if="loading && !items.length" :count="6" />
    <template v-else-if="error && !items.length">
      <p class="error" data-testid="library-error">{{ error }}</p>
      <button
        type="button"
        class="library-pg-btn"
        data-testid="library-error-retry"
        @click="retryFirstLoad"
      >
        Retry
      </button>
    </template>

    <EmptyState
      v-else-if="!items.length"
      tone="pause"
      headline="No sessions found"
      subtext="Try a different filter or start a new session."
    />

    <ul v-else class="library-list">
      <li
        v-for="{ s, story, chips, meta, mastered, descClass } in rows"
        :key="s.id"
        class="library-row"
        :data-testid="`library-card-${s.id}`"
      >
        <RouterLink class="library-card-link" :to="{ name: 'session', params: { id: s.id } }">
          <span class="library-card-head">
            <span class="library-topic">{{ s.topic || 'Untitled' }}</span>
            <span v-if="mastered" class="library-mastered" data-tabular aria-hidden="true">
              <svg
                class="library-mastered-mark"
                viewBox="0 0 12 12"
                width="10"
                height="10"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
                focusable="false"
              >
                <path :d="TICK_PATH" />
              </svg>
              {{ mastered }}
            </span>
          </span>
          <SessionChips v-if="chips.length" class="library-chips" :chips="chips" variant="card" />
          <span class="library-desc" :class="descClass">
            {{ story || 'No activity yet' }}
          </span>
          <span class="library-meta">{{ meta }}</span>
        </RouterLink>
        <button
          v-if="s.ended_at"
          type="button"
          class="library-continue"
          :data-testid="`library-continue-${s.id}`"
          :disabled="continueBusy"
          @click="continueSession(s)"
        >
          Continue topic
        </button>
      </li>
    </ul>

    <div
      v-if="items.length"
      ref="sentinelEl"
      class="library-sentinel"
      data-testid="library-sentinel"
    >
      <LibrarySkeletonGrid v-if="loading" :count="3" />
      <template v-else-if="error">
        <p class="error">{{ error }}</p>
        <button type="button" class="library-pg-btn" data-testid="library-retry" @click="retryLoad">
          Retry
        </button>
      </template>
      <p v-else-if="items.length >= total" class="muted library-end">
        {{ total }} {{ total === 1 ? 'session' : 'sessions' }}
      </p>
      <button
        v-else
        type="button"
        class="library-pg-btn"
        data-testid="library-more"
        @click="loadMore"
      >
        More
      </button>
    </div>
  </section>
</template>

<style scoped>
/* The contents page: every session a white card in a list, the controls
   written in blue above them, desk ground around the list. */
.library {
  max-width: 56rem;
  margin: 0 auto;
  padding: 1.75rem 0 3.5rem;
}

.library-head {
  display: flex;
  flex-direction: column;
  margin-bottom: 1.75rem;
}

.library-back {
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  gap: 0.375rem;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--lh-body);
  color: var(--ink-learner);
  text-decoration: none;
}

.library-back:hover {
  color: var(--color-accent-hover);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.library-back-mark {
  flex: 0 0 auto;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.library-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 600;
  letter-spacing: var(--tracking-display);
  line-height: var(--lh-display);
  color: var(--ink);
}

/* Controls are written on the rule, not boxed. */
.library-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0 1.25rem;
  margin-bottom: 1.75rem;
}

.library-filter {
  display: flex;
  gap: 1.25rem;
}

.library-filter-btn {
  /* A2: "All" is three letters, one column wide at 28px -- "Active" and
     "Ended" clear this by their own text length. Match .sb-status-btn's
     floor so every filter button has a comparable target width. */
  min-width: 2.5rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--lh-body);
  cursor: pointer;
}

.library-filter-btn:hover {
  color: var(--color-accent-hover);
}

/* The one in force is graphite under an ink underline; nothing is filled. */
.library-filter-btn.active {
  color: var(--ink);
  text-decoration: underline;
  text-decoration-color: var(--ink);
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
}

.library-filter-btn:focus-visible,
.library-sort:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.library-search {
  flex: 1 1 11.25rem;
  min-width: 8rem;
  appearance: none;
  padding: 0;
  border: 0;
  border-bottom: 1px solid var(--rule-strong);
  border-radius: 0;
  background: transparent;
  color: var(--ink-learner);
  caret-color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
}

.library-search::placeholder {
  color: var(--pencil);
}

.library-search:focus {
  outline: none;
  border-bottom-color: var(--ink-learner);
}

/* The sort control is written, not stamped: the native select keeps its
   behaviour, the platform arrow is dropped and a drawn chevron takes its
   place. */
.library-sort-field {
  position: relative;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: baseline;
}

.library-sort {
  flex: 0 0 auto;
  appearance: none;
  -webkit-appearance: none;
  padding: 0 1.125rem 0 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--lh-body);
  cursor: pointer;
}

.library-sort-mark {
  position: absolute;
  right: 0;
  top: calc(50% - 6px);
  fill: none;
  stroke: var(--ink-learner);
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  pointer-events: none;
}

/* Session cards, one per row. */
.library-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.library-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  column-gap: 1rem;
  padding: 0.875rem 1rem;
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-radius: var(--radius-card);
  box-shadow: 0 1px 0 var(--card-drop);
}

.library-row:hover {
  border-color: var(--card-drop);
}

.library-card-link {
  display: block;
  min-width: 0;
  color: var(--ink);
  text-decoration: none;
  cursor: pointer;
}

.library-card-link:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: -2px;
}

.library-card-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  min-width: 0;
  line-height: var(--lh-body);
}

.library-topic {
  flex: 1 1 auto;
  min-width: 0;
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Line one's right-hand cell: the mastered count, as on Home and the sidebar. */
.library-mastered {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 0.3125rem;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  color: var(--pencil);
}

.library-mastered-mark {
  flex: 0 0 auto;
  /* Mastered tick is green everywhere (tab law). */
  color: var(--tab-mastered);
}

.library-chips {
  display: block;
  line-height: var(--lh-body);
}

.library-desc {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--lh-body);
  color: var(--pencil);
}

.library-desc-muted,
.library-desc-quote {
  font-style: italic;
}

.library-desc-quote::before {
  content: '\201C';
}

.library-desc-quote::after {
  content: '\201D';
}

.library-meta {
  display: block;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--lh-body);
  color: var(--pencil);
}

/* The row's Continue and the sentinel's More/Retry are the same blue text
   control; only the row one has to place itself in the card grid. */
.library-continue,
.library-pg-btn {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--lh-body);
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}

.library-continue:hover:not(:disabled),
.library-pg-btn:hover:not(:disabled) {
  color: var(--color-accent-hover);
}

.library-continue:disabled,
.library-pg-btn:disabled {
  color: var(--pencil);
  text-decoration: none;
  cursor: default;
}

.library-continue:focus-visible,
.library-pg-btn:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.library-continue {
  align-self: start;
}

.muted {
  color: var(--pencil);
}

.error {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink-marker-text);
}

.library-sentinel {
  display: flex;
  align-items: baseline;
  gap: 1.25rem;
  min-height: 1.75rem;
  padding: 0 0.25rem 0 0.75rem;
}

.library-sentinel > :deep(*) {
  flex: 0 1 auto;
}

.library-end {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--lh-body);
}

@media (max-width: 599px) {
  .library-row {
    grid-template-columns: minmax(0, 1fr);
    row-gap: 0;
  }

  .library-continue {
    justify-self: start;
  }

  .library-controls {
    gap: 0 1rem;
  }
}
</style>
