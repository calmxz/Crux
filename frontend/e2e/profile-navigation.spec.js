import { test, expect } from '@playwright/test'

import { signIn } from './support/auth.js'

// Runs against the real e2e backend (Postgres). The combined profile is reached
// from the sidebar, and a session's own profile from its topic card there.
test.describe('profile navigation', () => {
  test.beforeEach(async ({ context, page }) => {
    await context.clearCookies()
    await signIn(page)
  })

  test('home -> combined profile -> back; session -> session profile', async ({ page }) => {
    await page.goto('/')
    await page.getByTestId('onboarding-name').fill('Eddy')
    await page.getByTestId('onboarding-submit').click()
    await expect(page).toHaveURL(/\/$/)

    // Home -> Combined profile
    await page.getByTestId('sidebar-profile').first().click()
    await expect(page).toHaveURL(/\/profile$/)
    await expect(page.getByTestId('aggregate-profile')).toBeVisible()

    // Empty state on first run.
    await expect(page.getByTestId('aprof-empty')).toBeVisible()
    await page.goBack()
    await expect(page).toHaveURL(/\/$/)

    // Create a session and visit its per-session profile.
    await page.getByTestId('home-quick-topic').fill('Recursion')
    await page.getByTestId('home-quick-go').click()
    await expect(page).toHaveURL(/\/session\//)

    const sessionId = page.url().split('/session/')[1].split(/[?#]/)[0]

    await page.getByTestId('sidebar-profile').first().click()
    await page.getByTestId('aprof-topic-card').getByRole('link', { name: 'Open profile' }).click()
    await expect(page).toHaveURL(new RegExp(`/session/${sessionId}/profile$`))
    await expect(page.getByTestId('session-profile')).toBeVisible()
    await expect(page.getByTestId('sprof-mastered')).toBeVisible()
    await expect(page.getByTestId('sprof-gaps')).toBeVisible()
  })
})
