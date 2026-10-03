import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CitationsList from '../components/chat/CitationsList.vue'

describe('CitationsList', () => {
  it('renders nothing for empty array', () => {
    const w = mount(CitationsList, { props: { citations: [] } })
    expect(w.html().trim()).toBe('<!--v-if-->')
  })

  it('renders document name and page list', () => {
    const w = mount(CitationsList, {
      props: {
        citations: [
          { doc_id: 'algo-ch3', doc_name: 'Algorithms Chapter 3', page: 42 },
          { doc_id: 'algo-ch3', doc_name: 'Algorithms Chapter 3', page: 44 },
        ],
      },
    })

    expect(w.text()).toContain('Algorithms Chapter 3')
    expect(w.text()).toContain('p.42')
    expect(w.text()).toContain('p.44')
  })

  it('groups citations from same document', () => {
    const w = mount(CitationsList, {
      props: {
        citations: [
          { doc_id: 'a', doc_name: 'A', page: 1 },
          { doc_id: 'b', doc_name: 'B', page: 2 },
          { doc_id: 'a', doc_name: 'A', page: 3 },
        ],
      },
    })

    const docs = w.findAll('.citation-doc')
    expect(docs).toHaveLength(2)
    expect(docs[0].text()).toContain('A')
    expect(docs[0].text()).toContain('p.1')
    expect(docs[0].text()).toContain('p.3')
  })

  it('falls back to doc_id when doc_name is missing', () => {
    const w = mount(CitationsList, {
      props: { citations: [{ doc_id: 'fallback-id', page: 7 }] },
    })

    expect(w.text()).toContain('fallback-id')
  })

  it('renders doc name with no page chips when citations lack a page field', () => {
    // Phase 1 shape: { doc_id, text } with no page. Must not render p.undefined.
    const w = mount(CitationsList, {
      props: { citations: [{ doc_id: 'algo-ch3', text: 'a snippet' }] },
    })

    expect(w.text()).toContain('algo-ch3')
    expect(w.text()).not.toContain('p.')
    expect(w.find('.citation-pages').exists()).toBe(false)
  })
})
