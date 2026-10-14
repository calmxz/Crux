import { defineConfig, devices } from '@playwright/test'

// E2E suite assumes the backend is already running at http://localhost:8000
// with LLM_STUB=1 (or GEMINI_API_KEY=test) so responses are deterministic.
// The frontend dev server is managed by Playwright via webServer below.
//
// The backend must run on Postgres + pgvector, as CI does: SQLite cannot run
// pgvector's `<=>` vector search.
//
// Local run: `frontend/e2e/run-local.sh [spec...]` (bash) starts that stack
// -- throwaway pgvector Postgres, the e2e JWKS that e2e/support/auth.js signs
// against (#518), the stubbed backend -- runs Playwright, and stops it all.
// Its header lists the ports it needs free.

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    trace: process.env.PWDEBUG ? 'on' : 'on-first-retry',
    video: process.env.CI ? 'retain-on-failure' : 'off',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
