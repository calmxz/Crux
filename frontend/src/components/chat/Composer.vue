<template>
  <div class="composer-wrap">
    <input
      ref="fileInputEl"
      type="file"
      accept=".pdf,.pptx,.txt,.md"
      data-testid="session-upload-input"
      hidden
      @change="onFileChange"
    />

    <div class="composer" :class="{ 'is-disabled': disabled }">
      <button
        type="button"
        class="composer-attach hit-44"
        data-testid="session-upload-btn"
        :disabled="disabled || uploading"
        :aria-label="uploading ? 'Uploading file' : 'Attach a reference file'"
        :title="uploading ? 'Uploading...' : 'Attach a reference file (PDF, PPTX, TXT, MD)'"
        @click="openFilePicker"
      >
        <svg
          v-if="!uploading"
          class="composer-icon"
          viewBox="0 0 20 20"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <path
            d="M17.87 9.21 l-7.66 7.66 a5 5 0 0 1 -7.08 -7.08 l7.66 -7.66 a3.33 3.33 0 0 1 4.72 4.72 l-7.67 7.66 a1.67 1.67 0 0 1 -2.36 -2.36 l7.08 -7.07"
          />
        </svg>
        <svg
          v-else
          class="composer-icon composer-spinner spin"
          viewBox="0 0 20 20"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M17 10 A7 7 0 1 1 10 3" />
        </svg>
      </button>

      <textarea
        ref="composerEl"
        :value="modelValue"
        data-testid="session-input"
        class="composer-input"
        rows="1"
        placeholder="Ask anything."
        :disabled="disabled"
        :maxlength="MAX_DRAFT_LEN"
        aria-label="Message the tutor"
        :aria-describedby="describedbyIds"
        @input="onInput"
        @keydown="onKeydown"
      />

      <button
        v-if="streamState === 'idle'"
        type="button"
        class="composer-send hit-44"
        :class="{ 'is-armed': sendArmed }"
        data-testid="session-send"
        :disabled="disabled || !modelValue.trim() || sending"
        :aria-label="sending ? 'Sending message' : 'Send message'"
        @click="emit('send')"
      >
        <svg
          class="composer-icon"
          :class="sending ? 'composer-spinner spin' : ''"
          viewBox="0 0 20 20"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <path v-if="sending" d="M17 10 A7 7 0 1 1 10 3" />
          <template v-else>
            <path d="M10 16.5 L10 3.5" />
            <path d="M4.5 9 L10 3.5 L15.5 9" />
          </template>
        </svg>
      </button>

      <button
        v-else
        type="button"
        class="composer-stop hit-44"
        data-testid="session-stop"
        :disabled="streamState === 'stopping'"
        aria-label="Stop generating"
        @click="emit('stop')"
      >
        <svg
          class="composer-icon"
          viewBox="0 0 20 20"
          width="20"
          height="20"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
          focusable="false"
        >
          <rect x="5" y="5" width="10" height="10" />
        </svg>
      </button>
    </div>

    <div class="composer-hints" :class="{ 'is-near-limit': nearCharLimit }">
      <span class="composer-hint">Enter to send, Shift + Enter for a new line</span>
      <!-- The spinner's caption in words. Hidden visually while the arc turns;
           under reduced motion the arc goes and this line takes its place. The
           buttons carry the same wording as their accessible name, so this is
           never announced twice. -->
      <span
        v-if="uploading || sending"
        class="composer-busy sr-only"
        aria-hidden="true"
        data-testid="composer-busy"
      >
        {{ uploading ? 'Uploading file' : 'Sending message' }}
      </span>
      <!-- D-09: the counter itself is silent. It changes on every keystroke, so
           announcing it would talk over the typing. The length rule is a static
           description on the textarea instead, and only the last stretch before
           the cap is announced, from the live region below. -->
      <span v-if="modelValue.length" class="composer-count" data-tabular>
        {{ modelValue.length.toLocaleString() }} / {{ MAX_DRAFT_LEN.toLocaleString() }}
      </span>
    </div>

    <span :id="LIMIT_HINT_ID" class="sr-only">
      Up to {{ MAX_DRAFT_LEN.toLocaleString() }} characters.
    </span>
    <!-- Always in the DOM: a live region has to exist before its text changes
         or the change is not announced. Empty until the draft is near the cap. -->
    <span class="sr-only" role="status" aria-live="polite" data-testid="composer-limit-live">
      {{ limitAnnouncement }}
    </span>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  uploading: { type: Boolean, default: false },
  sending: { type: Boolean, default: false },
  streamState: { type: String, default: 'idle' },
  // id(s) of an element explaining why the composer is disabled (e.g. the active
  // cap banner). Wired to aria-describedby so SR users hear the reason on focus.
  describedby: { type: String, default: null },
})

const emit = defineEmits(['update:modelValue', 'send', 'stop', 'attach'])

const composerEl = ref(null)

const fileInputEl = ref(null)

// I-10: matches ChatRequest.message maxLength in the API contract.
const MAX_DRAFT_LEN = 4000

// Six pitches: the textarea grows from one ruled line to six, then scrolls.
const COMPOSER_MAX_HEIGHT_PX = 168

const nearCharLimit = computed(() => props.modelValue.length >= MAX_DRAFT_LEN * 0.9)

// D-09: static description of the cap, announced once on focus.
const LIMIT_HINT_ID = 'composer-char-limit'

// The parent may point the composer at a cap banner too; both descriptions are
// wanted, so the ids are merged rather than overwritten.
const describedbyIds = computed(() => [props.describedby, LIMIT_HINT_ID].filter(Boolean).join(' '))

// Silent until the draft is within 10% of the cap, then one short line per
// change; at the cap the wording says so outright.
const limitAnnouncement = computed(() => {
  const left = MAX_DRAFT_LEN - props.modelValue.length

  if (left <= 0) return 'Character limit reached'

  if (!nearCharLimit.value) return ''

  return `${left.toLocaleString()} character${left === 1 ? '' : 's'} left`
})

// A draft worth sending arms the send control: the drawn arrow sits on a
// filled blue square instead of on the page.
const sendArmed = computed(() => !props.disabled && Boolean(props.modelValue.trim()))

function autoResize() {
  const inner = composerEl.value

  if (!inner) return
  inner.style.height = 'auto'
  const next = Math.min(inner.scrollHeight, COMPOSER_MAX_HEIGHT_PX)
  inner.style.height = `${next}px`
}

// Every draft change reaches the textarea through v-model, so this covers
// typing as well as programmatic writes (quick prompts, restored drafts,
// clear-on-send); onInput does not need its own resize call.
watch(
  () => props.modelValue,
  () => nextTick(autoResize),
)

function onInput(e) {
  emit('update:modelValue', e.target.value)
}

function onKeydown(ev) {
  if (
    ev.key === 'Enter' &&
    !ev.shiftKey &&
    !ev.isComposing &&
    props.streamState === 'idle' &&
    !props.disabled &&
    props.modelValue.trim() &&
    !props.sending
  ) {
    ev.preventDefault()
    emit('send')
  }
}

function openFilePicker() {
  fileInputEl.value?.click()
}

function onFileChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''

  if (file) {
    emit('attach', file)
  }
}

function focus() {
  const el = composerEl.value

  if (el) {
    el.focus()
    autoResize()
  }
}

defineExpose({ focus })
</script>

<style scoped>
/* The composer is a white card, same grammar as a turn: the learner writes
   inside it, attach sits left, send is a 28px blue square that arms on a
   non-empty draft. */
.composer-wrap {
  display: flex;
  flex-direction: column;
}

.composer {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: end;
  gap: 0.5rem;
  padding: 0.55rem 0.9rem;
  background: var(--card);
  /* D-20: this is the resting edge of a text control, not card chrome, so it
     takes the 3:1 token (base.css) rather than --card-edge. */
  border: 1px solid var(--control-edge);
  border-radius: var(--radius-card);
  box-shadow: 0 1px 0 var(--card-drop);
  transition: border-color var(--motion-fast) ease;
}

.composer:focus-within {
  border-color: var(--ink-learner);
}

/* A disabled control is exempt from 1.4.11, and the faint card edge is what
   says it is out of play -- so this deliberately stays on --card-edge. */
.composer.is-disabled {
  border-color: var(--card-edge);
}

.composer.is-disabled .composer-input,
.composer.is-disabled .composer-input::placeholder {
  color: var(--pencil);
}

.composer-input {
  grid-column: 2;
  align-self: stretch;
  width: 100%;
  min-height: 1.75rem;
  /* COMPOSER_MAX_HEIGHT_PX (168px) in <script>, in rem. autoResize clamps the
     inline height, but it only runs once the draft first changes, so this caps
     the frames before that -- and it tracks the root font size, which the px
     clamp cannot. */
  max-height: 10.5rem;
  padding: 0;
  margin: 0;
  background: transparent;
  border: 0;
  outline: 0;
  resize: none;
  overflow-y: auto;

  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink-learner);
  caret-color: var(--ink-learner);

  scrollbar-width: thin;
  scrollbar-color: var(--rule-strong) transparent;
}

.composer-input::placeholder {
  color: var(--pencil);
  opacity: 1;
}

.composer-input::-webkit-scrollbar {
  width: 8px;
}
.composer-input::-webkit-scrollbar-button {
  display: none;
  height: 0;
  width: 0;
}
.composer-input::-webkit-scrollbar-track {
  background: transparent;
}
.composer-input::-webkit-scrollbar-thumb {
  background: var(--rule-strong);
  border: 2px solid transparent;
  background-clip: padding-box;
}

/* Attach and stop are drawn icons in the learner's ink; send is the 28px
   blue square that arms once there is a draft to send. */
.composer-attach,
.composer-send,
.composer-stop {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  background: transparent;
  border: 0;
  border-radius: var(--radius-sm);
  font-size: 1rem;
  color: var(--ink-learner);
  cursor: pointer;
  transition: color var(--motion-fast) ease;
}

/* Drawn strokes, not a glyph font: one weight, round ends, the button's ink. */
.composer-icon {
  flex: 0 0 auto;
  position: relative;
}

/* The fill is a pseudo-element under the arrow, faded in and out; the square
   itself never changes size, so nothing on the line moves. .hit-44 already
   makes the button a positioning context and owns ::after for its hit area. */
.composer-send::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--color-accent-strong);
  border-radius: var(--radius-sm);
  opacity: 0;
  transition: opacity var(--motion-fast) ease;
}

.composer-send.is-armed::before {
  opacity: 1;
}

.composer-send.is-armed {
  color: var(--color-text-on-accent);
}

.composer-attach {
  grid-column: 1;
  align-self: end;
}

.composer-send,
.composer-stop {
  grid-column: 3;
  align-self: end;
}

.composer-attach:focus-visible,
.composer-send:focus-visible,
.composer-stop:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.composer-stop {
  color: var(--ink-marker-text);
}

/* An armed send stays filled while it is sending, so the square does not
   blink off and on again between the click and the first token. */
.composer-attach:disabled,
.composer-stop:disabled,
.composer-send:disabled:not(.is-armed) {
  color: var(--pencil);
}

/* An armed send greys out nowhere, but every disabled control still refuses
   the pointer. */
.composer-input:disabled,
.composer-attach:disabled,
.composer-stop:disabled,
.composer-send:disabled {
  cursor: not-allowed;
}

/* Hints in pencil under the card. */
.composer-hints {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.3rem 0.2rem 0;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  color: var(--pencil);
  user-select: none;
}

.composer-count {
  transition: color var(--motion-fast) ease;
}

.composer-hints.is-near-limit .composer-count {
  color: var(--ink-marker-text);
  font-weight: 700;
}

/* .spin (base.css) does the rotation; the arc is a whole <svg> so it turns
   about its own centre. The caption beside it is out of sight while it turns
   -- .sr-only (base.css) hides it; the override below brings it back.

   A still arc says nothing, so under reduced motion it leaves and its caption
   is written on the hint line instead, in pencil on the pitch. */
@media (prefers-reduced-motion: reduce) {
  .composer-spinner {
    display: none;
  }

  .composer-busy {
    position: static;
    width: auto;
    height: auto;
    margin: 0;
    overflow: visible;
    clip: auto;
    font-size: var(--fs-label);
    line-height: var(--lh-body);
    color: var(--pencil);
  }
}

@media (max-width: 599px) {
  .composer-hint {
    display: none;
  }
}
</style>
