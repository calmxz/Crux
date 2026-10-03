import { test, expect } from '@playwright/test'

// TODO(phase-8): rebuild e2e harness for Phase 7 auth + Postgres. The app now
// redirects unauthenticated visits to /login (see auth.spec.js), and no
// auth-session-seeding helper exists yet to get a Playwright session past that
// gate, so the onboarding step below times out. Skipped to match every other
// content-flow spec in this folder (onboarding-to-chat, chat-stream, etc.),
// which are skipped for the identical reason. The flow/assertions here target
// the roadmap-slice3 Continue-topic path and are ready the moment the seeding
// helper + Postgres service in e2e.yml land — un-skip then.
test.describe.skip('resume carries profile', () => {
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

    // Capture session id from the URL so we can target the sidebar row and
    // the library's Continue-topic button for it later.
    const sessionId = page.url().split('/session/')[1].split(/[?#]/)[0]

    await page.getByTestId('session-input').fill('teach me base cases')
    await page.getByTestId('session-send').click()
    await expect(page.getByTestId('msg-assistant').last()).toContainText('[STUB:fresh]')

    // End session A via the sidebar row's overflow menu (ticket 10 also added
    // an in-page End control on SessionView itself, but the row menu exercises
    // the same shared useSessionActions.confirmEnd path). Awaits the
    // end-of-session summary synchronously and persists it onto
    // topic_profile.last_session_summary.
    await page
      .locator(`[data-session-id="${sessionId}"] [data-testid="sidebar-row-menu-trigger"]`)
      .click()

    // Start waiting for the end-session request before clicking: the click
    // resolves on event dispatch, not on the async handler, and the
    // subsequent page.goto is a full-page navigation that would abort an
    // in-flight fetch. Without this wait the request can be cut short, so
    // session A never persists as ended and the Ended-library assertions
    // below flake (see backend/routes/sessions.py POST /sessions/{id}/end).
    const endResponse = page.waitForResponse(
      (r) => r.url().includes(`/sessions/${sessionId}/end`) && r.ok(),
    )

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
