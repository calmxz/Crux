<template>
  <section class="aprof profile-page" data-testid="aggregate-profile">
    <header class="head" data-section="head">
      <h1 class="title">Your profile</h1>
      <p class="lede" data-testid="aprof-lede">
        What the tutor knows about you, topic by topic.<template v-if="lastStudied">
          Last studied {{ lastStudied }}.</template
        >
      </p>
    </header>

    <div v-if="loading" class="skel" data-testid="aprof-loading" aria-hidden="true">
      <span class="skel-block" />
      <span class="skel-block" />
      <span class="skel-block skel-short" />
    </div>
    <span v-if="loading" class="sr-only" role="status">Loading</span>
    <div v-else-if="error" class="error">
      <p class="error-text" data-testid="aprof-error">{{ error }}</p>
      <button type="button" class="text-btn" data-testid="aprof-retry" @click="load">Retry</button>
    </div>

    <EmptyState
      v-else-if="isEmpty"
      data-testid="aprof-empty"
      tone="celebrate"
      headline="No sessions yet"
      subtext="Start one. Your profile builds itself as you go."
    >
      <template #cta>
        <router-link :to="{ name: 'home' }" class="text-btn">Start your first session</router-link>
      </template>
    </EmptyState>

    <template v-else-if="data">
      <div class="topics" data-section="topics">
        <h2 class="sr-only">Topics</h2>
        <ol class="topic-grid">
          <li v-for="t in topics" :key="t.id" class="topic-card" data-testid="aprof-topic-card">
            <p class="topic-head">
              <b data-testid="aprof-topic-state">{{ t.ended_at ? 'ended' : 'active' }}</b>
              <span>{{ formatRelative(t.last_activity_at || t.created_at) }}</span>
            </p>
            <router-link :to="profileOf(t.id)" class="topic-name">{{
              t.topic || 'Untitled'
            }}</router-link>
            <div class="topic-cues">
              <span class="cue">
                <svg
                  class="level-mark"
                  :class="{ 'is-unset': !t.progress?.level }"
                  viewBox="0 0 24 24"
                  width="18"
                  height="12"
                  aria-hidden="true"
                  focusable="false"
                >
                  <path :d="LEVEL_MARK_PATH" :stroke-width="levelStroke(t.progress?.level)" />
                </svg>
                <span
                  class="level-word"
                  :class="{ 'is-unset': !t.progress?.level }"
                  data-testid="aprof-topic-level"
                  >{{ t.progress?.level || 'level not set' }}</span
                >
              </span>
              <span class="cue">
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
                <span
                  v-if="t.progress?.focus_target_gap"
                  class="focus-word"
                  data-testid="aprof-topic-focus"
                  ><span class="sr-only">focus: </span>{{ t.progress.focus_target_gap }}</span
                >
                <span v-else class="cue-none-inline" data-testid="aprof-topic-focus"
                  >no focus cue yet</span
                >
              </span>
              <span class="cue">
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
                <span class="meta" data-testid="aprof-topic-mastered"
                  >{{ t.progress?.mastered_count || 0 }} mastered</span
                >
              </span>
            </div>
            <p
              v-if="topicStory(t)"
              class="topic-story"
              :class="{ 'is-preview': topicStory(t).preview }"
              data-testid="aprof-topic-story"
            >
              {{ topicStory(t).text }}
            </p>
            <div class="topic-actions">
              <router-link :to="sessionOf(t.id)" class="text-btn">{{
                t.ended_at ? 'Resume' : 'Continue'
              }}</router-link>
              <router-link :to="profileOf(t.id)" class="text-btn">Open profile</router-link>
            </div>
          </li>
        </ol>
        <p class="topics-foot" data-testid="aprof-topics-foot">
          Showing {{ topics.length }} of {{ data.total_sessions }} topics.
          <router-link :to="{ name: 'sessions-library' }" class="text-btn"
            >See all topics</router-link
          >
        </p>
      </div>

      <section class="divider" data-section="level" data-testid="aprof-level">
        <h2 class="divider-tab divider-tab--level">
          Level <span class="tab-count">{{ data.total_sessions }}</span>
        </h2>
        <div class="divider-body">
          <ul class="cue-list">
            <li v-for="row in levelRows" :key="row.key" class="cue" data-testid="aprof-level-row">
              <svg
                class="level-mark"
                :class="{ 'is-unset': !row.level }"
                viewBox="0 0 24 24"
                width="18"
                height="12"
                aria-hidden="true"
                focusable="false"
              >
                <path :d="LEVEL_MARK_PATH" :stroke-width="levelStroke(row.level)" />
              </svg>
              <span class="level-word" :class="{ 'is-unset': !row.level }">{{ row.label }}</span>
              <span class="meta">{{ row.count }} {{ row.count === 1 ? 'topic' : 'topics' }}</span>
            </li>
          </ul>
        </div>
      </section>

      <section
        v-for="sec in CUE_SECTIONS"
        :key="sec.key"
        class="divider"
        :data-section="sec.key"
        :data-testid="sec.testid"
      >
        <h2 class="divider-tab" :class="sec.tabClass">
          {{ sec.label }} <span class="tab-count">{{ data[sec.field].length }}</span>
        </h2>
        <div class="divider-body">
          <p v-if="!data[sec.field].length" class="cue-none">{{ sec.empty }}</p>
          <ul v-else class="cue-list cue-grid">
            <li
              v-for="c in data[sec.field]"
              :key="c.concept"
              class="cue"
              data-testid="aprof-cue-row"
            >
              <svg
                class="cue-mark"
                :class="sec.markClass"
                viewBox="0 0 12 12"
                width="12"
                height="12"
                aria-hidden="true"
                focusable="false"
              >
                <path v-if="sec.tick" :d="TICK_PATH" />
                <circle v-else cx="6" cy="6" r="4" />
              </svg>
              <router-link :to="profileOf(c.first_seen_session_id)" class="cue-word">{{
                c.concept
              }}</router-link>
              <span v-if="c.count > 1" class="meta">in {{ c.count }} sessions</span>
            </li>
          </ul>
        </div>
      </section>

      <div class="figures" data-section="figures">
        <section class="sec" data-testid="aprof-weekly">
          <h2 class="sec-title">Mastered by week</h2>
          <template v-if="weeklyHasData">
            <div class="weekly-figure">
              <svg
                class="weekly-svg"
                :viewBox="`0 0 ${weeklyChartWidth} ${WEEKLY_CHART_HEIGHT + 1}`"
                preserveAspectRatio="xMidYMid meet"
                aria-hidden="true"
              >
                <line
                  class="weekly-baseline"
                  :x1="0"
                  :x2="weeklyChartWidth"
                  :y1="WEEKLY_CHART_HEIGHT"
                  :y2="WEEKLY_CHART_HEIGHT"
                />
                <rect
                  v-for="col in weeklyColumns"
                  :key="col.key"
                  class="weekly-bar"
                  :x="col.x"
                  :y="col.barY"
                  :width="WEEKLY_BAR_WIDTH"
                  :height="col.barHeight"
                  rx="4"
                  ry="4"
                >
                  <title>{{ col.title }}</title>
                </rect>
              </svg>
              <div class="weekly-labels" aria-hidden="true">
                <span v-for="col in weeklyColumns" :key="col.key" class="weekly-label">{{
                  col.showLabel ? col.label : ''
                }}</span>
              </div>
            </div>
            <ul class="sr-only" data-testid="aprof-weekly-text">
              <li v-for="col in weeklyColumns" :key="col.key">{{ col.title }}</li>
            </ul>
          </template>
          <p v-else class="cue-none">none yet</p>
        </section>

        <section class="sec" data-testid="aprof-accuracy">
          <h2 class="sec-title">Check accuracy</h2>
          <template v-if="conceptAccuracy.length">
            <div v-for="group in accuracyGroupList" :key="group.key" class="accuracy-group">
              <p v-if="group.label" class="accuracy-group-label">{{ group.label }}</p>
              <ul class="accuracy-list">
                <li
                  v-for="c in group.rows"
                  :key="c.concept"
                  class="accuracy-row"
                  data-testid="aprof-accuracy-row"
                >
                  <router-link :to="profileOf(c.first_seen_session_id)" class="accuracy-concept">{{
                    c.concept
                  }}</router-link>
                  <span class="meta" data-tabular
                    >{{ c.correct_count }} of {{ c.total_count }}</span
                  >
                  <span class="accuracy-marks">
                    <span class="sr-only">last results, oldest first: </span>
                    <svg
                      v-for="(result, idx) in c.last_results"
                      :key="idx"
                      class="accuracy-mark"
                      viewBox="0 0 12 12"
                      width="12"
                      height="12"
                      focusable="false"
                      role="img"
                      :aria-label="result ? 'correct' : 'incorrect'"
                    >
                      <path v-if="result" :d="TICK_PATH" />
                      <template v-else>
                        <path d="M2.5 2.5 L9.5 9.5" />
                        <path d="M9.5 2.5 L2.5 9.5" />
                      </template>
                    </svg>
                  </span>
                </li>
              </ul>
            </div>
          </template>
          <p v-else class="cue-none">none yet</p>
        </section>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

import EmptyState from '../components/EmptyState.vue'
import { LEVEL_MARK_PATH, TICK_PATH, levelStroke } from '../components/chat/levelMark.js'
import { friendlyError } from '../lib/errors.js'
import { getAggregateProfile } from '../services/profileApi.js'
import { formatRelative } from '../utils/formatDate.js'
import { cleanPreview, stripAutoPrefix } from '../utils/sessionCard.js'
import '@/assets/profile.css'

const LEVELS = ['beginner', 'intermediate', 'advanced']

// Gaps and Mastered are the same divider over a different list; the tab
// colour and mark are the only difference (tab law: amber only Gaps, green
// only Mastered).
const CUE_SECTIONS = [
  {
    key: 'gaps',
    field: 'combined_confirmed_gaps',
    label: 'Gaps',
    tabClass: 'divider-tab--gaps',
    testid: 'aprof-gaps',
    markClass: 'cue-mark--gap',
    tick: false,
    empty: 'none open',
  },
  {
    key: 'mastered',
    field: 'combined_mastered_concepts',
    label: 'Mastered',
    tabClass: 'divider-tab--mastered',
    testid: 'aprof-mastered',
    markClass: 'cue-mark--tick',
    tick: true,
    empty: 'none yet',
  },
]

const data = ref(null)

const loading = ref(false)

const error = ref('')

async function load() {
  loading.value = true
  error.value = ''

  try {
    data.value = await getAggregateProfile()
  } catch (e) {
    error.value = friendlyError(e)
  }

  loading.value = false
}

onMounted(load)

// total_sessions rather than recent_topics.length: a learner with sessions
// but nothing in the recent window is not a fresh account.
const isEmpty = computed(() => data.value !== null && (data.value.total_sessions ?? 0) === 0)

const lastStudied = computed(() =>
  data.value?.last_active_at ? formatRelative(data.value.last_active_at) : '',
)

// recent_topics is capped at 5 and sorted server-side; the foot line and
// "See all topics" cover the rest.
const topics = computed(() => data.value?.recent_topics ?? [])

const weeklyMastery = computed(() => data.value?.weekly_mastery ?? [])

const conceptAccuracy = computed(() => data.value?.concept_accuracy ?? [])

const profileOf = (id) => ({ name: 'session-profile', params: { id } })

const sessionOf = (id) => ({ name: 'session', params: { id } })

// The card's one line of story: the session summary (auto prefix stripped)
// or, failing that, the last message preview in italic, cleaned of markdown
// and math the same way the library cards clean it.
function topicStory(t) {
  const summary = stripAutoPrefix(t.last_session_summary)

  if (summary) return { text: summary, preview: false }
  const preview = cleanPreview(t.last_message_preview)

  return preview ? { text: preview, preview: true } : null
}

const levelRows = computed(() => {
  const dist = data.value?.knowledge_level_distribution ?? {}
  const rows = LEVELS.map((l) => ({ key: l, level: l, label: l, count: dist[l] ?? 0 }))

  if (dist.unknown) {
    rows.push({ key: 'unknown', level: null, label: 'level not set', count: dist.unknown })
  }

  return rows
})

function formatWeekLabel(iso) {
  const d = new Date(`${iso}T00:00:00Z`)

  if (Number.isNaN(d.getTime())) return iso

  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
}

// Small bounded column chart: thin bars, rounded data-ends on the baseline,
// a fixed bar/gap pitch so it never scales with the card (see
// .weekly-figure max-width). One series in the green mastered token only.
const WEEKLY_BAR_WIDTH = 16

const WEEKLY_GAP = 8

const WEEKLY_CHART_HEIGHT = 56

// weekly_mastery is always 12 zero-filled points server-side, so "has data"
// is some week carrying a count, never the array's length.
const weeklyHasData = computed(() => weeklyMastery.value.some((w) => w.count > 0))

const weeklyMax = computed(() => Math.max(...weeklyMastery.value.map((w) => w.count), 1))

const weeklyChartWidth = computed(() => {
  const n = weeklyMastery.value.length

  return n ? n * WEEKLY_BAR_WIDTH + (n - 1) * WEEKLY_GAP : WEEKLY_BAR_WIDTH
})

// 12 captions drift off the 20rem figure, so only the first, last and every
// 4th week (clear of the last) get one; the per-bar <title> and the sr-only
// list still carry every date.
const weeklyColumns = computed(() => {
  const points = weeklyMastery.value
  const n = points.length

  return points.map((w, i) => {
    const barHeight = (w.count / weeklyMax.value) * WEEKLY_CHART_HEIGHT

    return {
      key: w.week_start,
      x: i * (WEEKLY_BAR_WIDTH + WEEKLY_GAP),
      barY: WEEKLY_CHART_HEIGHT - barHeight,
      barHeight,
      label: formatWeekLabel(w.week_start),
      showLabel: i === 0 || i === n - 1 || (i % 4 === 0 && n - 1 - i >= 2),
      title: `Week of ${formatWeekLabel(w.week_start)}: ${w.count} mastered`,
    }
  })
})

// The server sorts concept_accuracy ascending by accuracy, so the least
// accurate are the first 3 and the most accurate the last 3. With fewer than
// 6 the slices overlap; the most-accurate group drops anything already shown,
// and the labels only appear when both groups do.
const ACCURACY_GROUP_SIZE = 3

const accuracyGroupList = computed(() => {
  const all = conceptAccuracy.value
  const least = all.slice(0, ACCURACY_GROUP_SIZE)
  const leastNames = new Set(least.map((c) => c.concept))
  const most = all.slice(-ACCURACY_GROUP_SIZE).filter((c) => !leastNames.has(c.concept))
  const showLabels = least.length > 0 && most.length > 0
  const groups = []

  if (least.length)
    groups.push({ key: 'least', label: showLabels ? 'Least accurate' : null, rows: least })

  if (most.length)
    groups.push({ key: 'most', label: showLabels ? 'Most accurate' : null, rows: most })

  return groups
})
</script>

<style scoped>
/* The aggregate profile: a 72rem stack of full-width cards 1.5rem apart, the
   same grammar as the per-session profile page. Topic cards first (the
   learner comes back over weeks), then the Level, Gaps and Mastered dividers
   across every session, then the two figures. The dividers, cue marks,
   .sec/.sec-title, .cue-none, .text-btn and the skeleton rule come from
   assets/profile.css (shared with ProfileView); only what differs is here. */
.aprof {
  max-width: 72rem;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.head {
  display: flex;
  flex-direction: column;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--rule-strong);
}

.title {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--fs-h1);
  font-weight: 600;
  letter-spacing: var(--tracking-display);
  line-height: var(--lh-display);
  color: var(--ink);
}

.lede {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--pencil);
}

/* Topic cards: two columns from 60rem, one below. */
.topics {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.topic-grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0.75rem;
}

.topic-card {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 0;
  padding: 0.55rem 0.9rem 0.7rem;
  background: var(--card);
  border: 1px solid var(--card-edge);
  border-radius: var(--radius-card);
  box-shadow: 0 1px 0 var(--card-drop);
}

/* The pencil head line every card carries: state left, time right. */
.topic-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--lh-body);
  color: var(--pencil);
}

.topic-head b {
  font-weight: 700;
}

/* The session-topic face: the topic reads as a title, underlined in the
   marker's red on hover like the session action bar's topic link. */
.topic-name {
  align-self: flex-start;
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 600;
  letter-spacing: var(--tracking-display);
  line-height: var(--lh-display);
  color: var(--ink);
  text-decoration: none;
  overflow-wrap: anywhere;
}

.topic-name:hover {
  text-decoration: underline;
  text-decoration-color: var(--ink-marker);
  text-decoration-thickness: 2px;
  text-underline-offset: 4px;
}

.topic-name:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.topic-cues {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1.25rem;
}

.topic-cues .cue {
  gap: 0.4rem;
  min-height: 0;
}

.topic-story {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--pencil);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.topic-story.is-preview {
  font-style: italic;
}

.topic-actions {
  display: flex;
  gap: 1rem;
  margin-top: 0.25rem;
}

.topics-foot {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--pencil);
}

/* Cue rows: a drawn mark, then the word, then a pencil note. */
.cue {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  min-height: 1.5rem;
}

.cue-list {
  width: 100%;
}

/* Gaps and Mastered lists: one column, two from 60rem. */
.cue-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  column-gap: 2rem;
}

.cue-word {
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink-learner);
  text-decoration: none;
  overflow-wrap: anywhere;
}

.cue-word:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.cue-word:focus-visible,
.accuracy-concept:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.cue-mark {
  align-self: center;
}

.level-mark {
  flex: 0 0 auto;
  align-self: center;
  fill: none;
  stroke: var(--ink);
  stroke-linecap: round;
}

.level-mark.is-unset {
  stroke: var(--pencil);
}

.level-word {
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--lh-body);
  color: var(--ink);
}

.level-word.is-unset {
  font-weight: 400;
  color: var(--pencil);
}

/* The focus cue stays in ink and is marked in red; the word is never set in
   red (tab law: red only Focus). */
.focus-word {
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--lh-body);
  color: var(--ink);
  text-decoration: underline;
  text-decoration-color: var(--ink-marker);
  text-decoration-thickness: 2px;
  text-underline-offset: 4px;
}

.cue-none-inline {
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--pencil);
}

.meta {
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--lh-body);
  color: var(--pencil);
  white-space: nowrap;
}

.topic-cues .meta {
  font-size: var(--fs-caption);
}

/* The dividers' tab count: the tab and body themselves come from
   assets/profile.css. */
.tab-count {
  font-weight: 400;
  margin-left: 0.2rem;
}

/* Figures: two cards side by side from 60rem. */
.figures {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1.5rem;
}

.sec {
  align-items: stretch;
  min-width: 0;
}

/* Capped measure: the chart must not scale with the card. */
.weekly-figure {
  max-width: 20rem;
  margin-top: 0.25rem;
}

.weekly-svg {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
}

.weekly-baseline {
  stroke: var(--rule);
  stroke-width: 1;
}

.weekly-bar {
  fill: var(--tab-mastered);
}

.weekly-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
}

.weekly-label {
  flex: 1 1 0;
  min-width: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--line-pitch);
  color: var(--pencil);
  text-align: center;
  white-space: nowrap;
}

.accuracy-group + .accuracy-group {
  margin-top: 0.75rem;
}

.accuracy-group-label {
  margin: 0 0 0.25rem;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--lh-body);
  color: var(--pencil);
}

.accuracy-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.accuracy-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.4rem 0.9rem;
  padding: 0.4rem 0;
  box-shadow: inset 0 -1px 0 var(--rule);
}

.accuracy-concept {
  flex: 1 1 auto;
  min-width: 6rem;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  color: var(--ink-learner);
  text-decoration: none;
  overflow-wrap: anywhere;
}

.accuracy-concept:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.accuracy-marks {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  flex: 0 0 auto;
}

/* Grading is the marker's hand, same as the check card: a drawn mark, never a
   fill. Correctness is exempt from the tab law (DESIGN.md), so red here is
   not a tab colour. */
.accuracy-mark {
  flex: 0 0 auto;
  fill: none;
  stroke: var(--ink-marker);
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.error {
  display: flex;
  align-items: baseline;
  gap: 0.625rem;
}

.error-text {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink-marker-text);
}

@media (min-width: 60rem) {
  .topic-grid,
  .figures {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }

  .cue-grid {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}
</style>
