<template>
  <Dialog
    :visible="visible"
    modal
    header="Which gap should we review?"
    :style="{ width: 'min(24rem, calc(100vw - 2rem))' }"
    class="crux-dialog"
    data-testid="gap-picker"
    @update:visible="$emit('update:visible', $event)"
  >
    <ul class="gap-list" aria-label="Confirmed gaps">
      <li v-for="(g, i) in gaps" :key="g">
        <button
          type="button"
          class="gap-option"
          :data-testid="`gap-picker-option-${i}`"
          @click="choose(g)"
        >
          <svg
            class="gap-mark"
            viewBox="0 0 12 12"
            width="12"
            height="12"
            aria-hidden="true"
            focusable="false"
          >
            <circle cx="6" cy="6" r="4" />
          </svg>
          <span class="gap-word">{{ g }}</span>
        </button>
      </li>
    </ul>
  </Dialog>
</template>

<script setup>
import Dialog from 'primevue/dialog'

defineProps({
  visible: { type: Boolean, default: false },
  gaps: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:visible', 'select'])

function choose(gap) {
  emit('select', gap)
  emit('update:visible', false)
}
</script>

<style scoped>
/* Entries as cue words on ruled lines, not boxed options. */
.gap-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.gap-option {
  display: flex;
  align-items: baseline;
  gap: 0.625rem;
  width: 100%;
  padding: 0.5rem 0;
  border: 0;
  box-shadow: inset 0 -1px 0 var(--card-edge);
  border-radius: 0;
  background: transparent;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  cursor: pointer;
  text-align: left;
}

.gap-option:last-child {
  box-shadow: none;
}

.gap-mark {
  flex: 0 0 auto;
  align-self: center;
  fill: none;
  stroke: var(--pencil);
  stroke-width: 1.5;
}

.gap-word {
  color: var(--ink-learner);
}

.gap-option:hover .gap-word {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.gap-option:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}
</style>
