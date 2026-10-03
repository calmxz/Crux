<template>
  <div class="usage" data-testid="usage-panel">
    <h2 class="heading">Usage</h2>

    <p v-if="noSpend" class="muted" data-testid="usage-empty">
      No usage yet — spend history appears once you start chatting.
    </p>

    <template v-else>
      <div class="glance" data-testid="usage-glance" data-tabular>
        <div class="glance-today">
          <span class="glance-figure">${{ usage.today_spend_usd.toFixed(2) }}</span>
          <span class="glance-caption">today · ${{ usage.hard_cap_usd.toFixed(2) }} daily cap</span>
        </div>
      </div>

      <div class="meter-wrap">
        <div class="meter-row">
          <div class="meter-col">
            <div class="meter" role="img" data-testid="usage-meter" :aria-label="meterPctLabel">
              <span
                class="meter-fill"
                :class="{ 'meter-fill--over-urgent': overUrgent }"
                :style="{ width: fillPct }"
              />
              <span
                class="meter-tick"
                data-testid="usage-tick-soft"
                :style="{ left: pctOfHard(usage.soft_cap_usd) }"
                :title="`soft cap $${usage.soft_cap_usd.toFixed(2)}`"
              />
              <span
                class="meter-tick"
                data-testid="usage-tick-urgent"
                :style="{ left: pctOfHard(usage.urgent_cap_usd) }"
                :title="`urgent cap $${usage.urgent_cap_usd.toFixed(2)}`"
              />
              <span
                class="meter-tick meter-tick-hard"
                data-testid="usage-tick-hard"
                style="left: 100%"
                :title="`hard cap $${usage.hard_cap_usd.toFixed(2)}`"
              />
            </div>
            <div class="meter-labels" data-tabular>
              <span
                class="meter-label meter-label-soft"
                :style="{ left: pctOfHard(usage.soft_cap_usd) }"
                >soft ${{ usage.soft_cap_usd.toFixed(2) }}</span
              >
              <span
                class="meter-label meter-label-urgent"
                :style="{ left: pctOfHard(usage.urgent_cap_usd) }"
                >urgent ${{ usage.urgent_cap_usd.toFixed(2) }}</span
              >
            </div>
          </div>
          <span class="meter-figure" data-tabular
            >${{ usage.today_spend_usd.toFixed(2) }} of ${{
              usage.hard_cap_usd.toFixed(2)
            }}
            today</span
          >
        </div>
      </div>

      <p class="muted" data-testid="usage-reset">
        Resets at {{ resetTime }}. At the limit, chat pauses until then.
      </p>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import { formatTime } from '../../utils/formatDate.js'

const props = defineProps({
  usage: { type: Object, required: true },
})

const maxDay = computed(() => Math.max(...props.usage.daily.map((d) => d.cost_usd), 0))

// top_sessions is all-time while daily covers a short window, so a learner
// whose last spend fell outside the window still counts as having history.
const hasPastSessions = computed(() => (props.usage.top_sessions || []).length > 0)

const noSpend = computed(
  () => maxDay.value === 0 && props.usage.today_spend_usd === 0 && !hasPastSessions.value,
)

// resets_at is the next UTC midnight; the learner reads it in their own zone.
// Time only, unlike formatResetTime: the reset is always within a day.
const resetTime = computed(() => formatTime(props.usage.resets_at))

const pctOfHard = (v) => `${Math.min(100, Math.round((v / props.usage.hard_cap_usd) * 100))}%`

const fillPct = computed(() => pctOfHard(props.usage.today_spend_usd))

const overUrgent = computed(() => props.usage.today_spend_usd >= props.usage.urgent_cap_usd)

// The meter's one accessible name. It carries the percentage so it adds to,
// rather than repeats, the visible "$x.xx of $y.yy today" figure.
const meterPctLabel = computed(() => {
  const pct = Math.min(
    100,
    Math.round((props.usage.today_spend_usd / props.usage.hard_cap_usd) * 100),
  )

  return `${pct}% of daily cap spent`
})
</script>

<style scoped>
/* Today against the cap: the glance figure and one ruled meter. */
.usage {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.heading {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--line-pitch);
  color: var(--ink);
}

.muted {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--line-pitch);
  color: var(--pencil);
}

.glance {
  display: flex;
  flex-direction: column;
}

.glance-today {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.glance-figure {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--fs-h2);
  font-weight: 600;
  line-height: var(--line-pitch);
  color: var(--ink);
}

.glance-caption {
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--line-pitch);
  color: var(--pencil);
}

.meter-wrap {
  display: flex;
  flex-direction: column;
  padding: 12px 0;
}

.meter-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  flex-wrap: wrap;
}

/* The meter and its tier labels share one column so a label's left: pct%
   lands on its tick; the figure sits beside the column, not under it. The
   top padding centres the 4px meter on the figure's line. */
.meter-col {
  flex: 1 1 auto;
  min-width: 6rem;
  padding-top: calc((var(--line-pitch) - 4px) / 2);
}

.meter {
  position: relative;
  height: 4px;
  background: var(--rule);
}

.meter-fill {
  display: block;
  height: 100%;
  background: var(--color-accent);
}

.meter-fill--over-urgent {
  background: var(--ink-marker-text);
}

.meter-tick {
  position: absolute;
  top: -4px;
  bottom: -4px;
  width: 1px;
  background: var(--pencil);
}

.meter-figure {
  flex: 0 0 auto;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--line-pitch);
  color: var(--ink);
  white-space: nowrap;
}

.meter-labels {
  position: relative;
  height: var(--line-pitch);
}

.meter-label {
  position: absolute;
  top: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--line-pitch);
  color: var(--pencil);
  white-space: nowrap;
}

/* Each tier label hangs off its own tick: soft to the right of its marker,
   urgent to the left, so neither can run past the meter's edge. The daily
   cap is already written in the glance caption. */
.meter-label-soft {
  transform: translateX(0.25rem);
}

.meter-label-urgent {
  transform: translateX(calc(-100% - 0.25rem));
}

@media (max-width: 600px) {
  .meter-labels {
    height: auto;
    min-height: var(--line-pitch);
  }

  .meter-label {
    position: static;
    display: inline-block;
    transform: none;
    margin-right: 0.75rem;
  }
}
</style>
