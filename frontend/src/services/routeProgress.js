import { reactive } from 'vue'

// Route-transition progress state. The bar only appears when a navigation
// (lazy chunk fetch, auth init, data guards) outlives SHOW_DELAY_MS, so
// instant navigations never flash it.
const SHOW_DELAY_MS = 150

const HIDE_AFTER_DONE_MS = 200

export const routeProgress = reactive({ visible: false, progress: 0 })

let showTimer = null

let hideTimer = null

export function start() {
  clearTimeout(showTimer)
  clearTimeout(hideTimer)
  routeProgress.visible = false
  routeProgress.progress = 0
  showTimer = setTimeout(() => {
    routeProgress.visible = true
    // The component's CSS transform transition animates the trickle toward 85%.
    routeProgress.progress = 0.85
  }, SHOW_DELAY_MS)
}

export function finish() {
  clearTimeout(showTimer)
  clearTimeout(hideTimer)

  if (!routeProgress.visible) {
    routeProgress.progress = 0

    return
  }

  routeProgress.progress = 1
  hideTimer = setTimeout(() => {
    routeProgress.visible = false
    routeProgress.progress = 0
  }, HIDE_AFTER_DONE_MS)
}

export const fail = finish
