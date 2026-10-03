<template>
  <section class="appearance" data-testid="settings-appearance">
    <h2 class="heading">Appearance</h2>
    <p class="note">The same desk, with the lamp on or off.</p>

    <fieldset class="modes" data-testid="settings-theme-toggle">
      <legend class="sr-only">Theme</legend>
      <label
        v-for="opt in MODES"
        :key="opt.value"
        class="mode"
        :class="{ selected: override === opt.value }"
      >
        <input
          type="radio"
          class="mode-input"
          name="crux-theme"
          :value="opt.value"
          :checked="override === opt.value"
          :data-testid="`settings-theme-${opt.value}`"
          @change="setTheme(opt.value)"
        />
        <span class="mode-swatch" aria-hidden="true">
          <span v-if="opt.value === 'auto'" class="sw-split">
            <span class="sw-half sw-light">
              <span class="sw-desk" />
              <span class="sw-card" />
            </span>
            <span class="sw-half sw-dark">
              <span class="sw-desk" />
              <span class="sw-card" />
            </span>
          </span>
          <span v-else :class="['sw-stack', `sw-${opt.value}`]">
            <span class="sw-desk" />
            <span class="sw-card" />
          </span>
        </span>
        <span class="mode-line">
          <span class="mode-label" :data-label="opt.label">{{ opt.label }}</span>
          <svg
            class="mode-tick"
            :class="{ 'mode-tick--on': override === opt.value }"
            viewBox="0 0 12 12"
            width="12"
            height="12"
            aria-hidden="true"
            focusable="false"
          >
            <path :d="TICK_PATH" />
          </svg>
        </span>
      </label>
    </fieldset>
  </section>
</template>

<script setup>
import { useTheme } from '../../composables/useTheme.js'
import { TICK_PATH } from '../chat/levelMark.js'

const { override, setTheme } = useTheme()

const MODES = [
  { value: 'light', label: 'Lamp on' },
  { value: 'dark', label: 'Lamp off' },
  { value: 'auto', label: 'Match system' },
]
</script>

<style scoped>
.appearance {
  display: flex;
  flex-direction: column;
}

.heading {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--line-pitch);
  color: var(--ink);
}

.note {
  margin: 0 0 var(--line-pitch);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--line-pitch);
  color: var(--pencil);
}

.modes {
  display: flex;
  gap: 3rem;
  border: 0;
  padding: 0;
  margin: 0;
}

.mode {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  cursor: pointer;
}

.mode-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

/* Each swatch is two small stacked cards drawn in the theme it names, so the
   light swatch stays light while the app is dark. Theme tokens cascade from
   :root[data-theme], so they cannot express "the other theme" here: the
   ground and card layers come from the theme-independent --sw-* tokens
   declared once in base.css's plain :root block. The card's stroke is the
   live accent so it reads as blue, the one colour that carries across both
   themes. The system swatch cannot be drawn from the live tokens either --
   that would just mirror whichever theme happens to be active -- so it is
   drawn as half light stack, half dark stack, literally split down the
   middle. */
.mode-swatch {
  display: inline-flex;
}

/* One pair of theme classes, worn by the whole stack or by half of the split
   system swatch. */
.sw-light {
  --sw-desk: var(--sw-light-paper);
  --sw-card: var(--sw-light-rule);
  --sw-ink: var(--sw-light-ink);
}

.sw-dark {
  --sw-desk: var(--sw-dark-paper);
  --sw-card: var(--sw-dark-rule);
  --sw-ink: var(--sw-dark-ink);
}

.sw-stack,
.sw-half {
  position: relative;
  display: inline-block;
  height: 72px;
}

.sw-stack {
  width: 56px;
}

.sw-half {
  width: 28px;
}

.sw-split {
  display: flex;
}

.sw-desk {
  position: absolute;
  inset: 0;
  background: var(--sw-desk);
  border: 1px solid var(--sw-ink);
  border-radius: var(--radius-card);
}

.sw-card {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 3px;
  bottom: 3px;
  background: var(--sw-card);
  border: 2px solid var(--color-accent);
  border-radius: var(--radius-card);
}

.mode-line {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.mode-label {
  position: relative;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--line-pitch);
  color: var(--ink);
}

/* Reserves the width the label would need at 700 weight, invisibly, so
   selecting a mode never widens its label and pushes its siblings. */
.mode-label::after {
  content: attr(data-label);
  display: block;
  height: 0;
  overflow: hidden;
  visibility: hidden;
  pointer-events: none;
  font-weight: 700;
}

.mode.selected .mode-label {
  font-weight: 700;
}

.mode:hover .mode-label {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.mode-tick {
  flex: 0 0 auto;
  visibility: hidden;
  fill: none;
  stroke: var(--ink-learner);
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.mode-tick--on {
  visibility: visible;
}

.mode:has(.mode-input:focus-visible) {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}
</style>
