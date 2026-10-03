<template>
  <div class="learning-tab" data-testid="agg-learning">
    <section
      v-for="control in controls"
      :key="control.key"
      class="sec"
      :data-testid="`learning-${control.key}`"
    >
      <div class="sec-head">
        <h2 class="sec-title">{{ control.title }}</h2>
        <span
          v-if="control.state.saved"
          class="saved-flash"
          role="status"
          :data-testid="`learning-${control.key}-saved`"
        >
          <svg
            class="tick"
            viewBox="0 0 12 12"
            width="12"
            height="12"
            aria-hidden="true"
            focusable="false"
          >
            <path :d="TICK_PATH" />
          </svg>
          Saved.
        </span>
      </div>
      <p v-if="control.help" class="sec-help" :data-testid="`learning-${control.key}-help`">
        {{ control.help }}
      </p>
      <LetteredLinesPicker
        :model-value="control.state.value"
        :options="control.options"
        :legend="control.title"
        :testid-prefix="control.testidPrefix"
        @update:model-value="control.state.change"
      />
    </section>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'

import LetteredLinesPicker from '../LetteredLinesPicker.vue'
import { TICK_PATH } from '../chat/levelMark.js'
import { friendlyError } from '../../lib/errors.js'
import { TUTOR_PREFERENCES, preferenceValue } from '../../lib/tutorPreferences.js'
import { useUserStore } from '../../stores/user.js'
import { useToast } from '../../composables/useToast.js'

const user = useUserStore()

const { showError } = useToast()

// One autosaving tutor preference (#357). Every change is its own
// single-field PATCH /api/me; changes to one control are queued so they reach
// the server in the order the learner made them and the last choice sticks.
// A failed write puts the control back on the value the store (and so the
// server) still holds.
function autosaved(key) {
  const stored = () => preferenceValue(user.interactionPreferences, key)
  const value = ref(stored())
  const saved = ref(false)
  let queue = Promise.resolve()
  let latest = 0
  let pending = 0

  // The router hydrates /me in the background, so the tab can mount on a
  // stale local snapshot; follow the store unless a save of ours is queued.
  watch(stored, (next) => {
    if (!pending) value.value = next
  })

  function change(next) {
    value.value = next
    saved.value = false
    const seq = ++latest
    pending++
    queue = queue.then(async () => {
      try {
        await user.updateProfile({ [key]: next })

        if (seq === latest) saved.value = true
      } catch (e) {
        showError(friendlyError(e))

        if (seq === latest) value.value = stored()
      } finally {
        pending--
      }
    })
  }

  return reactive({ value, saved, change })
}

// Options and fallbacks come from lib/tutorPreferences.js.
const controls = [
  {
    key: 'feedback',
    title: 'Feedback style',
    testidPrefix: 'feedback-style',
    options: TUTOR_PREFERENCES.feedback.options,
    state: autosaved('feedback'),
  },
  {
    key: 'check-ins',
    title: 'Check-ins',
    help: 'How often the tutor runs a quick check without being asked.',
    testidPrefix: 'check-ins',
    options: TUTOR_PREFERENCES.checkIns.options,
    state: autosaved('checkIns'),
  },
  {
    key: 'reply-length',
    title: 'Reply length',
    testidPrefix: 'reply-length',
    options: TUTOR_PREFERENCES.replyLength.options,
    state: autosaved('replyLength'),
  },
]
</script>

<style scoped>
/* The tutor-preferences tab (#357): Feedback style, Check-ins and Reply
   length, each autosaving. The aggregate-profile analytics were removed
   (#350) and belong to the /profile page (#358). */
.learning-tab {
  /* Full panel width. Independent sections stacked here and sitting side
     by side from 60rem up. */
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--line-pitch);
}

/* Card shell, .sec-title, .saved-flash and .tick come from assets/sheet.css;
   only this tab's own alignment is declared here. */
.sec {
  align-items: stretch;
  gap: 0.5rem;
}

/* The "Saved." flash sits on the title's line, beside it. */
.sec-head {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}

.sec-help {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--line-pitch);
  color: var(--pencil);
}

/* From 60rem the cards sit side by side, filling left to right. */
@media (min-width: 60rem) {
  .learning-tab {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}
</style>
