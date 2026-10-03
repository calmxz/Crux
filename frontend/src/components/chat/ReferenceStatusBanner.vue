<template>
  <div
    v-if="status || failed"
    class="ref-status"
    :class="[status ? `is-${status}` : null, { 'is-unavailable': failed }]"
    data-testid="reference-status"
  >
    <button
      v-if="status"
      type="button"
      class="ref-header"
      data-testid="ref-toggle"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <svg
        v-if="status === 'pending'"
        class="ref-icon ref-spinner spin"
        viewBox="0 0 20 20"
        width="16"
        height="16"
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
      <svg
        v-else-if="status === 'failed'"
        class="ref-icon"
        viewBox="0 0 20 20"
        width="16"
        height="16"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <path d="M10 2.5 L18 17 H2 Z" />
        <path d="M10 8 L10 12" />
        <path d="M10 14.5 L10 14.6" />
      </svg>
      <svg
        v-else-if="status === 'ready'"
        class="ref-icon"
        viewBox="0 0 20 20"
        width="16"
        height="16"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <circle cx="10" cy="10" r="7.5" />
        <path d="M6.8 10.2 L9 12.5 L13.2 7.5" />
      </svg>
      <span class="ref-text" role="status" aria-live="polite">{{ message }}</span>
      <svg
        class="ref-icon ref-chevron"
        viewBox="0 0 20 20"
        width="16"
        height="16"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <path v-if="expanded" d="M5 12.5 L10 7.5 L15 12.5" />
        <path v-else d="M5 7.5 L10 12.5 L15 7.5" />
      </svg>
    </button>

    <!-- F-12: a poll threw. The last-known list above (if any) stays rendered so
         per-file delete stays reachable; this row owns the outage and its retry. -->
    <div v-if="failed" class="ref-unavailable" data-testid="ref-unavailable">
      <span class="ref-text" role="status" aria-live="polite">References unavailable.</span>
      <button type="button" class="ref-retry" data-testid="ref-retry" @click="emit('refresh')">
        Retry
      </button>
    </div>

    <ul v-if="expanded" class="ref-file-list" data-testid="ref-file-list">
      <li v-for="doc in documents" :key="doc.id" class="ref-file-row">
        <span class="ref-file-name">{{ doc.filename }}</span>
        <span class="ref-file-status" :class="`is-${doc.status}`">{{ doc.status }}</span>
        <span v-if="doc.status === 'failed' && doc.error" class="ref-file-error">{{
          doc.error
        }}</span>
        <button
          type="button"
          class="ref-file-delete"
          :data-testid="`ref-delete-${doc.id}`"
          :aria-label="`Delete ${doc.filename}`"
          @click="confirmDelete(doc)"
        >
          <svg
            class="ref-icon"
            viewBox="0 0 20 20"
            width="16"
            height="16"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
            focusable="false"
          >
            <path
              d="M4 5.5 H16 M8 5.5 V4 a1 1 0 0 1 1 -1 h2 a1 1 0 0 1 1 1 v1.5 M6 5.5 L6.7 16 a1 1 0 0 0 1 0.9 h4.6 a1 1 0 0 0 1 -0.9 L14 5.5"
            />
          </svg>
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useConfirm } from 'primevue/useconfirm'

import { deleteDocument } from '../../services/uploadApi.js'
import { useToast } from '../../composables/useToast.js'

// F-12 / E-07: this component used to own a fixed-2s poller of its own, running
// alongside SessionView's fixed-1s upload poller against the same fact. Both
// now read one useReferencePoll instance owned by SessionView, so the banner is
// presentational plus the delete flow. `refresh` asks the owner to re-poll.
const props = defineProps({
  // 'pending' | 'ready' | 'failed' | null
  status: { type: String, default: null },
  documents: { type: Array, default: () => [] },
  failed: { type: Boolean, default: false },
})

const emit = defineEmits(['refresh'])

const expanded = ref(false)

const readyCount = computed(() => props.documents.filter((d) => d.status === 'ready').length)

const failedCount = computed(() => props.documents.filter((d) => d.status === 'failed').length)

const total = computed(() => props.documents.length)

const message = computed(() => {
  if (props.status === 'pending') {
    return `Indexing ${total.value} reference${total.value === 1 ? '' : 's'}... you can start chatting now.`
  }

  if (props.status === 'failed') {
    return `${failedCount.value} reference${failedCount.value === 1 ? '' : 's'} could not be indexed.`
  }

  if (props.status === 'ready') {
    return `${readyCount.value} reference${readyCount.value === 1 ? '' : 's'} ready.`
  }

  return ''
})

const confirm = useConfirm()

const { showSuccess, showError } = useToast()

function confirmDelete(doc) {
  confirm.require({
    message: `Remove "${doc.filename}" from this chat? This deletes the file and its indexed content.`,
    header: 'Delete file',
    // No glyph icon font in this world -- the dialog carries no mark.
    rejectLabel: 'Cancel',
    acceptLabel: 'Delete',
    // Neutral cancel (drops the default primary/coral fill); darker destructive
    // accept via the global .confirm-delete-strong rule in base.css.
    rejectClass: 'p-button-text p-button-secondary',
    acceptClass: 'p-button-danger confirm-delete-strong',
    accept: async () => {
      try {
        await deleteDocument(doc.id)
        showSuccess(`${doc.filename} removed.`)
        emit('refresh')
      } catch {
        showError(`Could not delete ${doc.filename}. Please try again.`)
        emit('refresh')
      }
    },
  })
}
</script>

<style scoped>
/* Status caption card: card stock with a 3px tab-colour rule at the head,
   never a side border. */
.ref-status {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding: 0.4rem 0.75rem;
  background: var(--card);
  /* Head rule reads as a tab edge: top corners square, bottom corners card radius. */
  border-radius: 0 0 var(--radius-card) var(--radius-card);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--lh-body);
  border: 1px solid var(--card-edge);
  border-top: 3px solid var(--color-accent);
  color: var(--ink);
}

.ref-status.is-ready {
  border-top-color: var(--tab-mastered);
}

.ref-status.is-failed {
  border-top-color: var(--tab-focus);
  color: var(--ink-marker-text);
}

/* A transient outage, not a rejected document: same warning tab edge, but the
   ink stays neutral so a stale ready/pending count above it still reads. */
.ref-status.is-unavailable {
  border-top-color: var(--tab-focus);
}

.ref-unavailable {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  line-height: 1.75rem;
}

/* Only when a last-known status line sits above it, so the outage row reads as
   a second line rather than a floating sentence. */
.ref-header + .ref-unavailable {
  border-top: 1px solid var(--card-edge);
}

.ref-retry {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: var(--ink-learner);
  font: inherit;
  text-decoration: underline;
}

.ref-retry:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}

.ref-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: inherit;
  font: inherit;
  text-align: left;
}
/* Drawn strokes, not a glyph font: one weight, round ends, the caption's ink. */
.ref-icon {
  flex-shrink: 0;
}
.ref-chevron {
  margin-left: auto;
}
/* A still arc says nothing, and .ref-text already spells the state out beside
   it, so the spinner simply leaves rather than freezing. */
@media (prefers-reduced-motion: reduce) {
  .ref-spinner {
    display: none;
  }
}
.ref-file-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.ref-file-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: var(--fs-label);
  line-height: 1.75rem;
  border-top: 1px solid var(--card-edge);
}
.ref-file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ref-file-status {
  color: var(--pencil);
}
.ref-file-status.is-failed {
  color: var(--ink-marker-text);
}
.ref-file-error {
  color: var(--ink-marker-text);
}
.ref-file-delete {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--ink-learner);
  padding: 0.2rem;
  border-radius: var(--radius-sm);
}
.ref-file-delete:focus-visible {
  outline: 2px solid var(--color-accent-ring);
  outline-offset: 2px;
}
</style>
