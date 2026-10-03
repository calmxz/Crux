import { MIN_PASSWORD_LEN } from '../utils/validation.js'

// E-13: Supabase AuthErrors used to be surfaced by rendering `e.message`
// straight into the view. That leaks SDK/GoTrue prose ("Invalid login
// credentials", "For security purposes, you can only request this after 46
// seconds") in a voice that is not ours, and it made the login view sniff for
// the substring /not confirmed/i to decide whether to offer a resend.
//
// auth-js 2.112.3 puts a stable machine-readable `code` on every AuthError
// (type ErrorCode in node_modules/@supabase/auth-js/dist/module/lib/
// error-codes.d.ts), so key on that first, `status` second, and never on prose.
//
// Deliberately NOT routed through lib/errors.js friendlyError(): AuthErrors
// carry an HTTP status, so friendlyError would collapse every one of these into
// its generic status copy (constraint from commit 1d0f4aa).

// Same sentences as the corresponding branches in lib/errors.js, so an auth
// failure and an API failure of the same kind read identically. Kept as
// literals because errors.js does not export them.
const THROTTLED_COPY = 'Too many requests - wait a moment and retry.'

const SERVER_COPY = 'Something went wrong on our side. Try again shortly.'

export const AUTH_CODE_COPY = {
  invalid_credentials: 'That email and password do not match. Check both and try again.',
  email_not_confirmed: 'Confirm your email address first - check your inbox for the link.',
  user_already_exists: 'An account already exists for that email. Sign in instead.',
  email_exists: 'An account already exists for that email. Sign in instead.',
  weak_password: `That password is too weak. Use at least ${MIN_PASSWORD_LEN} characters.`,
  same_password: 'That is already your current password. Choose a different one.',
  otp_expired: 'That link has expired. Request a new one.',
  over_email_send_rate_limit: 'Too many emails sent. Wait a minute and try again.',
  over_request_rate_limit: THROTTLED_COPY,
  email_address_invalid: 'That email address is not valid. Check it and try again.',
  session_expired: 'Your session expired. Sign in again.',
}

/**
 * User-facing copy for a Supabase AuthError.
 *
 * @param {unknown} e the caught error
 * @param {string} fallback the view's own sentence for anything unrecognised
 * @returns {string}
 */
export function authErrorCopy(e, fallback) {
  const code = e && typeof e === 'object' ? e.code : null

  if (typeof code === 'string' && Object.hasOwn(AUTH_CODE_COPY, code)) {
    return AUTH_CODE_COPY[code]
  }

  const status = e && typeof e === 'object' ? e.status : null

  if (status === 429) return THROTTLED_COPY

  if (typeof status === 'number' && status >= 500) return SERVER_COPY

  return fallback
}

/**
 * Whether the sign-in failed only because the address is unconfirmed, which is
 * what gates the "resend confirmation" affordance. Replaces a /not confirmed/i
 * test against SDK prose.
 */
export function isEmailNotConfirmed(e) {
  return (e && typeof e === 'object' ? e.code : null) === 'email_not_confirmed'
}
