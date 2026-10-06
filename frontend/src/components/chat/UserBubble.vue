<script setup>
import { computed } from 'vue'
import MarkdownContent from './MarkdownContent.vue'
import { formatTime } from '../../utils/formatDate.js'

const props = defineProps({
  content: { type: String, default: '' },
  createdAt: { type: String, default: null },
})

// The head line carries the time only when the server sent one; never invent it.
const timeLabel = computed(() => formatTime(props.createdAt))
</script>

<template>
  <article class="msg user" data-testid="msg-user">
    <div class="msg-gutter">
      <span class="role-tag">you</span>
      <span v-if="timeLabel" class="msg-time">{{ timeLabel }}</span>
    </div>
    <div class="msg-body">
      <MarkdownContent class="content" :text="content || ''" />
    </div>
  </article>
</template>

<style scoped>
/* The learner's card: blue stock, right-aligned. Same card grammar as the
   tutor, different material -- that is how the two voices are told apart. */
.msg {
  align-self: flex-end;
  max-width: 78%;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  background: var(--card-learner);
  border: 1px solid var(--card-learner-edge);
  border-radius: var(--radius-card);
  box-shadow: 0 1px 0 var(--card-drop);
  padding: 0.55rem 0.9rem 0.7rem;
}

.msg-gutter {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  min-width: 0;
}

.role-tag {
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  font-weight: 700;
  color: var(--ink-learner);
  opacity: 0.75;
}

.msg-time {
  margin-left: auto;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  color: var(--ink-learner);
  opacity: 0.75;
}

.msg-body {
  min-width: 0;
}

.content {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink-learner);
  /* D-13: a pasted URL or a long token has no break opportunity, so without
     these it widens the bubble past the column instead of wrapping. */
  overflow-wrap: anywhere;
  word-break: break-word;
}

@media (max-width: 599px) {
  .msg {
    max-width: 92%;
  }
}
</style>
