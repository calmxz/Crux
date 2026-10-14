import { defineConfig, globalIgnores } from 'eslint/config'
import globals from 'globals'
import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import pluginVitest from '@vitest/eslint-plugin'
import pluginOxlint from 'eslint-plugin-oxlint'
import skipFormatting from 'eslint-config-prettier/flat'

export default defineConfig([
  {
    name: 'app/files-to-lint',
    files: ['**/*.{vue,js,mjs,jsx}'],
  },

  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**']),

  {
    languageOptions: {
      globals: {
        ...globals.browser,
      },
    },
  },

  // Node-context configs and Playwright specs run under Node, not the browser.
  {
    files: ['playwright.config.js', 'e2e/**/*.{js,mjs}', '*.config.js'],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },

  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],

  {
    ...pluginVitest.configs.recommended,
    files: ['src/**/__tests__/*'],
  },

  ...pluginOxlint.buildFromOxlintConfigFile('.oxlintrc.json'),

  // data-testid is a test hook: product code reaches elements through template
  // refs, an exposed method, or a class/attribute it owns, so renaming a test
  // hook can never silently break behaviour (focus restore, #544).
  {
    files: ['src/**/*.{vue,js}'],
    ignores: ['src/**/__tests__/**'],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector: 'Literal[value=/data-testid/]',
          message: 'Product code must not select by data-testid; use a ref or an owned class.',
        },
        {
          selector: 'TemplateElement[value.raw=/data-testid/]',
          message: 'Product code must not select by data-testid; use a ref or an owned class.',
        },
      ],
    },
  },

  // Single-word component names that are intentional (design-specified filenames).
  {
    files: ['src/components/chat/Composer.vue'],
    rules: { 'vue/multi-word-component-names': 'off' },
  },

  skipFormatting,
])
