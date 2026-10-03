<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import { useToast } from './composables/useToast.js'
import { useSidebar } from './composables/useSidebar.js'
import { usePanel } from './composables/usePanel.js'
import { errorBus } from './services/errorBus.js'
import { friendlyError } from './lib/errors.js'
import Sidebar from './components/sidebar/Sidebar.vue'
import SidebarMobileTopStrip from './components/sidebar/SidebarMobileTopStrip.vue'
import RouteProgressBar from './components/RouteProgressBar.vue'

const { showError } = useToast()

const route = useRoute()

const { isDesktop, mode, closeDrawer, openDrawer, toggleDesktop } = useSidebar()

const { toggleDesktop: togglePanel } = usePanel()

const showShell = computed(() => route.meta?.sidebar !== false)

// Sheet routes are the page itself: they run edge to edge so the desk ground
// reaches the full width of the shell.
const isSheet = computed(() => route.meta?.sheet === true)

const { drawerOpen } = useSidebar()

// Drives the shell's sidebar column width (see .shell CSS below). The column
// snaps -- animating grid-template-columns relaid out the whole shell every
// frame; the collapse now reads as the sidebar's ink fading in (Sidebar.vue).
// On mobile the drawer is position: fixed and out of flow, so no class is
// applied and the column keeps its default "auto" (collapses to zero).
const shellSidebarClass = computed(() => {
  if (mode.value === 'expanded') return 'shell--sb-expanded'

  if (mode.value === 'collapsed') return 'shell--sb-collapsed'

  return null
})

// Close mobile drawer on every route change so tapping a session row
// dismisses the overlay (mobile UX expectation).
watch(
  () => route.fullPath,
  () => closeDrawer(),
)

// Lock body scroll while the mobile drawer is open so the user doesn't
// scroll the page underneath the backdrop.
watch(drawerOpen, (open) => {
  if (typeof document === 'undefined') return

  if (open) document.body.classList.add('sb-scroll-lock')
  else document.body.classList.remove('sb-scroll-lock')
})

onBeforeUnmount(() => {
  if (typeof document !== 'undefined') {
    document.body.classList.remove('sb-scroll-lock')
  }
})

// Skip 429 (daily-cap has dedicated banner+toast in SessionView) and 404
// (consumers typically render "not found" inline; double-surfacing is noisy).
// F-51: route through friendlyError() so raw backend detail (internal error
// codes, stack fragments) never lands in the toast.
const onApiError = (e) => {
  const err = e.detail

  if (!err || err.status === 429 || err.status === 404) return
  showError(friendlyError(err))
}

onMounted(() => errorBus.addEventListener('api-error', onApiError))

onBeforeUnmount(() => errorBus.removeEventListener('api-error', onApiError))

// Shell shortcuts: Ctrl+B folds the sidebar, Ctrl+. folds the profile panel.
// Both are no-ops while the user is typing, and while a PrimeVue overlay owns
// the screen -- a dialog or popover is a modal context, not the shell.
const EDITABLE_TAGS = ['INPUT', 'TEXTAREA', 'SELECT']

function isEditableTarget(target) {
  if (!target || typeof target !== 'object') return false

  if (EDITABLE_TAGS.includes(target.tagName)) return true

  return target.isContentEditable === true
}

function overlayOpen() {
  if (typeof document === 'undefined') return false

  return Boolean(document.querySelector('.p-overlay-mask, .p-dialog, .p-popover'))
}

function onShellKeydown(e) {
  // Ctrl only: Ctrl+Shift+B is the browser's own bookmarks-bar toggle.
  if (!e.ctrlKey || e.shiftKey || e.altKey || e.metaKey) return

  if (isEditableTarget(e.target)) return

  if (overlayOpen()) return

  const key = typeof e.key === 'string' ? e.key.toLowerCase() : ''

  if (key === 'b') {
    if (isDesktop.value) toggleDesktop()
    else if (drawerOpen.value) closeDrawer()
    else openDrawer()
    e.preventDefault()

    return
  }

  if (key === '.' || e.code === 'Period') {
    togglePanel()
    e.preventDefault()
  }
}

onMounted(() => {
  if (typeof window !== 'undefined') window.addEventListener('keydown', onShellKeydown)
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') window.removeEventListener('keydown', onShellKeydown)
})
</script>

<template>
  <RouteProgressBar />
  <div v-if="showShell" class="shell" :class="shellSidebarClass">
    <a class="skip-link" href="#main-content" data-testid="skip-link"> Skip to main content </a>
    <Sidebar />
    <div class="shell-main">
      <SidebarMobileTopStrip v-if="!isDesktop" />
      <main id="main-content" class="page" tabindex="-1">
        <div class="page-inner" :class="{ 'page-inner-sheet': isSheet }">
          <RouterView v-slot="{ Component }">
            <transition name="fade">
              <component :is="Component" />
            </transition>
          </RouterView>
        </div>
      </main>
    </div>
  </div>
  <!-- D-15: chrome-less routes (login, legal, 404, onboarding) get the same
       focus target as the shell so the router's afterEach has something stable
       to move focus to. The id lives on this wrapper rather than on each view
       root: afterEach runs before Vue swaps the rendered view, so a per-view id
       would resolve to the outgoing root and lose focus when it unmounts. -->
  <div v-else id="main-content" tabindex="-1">
    <RouterView v-slot="{ Component }">
      <transition name="fade">
        <component :is="Component" />
      </transition>
    </RouterView>
  </div>
  <Toast position="top-right" />
  <ConfirmDialog />
</template>

<style>
.shell {
  display: grid;
  grid-template-columns: var(--shell-sidebar-col, auto) 1fr;
  min-height: 100vh;
  align-items: stretch;
}

.shell--sb-expanded {
  --shell-sidebar-col: var(--sidebar-width-expanded, 18rem);
}

.shell--sb-collapsed {
  --shell-sidebar-col: var(--sidebar-width-collapsed, 3rem);
}

.shell-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 100vh;
}

.page {
  position: relative;
  flex: 1;
  z-index: 1;
}

.page-inner {
  max-width: 72rem;
  margin: 0 auto;
  padding: clamp(2rem, 6vw, 4.5rem) clamp(1rem, 4vw, 2.5rem) 4rem;
}

/* Full-width escape for sheet routes: the page runs to both edges. */
.page-inner-sheet {
  max-width: none;
  padding-left: 0;
  padding-right: 0;
}

/* U-02: enter-only route fade. The former mode="out-in" + leave transition
   could stall with a fully blank pane until the next re-render (leaving view
   removed, entering view never inserted) -- with no leave phase and no out-in
   gap, the old view drops instantly and the new one fades in.
   Opacity only: in this world ink appears, it never slides. */
.fade-enter-active {
  transition: opacity 160ms ease;
}
.fade-enter-from {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .fade-enter-active {
    transition: none;
  }
}
</style>
