<script setup>
defineProps({
  busy: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

defineEmits(['quiz', 'level', 'dismiss'])

const LEVELS = ['beginner', 'intermediate', 'advanced']

const LABELS = { beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced' }

const LETTERS = { beginner: 'A', intermediate: 'B', advanced: 'C' }
</script>

<template>
  <section
    class="diag-card"
    data-testid="diagnostic-consent-card"
    aria-label="Knowledge check offer"
  >
    <div class="diag-head">
      <p class="diag-title">Want me to pitch this at the right level?</p>
      <button
        type="button"
        class="diag-dismiss"
        data-testid="diag-dismiss"
        aria-label="Dismiss knowledge check offer"
        @click="$emit('dismiss')"
      >
        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" focusable="false">
          <path d="M4 4 L12 12" />
          <path d="M12 4 L4 12" />
        </svg>
      </button>
    </div>
    <p class="diag-sub">Take a quick 3-question check, or tell me where you are.</p>
    <ul class="diag-actions">
      <li>
        <button
          type="button"
          class="diag-quiz"
          data-testid="diag-quiz"
          :disabled="busy"
          @click="$emit('quiz')"
        >
          <span class="diag-letter" aria-hidden="true">Q.</span>
          <span>Quiz me (3 quick questions)</span>
        </button>
      </li>
      <li v-for="lvl in LEVELS" :key="lvl">
        <button
          type="button"
          class="diag-level"
          :data-testid="`diag-level-${lvl}`"
          :disabled="busy"
          @click="$emit('level', lvl)"
        >
          <span class="diag-letter" aria-hidden="true">{{ LETTERS[lvl] }}.</span>
          <span>{{ LABELS[lvl] }}</span>
        </button>
      </li>
    </ul>
    <p v-if="error" class="diag-error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
/* Same grammar as a check card. */
.diag-card {
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

/* Same head grammar as a check card: a 3px graphite rule closes the head. */
.diag-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding-bottom: 0.4rem;
  border-bottom: 3px solid var(--ink);
}

.diag-title {
  margin: 0;
  font-size: var(--fs-body);
  font-weight: 700;
  line-height: var(--lh-body);
  color: var(--ink);
}

.diag-sub {
  margin: 0;
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--pencil);
}

.diag-dismiss {
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

.diag-dismiss svg {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
}

.diag-dismiss:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.diag-actions {
  list-style: none;
  margin: 0;
  padding: 0;
}

.diag-quiz,
.diag-level {
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

.diag-letter {
  flex: 0 0 auto;
  font-weight: 700;
  color: var(--ink-learner);
}

.diag-quiz:not(:disabled):hover,
.diag-level:not(:disabled):hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.diag-quiz:not(:disabled):focus-visible,
.diag-level:not(:disabled):focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.diag-quiz:disabled,
.diag-level:disabled {
  color: var(--pencil);
  cursor: default;
  pointer-events: none;
}

.diag-error {
  margin: 0;
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--ink-marker-text);
}
</style>
