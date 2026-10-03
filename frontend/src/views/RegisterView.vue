<template>
  <AuthCover title="Join Crux" lede="Register with your email and a password.">
    <form v-if="!sent" class="form" data-testid="register-form" @submit.prevent="submit">
      <div class="field">
        <label for="email" class="field-label">Email</label>
        <div class="field-line">
          <InputText
            id="email"
            v-model="email"
            type="email"
            data-testid="register-email"
            autocomplete="email"
            placeholder="you@example.com"
            required
            class="field-input"
          />
        </div>
      </div>

      <div class="field">
        <label for="password" class="field-label">Password</label>
        <div class="field-line">
          <InputText
            id="password"
            v-model="password"
            type="password"
            data-testid="register-password"
            autocomplete="new-password"
            placeholder="At least 8 characters"
            required
            class="field-input"
          />
        </div>
      </div>

      <div class="field">
        <label for="confirm" class="field-label">Confirm password</label>
        <div class="field-line">
          <InputText
            id="confirm"
            v-model="confirm"
            type="password"
            data-testid="register-confirm"
            autocomplete="new-password"
            placeholder="Re-enter password"
            required
            class="field-input"
          />
        </div>
      </div>

      <p v-if="mismatch" class="field-error" data-testid="register-mismatch">
        Passwords do not match.
      </p>
      <p v-if="error" class="status is-alert" role="alert" data-testid="register-error">
        {{ error }}
      </p>

      <label class="consent">
        <input
          type="checkbox"
          v-model="consent"
          data-testid="register-consent"
          class="consent-box"
        />
        <span>
          I agree to the
          <RouterLink class="link" to="/tos" target="_blank">Terms of Service</RouterLink>
          and
          <RouterLink class="link" to="/privacy" target="_blank">Privacy Policy</RouterLink>.
        </span>
      </label>

      <div class="actions">
        <button
          type="submit"
          class="cta"
          data-testid="register-submit"
          :disabled="!canSubmit || submitting"
        >
          <span>{{ submitting ? 'Creating…' : 'Create account' }}</span>
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
        Already have an account?
        <RouterLink class="link" to="/login" data-testid="register-to-login">Sign in</RouterLink>
      </p>
    </form>

    <div v-else class="form" data-testid="register-sent">
      <p class="status is-done">
        Check your inbox at <strong>{{ email.trim() }}</strong> to confirm your account, then sign
        in.
      </p>
      <p class="line">
        <RouterLink class="link" to="/login" data-testid="register-sent-to-login"
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
import { isValidEmail, isValidPassword, passwordsMismatch } from '../utils/validation.js'

const auth = useAuthStore()

const email = ref('')

const password = ref('')

const confirm = ref('')

const submitting = ref(false)

const error = ref('')

const sent = ref(false)

const consent = ref(false)

const emailValid = computed(() => isValidEmail(email.value.trim()))

const passwordValid = computed(() => isValidPassword(password.value))

const mismatch = computed(() => passwordsMismatch(password.value, confirm.value))

const canSubmit = computed(
  () =>
    emailValid.value && passwordValid.value && confirm.value === password.value && consent.value,
)

async function submit() {
  if (!canSubmit.value) return
  error.value = ''
  submitting.value = true

  try {
    await auth.register(email.value.trim(), password.value)
    sent.value = true
  } catch (e) {
    // Supabase AuthErrors carry an HTTP status, so friendlyError() would swap
    // their specific copy ("User already registered") for a generic status
    // message. Surface the SDK message instead.
    // E-13: code-keyed copy, never SDK prose (see lib/authErrors.js).
    error.value = authErrorCopy(e, 'Could not create account. Try again.')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.consent {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--pencil);
  cursor: pointer;
}

.consent-box {
  flex-shrink: 0;
  width: 1rem;
  height: 1rem;
  margin: 6px 0 0;
  accent-color: var(--ink-learner);
}

.consent-box:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.field-error {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--ink-marker-text);
}
</style>
