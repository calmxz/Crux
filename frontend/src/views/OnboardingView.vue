<template>
  <AuthCover
    title="Welcome to Crux."
    lede="Tell us how you like to learn — we'll tune the tutor before you begin."
  >
    <form class="form" @submit.prevent="submit">
      <div class="field stagger" style="--delay: 0ms">
        <label for="display-name" class="field-label">What we call you</label>
        <div class="field-line">
          <InputText
            id="display-name"
            v-model="displayName"
            data-testid="onboarding-name"
            placeholder="Learner"
            autocomplete="off"
            class="field-input"
          />
        </div>
      </div>

      <div class="field stagger" style="--delay: 60ms">
        <div class="choice" data-testid="onboarding-feedback">
          <p class="field-label">When you get stuck</p>
          <LetteredLinesPicker
            v-model="feedback"
            :options="feedbackOptions"
            name="feedback-style"
            legend="Feedback style"
            testid-prefix="feedback-style"
          />
        </div>
        <p class="help">
          {{
            feedback === 'hints'
              ? 'Tutor will nudge you toward the answer.'
              : 'Tutor will explain the answer outright when asked.'
          }}
        </p>
      </div>

      <div class="actions stagger" style="--delay: 120ms">
        <button type="submit" class="cta" data-testid="onboarding-submit" :disabled="submitting">
          <span>Begin</span>
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

      <p v-if="submitError" class="status is-alert" role="alert" data-testid="onboarding-error">
        {{ submitError }}
      </p>

      <!-- E-09: onboarding must not be a dead end for a learner who cannot
           or does not want to complete it right now (e.g. force-landed here
           after a failed hydrate). Same sign-out as Sidebar.vue's onSignOut. -->
      <p class="line">
        <button type="button" class="linkbtn" data-testid="onboarding-signout" @click="signOut">
          Sign out
        </button>
      </p>
    </form>
  </AuthCover>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import InputText from 'primevue/inputtext'

import AuthCover from '../components/auth/AuthCover.vue'
import LetteredLinesPicker from '../components/LetteredLinesPicker.vue'
import { friendlyError } from '@/lib/errors.js'
import { TUTOR_PREFERENCES, preferenceValue } from '@/lib/tutorPreferences.js'
import { useUserStore } from '../stores/user.js'
import { useAuthStore } from '../stores/auth.js'
import { useToast } from '../composables/useToast.js'

const router = useRouter()

const userStore = useUserStore()

const authStore = useAuthStore()

const displayName = ref(userStore.name || '')

// Labels only: the help line below the picker carries the explanation here,
// so the Settings sub copy is left off.
const feedbackOptions = TUTOR_PREFERENCES.feedback.options.map(({ value, label }) => ({
  value,
  label,
}))

const feedback = ref(preferenceValue(userStore.interactionPreferences, 'feedback'))

const submitting = ref(false)

const submitError = ref(null)

async function submit() {
  if (submitting.value) return
  submitting.value = true
  submitError.value = null

  try {
    await userStore.completeOnboarding({
      name: displayName.value,
      feedback: feedback.value,
    })
    router.push({ name: 'home' })
  } catch (e) {
    // F-11: inline surface (LoginView pattern); the errorBus toast alone
    // left the form frozen with no explanation and an unhandled rejection.
    submitError.value = friendlyError(e)
  } finally {
    submitting.value = false
  }
}

// Same sign-out as Sidebar.vue's onSignOut, except a failure keeps the learner here.
async function signOut() {
  try {
    await authStore.signOut()
  } catch (err) {
    useToast().showError(err?.message || 'Sign out failed')

    return
  }

  router.push('/login')
}
</script>

<style scoped>
/* The picker's own label sits as a paragraph rather than a <label>, so it
   needs the block box the cover's <label> elements already have. */
.field-label {
  display: block;
  padding: 0;
}

/* The lettered lines come from the shared LetteredLinesPicker, so the
   grammar has one source; this wrapper only carries the pencil label. */
.choice {
  min-width: 0;
}

.choice .field-label {
  margin: 0;
}

.help {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--pencil);
}

/* Ink appears: the sheet fills in line by line, nothing moves. */
.stagger {
  opacity: 0;
  animation: ink-in var(--motion-ink) var(--motion-out-expo) forwards;
  animation-delay: var(--delay, 0ms);
}

@keyframes ink-in {
  to {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .stagger {
    opacity: 1;
    animation: none;
  }
}

/* The sign-out control is a button that has to read as the cover's link. */
.linkbtn {
  background: none;
  border: 0;
  padding: 0;
  font: inherit;
  font-weight: 700;
  color: var(--ink-learner);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.linkbtn:hover {
  color: var(--color-accent-hover);
}

.linkbtn:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}
</style>
