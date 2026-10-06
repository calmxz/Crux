import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatEmptyState from '@/components/chat/EmptyState.vue'

describe('ChatEmptyState', () => {
  describe('active variant (archived=false, default)', () => {
    it('renders data-testid="session-empty"', () => {
      const wrapper = mount(ChatEmptyState)
      expect(wrapper.find('[data-testid="session-empty"]').exists()).toBe(true)
    })

    it('renders eyebrow "begin"', () => {
      const wrapper = mount(ChatEmptyState)
      expect(wrapper.find('.empty-eyebrow').text()).toBe('begin')
    })

    it('renders the prompt line', () => {
      const wrapper = mount(ChatEmptyState)
      expect(wrapper.find('.empty-line').text()).toBe(
        'Send a question or share what you already know.',
      )
    })

    it('renders at least one quick-prompt pill', () => {
      const wrapper = mount(ChatEmptyState)
      const pills = wrapper.findAll('[data-testid^="quick-prompt-"]')
      expect(pills.length).toBeGreaterThan(0)
    })

    it('clicking quick-prompt-0 emits "quick-prompt" with that pill text', async () => {
      const wrapper = mount(ChatEmptyState)
      const pill = wrapper.get('[data-testid="quick-prompt-0"]')
      await pill.trigger('click')
      const emitted = wrapper.emitted('quick-prompt')
      expect(emitted).toBeTruthy()
      expect(emitted[0][0]).toBe('Where should I start with this topic?')
    })

    it('emitted payload matches the pill text for each pill', async () => {
      const wrapper = mount(ChatEmptyState)
      const pills = wrapper.findAll('[data-testid^="quick-prompt-"]')

      for (let i = 0; i < pills.length; i++) {
        const text = pills[i].text()
        await pills[i].trigger('click')
        const emitted = wrapper.emitted('quick-prompt')
        expect(emitted[i][0]).toBe(text)
        expect(text.length).toBeGreaterThan(0)
      }
    })

    it('renders the spark SVG', () => {
      const wrapper = mount(ChatEmptyState)
      expect(wrapper.find('.empty-spark').exists()).toBe(true)
    })

    it('does NOT have class archived-empty', () => {
      const wrapper = mount(ChatEmptyState)
      expect(wrapper.find('.archived-empty').exists()).toBe(false)
    })
  })

  describe('archived variant (archived=true)', () => {
    it('renders eyebrow "archive"', () => {
      const wrapper = mount(ChatEmptyState, { props: { archived: true } })
      expect(wrapper.find('.empty-eyebrow').text()).toBe('archive')
    })

    it('renders "No transcript stored for this session." line', () => {
      const wrapper = mount(ChatEmptyState, { props: { archived: true } })
      expect(wrapper.find('.empty-line').text()).toBe(
        'No transcript stored for this session.',
      )
    })

    it('root element has class "archived-empty"', () => {
      const wrapper = mount(ChatEmptyState, { props: { archived: true } })
      expect(wrapper.classes()).toContain('archived-empty')
    })

    it('does NOT render quick-prompt pills', () => {
      const wrapper = mount(ChatEmptyState, { props: { archived: true } })
      expect(wrapper.findAll('[data-testid^="quick-prompt-"]').length).toBe(0)
    })

    it('does NOT render the spark SVG', () => {
      const wrapper = mount(ChatEmptyState, { props: { archived: true } })
      expect(wrapper.find('.empty-spark').exists()).toBe(false)
    })
  })
})
