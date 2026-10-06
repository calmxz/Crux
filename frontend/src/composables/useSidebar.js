import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const BREAKPOINT = 1280

const LS_KEY = 'crux.sidebar.expanded'

const viewport = ref(typeof window !== 'undefined' ? window.innerWidth : BREAKPOINT)

const desktopExpanded = ref(_readPersisted())

const drawerOpen = ref(false)

// One window listener for every consumer: each sidebar row and the session
// actions composable call useSidebar(), so per-instance listeners multiplied
// with the row count. Ref-counted so the listener lives while any consumer
// is mounted and goes when the last one leaves.
let _listeners = 0

function _onResize() {
  viewport.value = window.innerWidth

  if (viewport.value >= BREAKPOINT) drawerOpen.value = false
}

function _readPersisted() {
  if (typeof window === 'undefined') return true

  try {
    const raw = window.localStorage.getItem(LS_KEY)

    if (raw === null) return true

    return raw === '1'
  } catch {
    return true
  }
}

function _persist(v) {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.setItem(LS_KEY, v ? '1' : '0')
  } catch {
    /* private mode, ignore */
  }
}

export function useSidebar() {
  const isDesktop = computed(() => viewport.value >= BREAKPOINT)

  const mode = computed(() => {
    if (!isDesktop.value) return drawerOpen.value ? 'drawer-open' : 'drawer-closed'

    return desktopExpanded.value ? 'expanded' : 'collapsed'
  })

  function toggleDesktop() {
    desktopExpanded.value = !desktopExpanded.value
    _persist(desktopExpanded.value)
  }

  function openDrawer() {
    drawerOpen.value = true
  }

  function closeDrawer() {
    drawerOpen.value = false
  }


  onMounted(() => {
    if (typeof window === 'undefined') return

    if (_listeners === 0) {
      window.addEventListener('resize', _onResize, { passive: true })
    }

    _listeners += 1
  })
  onBeforeUnmount(() => {
    if (typeof window === 'undefined') return
    _listeners = Math.max(0, _listeners - 1)

    if (_listeners === 0) {
      window.removeEventListener('resize', _onResize)
    }
  })

  return {
    mode,
    isDesktop,
    desktopExpanded,
    drawerOpen,
    toggleDesktop,
    openDrawer,
    closeDrawer,
  }
}

export const __test__ = {
  BREAKPOINT,
  LS_KEY,
  _setViewport(v) {
    viewport.value = v
  },
  _setExpanded(v) {
    desktopExpanded.value = v
  },
}
