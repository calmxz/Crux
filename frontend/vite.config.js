import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

import { cspPlugin } from './cspPlugin.js'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      vue(),
      vueDevTools(),
      cspPlugin(env.VITE_API_BASE_URL || ''),
    ],
    define: {
      // Vercel sets VERCEL=1 during its builds; see src/lib/analytics.js.
      'import.meta.env.VITE_VERCEL_ANALYTICS': JSON.stringify(process.env.VERCEL === '1' ? '1' : ''),
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      },
    },
  }
})
