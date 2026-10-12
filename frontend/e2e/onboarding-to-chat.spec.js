import { test, expect } from '@playwright/test'

// TODO(phase-8): rebuild e2e harness for Phase 7 auth + Postgres. Spec assumes
// pre-auth flow (no /login gate), removed in Phase 7. e2e.yml runs on Postgres
// since #434; restore once an auth session seeding helper lands.
test.describe.skip('onboarding to chat', () => {
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

  test('completes onboarding, creates fresh session, sends message, gets stub reply', async ({
    page,
  }) => {
    await page.goto('/')

    // Router guard should bounce / -> /onboarding for unauth'd user.
    await expect(page).toHaveURL(/\/onboarding$/)
    await expect(page.getByText('Welcome to Crux')).toBeVisible()

    await page.getByTestId('onboarding-name').fill('Eddy')
    await page.getByTestId('onboarding-submit').click()

    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByTestId('home-empty-active')).toBeVisible()

    await page.getByTestId('home-new-session').click()
    await expect(page).toHaveURL(/\/new$/)

    await page.getByTestId('new-topic').fill('Recursion')
    await page.getByTestId('new-submit').click()

    await expect(page).toHaveURL(/\/session\//)
    await expect(page.getByTestId('session-input')).toBeVisible()

    await page.getByTestId('session-input').fill('what is recursion?')
    await page.getByTestId('session-send').click()

    const assistant = page.getByTestId('msg-assistant').last()
    await expect(assistant).toBeVisible()
    await expect(assistant).toContainText('[STUB:fresh]')
    await expect(assistant).toContainText('what is recursion?')
  })
})
