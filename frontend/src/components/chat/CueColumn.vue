<script setup>
import { computed, ref, watch } from 'vue'

import { usePanel } from '@/composables/usePanel.js'
import { NARROW_QUERY, useMediaQuery } from '@/composables/useMediaQuery.js'
import { entryNames } from '@/utils/conceptEntry.js'
import { LEVEL_MARK_PATH, TICK_PATH, levelStroke as levelStrokeFor } from './levelMark.js'

const props = defineProps({
  // TopicProfile as served by the API: knowledge_level, subtopic_levels,
  // confirmed_gaps[], mastered_concepts[], focus_target_gap.
  profile: { type: Object, default: null },
  // Discriminator: a different session reseeds the "already seen" set so
  // switching sessions never replays the reveal for pre-existing entries.
  sessionId: { type: String, default: '' },
  // Cue currently under an open check batch; marked, never recoloured.
  testingGap: { type: String, default: '' },
})

const emit = defineEmits(['landed'])

const level = computed(() => props.profile?.knowledge_level ?? null)

const levelLabel = computed(() => level.value || 'level not set')

const levelStroke = computed(() => levelStrokeFor(level.value))

const focus = computed(() => props.profile?.focus_target_gap || '')

const gaps = computed(() => entryNames(props.profile?.confirmed_gaps).filter(Boolean))

const mastered = computed(() => entryNames(props.profile?.mastered_concepts).filter(Boolean))

// The focus cue has its own section; listing it twice would read as two gaps.
const openGaps = computed(() => gaps.value.filter((g) => g !== focus.value))

// The strip counts what the Gaps section actually lists, and says "1 gap".
// "mastered" is already a participle, so it never takes a plural.
const gapsCount = computed(() =>
  openGaps.value.length === 1 ? '1 gap' : `${openGaps.value.length} gaps`,
)

const subtopics = computed(() => {
  const map = props.profile?.subtopic_levels ?? {}

  return Object.keys(map).map((name) => ({
    name,
    level: map[name],
    stroke: levelStrokeFor(map[name]),
  }))
})

// Cue-lands. Every name currently on the page as one flat list; the first
// non-null profile for a session seeds the set without animating, and only
// later additions get the filing motion.
const allNames = computed(() => [
  ...(focus.value ? [`focus:${focus.value}`] : []),
  ...openGaps.value.map((g) => `gap:${g}`),
  ...mastered.value.map((m) => `mastered:${m}`),
])

const seen = ref(new Set())

const fresh = ref(new Set())

let seededFor = null

watch(
  [() => props.sessionId, () => props.profile, allNames],
  ([sid, profile, names]) => {
    if (!profile) return

    if (sid !== seededFor) {
      seededFor = sid
      seen.value = new Set(names)
      fresh.value = new Set()

      return
    }

    const added = names.filter((n) => !seen.value.has(n))
    seen.value = new Set(names)

    if (!added.length) return
    fresh.value = new Set(added)
    emit('landed', added)
  },
  { immediate: true },
)

function isFresh(key) {
  return fresh.value.has(key)
}

// Below 900px the column collapses to the strip; the disclosure opens the same
// dividers as a sheet over the thread. The switch is CSS-only (see the media
// block), so there is one instance and one landed stream at every width.
const expanded = ref(false)

// Panel collapse (desktop). usePanel owns the state and the persistence;
// SessionView reads the same flag for the column width.
const { collapsed: panelCollapsed, toggleDesktop } = usePanel()

// The collapsed form is a vertical tab rail inside a 2.75rem column, and that
// column only exists at >= 900px -- below it the panel is the horizontal strip.
// Without this guard a panel collapsed on a laptop would follow the user down
// to a phone width and hide the profile behind a rail that has nowhere to sit.
const isNarrow = useMediaQuery(NARROW_QUERY)

const isCollapsed = computed(() => panelCollapsed.value && !isNarrow.value)
</script>

<template>
  <aside
    class="cue"
    :class="{ 'is-expanded': expanded, 'is-collapsed': isCollapsed }"
    data-testid="cue-column"
    aria-label="What the tutor knows"
  >
    <!-- Half-tab on the panel's left edge, the mirror of the sidebar's own
         toggle. Hidden below 900px, where the panel has no column to collapse. -->
    <button
      type="button"
      class="cue-toggle hit-44"
      data-testid="cue-collapse-toggle"
      :aria-label="isCollapsed ? 'Expand profile' : 'Collapse profile'"
      @click="toggleDesktop"
    >
      <svg
        class="cue-toggle-mark"
        viewBox="0 0 12 12"
        width="12"
        height="12"
        fill="none"
        stroke="currentColor"
        stroke-width="1.8"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <path :d="isCollapsed ? 'M7.5 2 L3.5 6 L7.5 10' : 'M4.5 2 L8.5 6 L4.5 10'" />
      </svg>
    </button>

    <ul v-if="isCollapsed" class="cue-rail">
      <li class="cue-rail-tab cue-tab cue-tab--focus">
        Focus <span class="cue-count" data-tabular>{{ focus ? 1 : 0 }}</span>
      </li>
      <li class="cue-rail-tab cue-tab cue-tab--gaps">
        Gaps <span class="cue-count" data-tabular>{{ openGaps.length }}</span>
      </li>
      <li class="cue-rail-tab cue-tab cue-tab--mastered">
        Mastered <span class="cue-count" data-tabular>{{ mastered.length }}</span>
      </li>
    </ul>

    <template v-else>
      <div class="cue-strip" data-testid="cue-strip">
        <p class="cue-strip-line">
          <span v-if="focus" class="cue-strip-focus cue-tab cue-tab--focus">
            <svg
              class="cue-mark cue-mark--focus"
              viewBox="0 0 12 12"
              width="10"
              height="10"
              aria-hidden="true"
              focusable="false"
            >
              <path d="M1 6 L11 6" />
            </svg>
            <span class="cue-strip-focus-word">{{ focus }}</span>
          </span>
          <span v-else class="cue-strip-focus cue-strip-focus--none">no focus cue yet</span>
          <span class="cue-strip-count cue-tab cue-tab--gaps" data-tabular>{{ gapsCount }}</span>
          <span class="cue-strip-count cue-tab cue-tab--mastered" data-tabular
            >{{ mastered.length }} mastered</span
          >
        </p>
        <button
          type="button"
          class="cue-disclosure hit-44"
          data-testid="cue-disclosure"
          :aria-expanded="expanded ? 'true' : 'false'"
          :aria-label="expanded ? 'Hide what the tutor knows' : 'Show what the tutor knows'"
          @click="expanded = !expanded"
        >
          <svg
            class="cue-disclosure-mark"
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
            <path :d="expanded ? 'M5 12 L10 7 L15 12' : 'M5 8 L10 13 L15 8'" />
          </svg>
        </button>
      </div>

      <div class="cue-body">
        <section class="cue-section">
          <h2 class="cue-heading cue-tab cue-tab--focus">
            Focus <span class="cue-count" data-tabular>{{ focus ? 1 : 0 }}</span>
          </h2>
          <div class="cue-card">
            <p
              v-if="focus"
              class="cue-entry cue-entry--focus"
              :class="{ 'is-fresh': isFresh(`focus:${focus}`) }"
              data-testid="cue-focus"
            >
              <svg
                class="cue-mark cue-mark--focus"
                viewBox="0 0 12 12"
                width="12"
                height="12"
                aria-hidden="true"
                focusable="false"
              >
                <path d="M1 6 L11 6" />
              </svg>
              <span class="cue-word">{{ focus }}</span>
            </p>
            <p v-else class="cue-none">no focus cue yet</p>
          </div>
        </section>

        <section class="cue-section">
          <h2 class="cue-heading cue-tab cue-tab--gaps">
            Gaps <span class="cue-count" data-tabular>{{ openGaps.length }}</span>
          </h2>
          <div class="cue-card">
            <ul v-if="openGaps.length" class="cue-list">
              <li
                v-for="g in openGaps"
                :key="g"
                class="cue-entry"
                :class="{ 'is-fresh': isFresh(`gap:${g}`) }"
                data-testid="cue-gap"
              >
                <svg
                  class="cue-mark cue-mark--gap"
                  viewBox="0 0 12 12"
                  width="12"
                  height="12"
                  aria-hidden="true"
                  focusable="false"
                >
                  <circle cx="6" cy="6" r="4" />
                </svg>
                <span class="cue-word" :class="{ 'is-testing': testingGap && testingGap === g }">{{
                  g
                }}</span>
              </li>
            </ul>
            <p v-else class="cue-none">none open</p>
          </div>
        </section>

        <section class="cue-section">
          <h2 class="cue-heading cue-tab cue-tab--mastered">
            Mastered <span class="cue-count" data-tabular>{{ mastered.length }}</span>
          </h2>
          <div class="cue-card">
            <ul v-if="mastered.length" class="cue-list">
              <li
                v-for="m in mastered"
                :key="m"
                class="cue-entry"
                :class="{ 'is-fresh': isFresh(`mastered:${m}`) }"
                data-testid="cue-mastered"
              >
                <svg
                  class="cue-mark cue-mark--tick"
                  viewBox="0 0 12 12"
                  width="12"
                  height="12"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path :d="TICK_PATH" />
                </svg>
                <span class="cue-word">{{ m }}</span>
              </li>
            </ul>
            <p v-else class="cue-none">none yet</p>
          </div>
        </section>

        <section class="cue-section">
          <h2 class="cue-heading cue-tab cue-tab--level">Level</h2>
          <div class="cue-card">
            <!-- The comp shows a "from unset, today" aside here. TopicProfile
                 carries knowledge_level and subtopic_levels as bare strings with
                 no timestamp (last_event_at lives on ConceptEntry only), so the
                 phrase is omitted rather than invented. -->
            <p class="cue-level" :class="{ 'is-unset': !level }" data-testid="cue-level">
              <svg
                class="cue-level-mark"
                viewBox="0 0 24 24"
                width="24"
                height="16"
                aria-hidden="true"
                focusable="false"
              >
                <path :d="LEVEL_MARK_PATH" :stroke-width="levelStroke" />
              </svg>
              <span class="cue-level-label">{{ levelLabel }}</span>
            </p>
            <ul v-if="subtopics.length" class="cue-list cue-list--subtopics">
              <li
                v-for="s in subtopics"
                :key="s.name"
                class="cue-subtopic"
                data-testid="cue-subtopic"
              >
                <svg
                  class="cue-level-mark"
                  viewBox="0 0 24 24"
                  width="18"
                  height="12"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path :d="LEVEL_MARK_PATH" :stroke-width="s.stroke" />
                </svg>
                <span class="cue-subtopic-name">{{ s.name }}</span>
              </li>
            </ul>
          </div>
        </section>
      </div>
    </template>
  </aside>
</template>

<style scoped>
/* The profile panel is the box's tabbed dividers. The shell cell (.sheet-cue)
   is a bare grid cell with no padding, so this root fills it and owns both the
   panel ground and its inset -- the left inset leaves room for the half-tab. */
.cue {
  --cue-row: 1.5rem;
  position: relative;
  box-sizing: border-box;
  flex: 1;
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--desk-deep);
  border-left: 1px solid var(--card-edge);
  padding: 0.9rem 0.9rem 0 1.4rem;
}

/* No overflow clip here: the half-tab sits at left: -1px, outside the padding
   box, and a clip would bite its leftmost pixel off. */
.cue.is-collapsed {
  padding: 0.9rem 0.25rem 0 0.25rem;
}

/* The half-tab: a card-stock tab bitten into the panel's left edge, the mirror
   of the sidebar's own toggle. */
.cue-toggle {
  position: absolute;
  top: 14px;
  left: -1px;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 22px;
  height: 28px;
  padding: 0;
  background: var(--card);
  color: var(--pencil);
  border: 1px solid var(--card-edge);
  border-left: 0;
  border-radius: 0 var(--radius-card) var(--radius-card) 0;
  cursor: pointer;
  transition: color var(--motion-fast) ease;
}

.cue-toggle:hover {
  color: var(--ink);
}

.cue-toggle:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.cue-toggle-mark {
  flex: 0 0 auto;
}

.cue-body {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--card-edge) transparent;
}

.cue-section {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

/* Tab colour is law: red is only ever Focus, amber only Gaps, green only
   Mastered, pencil for Level. The tab is a 5px-top-radius shape, never a rule. */
.cue-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  max-width: 100%;
  padding: 0.15rem 0.6rem;
  border-radius: 5px 5px 0 0;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  font-weight: 700;
  line-height: var(--cue-row);
  color: var(--tab-ink);
}

.cue-tab--focus {
  background: var(--tab-focus);
}

.cue-tab--gaps {
  background: var(--tab-gaps);
}

.cue-tab--mastered {
  background: var(--tab-mastered);
}

.cue-tab--level {
  background: var(--tab-level);
}

.cue-heading {
  margin: 0;
}

.cue-count {
  flex: 0 0 auto;
  font-weight: 400;
  color: var(--tab-ink);
}

/* The divider body: a card the tab is fixed to, so the corner under the tab
   stays square and the other three are carded. */
.cue-card {
  align-self: stretch;
  box-sizing: border-box;
  min-width: 0;
  padding: 0.4rem 0.7rem;
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-radius: 0 var(--radius-card) var(--radius-card) var(--radius-card);
  box-shadow: 0 1px 0 var(--card-drop);
}

.cue-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.cue-entry,
.cue-none,
.cue-level,
.cue-subtopic {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--cue-row);
  overflow-wrap: anywhere;
}

.cue-word {
  color: var(--ink-learner);
}

/* The focus cue and the cue under an open check stay in graphite and are marked
   in red; the word itself is never set in red. */
.cue-entry--focus .cue-word,
.cue-word.is-testing {
  color: var(--ink);
  text-decoration: underline;
  text-decoration-color: var(--ink-marker);
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
}

/* Only the focus cue carries the extra weight; a gap under an open check is
   still a gap, marked but not promoted. */
.cue-entry--focus .cue-word {
  font-weight: 700;
}

.cue-none {
  color: var(--pencil);
}

/* Marks sit on the first line of a row, so a cue that wraps keeps its mark
   beside its first word rather than floating mid-block. */
.cue-mark {
  flex: 0 0 auto;
  align-self: flex-start;
  margin-top: calc((var(--cue-row) - 12px) / 2);
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.5;
}

.cue-mark--focus {
  stroke: var(--ink-marker);
  stroke-width: 2;
}

.cue-mark--gap {
  stroke: var(--pencil);
}

.cue-mark--tick {
  stroke: var(--tab-mastered);
}

.cue-level-mark {
  flex: 0 0 auto;
  align-self: flex-start;
  margin-top: calc((var(--cue-row) - 16px) / 2);
  fill: none;
  stroke: var(--ink);
  stroke-linecap: round;
}

.cue-subtopic .cue-level-mark {
  margin-top: calc((var(--cue-row) - 12px) / 2);
}

.cue-level.is-unset .cue-level-mark {
  stroke: var(--pencil);
}

/* A recorded level is a fact about the page, so it is written in graphite at
   caption weight; "level not set" is still a pencil note. */
.cue-level-label {
  font-size: var(--fs-caption);
  font-weight: 700;
  color: var(--ink);
}

.cue-level.is-unset .cue-level-label,
.cue-subtopic-name {
  font-weight: 400;
  color: var(--pencil);
}

/* Filing: a newly recorded cue lifts off the body (120ms) and settles at its
   new home (240ms). Nothing slides across columns, nothing bounces. */
.cue-entry.is-fresh {
  animation: cue-file 360ms cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes cue-file {
  0% {
    opacity: 0;
    transform: translateY(-4px);
    box-shadow: 0 6px 10px -6px var(--card-drop);
  }
  33% {
    opacity: 1;
    transform: translateY(-4px);
    box-shadow: 0 6px 10px -6px var(--card-drop);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
    box-shadow: 0 0 0 transparent;
  }
}

/* The collapsed form: the three coloured tabs stood on their edge, stacked
   under the half-tab. Level has no count, so it does not ride the rail. */
.cue-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  list-style: none;
  margin: 0;
  padding: 2.3rem 0 0;
  min-height: 0;
  overflow: hidden;
}

/* Rotated so the rounded corners face the thread and the flat edge sits against
   the panel wall, the same way a divider tab stands in a real box. */
.cue-rail-tab {
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  padding: 0.6rem 0.2rem;
  border-radius: 0 5px 5px 0;
  white-space: nowrap;
}

/* The strip is the sub-900px form; hidden while the column has its own width. */
.cue-strip {
  display: none;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: flex-end;
  gap: 0.5rem;
}

.cue-strip-line {
  display: flex;
  align-items: flex-end;
  gap: 0.35rem;
  margin: 0;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
}

.cue-strip-focus {
  min-width: 0;
}

.cue-strip .cue-mark--focus {
  align-self: center;
  margin-top: 0;
  stroke: var(--tab-ink);
}

.cue-strip-focus-word {
  overflow: hidden;
  text-overflow: ellipsis;
}

/* No focus cue is not a Focus divider, so it does not take the red tab. */
.cue-strip-focus--none {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.6rem;
  border-radius: 5px 5px 0 0;
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-bottom: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--cue-row);
  color: var(--pencil);
}

.cue-strip-count {
  flex: 0 0 auto;
}

.cue-disclosure {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  background: transparent;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--ink-learner);
  cursor: pointer;
}

.cue-disclosure-mark {
  flex: 0 0 auto;
}

.cue-disclosure:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

@media (max-width: 899px) {
  /* No column at this width: the panel is a tab row under the head, on the
     desk, with no left edge and no half-tab. */
  .cue {
    border-left: 0;
    padding: 0;
    background: transparent;
  }

  .cue-toggle {
    display: none;
  }

  /* The strip stays put while the page scrolls under it; SessionView makes
     its .sheet-cue grid cell sticky, since this element's own containing
     block is only as tall as the strip. */
  .cue-strip {
    display: grid;
    background: var(--desk);
    padding: 0.35rem clamp(1rem, 3vw, 1.5rem) 0;
  }

  /* R2: the dividers open as a sheet OVER the thread rather than in flow.
     In flow a long profile pushed the notes column down, which collapsed the
     transcript to 0px and put the composer below the viewport; the 40vh cap
     bounds the sheet itself. */
  .cue-body {
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 2;
    padding: 0.5rem clamp(1rem, 3vw, 1.5rem);
    gap: 0.6rem;
    max-height: 40vh;
    overflow-y: auto;
    background: var(--card);
    /* The sheet is a card pulled out over the thread, so it closes: a bottom
       edge and two carded bottom corners. Without them the last divider ran
       into the first turn below and the two read as one broken card. The 40vh
       cap plus this box's own scroll keeps the last divider reachable. */
    border-top: 1px solid var(--card-edge);
    border-bottom: 1px solid var(--card-edge);
    border-radius: 0 0 var(--radius-card) var(--radius-card);
    box-shadow: var(--shadow-lift);
  }

  .cue.is-expanded .cue-body {
    display: flex;
  }

  /* The thread is put away while the sheet is out: a desk-coloured wash from
     the foot of the strip down. It sits under the sheet (z-index 1 against the
     sheet's 2) so the dividers stay at full strength, and takes no pointer
     events so the composer and an open check batch stay usable underneath.
     A viewport's worth of height is deliberate -- SessionView clips the grid
     at this width, so the overhang costs the page nothing. */
  .cue.is-expanded::after {
    content: '';
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    height: 100dvh;
    z-index: 1;
    pointer-events: none;
    background: var(--desk);
    opacity: 0.55;
  }
}

@media (prefers-reduced-motion: reduce) {
  /* Reduced motion shows the final state: the cue is simply at its new home. */
  .cue-entry.is-fresh {
    animation: none;
  }
}
</style>
