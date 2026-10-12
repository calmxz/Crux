import { test, expect } from '@playwright/test'

import { signIn } from './support/auth.js'

// Runs against the real e2e backend with LLM_STUB=1, so /chat/stream emits
// deterministic chunked deltas.
test.describe('chat stream', () => {
  test.beforeEach(async ({ context, page }) => {
    await context.clearCookies()
    await signIn(page)
  })

  async function openFreshSession(page, topic) {
    await page.goto('/')
    await expect(page).toHaveURL(/\/onboarding$/)
    await page.getByTestId('onboarding-name').fill('Eddy')
    await page.getByTestId('onboarding-submit').click()

    await expect(page).toHaveURL(/\/$/)
    await page.getByTestId('home-quick-topic').fill(topic)
    await page.getByTestId('home-quick-go').click()
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

    // The stub LLM emits its whole reply at once, so on a fast runner the
    // stream ends before Stop can be clicked. Hold the request open until the
    // client aborts it: a handler that never answers keeps the turn mid-stream.
    await page.route('**/api/chat/stream', () => {})

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
