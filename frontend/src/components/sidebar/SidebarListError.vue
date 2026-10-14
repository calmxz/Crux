<script setup>
import { ref } from 'vue'

import { LIST_FAILED_COPY } from '../../lib/errors.js'

defineEmits(['retry'])

const retryEl = ref(null)

defineExpose({
  focus: () => retryEl.value?.focus(),
  hasFocus: () => !!retryEl.value && document.activeElement === retryEl.value,
})
</script>

<template>
  <!-- #544: shown when no list has loaded this sign-in and the latest one
       failed: in place of a tab's empty hint, or under the rows a create
       inserted. Same shape as the session page's error line: the message,
       then a written Retry. -->
  <div class="sb-list-error" role="alert" data-testid="sidebar-list-error">
    <p class="sb-list-error-msg">{{ LIST_FAILED_COPY }}</p>
    <button
      ref="retryEl"
      type="button"
      class="sb-list-retry coarse-2x"
      data-testid="sidebar-list-retry"
      @click="$emit('retry')"
    >
      Retry
    </button>
  </div>
</template>

<style scoped>
.sb-list-error {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0 0.75rem;
  padding: 0 0.75rem;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--line-pitch);
}

.sb-list-error-msg {
  margin: 0;
  color: var(--ink-marker-text);
}

.sb-list-retry {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink-learner);
  font: inherit;
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}

.sb-list-retry:hover {
  color: var(--color-accent-hover);
}

.sb-list-retry:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: 2px;
}
</style>
