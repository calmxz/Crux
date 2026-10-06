<template>
  <div class="usage-tab sec">
    <div v-if="loading" class="skel" data-testid="usage-tab-loading" aria-hidden="true">
      <span class="skel-block" />
      <span class="skel-block" />
      <span class="skel-block skel-short" />
    </div>
    <span v-if="loading" class="sr-only" role="status">Loading</span>
    <div v-else-if="error" class="error-row">
      <p class="error" data-testid="usage-error">Usage data is unavailable right now.</p>
      <button type="button" class="retry" data-testid="usage-retry" @click="load">Retry</button>
    </div>
    <UsagePanel v-else-if="usage" :usage="usage" />
  </div>
</template>

<script setup>
import { onActivated, onMounted, ref } from 'vue'

import UsagePanel from '../profile/UsagePanel.vue'
import { getUsageSummary } from '../../services/profileApi.js'

const usage = ref(null)

const loading = ref(true)

const error = ref(false)

async function load() {
  loading.value = true
  error.value = false

  try {
    usage.value = await getUsageSummary()
  } catch (e) {
    error.value = true
    console.error('usage fetch failed', e)
  } finally {
    loading.value = false
  }
}

onMounted(load)

// E-10: SettingsView keeps the tab alive, so a failed read would otherwise
// stay failed for the rest of the visit. Coming back to the tab retries.
// The guard matters: onActivated also fires on the first mount, right after
// onMounted, and without it every visit would fetch twice.
onActivated(() => {
  if (error.value) load()
})
</script>

<style scoped>
/* The card shell and .skel-block come from assets/sheet.css; the tab
   carries the .sec class and declares only what is its own. */

/* A failed read is a line of text-safe red on the pitch, not a banner, with
   the retry written beside it (same grammar as SessionView's .error-retry). */
.error-row {
  display: flex;
  align-items: baseline;
  gap: 0.625rem;
}

.retry {
  flex: 0 0 auto;
  background: transparent;
  border: 0;
  padding: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--line-pitch);
  color: var(--ink-learner);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.retry:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.error {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--line-pitch);
  color: var(--ink-marker-text);
}

/* Skeleton: pencil-weight rules on the pitch, no shimmer and no fill. */
.skel {
  display: flex;
  flex-direction: column;
}

.skel-short {
  width: 55%;
}
</style>
