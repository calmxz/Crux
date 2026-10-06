import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

// Profile panel (CueColumn) collapse state. Mirrors useSidebar.js in shape:
// module-singleton refs, localStorage persistence, a resize listener.
//
// Deliberate difference from useSidebar: `collapsed` is NOT gated on isDesktop.
// The panel column only exists at >= 900px (SessionView's media query drops
// --panel-col below that), and the desktop breakpoint here is 1280 -- gating
// would make the toggle a silent no-op on every 1024-1279 laptop. isDesktop is
// still exposed for consumers that want it.
const BREAKPOINT = 1280

const LS_KEY = 'crux.panel.expanded'

const viewport = ref(typeof window !== 'undefined' ? window.innerWidth : BREAKPOINT)

const desktopExpanded = ref(_readPersisted())

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

export function usePanel() {
  const isDesktop = computed(() => viewport.value >= BREAKPOINT)
  const collapsed = computed(() => !desktopExpanded.value)

  function toggleDesktop() {
    desktopExpanded.value = !desktopExpanded.value
    _persist(desktopExpanded.value)
  }

  function onResize() {
    if (typeof window === 'undefined') return
    viewport.value = window.innerWidth
  }

  onMounted(() => {
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', onResize, { passive: true })
    }
  })
  onBeforeUnmount(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', onResize)
    }
  })

  return {
    isDesktop,
    desktopExpanded,
    collapsed,
    toggleDesktop,
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
