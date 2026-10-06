import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AssistantBubble from '../components/chat/AssistantBubble.vue'
import MarkdownContent from '../components/chat/MarkdownContent.vue'

describe('AssistantBubble', () => {
  it('renders markdown content (bold becomes <strong>)', () => {
    const w = mount(AssistantBubble, {
      props: { message: { content: '**bold**', tool_calls: [], citations: [] } },
    })

    expect(w.html()).toContain('<strong>bold</strong>')
  })

  it('renders tool-call chips with summary text', () => {
    const w = mount(AssistantBubble, {
      props: {
        message: {
          content: '',
          tool_calls: [
            { id: 't1', name: 'retrieve_chunks', state: 'done', summary: 'Found 5 passages' },
          ],
          citations: [],
        },
      },
    })

    expect(w.text()).toContain('Found 5 passages')
  })

  it('renders citations with doc_name and page', () => {
    const w = mount(AssistantBubble, {
      props: {
        message: {
          content: '',
          tool_calls: [],
          citations: [{ doc_id: 'd', doc_name: 'Doc', page: 1 }],
        },
      },
    })

    expect(w.text()).toContain('Doc')
    expect(w.text()).toContain('p.1')
  })

  it('shows cancelled marker when status is cancelled', () => {
    const w = mount(AssistantBubble, {
      props: {
        message: { content: 'partial', tool_calls: [], citations: [], status: 'cancelled' },
      },
    })

    expect(w.text()).toMatch(/stopped/i)
    expect(w.find('.cancelled-marker').exists()).toBe(true)
  })

  it('shows an interrupted marker for partial messages', () => {
    const w = mount(AssistantBubble, {
      props: {
        message: { content: 'partial text', tool_calls: [], citations: [], status: 'partial' },
      },
    })

    expect(w.text()).toContain('(interrupted)')
  })

  it('does not show cancelled marker when status is complete', () => {
    const w = mount(AssistantBubble, {
      props: {
        message: { content: 'full answer', tool_calls: [], citations: [], status: 'complete' },
      },
    })

    expect(w.find('.cancelled-marker').exists()).toBe(false)
  })

  it('streaming=true: MarkdownContent receives streaming=true, testid is msg-streaming', () => {
    const w = mount(AssistantBubble, {
      props: {
        message: { content: 'hello', tool_calls: [], citations: [] },
        streaming: true,
      },
    })

    expect(w.findComponent(MarkdownContent).props('streaming')).toBe(true)
    expect(w.attributes('data-testid')).toBe('msg-streaming')
    expect(w.classes()).toContain('streaming')
  })

  it('streaming=false: MarkdownContent receives streaming=false, testid is msg-assistant', () => {
    const w = mount(AssistantBubble, {
      props: {
        message: { content: 'hello', tool_calls: [], citations: [] },
        streaming: false,
      },
    })

    expect(w.findComponent(MarkdownContent).props('streaming')).toBe(false)
    expect(w.attributes('data-testid')).toBe('msg-assistant')
    expect(w.classes()).not.toContain('streaming')
  })

  it('root element has classes msg and assistant', () => {
    const w = mount(AssistantBubble, {
      props: { message: { content: 'test', tool_calls: [], citations: [] } },
    })

    expect(w.classes()).toContain('msg')
    expect(w.classes()).toContain('assistant')
  })

  it('role-tag reads "tutor"', () => {
    const w = mount(AssistantBubble, {
      props: { message: { content: 'test', tool_calls: [], citations: [] } },
    })

    expect(w.find('.role-tag').text()).toBe('tutor')
  })

  it('does not render an empty content pill when content is empty and not streaming', () => {
    // Live smoke 2026-08-02: a turn that was tool-call-only (ask_check_questions,
    // no prose) rendered a blank bubble above the check card.
    const w = mount(AssistantBubble, {
      props: {
        message: {
          content: '',
          tool_calls: [{ id: 't1', name: 'ask_check_questions', state: 'done' }],
          citations: [],
        },
        streaming: false,
      },
    })

    expect(w.find('.content').exists()).toBe(false)
  })

  it('still renders the content pill while streaming even if content is empty so far', () => {
    const w = mount(AssistantBubble, {
      props: {
        message: { content: '', tool_calls: [], citations: [] },
        streaming: true,
      },
    })

    expect(w.find('.content').exists()).toBe(true)
  })

  it('hides an error tool chip when the same tool later succeeded in the message', () => {
    // Live smoke 2026-08-02: "Could not ask questions" then "Questions asked"
    // both shown — retry succeeded, failure badge is learner-facing noise.
    const w = mount(AssistantBubble, {
      props: {
        message: {
          content: 'text',
          tool_calls: [
            { id: 't1', name: 'ask_check_questions', state: 'error' },
            { id: 't2', name: 'ask_check_questions', state: 'done' },
          ],
          citations: [],
        },
      },
    })

    expect(w.text()).not.toContain('Could not ask questions')
    expect(w.findAll('.tool-call-row').length).toBe(1)
  })

  it('keeps an error tool chip when no later success for that tool exists', () => {
    const w = mount(AssistantBubble, {
      props: {
        message: {
          content: 'text',
          tool_calls: [{ id: 't1', name: 'ask_check_questions', state: 'error' }],
          citations: [],
        },
      },
    })

    expect(w.text()).toContain('Could not ask questions')
  })

  it('renders without tool_calls or citations fields (guards against missing props)', () => {
    const w = mount(AssistantBubble, {
      props: { message: { content: 'safe' } },
    })

    expect(w.exists()).toBe(true)
    expect(w.text()).toContain('safe')
  })

})

const recapBatch = {
  gap: 'atp',
  total: 1,
  items: [
    {
      question: 'Q?',
      options: ['a', 'b'],
      status: 'answered',
      selectedIndex: 0,
      correctIndex: 0,
      correct: true,
      explanation: 'a.',
    },
  ],
}

describe('AssistantBubble check_batch', () => {
  it('renders CheckRecap and suppresses tool-call chips when check_batch present', () => {
    const w = mount(AssistantBubble, {
      props: {
        message: {
          content: '',
          check_batch: recapBatch,
          tool_calls: [{ id: 't1', name: 'ask_check_questions', state: 'done' }],
        },
      },
    })

    expect(w.find('[data-testid="check-recap"]').exists()).toBe(true)
    expect(w.find('.tool-call-row').exists()).toBe(false)
  })

  it('does not render the empty content pill when check_batch present and content empty', () => {
    const w = mount(AssistantBubble, {
      props: { message: { content: '', check_batch: recapBatch } },
    })

    expect(w.find('.content').exists()).toBe(false)
  })

  it('still renders non-empty content alongside the recap', () => {
    const w = mount(AssistantBubble, {
      props: { message: { content: 'Nice work!', check_batch: recapBatch } },
    })

    expect(w.find('[data-testid="check-recap"]').exists()).toBe(true)
    expect(w.text()).toContain('Nice work!')
  })

  it('unchanged when check_batch absent', () => {
    const w = mount(AssistantBubble, {
      props: { message: { content: 'hello', tool_calls: [] } },
    })

    expect(w.find('[data-testid="check-recap"]').exists()).toBe(false)
    expect(w.find('.content').exists()).toBe(true)
  })
})
