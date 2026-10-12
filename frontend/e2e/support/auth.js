// #518: sign a fresh test user in, for specs that talk to the real e2e backend.
//
// GoTrue is stubbed with page.route as in auth.spec.js, but the access token it
// hands out is a real RS256 JWT signed with the key from auth-keys.js, so the
// backend verifies it against the JWKS the e2e job serves and every /api call
// runs authenticated against Postgres.
import { createSign, randomUUID } from 'node:crypto'
import { expect } from '@playwright/test'

import { ISSUER_ORIGIN, readSigningKey } from './auth-keys.js'

const API_BASE_URL = process.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

const b64url = (value) => Buffer.from(value).toString('base64url')

function signAccessToken(claims) {
  const { kid, privateKey } = readSigningKey()
  const header = b64url(JSON.stringify({ alg: 'RS256', typ: 'JWT', kid }))
  const payload = b64url(JSON.stringify(claims))
  const signer = createSign('RSA-SHA256')
  signer.update(`${header}.${payload}`)
  const signature = signer.sign(privateKey).toString('base64url')

  return `${header}.${payload}.${signature}`
}

function json(route, body) {
  return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
}

/**
 * Sign a brand-new user in through the real /login form and wait to leave it.
 * Each call mints a new user id, so every test starts with an empty account
 * (no sessions, onboarding not done). Returns the user id.
 *
 * Do not pair it with an addInitScript storage wipe: that re-runs on every
 * navigation and drops the supabase-js session this sign-in persists.
 */
export async function signIn(page) {
  const userId = randomUUID()
  const email = `e2e-${userId}@example.com`
  const now = Math.floor(Date.now() / 1000)
  // The register form's consent claim (F-52), as a real signup carries it.
  const userMetadata = { accepted_terms: true }

  const accessToken = signAccessToken({
    sub: userId,
    aud: 'authenticated',
    role: 'authenticated',
    iss: `${ISSUER_ORIGIN}/auth/v1`,
    email,
    user_metadata: userMetadata,
    iat: now,
    exp: now + 3600,
  })

  // Fail here, by name, if the backend rejects the token (stale key, issuer
  // mismatch, JWKS not served). Otherwise the stubbed login still succeeds and
  // the spec times out later on an unrelated locator.
  const me = await page.request.get(`${API_BASE_URL}/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })

  if (!me.ok()) {
    throw new Error(
      `e2e backend rejected the signIn token: ${me.status()} ${await me.text()}. ` +
        'Check the served JWKS and that SUPABASE_URL matches ISSUER_ORIGIN.',
    )
  }

  const user = {
    id: userId,
    aud: 'authenticated',
    role: 'authenticated',
    email,
    app_metadata: {},
    user_metadata: userMetadata,
    created_at: new Date(now * 1000).toISOString(),
  }

  await page.route('**/auth/v1/settings**', (route) =>
    json(route, { external: {}, mfa: {}, disable_signup: false }),
  )
  await page.route('**/auth/v1/token**', (route) =>
    json(route, {
      access_token: accessToken,
      token_type: 'bearer',
      expires_in: 3600,
      expires_at: now + 3600,
      refresh_token: 'e2e-refresh-token',
      user,
    }),
  )
  await page.route('**/auth/v1/user**', (route) => json(route, user))

  await page.goto('/login')
  await page.getByTestId('login-email').fill(email)
  await page.getByTestId('login-password').fill('e2e-password')
  await page.getByTestId('login-submit').click()
  await expect(page).not.toHaveURL(/\/login/)

  return userId
}
