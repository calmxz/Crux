<script setup>
defineOptions({ name: 'AppSidebar' })

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useSidebar } from '@/composables/useSidebar.js'
import { useToast } from '@/composables/useToast.js'
import { useAuthStore } from '@/stores/auth.js'
import { useSessionStore } from '@/stores/session.js'
import { useUserStore } from '@/stores/user.js'
import { useSessionGroups } from '@/composables/useSessionGroups.js'
import { getReviewQueue } from '@/services/reviewApi.js'
import * as sessionsApi from '@/services/sessionsApi.js'
import { runWhenIdle } from '@/utils/idle.js'
import Logo from '@/components/Logo.vue'
import SidebarSessionRow from './SidebarSessionRow.vue'
import SidebarSkeletonList from './SidebarSkeletonList.vue'
import SidebarUserMenu from './SidebarUserMenu.vue'

const { mode, isDesktop, drawerOpen, toggleDesktop, closeDrawer } = useSidebar()

const router = useRouter()

const route = useRoute()

const authStore = useAuthStore()

const { isAuthenticated, userEmail } = storeToRefs(authStore)

const userStore = useUserStore()

const { name: userName } = storeToRefs(userStore)

const sessionStore = useSessionStore()

const { sessions, loading, activeTotal, endedTotal, searchRows } = storeToRefs(sessionStore)

const listEl = ref(null)

const asideEl = ref(null)

const statusFilter = ref('active') // 'active' | 'ended'

const STATUS_TABS = [
  { key: 'active', label: 'Active' },
  { key: 'ended', label: 'Ended' },
]

let lastFocused = null

let cancelIdleBadge = null

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'

function getFocusables() {
  if (!asideEl.value) return []

  return Array.from(asideEl.value.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
    (el) => !el.hasAttribute('disabled') && el.offsetParent !== null,
  )
}

function onTrapKeydown(e) {
  if (e.key === 'Escape') {
    e.preventDefault()
    closeDrawer()

    return
  }

  if (e.key !== 'Tab') return
  const focusables = getFocusables()

  if (focusables.length === 0) {
    e.preventDefault()

    return
  }

  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  const active = document.activeElement

  if (e.shiftKey && (active === first || !asideEl.value?.contains(active))) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && active === last) {
    e.preventDefault()
    first.focus()
  }
}

watch(drawerOpen, async (open) => {
  if (typeof document === 'undefined') return

  if (open && !isDesktop.value) {
    lastFocused = document.activeElement
    document.addEventListener('keydown', onTrapKeydown, true)
    await nextTick()
    const focusables = getFocusables()
    focusables[0]?.focus()
  } else {
    document.removeEventListener('keydown', onTrapKeydown, true)

    if (lastFocused && typeof lastFocused.focus === 'function') {
      lastFocused.focus()
    }

    lastFocused = null
  }
})

onBeforeUnmount(() => {
  if (typeof document !== 'undefined') {
    document.removeEventListener('keydown', onTrapKeydown, true)
  }

  clearTimeout(searchTimer)
  cancelIdleBadge?.()
  listResizeObserver?.disconnect()
  listResizeObserver = null
})

const searchQuery = ref('')

const { searching, pinnedActive, activeRows, endedRows } = useSessionGroups(sessions, searchQuery)

// SIDEBAR_CAP is the floor (and the fallback wherever the list's height cannot
// be measured -- jsdom, or a browser without ResizeObserver). SIDEBAR_CAP_MAX
// is the ceiling, and matches the store's SIDEBAR_PAGE_LIMIT window: rendering
// past it would only ever draw rows the store does not hold.
const SIDEBAR_CAP = 15

const SIDEBAR_CAP_MAX = 40

const DEFAULT_PITCH_PX = 28

// How many rows the list column actually has room for. Recomputed from the
// measured height of `listEl` so a tall screen fills instead of stopping at
// the floor and leaving dead space below the last row.
const renderCap = ref(SIDEBAR_CAP)

let listResizeObserver = null

function measureRenderCap() {
  const el = listEl.value

  if (!el) return
  const raw = getComputedStyle(el).getPropertyValue('--line-pitch')
  const parsed = parseFloat(raw)
  const pitchPx = Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_PITCH_PX
  // One pitch is reserved for the closing "View all" line.
  const fit = Math.floor((el.clientHeight - pitchPx) / pitchPx)
  renderCap.value = Math.min(SIDEBAR_CAP_MAX, Math.max(SIDEBAR_CAP, fit))
}

// Search queries the library endpoint server-side (the store only holds a
// SIDEBAR_CAP-windowed slice, so client-side filtering of `sessions` could
// silently miss matches outside that window). Results live in the store's
// `searchRows` (not the sidebar's own local state) because the rows are
// rendered directly and routinely describe sessions outside the `sessions`
// window -- see session.js for why every mutating action must be able to
// patch them. The store's `sessions` array is never written by search.
const searchTotal = ref(0)

const searchLoading = ref(false)

let searchTimer = null

let _searchSeq = 0

// Scoped to the current tab (status: statusFilter). Re-runs on a tab change
// too, through the same debounce/sequence-guard path as a keystroke, so the
// tab toggle can widen a search's scope without an unguarded fetch.
watch([searchQuery, statusFilter], ([raw]) => {
  if (searchTimer) clearTimeout(searchTimer)
  const q = (raw || '').trim()

  if (!q) {
    _searchSeq++ // invalidate any in-flight response
    searchRows.value = []
    searchTotal.value = 0
    searchLoading.value = false

    return
  }

  searchLoading.value = true
  searchTimer = setTimeout(async () => {
    const seq = ++_searchSeq

    try {
      // silent: a sidebar search must never toast; errors render as zero matches
      const page = await sessionsApi.getSessionLibrary(
        { status: statusFilter.value, q, sort: 'last_activity', limit: SIDEBAR_CAP, offset: 0 },
        { silent: true },
      )

      if (seq !== _searchSeq) return // stale response; a newer query owns the state
      searchRows.value = page.items
      searchTotal.value = page.total
    } catch {
      if (seq !== _searchSeq) return
      searchRows.value = []
      searchTotal.value = 0
    } finally {
      if (seq === _searchSeq) searchLoading.value = false
    }
  }, 250)
})

// Gated on !searchLoading: while a newer query is in flight, searchTotal
// still reflects the PREVIOUS query's total. Showing the link during that
// window would pair a stale total with the freshly typed q in its route
// query. The previous query's rows stay visible underneath (see template) --
// only the link/total, which would be actively wrong, is hidden.
const showViewAllSearch = computed(
  () => !searchLoading.value && searchTotal.value > searchRows.value.length,
)

// Pinned rows render first and count toward the cap; server's pinned_activity
// sort already guarantees pinned rows are inside the fetched page. Pinned
// itself is also sliced to the cap so a long pinned list can never push the
// component's total render past renderCap on its own.
const cappedPinnedActive = computed(() => pinnedActive.value.slice(0, renderCap.value))

const cappedActiveFlat = computed(() =>
  activeRows.value.slice(0, Math.max(0, renderCap.value - cappedPinnedActive.value.length)),
)

const cappedEndedRows = computed(() => endedRows.value.slice(0, renderCap.value))

const activeRendered = computed(
  () => cappedPinnedActive.value.length + cappedActiveFlat.value.length,
)

// View all is the list's closing line whenever rows are rendered. The
// zero-rows guard stays: createSession bumps activeTotal without pushing
// into the (windowed) `sessions` array, so a fresh account can sit at
// activeTotal=1 with zero rendered rows. Without this guard the sidebar
// would show "No sessions yet" and "View all 1 sessions" at once.
const showViewAllActive = computed(() => activeRendered.value > 0)

const showViewAllEnded = computed(() => cappedEndedRows.value.length > 0)

const showSkeleton = computed(() => loading.value && !sessions.value.length)

const showEmptyHint = computed(() => !loading.value && !searching.value && !sessions.value.length)

const reviewTotal = ref(0)

// The Profile glyph: a divider card with its tab up, the profile's own
// furniture. Not a person silhouette -- the identity circle in the foot is the
// only mark of a person the shell draws (DESIGN.md).
const PROFILE_ICON_PATH = 'M3 7.5 H17 V16 H3 Z M4.5 7.5 V4 H10 V7.5 M6 11 H14 M6 13.5 H11'

const showEmptyActiveHint = computed(
  () =>
    !loading.value &&
    !searching.value &&
    sessions.value.length > 0 &&
    !activeRows.value.length &&
    !pinnedActive.value.length,
)

// Fetch only if we haven't loaded yet. HomeView also calls listSessions on mount;
// the store de-dupes concurrent calls via _inflight, and skipping when populated
// avoids the deep-link redundant fetch.
onMounted(async () => {
  // Fit-to-height: measure once the list column exists (desktop or drawer) and
  // again whenever it resizes. Guarded so jsdom -- which has no
  // ResizeObserver -- keeps the SIDEBAR_CAP floor.
  if (listEl.value && typeof ResizeObserver !== 'undefined') {
    listResizeObserver = new ResizeObserver(() => measureRenderCap())
    listResizeObserver.observe(listEl.value)
  }

  if (isAuthenticated.value && !sessions.value.length) {
    await sessionStore.listSessions().catch(() => {})
  }

  if (isAuthenticated.value) {
    // Badge count only; silent - a sidebar badge must never toast.
    // Deferred to browser idle so it never competes with first paint.
    cancelIdleBadge = runWhenIdle(() => {
      if (!isAuthenticated.value) return
      getReviewQueue({ limit: 1, offset: 0 }, { silent: true })
        .then((q) => {
          reviewTotal.value = q?.total || 0
        })
        .catch(() => {})
    })
  }
})

// Scroll the active session row into view on route change.
watch(
  () => route.params.id,
  async (id) => {
    // Nothing to scroll to off a session route -- skip the nextTick + query.
    if (!id) return
    await nextTick()

    if (!listEl.value) return
    const target = listEl.value.querySelector(`[data-session-id="${id}"]`)
    target?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  },
)

const isExpanded = computed(() => mode.value === 'expanded' || mode.value === 'drawer-open')

const showDrawerClose = computed(() => !isDesktop.value && mode.value === 'drawer-open')

const isRail = computed(() => isDesktop.value && !isExpanded.value)

// Identity row name. stores/user.js writes the literal 'Learner' when the
// learner leaves the name blank, so that placeholder counts as unset here and
// the row falls back to the email's local part.
const identityName = computed(() => {
  const n = userName.value

  return n && n !== 'Learner' ? n : ''
})

// Clear search when collapsing: the field folds away with the list, so a
// query left behind would silently filter the list on the next unfold.
watch(isExpanded, (expanded) => {
  if (!expanded) searchQuery.value = ''
})

// Rail Search unfolds the sidebar, then hands the caret to the search field
// once the expanded body has rendered.
async function onRailSearch() {
  toggleDesktop()
  await nextTick()
  asideEl.value?.querySelector('[data-testid="sidebar-search"]')?.focus()
}

function onNewSession() {
  closeDrawer()
  router.push({ name: 'new-session' })
}

// The account menu's Settings, Usage and Account items.
function onMenuNavigate(to) {
  closeDrawer()
  router.push(to)
}

// Sign out lives in the identity row's account menu at the sidebar foot:
// it is a navigation act, not a setting.
async function onSignOut() {
  closeDrawer()

  try {
    await authStore.signOut()
  } catch (err) {
    // The store clears the local session even when the SDK throws, so the
    // shell is already signed out; say so and still leave the protected
    // route rather than stranding the learner on it.
    useToast().showError(err?.message || 'Sign out failed')
  }

  router.push('/login')
}
</script>

<template>
  <Teleport to="body" :disabled="isDesktop">
    <div
      v-if="!isDesktop && mode === 'drawer-open'"
      class="sb-backdrop"
      data-testid="sidebar-backdrop"
      @click="closeDrawer"
    />
  </Teleport>
  <aside
    ref="asideEl"
    class="sidebar"
    :class="{
      'sidebar--expanded': isExpanded,
      'sidebar--collapsed': !isExpanded && isDesktop,
      'sidebar--drawer': !isDesktop,
      'sidebar--drawer-open': !isDesktop && mode === 'drawer-open',
    }"
    :data-mode="mode"
    :inert="(!isDesktop && mode !== 'drawer-open') || null"
    aria-label="App navigation"
  >
    <div class="sb-header">
      <!-- Folded, the rail starts at the toggle: no mark above it. -->
      <RouterLink
        v-if="!isRail"
        to="/"
        class="sb-brand"
        aria-label="Crux home"
        @click="closeDrawer"
      >
        <Logo size="md" variant="full" />
      </RouterLink>
      <button
        v-if="isDesktop"
        type="button"
        class="sb-toggle sb-toggle--head hit-44"
        :aria-label="isExpanded ? 'Collapse sidebar' : 'Expand sidebar'"
        :title="isExpanded ? 'Collapse sidebar' : 'Expand sidebar'"
        data-testid="sidebar-collapse-toggle"
        @click="toggleDesktop"
      >
        <!-- The drawn "sidebar" glyph: a page with a narrow left pane. -->
        <svg
          class="sb-toggle-icon"
          viewBox="0 0 20 20"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <rect x="3" y="4" width="14" height="12" rx="2" />
          <path d="M8 4 L8 16" />
        </svg>
      </button>
      <button
        v-if="showDrawerClose"
        type="button"
        class="sb-toggle sb-toggle--end hit-44"
        aria-label="Close sessions sidebar"
        title="Close"
        data-testid="sidebar-drawer-close"
        @click="closeDrawer"
      >
        <svg
          class="sb-toggle-icon"
          viewBox="0 0 20 20"
          width="14"
          height="14"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M5 5 L15 15 M15 5 L5 15" />
        </svg>
      </button>
    </div>

    <div class="sb-cta">
      <button
        type="button"
        class="sb-new-session"
        :class="{ 'sb-new-session--icon': !isExpanded }"
        :title="isExpanded ? '' : 'New session'"
        :aria-label="isExpanded ? null : 'New session'"
        data-testid="sidebar-new-session"
        @click="onNewSession"
      >
        <svg
          class="sb-inline-icon"
          viewBox="0 0 20 20"
          width="16"
          height="16"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M10 4 L10 16 M4 10 L16 10" />
        </svg>
        <span v-if="isExpanded">New session</span>
      </button>
    </div>

    <!-- Folded rail: Search, Profile and Recall stay one click away without unfolding. -->
    <div v-if="isDesktop && !isExpanded" class="sb-rail-actions">
      <button
        type="button"
        class="sb-icon sb-icon-btn hit-44"
        aria-label="Search sessions"
        title="Search sessions"
        data-testid="sidebar-rail-search"
        @click="onRailSearch"
      >
        <svg
          class="sb-inline-icon"
          viewBox="0 0 20 20"
          width="16"
          height="16"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <circle cx="8.5" cy="8.5" r="6" />
          <path d="M13 13 L17.5 17.5" />
        </svg>
      </button>
      <RouterLink
        :to="{ name: 'profile-aggregate' }"
        class="sb-icon hit-44"
        data-testid="sidebar-profile"
        aria-label="Profile"
        title="Profile"
      >
        <svg
          class="sb-inline-icon"
          viewBox="0 0 20 20"
          width="16"
          height="16"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <path :d="PROFILE_ICON_PATH" />
        </svg>
      </RouterLink>
      <RouterLink
        v-if="reviewTotal > 0"
        to="/recall"
        class="sb-icon sb-rail-review hit-44"
        data-testid="sidebar-recall"
        :aria-label="`Recall: ${reviewTotal} ${reviewTotal === 1 ? 'concept' : 'concepts'} due`"
        title="Recall"
      >
        <svg
          class="sb-inline-icon"
          viewBox="0 0 20 20"
          width="16"
          height="16"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <circle cx="10" cy="10.5" r="7" />
          <path d="M10 6.5 L10 10.5 L13 12.5" />
        </svg>
        <span class="sb-rail-badge" aria-hidden="true">{{ reviewTotal }}</span>
      </RouterLink>
    </div>

    <!-- Profile is always shown (Recall hides at zero due); it sits first so
         it never jumps when the idle-loaded Recall line appears under it. -->
    <RouterLink
      v-if="isExpanded"
      :to="{ name: 'profile-aggregate' }"
      class="sb-navline"
      data-testid="sidebar-profile"
      @click="closeDrawer"
    >
      <svg
        class="sb-inline-icon"
        viewBox="0 0 20 20"
        width="14"
        height="14"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <path :d="PROFILE_ICON_PATH" />
      </svg>
      <span>Profile</span>
    </RouterLink>
    <RouterLink
      v-if="isExpanded && reviewTotal > 0"
      to="/recall"
      class="sb-navline"
      data-testid="sidebar-recall"
      :aria-label="`Recall: ${reviewTotal} ${reviewTotal === 1 ? 'concept' : 'concepts'} due`"
      @click="closeDrawer"
    >
      <svg
        class="sb-inline-icon"
        viewBox="0 0 20 20"
        width="14"
        height="14"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <circle cx="10" cy="10.5" r="7" />
        <path d="M10 6.5 L10 10.5 L13 12.5" />
      </svg>
      <span>Recall</span>
      <span class="sb-navline-count" aria-hidden="true">{{ reviewTotal }}</span>
    </RouterLink>

    <div v-if="isExpanded" class="sb-search">
      <svg
        class="sb-inline-icon"
        viewBox="0 0 20 20"
        width="13"
        height="13"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <circle cx="8.5" cy="8.5" r="6" />
        <path d="M13 13 L17.5 17.5" />
      </svg>
      <input
        v-model="searchQuery"
        type="search"
        class="sb-search-input"
        placeholder="Search sessions"
        aria-label="Search sessions"
        data-testid="sidebar-search"
      />
    </div>

    <div
      v-if="isExpanded"
      class="sb-status-toggle"
      role="group"
      aria-label="Filter sessions by status"
    >
      <button
        v-for="t in STATUS_TABS"
        :key="t.key"
        type="button"
        class="sb-status-btn"
        :class="{ active: statusFilter === t.key }"
        :aria-pressed="statusFilter === t.key"
        :data-testid="`sidebar-status-${t.key}`"
        @click="statusFilter = t.key"
      >
        {{ t.label }}
        <span v-if="t.key === 'ended' && endedTotal" class="sb-section-count"
          >({{ endedTotal }})</span
        >
      </button>
    </div>

    <!-- Folded, the rail shows actions only; the list returns on unfold. The
         nav itself stays as the spacer that holds the identity foot down (and
         the fit-to-height target), hidden so it is not an empty landmark. -->
    <nav ref="listEl" class="sb-list-wrap" aria-label="Sessions" :aria-hidden="isRail || null">
      <template v-if="isExpanded">
        <template v-if="searching">
          <p
            class="sb-search-count label"
            data-testid="sidebar-search-count"
            aria-live="polite"
            aria-atomic="true"
          >
            <template v-if="searchLoading">Searching...</template>
            <template v-else
              >{{ searchTotal }} {{ searchTotal === 1 ? 'match' : 'matches' }}</template
            >
          </p>
          <ul v-if="searchRows.length" class="sb-session-list">
            <SidebarSessionRow
              v-for="s in searchRows"
              :key="s.id"
              :session="s"
              :state="s.ended_at ? 'ended' : 'active'"
            />
          </ul>
          <p
            v-else-if="!searchLoading"
            class="sb-empty-hint"
            data-testid="sidebar-search-empty"
            aria-live="polite"
            aria-atomic="true"
          >
            No sessions match "{{ searchQuery }}".
          </p>
          <RouterLink
            v-if="showViewAllSearch"
            class="sb-view-all"
            :to="{
              name: 'sessions-library',
              query: { status: statusFilter, q: searchQuery.trim() },
            }"
            data-testid="sidebar-view-all-search"
            @click="closeDrawer"
          >
            View all {{ searchTotal }} matches
          </RouterLink>
        </template>
        <template v-else>
          <!-- ACTIVE view: pinned mini-group + session activity buckets -->
          <template v-if="statusFilter === 'active'">
            <section
              v-if="cappedPinnedActive.length"
              class="sb-section sb-section--pinned"
              data-testid="sidebar-section-pinned"
            >
              <h2 class="sb-section-label label">
                <svg
                  class="sb-inline-icon"
                  viewBox="0 0 20 20"
                  width="12"
                  height="12"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path d="M6 3.5 H14 V16.5 L10 13.5 L6 16.5 Z" />
                </svg>
                Pinned
                <span class="sb-section-count">({{ cappedPinnedActive.length }})</span>
              </h2>
              <ul class="sb-session-list">
                <SidebarSessionRow
                  v-for="s in cappedPinnedActive"
                  :key="s.id"
                  :session="s"
                  state="active"
                />
              </ul>
            </section>

            <section class="sb-section sb-section--active" data-testid="sidebar-section-active">
              <SidebarSkeletonList v-if="showSkeleton" :count="3" />
              <template v-else>
                <div data-testid="sidebar-quick-group">
                  <ul v-if="cappedActiveFlat.length" class="sb-session-list">
                    <SidebarSessionRow
                      v-for="s in cappedActiveFlat"
                      :key="s.id"
                      :session="s"
                      state="active"
                    />
                  </ul>
                </div>
                <p v-if="showEmptyHint" class="sb-empty-hint" data-testid="sidebar-empty-hint">
                  No sessions yet. Click + New session above.
                </p>
                <p
                  v-else-if="showEmptyActiveHint"
                  class="sb-empty-hint"
                  data-testid="sidebar-empty-active"
                >
                  No active sessions. Check the Ended tab.
                </p>
              </template>
            </section>

            <RouterLink
              v-if="showViewAllActive"
              class="sb-view-all"
              :to="{ name: 'sessions-library', query: { status: 'active' } }"
              data-testid="sidebar-view-all-active"
              @click="closeDrawer"
            >
              View all {{ activeTotal }} sessions
            </RouterLink>
          </template>

          <!-- ENDED view: flat recency-sorted list, no pinning -->
          <section v-else class="sb-section sb-section--ended" data-testid="sidebar-section-ended">
            <ul v-if="cappedEndedRows.length" class="sb-session-list">
              <SidebarSessionRow
                v-for="s in cappedEndedRows"
                :key="s.id"
                :session="s"
                state="ended"
              />
            </ul>
            <p
              v-if="!cappedEndedRows.length"
              class="sb-empty-hint"
              data-testid="sidebar-ended-empty"
            >
              No ended sessions yet.
            </p>
            <RouterLink
              v-if="showViewAllEnded"
              class="sb-view-all"
              :to="{ name: 'sessions-library', query: { status: 'ended' } }"
              data-testid="sidebar-view-all-ended"
              @click="closeDrawer"
            >
              View all {{ endedTotal }} sessions
            </RouterLink>
          </section>
        </template>
      </template>
    </nav>

    <footer v-if="isAuthenticated" class="sb-rail" :class="{ 'sb-rail--column': !isExpanded }">
      <SidebarUserMenu
        :name="identityName"
        :email="userEmail || ''"
        :collapsed="isRail"
        @navigate="onMenuNavigate"
        @sign-out="onSignOut"
      />
    </footer>
  </aside>
</template>

<style scoped>
/* The contents page: paper, one rule down its right edge, nothing floating. */
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100vh;
  /* D-18: mobile browser chrome eats into 100vh, so the drawer's own footer
     sits under it. 100dvh tracks the visible viewport; 100vh stays as the
     fallback for engines without dvh (matches SessionView). */
  height: 100dvh;
  position: sticky;
  top: 0;
  background: var(--desk-deep);
  border-right: 1px solid var(--card-edge);
  z-index: 30;
  overflow: hidden;
}

.sidebar--expanded,
.sidebar--collapsed {
  width: 100%;
}

/* P2: the shell column snaps rather than animating grid-template-columns (a
   whole-shell relayout every frame). The collapse instead reads the way
   everything else in this world does: the paper and its right-hand rule hold
   still while the ink on it fades back in at the new measure. The class flip
   between --expanded and --collapsed is what re-runs the animation, so this
   needs no per-branch wrapper -- the expanded body and the collapsed rail are
   the same interleaved v-if branches, and neither is ever mid-fade while
   focusable, since only opacity moves. */
@keyframes sb-mode-fade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.sidebar--expanded > *,
.sidebar--collapsed > * {
  animation: sb-mode-fade var(--motion-fast) ease;
}

/* Mobile drawer: the same paper, laid over the page. It appears and leaves in
   opacity -- in this world ink is never slid into place. The shell grid column
   collapses to zero so the main column gets full width when it is closed. */
.sidebar--drawer {
  position: fixed;
  top: 0;
  left: 0;
  width: var(--sidebar-width-expanded, 18rem);
  max-width: 85vw;
  box-shadow: var(--shadow-lift);
  opacity: 0;
  visibility: hidden;
  transition:
    opacity var(--motion-fast) ease,
    visibility 0s linear var(--motion-fast);
}

.sidebar--drawer-open {
  opacity: 1;
  visibility: visible;
  transition: opacity var(--motion-fast) ease;
}

.sb-backdrop {
  position: fixed;
  inset: 0;
  z-index: 29;
  background: color-mix(in srgb, var(--ink) 45%, transparent);
  animation: sb-mode-fade var(--motion-fast) ease;
}

/* The contents, the backdrop and the drawer all arrive at their final state at
   once: full opacity, no fade. Visibility still flips, so the closed drawer
   stays out of the tab order. */
@media (prefers-reduced-motion: reduce) {
  .sb-backdrop,
  .sidebar--expanded > *,
  .sidebar--collapsed > * {
    animation: none;
  }

  .sidebar--drawer,
  .sidebar--drawer-open {
    transition: visibility 0s;
  }
}

.sb-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  min-height: 3.25rem;
}

.sidebar--collapsed .sb-header {
  flex-direction: column;
  padding: 0.75rem 0;
}

.sb-toggle--end {
  margin-left: auto;
}

.sb-brand {
  display: inline-flex;
  text-decoration: none;
  color: var(--color-heading);
}

.sb-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--pencil);
  cursor: pointer;
  font-size: 0.875rem;
  transition: color var(--motion-fast) ease;
}

.sb-toggle:hover {
  color: var(--ink-learner);
}

.sb-toggle:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: 2px;
}

/* The fold control is a drawn icon in the head: right of the wordmark when
   open, alone at the top of the rail when folded. */
.sb-toggle--head {
  margin-left: auto;
  width: 2rem;
  height: 2rem;
}

.sidebar--collapsed .sb-toggle--head {
  margin-left: 0;
}

/* Folded rail rows: Search, Profile and Recall, centred under New session. */
.sb-rail-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0 0 0.25rem;
}

.sb-rail-review {
  position: relative;
}

.sb-rail-badge {
  position: absolute;
  top: -4px;
  /* The 36px icon sits centred in the 48px rail (47px inside its right
     border), so -4px keeps the count clear of the rail's overflow clip. */
  right: -4px;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  font-weight: 700;
  line-height: 1;
  color: var(--ink-learner);
  font-variant-numeric: tabular-nums;
}

.sb-cta {
  padding: 0 0.75rem 0.25rem;
}

.sidebar--collapsed .sb-cta {
  padding: 0 0 0.25rem;
  display: flex;
  justify-content: center;
}

/* Written, not stamped: the primary action is a line of blue text. */
.sb-new-session {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  min-height: var(--line-pitch);
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  font-weight: 700;
  cursor: pointer;
  transition: color var(--motion-fast) ease;
}

.sb-new-session:hover {
  color: var(--color-accent-hover);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.sb-new-session:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: 2px;
}

.sb-new-session--icon {
  width: 2.25rem;
  height: 2.25rem;
  min-height: 0;
  justify-content: center;
}

.sb-list-wrap {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0;
  border-top: 1px solid var(--rule-strong);
}

/* Folded, the list is empty space above the foot; a rule under the actions
   would close off nothing. */
.sidebar--collapsed .sb-list-wrap {
  border-top: 0;
}

.sb-section {
  margin: 0;
}

/* A section heading, set as a heading: no tracking, no uppercase, no eyebrow. */
.sb-section-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  width: 100%;
  padding: 0 0.75rem;
  margin: 0;
  line-height: var(--line-pitch);
  border: 0;
  background: transparent;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  letter-spacing: 0;
  color: var(--color-text);
}

.sb-section-label .sb-inline-icon {
  color: var(--pencil);
}

/* Drawn strokes, not a glyph font: one weight, round ends, the control's ink. */
.sb-inline-icon,
.sb-toggle-icon {
  flex-shrink: 0;
}

.sb-section-count {
  font-variant-numeric: tabular-nums;
  color: var(--pencil);
  font-weight: 400;
}

.sb-section-label .sb-section-count {
  margin-left: auto;
}

.sb-session-list {
  list-style: none;
  margin: 0;
  padding: 0.25rem 0;
  display: flex;
  flex-direction: column;
}

.sb-empty-hint {
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  color: var(--pencil);
  padding: 0 0.75rem;
  margin: 0;
  line-height: var(--line-pitch);
}

.sb-view-all {
  display: block;
  padding: 0 0.75rem;
  line-height: var(--line-pitch);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  color: var(--ink-learner);
}

.sb-view-all:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: -2px;
}

.sb-rail {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding: 0.25rem 0.75rem;
  border-top: 1px solid var(--rule-strong);
}

.sb-rail--column {
  align-items: center;
  padding: 0.5rem 0;
}

.sb-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text);
  cursor: pointer;
  text-decoration: none;
  font-size: 1rem;
  transition: color var(--motion-fast) ease;
}

/* Rail Search is a button, not a link; strip the UA chrome so it reads as the
   same drawn mark as the links around it. */
.sb-icon-btn {
  background: transparent;
  border: 0;
  font: inherit;
  text-align: left;
}

.sb-icon:hover {
  color: var(--ink-learner);
}

.sb-icon:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: 2px;
}

/* Search is written on a rule, not boxed in. */
.sb-search {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0.75rem 0.25rem;
  padding: 0;
  border-bottom: 1px solid var(--rule-strong);
  color: var(--pencil);
}

.sb-search:focus-within {
  border-bottom-color: var(--ink-learner);
}

.sb-search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--color-text);
  font-family: inherit;
  font-size: 0.9375rem;
  line-height: calc(var(--line-pitch) - 1px);
  outline: none;
}

.sb-search-input::placeholder {
  color: var(--pencil);
}

.sb-search-count {
  padding: 0 0.75rem;
  line-height: var(--line-pitch);
  color: var(--pencil);
}

/* Two written toggles; the one in force is in ink and underlined. */
.sb-status-toggle {
  display: flex;
  gap: 1rem;
  margin: 0 0.75rem 0.25rem;
}

.sb-status-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0;
  border: 0;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: transparent;
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: calc(var(--line-pitch) - 4px);
  cursor: pointer;
  transition:
    color var(--motion-fast) ease,
    border-color var(--motion-fast) ease;
}

.sb-status-btn:hover {
  color: var(--color-accent-hover);
}

.sb-status-btn:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: 2px;
  border-radius: 0;
}

.sb-status-btn.active {
  color: var(--color-text);
  border-bottom-color: var(--ink);
}

.sb-navline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0.75rem;
  padding: 0;
  min-height: var(--line-pitch);
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  font-weight: 700;
  text-decoration: none;
}

.sb-navline:hover {
  color: var(--color-accent-hover);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.sb-navline:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: 2px;
}

.sb-navline-count {
  margin-left: auto;
  font-size: var(--fs-label);
  font-weight: 400;
  color: var(--pencil);
  font-variant-numeric: tabular-nums;
}
</style>
