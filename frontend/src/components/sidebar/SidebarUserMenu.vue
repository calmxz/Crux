<script setup>
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

const props = defineProps({
  /** Display name; empty when the learner has not set one. */
  name: { type: String, default: '' },
  email: { type: String, default: '' },
  /** Folded rail: the circle alone; the menu lifts out of the clipped rail but opens where it does unfolded. */
  collapsed: { type: Boolean, default: false },
})

// `navigate` carries a router location; the parent routes and closes the
// mobile drawer.
const emit = defineEmits(['navigate', 'sign-out'])

// Drawn 20-unit icons in the sidebar's stroke grammar, one per item. An item
// with `to` navigates; Sign out, set apart by a rule, has none.
const ITEMS = [
  {
    slug: 'settings',
    label: 'Settings',
    to: '/settings',
    paths: [
      'M10 3.5 V5.5 M10 14.5 V16.5 M16.5 10 H14.5 M5.5 10 H3.5 M14.7 5.3 L13.3 6.7 M6.7 13.3 L5.3 14.7 M14.7 14.7 L13.3 13.3 M6.7 6.7 L5.3 5.3',
    ],
    circle: { cx: 10, cy: 10, r: 2.5 },
  },
  {
    slug: 'usage',
    label: 'Usage',
    to: { name: 'settings', params: { tab: 'usage' } },
    paths: ['M3.5 14.5 A6.5 6.5 0 1 1 16.5 14.5', 'M10 14.5 L13 9.5'],
  },
  {
    slug: 'account',
    label: 'Account',
    to: { name: 'account' },
    paths: ['M4 16.5 C4 13.5 6.7 12 10 12 C13.3 12 16 13.5 16 16.5'],
    circle: { cx: 10, cy: 7, r: 3 },
  },
  {
    slug: 'sign-out',
    label: 'Sign out',
    testid: 'sidebar-sign-out',
    ruleBefore: true,
    paths: ['M8 3.5 H4.5 V16.5 H8', 'M11.5 6.5 L15 10 L11.5 13.5 M15 10 H8'],
  },
]

const open = ref(false)

const triggerEl = ref(null)

const popoverEl = ref(null)

const fixedStyle = ref(null)

const menuId = `sb-user-menu-${useId()}`

// The name, else the email's local part: the row never shows a full address.
// The full email appears only as the open menu's head.
const displayName = computed(
  () => (props.name || '').trim() || (props.email || '').trim().split('@')[0],
)

const initial = computed(() => {
  // Array.from splits by code point, so a leading astral character (emoji,
  // rarer CJK) stays whole rather than yielding half a surrogate pair.
  return Array.from(displayName.value)[0]?.toUpperCase() ?? '?'
})

function menuItems() {
  return popoverEl.value ? Array.from(popoverEl.value.querySelectorAll('[role="menuitem"]')) : []
}

// The sidebar clips its overflow, and the folded rail is narrower than the
// card. Folded, the popover is teleported to <body> and pinned where it sits
// unfolded: 0.25rem above the trigger, its left edge on the avatar's.
function placeFixed() {
  const trigger = triggerEl.value

  if (!trigger) return
  const rect = trigger.getBoundingClientRect()
  // Folded, the avatar is centred in a wider trigger, so align to the avatar
  // itself rather than the trigger's edge.
  const avatar = trigger.querySelector('.sb-avatar')?.getBoundingClientRect() ?? rect
  fixedStyle.value = {
    left: `${avatar.left}px`,
    // 4px mirrors the unfolded card's `bottom: calc(100% + 0.25rem)`.
    bottom: `${Math.max(0, window.innerHeight - rect.top + 4)}px`,
  }
}

async function openMenu(focusLast = false) {
  if (props.collapsed) placeFixed()
  open.value = true
  await nextTick()
  const items = menuItems()
  items[focusLast ? items.length - 1 : 0]?.focus()
}

function close() {
  open.value = false
}

function focusTrigger() {
  triggerEl.value?.focus()
}

function closeAndReturn() {
  close()
  focusTrigger()
}

function toggle() {
  if (open.value) closeAndReturn()
  else openMenu()
}

// Menu button pattern: ArrowDown and Enter open on the first item, ArrowUp
// on the last. Space is left to the native button click, which opens on the
// first item through toggle().
function onTriggerKeydown(e) {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()

    if (!open.value) openMenu(e.key === 'ArrowUp')
  } else if (e.key === 'Enter') {
    // Cancelling Enter's default also cancels its synthetic click.
    e.preventDefault()
    toggle()
  }
}

function onMenuKeydown(e) {
  const items = menuItems()

  if (!items.length) return
  const idx = items.indexOf(document.activeElement)

  if (e.key === 'ArrowDown') {
    e.preventDefault()
    items[(idx + 1) % items.length].focus()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    items[(idx - 1 + items.length) % items.length].focus()
  } else if (e.key === 'Home') {
    e.preventDefault()
    items[0].focus()
  } else if (e.key === 'End') {
    e.preventDefault()
    items[items.length - 1].focus()
  } else if (e.key === 'Tab') {
    // Leave the menu from its trigger so Tab carries on through the sidebar
    // even when the card is teleported to the end of <body>. The default is
    // cancelled so this Tab cannot slip past the mobile drawer's focus trap;
    // the next Tab moves on from the trigger as usual.
    e.preventDefault()
    closeAndReturn()
  }
}

function onItem(item) {
  closeAndReturn()

  if (item.to) emit('navigate', item.to)
  else emit('sign-out')
}

function onDocPointerDown(e) {
  if (!open.value) return

  if (popoverEl.value?.contains(e.target)) return

  if (triggerEl.value?.contains(e.target)) return
  // Outside click: focus follows the pointer, so it is not pulled back.
  close()
}

function onKey(e) {
  if (!open.value) return

  if (e.key === 'Escape') {
    e.stopPropagation()
    closeAndReturn()
  }
}

// Closing while focus is inside the menu would drop it to <body>; hand it
// back to the trigger once the menu is gone.
function closeKeepingFocus() {
  const hadFocus = popoverEl.value?.contains(document.activeElement)
  close()

  if (hadFocus) nextTick(focusTrigger)
}

// Only the folded, fixed-position card is pinned to viewport coordinates;
// the in-flow card follows the layout on its own.
function onViewportChange() {
  if (props.collapsed) closeKeepingFocus()
}

// Keydown listens on window in the capture phase, which runs before the
// mobile drawer's document-capture handler, so stopping Escape here closes
// only the menu and leaves the drawer open.
function addDocListeners() {
  document.addEventListener('pointerdown', onDocPointerDown, true)
  window.addEventListener('keydown', onKey, true)
  window.addEventListener('resize', onViewportChange)
}

function removeDocListeners() {
  document.removeEventListener('pointerdown', onDocPointerDown, true)
  window.removeEventListener('keydown', onKey, true)
  window.removeEventListener('resize', onViewportChange)
}

watch(open, (isOpen) => {
  if (isOpen) addDocListeners()
  else removeDocListeners()
})

// Folding or unfolding with the menu open would leave it anchored to the
// old layout; close it instead.
watch(
  () => props.collapsed,
  () => closeKeepingFocus(),
)

onBeforeUnmount(removeDocListeners)

defineExpose({ focusTrigger })
</script>

<template>
  <div class="sb-user" :class="{ 'sb-user--collapsed': collapsed }">
    <button
      ref="triggerEl"
      type="button"
      class="sb-user-trigger hit-44 coarse-2x"
      :class="{ 'is-open': open }"
      aria-haspopup="menu"
      :aria-expanded="open"
      :aria-controls="open ? menuId : undefined"
      :aria-label="`Account menu for ${displayName}`"
      :title="displayName"
      data-testid="sidebar-user-trigger"
      @click="toggle"
      @keydown="onTriggerKeydown"
    >
      <span class="sb-avatar" aria-hidden="true" data-testid="sidebar-user-initial">{{
        initial
      }}</span>
      <span v-if="!collapsed" class="sb-user-name" data-testid="sidebar-user-name">{{
        displayName
      }}</span>
    </button>
    <Teleport to="body" :disabled="!collapsed">
      <div
        v-if="open"
        ref="popoverEl"
        class="sb-user-menu"
        :class="{ 'sb-user-menu--fixed': collapsed }"
        :style="collapsed ? fixedStyle : null"
        data-testid="sidebar-user-menu"
        @keydown="onMenuKeydown"
      >
        <!-- The head names the signed-in account, the one place the full
             email shows. -->
        <p v-if="email" class="sb-user-menu-email" data-testid="sidebar-user-menu-email">
          {{ email }}
        </p>
        <div
          :id="menuId"
          role="menu"
          :aria-label="`Account menu for ${displayName}`"
          class="sb-user-menu-list"
          data-testid="sidebar-user-menu-list"
        >
          <template v-for="item in ITEMS" :key="item.slug">
            <div v-if="item.ruleBefore" class="sb-user-menu-rule" role="separator" />
            <button
              type="button"
              role="menuitem"
              tabindex="-1"
              class="sb-user-menu-item"
              :data-testid="item.testid || `sidebar-user-menu-${item.slug}`"
              @click="onItem(item)"
            >
              <svg
                class="sb-user-menu-icon"
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
                <circle v-if="item.circle" v-bind="item.circle" />
                <path v-for="d in item.paths" :key="d" :d="d" />
              </svg>
              {{ item.label }}
            </button>
          </template>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.sb-user {
  position: relative;
  display: flex;
}

.sb-user--collapsed {
  justify-content: center;
}

/* The identity row: a written line in the foot, one line pitch tall. */
.sb-user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  min-height: var(--line-pitch);
  padding: 0.25rem 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: color var(--motion-fast) ease;
}

.sb-user--collapsed .sb-user-trigger {
  width: 2.25rem;
  height: 2.25rem;
  padding: 0;
  justify-content: center;
}

.sb-user-trigger:hover,
.sb-user-trigger.is-open {
  color: var(--ink-learner);
}

.sb-user-trigger:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: 2px;
}

/* The one permitted mark of a person, and only in the shell. */
.sb-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--card);
  border: 1px solid var(--card-edge);
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: 1;
}

.sb-user-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-sans);
  font-size: 0.9375rem;
}

/* An overlay is the one thing allowed to lift off the page. */
.sb-user-menu {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% + 0.25rem);
  z-index: 40;
  min-width: 12rem;
  background: var(--color-surface-raised);
  border: 1px solid var(--rule-strong);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lift);
  padding: 0.25rem 0;
  display: flex;
  flex-direction: column;
}

.sb-user-menu--fixed {
  position: fixed;
  right: auto;
  max-width: 16rem;
}

/* The head: the signed-in email in pencil, above the items. */
.sb-user-menu-email {
  margin: 0;
  padding: 0.25rem 0.75rem 0.375rem;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  color: var(--pencil);
}

/* Sets Sign out apart from the navigation items. */
.sb-user-menu-rule {
  height: 0;
  margin: 0.25rem 0;
  border-top: 1px solid var(--rule);
}

.sb-user-menu-list {
  display: flex;
  flex-direction: column;
}

.sb-user-menu-item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
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

.sb-user-menu-item:hover {
  background: var(--desk-deep);
}

.sb-user-menu-icon {
  flex-shrink: 0;
  color: var(--pencil);
}

.sb-user-menu-item:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: -2px;
  border-radius: 0;
}

@media (prefers-reduced-motion: reduce) {
  .sb-user-trigger,
  .sb-user-menu-item {
    transition: none;
  }
}
</style>
