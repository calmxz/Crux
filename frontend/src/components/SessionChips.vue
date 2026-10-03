<script setup>
import { LEVEL_MARK_PATH, TICK_PATH, levelStroke } from './chat/levelMark.js'

defineProps({
  /** Optional id so consumers can reference the chip row from aria-describedby. */
  id: { type: String, default: undefined },
  /** Output of cardChips(session): [{ type, label, count?, level? }]. */
  chips: { type: Array, required: true },
  /** 'rail' (sidebar, compact) | 'card' (home/library, full-size). */
  variant: {
    type: String,
    default: 'card',
    validator: (v) => ['rail', 'card'].includes(v),
  },
})
</script>

<template>
  <span class="chips" :id="id" :class="`chips--${variant}`" data-testid="session-chips">
    <template v-for="chip in chips" :key="chip.type">
      <span v-if="chip.type === 'focus'" class="chip chip--focus" data-testid="chip-focus">
        <span class="chip-glyph" aria-hidden="true">
          <svg viewBox="0 0 12 12" width="10" height="10" focusable="false">
            <path d="M1 6 L11 6" />
          </svg>
        </span>
        <span v-if="variant !== 'card'" class="sr-only">Focus:</span>
        <!-- single text node so the "Focus: " space is a real space, not NBSP/condensed -->
        <span class="chip-text">{{
          variant === 'card' ? `Focus: ${chip.label}` : chip.label
        }}</span>
      </span>
      <span v-else-if="chip.type === 'level'" class="chip chip--level" data-testid="chip-level">
        <span class="chip-glyph" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="12" focusable="false">
            <path :d="LEVEL_MARK_PATH" :stroke-width="levelStroke(chip.level)" />
          </svg>
        </span>
        <span class="chip-text">{{ chip.label }}</span>
      </span>
      <span
        v-else-if="chip.type === 'mastered'"
        class="chip chip--mastered"
        data-testid="chip-mastered"
      >
        <span class="chip-glyph" aria-hidden="true">
          <svg viewBox="0 0 12 12" width="10" height="10" focusable="false">
            <path :d="TICK_PATH" />
          </svg>
        </span>
        <span class="chip-text">{{ variant === 'card' ? chip.label : chip.count }}</span>
        <span v-if="variant !== 'card'" class="sr-only"> mastered</span>
      </span>
    </template>
  </span>
</template>

<style scoped>
/* The three-cell label: topic sits with the row, this carries focus / level /
   mastered count. Marks are drawn, never unicode glyphs. */
.chips {
  display: inline-flex;
  align-items: baseline;
  gap: 0.75rem;
  min-width: 0;
  max-width: 100%;
}

.chip {
  display: inline-flex;
  align-items: baseline;
  gap: 0.3125rem;
  min-width: 0;
  max-width: 100%;
  padding: 0.15rem 0.5rem;
  font-size: var(--fs-label);
  line-height: var(--lh-body);
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-radius: var(--radius-card);
  box-shadow: 0 1px 0 var(--card-drop);
  font-family: var(--font-sans);
  white-space: nowrap;
}

.chip-glyph {
  display: inline-flex;
  align-self: center;
  flex: 0 0 auto;
}

.chip-glyph svg {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.chip--focus {
  color: var(--ink);
}

.chip--focus .chip-glyph {
  color: var(--ink-marker);
}

.chip--level {
  color: var(--pencil);
}

.chip--level .chip-glyph {
  color: var(--ink);
}

.chip--mastered {
  /* fixed-content chip: never shrinks; the focus chip absorbs all flex shrinkage */
  flex-shrink: 0;
  color: var(--pencil);
}

.chip--mastered .chip-glyph {
  color: var(--ink-learner);
}

.chip-text {
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.chips--rail .chip--focus .chip-text {
  max-width: 8rem;
}

.chips--card .chip--focus .chip-text {
  max-width: 18rem;
}
</style>
