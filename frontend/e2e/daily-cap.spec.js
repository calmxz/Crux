import { test, expect } from '@playwright/test'

// TODO(phase-8): rebuild e2e harness for Phase 7 auth + Postgres. Spec assumes
// pre-auth flow (no /login gate), removed in Phase 7. e2e.yml runs on Postgres
// since #434; restore once an auth session seeding helper lands.
test.describe.skip('daily cap UI', () => {
  test.beforeEach(async ({ context }) => {
    await context.clearCookies()
    await context.addInitScript(() => {
      try {
        localStorage.clear()
      } catch {
        // ignore
      }
    })
  })

  test('429 daily_cap_reached locks the composer and shows banner', async ({ page }) => {
    // Onboard + create a session normally so the backend session row exists.
    await page.goto('/')
    await page.getByTestId('onboarding-name').fill('Eddy')
    await page.getByTestId('onboarding-submit').click()
    await page.getByTestId('home-new-session').click()
    await page.getByTestId('new-topic').fill('Cap demo')
    await page.getByTestId('new-submit').click()
    await expect(page).toHaveURL(/\/session\//)

    // Intercept /api/chat to simulate the 429 envelope the backend returns
    // when the daily cap is reached.
    await page.route('**/api/chat', async (route) => {
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: {
            code: 'daily_cap_reached',
            cap: 2,
            used: 2,
            resets_at: '2099-01-01T00:00:00+00:00',
          },
        }),
      })
    })

    await page.getByTestId('session-input').fill('one more please')
    await page.getByTestId('session-send').click()

    await expect(page.getByTestId('session-cap-banner')).toBeVisible()
    await expect(page.getByTestId('session-cap-banner')).toContainText('Daily limit reached')

    // Composer becomes unusable after the cap fires.
    await expect(page.getByTestId('session-input')).toBeDisabled()
    await expect(page.getByTestId('session-send')).toBeDisabled()
  })
})
