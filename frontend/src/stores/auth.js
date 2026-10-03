// Supabase auth state, exposed to the rest of the app as a Pinia store.
//
// - `init()` is called once at boot (main.js) before mount. After it
//   resolves, `ready === true` and the router guard can synchronously
//   read `isAuthenticated`.
// - `onAuthStateChange` keeps `session` in sync with sign-in / sign-out /
//   token-refresh events from the SDK.
// - Email + password sign-in is configured server-side. New accounts require
//   email confirmation; `resendConfirmation` re-sends the confirmation mail.

import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getSupabase } from '../services/supabase.js'
import { useUserStore } from './user.js'

export const useAuthStore = defineStore('auth', () => {
  const session = ref(null)
  const ready = ref(false)
  const _unsubscribe = ref(null)

  const userId = computed(() => session.value?.user?.id ?? null)
  const accessToken = computed(() => session.value?.access_token ?? null)
  const userEmail = computed(() => session.value?.user?.email ?? null)
  const isAuthenticated = computed(() => Boolean(session.value?.user?.id))

  async function init() {
    if (ready.value) return
    const sb = getSupabase()
    const { data } = await sb.auth.getSession()
    session.value = data?.session ?? null
    useUserStore().setActiveUser(session.value?.user?.id ?? null)

    const sub = sb.auth.onAuthStateChange((_event, sess) => {
      session.value = sess ?? null
      useUserStore().setActiveUser(sess?.user?.id ?? null)
    })

    _unsubscribe.value = sub?.data?.subscription?.unsubscribe ?? null
    ready.value = true
  }

  async function register(email, password) {
    const sb = getSupabase()

    const { data, error } = await sb.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: typeof window !== 'undefined' ? `${window.location.origin}/` : undefined,
        // F-52: consent travels as a verified JWT metadata claim; the backend
        // stamps accepted_terms_at only when it is present. The register form
        // cannot submit without the checkbox, so this is set iff consent.
        data: { accepted_terms: true },
      },
    })

    if (error) throw error

    return data
  }

  async function signIn(email, password) {
    const sb = getSupabase()
    const { error } = await sb.auth.signInWithPassword({ email, password })

    if (error) throw error
  }

  async function resendConfirmation(email) {
    const sb = getSupabase()
    const { error } = await sb.auth.resend({ type: 'signup', email })

    if (error) throw error
  }

  async function requestPasswordReset(email) {
    const sb = getSupabase()

    const { error } = await sb.auth.resetPasswordForEmail(email, {
      redirectTo:
        typeof window !== 'undefined' ? `${window.location.origin}/reset-password` : undefined,
    })

    if (error) throw error
  }

  async function updatePassword(password) {
    const sb = getSupabase()
    const { error } = await sb.auth.updateUser({ password })

    if (error) throw error
  }

  async function signOut() {
    const sb = getSupabase()

    try {
      const { error } = await sb.auth.signOut()

      if (error) throw error
    } finally {
      // Clear local session even when the SDK call throws (network drop,
      // already-revoked token, etc). Otherwise the router guard's stale
      // isAuthenticated bounces /login back to home and re-hydrates /me,
      // recreating a users row for an account that just tried to sign out.
      session.value = null
      // Belt-and-braces: the SIGNED_OUT event from onAuthStateChange also
      // clears the user store; setActiveUser(null) is idempotent.
      useUserStore().setActiveUser(null)
    }
  }

  function _resetForTests() {
    session.value = null
    ready.value = false

    if (typeof _unsubscribe.value === 'function') _unsubscribe.value()
    _unsubscribe.value = null
  }

  return {
    session,
    ready,
    userId,
    accessToken,
    userEmail,
    isAuthenticated,
    init,
    register,
    signIn,
    resendConfirmation,
    requestPasswordReset,
    updatePassword,
    signOut,
    _resetForTests,
  }
})
