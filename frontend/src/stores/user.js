import { ref } from 'vue'
import { defineStore } from 'pinia'

import { useSessionStore } from './session.js'
import { apiGet, apiPatch } from '../services/apiClient.js'
import { TUTOR_PREFERENCES } from '../lib/tutorPreferences.js'

// Phase 7+: identity comes from `useAuthStore` (Supabase JWT). This store
// only persists local UX preferences -- name + tutor preferences (feedback
// style, check-ins, reply length) + onboarding completion -- in a
// localStorage entry namespaced by Supabase userId so two accounts on one
// browser never share prefs (F-08).

const STORAGE_PREFIX = 'crux:user:v1'

// interactionPreferences key -> /api/me field, from the shared tutor
// preferences. Hydration and updateProfile both read this.
const PREF_FIELDS = Object.fromEntries(
  Object.entries(TUTOR_PREFERENCES).map(([key, { field }]) => [key, field]),
)

export const useUserStore = defineStore('user', () => {
  const name = ref(null)
  const interactionPreferences = ref(null)
  const onboardingComplete = ref(false)
  // Supabase uid the in-memory state belongs to; null = signed out.
  const activeUserId = ref(null)
  // F-46: whether hydrateFromServer has completed (success or failure) for
  // the current active user. The router guard awaits one hydrate before
  // trusting onboardingComplete, so a new device doesn't get force-routed
  // through onboarding off a stale/absent localStorage snapshot.
  const hydrated = ref(false)
  // E-09: distinguishes "hydrate ran and the server said onboarding is
  // incomplete" from "hydrate could not reach the server at all". The router
  // guard must not force-route into onboarding on the latter -- that would
  // trap a user with no local snapshot and no way to reach the app.
  const hydrateFailed = ref(false)

  function _storageKey() {
    return `${STORAGE_PREFIX}:${activeUserId.value}`
  }

  function _clearInMemory() {
    name.value = null
    interactionPreferences.value = null
    onboardingComplete.value = false
    hydrated.value = false
    hydrateFailed.value = false
  }

  function setActiveUser(uid) {
    const next = uid ?? null

    if (next === activeUserId.value) return
    activeUserId.value = next
    _clearInMemory()
    // F-02: an account switch (or sign-out) must not leave the previous
    // user's sessions/messages/profile state readable by the next account
    // on the same tab. Token refreshes hit the same-uid early return above.
    useSessionStore().reset()

    if (next) loadFromLocalStorage()
  }

  function loadFromLocalStorage() {
    if (typeof localStorage === 'undefined' || !activeUserId.value) return
    const raw = localStorage.getItem(_storageKey())

    if (!raw) return

    try {
      const data = JSON.parse(raw)
      name.value = data.name ?? null
      interactionPreferences.value = data.interactionPreferences ?? null
      onboardingComplete.value = Boolean(data.onboardingComplete)
    } catch {
      localStorage.removeItem(_storageKey())
    }
  }

  function persist() {
    if (typeof localStorage === 'undefined' || !activeUserId.value) return
    localStorage.setItem(
      _storageKey(),
      JSON.stringify({
        name: name.value,
        interactionPreferences: interactionPreferences.value,
        onboardingComplete: onboardingComplete.value,
      }),
    )
  }

  // F-46: server is authoritative for onboarding state; localStorage is a
  // warm cache only. A failed hydrate (offline / API down) keeps whatever
  // localStorage already loaded rather than blocking the app.
  async function hydrateFromServer() {
    if (!activeUserId.value) return
    hydrateFailed.value = false

    try {
      const me = await apiGet('/me', undefined, { silent: true })

      if (me) {
        if (me.display_name != null) name.value = me.display_name
        const prefs = {}

        for (const [key, field] of Object.entries(PREF_FIELDS)) {
          if (me[field] != null) prefs[key] = me[field]
        }

        if (Object.keys(prefs).length) {
          interactionPreferences.value = { ...interactionPreferences.value, ...prefs }
        }

        onboardingComplete.value = Boolean(me.onboarding_complete)
        persist()
      }
    } catch {
      // Offline / API down: keep the localStorage snapshot already loaded.
      hydrateFailed.value = true
    } finally {
      hydrated.value = true
    }
  }

  async function completeOnboarding({ name: displayName, feedback }) {
    const finalName = displayName?.trim() || 'Learner'
    await apiPatch('/me', {
      display_name: finalName,
      feedback_pref: feedback,
      onboarding_complete: true,
    })
    name.value = finalName
    // Merge, not replace: a hydrated check-ins / reply-length choice survives.
    interactionPreferences.value = { ...interactionPreferences.value, feedback }
    onboardingComplete.value = true
    persist()
  }

  function resetOnboarding() {
    _clearInMemory()

    if (typeof localStorage !== 'undefined' && activeUserId.value) {
      localStorage.removeItem(_storageKey())
    }
  }

  // R2-25: called right after DELETE /me succeeds, before authStore.signOut().
  // Wipes the in-memory state AND removes the persisted localStorage snapshot
  // for this account -- signOut alone (setActiveUser(null)) clears memory but
  // leaves the storage key behind, so a later sign-in on the same browser
  // (same uid resurrected, or reused by a new account) must not read the
  // deleted user's name/onboarding flags back out of localStorage.
  //
  // Body is identical to resetOnboarding(); it keeps its own name because the
  // call site's intent (post-delete wipe vs. onboarding restart) is what a
  // reader needs, not the mechanism.
  function clearForAccountDeletion() {
    resetOnboarding()
  }

  // Sends only the fields given, so each Learning-tab control's autosave is a
  // single-field PATCH that never overwrites the others (#357).
  async function updateProfile({ name: displayName, ...changes }) {
    const body = {}
    const prefs = {}

    if (displayName != null) body.display_name = displayName.trim() || 'Learner'

    for (const [key, field] of Object.entries(PREF_FIELDS)) {
      if (changes[key] != null) {
        body[field] = changes[key]
        prefs[key] = changes[key]
      }
    }

    if (Object.keys(body).length) {
      await apiPatch('/me', body)
    }

    if (displayName != null) name.value = displayName.trim() || 'Learner'

    if (Object.keys(prefs).length) {
      interactionPreferences.value = { ...interactionPreferences.value, ...prefs }
    }

    persist()
  }

  return {
    name,
    interactionPreferences,
    onboardingComplete,
    activeUserId,
    hydrated,
    hydrateFailed,
    setActiveUser,
    loadFromLocalStorage,
    hydrateFromServer,
    completeOnboarding,
    resetOnboarding,
    clearForAccountDeletion,
    updateProfile,
  }
})
