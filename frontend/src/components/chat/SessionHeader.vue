<script setup>
import { computed, nextTick, ref, watch } from 'vue'

import { useSessionActions } from '@/composables/useSessionActions.js'
import { formatRelative } from '../../utils/formatDate.js'
import { LEVEL_MARK_PATH, levelStroke } from './levelMark.js'

// Ticket 10: the session action bar. The head keeps its topic link, level and
// started line, and gains the session's own actions -- the same shared
// implementation the sidebar row calls (useSessionActions), so the two
// surfaces can never drift apart.
const props = defineProps({
  // { id, topic, created_at, pinned, ended_at } -- null while nothing is known.
  session: { type: Object, default: null },
  level: { type: String, default: '' },
  // Reference-file aggregate: null (no documents) | 'processing' | 'ready' | 'failed'
  refStatus: {
    type: String,
    default: null,
    validator: (v) => v === null || ['processing', 'ready', 'failed'].includes(v),
  },
  // True whenever the tutor stream is not idle. End must not stay enabled
  // while a reply is mid-stream -- store.endSession never aborts the stream,
  // and ending mid-stream would unmount the composer's own Stop button.
  streaming: { type: Boolean, default: false },
})

const actions = useSessionActions()

const { busy } = actions

const topic = computed(() => props.session?.topic || '')

const sessionId = computed(() => props.session?.id || '')

const startedAt = computed(() => props.session?.created_at || '')

const isEnded = computed(() => Boolean(props.session?.ended_at))

const isPinned = computed(() => Boolean(props.session?.pinned))

const started = computed(() =>
  startedAt.value ? `started ${formatRelative(startedAt.value)}` : '',
)

const levelText = computed(() => props.level || 'level not set')

const stroke = computed(() => levelStroke(props.level))

const pinLabel = computed(() => (isPinned.value ? 'Unpin session' : 'Pin session'))

const pinTitle = computed(() => (isPinned.value ? 'Unpin' : 'Pin'))

const refLabel = computed(() => (props.refStatus ? `Reference files: ${props.refStatus}` : ''))

// Rename: mirrors SidebarSessionRow -- Enter commits, Escape cancels, blur
// commits; focus returns to the Rename button afterwards.
const renaming = ref(false)

const draft = ref('')

const inputEl = ref(null)

const renameBtn = ref(null)

const endBtn = ref(null)

const resumeBtn = ref(null)

async function startRename() {
  draft.value = topic.value
  renaming.value = true
  await nextTick()
  inputEl.value?.focus()
  inputEl.value?.select()
}

async function refocusRename() {
  await nextTick()
  renameBtn.value?.focus()
}

function cancelRename() {
  draft.value = topic.value
  renaming.value = false
  refocusRename()
}

async function commitRename() {
  if (!renaming.value) return
  const next = draft.value.trim()
  renaming.value = false
  await actions.rename(props.session, next)
}

function commitRenameFromKey() {
  commitRename()
  refocusRename()
}

function togglePin() {
  actions.setPinned(props.session, !isPinned.value)
}

function endSession() {
  actions.confirmEnd(props.session)
}

function resumeSession() {
  actions.resume(props.session)
}

// Switching sessions (sidebar click, same route component instance) must not
// carry an in-progress rename from the previous session's topic into the new
// one -- the draft was seeded from the old topic and the input would commit
// it onto whichever session loads next.
watch(
  () => props.session?.id,
  () => {
    renaming.value = false
    draft.value = ''
  },
)

// End and Resume are v-if/v-else: whichever one is clicked unmounts itself
// once ended_at flips, dropping focus to <body>. Only follow the swap when
// the button being removed actually had focus -- ended_at can also flip from
// elsewhere (E-11's "ended elsewhere" mid-send, the foot SessionEndedBanner's
// own Resume, a fresh load landing on an already-ended session, a sidebar
// switch onto one), and none of those should yank focus into the header.
// Default watch flush ('pre') runs before the DOM update, so the outgoing
// button is still mounted when this reads document.activeElement.
watch(isEnded, async (ended) => {
  const leaving = ended ? endBtn.value : resumeBtn.value

  if (!leaving || document.activeElement !== leaving) return
  await nextTick()

  const target = ended ? resumeBtn.value : endBtn.value

  ;(target || renameBtn.value)?.focus()
})
</script>

<template>
  <header v-if="topic" class="session-header" data-testid="session-header">
    <div class="session-title-line">
      <h1 class="session-topic-wrap">
        <input
          v-if="renaming"
          ref="inputEl"
          v-model="draft"
          type="text"
          class="session-topic session-rename-input"
          aria-label="Rename session"
          data-testid="session-rename-input"
          @keydown.enter.prevent="commitRenameFromKey"
          @keydown.esc.prevent="cancelRename"
          @blur="commitRename"
        />
        <RouterLink
          v-else-if="sessionId"
          :to="`/session/${sessionId}/profile`"
          class="session-topic session-topic-link"
          :title="`${topic} — open session profile`"
          data-testid="session-topic-link"
        >
          {{ topic }}
        </RouterLink>
        <span v-else class="session-topic" :title="topic">{{ topic }}</span>
      </h1>
      <p class="session-meta">
        <span class="session-level">
          <svg
            class="session-level-mark"
            viewBox="0 0 24 24"
            width="28"
            height="18"
            aria-hidden="true"
            focusable="false"
          >
            <path :d="LEVEL_MARK_PATH" :stroke-width="stroke" />
          </svg>
          {{ levelText }}
        </span>
        <span v-if="started" class="session-meta-sep" aria-hidden="true">&middot;</span>
        <span v-if="started" class="session-started">{{ started }}</span>
      </p>
    </div>

    <div class="session-actions" data-testid="session-actions">
      <span
        v-if="refStatus"
        class="session-ref-status"
        :class="`is-${refStatus}`"
        :title="refLabel"
        data-testid="session-ref-status"
      >
        <span class="session-ref-dot" aria-hidden="true" />
        <span class="sr-only">{{ refLabel }}</span>
      </span>

      <button
        ref="renameBtn"
        type="button"
        class="session-action hit-44"
        aria-label="Rename session"
        title="Rename"
        data-testid="session-action-rename"
        @click="startRename"
      >
        <svg
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
          <path d="M13.5 3.5 L16.5 6.5 L7 16 L3.5 16.5 L4 13 Z" />
          <path d="M11.5 5.5 L14.5 8.5" />
        </svg>
      </button>

      <button
        type="button"
        class="session-action hit-44"
        :class="{ 'is-on': isPinned }"
        :aria-label="pinLabel"
        :title="pinTitle"
        data-testid="session-action-pin"
        @click="togglePin"
      >
        <svg
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
          <path d="M7.5 3 H12.5 M8.5 3 V8 L5.5 11.5 H14.5 L11.5 8 V3" />
          <path d="M10 11.5 V17" />
        </svg>
      </button>

      <button
        v-if="!isEnded"
        ref="endBtn"
        type="button"
        class="session-action hit-44"
        aria-label="End session"
        title="End session"
        data-testid="session-action-end"
        :disabled="busy || streaming"
        @click="endSession"
      >
        <svg
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
          <circle cx="10" cy="10" r="7.5" />
          <rect x="7.25" y="7.25" width="5.5" height="5.5" rx="0.5" />
        </svg>
      </button>

      <button
        v-else
        ref="resumeBtn"
        type="button"
        class="session-action hit-44"
        aria-label="Resume session"
        title="Resume session"
        data-testid="session-action-resume"
        :disabled="busy"
        @click="resumeSession"
      >
        <svg
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
          <circle cx="10" cy="10" r="7.5" />
          <path d="M8.25 6.75 L13.25 10 L8.25 13.25 Z" />
        </svg>
      </button>
    </div>
  </header>
</template>

<style scoped>
/* The action bar: one 56px row on the desk, a hairline card-edge rule below.
   It heads the page and scrolls away with it (#346); only the composer and
   the profile stay pinned. */
.session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  height: 56px;
  min-height: 56px;
  padding: 0 clamp(1rem, 3vw, 1.5rem);
  background: var(--desk);
  border-bottom: 1px solid var(--card-edge);
  box-sizing: border-box;
}

/* Topic, then the pencil caption, on one baseline. */
.session-title-line {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  flex: 1 1 auto;
  min-width: 0;
}

.session-topic-wrap {
  margin: 0;
  min-width: 0;
  flex: 0 1 auto;
}

.session-topic {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 600;
  letter-spacing: var(--tracking-display);
  line-height: var(--lh-display);
  color: var(--ink);
  display: inline-block;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  vertical-align: bottom;
}

.session-topic-link {
  text-decoration: underline;
  text-underline-offset: 0.15em;
  text-decoration-color: var(--pencil);
  cursor: pointer;
}

.session-topic-link:hover {
  text-decoration: underline;
  text-decoration-color: var(--ink-marker);
  text-decoration-thickness: 2px;
  text-underline-offset: 4px;
}

.session-topic-link:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 3px;
}

/* Renaming writes on the same rule the topic sits on (as the sidebar row). */
.session-rename-input {
  width: 20rem;
  max-width: 100%;
  border: 0;
  border-bottom: 1px solid var(--ink-learner);
  border-radius: 0;
  background: transparent;
  padding: 0;
}

.session-rename-input:focus-visible {
  outline: none;
  border-bottom-width: 2px;
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 0;
  flex: 0 0 auto;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--line-pitch);
  color: var(--pencil);
  white-space: nowrap;
}

/* One caption line: the level stroke and its word, a pencil middot, then the
   start date. The middot only exists when there is a date to separate from. */
.session-meta-sep {
  flex: 0 0 auto;
  color: var(--pencil);
}

.session-level {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

/* The header meta line is pencil throughout: date and level are notes to the
   side of the page, not part of its ink. */
.session-level-mark {
  fill: none;
  stroke: var(--pencil);
  stroke-linecap: round;
}

.session-actions {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex: 0 0 auto;
}

/* hit-44 grows each button's hit area by 8px on every side via ::after --
   at the 0.25rem (4px) resting gap that is enough overlap for adjacent
   buttons' hit areas to touch. Widen the gap on coarse pointers only so
   neighbouring hit areas never overlap. */
@media (pointer: coarse) {
  .session-actions {
    gap: 0.5rem;
  }
}

/* 28px drawn icon buttons: pencil at rest, ink on hover, no fill. */
.session-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: none;
  color: var(--pencil);
  cursor: pointer;
}

.session-action:hover:not(:disabled) {
  color: var(--ink);
}

.session-action.is-on {
  color: var(--ink);
}

.session-action:disabled {
  cursor: default;
  opacity: 0.5;
}

.session-action:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

/* Reference-file status: an 8px dot, its state in the tooltip and in hidden
   text for screen readers. */
.session-ref-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
}

.session-ref-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--pencil);
}

.session-ref-status.is-ready .session-ref-dot {
  background: var(--tab-mastered);
}

.session-ref-status.is-failed .session-ref-dot {
  background: var(--ink-marker-text);
}

/* Under 900px the bar keeps its 56px single row: the topic ellipsises so the
   level, the started date and the actions still fit. */
@media (max-width: 899px) {
  .session-header {
    gap: 0.5rem;
  }

  .session-title-line {
    gap: 0.75rem;
  }
}

/* Story 48: "started" stays visible at every width. Below 600px there is no
   longer room for it on the topic's baseline, so the caption line moves under
   the topic instead of being dropped. The bar keeps its 56px height -- the
   stacked topic (~23px) plus caption (~18px) still fits inside it. */
@media (max-width: 599px) {
  .session-title-line {
    flex-direction: column;
    align-items: flex-start;
    gap: 0;
  }

  .session-meta {
    line-height: 1.25;
    gap: 0.5rem;
  }
}
</style>
