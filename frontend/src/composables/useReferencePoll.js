import { computed, getCurrentInstance, onUnmounted, ref, unref, watch } from 'vue'

import { getSessionIngestion } from '../services/uploadApi.js'

// F-12 / E-07: one poller per session, shared by the reference banner and the
// per-upload chip. Before this there were two independent fixed-interval
// pollers (the banner every 2s, the upload chip every 1s for 90 attempts)
// hitting two endpoints for the same fact.
//
// Backoff while the server is still working, so a long ingest costs a handful
// of requests instead of one per second.
export const POLL_DELAYS_MS = [2000, 4000, 8000, 15000]

// E-07: the old chip gave up after 90 fixed-1s attempts. Under backoff an
// attempt count means nothing, so the ceiling is wall-clock. The cumulative
// schedule is 2, 6, 14, 29, 44, 59, 74, 89s; schedule() clamps the next delay
// to a watcher's remaining time so the ceiling lands on 90s exactly instead of
// overshooting to the next backoff step (104s).
export const WATCH_CEILING_MS = 90000

/**
 * Poll a session's ingestion status.
 *
 * @param {string|import('vue').Ref<string>|(() => string)} sessionIdSource
 * @returns {{
 *   documents: import('vue').Ref<Array<object>>,
 *   status: import('vue').Ref<string|null>,
 *   failed: import('vue').Ref<boolean>,
 *   refresh: () => void,
 *   retry: () => void,
 *   watch: (documentId: string|number, filename: string) => Promise<object>,
 *   stop: () => void,
 * }}
 */
export function useReferencePoll(sessionIdSource) {
  const documents = ref([])
  const status = ref(null)
  const failed = ref(false)

  let timer = null
  let stopped = false
  // Bumped on every poll so an in-flight request whose await resolves late
  // (after a refresh or a session switch) cannot clobber newer state. Same
  // generation-guard idiom the banner used before the poll moved in here.
  let generation = 0
  let delayIndex = 0
  // documentId (string) -> { filename, deadline, resolve }
  const watched = new Map()

  const readId = () =>
    typeof sessionIdSource === 'function' ? sessionIdSource() : unref(sessionIdSource)

  let sessionId = readId()

  function clearTimer() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  function settle(key, outcome) {
    const entry = watched.get(key)

    if (!entry) return
    watched.delete(key)
    entry.resolve(outcome)
  }

  // Map iteration tolerates deleting the entry currently being visited, so
  // these loops read the live Map rather than a snapshot copy.
  function settleAll(outcome) {
    for (const key of watched.keys()) settle(key, outcome)
  }

  // Resolve every watcher whose document has reached a terminal state, or
  // whose wall-clock ceiling has passed with the document still pending.
  function settleFromDocuments() {
    for (const [key, entry] of watched.entries()) {
      const doc = documents.value.find((d) => String(d?.id) === key)

      if (doc?.status === 'ready') settle(key, { status: 'ready' })
      else if (doc?.status === 'failed') settle(key, { status: 'failed', error: doc.error })
      else if (Date.now() >= entry.deadline) settle(key, { timedOut: true })
    }
  }

  function schedule() {
    if (stopped || timer) return

    // Keep going while the server is still working, while a watched upload has
    // not settled, or while the last poll threw (transient outage -- the banner
    // shows "References unavailable" and this loop is what clears it).
    if (!(status.value === 'pending' || failed.value || watched.size > 0)) return
    let delay = POLL_DELAYS_MS[Math.min(delayIndex, POLL_DELAYS_MS.length - 1)]
    delayIndex += 1

    // Never sleep past a watcher's wall-clock ceiling: at the 15s cap the next
    // step after 89s would be 104s, so the chip would sit on "Uploading..."
    // 14s beyond the advertised 90s. Wake exactly on the earliest deadline.
    for (const entry of watched.values()) {
      delay = Math.min(delay, Math.max(0, entry.deadline - Date.now()))
    }

    timer = setTimeout(() => {
      timer = null
      poll()
    }, delay)
  }

  async function poll() {
    if (stopped || !sessionId) return
    const gen = (generation += 1)
    const id = sessionId

    try {
      // fresh: true -- apiClient's 5s GET cache (F-18) would otherwise hand
      // this poll its own previous response back. silent: true -- the banner's
      // failed row is the error surface, not a toast per failed attempt.
      const res = await getSessionIngestion(id, { fresh: true, silent: true })

      if (stopped || gen !== generation) return
      status.value = res?.status ?? null
      documents.value = res?.documents ?? []

      // Recovered from an outage: drop back to the fast cadence.
      if (failed.value) delayIndex = 0
      failed.value = false
      settleFromDocuments()
    } catch (e) {
      if (stopped || gen !== generation) return

      // A 4xx is a verdict, not an outage: an unknown or foreign session id
      // 404s forever, so retrying it just loops at the 15s cap while the
      // banner claims "References unavailable" on a page that has none. Leave
      // `failed` false and `status` null so the banner stays hidden and
      // schedule() finds nothing to keep the loop alive.
      if (e?.status >= 400 && e.status < 500) {
        failed.value = false
        settleAll({ unavailable: true, error: e })

        return
      }

      // Keep the last known document list so per-file delete stays reachable.
      failed.value = true
      // The chip must not wait out the ceiling for an outage: the old poller
      // gave up on the first status error, so watchers settle immediately
      // while this loop keeps retrying in the background.
      settleAll({ unavailable: true, error: e })
    }

    schedule()
  }

  function refresh() {
    if (stopped) return
    clearTimer()
    delayIndex = 0
    poll()
  }

  /**
   * Resolve once `documentId` reaches a terminal state. Outcomes:
   * `{ status: 'ready' }`, `{ status: 'failed', error }`,
   * `{ unavailable: true, error }` (a poll threw), `{ timedOut: true }`
   * (still pending at the ceiling), `{ cancelled: true }` (session switched
   * or the poller stopped).
   */
  function watchDocument(documentId, filename) {
    if (stopped || !sessionId) return Promise.resolve({ cancelled: true })
    const key = String(documentId)

    return new Promise((resolve) => {
      watched.set(key, { filename, deadline: Date.now() + WATCH_CEILING_MS, resolve })
      refresh()
    })
  }

  function reset(nextId) {
    clearTimer()
    generation += 1
    delayIndex = 0
    settleAll({ cancelled: true })
    sessionId = nextId
    status.value = null
    documents.value = []
    failed.value = false

    if (nextId) poll()
  }

  function stop() {
    stopped = true
    clearTimer()
    settleAll({ cancelled: true })
  }

  if (sessionId) poll()

  if (getCurrentInstance()) {
    watch(
      () => readId(),
      (id) => reset(id),
    )
    onUnmounted(stop)
  }

  return {
    documents: computed(() => documents.value),
    status: computed(() => status.value),
    failed: computed(() => failed.value),
    refresh,
    retry: refresh,
    watch: watchDocument,
    stop,
  }
}
