import { computed, readonly, ref } from 'vue'

const STORAGE_KEY = 'crux:theme:v1'

const VALID = ['light', 'dark', 'auto']

const override = ref(loadInitial())

const systemDark = ref(false)

let mediaQuery = null

function loadInitial() {
  if (typeof window === 'undefined') return 'auto'
  const stored = window.localStorage?.getItem(STORAGE_KEY)

  return VALID.includes(stored) ? stored : 'auto'
}

function persist(value) {
  if (typeof window === 'undefined') return

  try {
    window.localStorage?.setItem(STORAGE_KEY, value)
  } catch {
    /* private mode, ignore */
  }
}

function applyAttribute(resolved) {
  if (typeof document === 'undefined') return
  // Always pin data-theme to the resolved value, including in auto mode.
  // PrimeVue overlays (ConfirmDialog/Toast, teleported to <body>) only adopt
  // dark styling via the [data-theme="dark"] selector. Stripping the attribute
  // in auto mode left those overlays light while the app tokens went dark via
  // the prefers-color-scheme fallback in base.css.
  document.documentElement.setAttribute('data-theme', resolved)
}

const resolved = computed(() => {
  if (override.value === 'light') return 'light'

  if (override.value === 'dark') return 'dark'

  return systemDark.value ? 'dark' : 'light'
})

// F-20: module-scope so dispose() can remove the exact listener init() added
// (a closure declared inside init() would be a different function reference
// each call, so removeEventListener/removeListener would silently no-op).
function handler(event) {
  systemDark.value = event.matches
  applyAttribute(resolved.value)
}

function init() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return

  // Re-entry guard: a second init() call (e.g. a second component mount)
  // must not attach a second matchMedia listener with no way to remove it.
  if (mediaQuery) return

  if (window.matchMedia) {
    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    systemDark.value = mediaQuery.matches

    if (mediaQuery.addEventListener) mediaQuery.addEventListener('change', handler)
    else mediaQuery.addListener(handler)
  }

  applyAttribute(resolved.value)
}

export function dispose() {
  if (!mediaQuery) return

  if (mediaQuery.removeEventListener) mediaQuery.removeEventListener('change', handler)
  else mediaQuery.removeListener(handler)
  mediaQuery = null
}

function setTheme(value) {
  if (!VALID.includes(value)) return
  override.value = value
  persist(value)
  applyAttribute(resolved.value)
}

function toggle() {
  setTheme(resolved.value === 'dark' ? 'light' : 'dark')
}

export function useTheme() {
  return {
    override: readonly(override),
    resolved: readonly(resolved),
    isDark: computed(() => resolved.value === 'dark'),
    init,
    dispose,
    setTheme,
    toggle,
  }
}
