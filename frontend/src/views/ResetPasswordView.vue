<template>
  <AuthCover
    title="Set a new password"
    :lede="
      hasRecovery
        ? 'Choose a new password for your account.'
        : 'Reset links work once and expire after an hour.'
    "
  >
    <form v-if="hasRecovery" class="form" data-testid="reset-form" @submit.prevent="submit">
      <div class="field">
        <label for="password" class="field-label">New password</label>
        <div class="field-line">
          <InputText
            id="password"
            v-model="password"
            type="password"
            data-testid="reset-password"
            autocomplete="new-password"
            placeholder="At least 8 characters"
            required
            class="field-input"
          />
        </div>
      </div>

      <div class="field">
        <label for="confirm" class="field-label">Confirm new password</label>
        <div class="field-line">
          <InputText
            id="confirm"
            v-model="confirm"
            type="password"
            data-testid="reset-confirm"
            autocomplete="new-password"
            placeholder="Re-enter password"
            required
            class="field-input"
          />
        </div>
      </div>

      <p v-if="mismatch" class="field-error" data-testid="reset-mismatch">
        Passwords do not match.
      </p>
      <p v-if="error" class="status is-alert" role="alert" data-testid="reset-error">
        {{ error }}
      </p>
      <p v-if="error" class="line">
        Link expired?
        <RouterLink class="link" to="/forgot" data-testid="reset-to-forgot"
          >Request a new one</RouterLink
        >
      </p>

      <div class="actions">
        <button
          type="submit"
          class="cta"
          data-testid="reset-submit"
          :disabled="!canSubmit || submitting"
        >
          <span>{{ submitting ? 'Updating…' : 'Update password' }}</span>
          <svg
            class="cta-arrow"
            viewBox="0 0 20 20"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
            focusable="false"
          >
            <path d="M3.5 10 L16.5 10" />
            <path d="M11 4.5 L16.5 10 L11 15.5" />
          </svg>
        </button>
      </div>
    </form>

    <div v-else class="form" data-testid="reset-no-session">
      <p class="status is-alert" role="alert">This reset link is invalid or has expired.</p>
      <p class="line">
        <RouterLink class="link" to="/forgot" data-testid="reset-to-forgot"
          >Request a new one</RouterLink
        >
      </p>
    </div>
  </AuthCover>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import InputText from 'primevue/inputtext'

import AuthCover from '../components/auth/AuthCover.vue'
import { authErrorCopy } from '../lib/authErrors.js'
import { useAuthStore } from '../stores/auth.js'
import { isValidPassword, passwordsMismatch } from '../utils/validation.js'

const auth = useAuthStore()

const router = useRouter()

const password = ref('')

const confirm = ref('')

const submitting = ref(false)

const error = ref('')

// Supabase exchanges the recovery hash asynchronously after init(), so the
// hash itself counts as evidence of a valid link; the form must never hide
// while "#...type=recovery" is in the URL.
const recoveryHash = ref(
  typeof window !== 'undefined' && window.location.hash.includes('type=recovery'),
)

const hasRecovery = computed(() => recoveryHash.value || !auth.ready || !!auth.session)

const passwordValid = computed(() => isValidPassword(password.value))

const mismatch = computed(() => passwordsMismatch(password.value, confirm.value))

const canSubmit = computed(() => passwordValid.value && confirm.value === password.value)

async function submit() {
  if (!canSubmit.value) return
  error.value = ''
  submitting.value = true

  try {
    await auth.updatePassword(password.value)
    await auth.signOut()
    router.push('/login?reset=1')
  } catch (e) {
    // Supabase AuthErrors carry an HTTP status, so friendlyError() would swap
    // their specific copy for a generic status message (commit 1d0f4aa).
    // E-13: lib/authErrors.js keys on AuthError.code instead of SDK prose.
    error.value = authErrorCopy(e, 'Could not update password. The link may have expired.')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.field-error {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--ink-marker-text);
}
</style>
