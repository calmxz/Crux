<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  // Batch: { gap, total, currentIndex, viewIndex, setIndex, setTotal, items: [
  //   { question, options, status, selectedIndex, correctIndex, correct, explanation } ] }
  // setIndex / setTotal (1-based, #340) may be null; null means one set.
  check: { type: Object, required: true },
  // F-04: true while a stream is live; Skip/Back/Next/Done are disabled so the
  // follow-up stream cannot be started on top of an active one.
  busy: { type: Boolean, default: false },
  // E-17: true while this item's answer POST is in flight. `answered` only
  // flips once that POST returns, so without this the options stayed live in
  // between and a second click was swallowed by the store's silent guard.
  // Distinct from `busy`, which is about the follow-up stream.
  answering: { type: Boolean, default: false },
})

const emit = defineEmits(['answer', 'skip', 'back', 'next', 'done', 'stop'])

const LETTERS = ['A', 'B', 'C', 'D', 'E']

const isResolved = (it) => it.status === 'answered' || it.status === 'skipped'

const item = computed(() => props.check.items[props.check.viewIndex] || {})

const answered = computed(() => isResolved(item.value))

const correct = computed(() => item.value.correct === true)

const isFirst = computed(() => props.check.viewIndex <= 0)

const isLast = computed(() => props.check.viewIndex >= props.check.total - 1)

// #348: free navigation within one set. Next and Back move between items
// answered or not; Done waits until every item is answered or skipped (a skip
// is the explicit "don't know", #339), and once it is, Done shows on any item.
const resolvedCount = computed(() => props.check.items.filter(isResolved).length)

const allResolved = computed(() => resolvedCount.value >= props.check.total)

const showDone = computed(() => isLast.value || allResolved.value)

const showProgress = computed(() => props.check.total > 1)

// #340: the learner can end the check early while any item is unresolved;
// once all are resolved, Done closes it. Chatting never ends a check.
const canStop = computed(() => props.check.currentIndex < props.check.total)

// Hidden-until-graded: the explanation is a raise, not a hint.
const graded = computed(() => item.value.status === 'answered')

// #364: a check of M sets cuts the head rule into M segments. Done sets are
// full, the live set fills as its items resolve (a skip counts; counted from
// item status since #348 lets items resolve in any order), upcoming sets are
// empty. One set keeps today's single solid rule and no set words.
const setIndex = computed(() => props.check.setIndex ?? 1)

const setTotal = computed(() => props.check.setTotal ?? 1)

const multiSet = computed(() => setTotal.value > 1)

const segments = computed(() =>
  Array.from({ length: setTotal.value }, (_, k) => {
    const n = k + 1

    if (n < setIndex.value) return { state: 'is-done', fill: 1 }

    if (n > setIndex.value) return { state: 'is-todo', fill: 0 }

    return { state: 'is-live', fill: resolvedCount.value / props.check.total || 0 }
  }),
)

function optionClass(i) {
  if (item.value.status !== 'answered') return ''

  if (i === item.value.correctIndex) return 'is-correct'

  if (i === item.value.selectedIndex) return 'is-incorrect'

  return ''
}

const backBtn = ref(null)

const nextBtn = ref(null)

const doneBtn = ref(null)

// Focus the way on once the viewed item resolves -- not when Back/Next land
// on an item that was already answered.
watch(
  [() => props.check.viewIndex, answered],
  async ([view, resolved], [prevView, wasResolved]) => {
    if (view !== prevView || !resolved || wasResolved) return
    await nextTick()
    const target = allResolved.value ? doneBtn.value : (nextBtn.value ?? doneBtn.value)
    target?.focus()
  },
)

// Back vanishes on the first item and Next on the last; keep keyboard focus
// on the card instead of dropping it to the page.
async function go(dir) {
  emit(dir)
  await nextTick()
  const kept = dir === 'back' ? backBtn.value : nextBtn.value

  if (kept) return
  const other = dir === 'back' ? nextBtn.value : (backBtn.value ?? doneBtn.value)
  other?.focus()
}
</script>

<template>
  <section
    class="check-card"
    :class="{ answered, correct, incorrect: answered && !correct }"
    data-testid="check-card"
  >
    <div class="check-gutter" :class="{ 'is-segmented': multiSet }">
      <span class="role-tag"
        >check<span v-if="multiSet" class="check-set" data-testid="check-set">
          &middot; set {{ setIndex }} of {{ setTotal }}</span
        ></span
      >
      <p v-if="showProgress" class="check-progress" data-tabular>
        {{ check.viewIndex + 1 }}/{{ check.total }}
      </p>
    </div>
    <div v-if="multiSet" class="check-rule" data-testid="check-set-rule" aria-hidden="true">
      <span
        v-for="(s, k) in segments"
        :key="k"
        class="check-rule-seg"
        :class="s.state"
        :style="{ '--fill': s.fill }"
        :data-fill="s.fill"
        data-testid="check-rule-seg"
      ></span>
    </div>
    <div class="check-box">
      <p class="check-question">{{ item.question }}</p>

      <div
        class="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
        data-testid="check-live"
      >
        <template v-if="graded">
          {{ correct ? 'Correct.' : 'Not quite.' }} {{ item.explanation || '' }}
        </template>
      </div>

      <ul class="check-options" :aria-busy="answering ? 'true' : undefined">
        <li v-for="(opt, i) in item.options" :key="i">
          <button
            type="button"
            class="check-option"
            :class="optionClass(i)"
            data-testid="check-option"
            :aria-disabled="answered || answering ? 'true' : undefined"
            @click="answered || answering ? undefined : emit('answer', i)"
          >
            <span class="check-letter" aria-hidden="true">{{ LETTERS[i] ?? i + 1 }}.</span>
            <span class="check-option-text">{{ opt }}</span>
            <svg
              v-if="optionClass(i) === 'is-correct'"
              class="check-mark check-mark--tick"
              viewBox="0 0 16 16"
              width="16"
              height="16"
              aria-hidden="true"
              focusable="false"
            >
              <path d="M2.5 8.5 L6.3 12.2 L13.5 4" pathLength="1" />
            </svg>
            <svg
              v-else-if="optionClass(i) === 'is-incorrect'"
              class="check-mark check-mark--cross"
              viewBox="0 0 16 16"
              width="16"
              height="16"
              aria-hidden="true"
              focusable="false"
            >
              <path d="M4 4 L12 12" pathLength="1" />
              <path d="M12 4 L4 12" pathLength="1" />
            </svg>
          </button>
        </li>
      </ul>

      <p v-if="graded" class="check-verdict" data-testid="check-verdict">
        {{ correct ? 'Correct' : 'Not quite' }}
      </p>
      <p
        v-if="graded && item.explanation"
        class="check-explanation"
        data-testid="check-explanation"
      >
        {{ item.explanation }}
      </p>

      <button
        v-if="!answered"
        type="button"
        class="check-skip coarse-2x"
        data-testid="check-skip"
        :disabled="busy"
        @click="emit('skip')"
      >
        Skip this question
      </button>

      <div class="check-nav">
        <button
          v-if="!isFirst"
          ref="backBtn"
          type="button"
          class="check-next"
          data-testid="check-back"
          :disabled="busy"
          @click="go('back')"
        >
          Back
        </button>
        <button
          v-if="!isLast"
          ref="nextBtn"
          type="button"
          class="check-next"
          data-testid="check-next"
          :disabled="busy"
          @click="go('next')"
        >
          Next
        </button>
        <button
          v-if="showDone"
          ref="doneBtn"
          type="button"
          class="check-next"
          data-testid="check-done"
          :disabled="busy || !allResolved"
          @click="emit('done')"
        >
          Done
        </button>
      </div>

      <button
        v-if="canStop"
        type="button"
        class="check-stop coarse-2x"
        data-testid="check-stop"
        :disabled="busy || answering"
        @click="emit('stop')"
      >
        Stop check
      </button>
    </div>
  </section>
</template>

<style scoped>
/* The check card pauses the stack: same white stock as the tutor, but the
   head line carries a 3px graphite rule as part of the head, not a side
   border, and the card runs a touch wider. */
.check-card {
  max-width: 84%;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-radius: var(--radius-card);
  box-shadow: 0 1px 0 var(--card-drop);
  padding: 0.55rem 0.9rem 0.7rem;
}

.check-gutter {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  min-width: 0;
  padding-bottom: 0.4rem;
  border-bottom: 3px solid var(--ink);
}

.role-tag {
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  font-weight: 400;
  color: var(--pencil);
}

.check-box {
  /* Containing block for the sr-only live region below; without it the
     absolutely positioned box resolves against the page and can grow the
     document past the fold on mobile. */
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 0.5rem;
  font-family: var(--font-sans);
}

/* The count sits in the head line's right slot, matching tutor/learner
   cards' timestamp -- same size as the "check" role label, pencil ink. */
.check-progress {
  margin: 0;
  flex: 0 0 auto;
  font-size: var(--fs-label);
  color: var(--pencil);
}

/* 390px: the set phrase never breaks, so the head line holds one baseline. */
.check-set {
  white-space: nowrap;
}

/* #364: with more than one set the head rule is the progress. The gutter
   drops its border and a 3px rule of M segments takes its place; the
   negative margin cancels the card's flex gap so it sits where the border
   was. */
.check-gutter.is-segmented {
  border-bottom: 0;
}

.check-rule {
  display: flex;
  gap: 4px;
  height: 3px;
  margin-top: -0.5rem;
}

.check-rule-seg {
  position: relative;
  flex: 1 1 0;
  overflow: hidden;
  background: var(--rule-strong);
}

.check-rule-seg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--ink);
  transform: scaleX(var(--fill, 0));
  transform-origin: left;
  transition: transform var(--motion-base) cubic-bezier(0.16, 1, 0.3, 1);
}

.check-question {
  margin: 0;
  font-size: var(--fs-body);
  font-weight: 700;
  line-height: var(--lh-body);
  color: var(--ink);
}

.check-options {
  list-style: none;
  margin: 0;
  padding: 0;
}

.check-option {
  display: flex;
  align-items: baseline;
  gap: 0.625rem;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 0;
  /* Painted, not laid out: a border-bottom made every option 29px. */
  box-shadow: inset 0 -1px 0 var(--rule);
  border-radius: 0;
  padding: 0.4rem 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink);
  cursor: pointer;
}

.check-letter {
  flex: 0 0 auto;
  color: var(--ink-learner);
  font-weight: 700;
}

.check-option-text {
  flex: 1 1 auto;
  min-width: 0;
}

.check-option:not([aria-disabled='true']):hover .check-option-text {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.check-option:not([aria-disabled='true']):focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.check-option[aria-disabled='true'] {
  cursor: default;
}

/* Grading is the marker's hand: red marks beside the line, never a fill. */
.check-mark {
  flex: 0 0 auto;
  align-self: center;
  fill: none;
  stroke: var(--ink-marker);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 1;
  animation: mark-draw var(--motion-base) cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes mark-draw {
  from {
    stroke-dashoffset: 1;
  }
  to {
    stroke-dashoffset: 0;
  }
}

.check-option.is-incorrect .check-option-text {
  color: var(--pencil);
}

.check-verdict {
  margin: 0;
  font-size: var(--fs-body);
  font-weight: 700;
  line-height: var(--lh-body);
  color: var(--ink);
}

.check-card.incorrect .check-verdict {
  color: var(--ink-marker-text);
}

.check-explanation {
  margin: 0;
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink);
}

/* #348: Back, Next and Done share one line, in reading order. */
.check-nav {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 1.25rem;
}

.check-skip,
.check-next,
.check-stop {
  align-self: flex-start;
  background: transparent;
  border: 0;
  padding: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  color: var(--ink-learner);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.check-skip:disabled,
.check-next:disabled,
.check-stop:disabled {
  color: var(--pencil);
  cursor: default;
  pointer-events: none;
  text-decoration: none;
}

.check-skip:focus-visible,
.check-next:focus-visible,
.check-stop:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

/* Ending the check is the quieter exit: pencil ink, not the learner blue. */
.check-stop {
  color: var(--pencil);
}

@media (prefers-reduced-motion: reduce) {
  .check-mark {
    animation: none;
    stroke-dashoffset: 0;
  }

  .check-rule-seg::after {
    transition: none;
  }
}

@media (max-width: 599px) {
  .check-card {
    max-width: 92%;
  }
}

/* R1: rows have only a painted separator between them -- fine for a mouse,
   too tight to tap reliably. On coarse pointers only, grow each row and
   centre the letter and text within it; the inset box-shadow separator
   keeps the ruled look unchanged. */
@media (pointer: coarse) {
  .check-option {
    min-height: 3.5rem;
    align-items: center;
  }
}
</style>
