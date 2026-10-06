<template>
  <AuthCover title="Forgot your password?" lede="Enter your email and we'll send you a reset link.">
    <form v-if="!sent" class="form" data-testid="forgot-form" @submit.prevent="submit">
      <div class="field">
        <label for="email" class="field-label">Email</label>
        <div class="field-line">
          <InputText
            id="email"
            v-model="email"
            type="email"
            data-testid="forgot-email"
            autocomplete="email"
            placeholder="you@example.com"
            required
            class="field-input"
          />
        </div>
      </div>

      <p v-if="error" class="status is-alert" role="alert" data-testid="forgot-error">
        {{ error }}
      </p>

      <div class="actions">
        <button
          type="submit"
          class="cta"
          data-testid="forgot-submit"
          :disabled="!canSubmit || submitting"
        >
          <span>{{ submitting ? 'Sending…' : 'Send reset link' }}</span>
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

      <p class="line">
        Remembered it?
        <RouterLink class="link" to="/login" data-testid="forgot-to-login"
          >Back to sign in</RouterLink
        >
      </p>
    </form>

    <div v-else class="form" data-testid="forgot-sent">
      <p class="status is-done">
        If an account exists for <strong>{{ email.trim() }}</strong
        >, a password reset link is on its way. Check your inbox.
      </p>
      <p class="line">
        <RouterLink class="link" to="/login" data-testid="forgot-sent-to-login"
          >Back to sign in</RouterLink
        >
      </p>
    </div>
  </AuthCover>
</template>

<script setup>
import { computed, ref } from 'vue'

import InputText from 'primevue/inputtext'

import AuthCover from '../components/auth/AuthCover.vue'
import { authErrorCopy } from '../lib/authErrors.js'
import { useAuthStore } from '../stores/auth.js'
import { isValidEmail } from '../utils/validation.js'

const auth = useAuthStore()

const email = ref('')

const submitting = ref(false)

const error = ref('')

const sent = ref(false)

const canSubmit = computed(() => isValidEmail(email.value.trim()))

async function submit() {
  if (!canSubmit.value) return
  error.value = ''
  submitting.value = true

  try {
    await auth.requestPasswordReset(email.value.trim())
    sent.value = true
  } catch (e) {
    // Supabase AuthErrors carry an HTTP status, so friendlyError() would swap
    // their specific copy (rate-limit wording, for instance) for a generic
    // status message. Surface the SDK message instead.
    // E-13: code-keyed copy, never SDK prose (see lib/authErrors.js).
    error.value = authErrorCopy(e, 'Could not send reset link. Try again.')
  } finally {
    submitting.value = false
  }
}
</script>
