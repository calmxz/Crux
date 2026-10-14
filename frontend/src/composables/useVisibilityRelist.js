import { onBeforeUnmount, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import { useSessionStore } from '@/stores/session.js'

// #534: re-list the sidebar window when the tab becomes visible again (the
// store throttles it; see relistIfStale). Module-scoped consumer count so two
// mounted sidebars register one document listener, removed when the last
// one unmounts.
let consumers = 0

function onVisibilityChange() {
  if (document.visibilityState !== 'visible') return

  if (!useAuthStore().isAuthenticated) return
  useSessionStore().relistIfStale()
}

export function useVisibilityRelist() {
  onMounted(() => {
    consumers += 1

    if (consumers === 1) document.addEventListener('visibilitychange', onVisibilityChange)
  })

  onBeforeUnmount(() => {
    consumers -= 1

    if (consumers === 0) document.removeEventListener('visibilitychange', onVisibilityChange)
  })
}
