<script setup>
import { computed, ref } from 'vue'

// #354: the start-flow topic card (#341 variant A). The tutor's first reply at
// the learner's level carries it. Every line is just a learner message: the
// view sends `pick`'s text through the normal composer path.
const props = defineProps({
  card: { type: Object, required: true },
  busy: { type: Boolean, default: false },
})

const emit = defineEmits(['pick', 'dismiss'])

const broad = computed(() => props.card.mode !== 'specific')

const TITLES = {
  broad: 'Here is what we would cover. Where do you want to start?',
  specific: 'Nearby ground I can teach. Want to widen out?',
}

// Specific mode leads with staying on the session topic; the card writes that
// line itself so the model only supplies the adjacent topics.
const lines = computed(() => {
  const items = (props.card.items || []).map((it) => ({
    label: it.label,
    hint: it.hint || '',
    message: `Let's start with ${it.label}`,
  }))

  if (broad.value) return items
  const keep = `Keep going on ${props.card.topic}`

  return [{ label: keep, hint: '', message: keep }, ...items]
})

// A. / B. / C. -- the lettered-line grammar (DESIGN.md), as on every check.
function letter(i) {
  return String.fromCharCode(65 + i)
}

const other = ref('')

function sendOther() {
  const text = other.value.trim()

  if (!text || props.busy) return
  emit('pick', text)
}
</script>

<template>
  <section class="topic-card" data-testid="topic-suggest-card" aria-label="Topic suggestions">
    <div class="topic-head">
      <p class="topic-title">{{ broad ? TITLES.broad : TITLES.specific }}</p>
      <button
        type="button"
        class="topic-dismiss"
        data-testid="topic-dismiss"
        aria-label="Dismiss topic suggestions"
        @click="emit('dismiss')"
      >
        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" focusable="false">
          <path d="M4 4 L12 12" />
          <path d="M12 4 L4 12" />
        </svg>
      </button>
    </div>
    <p class="topic-sub">
      {{
        broad
          ? 'Pick a subtopic, or tell me something else.'
          : 'Pick one, or tell me something else.'
      }}
    </p>
    <ul class="topic-lines">
      <li v-for="(line, i) in lines" :key="line.message">
        <button
          type="button"
          class="topic-line"
          :data-testid="`topic-line-${i}`"
          :disabled="busy"
          @click="emit('pick', line.message)"
        >
          <span class="topic-letter" aria-hidden="true">{{ letter(i) }}.</span>
          <span class="topic-label">{{ line.label }}</span>
          <span v-if="line.hint" class="topic-hint">{{ line.hint }}</span>
        </button>
      </li>
    </ul>
    <form class="topic-other" @submit.prevent="sendOther">
      <span class="topic-letter" aria-hidden="true">?</span>
      <input
        v-model="other"
        class="topic-other-input"
        data-testid="topic-other-input"
        placeholder="Something else..."
        aria-label="Something else to study"
        maxlength="200"
        :disabled="busy"
      />
      <button
        type="submit"
        class="topic-other-send"
        data-testid="topic-other-send"
        :disabled="busy || !other.trim()"
      >
        Send
      </button>
    </form>
    <p class="topic-nudge">
      Studying from your own notes or slides? Attach a file with the clip in the composer and I will
      teach from that instead.
    </p>
  </section>
</template>

<style scoped>
/* Same grammar as the level picker (DiagnosticConsentCard). */
.topic-card {
  max-width: 84%;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-radius: var(--radius-card);
  box-shadow: 0 1px 0 var(--card-drop);
  padding: 0.55rem 0.9rem 0.7rem;
  font-family: var(--font-sans);
}

.topic-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding-bottom: 0.4rem;
  border-bottom: 3px solid var(--ink);
}

.topic-title {
  margin: 0;
  font-size: var(--fs-body);
  font-weight: 700;
  line-height: var(--lh-body);
  color: var(--ink);
}

.topic-sub,
.topic-nudge {
  margin: 0;
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--pencil);
}

.topic-dismiss {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  background: none;
  border: none;
  cursor: pointer;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: var(--radius-sm);
  color: var(--ink-learner);
}

.topic-dismiss svg {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
}

.topic-dismiss:focus-visible,
.topic-line:not(:disabled):focus-visible,
.topic-other-send:not(:disabled):focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.topic-lines {
  list-style: none;
  margin: 0;
  padding: 0;
}

.topic-line {
  display: flex;
  align-items: baseline;
  gap: 0.625rem;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  /* Painted, not laid out: each action is a line inside the card. */
  box-shadow: inset 0 -1px 0 var(--rule);
  border-radius: 0;
  padding: 0.4rem 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink);
  cursor: pointer;
}

.topic-letter {
  flex: 0 0 auto;
  font-weight: 700;
  color: var(--ink-learner);
}

.topic-label {
  min-width: 0;
  overflow-wrap: anywhere;
}

.topic-hint {
  margin-left: auto;
  padding-left: 0.5rem;
  font-size: var(--fs-label);
  color: var(--pencil);
  text-align: right;
}

.topic-line:not(:disabled):hover .topic-label {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.topic-line:disabled {
  color: var(--pencil);
  cursor: default;
  pointer-events: none;
}

.topic-other {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding-top: 0.4rem;
}

.topic-other-input {
  flex: 1;
  min-width: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  border: 0;
  border-bottom: 1px solid var(--rule-strong);
  background: transparent;
  color: var(--ink-learner);
  padding: 0.1rem 0;
}

.topic-other-input::placeholder {
  color: var(--pencil);
}

.topic-other-input:focus-visible {
  outline: none;
  border-bottom-color: var(--ink-learner);
}

.topic-other-send {
  flex: 0 0 auto;
  background: none;
  border: 0;
  padding: 0 0.25rem;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  font-weight: 700;
  color: var(--ink-learner);
  cursor: pointer;
  border-radius: var(--radius-sm);
}

.topic-other-send:disabled {
  color: var(--pencil);
  cursor: default;
}
</style>
