<template>
  <section class="session" :class="{ 'is-sheet': !notFound, 'panel-collapsed': panelCollapsed }">
    <div v-if="notFound" class="not-found" data-testid="session-not-found">
      <BackButton />
      <span class="folio" data-tabular>404</span>
      <h1 class="topic">Session not found</h1>
      <p class="not-found-sub">
        The session id <code>{{ id }}</code> doesn't exist or was deleted.
      </p>
      <router-link to="/" class="home-link" data-testid="session-not-found-home">
        <svg
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
          <path d="M16 10 L4 10 M9 4.5 L4 10 L9 15.5" />
        </svg>
        Back to sessions
      </router-link>
    </div>

    <template v-else>
      <div class="sheet-header">
        <!-- D-21: SessionHeader's own h1 is gated on a resolved topic, so the
             page had no h1 at all while the detail fetch was in flight. This
             fills that window only -- the two are mutually exclusive on the
             same predicate, so the page never carries two h1s. The 404 branch
             is excluded structurally: it is the v-if arm above. -->
        <h1 v-if="!headerTopic" class="sr-only">Session</h1>
        <SessionHeader
          :session="headerSession"
          :level="profileLevel"
          :ref-status="headerRefStatus"
          :streaming="store.streamState !== 'idle'"
        />
      </div>

      <!-- Notes before cue in the DOM so the reading order is thread first;
           the panel is placed in column 2 by the grid. -->
      <div class="sheet-notes">
        <div
          class="messages"
          :class="{ 'is-empty': !store.messages.length }"
          data-testid="session-messages"
        >
          <div class="notes-measure">
            <MessageListSkeleton v-if="store.detailLoading" />
            <template v-else>
              <button
                v-if="store.hasMoreMessages && store.messages.length"
                type="button"
                class="load-earlier"
                data-testid="load-earlier"
                :disabled="store.loadingEarlier"
                @click="onLoadEarlier"
              >
                <template v-if="store.loadingEarlier">Loading…</template>
                <template v-else-if="store.loadEarlierError"
                  >Could not load earlier messages — retry</template
                >
                <template v-else>Load earlier messages</template>
              </button>
              <ChatEmptyState
                v-if="!store.messages.length"
                :archived="isEnded"
                @quick-prompt="useQuickPrompt"
              />
              <MessageList
                v-if="store.messages.length || store.streamingMessage || awaitingResponse"
                :messages="store.messages"
                :streaming-message="store.streamingMessage"
                :awaiting="awaitingResponse"
                :landed="cuesLanded"
              />

              <!-- #346: the check batch and the level picker scroll with the
                   page at every width. Pinned in the foot they took a fixed
                   slab of the viewport (R2: ~420px of a 844px screen), and the
                   foot is sticky now, so only the composer rides there. -->
              <CheckQuestion
                v-if="store.pendingCheck"
                class="transcript-card"
                :check="store.pendingCheck"
                :busy="store.streamState !== 'idle'"
                :answering="store.checkAnswering"
                @answer="onAnswerCheck"
                @skip="onSkipCheck"
                @back="store.prevCheck"
                @next="store.nextCheck"
                @done="onDoneCheck"
                @stop="onStopCheck"
              />

              <DiagnosticConsentCard
                v-if="showDiagnosticCard"
                class="transcript-card"
                :busy="store.streamState !== 'idle' || !canSend || diagLevelBusy"
                :error="diagError"
                @quiz="onDiagQuiz"
                @level="onDiagLevel"
                @dismiss="dismissDiag()"
              />

              <TopicSuggestCard
                v-if="topicCard"
                class="transcript-card"
                :card="topicCard"
                :busy="store.streamState !== 'idle' || !canSend"
                @pick="onTopicPick"
                @dismiss="dismissTopicCard()"
              />
            </template>
          </div>
        </div>

        <div class="notes-foot">
          <div class="notes-measure">
            <!-- One status slot: persistent state (caps, send error) stays
                 mounted because the composer's aria-describedby points at it;
                 the transient captions below it land one at a time. -->
            <div class="status-slot">
              <CapBanners />

              <div
                v-if="store.error || lastError"
                class="status-line is-alert"
                role="alert"
                data-testid="session-error"
              >
                <p class="error-message">{{ friendlyError(lastError || store.error) }}</p>
                <button
                  v-if="canRetry"
                  type="button"
                  class="error-retry"
                  data-testid="session-error-retry"
                  @click="retryLastMessage"
                >
                  Retry
                </button>
                <router-link
                  v-if="store.duplicateReopen"
                  :to="{ name: 'session', params: { id: store.duplicateReopen.sessionId } }"
                  class="home-link"
                  data-testid="go-to-active-session"
                >
                  Go to active session
                </router-link>
              </div>

              <ReferenceStatusBanner
                :status="refStatus"
                :documents="refDocuments"
                :failed="refFailed"
                @refresh="refreshReferences"
              />

              <UploadStatus v-if="topCaption === 'upload'" :upload="uploadStatus" />

              <p
                v-if="topCaption === 'followup'"
                class="status-line followup-notice"
                data-testid="followup-notice"
                role="status"
                aria-live="polite"
              >
                {{ store.followupNotice }}
              </p>
            </div>

            <Composer
              v-if="!isEnded"
              ref="composerRef"
              :model-value="draft"
              @update:model-value="draft = $event"
              :disabled="!canSend"
              :uploading="uploading"
              :sending="sending"
              :stream-state="store.streamState"
              :describedby="capDescribedby"
              @send="send"
              @stop="store.stopStream"
              @attach="onAttachFile"
            />

            <SessionEndedBanner
              v-if="isEnded"
              :ended-at="current.ended_at"
              :summary="endedSummary"
              :loading="resuming"
              :has-gaps="hasGaps"
              @resume="resume"
              @resume-gaps="resumeReviewGaps"
            />
          </div>
        </div>
      </div>

      <div class="sheet-cue">
        <CueColumn
          :profile="liveProfile"
          :session-id="props.id"
          :testing-gap="testingGap"
          @landed="onCuesLanded"
        />
      </div>

      <div class="sr-only" role="status" aria-live="polite" data-testid="stream-status">
        {{ streamAnnouncement }}
      </div>

      <GapPickerDialog
        v-model:visible="gapPickerOpen"
        :gaps="confirmedGaps"
        @select="sendReviewSeed"
      />

      <Dialog
        v-model:visible="summaryDialog"
        header="Nice work!"
        modal
        :closable="true"
        data-testid="session-summary-dialog"
        class="crux-dialog summary-dialog"
      >
        <p class="summary" :data-testid="`session-summary-${summaryKind}`">
          {{ summaryText }}
        </p>
        <template #footer>
          <Button label="Close" data-testid="session-summary-close" @click="goHome" />
        </template>
      </Dialog>
    </template>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Button from 'primevue/button'
import Dialog from 'primevue/dialog'

import BackButton from '../components/BackButton.vue'
import CapBanners from '../components/chat/CapBanners.vue'
import ChatEmptyState from '../components/chat/EmptyState.vue'
import CheckQuestion from '../components/chat/CheckQuestion.vue'
import Composer from '../components/chat/Composer.vue'
import CueColumn from '../components/chat/CueColumn.vue'
import DiagnosticConsentCard from '../components/DiagnosticConsentCard.vue'
import GapPickerDialog from '../components/GapPickerDialog.vue'
import MessageList from '../components/chat/MessageList.vue'
import MessageListSkeleton from '../components/chat/MessageListSkeleton.vue'
import SessionHeader from '../components/chat/SessionHeader.vue'
import SessionEndedBanner from '../components/SessionEndedBanner.vue'
import TopicSuggestCard from '../components/TopicSuggestCard.vue'
import ReferenceStatusBanner from '../components/chat/ReferenceStatusBanner.vue'
import UploadStatus from '../components/chat/UploadStatus.vue'
import { friendlyError, StreamAbortedError } from '../lib/errors.js'
import { useSessionStore } from '../stores/session.js'
import { REDUCED_MOTION_QUERY, useMediaQuery } from '../composables/useMediaQuery.js'
import { usePanel } from '../composables/usePanel.js'
import { useToast } from '../composables/useToast.js'
import { costBus } from '../services/costBus.js'
import { getSessionProfile, patchProfile } from '../services/profileApi.js'
import { uploadDocument, validateFile } from '../services/uploadApi.js'
import { useReferencePoll } from '../composables/useReferencePoll.js'
import { entryNames } from '../utils/conceptEntry.js'
import { formatResetTime } from '../utils/formatDate.js'
import {
  session as sessionStorageThunk,
  storageGet,
  storageRemove,
  storageSet,
} from '../utils/safeStorage.js'
import { stripAutoPrefix } from '../utils/sessionCard.js'
import { costCapToastMessage, dailyCapToastMessage } from '../lib/capToast.js'

const props = defineProps({ id: { type: String, required: true } })

const route = useRoute()

const router = useRouter()

const store = useSessionStore()

// Drives the panel column width only (see --panel-col in <style>); CueColumn
// owns its own collapsed rendering and the toggle button.
const { collapsed: panelCollapsed } = usePanel()

const draft = ref('')

const lastSentText = ref('')

const summaryDialog = ref(false)

const summaryText = ref('')

const summaryKind = ref('summary')

const notFound = ref(false)

const resuming = ref(false)

const gapPickerOpen = ref(false)

const sending = ref(false)

const composerRef = ref(null)

const uploading = ref(false)

const uploadStatus = ref(null)

// Same generation-counter idiom as useReferencePoll: /session/:id reuses
// this component instance across sidebar switches, so an in-flight upload poll
// from the previous session must not write uploadStatus/uploading after the id
// changes. Bumped by the props.id watcher; every write after an await checks it.
let uploadGen = 0

const lastError = ref(null)

// F-12 / E-07: one poller for this session, shared by the reference banner and
// the upload chip. Destructured at top level so the template auto-unwraps the
// refs (a nested `refPoll.documents` would hand the child the ComputedRef).
// It follows props.id itself and settles any watcher on a session switch.
const {
  documents: refDocuments,
  status: refStatus,
  failed: refFailed,
  refresh: refreshReferences,
  watch: watchReference,
} = useReferencePoll(() => props.id)

// Diagnostic consent card (spec 2026-07-25-diagnostic-consent-design.md).
// diagProfile holds the latest GET /profile/:id payload ({ profile, etag });
// null means not loaded or load failed - the card simply does not render,
// the tutor's conversational offer is the fallback.
const diagProfile = ref(null)

const diagDismissed = ref(false)

const diagError = ref('')

// A conversational decline ("no thanks, just teach me") never writes a level,
// so knowledge_level stays null and the card would render for the rest of the
// session. Two completed tutor turns with the level still null are treated as
// an implicit decline. Dismissals (explicit or implicit) persist per session in
// sessionStorage so a reload does not resurrect the card.
let diagNullTurns = 0

function diagDismissKey(id) {
  return `crux:diag-dismissed:${id}`
}

function dismissDiag() {
  diagDismissed.value = true
  // storage unavailable (private mode/quota) - in-memory dismissal still holds
  storageSet(sessionStorageThunk, diagDismissKey(props.id), '1')
}

// F5: guards onDiagLevel's async body against a rapid second click firing a
// second PATCH with the same (soon-to-be-stale) etag. Folded into the card's
// busy binding so the buttons visually disable too.
const diagLevelBusy = ref(false)

const showDiagnosticCard = computed(() =>
  Boolean(
    diagProfile.value &&
    diagProfile.value.profile?.knowledge_level == null &&
    !store.pendingCheck &&
    !diagDismissed.value &&
    !isEnded.value &&
    !resuming.value &&
    !notFound.value &&
    !store.detailLoading,
  ),
)

// #354 topic card: offered once per session, under the tutor's first reply at
// the learner's level. It lives only while that reply is the latest message:
// a tap (or anything the learner writes) appends a learner turn and closes it.
// A dismissal persists per session, like the level picker's.
const topicDismissed = ref(false)

function topicDismissKey(id) {
  return `crux:topic-dismissed:${id}`
}

function dismissTopicCard() {
  topicDismissed.value = true
  storageSet(sessionStorageThunk, topicDismissKey(props.id), '1')
}

const topicCard = computed(() => {
  const last = store.messages.at(-1)

  if (last?.role !== 'assistant' || !last.topic_suggestions) return null

  if (
    topicDismissed.value ||
    store.streamingMessage ||
    store.pendingCheck ||
    showDiagnosticCard.value ||
    isEnded.value ||
    resuming.value ||
    notFound.value ||
    store.detailLoading
  )
    return null

  return last.topic_suggestions
})

async function onTopicPick(text) {
  if (!canSend.value) return
  lastError.value = null
  cuesLanded.value = false
  sending.value = true

  try {
    await store.sendMessageStreaming({ text })
  } catch (e) {
    // The store already surfaced an aborted stream (ended banner / login).
    if (e instanceof StreamAbortedError) return
    lastSentText.value = text
    lastError.value = e
  } finally {
    sending.value = false
  }
}

async function loadDiagProfile(id) {
  try {
    const data = await getSessionProfile(id)

    if (id !== props.id) return // stale response from a previous session
    diagProfile.value = data
  } catch {
    if (id === props.id) diagProfile.value = null
  }
}

// F-18: a live region over the token-streaming bubble spams SRs with every
// mutation. Announce discrete transitions instead. The store's stream state
// machine has intermediate members beyond idle/streaming (tool_running,
// stopping), so the edges we care about are idle -> non-idle (start) and
// non-idle -> idle (finish), not every individual hop.
const streamAnnouncement = ref('')

// Both things this view does on a stream-state edge, in one watcher.
//
// F2: the agent may have conversationally recorded a declared level
// (update_topic_profile) during the turn -- that only becomes visible to us
// via a refetch. Once the tutor's turn finishes, refetch so the card hides
// itself and the cached etag stays fresh, instead of lingering with a stale
// null level until the next explicit reload.
// The same refetch is what keeps the cue column live: the store only writes
// topic_profile on loadSession, so a turn that recorded a gap, a mastered
// concept or a level would otherwise never reach the cues. Runs every turn,
// not only while the level is unset; the implicit-decline accounting still
// reads the pre-refetch copy, exactly as before.
watch(
  () => store.streamState,
  (next, prev) => {
    if (prev === 'idle' && next !== 'idle') {
      streamAnnouncement.value = 'Tutor is replying.'

      return
    }

    if (prev === 'idle' || next !== 'idle') return
    streamAnnouncement.value = 'Reply finished.'

    const stillUnset =
      diagProfile.value &&
      diagProfile.value.profile?.knowledge_level == null &&
      !diagDismissed.value

    loadDiagProfile(props.id)

    if (!stillUnset) return
    diagNullTurns += 1

    if (diagNullTurns >= 2) dismissDiag()
  },
)

// THE target-id discriminator, written once. While the detail fetch is in
// flight, store.currentSession still holds the PREVIOUS session (it is
// overwritten only after the await resolves), so anything that reads a field
// off it during a switch would show the old session's state: a stale ended
// banner, a resume() pointed at the old id, or a composer enabled+pointed at
// the old session (currentSessionId lags props.id until the await resolves) —
// a send would land in the wrong session and then vanish when the target
// detail loads. `current` is the session only when it IS this view's session,
// and null otherwise; everything below derives from it.
const current = computed(() =>
  store.currentSession?.id === props.id ? store.currentSession : null,
)

// Falls back to not-ended until the target detail resolves.
const isEnded = computed(() => Boolean(current.value?.ended_at))

// The one profile the frontend holds. The store's copy is only written on
// loadSession, so the per-turn GET /profile/:id refetch (diagProfile) is the
// fresher of the two and wins when present; both are already discriminated on
// props.id, so a switch never paints the previous session's cues.
const liveProfile = computed(() => {
  if (diagProfile.value?.profile) return diagProfile.value.profile

  return current.value?.topic_profile ?? null
})

const profileLevel = computed(() => liveProfile.value?.knowledge_level || '')

const startedAt = computed(() => current.value?.created_at || '')

const endedSummary = computed(() => stripAutoPrefix(liveProfile.value?.last_session_summary))

// While a check batch is open, the cue it tests carries the red underline.
const testingGap = computed(() => store.pendingCheck?.gap || '')

// The full gap list drives the picker (single gap skips it, >1 gap opens it).
const confirmedGaps = computed(() => entryNames(current.value?.topic_profile?.confirmed_gaps))

// Gates the "Review my gaps" CTA — only meaningful once we're showing the
// ended banner for this session.
const hasGaps = computed(() => confirmedGaps.value.length > 0)

const canEnd = computed(() => Boolean(current.value) && !isEnded.value)

const canSend = computed(() => canEnd.value && !store.dailyCapReached && !store.costCapReached)

// Cue-lands: CueColumn diffs the live profile and tells us when new cues were
// written; the gutter of the latest tutor turn then carries the blue tick
// until the learner writes again.
const cuesLanded = ref(false)

function onCuesLanded() {
  cuesLanded.value = true
}

// One caption slot, one caption at a time: an upload report outranks a
// follow-up notice (it is the newer, more specific event).
const topCaption = computed(() => {
  if (uploadStatus.value) return 'upload'

  if (store.followupNotice) return 'followup'

  return null
})

// Optimistic header: while the detail fetch is in flight, store.currentSession
// still holds the PREVIOUS session (it is overwritten only after the await
// resolves), so paint the target session's topic from the already-known list
// row. View-local only — store.currentSession is never stubbed, which is what
// keeps this clear of the PR #72 switch-reload bug class.
const knownRow = computed(() => store.sessions.find((s) => s.id === props.id) || null)

const headerTopic = computed(() => {
  if (current.value) return current.value.topic || ''

  return knownRow.value?.topic || ''
})

// Ticket 10: the action bar takes one session object. Built from the same
// optimistic sources as headerTopic so the D-21 h1 gating is unchanged;
// ended_at reads `current` only, so End/Resume flips on the same predicate as
// isEnded and the composer. `pinned` falls back to the list row (setPinned
// patches both copies optimistically).
const headerSession = computed(() => {
  if (!current.value && !knownRow.value) return null

  return {
    id: props.id,
    topic: headerTopic.value,
    created_at: startedAt.value,
    pinned: Boolean(current.value?.pinned ?? knownRow.value?.pinned),
    ended_at: current.value?.ended_at ?? null,
  }
})

// The reference-file dot in the action bar reads the same session-wide
// aggregate the status banner reads (refStatus from useReferencePoll, which
// mirrors backend documents_service.aggregate_status: (pending or processing)
// > ready > failed > null). Re-deriving a rank from the raw document list here
// used a different priority (any non-terminal doc beat a failure), so a
// session with one ready and one failed file showed a green banner alongside
// a red dot -- two different verdicts for the same ingestion state. The
// aggregate's 'pending' maps onto the header's own 'processing' vocabulary;
// 'ready'/'failed'/null pass through unchanged.
const headerRefStatus = computed(() => {
  const s = refStatus.value

  return s === 'pending' ? 'processing' : s || null
})

// When the composer is disabled because a daily/cost cap was hit, point its
// aria-describedby at the matching cap banner so screen-reader users hear why
// input is blocked. null when not cap-disabled (renders no attribute).
const capDescribedby = computed(() => {
  const ids = []

  if (store.dailyCapReached) ids.push('cap-banner-daily')

  if (store.costCapReached) ids.push('cap-banner-cost')

  return ids.length ? ids.join(' ') : null
})

const { showError, showWarn } = useToast()

watch(
  () => store.dailyCapReached,
  (now) => {
    if (!now || !store.dailyCapInfo) return
    const when = formatResetTime(store.dailyCapInfo.resets_at)
    const { message, summary } = dailyCapToastMessage(store.dailyCapInfo, when)
    showError(message, { summary, life: 8000 })
  },
)

watch(
  () => store.costCapReached,
  (now) => {
    if (!now || !store.costCapInfo) return
    const when = formatResetTime(store.costCapInfo.resets_at)
    const { message, summary } = costCapToastMessage(store.costCapInfo, when)
    showError(message, { summary, life: 8000 })
  },
)

// One warning per level, per mount of this view (i.e. per session entry).
// Soft and urgent are tracked separately so an urgent warning can still
// surface even if a soft one already showed earlier in this mount (urgent
// escalates the signal; it must never be silently swallowed by a prior soft
// warning), while neither level repeats. Never read by the template, so plain
// per-instance flags (setup scope, i.e. one pair per mount) rather than refs.
let softCapShown = false

let urgentCapShown = false

function resolveCostWarningLevel(detail) {
  let level = detail?.level

  if (!level && typeof detail?.header === 'string') {
    const match = detail.header.match(/level=(\w+)/)
    level = match ? match[1] : null
  }

  return level === 'urgent' ? 'urgent' : 'soft'
}

function onCostWarning(event) {
  const level = resolveCostWarningLevel(event?.detail)

  if (level === 'urgent') {
    if (urgentCapShown) return
    urgentCapShown = true
    showError('You are very close to today’s cost limit.', {
      summary: 'Cost limit near',
      life: 8000,
    })

    return
  }

  if (softCapShown) return
  softCapShown = true
  showWarn('You’re approaching the daily cost limit for this session.', {
    summary: 'Cost warning',
    life: 6000,
  })
}

onMounted(() => costBus.addEventListener('cost-warning', onCostWarning))

onUnmounted(() => costBus.removeEventListener('cost-warning', onCostWarning))

// #346: the document is the scroller. A body class drives the route-scoped
// flex-height cascade (see <style>) so a short transcript still puts the
// composer at the foot of the viewport. Removed unconditionally on leave.
onMounted(() => document.body.classList.add('session-page'))

onUnmounted(() => document.body.classList.remove('session-page'))

// There is no router scrollBehavior, so a long session scrolled to its foot
// would hand the next route a scrolled-down document.
onUnmounted(() => window.scrollTo(0, 0))

// F-01: leaving the session view must not leave a stream running (and
// billing) in the background, nor let it deliver into a later session.
onUnmounted(() => store.abandonStream())

// Show the "typing" placeholder when we've appended the user message but the
// tutor reply hasn't arrived yet. Driven by `sending` rather than `store.loading`
// so list-load spinners don't flicker the placeholder.
const awaitingResponse = computed(() => {
  if (!sending.value) return false
  const last = store.messages[store.messages.length - 1]

  return !last || last.role === 'user'
})

// #346: the page scrolls, so every scroll read and write goes to the document.
function docScrollHeight() {
  return (document.scrollingElement || document.documentElement).scrollHeight
}

function scrollToBottom() {
  nextTick(() => window.scrollTo(0, docScrollHeight()))
}

// #347: follow the stream. Autoscroll is on until the learner scrolls up and
// back on once they return to the bottom. Cancel keys on scroll *direction*,
// not on "not at the bottom": content growth and an in-flight smooth scroll
// both leave the view short of the bottom without the learner doing anything,
// and neither ever moves scrollY up. Any upward move short of the exact bottom
// cancels (a small nudge counts); a shrink that clamps the view to the bottom
// does not. Re-arming takes FOLLOW_SLACK_PX so sub-pixel rounding still
// counts as "back at the bottom". Never read by the template, so plain lets.
const FOLLOW_SLACK_PX = 40

let following = true

let lastScrollY = 0

const reducedMotion = useMediaQuery(REDUCED_MOTION_QUERY)

function distanceFromBottom() {
  return docScrollHeight() - window.scrollY - window.innerHeight
}

function onWindowScroll() {
  const distance = distanceFromBottom()

  if (window.scrollY < lastScrollY && distance > 1) following = false
  else if (distance <= FOLLOW_SLACK_PX) following = true
  lastScrollY = window.scrollY
}

// The scroll event lags the gesture by a frame, long enough for a token to
// land and a programmatic scroll to swallow the learner's first flick. A wheel
// turned upward is intent itself, so cancel on it directly.
function onWindowWheel(event) {
  if (event.deltaY < 0 && window.scrollY > 0) following = false
}

onMounted(() => {
  window.addEventListener('scroll', onWindowScroll, { passive: true })
  window.addEventListener('wheel', onWindowWheel, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', onWindowScroll)
  window.removeEventListener('wheel', onWindowWheel)
})

function followStream() {
  if (!following) return
  nextTick(() =>
    window.scrollTo({
      top: docScrollHeight(),
      behavior: reducedMotion.value ? 'instant' : 'smooth',
    }),
  )
}

// content grows in place (streamingMessage.content += text), so messages.length
// never moves while a reply streams -- watch the parts that add height. A tool
// call settling from running to done relabels its chip, which can wrap.
watch(
  () => {
    const s = store.streamingMessage

    return s && [s.content.length, s.tool_calls.map((t) => t.state).join(), s.citations.length]
  },
  (streamSize) => {
    if (streamSize) followStream()
  },
)

// True from the moment a "load earlier" click starts until its scroll-offset
// restore lands. The autoscroll watcher below fires when store.messages.length
// changes (prepend included) - without this guard it would yank the view back
// to the bottom right after older messages are spliced in. store.loadingEarlier
// is already false by the time the watcher flushes (it's cleared before the
// awaited nextTick below resolves), so it can't do this job - this local flag
// is the whole point. Never read by the template, so a plain flag, not a ref.
let prepending = false

async function onLoadEarlier() {
  const prevHeight = docScrollHeight()
  const prevTop = window.scrollY
  prepending = true

  try {
    await store.loadEarlierMessages()
    await nextTick()
    window.scrollTo(0, prevTop + (docScrollHeight() - prevHeight))
  } finally {
    prepending = false
  }
}

watch([() => store.messages.length, awaitingResponse], () => {
  if (prepending) return

  // A learner who just sent expects to see the reply, wherever they were; a
  // reply landing while they read history above must not yank them down.
  if (awaitingResponse.value || store.messages.at(-1)?.role === 'user') following = true

  if (following) scrollToBottom()
})

// The check batch and the level picker sit at the end of the transcript, so a
// newly opened one would otherwise land below the fold. Shallow watch -- the
// store assigns a fresh pendingCheck per batch, so this fires once per batch,
// not per answered item.
watch(
  [() => store.pendingCheck, showDiagnosticCard, topicCard],
  ([check, diag, topic], [prevCheck, prevDiag, prevTopic]) => {
    if ((check && check !== prevCheck) || (diag && !prevDiag) || (topic && !prevTopic))
      scrollToBottom()
  },
)

async function loadCurrent(id) {
  // Reset per-load so navigating away from a 404 session clears the state.
  notFound.value = false
  // Drop any prior session's send-error so it can't render (with a wrong-session
  // Retry) over the newly-navigated session. Mirrors store.error clearing on
  // loadSession entry. loadCurrent only runs on mount + id-change, so a same-
  // session send-error stays retryable.
  lastError.value = null
  following = true
  lastScrollY = window.scrollY
  cuesLanded.value = false
  diagProfile.value = null
  diagNullTurns = 0
  diagDismissed.value = storageGet(sessionStorageThunk, diagDismissKey(id)) === '1'
  topicDismissed.value = storageGet(sessionStorageThunk, topicDismissKey(id)) === '1'
  diagError.value = ''
  diagLevelBusy.value = false
  loadDiagProfile(id) // deliberately not awaited: card is best-effort

  try {
    await store.loadSession(id)
  } catch (e) {
    // Superseded load: a newer navigation already changed props.id, so a late
    // 404 from the session we left must not flash its not-found over the one now
    // on screen. Same discriminator the success-path computeds use (id===props.id).
    if (id !== props.id) return

    if (e?.status === 404) {
      notFound.value = true
      store.setError(null)
    }
  }

  if (!isEnded.value && !notFound.value) focusComposer()

  // Covers fresh navigation (new id, e.g. from ProfileView's "Review gaps"
  // button, or the level-at-start picker's "Quiz me" chip) where the query
  // is already present before the session loads. handleQuizQuery runs first
  // so its review_gap precedence guard reads the query before
  // handleReviewGapQuery strips it.
  if (!notFound.value) {
    await handleQuizQuery()
    await handleReviewGapQuery()
  }
}

onMounted(() => {
  loadCurrent(props.id)
  restoreStashedDraft(props.id)
})

// Sidebar session->session clicks reuse this route component (same /session/:id
// route), so onMounted does not re-fire. Re-load when the id prop changes;
// otherwise the body keeps showing the previous session until a full refresh.
watch(
  () => props.id,
  (id) => {
    if (!id) return
    // Invalidate any in-flight upload/poll from the previous session and clear
    // its banner/lock so the new session never shows or inherits them.
    uploadGen += 1
    uploading.value = false
    uploadStatus.value = null
    loadCurrent(id)
    restoreStashedDraft(id)
  },
)

// Covers same-id in-place navigation (e.g. ProfileView -> back to the session
// already open) where loadCurrent does not re-run. Not immediate: the initial
// value is handled by loadCurrent above, which waits for the session to load
// first -- an immediate watch here would fire during setup, before
// store.currentSession is populated, and either send into the wrong session
// or throw "no active session".
watch(
  () => route.query.review_gap,
  (gap) => {
    if (!gap) return

    if (!current.value) return
    handleReviewGapQuery()
  },
)

// Twin of the review_gap watcher above, for the smart-start quiz seed.
watch(
  () => route.query.quiz,
  (quiz) => {
    if (!quiz) return

    if (!current.value) return
    handleQuizQuery()
  },
)

function focusComposer() {
  nextTick(() => composerRef.value?.focus())
}

function useQuickPrompt(text) {
  draft.value = text
  focusComposer()
}

const canRetry = computed(() => Boolean(lastSentText.value) && !sending.value && !isEnded.value)

async function send() {
  const text = draft.value

  if (!text.trim()) return
  draft.value = ''
  lastSentText.value = text
  lastError.value = null
  // The learner is writing again: the previous turn's landed tick is spent.
  cuesLanded.value = false
  sending.value = true

  try {
    await store.sendMessageStreaming({ text })
    lastSentText.value = ''
  } catch (e) {
    if (e instanceof StreamAbortedError) {
      // The store already surfaced the state (ended banner / login redirect),
      // so a generic error chip on top of it would be noise. Just give the
      // text back so nothing the user typed is lost.
      if (e.reason === 'auth_expired') {
        // E-05: this component is about to unmount via the login redirect, so
        // in-memory draft restore is not enough - park it where the post-login
        // remount can find it. If storage is unavailable (private mode/quota)
        // the in-memory restore below is still the best we can do.
        storageSet(sessionStorageThunk, `crux:draft:${props.id}`, text)
      }

      draft.value = text
    } else {
      draft.value = text
      lastError.value = e
    }
  } finally {
    sending.value = false
  }
}

async function retryLastMessage() {
  // E-14: the composer wins. After a failed send the draft is restored, and the
  // user may have edited it before hitting Retry - resending lastSentText would
  // silently discard that edit. lastSentText is only the fallback for the case
  // where the composer was cleared.
  if (!draft.value.trim() && lastSentText.value) draft.value = lastSentText.value

  if (!draft.value.trim()) return
  await send()
}

// E-05: a draft stashed by send() just before the auth redirect survives the
// login round-trip in sessionStorage; restore it exactly once.
function restoreStashedDraft(id) {
  const key = `crux:draft:${id}`
  const stashed = storageGet(sessionStorageThunk, key)

  if (stashed !== null) {
    draft.value = stashed
    storageRemove(sessionStorageThunk, key)
  }
}

async function onDiagQuiz() {
  if (!canSend.value) return
  const id = props.id
  diagError.value = ''

  try {
    await store.sendMessageStreaming({ text: 'Quiz me to gauge my level' })
  } catch {
    if (id !== props.id) return // stale response from a previous session
    // F6: surface on the card, like the level path, instead of the generic
    // session error banner -- a card failure should read as a card failure.
    diagError.value = 'Could not start the quiz. Try again.'
  }
}

// The card's PATCH writes the level out-of-band of the conversation, so the
// transcript would otherwise end with the tutor's own unanswered offer -- which
// makes the model re-ask it next turn. Close the loop with a normal user
// message. Best-effort: the level is already saved deterministically, so a
// send failure is not surfaced on the card.
async function sendLevelDeclaration(level) {
  if (!canSend.value) return

  try {
    await store.sendMessageStreaming({ text: `I'd say my level is ${level}.` })
  } catch {
    /* level already persisted; DIAGNOSTIC flips OFF regardless */
  }
}

async function onDiagLevel(level) {
  // F5: a rapid second click before the first PATCH resolves must not fire a
  // second PATCH with the same (soon-to-be-stale) etag.
  if (diagLevelBusy.value) return
  // Same reuse-across-switches hazard as uploadGen (see comment above): this
  // component instance survives a session switch, so a PATCH started before
  // the switch must not write the new session's diagProfile/diagError when it
  // resolves late.
  const id = props.id
  const etag = diagProfile.value?.etag

  if (!etag) return
  diagLevelBusy.value = true
  diagError.value = ''

  try {
    const res = await patchProfile(id, { knowledge_level: level }, etag)

    if (id !== props.id) return // stale response from a previous session
    diagProfile.value = { profile: res.profile, etag: res.etag }
    await sendLevelDeclaration(level)
  } catch (e) {
    if (e?.status === 412) {
      // Concurrent write (e.g. a quiz just graded). Refetch; if the level is
      // now set the card hides itself via showDiagnosticCard. loadDiagProfile
      // has its own stale-response guard, so this is safe even if the
      // session has since switched.
      await loadDiagProfile(id)

      if (id !== props.id) return // stale response from a previous session

      if (diagProfile.value == null) {
        // The refetch itself failed (loadDiagProfile sets it to null on
        // error) -- distinct from "refetch succeeded, level still null".
        diagError.value = 'Could not save your level. Try again.'
      } else if (diagProfile.value.profile?.knowledge_level == null) {
        // Refetch shows the level is STILL unset: the 412 was a stale-etag
        // false alarm, not a real conflicting write. Retry once with the
        // fresh etag so the original click is not silently swallowed.
        const freshEtag = diagProfile.value.etag

        try {
          const retryRes = await patchProfile(id, { knowledge_level: level }, freshEtag)

          if (id !== props.id) return // stale response from a previous session
          diagProfile.value = { profile: retryRes.profile, etag: retryRes.etag }
          await sendLevelDeclaration(level)
        } catch {
          if (id !== props.id) return // stale response from a previous session
          diagError.value = 'Could not save your level. Try again.'
        }
      }
    } else {
      if (id !== props.id) return // stale response from a previous session
      diagError.value = 'Could not save your level. Try again.'
    }
  } finally {
    if (id === props.id) diagLevelBusy.value = false
  }
}

// End is triggered from the sidebar row context menu (S2) or the session action
// bar (ticket 10); both call useSessionActions.confirmEnd. When the store
// commits the End and the ended session matches this view's id, surface the
// closing summary modal here. Watching pendingSummary keeps the trigger
// location decoupled from the dialog owner.
watch(
  () => store.pendingSummary,
  (s) => {
    if (!s || s.sessionId !== props.id) return
    summaryKind.value = s.kind
    summaryText.value = s.text
    summaryDialog.value = true
    store.consumePendingSummary()
  },
  { immediate: true },
)

async function onAttachFile(file) {
  // Client-side pre-check for instant feedback; backend re-validates (type + 25 MB).
  const v = validateFile(file)

  if (!v.ok) {
    uploadStatus.value = { kind: 'failed', text: v.reason }

    return
  }

  uploading.value = true
  uploadStatus.value = { kind: 'pending', text: `Uploading ${file.name}...` }
  const gen = uploadGen

  try {
    const resp = await uploadDocument({ sessionId: props.id, file })

    if (gen !== uploadGen) return
    // The shared poller both drives the banner (so the new doc appears) and
    // resolves once this document reaches a terminal state, replacing the old
    // fixed-1s / 90-attempt pollUploadStatus loop.
    const outcome = await watchReference(resp.document_id, file.name)

    if (gen !== uploadGen) return
    applyUploadOutcome(outcome, file.name)
  } catch (e) {
    if (gen !== uploadGen) return
    // I-09: the 415 (and friends) carry an actionable server message -
    // prefer it over the generic friendlyError copy.
    const serverMsg = e?.body?.detail?.message
    uploadStatus.value = {
      kind: 'failed',
      text: `Upload failed: ${serverMsg || friendlyError(e)}`,
    }
  } finally {
    // The watcher already reset uploading for the new session; a stale finally
    // must not clobber a newer upload's uploading=true either.
    if (gen === uploadGen) uploading.value = false
  }
}

// Maps a useReferencePoll watch outcome onto the chip. Copy is unchanged from
// the old pollUploadStatus; only the attempt ceiling became a ~90s wall-clock
// ceiling (timedOut), because attempt counts mean nothing under backoff.
function applyUploadOutcome(outcome, filename) {
  // Session switched or the poller stopped: the id watcher already cleared the
  // chip, so writing anything here would paint a stale session's status.
  if (!outcome || outcome.cancelled) return

  if (outcome.status === 'ready') {
    uploadStatus.value = { kind: 'ready', text: `${filename} is ready. Ask a question about it.` }

    return
  }

  if (outcome.status === 'failed') {
    uploadStatus.value = {
      kind: 'failed',
      text: `Upload failed: ${outcome.error || 'ingestion error'}`,
    }

    return
  }

  if (outcome.unavailable) {
    uploadStatus.value = {
      kind: 'failed',
      text: `Upload status unavailable: ${friendlyError(outcome.error)}`,
    }

    return
  }

  // E-15: still pending at the wall-clock ceiling. The chip is a report on one
  // upload attempt and nothing clears it, so a "still processing" caption sat
  // there for the rest of the session on top of ReferenceStatusBanner, which
  // already owns steady-state ingestion status. Hand it over: clear the chip.
  uploadStatus.value = null
}

async function resume() {
  if (!store.currentSession) return
  resuming.value = true

  try {
    await store.reopenSession(store.currentSession.id)
  } catch {
    // store.error already populated
  } finally {
    resuming.value = false
  }
}

async function resumeReviewGaps() {
  if (!store.currentSession) return

  if (confirmedGaps.value.length > 1) {
    gapPickerOpen.value = true

    return
  }

  await sendReviewSeed(confirmedGaps.value[0])
}

async function sendReviewSeed(gap) {
  // Covers the query-driven path (handleReviewGapQuery), which is only
  // gated on !notFound in loadCurrent -- a non-404 loadSession failure
  // leaves store.currentSession null or stale relative to props.id. The
  // button path (resumeReviewGaps) already guards on !store.currentSession
  // before calling in, but this covers both null and stale defensively.
  if (!current.value) return
  resuming.value = true

  try {
    if (isEnded.value) await store.reopenSession(current.value.id)
    await store.sendMessageStreaming({
      text: `Review my gap: ${gap}`,
      reviewGaps: true,
      reviewGap: gap,
    })
  } catch {
    // store.error already populated
  } finally {
    resuming.value = false
  }
}

async function handleReviewGapQuery() {
  const gap = route.query.review_gap

  if (!gap) return
  router.replace({ query: { ...route.query, review_gap: undefined } })
  await sendReviewSeed(String(gap))
}

// Smart-start diagnostic quiz seed (?quiz=1, e.g. from the level-at-start
// picker's "Quiz me" chip). Mirrors handleReviewGapQuery/sendReviewSeed
// above. review_gap takes precedence when both params are present -- checked
// here (not after handleReviewGapQuery runs) because router.replace()'s
// query mutation is not guaranteed to be visible synchronously by the time
// handleReviewGapQuery's await resolves, so this guard must read
// route.query.review_gap before handleReviewGapQuery has a chance to strip
// it. Call sites therefore invoke handleQuizQuery() before
// handleReviewGapQuery().
async function handleQuizQuery() {
  if (!route.query.quiz) return
  // Read review_gap precedence before stripping quiz -- see comment above --
  // but always strip quiz regardless of the outcome. Otherwise a stale
  // ?quiz=1 that lost to review_gap on this render survives in the URL and
  // fires unprompted on a later remount/reload once review_gap is gone.
  const yieldToReviewGap = !!route.query.review_gap
  router.replace({ query: { ...route.query, quiz: undefined } })

  if (yieldToReviewGap) return

  if (!current.value) return

  try {
    await store.sendMessageStreaming({
      text: 'Quiz me so you can pitch this at the right level.',
      diagnosticAccepted: true,
    })
  } catch {
    // store.error already populated; consent card remains as fallback
  }
}

async function onAnswerCheck(index) {
  try {
    await store.answerCheck(index)
  } catch (e) {
    lastError.value = e
  }
}

async function onSkipCheck() {
  try {
    await store.skipCheck()
  } catch (e) {
    lastError.value = e
  }
}

// #340: same settle path as Done -- the stream-state watcher refetches the
// profile (a stopped diagnostic may just have set knowledge_level).
async function onStopCheck() {
  try {
    await store.stopCheck()
  } catch (e) {
    lastError.value = e
  }
}

async function onDoneCheck() {
  try {
    // A graded diagnostic sets knowledge_level server-side. completeCheck runs
    // the follow-up as a stream, and every way that stream can settle (done,
    // cap, error, abort, superseded) puts streamState back to 'idle', so the
    // stream-state watcher above already refetches the profile and the card
    // stays gone. No second fetch here.
    await store.completeCheck()
  } catch (e) {
    lastError.value = e
  }
}

function goHome() {
  summaryDialog.value = false
  router.push({ name: 'home' })
}
</script>

<style scoped>
/* #346: the document is the scroller. The body.session-page class (toggled on
   mount/unmount) only drives a flex-height cascade so the sheet is at least a
   viewport tall: a short transcript still puts the composer at the foot of the
   screen, a long one grows the page. The composer is pinned by the sticky
   .notes-foot, not by locking the page. */
:global(body.session-page .page) {
  display: flex;
  flex-direction: column;
}
/* The sheet owns its own edges: no page padding, no measure cap. width: 100%
   because the shared margin: 0 auto would shrink-wrap a flex item. */
:global(body.session-page .page-inner) {
  display: flex;
  flex: 1;
  flex-direction: column;
  width: 100%;
  padding: 0;
}

/* The desk: thread on the left, profile panel on the right, one header across.
   --panel-col is the panel's width; the collapsed value is the vertical tab
   strip (CueColumn renders it, usePanel owns the state). --sticky-top is where
   sticky chrome parks: under the shell's mobile top strip below 1280px (the
   useSidebar breakpoint), at the viewport edge above it. */
.session.is-sheet {
  --panel-col: 17rem;
  --sticky-top: 0px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) var(--panel-col);
  grid-template-rows: auto 1fr;
  flex: 1;
  width: 100%;
}

@media (max-width: 1279px) {
  .session.is-sheet {
    --sticky-top: var(--sidebar-mobile-strip-height, 3rem);
  }
}

.session.is-sheet.panel-collapsed {
  --panel-col: 2.75rem;
}

.sheet-header {
  grid-column: 1 / -1;
  grid-row: 1;
  min-width: 0;
}

.sheet-cue {
  grid-column: 2;
  grid-row: 2;
  display: flex;
  align-items: flex-start;
  min-width: 0;
}

/* The profile panel stays in view while the page scrolls under it. Capped at
   the lesser of its row and the visible viewport, so it fills a short page
   without growing it and its own .cue-body scroll keeps long profiles
   reachable on a tall one. Narrow widths pin the whole strip cell instead. */
@media (min-width: 900px) {
  .sheet-cue :deep(.cue) {
    position: sticky;
    top: var(--sticky-top);
    height: min(100%, calc(100dvh - var(--sticky-top)));
  }
}

.sheet-notes {
  grid-column: 1;
  grid-row: 2;
  display: grid;
  grid-template-rows: 1fr auto;
  min-width: 0;
}

.messages {
  /* The cards are laid on the desk: no ruled ground, the ground is what the
     turns sit on. The 1fr row stretches it so the foot sits at the bottom of
     the viewport on a short transcript. */
  /* position: relative makes the transcript the containing block for
     everything inside it. Without it an absolutely positioned descendant with
     no offsets (the check card's sr-only live region) resolves against the page
     and is laid out at its static position, adding phantom height to the
     document (1132px on a 844px viewport, 2026-09-16). */
  position: relative;
  background: var(--desk);
  padding: 1rem clamp(1rem, 3vw, 2rem);
}

/* Cards opened in the transcript keep the spacing of the turns above them. */
.transcript-card {
  margin-top: 0.75rem;
}

/* The measure: a 72ch text column plus the card's own padding, centered in the
   notes column. The foot uses the same rule so the composer card stays under
   the thread. */
.notes-measure {
  width: 100%;
  max-width: calc(72ch + 2rem);
  margin: 0 auto;
}

/* No top rule: the composer is a card on the desk, not a footer band. Sticky
   pins it to the bottom of the viewport while the page scrolls; the desk
   ground keeps the transcript from showing through behind it. */
.notes-foot {
  position: sticky;
  bottom: 0;
  z-index: 1;
  padding: 0 clamp(1rem, 3vw, 2rem) 1rem;
  min-width: 0;
  background: var(--desk);
}

.notes-foot .notes-measure {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-top: 0.75rem;
}

/* The slot is a grouping wrapper only: its children join the foot's own
   column so an empty slot costs no vertical space. */
.status-slot {
  display: contents;
}

.load-earlier {
  display: block;
  width: 100%;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--rule-strong);
  padding: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  /* 27px + the 1px rule = one pitch, so the turns below still sit on the rules. */
  line-height: calc(var(--line-pitch) - 1px);
  color: var(--ink-learner);
  cursor: pointer;
  text-align: left;
}

.load-earlier:hover:not(:disabled) {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.load-earlier:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.load-earlier:disabled {
  cursor: default;
  color: var(--pencil);
}

/* Status captions: small cards with a head rule, tab colour on top only. */
.status-line {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.75rem;
  margin: 0;
  padding: 0.25rem 0.75rem;
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-top: 3px solid var(--color-accent);
  border-radius: 0 0 var(--radius-card) var(--radius-card);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--ink);
  animation: status-land var(--motion-ink) cubic-bezier(0.16, 1, 0.3, 1) both;
}

.status-line.is-alert {
  border-top-color: var(--tab-focus);
}

@keyframes status-land {
  from {
    clip-path: inset(0 100% 0 0);
  }
  to {
    clip-path: inset(0);
  }
}

.error-message {
  margin: 0;
  flex: 1 1 auto;
  min-width: 0;
}

.error-retry {
  flex: 0 0 auto;
  background: transparent;
  color: var(--ink-learner);
  border: 0;
  padding: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.error-retry:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.followup-notice {
  color: var(--pencil);
}

/* End-session summary dialog */
.summary {
  white-space: pre-wrap;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink);
  padding: 0.5rem 0;
}

/* Not-found */
.not-found {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: var(--line-pitch) clamp(1rem, 4vw, 2.5rem);
  max-width: 40rem;
}

.folio {
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--line-pitch);
  color: var(--pencil);
}

.topic {
  font-family: var(--font-display);
  font-size: var(--fs-display);
  font-weight: 600;
  letter-spacing: var(--tracking-display);
  line-height: var(--lh-display);
  color: var(--ink);
  margin: 0;
  overflow-wrap: anywhere;
}

.not-found-sub {
  margin: 0;
  line-height: var(--line-pitch);
  color: var(--pencil);
}

.not-found code {
  font-family: var(--font-mono);
  font-size: 0.875em;
  padding: 0.125rem 0.4rem;
  background: var(--color-surface-soft);
  border: 1px solid var(--rule-strong);
  border-radius: var(--radius-sm);
}

.home-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.75rem;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  color: var(--ink-learner);
  text-decoration: none;
}

.home-link:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.home-link:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

/* Under 900px the profile panel becomes a strip under the header: one column,
   so --panel-col is unused at this width. */
@media (max-width: 899px) {
  .session.is-sheet {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto auto 1fr;
    /* clip, never hidden: hidden would make the grid a scroll container and
       change what the sticky strip and foot stick to. clip swallows the
       sheet's dim overlay (which runs a viewport's worth past the strip) so
       opening the profile never grows the page. */
    overflow: clip;
  }

  /* The strip stays put while the page scrolls under it, so the disclosure
     control is always reachable. Sticky lives on this grid cell, not on the
     strip inside CueColumn: the cell's containing block is the whole sheet,
     the strip's would only be the strip-tall panel. The expanded profile is
     bounded by .cue-body's own 40vh cap in CueColumn. */
  .sheet-cue {
    grid-column: 1;
    grid-row: 2;
    display: block;
    position: sticky;
    top: var(--sticky-top);
    z-index: 2;
  }

  .sheet-notes {
    grid-column: 1;
    grid-row: 3;
  }
}

@media (prefers-reduced-motion: reduce) {
  .status-line {
    animation: none;
  }
}
</style>
