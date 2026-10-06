<script setup>
import { computed } from 'vue'

import UserBubble from './UserBubble.vue'
import AssistantBubble from './AssistantBubble.vue'

const props = defineProps({
  messages: { type: Array, required: true },
  streamingMessage: { type: Object, default: null },
  awaiting: { type: Boolean, default: false },
  // Cue-lands: the latest tutor turn changed the profile, so its gutter
  // carries the blue tick until the next tutor turn starts.
  landed: { type: Boolean, default: false },
})

// U-01: history can contain assistant rows with nothing to show (e.g. a
// turn whose only output was tool activity that persisted no text).
// AssistantBubble would render them as an empty row, so they are
// skipped. Cancelled/partial rows keep their marker even without text.
function _renderable(m) {
  if (m.role === 'user') return true

  return Boolean(
    m.content ||
    m.check_batch ||
    m.tool_calls?.length ||
    m.citations?.length ||
    m.status === 'cancelled' ||
    m.status === 'partial',
  )
}

const visibleMessages = computed(() => props.messages.filter(_renderable))

// Index of the last rendered assistant row; the tick belongs to that turn.
const lastAssistantIndex = computed(() => {
  for (let i = visibleMessages.value.length - 1; i >= 0; i -= 1) {
    if (visibleMessages.value[i].role !== 'user') return i
  }

  return -1
})

function tickAt(i) {
  return props.landed && !props.streamingMessage && i === lastAssistantIndex.value
}

// Speaker-change gap: the rhythm of the thread grows when the voice changes.
// Based on visibleMessages (the rendered list), not the raw messages array,
// so a skipped-empty assistant row (U-01) never counts as a voice change.
function speakerChangeAt(i) {
  if (i === 0) return false

  return visibleMessages.value[i].role !== visibleMessages.value[i - 1].role
}

// The typing/streaming row is always the tutor; it grows the gap only when
// the last rendered turn was the learner's.
const trailingSpeakerChange = computed(() => {
  const last = visibleMessages.value[visibleMessages.value.length - 1]

  return last ? last.role === 'user' : false
})
</script>

<template>
  <div class="message-list">
    <TransitionGroup name="msg-fade" tag="div" class="msg-list">
      <!-- F-21: an optimistic user row has no server id until the turn is
           reloaded, so two of them in a row both fell back to the index and
           shared a key. client_id is the local stand-in; message_id still
           wins wherever it exists (it is also the pagination cursor, so a
           client value must never be written into it). Dup-key fix: a
           locally-cancelled assistant row carries the literal message_id
           'pending' (session.js handleCancelled) until reload, so two Stop
           clicks in one session shared that same string key -- 'pending'
           must be treated as no server id too. -->
      <template
        v-for="(m, i) in visibleMessages"
        :key="
          (m.message_id && m.message_id !== 'pending' ? m.message_id : null) ??
          m.client_id ??
          `m-${i}`
        "
      >
        <UserBubble
          v-if="m.role === 'user'"
          :class="{ 'msg-row--speaker-change': speakerChangeAt(i) }"
          :content="m.content || ''"
          :created-at="m.created_at || null"
        />
        <AssistantBubble
          v-else
          :class="{ 'msg-row--speaker-change': speakerChangeAt(i) }"
          :message="m"
          :streaming="false"
          :landed="tickAt(i)"
        />
      </template>
    </TransitionGroup>
    <article
      v-if="awaiting && !streamingMessage"
      :class="['msg', 'assistant', 'typing', { 'msg-row--speaker-change': trailingSpeakerChange }]"
      data-testid="msg-typing"
    >
      <div class="msg-gutter">
        <span class="role-tag">tutor</span>
      </div>
      <div class="msg-body">
        <!-- D-07: aria-label on a <p> is not a supported name source. The dots
             are decoration; the text lives in a visually-hidden sibling so
             `.typing-dots span` cannot style it as a fourth dot. -->
        <span class="sr-only">Tutor is thinking</span>
        <p class="content typing-dots"><span></span><span></span><span></span></p>
      </div>
    </article>
    <AssistantBubble
      v-if="streamingMessage"
      :class="{ 'msg-row--speaker-change': trailingSpeakerChange }"
      :message="streamingMessage"
      :streaming="true"
    />
  </div>
</template>

<style scoped>
.msg-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Speaker-change gap: 0.75rem inside one voice (the flex gap above), 1.5rem
   when the voice changes -- the extra margin stacks on top of the gap. */
.msg-list > .msg-row--speaker-change {
  margin-top: 0.75rem;
}

/* A card appears; it never slides. */
.msg-fade-enter-active {
  transition: opacity var(--motion-fast) ease;
}

.msg-fade-enter-from {
  opacity: 0;
}

.msg-fade-leave-active {
  transition: opacity var(--motion-fast) ease;
}

.msg-fade-leave-to {
  opacity: 0;
}

/* The typing row and the streaming turn are siblings of the list, not
   children of it: give them the same card gap as everything else. */
.msg-list + .msg.typing,
.msg-list + .msg.assistant {
  margin-top: 0.75rem;
}

.msg-list + .msg.typing.msg-row--speaker-change,
.msg-list + .msg.assistant.msg-row--speaker-change {
  margin-top: 1.5rem;
}

/* Typing indicator: a flat tutor turn with three dots instead of prose, the
   same measure as the settled turn so nothing jumps when the first token
   lands. Scoped to .typing so it never collides with the learner card. */
.msg.typing {
  align-self: flex-start;
  width: 78%;
  max-width: 78%;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.msg.typing .msg-gutter {
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

.msg.typing .content {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  margin: 0;
}

.typing-dots span {
  display: inline-block;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--pencil);
  animation: typing-fade 1200ms ease-in-out infinite;
}

.typing-dots span:nth-child(2) {
  animation-delay: 200ms;
}
.typing-dots span:nth-child(3) {
  animation-delay: 400ms;
}

@keyframes typing-fade {
  0%,
  60%,
  100% {
    opacity: 0.35;
  }
  30% {
    opacity: 1;
  }
}

/* The dots stop pulsing and settle between the two ends of the pulse, so the
   row still reads as pencil-weight waiting ink rather than a frozen frame. */
@media (prefers-reduced-motion: reduce) {
  .typing-dots span {
    animation: none;
    opacity: 0.6;
  }

  .msg-fade-enter-active,
  .msg-fade-leave-active {
    transition: none;
  }
}

@media (max-width: 599px) {
  .msg.typing {
    max-width: 92%;
  }
}
</style>
