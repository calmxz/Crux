<script setup>
import { computed } from 'vue'

const props = defineProps({
  citations: { type: Array, required: true },
})

const grouped = computed(() => {
  const map = new Map()

  for (const c of props.citations || []) {
    const key = c.doc_id
    const name = c.doc_name || c.doc_id

    if (!map.has(key)) map.set(key, { doc_id: key, doc_name: name, pages: [] })

    // Phase 1 citations are {doc_id, text} with no page; Phase 2 (Task 14)
    // extends the contract with page. Only show chips for real page numbers.
    if (c.page !== undefined && c.page !== null) map.get(key).pages.push(c.page)
  }

  return Array.from(map.values())
})
</script>

<template>
  <div v-if="grouped.length" class="citations-list">
    <p v-for="(doc, i) in grouped" :key="doc.doc_id" class="citation-doc">
      <sup class="citation-ref" data-tabular>{{ i + 1 }}</sup>
      <span class="citation-doc-name">{{ doc.doc_name }}</span>
      <span v-if="doc.pages.length" class="citation-pages">
        <span v-for="(p, pi) in doc.pages" :key="pi" class="citation-page" data-tabular
          >p.{{ p }}</span
        >
      </span>
    </p>
  </div>
</template>

<style scoped>
/* A footnote block inside the card: pencil, small, above a hairline top rule. */
.citations-list {
  border-top: 1px solid var(--card-edge);
  margin-top: 0.35rem;
  padding-top: 0.35rem;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  color: var(--pencil);
}

.citation-doc {
  display: flex;
  gap: 0.5rem;
  align-items: baseline;
  margin: 0;
  line-height: var(--lh-body);
}

.citation-ref {
  flex: 0 0 auto;
  font-size: 0.75em;
  line-height: 1;
}

.citation-doc-name {
  font-weight: 700;
}

.citation-pages {
  display: inline-flex;
  gap: 0.375rem;
}
</style>
