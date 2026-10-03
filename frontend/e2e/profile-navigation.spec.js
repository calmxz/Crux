import { test, expect } from '@playwright/test'

// TODO(phase-8): rebuild e2e harness for Phase 7 auth + Postgres. Spec assumes
// pre-auth flow (no /login gate) and SQLite backend; both removed in Phase 7.
// Restore once auth session seeding helper + Postgres service in e2e.yml land.
test.describe.skip('profile navigation', () => {
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

  test('home -> combined profile -> back; session -> session profile', async ({ page }) => {
    await page.goto('/')
    await page.getByTestId('onboarding-name').fill('Eddy')
    await page.getByTestId('onboarding-submit').click()
    await expect(page).toHaveURL(/\/$/)

    // Home -> Combined profile
    await page.getByTestId('home-profile-link').click()
    await expect(page).toHaveURL(/\/profile$/)
    await expect(page.getByTestId('agg-learning')).toBeVisible()

    // Empty state on first run.
    await expect(page.getByTestId('agg-empty')).toBeVisible()
    await page.getByTestId('back-button').click()
    await expect(page).toHaveURL(/\/$/)

    // Create a session and visit its per-session profile.
    await page.getByTestId('home-new-session').click()
    await page.getByTestId('new-topic').fill('Recursion')
    await page.getByTestId('new-submit').click()
    await expect(page).toHaveURL(/\/session\//)

    const sessionId = page.url().split('/session/')[1].split(/[?#]/)[0]

    await page.getByTestId('session-profile-link').click()
    await expect(page).toHaveURL(new RegExp(`/session/${sessionId}/profile$`))
    await expect(page.getByTestId('session-profile')).toBeVisible()
    await expect(page.getByTestId('sprof-mastered')).toBeVisible()
    await expect(page.getByTestId('sprof-gaps')).toBeVisible()
  })
})
