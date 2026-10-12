import { defineConfig, devices } from '@playwright/test'

// E2E suite assumes the backend is already running at http://localhost:8000
// with LLM_STUB=1 (or GEMINI_API_KEY=test) so responses are deterministic.
// The frontend dev server is managed by Playwright via webServer below.
//
// The backend must run on Postgres + pgvector, as CI does: SQLite cannot run
// pgvector's `<=>` vector search.
//
// Local run (bash; in PowerShell set each variable with $env:NAME='value'):
//   0) docker run -d --rm --name crux-e2e -p 55432:5432 -e POSTGRES_USER=crux \
//        -e POSTGRES_PASSWORD=crux -e POSTGRES_DB=crux_e2e pgvector/pgvector:pg17
//      (port 55432 avoids a native Postgres on 5432)
//   1) In frontend/: `node e2e/support/auth-keys.js`, then serve the JWKS:
//        python -m http.server 8787 --bind 127.0.0.1 --directory e2e/.auth/jwks
//      Specs sign in with e2e/support/auth.js, whose tokens the backend
//      verifies against this JWKS (#518).
//   2) In backend/, with these set:
//        DATABASE_URL=postgresql://crux:crux@localhost:55432/crux_e2e
//        CRUX_SKIP_DOTENV=1 LLM_STUB=1
//        SUPABASE_URL=http://e2e-auth.invalid
//        SUPABASE_JWKS_URL_OVERRIDE=http://127.0.0.1:8787/jwks.json
//      run `alembic upgrade head` (retry for a few seconds if the container
//      is still starting), then `uvicorn main:app --port 8000`
//   3) In frontend/: VITE_API_BASE_URL=http://localhost:8000/api npm run test:e2e

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
