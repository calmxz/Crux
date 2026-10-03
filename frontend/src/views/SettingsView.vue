<template>
  <section class="settings" data-testid="settings">
    <header class="head">
      <h1 class="title">Settings</h1>
    </header>

    <div class="layout">
      <!-- D-16: only the active panel is mounted, so aria-controls is bound on
           the selected tab alone; on the others it would dangle. -->
      <nav
        class="rail"
        role="tablist"
        aria-label="Settings sections"
        data-testid="settings-tab-rail"
      >
        <button
          v-for="(t, i) in tabs"
          :key="t.slug"
          :ref="(el) => (tabRefs[i] = el)"
          role="tab"
          :id="`tab-${t.slug}`"
          :aria-controls="t.slug === tab ? `panel-${t.slug}` : undefined"
          :aria-selected="t.slug === tab ? 'true' : 'false'"
          :tabindex="t.slug === tab ? 0 : -1"
          :class="['rail-tab', 'coarse-2x', { 'rail-tab--active': t.slug === tab }]"
          :data-testid="`settings-tab-${t.slug}`"
          type="button"
          @click="activate(i)"
          @keydown="onKeydown($event, i)"
        >
          <span>{{ t.label }}</span>
        </button>
      </nav>

      <div
        class="panel"
        role="tabpanel"
        :id="`panel-${tab}`"
        :aria-labelledby="`tab-${tab}`"
        tabindex="0"
      >
        <KeepAlive>
          <component :is="activeComponent" />
        </KeepAlive>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import '@/assets/sheet.css'
import LearningTab from '../components/settings/LearningTab.vue'
import UsageTab from '../components/settings/UsageTab.vue'
import AppearanceTab from '../components/settings/AppearanceTab.vue'

const props = defineProps({
  tab: { type: String, default: 'learning' },
})

const router = useRouter()

// The rail is the contents list of this section: one row per page, no icons.
// Account moved to its own route (/account); it is no longer a Settings tab.
const tabs = [
  { slug: 'learning', label: 'Learning', component: LearningTab },
  { slug: 'usage', label: 'Usage', component: UsageTab },
  { slug: 'appearance', label: 'Appearance', component: AppearanceTab },
]

const activeComponent = computed(
  () => (tabs.find((t) => t.slug === props.tab) || tabs[0]).component,
)

const tabRefs = ref([])

// The deep-desk ground must fill the whole routed pane, not just the
// settings element, so it is painted on .page via a body class (same
// mechanism SessionView uses for session-page).
onMounted(() => document.body.classList.add('settings-page'))

onUnmounted(() => document.body.classList.remove('settings-page'))

async function activate(i) {
  const slug = tabs[i].slug

  if (slug !== props.tab) {
    await router.push({ name: 'settings', params: { tab: slug } })
  }

  await nextTick()
  tabRefs.value[i]?.focus()
}

function onKeydown(e, i) {
  let nextIndex = null

  if (e.key === 'ArrowDown' || e.key === 'ArrowRight') nextIndex = (i + 1) % tabs.length

  if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') nextIndex = (i - 1 + tabs.length) % tabs.length

  if (nextIndex === null) return
  e.preventDefault()
  activate(nextIndex)
}
</script>

<style scoped>
/* The deep-desk page ground (body.settings-page .page) and the .panel sheet
   shell, plus the shared .sec/.sec-title/.saved-flash/.tick/.skel-block
   furniture, live in assets/sheet.css (imported above) so AccountView can
   share them without re-declaring or reaching through :deep(). */

.settings {
  display: flex;
  flex-direction: column;
}

.head {
  display: flex;
  flex-direction: column;
  padding-bottom: var(--line-pitch);
}

.title {
  font-family: var(--font-display);
  font-size: var(--fs-h1);
  font-weight: 600;
  letter-spacing: var(--tracking-display);
  line-height: var(--lh-display);
  color: var(--ink);
  margin: 0;
}

/* The page uses the full width: title on a strong rule, one pitch, then the
   contents list laid down as one ruled tab line (the sidebar's own Active /
   Ended grammar), then the panel full width beneath it. */
.layout {
  display: flex;
  flex-direction: column;
}

/* Divider tabs: each is its own tab shape on the deep desk; the one in
   force lifts to the sheet's own white and sits flush against it (negative
   margin overlaps the panel's top border) so rail and sheet read as one
   joined object. */
.rail {
  display: flex;
  flex-direction: row;
  align-items: flex-end;
  gap: 0.375rem;
  overflow-x: auto;
  position: static;
  padding: 0;
  margin-top: var(--line-pitch);
}

.rail-tab {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  padding: 0.5rem 1rem;
  border: 1px solid var(--card-edge);
  border-bottom: 0;
  border-radius: var(--radius-card) var(--radius-card) 0 0;
  background: var(--desk);
  color: var(--pencil);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: calc(var(--line-pitch) - 1px);
  text-align: left;
  cursor: pointer;
}

.rail-tab:hover {
  background: var(--card);
  color: var(--ink);
}

.rail-tab--active {
  position: relative;
  z-index: 1;
  margin-bottom: -1px;
  background: var(--card);
  color: var(--ink);
}

.rail-tab:focus-visible {
  outline: 2px solid var(--ink-learner);
  outline-offset: 2px;
}

/* The sheet joins to the active tab, square only at the top-left where the
   rail starts. Its box rules and the .sec/.sec-title/.saved-flash/.tick/
   .skel-block furniture shared with every tab live in assets/sheet.css;
   only the joined corner is Settings' own. */
.panel {
  border-radius: 0 var(--radius-card) var(--radius-card) var(--radius-card);
}
</style>
