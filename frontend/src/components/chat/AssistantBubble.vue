<script setup>
import { computed } from 'vue'
import MarkdownContent from './MarkdownContent.vue'
import ToolCallChip from './ToolCallChip.vue'
import CitationsList from './CitationsList.vue'
import CheckRecap from './CheckRecap.vue'
import { TICK_PATH } from './levelMark.js'
import { formatTime } from '../../utils/formatDate.js'

const props = defineProps({
  message: { type: Object, required: true },
  streaming: { type: Boolean, default: false },
  // Cue-lands: this turn changed the profile, so its head line carries the tick.
  landed: { type: Boolean, default: false },
})

// A failed tool call that was retried successfully in the same message is
// noise to the learner -- show only the successful chip.
const visibleToolCalls = computed(() => {
  const calls = props.message.tool_calls || []

  const succeeded = new Set(
    calls.filter((tc) => (tc.state || 'done') !== 'error').map((tc) => tc.name),
  )

  return calls.filter((tc) => tc.state !== 'error' || !succeeded.has(tc.name))
})

// The head line carries the time only when the server sent one; never invent it.
const timeLabel = computed(() => formatTime(props.message.created_at))
</script>

<template>
  <article
    :class="['msg', 'assistant', { streaming }]"
    :data-testid="streaming ? 'msg-streaming' : 'msg-assistant'"
  >
    <div class="msg-gutter">
      <span class="role-tag">tutor</span>
      <span v-if="timeLabel" class="msg-time">{{ timeLabel }}</span>
      <svg
        v-if="landed"
        class="landed-tick"
        viewBox="0 0 12 12"
        width="12"
        height="12"
        aria-hidden="true"
        focusable="false"
        data-testid="msg-landed-tick"
      >
        <path :d="TICK_PATH" pathLength="1" />
      </svg>
    </div>
    <div class="msg-body">
      <template v-if="message.check_batch">
        <CheckRecap :batch="message.check_batch" />
        <MarkdownContent
          v-if="message.content"
          class="content"
          :text="message.content"
          :streaming="streaming"
        />
      </template>
      <template v-else>
        <span v-for="(tc, ti) in visibleToolCalls" :key="tc.id ?? ti" class="tool-call-row">
          <ToolCallChip :tool_call="tc" :state="tc.state || 'done'" />
        </span>
        <MarkdownContent
          v-if="message.content || streaming"
          class="content"
          :text="message.content || ''"
          :streaming="streaming"
        />
      </template>
      <span v-if="message.status === 'cancelled'" class="cancelled-marker">(stopped)</span>
      <span v-else-if="message.status === 'partial'" class="cancelled-marker">(interrupted)</span>
      <CitationsList :citations="message.citations || []" />
    </div>
  </article>
</template>

<style scoped>
/* The tutor writes flat on the desk -- no card, no edge, no drop. Told
   apart from the learner by the absence of a card, never by an avatar.
   The head line carries the role and time in pencil. */
.msg {
  align-self: flex-start;
  /* A fixed measure, not shrink-to-fit: with no card edge to explain it, the
     time label and landed tick must land on one shared right edge. */
  width: 78%;
  max-width: 78%;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.msg-gutter {
  position: relative;
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  min-width: 0;
}

.role-tag {
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  font-weight: 700;
  color: var(--pencil);
}

.msg-time {
  margin-left: auto;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  color: var(--pencil);
}

/* Top-right of the head line: filing the profile never reflows the card. */
.landed-tick {
  position: absolute;
  top: 0;
  right: 0;
  fill: none;
  stroke: var(--ink-learner);
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 0;
  animation: tick-draw var(--motion-base) cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes tick-draw {
  from {
    stroke-dashoffset: 1;
  }
  to {
    stroke-dashoffset: 0;
  }
}

.msg-body {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
}

.content {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink);
}

.tool-call-row {
  display: block;
}

.cancelled-marker {
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-style: italic;
  color: var(--pencil);
}

@media (prefers-reduced-motion: reduce) {
  .landed-tick {
    animation: none;
  }
}

@media (max-width: 599px) {
  .msg {
    width: 92%;
    max-width: 92%;
  }
}
</style>
