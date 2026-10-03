<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  /** 'active' | 'ended' — controls which action is offered */
  state: { type: String, required: true },
  /** Disable while async store action in flight */
  busy: { type: Boolean, default: false },
  /** Whether this session is currently pinned */
  pinned: { type: Boolean, default: false },
})

const emit = defineEmits(['end', 'resume', 'continue-topic', 'rename', 'pin', 'unpin'])

const open = ref(false)

const triggerEl = ref(null)

const popoverEl = ref(null)

function toggle() {
  if (props.busy) return
  open.value = !open.value
}

function close() {
  open.value = false
}

function focusTrigger() {
  triggerEl.value?.focus()
}

// Every item does the same three things; only the emitted name differs.
function onAction(kind) {
  if (props.busy) return
  emit(kind)
  close()
  focusTrigger()
}

function onDocPointerDown(e) {
  if (!open.value) return

  if (popoverEl.value?.contains(e.target)) return

  if (triggerEl.value?.contains(e.target)) return
  close()
}

function onKey(e) {
  if (!open.value) return

  if (e.key === 'Escape') {
    e.stopPropagation()
    close()
    focusTrigger()
  }
}

// Bound only while this row's menu is open. A sidebar can hold 40 rows, and
// document-level capture listeners kept for every row's whole lifetime would
// run 80 handlers on every keystroke in the app.
function addDocListeners() {
  document.addEventListener('pointerdown', onDocPointerDown, true)
  document.addEventListener('keydown', onKey, true)
}

function removeDocListeners() {
  document.removeEventListener('pointerdown', onDocPointerDown, true)
  document.removeEventListener('keydown', onKey, true)
}

watch(open, (isOpen) => {
  if (isOpen) addDocListeners()
  else removeDocListeners()
})

onBeforeUnmount(removeDocListeners)

// Lets the owning row put focus back on this trigger after an action that
// leaves the row mounted (rename).
defineExpose({ focusTrigger })
</script>

<template>
  <div class="sb-row-menu" @click.stop>
    <button
      ref="triggerEl"
      type="button"
      class="sb-row-menu-trigger hit-44"
      :class="{ 'is-open': open }"
      :aria-expanded="open"
      :aria-label="state === 'active' ? 'Session actions' : 'Ended session actions'"
      :disabled="busy"
      data-testid="sidebar-row-menu-trigger"
      @click="toggle"
    >
      <svg
        class="sb-menu-icon"
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
        <path d="M4.5 10 L4.6 10 M10 10 L10.1 10 M15.5 10 L15.6 10" />
      </svg>
    </button>
    <div
      v-if="open"
      ref="popoverEl"
      class="sb-row-menu-popover"
      role="group"
      :aria-label="state === 'active' ? 'Session actions' : 'Ended session actions'"
      data-testid="sidebar-row-menu-popover"
    >
      <button
        type="button"
        class="sb-row-menu-item"
        data-testid="sidebar-row-menu-rename"
        :disabled="busy"
        @click="onAction('rename')"
      >
        <svg
          class="sb-menu-icon"
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
          <path d="M13.5 3.5 L16.5 6.5 L6.5 16.5 H3.5 V13.5 Z M11.5 5.5 L14.5 8.5" />
        </svg>
        <span>Rename</span>
      </button>
      <button
        v-if="state === 'active'"
        type="button"
        class="sb-row-menu-item"
        data-testid="sidebar-row-menu-pin"
        :disabled="busy"
        @click="onAction(pinned ? 'unpin' : 'pin')"
      >
        <svg
          class="sb-menu-icon"
          viewBox="0 0 20 20"
          width="13"
          height="13"
          :fill="pinned ? 'currentColor' : 'none'"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M6 3.5 H14 V16.5 L10 13.5 L6 16.5 Z" />
        </svg>
        <span>{{ pinned ? 'Unpin' : 'Pin' }}</span>
      </button>
      <button
        v-if="state === 'active'"
        type="button"
        class="sb-row-menu-item sb-row-menu-item--danger"
        data-testid="sidebar-row-menu-end"
        :disabled="busy"
        @click="onAction('end')"
      >
        <svg
          class="sb-menu-icon"
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
          <path d="M4.5 3 V17 M4.5 4 H15 L12.5 7 L15 10 H4.5" />
        </svg>
        <span>End session</span>
      </button>
      <button
        v-if="state === 'ended'"
        type="button"
        class="sb-row-menu-item"
        data-testid="sidebar-row-menu-continue-topic"
        :disabled="busy"
        @click="onAction('continue-topic')"
      >
        <svg
          class="sb-menu-icon"
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
          <path d="M5.5 3.5 L15.5 10 L5.5 16.5 Z" />
        </svg>
        <span>Continue topic</span>
      </button>
      <button
        v-if="state === 'ended'"
        type="button"
        class="sb-row-menu-item"
        data-testid="sidebar-row-menu-resume"
        :disabled="busy"
        @click="onAction('resume')"
      >
        <svg
          class="sb-menu-icon"
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
          <path d="M16 10 A6 6 0 1 1 13.5 5.5" />
          <path d="M13 3 L14 6.5 L10.5 6" />
        </svg>
        <span>Resume</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.sb-row-menu {
  position: relative;
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.sb-row-menu-trigger {
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
  opacity: 0;
  transition:
    opacity var(--motion-fast) ease,
    color var(--motion-fast) ease;
}

.sb-row-menu-trigger.is-open,
.sb-row-menu-trigger:focus-visible,
.sb-row-menu-trigger:hover {
  opacity: 1;
  color: var(--ink-learner);
}

/* The trigger appears at once instead of fading in. */
@media (prefers-reduced-motion: reduce) {
  .sb-row-menu-trigger {
    transition: none;
  }
}

/* On touch / coarse-pointer devices there is no hover to reveal the trigger, so
   keep it visible -- otherwise Rename/Pin/End are unreachable (a row tap just
   navigates). Fine pointers keep the opacity:0-until-hover behavior above. */
@media (hover: none) {
  .sb-row-menu-trigger {
    opacity: 1;
  }
}

.sb-row-menu-trigger:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: 2px;
}

.sb-row-menu-trigger:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

/* An overlay is the one thing allowed to lift off the page. */
.sb-row-menu-popover {
  position: absolute;
  right: 0;
  top: calc(100% + 0.25rem);
  z-index: 40;
  min-width: 10rem;
  background: var(--color-surface-raised);
  border: 1px solid var(--rule-strong);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lift);
  padding: 0.25rem 0;
  display: flex;
  flex-direction: column;
}

.sb-row-menu-item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0 0.75rem;
  min-height: var(--line-pitch);
  border: 0;
  border-radius: 0;
  background: transparent;
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  color: var(--color-text);
  cursor: pointer;
  text-align: left;
  transition: background var(--motion-fast) ease;
}

.sb-menu-icon {
  flex-shrink: 0;
  color: var(--pencil);
}

.sb-row-menu-item:hover:not(:disabled) {
  background: var(--color-surface-soft);
}

.sb-row-menu-item:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: -2px;
  border-radius: 0;
}

.sb-row-menu-item:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.sb-row-menu-item--danger,
.sb-row-menu-item--danger .sb-menu-icon {
  color: var(--color-error-text);
}

.sb-row-menu-item--danger:hover:not(:disabled) {
  background: color-mix(in srgb, var(--ink-marker) 10%, transparent);
}
</style>
