<template>
  <section class="home">
    <div class="home-card">
      <h1 class="home-head">What do you want to learn?</h1>

      <div class="quick" data-testid="home-mode-quick">
        <label for="home-topic" class="sr-only">Topic</label>
        <input
          id="home-topic"
          v-model="quickTopic"
          class="quick-input"
          data-testid="home-quick-topic"
          placeholder="a topic, a chapter, a thing that will not stick..."
          autocomplete="off"
          @keydown.enter="startQuick"
        />

        <p class="quick-go">
          <button
            type="button"
            class="cta-primary hit-44"
            data-testid="home-quick-go"
            :disabled="busy"
            @click="startQuick"
          >
            <span>{{ startLabel }}</span>
            <svg
              class="cta-mark"
              viewBox="0 0 20 20"
              width="18"
              height="18"
              aria-hidden="true"
              focusable="false"
            >
              <path d="M4 10 L15 10 M10.5 5.5 L15 10 L10.5 14.5" />
            </svg>
          </button>
        </p>
      </div>
      <StartTopicIntercept
        v-if="stage === 'intercept'"
        :match="interceptMatch"
        :kind="interceptKind"
        :busy="busy"
        @open-existing="openExisting"
        @continue-topic="handleContinuePrior"
        @start-fresh="handleStartFresh"
        @cancel="cancel"
      />

      <!-- E-01: the form above must stay mounted regardless of store.error --
           this paragraph only ever adds a message underneath it. It shows
           either a start-attempt failure (createSession/lookupTopic/
           continueTopic rejecting) or, absent that, a boot-time list failure
           when there are no sessions yet to show instead. -->
      <p v-if="displayError" class="error" data-testid="home-error" role="alert">
        {{ displayError }}
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import StartTopicIntercept from '../components/start/StartTopicIntercept.vue'
import { useStartFlow } from '../composables/useStartFlow.js'
import { useSessionStore } from '../stores/session.js'
import { friendlyError } from '../lib/errors.js'

const router = useRouter()

const store = useSessionStore()

const quickTopic = ref('')

const startError = ref(null)

const {
  stage,
  busy,
  interceptMatch,
  interceptKind,
  begin,
  openExisting,
  continuePrior,
  startFresh,
  cancel,
} = useStartFlow({ store, router })

watch(quickTopic, () => cancel())

const startLabel = computed(() => (busy.value ? 'Starting...' : 'Start'))

const bootError = computed(() =>
  store.error && !store.sessions.length ? friendlyError(store.error) : null,
)

const displayError = computed(() => startError.value || bootError.value)

onMounted(() => {
  // U-05: boot-path load - failure is handled locally (store error state), so
  // a transient backend hiccup must not toast on Home's first mount. Silence
  // comes from { silent: true } on the getSessionLibrary calls inside
  // store.listSessions() (session.js), not from sessionsApi.listSessions.
  store.listSessions().catch(() => {})
})

// E-01: begin()/continuePrior()/startFresh() can reject (createSession,
// lookupTopic, continueTopic) and the composable does not swallow that --
// an unawaited/uncaught rejection here used to leave the form frozen with no
// feedback. Catch at the call site and surface inline instead.
async function startQuick() {
  startError.value = null

  try {
    await begin(quickTopic.value)
  } catch (e) {
    startError.value = friendlyError(e)
  }
}

async function handleContinuePrior() {
  startError.value = null

  try {
    await continuePrior()
  } catch (e) {
    startError.value = friendlyError(e)
  }
}

async function handleStartFresh() {
  startError.value = null

  try {
    await startFresh()
  } catch (e) {
    startError.value = friendlyError(e)
  }
}
</script>

<style scoped>
/* One centred white card on the desk: the question, the topic field and
   Start live on the sheet, the desk ground shows around it. */
.home {
  max-width: 44rem;
  margin: 0 auto;
  min-height: calc(100dvh - clamp(2rem, 6vw, 4.5rem) - 4rem);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.home-card {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
  padding: 2.5rem 2.5rem 2.75rem;
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-radius: var(--radius-card);
  box-shadow: 0 1px 0 var(--card-drop);
}

.home-head {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 600;
  letter-spacing: var(--tracking-display);
  line-height: var(--lh-display);
  color: var(--ink);
  text-align: center;
}

.error {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink-marker-text);
  text-align: center;
}

.quick {
  display: flex;
  flex-direction: column;
}

/* Field on a rule: no box, no radius, one bottom rule that inks on focus.
   overflow/text-overflow/white-space clip a long placeholder to an ellipsis
   on narrow viewports instead of letting it wrap or overflow mid-word. */
.quick-input {
  display: block;
  width: 100%;
  padding: 0;
  border: 0;
  border-bottom: 1px solid var(--rule-strong);
  border-radius: 0;
  background: transparent;
  color: var(--ink-learner);
  caret-color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-input::placeholder {
  color: var(--pencil);
}

.quick-input:focus {
  outline: none;
  border-bottom-color: var(--ink-learner);
}

.quick-go {
  margin: 0;
  padding-top: 1.75rem;
  line-height: var(--lh-body);
  text-align: center;
}

/* Written, not stamped: the default action is a line of blue text with a
   drawn arrow after the word. */
.cta-primary {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--lh-body);
  cursor: pointer;
}

.cta-primary > span {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.cta-primary:hover:not(:disabled) {
  color: var(--color-accent-hover);
}

.cta-primary:disabled {
  color: var(--pencil);
  cursor: default;
}

.cta-primary:disabled > span {
  text-decoration: none;
}

.cta-mark {
  flex: 0 0 auto;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.cta-primary:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}
</style>
