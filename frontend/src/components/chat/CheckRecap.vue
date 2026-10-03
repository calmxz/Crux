<script setup>
import { computed } from 'vue'

// Batch (camelCase, mapped by the session store):
//   { gap, total, setIndex, setTotal, items: [
//     { question, options, status, selectedIndex, correctIndex, correct, explanation } ] }
// setIndex / setTotal (1-based, #340) may be null; null means one set.
const props = defineProps({
  batch: { type: Object, required: true },
})

// #364: the same segmented head rule as the check card, sets 1..N done. The
// next set is not signposted here; the tutor's lead-in line carries that.
const setIndex = computed(() => props.batch.setIndex ?? 1)

const setTotal = computed(() => props.batch.setTotal ?? 1)

const multiSet = computed(() => setTotal.value > 1)

const LETTERS = ['A', 'B', 'C', 'D', 'E']

const items = computed(() => props.batch.items || [])

const graded = computed(() => items.value.filter((it) => it.status === 'answered'))

const nCorrect = computed(() => graded.value.filter((it) => it.correct === true).length)

function optionClass(item, i) {
  if (i === item.correctIndex) return 'is-correct'

  if (item.selectedIndex != null && i === item.selectedIndex) return 'is-incorrect'

  return ''
}

function isYourAnswer(item, i) {
  return item.selectedIndex != null && i === item.selectedIndex
}
</script>

<template>
  <section class="recap-card" data-testid="check-recap">
    <header class="recap-header" :class="{ 'is-segmented': multiSet }">
      <span class="recap-score" data-testid="recap-score" data-tabular>
        {{ nCorrect }} / {{ graded.length }}
      </span>
      <span v-if="multiSet" class="recap-gap">
        <span class="recap-gap-name" :title="batch.gap">{{ batch.gap }}</span>
        <span class="recap-set" data-testid="recap-set"
          >&middot; set {{ setIndex }} of {{ setTotal }}</span
        >
      </span>
      <span v-else class="recap-gap">{{ batch.gap }}</span>
    </header>
    <div v-if="multiSet" class="recap-rule" data-testid="recap-set-rule" aria-hidden="true">
      <span
        v-for="n in setTotal"
        :key="n"
        class="recap-rule-seg"
        :class="n <= setIndex ? 'is-done' : 'is-todo'"
        data-testid="recap-rule-seg"
      ></span>
    </div>

    <div v-for="(item, qi) in items" :key="qi" class="recap-item">
      <p class="recap-question">{{ item.question }}</p>
      <ul class="recap-options">
        <li
          v-for="(opt, i) in item.options"
          :key="i"
          class="recap-option"
          :class="optionClass(item, i)"
          data-testid="recap-option"
        >
          <span class="recap-letter" aria-hidden="true">{{ LETTERS[i] ?? i + 1 }}.</span>
          <span class="recap-option-text">{{ opt }}</span>
          <span v-if="isYourAnswer(item, i)" class="recap-tag">your answer</span>
          <span v-else-if="i === item.correctIndex" class="recap-tag">correct</span>
          <svg
            v-if="i === item.correctIndex"
            class="recap-mark"
            viewBox="0 0 16 16"
            width="16"
            height="16"
            aria-hidden="true"
            focusable="false"
          >
            <path d="M2.5 8.5 L6.3 12.2 L13.5 4" pathLength="1" />
          </svg>
        </li>
      </ul>
      <p v-if="item.selectedIndex == null" class="recap-norecord">Answer not recorded</p>
      <p v-if="item.explanation" class="recap-explanation">{{ item.explanation }}</p>
    </div>
  </section>
</template>

<style scoped>
/* Same card grammar as the check: the score is set in title-size, text-safe
   red beside the gap name. */
.recap-card {
  max-width: 84%;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-radius: var(--radius-card);
  box-shadow: 0 1px 0 var(--card-drop);
  padding: 0.55rem 0.9rem 0.7rem;
  font-family: var(--font-sans);
}

.recap-header {
  display: flex;
  align-items: baseline;
  gap: 0.625rem;
  padding-bottom: 0.4rem;
  border-bottom: 3px solid var(--ink);
}

.recap-score {
  font-family: var(--font-display);
  font-size: var(--fs-h2);
  font-weight: 600;
  color: var(--ink-marker-text);
}

.recap-gap {
  font-size: var(--fs-caption);
  color: var(--pencil);
}

/* 390px: the recap card is narrow, and a long gap name beside the set phrase
   would wrap the head line and crush the score onto two lines. The score and
   the set phrase never break; the gap name gives way with an ellipsis (its
   full name is in the title), so the head line holds one baseline. */
.recap-score {
  flex-shrink: 0;
  white-space: nowrap;
}

.recap-header.is-segmented .recap-gap {
  display: flex;
  gap: 0.3em;
  min-width: 0;
}

.recap-gap-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recap-set {
  flex-shrink: 0;
  white-space: nowrap;
}

/* #364: with more than one set the head rule is the progress; the negative
   margin cancels the card's flex gap so it sits where the border was. */
.recap-header.is-segmented {
  border-bottom: 0;
}

.recap-rule {
  display: flex;
  gap: 4px;
  height: 3px;
  margin-top: -0.6rem;
}

.recap-rule-seg {
  flex: 1 1 0;
  background: var(--rule-strong);
}

.recap-rule-seg.is-done {
  background: var(--ink);
}

.recap-item {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.recap-question {
  margin: 0;
  font-size: var(--fs-body);
  font-weight: 700;
  line-height: var(--lh-body);
  color: var(--ink);
}

.recap-options {
  list-style: none;
  margin: 0;
  padding: 0;
}

.recap-option {
  display: flex;
  align-items: baseline;
  gap: 0.625rem;
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink);
}

.recap-letter {
  flex: 0 0 auto;
  color: var(--ink-learner);
  font-weight: 700;
}

.recap-option-text {
  flex: 1 1 auto;
  min-width: 0;
}

/* Your answer is in your own ink; the correct one is ticked in red. */
.recap-option.is-incorrect .recap-option-text {
  color: var(--ink-learner);
  text-decoration: line-through;
  text-decoration-color: var(--ink-marker);
}

/* Not baseline-aligned: a 13px item on a 17px baseline adds half a pixel to
   the option row. Its own line-height is a full pitch, so it still reads level. */
.recap-tag {
  flex-shrink: 0;
  align-self: flex-start;
  font-size: var(--fs-label);
  color: var(--pencil);
}

.recap-mark {
  flex: 0 0 auto;
  align-self: center;
  fill: none;
  stroke: var(--ink-marker);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 1;
  animation: recap-mark-draw var(--motion-base) cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes recap-mark-draw {
  from {
    stroke-dashoffset: 1;
  }
  to {
    stroke-dashoffset: 0;
  }
}

.recap-norecord {
  margin: 0;
  font-size: var(--fs-caption);
  font-style: italic;
  line-height: var(--lh-body);
  color: var(--pencil);
}

.recap-explanation {
  margin: 0;
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--pencil);
}

@media (prefers-reduced-motion: reduce) {
  .recap-mark {
    animation: none;
    stroke-dashoffset: 0;
  }
}
</style>
