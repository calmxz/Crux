<script setup>
import { computed, nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSidebar } from '@/composables/useSidebar.js'
import { useSessionActions } from '@/composables/useSessionActions.js'
import SidebarRowMenu from './SidebarRowMenu.vue'

const props = defineProps({
  session: { type: Object, required: true },
  /** 'active' | 'ended' */
  state: { type: String, required: true },
})

const route = useRoute()

const router = useRouter()

const { closeDrawer } = useSidebar()

const actions = useSessionActions()

const { busy } = actions

const renaming = ref(false)

const draft = ref('')

const inputEl = ref(null)

const menuEl = ref(null)

const isCurrent = computed(() => route.params.id === props.session.id)

// Row label cells. SessionListItem.progress carries focus_target_gap, level,
// and mastered_count. Only the topic is shown on the row; the rest still feed
// the aria-label for screen readers.
const masteredCount = computed(() => props.session.progress?.mastered_count || 0)

const focusCue = computed(() => props.session.progress?.focus_target_gap || '')

const level = computed(() => props.session.progress?.level || null)

const rowLabel = computed(() => {
  const parts = [`Open session: ${props.session.topic || 'Untitled'}`]

  if (level.value) parts.push(`level ${level.value}`)

  if (focusCue.value) parts.push(`focus ${focusCue.value}`)

  if (masteredCount.value) parts.push(`${masteredCount.value} mastered`)

  return parts.join(', ')
})

function openSession() {
  closeDrawer()
  router.push({ name: 'session', params: { id: props.session.id } })
}

// E-12: ending a session is one-way from the row's point of view -- there is no
// undo on the row and the learner may be several screens from the transcript --
// so it asks first. Same dialog contract as the file delete in
// ReferenceStatusBanner: no icon, neutral cancel, strong destructive accept.
function onEnd() {
  actions.confirmEnd(props.session)
}

function onResume() {
  actions.resume(props.session)
}

function onContinueTopic() {
  actions.continueTopic(props.session)
}

// Rename never moves the row between lists, so this instance's own menu is
// still mounted and can be focused through its exposed method.
function refocusOwnTrigger() {
  nextTick(() => menuEl.value?.focusTrigger())
}

// Pinning DOES move the row: setPinned patches `pinned` optimistically, so the
// row leaves the pinned <ul> for the active one (or back) and Vue mounts a
// FRESH component. This instance's ref is nulled by then, so the replacement
// has to be found in the document by session id.
function refocusRowTrigger(id) {
  nextTick(() => {
    const row = document.querySelector(`[data-session-id="${id}"]`)
    row?.querySelector('[data-testid="sidebar-row-menu-trigger"]')?.focus()
  })
}

function setPin(on) {
  const id = props.session.id
  actions.setPinned(props.session, on)
  refocusRowTrigger(id)
}

async function startRename() {
  draft.value = props.session.topic || ''
  renaming.value = true
  await nextTick()
  inputEl.value?.focus()
  inputEl.value?.select()
}

function cancelRename() {
  draft.value = props.session.topic || ''
  renaming.value = false
  refocusOwnTrigger()
}

async function commitRename() {
  if (!renaming.value) return
  const next = draft.value
  renaming.value = false
  await actions.rename(props.session, next)
}

function commitRenameFromKey() {
  commitRename()
  refocusOwnTrigger()
}
</script>

<template>
  <li
    class="sb-row"
    :class="{
      'sb-row--current': isCurrent,
      'sb-row--ended': state === 'ended',
    }"
    :data-session-id="session.id"
    :data-testid="`sidebar-row-${session.id}`"
  >
    <button
      type="button"
      class="sb-row-button hit-44"
      :aria-current="isCurrent ? 'page' : undefined"
      :aria-label="rowLabel"
      data-testid="sidebar-row-open"
      @click="openSession"
    >
      <input
        v-if="renaming"
        ref="inputEl"
        v-model="draft"
        type="text"
        class="sb-row-rename-input"
        aria-label="Rename session"
        data-testid="sidebar-row-rename-input"
        @keydown.enter.prevent="commitRenameFromKey"
        @keydown.esc.prevent="cancelRename"
        @blur="commitRename"
        @click.stop
      />
      <span v-else class="sb-row-topic">
        <svg
          v-if="session.pinned && !session.ended_at"
          class="sb-row-pin"
          viewBox="0 0 20 20"
          width="12"
          height="12"
          fill="currentColor"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M6 3.5 H14 V16.5 L10 13.5 L6 16.5 Z" />
        </svg>
        {{ session.topic || 'Untitled' }}
      </span>
    </button>
    <SidebarRowMenu
      ref="menuEl"
      :state="state"
      :busy="busy"
      :pinned="session.pinned ?? false"
      @end="onEnd"
      @resume="onResume"
      @continue-topic="onContinueTopic"
      @pin="setPin(true)"
      @unpin="setPin(false)"
      @rename="startRename"
    />
  </li>
</template>

<style scoped>
/* A row is a ruled line on the contents page: no card, no radius, no fill.
   Height is a whole multiple of the pitch so every row sits on a rule. */
.sb-row {
  position: relative;
  display: flex;
  align-items: stretch;
  padding: 0;
  margin: 0;
  list-style: none;
  border-radius: var(--radius-card);
}

.sb-row:hover,
.sb-row:focus-within {
  background: color-mix(in srgb, var(--card) 60%, transparent);
}

/* The current session sits on its own white card, the one row on the
   contents page that is allowed to lift off the ground. */
.sb-row--current {
  background: var(--card);
  border: 1px solid var(--card-edge);
  box-shadow: 0 1px 0 var(--card-drop);
}

.sb-row--current:hover,
.sb-row--current:focus-within {
  background: var(--card);
}

.sb-row:hover :deep(.sb-row-menu-trigger),
.sb-row:focus-within :deep(.sb-row-menu-trigger) {
  opacity: 1;
}

.sb-row-button {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: var(--line-pitch);
  padding: 0.25rem 0.25rem 0.25rem 0.75rem;
  border: 0;
  border-radius: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  color: var(--color-text);
}

.sb-row-button:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: -2px;
  border-radius: 0;
}

.sb-row-topic {
  flex: 1;
  min-width: 0;
  /* Carried down from the wrappers this span replaced: the row's height is a
     whole multiple of the pitch so it sits on a rule. */
  line-height: var(--line-pitch);
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  font-weight: 400;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sb-row--ended .sb-row-topic {
  color: var(--pencil);
}

.sb-row--current .sb-row-topic {
  font-weight: 700;
}

/* Renaming writes on the same rule the row sits on. */
.sb-row-rename-input {
  width: 100%;
  border: 0;
  border-bottom: 1px solid var(--ink-learner);
  border-radius: 0;
  background: transparent;
  color: var(--color-text);
  font-family: inherit;
  font-size: 0.9375rem;
  line-height: calc(var(--line-pitch) - 1px);
  padding: 0;
}

.sb-row-rename-input:focus-visible {
  outline: none;
  border-bottom-width: 2px;
}

.sb-row-pin {
  flex-shrink: 0;
  vertical-align: middle;
  color: var(--pencil);
  margin-right: 0.25rem;
}
</style>
