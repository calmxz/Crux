import './assets/main.css'
import './assets/aura-tokens.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Aura from '@primeuix/themes/aura'
import { definePreset } from '@primeuix/themes'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth.js'
import { setUnauthorizedHandler } from './services/apiClient.js'
import { useTheme } from './composables/useTheme.js'
import { adaptPresetConfig } from './theme/adaptPreset.js'

const AdaptPreset = definePreset(Aura, adaptPresetConfig)

// F-16: carry the location like the router guard does (F-49), so re-login
// returns the user to where the expiry hit them. Wired here (rather than
// apiClient importing the router directly) to avoid a static import cycle --
// see the comment on setUnauthorizedHandler in apiClient.js.
setUnauthorizedHandler(() => {
  router.push({
    name: 'login',
    query: { redirect: router.currentRoute.value.fullPath },
  })
})

// Both origins are hit within the first moments of boot (Supabase getSession
// refresh, then /me + /sessions/library). Preconnect warms DNS+TCP+TLS while
// the rest of the bundle parses and auth resolves.
function preconnect() {
  const hrefs = [import.meta.env.VITE_API_BASE_URL, import.meta.env.VITE_SUPABASE_URL]

  for (const href of hrefs) {
    if (!href) continue

    try {
      const origin = new URL(href, window.location.href).origin

      if (origin === window.location.origin) continue
      const link = document.createElement('link')
      link.rel = 'preconnect'
      link.href = origin
      link.crossOrigin = 'anonymous'
      document.head.appendChild(link)
    } catch {
      // malformed env value -- skip
    }
  }
}

async function bootstrap() {
  preconnect()
  const app = createApp(App)
  app.use(createPinia())
  useTheme().init()

  // Resolve Supabase session before the router guard fires, so the first
  // navigation has a deterministic auth answer rather than racing with the
  // SDK's initial getSession() call. auth.init() also re-keys the user
  // store to the resolved uid (F-08), so no separate boot-time load here.
  try {
    await useAuthStore().init()
  } catch (e) {
    // F-14: never leave a blank page - mount unauthenticated and let the
    // router guard route to /login.
    console.error('auth init failed; continuing unauthenticated', e)
  }

  app.use(router)
  app.use(PrimeVue, {
    theme: {
      preset: AdaptPreset,
      options: {
        darkModeSelector: '[data-theme="dark"]',
      },
    },
  })
  app.use(ToastService)
  app.use(ConfirmationService)

  app.mount('#app')
}

bootstrap()
