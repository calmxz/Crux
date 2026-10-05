<template>
  <section class="sprof profile-page" data-testid="session-profile">
    <BackButton label="Back to session" :fallback="`/session/${id}`" />

    <header class="head">
      <div class="head-text">
        <h1 class="title">{{ topicLabel }}</h1>
        <p v-if="data?.profile?.knowledge_level" class="lede">
          Working at the <span class="level-word">{{ data.profile.knowledge_level }}</span> level.
        </p>
      </div>

      <div v-if="data" class="header-actions">
        <button
          v-if="data.profile.confirmed_gaps?.length"
          type="button"
          class="text-btn"
          data-testid="sprof-review-gaps"
          @click="startReview"
        >
          Review gaps
        </button>
      </div>
    </header>

    <GapPickerDialog v-model:visible="gapPickerOpen" :gaps="gapNames" @select="goReview" />

    <div v-if="loading" class="skel" data-testid="sprof-loading" aria-hidden="true">
      <span class="skel-block" />
      <span class="skel-block" />
      <span class="skel-block skel-short" />
    </div>
    <span v-if="loading" class="sr-only" role="status">Loading</span>
    <p v-else-if="error" class="error" data-testid="sprof-error">{{ error }}</p>

    <template v-else-if="data">
      <p v-if="conflict" class="conflict" data-testid="sprof-conflict" role="status">
        Profile changed elsewhere, so your change wasn't saved. Reloaded with the latest.
      </p>
      <p v-if="writeError" class="error" data-testid="sprof-write-error" role="alert">
        {{ writeError }}
      </p>

      <section class="divider divider--level" data-testid="sprof-level">
        <h2 class="divider-tab divider-tab--level">Level</h2>
        <div class="divider-body">
          <div class="level-edit" data-testid="level-select">
            <button
              v-for="lvl in LEVELS"
              :key="lvl"
              type="button"
              class="level-opt"
              :class="{ active: data.profile.knowledge_level === lvl }"
              :disabled="writing"
              @click="setLevel(lvl)"
            >
              <svg
                class="level-mark"
                viewBox="0 0 24 24"
                width="18"
                height="12"
                aria-hidden="true"
                focusable="false"
              >
                <path :d="LEVEL_MARK_PATH" :stroke-width="levelStroke(lvl)" />
              </svg>
              {{ lvl }}
            </button>
          </div>
        </div>
      </section>

      <section
        v-if="data.profile.focus_target_gap"
        class="divider divider--focus"
        data-testid="sprof-focus"
      >
        <h2 class="divider-tab divider-tab--focus">Focus</h2>
        <div class="divider-body">
          <p class="cue-entry cue-entry--focus">
            <svg
              class="cue-mark cue-mark--focus"
              viewBox="0 0 12 12"
              width="12"
              height="12"
              aria-hidden="true"
              focusable="false"
            >
              <path d="M1 6 L11 6" />
            </svg>
            <span class="cue-word">{{ data.profile.focus_target_gap }}</span>
          </p>
        </div>
      </section>

      <section v-if="subtopicEntries.length" class="sec" data-testid="sprof-subtopics">
        <h2 class="sec-title">Subtopic levels</h2>
        <ul class="subtopic-list">
          <li v-for="[name, lvl] in subtopicEntries" :key="`st-${name}`" class="subtopic-row">
            <span class="st-name">{{ name }}</span>
            <div class="level-edit">
              <button
                v-for="l in LEVELS"
                :key="l"
                type="button"
                class="level-opt"
                :class="{ active: lvl === l }"
                :disabled="writing"
                @click="setSubtopicLevel(name, l)"
              >
                <svg
                  class="level-mark"
                  viewBox="0 0 24 24"
                  width="18"
                  height="12"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path :d="LEVEL_MARK_PATH" :stroke-width="levelStroke(l)" />
                </svg>
                {{ l }}
              </button>
            </div>
            <button
              type="button"
              class="icon-btn hit-44"
              data-testid="subtopic-remove"
              :aria-label="`Remove ${name}`"
              :disabled="writing"
              @click="removeSubtopic(name)"
            >
              <svg
                class="icon-mark"
                viewBox="0 0 16 16"
                width="16"
                height="16"
                aria-hidden="true"
                focusable="false"
              >
                <path d="M4 4 L12 12 M12 4 L4 12" />
              </svg>
            </button>
          </li>
        </ul>
      </section>

      <section
        v-for="sec in CUE_SECTIONS"
        :key="sec.key"
        :class="sec.sectionClass"
        :data-testid="sec.testid"
      >
        <h2 :class="sec.tabClass">{{ sec.label }}</h2>
        <div class="divider-body">
          <p v-if="!data.profile[sec.key]?.length" class="cue-none">{{ sec.empty }}</p>
          <ul v-else class="cue-list">
            <li
              v-for="it in data.profile[sec.key]"
              :key="`${sec.keyPrefix}-${it.name}`"
              class="chip"
            >
              <svg
                :class="sec.markClass"
                viewBox="0 0 12 12"
                width="12"
                height="12"
                aria-hidden="true"
                focusable="false"
              >
                <path v-if="sec.markPath" :d="sec.markPath" />
                <circle v-else cx="6" cy="6" r="4" />
              </svg>
              <span class="cue-word">{{ it.name }}</span>
              <span v-if="it.evidence_type" class="chip-badge" data-testid="evidence-badge">
                {{ it.evidence_type }}
              </span>
              <button
                type="button"
                class="icon-btn hit-44"
                data-testid="chip-remove"
                :aria-label="`Remove ${it.name}`"
                :disabled="writing"
                @click="removeItem(sec.key, it.name)"
              >
                <svg
                  class="icon-mark"
                  viewBox="0 0 16 16"
                  width="16"
                  height="16"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path d="M4 4 L12 12 M12 4 L4 12" />
                </svg>
              </button>
            </li>
          </ul>
          <div class="add-row">
            <input
              v-model="drafts[sec.key]"
              :data-testid="sec.inputTestid"
              class="add-input"
              :placeholder="sec.placeholder"
              :aria-label="sec.inputLabel"
              maxlength="200"
              @keydown.enter="addItem(sec)"
            />
            <button
              type="button"
              :data-testid="sec.submitTestid"
              class="text-btn"
              :aria-label="sec.submitLabel"
              :disabled="writing"
              @click="addItem(sec)"
            >
              Add
            </button>
          </div>
        </div>
      </section>

      <section v-if="data.profile.last_session_summary" class="sec" data-testid="sprof-summary">
        <h2 class="sec-title">Session summary</h2>
        <p class="summary-text">{{ stripAutoPrefix(data.profile.last_session_summary) }}</p>
      </section>

      <section class="sec" data-testid="sprof-events">
        <h2 class="sec-title">Recent check-questions</h2>
        <p v-if="!data.recent_learning_events.length" class="cue-none">
          No learning events logged yet.
        </p>
        <ol v-else class="event-list">
          <li
            v-for="ev in data.recent_learning_events"
            :key="ev.id"
            :class="['event-row', ev.correct ? 'evt-ok' : 'evt-bad']"
          >
            <span class="event-mark">
              <!-- D-07: the mark is a <span>, which takes no accessible name
                   from aria-label; the word is written out for SRs instead. -->
              <span class="sr-only">{{ ev.correct ? 'correct' : 'missed' }}</span>
              <svg
                class="event-mark-draw"
                viewBox="0 0 16 16"
                width="16"
                height="16"
                aria-hidden="true"
                focusable="false"
              >
                <path v-if="ev.correct" d="M3 8.5 L6.5 12 L13 4" />
                <path v-else d="M4 4 L12 12 M12 4 L4 12" />
              </svg>
            </span>
            <span class="event-body">
              <span class="event-gap">{{ ev.gap_tested }}</span>
              <span class="event-q">{{ ev.question }}</span>
              <span class="event-when">{{ formatRelative(ev.created_at) }}</span>
            </span>
          </li>
        </ol>
      </section>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'

import BackButton from '../components/BackButton.vue'
import GapPickerDialog from '../components/GapPickerDialog.vue'
import { friendlyError } from '../lib/errors.js'
import { deleteProfileItem, getSessionProfile, patchProfile } from '../services/profileApi.js'
import { useSessionStore } from '../stores/session.js'
import { formatRelative } from '../utils/formatDate.js'
import { stripAutoPrefix } from '../utils/sessionCard.js'
import { LEVEL_MARK_PATH, TICK_PATH, levelStroke } from '../components/chat/levelMark.js'
import '@/assets/profile.css'

const props = defineProps({ id: { type: String, required: true } })

const LEVELS = ['beginner', 'intermediate', 'advanced']

// The two cue cards are identical apart from these values; the template renders
// one body for both. `key` doubles as the profile list name and the draft key.
const CUE_SECTIONS = [
  {
    key: 'confirmed_gaps',
    label: 'Gaps',
    sectionClass: 'divider divider--gaps',
    tabClass: 'divider-tab divider-tab--gaps',
    testid: 'sprof-gaps',
    keyPrefix: 'g',
    empty: 'None.',
    markClass: 'cue-mark cue-mark--gap',
    markPath: '',
    patchKey: 'add_gap',
    inputTestid: 'add-gap',
    placeholder: 'Add a gap',
    inputLabel: 'Add a gap',
    submitTestid: 'add-gap-submit',
    submitLabel: 'Add gap',
  },
  {
    key: 'mastered_concepts',
    label: 'Mastered',
    sectionClass: 'divider divider--mastered',
    tabClass: 'divider-tab divider-tab--mastered',
    testid: 'sprof-mastered',
    keyPrefix: 'm',
    empty: 'Nothing recorded yet.',
    markClass: 'cue-mark cue-mark--tick',
    markPath: TICK_PATH,
    patchKey: 'add_mastered',
    inputTestid: 'add-mastered',
    placeholder: 'Add a concept',
    inputLabel: 'Add a mastered concept',
    submitTestid: 'add-mastered-submit',
    submitLabel: 'Add concept',
  },
]

const router = useRouter()

const confirm = useConfirm()

const store = useSessionStore()

const data = ref(null)

const loading = ref(false)

const error = ref('')

const conflict = ref(false)

// F-05: write failures get their own ref. Reusing the load-path `error`
// would swap the whole loaded profile for an error paragraph (the template
// chain is loading -> error -> data) with no control left to retry.
const writeError = ref('')

// E-08: true while any profile write is in flight. Every mutating control is
// disabled for the duration, so a second write can never be issued against the
// etag the first one is about to replace.
const writing = ref(false)

const drafts = reactive({ confirmed_gaps: '', mastered_concepts: '' })

const gapPickerOpen = ref(false)

const topicLabel = computed(() => {
  const fromStore = store.sessions.find((s) => s.id === props.id)?.topic

  return fromStore || store.currentSession?.topic || 'Session profile'
})

const gapNames = computed(() => (data.value?.profile?.confirmed_gaps ?? []).map((g) => g.name))

const subtopicEntries = computed(() => Object.entries(data.value?.profile?.subtopic_levels ?? {}))

// E-18: the route component is reused across session->session navigation
// (same idiom as SessionView.vue), so a slow earlier load must not overwrite
// a newer one once it finally resolves. `loadSeq` marks each call; only the
// most recent one is allowed to write state.
let loadSeq = 0

let loadedId = null

async function load() {
  const seq = ++loadSeq
  // Stale-sibling-state fix: the route component is reused across
  // session->session navigation (E-18), so these must not survive into the
  // newly-loaded session -- a write-error banner, an open-conflict notice, an
  // unsaved add-item draft, or an open gap picker all belong to the session
  // being left. Drafts and the picker are reset only when the id actually
  // changed: load() is also the 412 recovery path, and a half-typed draft
  // must survive a conflict reload.
  conflict.value = false
  writeError.value = ''

  if (loadedId !== props.id) {
    drafts.confirmed_gaps = ''
    drafts.mastered_concepts = ''
    gapPickerOpen.value = false
  }

  loadedId = props.id
  loading.value = true
  error.value = ''

  try {
    const res = await getSessionProfile(props.id)

    if (seq !== loadSeq) return
    data.value = res
  } catch (e) {
    if (seq !== loadSeq) return
    error.value = friendlyError(e)
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

// E-08: every mutating call goes through one serial queue. Writes are
// etag-guarded, so two in flight at once means the second carries a stale etag
// and loses to a 412. `fn` reads data.value.etag when it runs -- not when it is
// queued -- so each write sees the etag the previous one produced.
// Re-entrancy is handled by serialising rather than by dropping: the mutating
// controls are disabled for the duration, and anything that still gets through
// (an Enter on the still-enabled text field) runs after the write ahead of it
// instead of racing it. A queued write is dropped only when the page it was
// aimed at is gone (#459, below).
let _writeQueue = Promise.resolve()

let _pendingWrites = 0

// #459: queued writes die with the page they were aimed at. Each write
// captures both generations when it is queued and checks them when it runs.
// `_conflictGen` is bumped once a 412 recovery reload has finished, so every
// write queued before the notice became visible (including one queued during
// the reload) is dropped instead of clearing the notice. `_sessionGen` is
// bumped on an id change, so nothing queued on session A is sent to B.
let _conflictGen = 0

let _sessionGen = 0

// Resolves to 'saved' | 'conflict' | 'failed' | 'dropped' | 'stale'.
function _applyWrite(fn) {
  const ticket = { conflictGen: _conflictGen, sessionGen: _sessionGen }
  _pendingWrites += 1
  writing.value = true
  const run = _writeQueue.then(() => _doWrite(fn, ticket))
  _writeQueue = run.catch(() => {})

  return run
}

async function _doWrite(fn, ticket) {
  // A write queued on session A must not paint its result, its error, or its
  // conflict notice onto session B, nor touch B's `writing` state.
  const isStale = () => ticket.sessionGen !== _sessionGen

  try {
    if (isStale()) return 'stale'

    if (ticket.conflictGen !== _conflictGen) return 'dropped'
    conflict.value = false
    writeError.value = ''
    const res = await fn()

    if (isStale()) return 'stale'
    // One source of truth for the etag: keeping a separate ref alongside
    // data.etag let the spread re-seed the stale value on the next write.
    data.value = { ...data.value, profile: res.profile, etag: res.etag }

    return 'saved'
  } catch (e) {
    if (isStale()) return 'stale'

    if (e?.status !== 412) {
      writeError.value = friendlyError(e)

      return 'failed'
    }

    // load() resets conflict at its top (stale-sibling-state fix), so the
    // flag must be set after the recovery reload finishes, not before --
    // otherwise load() would immediately wipe the notice it is meant to
    // introduce.
    await load()

    if (isStale()) return 'stale'
    _conflictGen += 1
    conflict.value = true

    return 'conflict'
  } finally {
    // A stale write's count was already zeroed by _dropQueuedWrites.
    if (!isStale()) {
      _pendingWrites -= 1

      if (_pendingWrites === 0) writing.value = false
    }
  }
}

// Session change: _doWrite skips the `_pendingWrites` decrement for stale
// writes, so the counter is reset here instead.
function _dropQueuedWrites() {
  _sessionGen += 1
  _writeQueue = Promise.resolve()
  _pendingWrites = 0
  writing.value = false
}

async function addItem(sec) {
  const v = drafts[sec.key].trim()

  if (!v) return
  drafts[sec.key] = ''

  const outcome = await _applyWrite(() =>
    patchProfile(props.id, { [sec.patchKey]: v }, data.value.etag),
  )

  // #459: a failed add puts its text back unless the learner has typed since.
  // A stale write never restores: drafts now belong to another session.
  const lost = outcome === 'conflict' || outcome === 'failed' || outcome === 'dropped'

  if (lost && drafts[sec.key] === '') drafts[sec.key] = v
}

function setLevel(level) {
  return _applyWrite(() => patchProfile(props.id, { knowledge_level: level }, data.value.etag))
}

// E-08: removing a concept is destructive and unlabelled by anything else on
// the page, so it asks first. Same dialog contract as the file-delete confirm.
function confirmRemove(name, accept) {
  confirm.require({
    message: `Remove "${name}" from this profile?`,
    header: 'Remove concept',
    // No glyph icon font in this world -- the dialog carries no mark.
    rejectLabel: 'Cancel',
    acceptLabel: 'Remove',
    rejectClass: 'p-button-text p-button-secondary',
    acceptClass: 'p-button-danger confirm-delete-strong',
    accept,
  })
}

function removeItem(listName, item) {
  confirmRemove(item, () =>
    _applyWrite(() => deleteProfileItem(props.id, listName, item, data.value.etag)),
  )
}

function setSubtopicLevel(name, level) {
  return _applyWrite(() =>
    patchProfile(props.id, { subtopic: name, subtopic_level: level }, data.value.etag),
  )
}

function removeSubtopic(name) {
  confirmRemove(name, () =>
    _applyWrite(() => deleteProfileItem(props.id, 'subtopic_levels', name, data.value.etag)),
  )
}

function startReview() {
  if (gapNames.value.length > 1) gapPickerOpen.value = true
  else if (gapNames.value.length === 1) goReview(gapNames.value[0])
}

function goReview(gap) {
  router.push({ name: 'session', params: { id: props.id }, query: { review_gap: gap } })
}

onMounted(load)

watch(
  () => props.id,
  () => {
    _dropQueuedWrites()
    load()
  },
)
</script>

<style scoped>
/* The session profile is a stack of full-width cards: what the tutor knows
   about this session, editable in place. The four coloured dividers (Level,
   Focus, Gaps, Mastered) carry the profile's law-bound colours; the rest
   are plain white cards on the desk. The dividers, cue marks, .sec/.sec-title,
   .cue-none, .text-btn and the skeleton rule come from assets/profile.css
   (shared with AggregateProfileView); only what differs is here. */
.sprof {
  max-width: 72rem;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.5rem;
  flex-wrap: wrap;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--rule-strong);
}

.head-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.title {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--fs-h1);
  font-weight: 600;
  letter-spacing: var(--tracking-display);
  line-height: var(--lh-display);
  color: var(--ink);
  overflow-wrap: anywhere;
}

.lede {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--pencil);
}

.level-word {
  color: var(--ink);
}

.header-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.25rem;
}

.sec {
  align-items: flex-start;
}

.chip,
.cue-entry {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin: 0;
}

.cue-word {
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink-learner);
  overflow-wrap: anywhere;
}

/* The focus cue stays in ink and is marked in red; the word is never set in
   red. */
.cue-entry--focus .cue-word {
  color: var(--ink);
  text-decoration: underline;
  text-decoration-color: var(--ink-marker);
  text-decoration-thickness: 2px;
  text-underline-offset: 4px;
}

.cue-mark {
  align-self: flex-start;
  margin-top: 0.35rem;
}

.chip-badge {
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--lh-body);
  color: var(--pencil);
}

/* Controls: blue text (.text-btn, from assets/profile.css), or a drawn stroke
   in an icon button. Nothing stamped. */
.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  align-self: flex-start;
  width: 1.5rem;
  height: 1.75rem;
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--ink-learner);
  cursor: pointer;
}

.icon-btn:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

/* Disabled while a write is in flight: the control drops to pencil and stops
   inviting a second click. */
.text-btn:disabled,
.icon-btn:disabled,
.level-opt:disabled {
  color: var(--pencil);
  cursor: default;
}

.text-btn:disabled {
  text-decoration: none;
}

.level-opt:disabled:hover {
  text-decoration: none;
}

.icon-mark {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
}

/* The level control: one word per step, the step drawn beside it. The level in
   force is graphite; the rest are written in blue. */
.level-edit {
  display: inline-flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.level-opt {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  cursor: pointer;
}

.level-opt:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.level-opt.active {
  color: var(--ink);
  font-weight: 700;
}

.level-opt:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.level-mark {
  flex: 0 0 auto;
  fill: none;
  stroke: var(--pencil);
  stroke-linecap: round;
}

.level-opt.active .level-mark {
  stroke: var(--ink);
}

.subtopic-list {
  list-style: none;
  padding: 0;
  margin: 0;
  width: 100%;
}

.subtopic-row {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  box-shadow: inset 0 -1px 0 var(--rule);
}

.st-name {
  flex: 1;
  min-width: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink);
  overflow-wrap: anywhere;
}

/* A field on a rule, with the action written in blue beside it. */
.add-row {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  width: 100%;
  max-width: 24rem;
}

.add-input {
  flex: 1;
  min-width: 0;
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

.add-input::placeholder {
  color: var(--pencil);
}

.add-input:focus {
  outline: none;
  border-bottom-color: var(--ink-learner);
}

.summary-text {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink);
  white-space: pre-wrap;
  max-width: 72ch;
}

/* Check-questions as marked lines: the mark drawn in red pen, the gap in blue,
   the question in graphite and the date in pencil. No side bar, no fill. */
.event-list {
  list-style: none;
  padding: 0;
  margin: 0;
  width: 100%;
}

.event-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding-bottom: 0.75rem;
  box-shadow: inset 0 -1px 0 var(--rule);
}

.event-row + .event-row {
  padding-top: 0.75rem;
}

.event-mark {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  height: 1.75rem;
}

.event-mark-draw {
  fill: none;
  stroke: var(--ink-marker);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.event-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.event-gap {
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--ink-learner);
  overflow-wrap: anywhere;
}

.event-q {
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink);
  overflow-wrap: anywhere;
}

.event-when {
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--lh-body);
  color: var(--pencil);
}

.error {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink-marker-text);
}

/* A status caption: a small card with a head rule; the alert tab is red pen. */
.conflict {
  align-self: flex-start;
  margin: 1.75rem 0 0;
  padding: 0.25rem 0.75rem;
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-top: 3px solid var(--tab-focus);
  border-radius: 0 0 var(--radius-card) var(--radius-card);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--ink);
}

.skel {
  padding-top: 1.75rem;
}
</style>
