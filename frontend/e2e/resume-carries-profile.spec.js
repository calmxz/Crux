import { test, expect } from '@playwright/test'

import { signIn } from './support/auth.js'

// Runs against the real e2e backend (Postgres, LLM_STUB=1).
test.describe('resume carries profile', () => {
  test.beforeEach(async ({ context, page }) => {
    await context.clearCookies()
    await signIn(page)
  })

  test('continue topic from library carries profile into a new session', async ({ page }) => {
    const topic = `Recursion-${Date.now()}`

    // Onboarding.
    await page.goto('/')
    await page.getByTestId('onboarding-submit').click()
    await expect(page).toHaveURL(/\/$/)

    // Session A: fresh, via Home's quick-start card (home-new-session /
    // /new flow was replaced by the single-input quick card).
    await page.getByTestId('home-quick-topic').fill(topic)
    await page.getByTestId('home-quick-go').click()
    await expect(page).toHaveURL(/\/session\//)

    // Capture session id from the URL so we can await its end request and
    // target the library's Continue-topic button for it later.
    const sessionId = page.url().split('/session/')[1].split(/[?#]/)[0]

    await page.getByTestId('session-input').fill('teach me base cases')
    await page.getByTestId('session-send').click()
    await expect(page.getByTestId('msg-assistant').last()).toContainText('[STUB:fresh]')

    // End session A through its sidebar row menu. Awaits the end-of-session
    // summary synchronously and persists it onto
    // topic_profile.last_session_summary.
    // Start waiting for the end-session request before clicking: the click
    // resolves on event dispatch, not on the async handler, and the
    // subsequent page.goto is a full-page navigation that would abort an
    // in-flight fetch. Without this wait the request can be cut short, so
    // session A never persists as ended and the Ended-library assertions
    // below flake (see backend/routes/sessions.py POST /sessions/{id}/end).
    const endResponse = page.waitForResponse(
      (r) => r.url().includes(`/sessions/${sessionId}/end`) && r.ok(),
    )

    const row = page.getByTestId(`sidebar-row-${sessionId}`)

    await row.hover()
    await row.getByTestId('sidebar-row-menu-trigger').click()
    await page.getByTestId('sidebar-row-menu-end').click()
    // E-12: End now sits behind a PrimeVue confirm dialog (same contract as
    // file delete); the request only fires on the destructive accept.
    await page.locator('.p-confirmdialog button.confirm-delete-strong').click()
    await endResponse

    // Continue topic from the Sessions library, Ended filter.
    await page.goto('/sessions')
    await page.getByTestId('library-filter-ended').click()
    await page.getByTestId(`library-continue-${sessionId}`).click()

    // A brand-new session (seed_mode=resume, priorSessionId=A) is created;
    // the URL must not still point at ended session A.
    await expect(page).toHaveURL(/\/session\//)
    await expect(page).not.toHaveURL(new RegExp(`/session/${sessionId}$`))

    await page.getByTestId('session-input').fill('continue')
    await page.getByTestId('session-send').click()

    // Continue-topic carries session A's last_session_summary into session
    // B's profile. The stub emits "[STUB:resumed:<hash8>]" whenever a
    // LAST_SESSION_SUMMARY line is present in the assembled system prompt
    // (backend/agent/_stub.py), which is the resumed-profile signal this
    // spec asserts on.
    const assistant = page.getByTestId('msg-assistant').last()
    await expect(assistant).toBeVisible()
    await expect(assistant).toContainText('[STUB:resumed:')
  })
})
