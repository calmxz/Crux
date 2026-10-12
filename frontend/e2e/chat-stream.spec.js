import { test, expect } from '@playwright/test'

// TODO(phase-8): rebuild e2e harness for Phase 7 auth + Postgres. Like the other
// specs in this folder, this one assumes the pre-auth flow (no /login gate) and a
// seeded session, which needs an auth-session seeding helper (e2e.yml runs on
// Postgres since #434). Un-skip once that lands.
//
// Also assumes the backend runs with LLM_STUB=1 so /chat/stream emits
// deterministic chunked deltas.
test.describe.skip('chat stream', () => {
  test.beforeEach(async ({ context }) => {
    await context.clearCookies()
    await context.addInitScript(() => {
      try {
        localStorage.clear()
      } catch {
        // Ignore SecurityErrors on isolated/about:blank pages.
      }
    })
  })

  async function openFreshSession(page, topic) {
    await page.goto('/')
    await expect(page).toHaveURL(/\/onboarding$/)
    await page.getByTestId('onboarding-name').fill('Eddy')
    await page.getByTestId('onboarding-submit').click()

    await expect(page).toHaveURL(/\/$/)
    await page.getByTestId('home-new-session').click()
    await expect(page).toHaveURL(/\/new$/)

    await page.getByTestId('new-topic').fill(topic)
    await page.getByTestId('new-submit').click()
    await expect(page).toHaveURL(/\/session\//)
    await expect(page.getByTestId('session-input')).toBeVisible()
  }

  test('renders a streamed assistant reply', async ({ page }) => {
    await openFreshSession(page, 'Big-O')

    await page.getByTestId('session-input').fill('Explain Big-O in two sentences')
    await page.getByTestId('session-send').click()

    // The streaming bubble appears first (msg-streaming), then finalizes into a
    // persisted assistant bubble (msg-assistant). Assert the finalized reply has
    // rendered, non-empty content.
    const assistant = page.getByTestId('msg-assistant').last()
    await expect(assistant).toBeVisible({ timeout: 30_000 })
    await expect(assistant).not.toBeEmpty()
  })

  test('Stop button cancels mid-stream and shows the (stopped) marker', async ({ page }) => {
    await openFreshSession(page, 'Operating systems')

    await page.getByTestId('session-input').fill('Write a long essay on operating systems history')
    await page.getByTestId('session-send').click()

    // While streaming, Send is swapped for Stop.
    const stop = page.getByTestId('session-stop')
    await expect(stop).toBeVisible({ timeout: 5_000 })
    await stop.click()

    // The cancelled assistant message persists with the (stopped) marker.
    await expect(page.locator('.cancelled-marker')).toBeVisible({ timeout: 5_000 })
    await expect(page.locator('.cancelled-marker')).toContainText('stopped')
  })
})
