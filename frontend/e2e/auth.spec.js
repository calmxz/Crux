// Email/password auth gate (Phase 7, rewritten for the email/password
// migration that replaced the magic-link OTP flow).
//
// Flows exercised end-to-end against the real app bundle, offline via
// `page.route` stubbing of Supabase GoTrue endpoints:
//   1) Unauthenticated visit to a protected route is redirected to /login.
//   2) /login gates submit until a valid email AND a password are present.
//   3) A rejected password sign-in surfaces the error banner.
//   4) /register surfaces the "check your inbox" confirmation after sign-up.
//
// The Supabase client reads VITE_SUPABASE_URL at bundle time. If that env
// var is unset, the app constructs a stub client against
// `http://placeholder.invalid` — the routes below match either host.
import { test, expect } from '@playwright/test'

test.describe('auth gate', () => {
  test.beforeEach(async ({ context, page }) => {
    await context.clearCookies()
    await context.addInitScript(() => {
      try {
        localStorage.clear()
        sessionStorage.clear()
      } catch {
        /* about:blank / isolated contexts can throw SecurityError */
      }
    })

    // Some Supabase JS versions probe /auth/v1/settings on init; return a
    // permissive payload so the client doesn't error out before our flow runs.
    await page.route('**/auth/v1/settings**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ external: {}, mfa: {}, disable_signup: false }),
      })
    })
  })

  test('unauthenticated visit to / is redirected to /login', async ({ page }) => {
    await page.goto('/')
    // F-49: the guard carries the intended path so a deep link survives login.
    await expect(page).toHaveURL(/\/login\?redirect=/)
    await expect(page.getByTestId('login-form')).toBeVisible()
  })

  test('login form disables submit until email and password are valid', async ({ page }) => {
    await page.goto('/login')
    const submit = page.getByTestId('login-submit')
    await expect(submit).toBeDisabled()

    await page.getByTestId('login-email').fill('not-an-email')
    await expect(submit).toBeDisabled()

    // Valid email alone is not enough; the password is still empty.
    await page.getByTestId('login-email').fill('me@example.com')
    await expect(submit).toBeDisabled()

    await page.getByTestId('login-password').fill('hunter2pw')
    await expect(submit).toBeEnabled()
  })

  test('a rejected sign-in shows the error banner', async ({ page }) => {
    // Stub the password grant endpoint to reject the credentials. GoTrue
    // returns an OAuth-style error body for grant_type=password.
    await page.route('**/auth/v1/token**', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        // GoTrue also sends `error_code`, which auth-js surfaces as
        // AuthError.code. E-13 keys the banner copy on that code, never on
        // the SDK prose in error_description.
        body: JSON.stringify({
          error: 'invalid_grant',
          error_code: 'invalid_credentials',
          error_description: 'Invalid login credentials',
        }),
      })
    })

    await page.goto('/login')
    await page.getByTestId('login-email').fill('me@example.com')
    await page.getByTestId('login-password').fill('wrongpass')
    await page.getByTestId('login-submit').click()

    await expect(page.getByTestId('login-error')).toBeVisible()
    await expect(page.getByTestId('login-error')).toContainText(
      'That email and password do not match',
    )
    await expect(page.getByTestId('login-error')).not.toContainText('Invalid login credentials')
  })

  test('registering shows the check-your-inbox confirmation', async ({ page }) => {
    // Stub sign-up to succeed without a session, which is what GoTrue returns
    // when email confirmation is required (no access_token => no auto sign-in).
    await page.route('**/auth/v1/signup**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'user-1',
          email: 'me@example.com',
          confirmation_sent_at: '2026-01-01T00:00:00Z',
        }),
      })
    })

    await page.goto('/register')
    await page.getByTestId('register-email').fill('me@example.com')
    await page.getByTestId('register-password').fill('hunter2pw')
    await page.getByTestId('register-confirm').fill('hunter2pw')
    await page.getByTestId('register-consent').check()
    await page.getByTestId('register-submit').click()

    await expect(page.getByTestId('register-sent')).toBeVisible()
    await expect(page.getByTestId('register-sent')).toContainText('me@example.com')
  })

  test('requesting a password reset shows the sent confirmation', async ({ page }) => {
    // Stub the recover endpoint so the flow runs offline.
    await page.route('**/auth/v1/recover**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({}),
      })
    })

    await page.goto('/forgot')
    await page.getByTestId('forgot-email').fill('me@example.com')
    await page.getByTestId('forgot-submit').click()

    await expect(page.getByTestId('forgot-sent')).toBeVisible()
    await expect(page.getByTestId('forgot-sent')).toContainText('me@example.com')
  })
})
