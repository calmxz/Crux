<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'

const props = defineProps({
  match: { type: Object, required: true },
  kind: { type: String, required: true, validator: (v) => ['active', 'ended'].includes(v) },
  busy: { type: Boolean, default: false },
})

defineEmits(['open-existing', 'continue-topic', 'start-fresh', 'cancel'])

const gapLine = computed(() =>
  props.kind === 'ended' && props.match.gap_count > 0
    ? `${props.match.gap_count} ${props.match.gap_count === 1 ? 'gap' : 'gaps'} open`
    : '',
)

const primaryBtn = ref(null)

onMounted(async () => {
  await nextTick()
  primaryBtn.value?.focus()
})
</script>

<template>
  <div
    class="intercept"
    data-testid="start-intercept"
    role="status"
    aria-live="polite"
    aria-label="Existing session found"
  >
    <button
      type="button"
      class="intercept-cancel"
      data-testid="intercept-cancel"
      aria-label="Dismiss"
      :disabled="busy"
      @click="$emit('cancel')"
    >
      <svg
        class="intercept-cancel-mark"
        viewBox="0 0 20 20"
        width="20"
        height="20"
        aria-hidden="true"
        focusable="false"
      >
        <path d="M6 6 L14 14 M14 6 L6 14" />
      </svg>
    </button>
    <p v-if="kind === 'active'" class="intercept-line">
      You have an active session on <strong>"{{ match.title }}"</strong>.
    </p>
    <p v-else class="intercept-line">
      You studied <strong>"{{ match.title }}"</strong> before<template v-if="gapLine">
        ({{ gapLine }})</template
      >.
    </p>
    <div class="intercept-actions">
      <button
        v-if="kind === 'active'"
        ref="primaryBtn"
        type="button"
        class="intercept-primary"
        data-testid="intercept-open-existing"
        :disabled="busy"
        @click="$emit('open-existing')"
      >
        Open it
      </button>
      <button
        v-else
        ref="primaryBtn"
        type="button"
        class="intercept-primary"
        data-testid="intercept-continue"
        :disabled="busy"
        @click="$emit('continue-topic')"
      >
        Continue where you left off
      </button>
      <button
        type="button"
        class="intercept-secondary"
        data-testid="intercept-fresh"
        :disabled="busy"
        @click="$emit('start-fresh')"
      >
        Start fresh
      </button>
    </div>
  </div>
</template>

<style scoped>
/* A card: the page pauses on it. White stock, same grammar as the tutor's
   own card, actions written not stamped. */
.intercept {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.875rem 2.5rem 0.875rem 1rem;
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-radius: var(--radius-card);
  box-shadow: 0 1px 0 var(--card-drop);
}

.intercept-line {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink);
}

.intercept-line strong {
  font-weight: 700;
}

.intercept-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0 1.25rem;
  line-height: var(--lh-body);
}

.intercept-primary,
.intercept-secondary {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--lh-body);
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}

.intercept-primary:hover:not(:disabled),
.intercept-secondary:hover:not(:disabled) {
  color: var(--color-accent-hover);
}

.intercept-cancel {
  position: absolute;
  top: 0.6rem;
  right: 0.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 1.75rem;
  padding: 0;
  background: transparent;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--ink-learner);
  cursor: pointer;
}

.intercept-cancel-mark {
  flex: 0 0 auto;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.intercept-primary:focus-visible,
.intercept-secondary:focus-visible,
.intercept-cancel:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.intercept-primary:disabled,
.intercept-secondary:disabled,
.intercept-cancel:disabled {
  color: var(--pencil);
  text-decoration: none;
  cursor: default;
}
</style>
