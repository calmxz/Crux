import { test, expect } from '@playwright/test'

import { signIn } from './support/auth.js'

// Runs against the real e2e backend (Postgres, LLM_STUB=1): onboarding writes
// the users row, the quick start creates a session, and the stub reply is
// read back from the persisted transcript.
test.describe('onboarding to chat', () => {
  test.beforeEach(async ({ context, page }) => {
    await context.clearCookies()
    await signIn(page)
  })

  test('completes onboarding, creates fresh session, sends message, gets stub reply', async ({
    page,
  }) => {
    await page.goto('/')

    // Router guard should bounce / -> /onboarding for a new user.
    await expect(page).toHaveURL(/\/onboarding$/)
    await expect(page.getByText('Welcome to Crux')).toBeVisible()

    await page.getByTestId('onboarding-name').fill('Eddy')
    await page.getByTestId('onboarding-submit').click()

    await expect(page).toHaveURL(/\/$/)
    // A new account has no sessions yet.
    await expect(page.getByTestId('sidebar-empty-hint')).toBeVisible()

    // The /new page was folded into Home's quick-start card.
    await page.getByTestId('home-quick-topic').fill('Recursion')
    await page.getByTestId('home-quick-go').click()

    await expect(page).toHaveURL(/\/session\//)
    await expect(page.getByTestId('session-input')).toBeVisible()

    await page.getByTestId('session-input').fill('what is recursion?')
    await page.getByTestId('session-send').click()

    const assistant = page.getByTestId('msg-assistant').last()
    await expect(assistant).toBeVisible()
    await expect(assistant).toContainText('[STUB:fresh]')
    await expect(assistant).toContainText('what is recursion?')

    // The turn was written to Postgres: a reload reads it back from the API.
    await page.reload()
    await expect(page.getByTestId('msg-assistant').last()).toContainText('[STUB:fresh]')
  })
})
