import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ToolCallChip from '../components/chat/ToolCallChip.vue'

describe('ToolCallChip', () => {
  it('renders running label for retrieve_chunks', () => {
    const w = mount(ToolCallChip, {
      props: { tool_call: { name: 'retrieve_chunks', id: '1' }, state: 'running' },
    })

    expect(w.text()).toMatch(/Searching your document/i)
    expect(w.classes()).toContain('tool-pill--running')
  })

  it('renders running label for update_topic_profile', () => {
    const w = mount(ToolCallChip, {
      props: { tool_call: { name: 'update_topic_profile', id: '1' }, state: 'running' },
    })

    expect(w.text()).toMatch(/Updating profile/i)
  })

  it('renders running label for record_learning_event', () => {
    const w = mount(ToolCallChip, {
      props: { tool_call: { name: 'record_learning_event', id: '1' }, state: 'running' },
    })

    expect(w.text()).toMatch(/Recording answer/i)
  })

  it('renders done label and class', () => {
    const w = mount(ToolCallChip, {
      props: {
        tool_call: { name: 'retrieve_chunks', id: '1', summary: 'Found 5 passages' },
        state: 'done',
      },
    })

    expect(w.text()).toContain('Found 5 passages')
    expect(w.classes()).toContain('tool-pill--done')
  })

  it('renders fallback done label when no summary provided', () => {
    const w = mount(ToolCallChip, {
      props: { tool_call: { name: 'retrieve_chunks', id: '1' }, state: 'done' },
    })

    expect(w.text()).toMatch(/Search complete/i)
  })

  it('renders error label and class', () => {
    const w = mount(ToolCallChip, {
      props: { tool_call: { name: 'retrieve_chunks', id: '1' }, state: 'error' },
    })

    expect(w.text()).toMatch(/Search failed/i)
    expect(w.classes()).toContain('tool-pill--error')
  })

  it('falls back to tool name for unknown tool', () => {
    const w = mount(ToolCallChip, {
      props: { tool_call: { name: 'mystery_tool', id: '1' }, state: 'running' },
    })

    expect(w.text()).toContain('mystery_tool')
  })

  it('shows the error string as title on the error state', () => {
    const wrapper = mount(ToolCallChip, {
      props: {
        tool_call: { name: 'update_topic_profile', error: 'evidence_type must be ...' },
        state: 'error',
      },
    })

    expect(wrapper.find('.tool-pill').attributes('title')).toContain('evidence_type')
  })
})
