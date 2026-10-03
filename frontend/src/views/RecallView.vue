<template>
  <section class="review">
    <BackButton label="Back" fallback="/" />
    <header class="head">
      <h1 class="title">Recall</h1>
      <p class="lede">Concepts due for a quick recall check.</p>
      <p class="lede">Each check that you get right extends the gap before the next one.</p>
    </header>

    <p v-if="queue.total > 0" class="count" data-testid="recall-count">
      {{ queue.total }} concept{{ queue.total === 1 ? '' : 's' }} ready.
    </p>

    <div v-if="showSkeleton" class="skel" data-testid="recall-loading" aria-hidden="true">
      <span class="skel-block" />
      <span class="skel-block" />
      <span class="skel-block skel-short" />
    </div>
    <span v-if="showSkeleton" class="sr-only" role="status">Loading</span>

    <template v-else-if="error">
      <p class="error" data-testid="recall-error">Could not load your recall queue.</p>
      <button type="button" class="retry coarse-2x" data-testid="recall-retry" @click="load">
        Retry
      </button>
    </template>

    <div v-else-if="groups.length" class="dividers">
      <section
        v-for="(group, g) in groups"
        :key="group.id"
        class="divider"
        data-testid="recall-divider"
        :aria-labelledby="tabId(g)"
      >
        <h2 :id="tabId(g)" class="tab" data-testid="recall-tab">
          <span class="tab-topic">{{ group.topic }}</span>
          <span class="tab-count">{{ group.items.length }} due</span>
        </h2>
        <div class="sheet">
          <ul class="cards">
            <li v-for="item in group.items" :key="item.concept">
              <button
                type="button"
                class="card"
                data-testid="recall-card"
                :disabled="startBusy"
                @click="startReview(item)"
              >
                <span v-if="item.due_at" class="card-head">{{ dueSince(item.due_at) }}</span>
                <span class="card-concept">{{ item.concept }}</span>
                <span class="card-streak">{{ streakLabel(item.streak) }}</span>
              </button>
            </li>
          </ul>
          <button
            type="button"
            class="check-group coarse-2x"
            data-testid="recall-check-group"
            :disabled="startBusy"
            @click="startReview(group.items[0])"
          >
            <span class="check-group-label">Check {{ group.topic }} now</span>
            <span class="check-group-first">starts with {{ group.items[0].concept }}</span>
          </button>
        </div>
      </section>

      <!-- D-11 again: a failed next page keeps what is loaded and retries
           that page alone; it never blanks the dividers above. -->
      <div v-if="moreError" class="more">
        <p class="error" data-testid="recall-more-error">
          Could not load more of your recall queue.
        </p>
        <button
          type="button"
          class="retry coarse-2x"
          data-testid="recall-more-retry"
          :disabled="moreLoading"
          @click="loadMore"
        >
          Retry
        </button>
      </div>
      <button
        v-else-if="hasMore"
        type="button"
        class="retry coarse-2x"
        data-testid="recall-load-more"
        :disabled="moreLoading"
        @click="loadMore"
      >
        Load more
      </button>
    </div>

    <section v-else-if="loaded" class="divider" data-testid="recall-empty">
      <h2 class="tab" data-testid="recall-tab">
        <span class="tab-topic">Nothing due</span>
      </h2>
      <div class="sheet sheet-empty">
        <p class="empty">
          No divider has a concept due. Finish a session and its concepts file themselves here when
          a check comes round.
        </p>
        <RouterLink to="/" class="empty-link coarse-2x">Back home</RouterLink>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import BackButton from '../components/BackButton.vue'
import { useSessionStore } from '../stores/session.js'
import { getReviewQueue } from '../services/reviewApi.js'
import { dueSince, groupBySource, streakLabel } from '../utils/recallQueue.js'

// The whole queue on one page (#363): no 3-row preview, no "View all". Pages
// past the route's cap of 100 come in by "Load more" (#385).
const QUEUE_LIMIT = 100

const router = useRouter()

const store = useSessionStore()

const queue = ref({ items: [], total: 0 })

const loaded = ref(false)

const startBusy = ref(false)

// D-11: a failed fetch is not an empty queue. `loading` and `error` are held
// apart from emptiness so the page can say which of the three it is.
const loading = ref(false)

const error = ref(false)

// The skeleton shows only while nothing is on screen: a failed fetch clears
// the queue, so a retry after an error blanks to the skeleton again.
const showSkeleton = computed(() => loading.value && !queue.value.items.length)

// The next page's own state, apart from the first load's: its failure leaves
// the loaded cards up.
const moreLoading = ref(false)

const moreError = ref(false)

// Where the next page starts on the server, counted from what each page
// returned, not from cards shown (a dropped duplicate still moved it on).
const nextOffset = ref(0)

// Appended pages regroup with the rest, so a later page can add cards to an
// earlier divider. Tab counts cover loaded items; the count line stays total.
const groups = computed(() => groupBySource(queue.value.items))

const hasMore = computed(() => queue.value.total > nextOffset.value)

function tabId(g) {
  return `recall-tab-${g}`
}

onMounted(() => {
  load()
})

async function load() {
  loading.value = true
  error.value = false
  moreError.value = false

  try {
    // Silent: the inline error row is the surface on this page, so a toast on
    // top of it would say the same thing twice. Retry goes through here too.
    queue.value = await getReviewQueue({ limit: QUEUE_LIMIT, offset: 0 }, { silent: true })
    nextOffset.value = queue.value.items.length
  } catch {
    // The recall page must never block; it says it could not load and offers
    // a retry instead of pretending nothing is due.
    queue.value = { items: [], total: 0 }
    error.value = true
  } finally {
    loading.value = false
    loaded.value = true
  }
}

async function loadMore() {
  if (moreLoading.value) return
  moreLoading.value = true
  moreError.value = false

  try {
    const page = await getReviewQueue(
      { limit: QUEUE_LIMIT, offset: nextOffset.value },
      { silent: true },
    )

    // An empty page means the queue shrank under us; stop offering more.
    nextOffset.value = page.items.length ? nextOffset.value + page.items.length : page.total
    // The queue can shift between pages (a check lands, a concept falls due),
    // so a concept already on screen is not filed twice.
    const seen = new Set(queue.value.items.map((item) => item.concept))
    const fresh = page.items.filter((item) => !seen.has(item.concept))
    queue.value = { ...page, items: [...queue.value.items, ...fresh] }
  } catch {
    moreError.value = true
  } finally {
    moreLoading.value = false
  }
}

async function startReview(item) {
  if (startBusy.value) return
  startBusy.value = true

  try {
    const created = await store.continueTopic({
      id: item.source_session_id,
      topic: item.source_topic,
    })

    if (created) {
      router.push({
        name: 'session',
        params: { id: created.id },
        query: { review_gap: item.concept },
      })
    }
  } catch {
    // F-45: store.continueTopic rethrows after _setError; without this catch
    // the rejection is unhandled and the double-click window stays open.
  } finally {
    startBusy.value = false
  }
}
</script>

<style scoped>
/* The recall box: one tabbed divider per source session, the concepts due
   from it filed behind the tab as blue cards. */
.review {
  max-width: 44rem;
  margin: 0 auto;
  padding-top: 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
}

.head {
  display: flex;
  flex-direction: column;
}

.title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 600;
  letter-spacing: var(--tracking-display);
  line-height: var(--lh-display);
  color: var(--ink);
}

.lede {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--pencil);
}

.count {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--pencil);
}

.dividers {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.divider {
  display: flex;
  flex-direction: column;
}

/* The divider's tab: the Settings rail's active tab (white stock, lifted,
   overlapping the sheet's top border by a pixel so tab and sheet read as one
   joined object). */
.tab {
  display: inline-flex;
  align-items: baseline;
  gap: 0.625rem;
  align-self: flex-start;
  max-width: 100%;
  position: relative;
  z-index: 1;
  margin: 0 0 -1px;
  padding: 0.5rem 1rem;
  border: 1px solid var(--card-edge);
  border-bottom: 0;
  border-radius: var(--radius-card) var(--radius-card) 0 0;
  background: var(--card);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: calc(var(--line-pitch) - 1px);
}

.tab-topic {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tab-count {
  flex: 0 0 auto;
  font-weight: 400;
  color: var(--pencil);
}

/* The sheet joins the tab, square only at the top-left where the tab sits
   (the Settings panel's corner). */
.sheet {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-radius: 0 var(--radius-card) var(--radius-card) var(--radius-card);
  box-shadow: 0 1px 0 var(--card-drop);
}

.cards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr));
  gap: 0.75rem;
}

/* Each due concept is a card in the learner's blue stock: the pencil head
   line (due-since), the concept, then the streak in words. The whole card is
   the control that starts its check. */
.card {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  width: 100%;
  height: 100%;
  min-height: 5.5rem;
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--card-learner-edge);
  border-radius: var(--radius-card);
  background: var(--card-learner);
  box-shadow: 0 1px 0 var(--card-drop);
  color: var(--ink-learner);
  font-family: var(--font-sans);
  text-align: left;
  cursor: pointer;
}

.card-head,
.card-streak {
  font-size: var(--fs-label);
  line-height: var(--lh-body);
  color: var(--pencil);
}

/* A concept is never truncated -- it is the thing the learner has to
   recall. */
.card-concept {
  font-size: var(--fs-body);
  font-weight: 700;
  line-height: var(--lh-body);
  overflow-wrap: anywhere;
}

.card:hover:not(:disabled) .card-concept {
  color: var(--color-accent-hover);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.card:disabled {
  color: var(--pencil);
  cursor: default;
}

.card:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

/* Written, not stamped: the per-divider control is a blue line with its
   pencil aside naming the card it starts. */
.check-group {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.25rem 0.75rem;
  align-self: flex-start;
  max-width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--lh-body);
  text-align: left;
  overflow-wrap: anywhere;
  cursor: pointer;
}

/* Only the written control is underlined; the pencil aside is a note. */
.check-group-label {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.check-group-first {
  font-weight: 400;
  color: var(--pencil);
}

.check-group:hover:not(:disabled) {
  color: var(--color-accent-hover);
}

.check-group:disabled {
  color: var(--pencil);
  cursor: default;
}

.check-group:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.sheet-empty {
  gap: 0.5rem;
}

.empty {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--pencil);
}

.empty-link {
  align-self: flex-start;
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.empty-link:hover {
  color: var(--color-accent-hover);
}

/* Skeleton: pencil-weight rules on the pitch, no shimmer (same as the session
   profile's). */
.skel {
  display: flex;
  flex-direction: column;
}

.skel-block {
  display: block;
  height: 1.75rem;
  border-bottom: 1px solid var(--rule-strong);
}

.skel-short {
  width: 55%;
}

.error {
  margin: 0;
  max-width: 42rem;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink-marker-text);
}

.more {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.retry {
  align-self: flex-start;
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

.retry:hover:not(:disabled) {
  color: var(--color-accent-hover);
}

.retry:disabled {
  color: var(--pencil);
  text-decoration: none;
  cursor: default;
}

.retry:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

/* Narrow: one card per line, the sheet tighter so cards run near its edge. */
@media (max-width: 599px) {
  .cards {
    grid-template-columns: minmax(0, 1fr);
  }

  .card {
    min-height: 0;
  }

  .sheet {
    padding: 0.75rem;
  }
}
</style>
