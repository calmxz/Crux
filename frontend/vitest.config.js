import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig({ mode: 'test', command: 'serve' }),
  defineConfig({
    test: {
      environment: 'jsdom',
      // One jsdom per worker instead of per file; vm contexts keep per-file isolation.
      pool: 'vmThreads',
      exclude: [...configDefaults.exclude, 'e2e/**'],
      root: fileURLToPath(new URL('./', import.meta.url)),
      setupFiles: ['./src/__tests__/setup.js'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'html'],
        include: ['src/**/*.{js,vue}'],
        exclude: ['src/**/*.spec.js', 'src/**/__tests__/**', 'e2e/**', 'src/main.js'],
        thresholds: { lines: 80, statements: 80, functions: 70, branches: 65 },
      },
    },
  }),
)
