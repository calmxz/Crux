<script setup>
import { computed } from 'vue'
import { labelFor } from './toolLabels.js'

const props = defineProps({
  tool_call: { type: Object, required: true },
  state: {
    type: String,
    required: true,
    validator: (v) => ['running', 'done', 'error'].includes(v),
  },
})

const display = computed(() => {
  if (props.state === 'done' && props.tool_call.summary) {
    return props.tool_call.summary
  }

  return labelFor(props.tool_call.name, props.state)
})
</script>

<template>
  <span
    class="tool-pill"
    :class="`tool-pill--${state}`"
    :title="state === 'error' ? tool_call.error || display : undefined"
  >
    <span class="tool-pill-dot" aria-hidden="true"></span>
    <span class="tool-pill-text">{{ display }}</span>
  </span>
</template>

<style scoped>
/* No pill: what the tutor did while writing is a pencil aside inside the card. */
.tool-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--pencil);
}

.tool-pill-dot {
  width: 12px;
  height: 1px;
  flex-shrink: 0;
  background: var(--pencil);
}

.tool-pill--running .tool-pill-dot {
  animation: tool-mark-fade 1s ease-in-out infinite;
}

.tool-pill--error {
  color: var(--ink-marker-text);
}

.tool-pill--error .tool-pill-dot {
  background: var(--ink-marker);
}

@keyframes tool-mark-fade {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

@media (prefers-reduced-motion: reduce) {
  .tool-pill--running .tool-pill-dot {
    animation: none;
  }
}
</style>
