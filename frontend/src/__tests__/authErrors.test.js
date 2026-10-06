import { describe, it, expect } from 'vitest'

import { authErrorCopy, isEmailNotConfirmed, AUTH_CODE_COPY } from '@/lib/authErrors.js'

// Shape of a real auth-js AuthError: prose message + machine-readable code +
// HTTP status. The prose is deliberately something we must never render.
function authError(code, status = 400, message = 'raw gotrue prose') {
  return Object.assign(new Error(message), { code, status, name: 'AuthApiError' })
}

const FALLBACK = 'Could not sign in. Try again.'

describe('authErrorCopy', () => {
  it.each([
    'invalid_credentials',
    'email_not_confirmed',
    'user_already_exists',
    'email_exists',
    'weak_password',
    'same_password',
    'otp_expired',
    'over_email_send_rate_limit',
    'over_request_rate_limit',
    'email_address_invalid',
    'session_expired',
  ])('maps %s to its own copy', (code) => {
    expect(authErrorCopy(authError(code), FALLBACK)).toBe(AUTH_CODE_COPY[code])
  })

  it('prefers the code over the status', () => {
    // 429 would otherwise win; the more specific code must.
    expect(authErrorCopy(authError('over_email_send_rate_limit', 429), FALLBACK)).toBe(
      AUTH_CODE_COPY.over_email_send_rate_limit,
    )
  })

  it('never renders the SDK prose', () => {
    const e = authError('invalid_credentials', 400, 'Invalid login credentials')
    expect(authErrorCopy(e, FALLBACK)).not.toContain('Invalid login credentials')
  })

  it('falls back to throttled copy on a 429 with an unknown code', () => {
    expect(authErrorCopy(authError('something_new', 429), FALLBACK)).toMatch(/too many requests/i)
  })

  it.each([500, 502, 503])('falls back to generic server copy on %i', (status) => {
    expect(authErrorCopy(authError('something_new', status), FALLBACK)).toMatch(/on our side/i)
  })

  it('uses the view fallback for an unknown code on a 4xx', () => {
    expect(authErrorCopy(authError('something_new', 400), FALLBACK)).toBe(FALLBACK)
  })

  it('uses the view fallback for a plain Error with no code or status', () => {
    expect(authErrorCopy(new Error('boom'), FALLBACK)).toBe(FALLBACK)
  })

  it.each([null, undefined, 'a string', 42])('uses the view fallback for %p', (e) => {
    expect(authErrorCopy(e, FALLBACK)).toBe(FALLBACK)
  })

  it('states the real minimum for weak_password', () => {
    expect(AUTH_CODE_COPY.weak_password).toContain('8 characters')
  })

  it('carries no exclamation marks', () => {
    for (const copy of Object.values(AUTH_CODE_COPY)) expect(copy).not.toContain('!')
  })
})

describe('isEmailNotConfirmed', () => {
  it('is true only for the email_not_confirmed code', () => {
    expect(isEmailNotConfirmed(authError('email_not_confirmed'))).toBe(true)
    expect(isEmailNotConfirmed(authError('invalid_credentials'))).toBe(false)
  })

  it('does not sniff prose', () => {
    // The old implementation tested /not confirmed/i against e.message.
    expect(isEmailNotConfirmed(new Error('Email not confirmed'))).toBe(false)
  })

  it.each([null, undefined, 'a string'])('is false for %p', (e) => {
    expect(isEmailNotConfirmed(e)).toBe(false)
  })
})
