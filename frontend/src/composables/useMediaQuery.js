import { onBeforeUnmount, onMounted, ref } from 'vue'

// The one breakpoint the chat shell switches on in JS as well as CSS. Kept in
// sync with the 899px media blocks in SessionView.vue and CueColumn.vue.
export const NARROW_QUERY = '(max-width: 899px)'

// JS-driven motion (e.g. window.scrollTo behavior) has no CSS media block to
// fall back on, so it reads the preference through this query.
export const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)'

// Reactive matchMedia. Returns a ref that is false where matchMedia does not
// exist (jsdom, SSR) and otherwise tracks the query for the component's life.
export function useMediaQuery(query) {
  const matches = ref(false)
  let mql = null

  function onChange(e) {
    matches.value = e.matches
  }

  onMounted(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    mql = window.matchMedia(query)
    matches.value = mql.matches
    mql.addEventListener?.('change', onChange)
  })
  onBeforeUnmount(() => {
    mql?.removeEventListener?.('change', onChange)
    mql = null
  })

  return matches
}
