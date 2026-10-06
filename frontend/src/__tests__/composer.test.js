import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Composer from '@/components/chat/Composer.vue'

function mountComposer(props = {}) {
  return mount(Composer, {
    props: {
      modelValue: '',
      disabled: false,
      uploading: false,
      sending: false,
      streamState: 'idle',
      ...props,
    },
  })
}

describe('Composer', () => {
  it('emits send on plain Enter when modelValue non-empty, idle, not disabled', async () => {
    const wrapper = mountComposer({ modelValue: 'hello' })
    const textarea = wrapper.get('[data-testid="session-input"]')
    await textarea.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('send')).toHaveLength(1)
  })

  it('does NOT emit send on Shift+Enter', async () => {
    const wrapper = mountComposer({ modelValue: 'hello' })
    const textarea = wrapper.get('[data-testid="session-input"]')
    await textarea.trigger('keydown', { key: 'Enter', shiftKey: true })
    expect(wrapper.emitted('send')).toBeFalsy()
  })

  it('does NOT emit send when modelValue is empty', async () => {
    const wrapper = mountComposer({ modelValue: '' })
    const textarea = wrapper.get('[data-testid="session-input"]')
    await textarea.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('send')).toBeFalsy()
  })

  it('does NOT emit send when modelValue is whitespace only', async () => {
    const wrapper = mountComposer({ modelValue: '   ' })
    const textarea = wrapper.get('[data-testid="session-input"]')
    await textarea.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('send')).toBeFalsy()
  })

  it('click session-send emits send', async () => {
    const wrapper = mountComposer({ modelValue: 'hello' })
    await wrapper.get('[data-testid="session-send"]').trigger('click')
    expect(wrapper.emitted('send')).toHaveLength(1)
  })

  it('shows session-send when streamState is idle', () => {
    const wrapper = mountComposer({ streamState: 'idle' })
    expect(wrapper.find('[data-testid="session-send"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="session-stop"]').exists()).toBe(false)
  })

  it('shows session-stop and hides session-send when streamState is streaming', () => {
    const wrapper = mountComposer({ streamState: 'streaming' })
    expect(wrapper.find('[data-testid="session-stop"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="session-send"]').exists()).toBe(false)
  })

  it('click session-stop emits stop', async () => {
    const wrapper = mountComposer({ streamState: 'streaming' })
    await wrapper.get('[data-testid="session-stop"]').trigger('click')
    expect(wrapper.emitted('stop')).toHaveLength(1)
  })

  it('stop button is disabled when streamState is stopping', () => {
    const wrapper = mountComposer({ streamState: 'stopping' })
    const stopBtn = wrapper.get('[data-testid="session-stop"]')
    expect(stopBtn.attributes('disabled')).toBeDefined()
  })

  it('does NOT emit send when streamState is not idle (Enter key)', async () => {
    const wrapper = mountComposer({ modelValue: 'hello', streamState: 'streaming' })
    const textarea = wrapper.get('[data-testid="session-input"]')
    await textarea.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('send')).toBeFalsy()
  })

  it('disabled=true disables the textarea', () => {
    const wrapper = mountComposer({ disabled: true })
    const textarea = wrapper.get('[data-testid="session-input"]')
    expect(textarea.attributes('disabled')).toBeDefined()
  })

  it('disabled=true disables the send button', () => {
    const wrapper = mountComposer({ disabled: true, modelValue: 'hello' })
    const sendBtn = wrapper.get('[data-testid="session-send"]')
    expect(sendBtn.attributes('disabled')).toBeDefined()
  })

  it('emits update:modelValue when typing in textarea', async () => {
    const wrapper = mountComposer({ modelValue: '' })
    const textarea = wrapper.get('[data-testid="session-input"]')
    await textarea.setValue('new text')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted[emitted.length - 1][0]).toBe('new text')
  })

  it('emits attach with the File when file input changes', async () => {
    const wrapper = mountComposer()
    const file = new File(['bytes'], 'doc.pdf', { type: 'application/pdf' })
    const input = wrapper.get('[data-testid="session-upload-input"]')
    Object.defineProperty(input.element, 'files', {
      value: [file],
      configurable: true,
    })
    await input.trigger('change')
    const attached = wrapper.emitted('attach')
    expect(attached).toHaveLength(1)
    expect(attached[0][0]).toBe(file)
  })

  it('shows char counter when modelValue is non-empty', () => {
    const wrapper = mountComposer({ modelValue: 'hello' })
    expect(wrapper.find('.composer-count').exists()).toBe(true)
  })

  it('does NOT show char counter when modelValue is empty', () => {
    const wrapper = mountComposer({ modelValue: '' })
    expect(wrapper.find('.composer-count').exists()).toBe(false)
  })

  // I-10: cap must match ChatRequest.message maxLength (docs/api/openapi.yaml).
  it('caps the draft at the contract limit 4000', () => {
    const wrapper = mountComposer({ modelValue: '' })
    expect(wrapper.get('[data-testid="session-input"]').attributes('maxlength')).toBe('4000')
  })

  // A1: textarea must have an accessible name for screen readers.
  it('has an accessible name on the textarea', () => {
    const wrapper = mountComposer()
    expect(wrapper.get('[data-testid="session-input"]').attributes('aria-label')).toBe(
      'Message the tutor',
    )
  })

  // D-09: the counter changes on every keystroke, so it must not be a live
  // region. The cap is a static description instead, and only the last 10%
  // before the cap is announced.
  describe('character-limit announcement', () => {
    const live = (w) => w.get('[data-testid="composer-limit-live"]')

    it('keeps the visible counter out of the live region', () => {
      const wrapper = mountComposer({ modelValue: 'hello' })
      const count = wrapper.get('.composer-count')
      expect(count.attributes('aria-live')).toBeUndefined()
      expect(count.attributes('role')).toBeUndefined()
      expect(live(wrapper).attributes('aria-live')).toBe('polite')
    })

    it('describes the cap on the textarea', () => {
      const wrapper = mountComposer()

      const describedby = wrapper
        .get('[data-testid="session-input"]')
        .attributes('aria-describedby')

      expect(describedby).toContain('composer-char-limit')
      expect(wrapper.get('#composer-char-limit').text()).toContain('4,000 characters')
    })

    it('merges the parent description with the cap hint', () => {
      const wrapper = mountComposer({ describedby: 'cap-banner' })
      expect(wrapper.get('[data-testid="session-input"]').attributes('aria-describedby')).toBe(
        'cap-banner composer-char-limit',
      )
    })

    it('is silent below 90% of the cap', () => {
      const wrapper = mountComposer({ modelValue: 'a'.repeat(3599) })
      expect(live(wrapper).text()).toBe('')
    })

    it('announces the remaining count from 90% of the cap', () => {
      const wrapper = mountComposer({ modelValue: 'a'.repeat(3600) })
      expect(live(wrapper).text()).toBe('400 characters left')
    })

    it('announces the singular at one character left', () => {
      const wrapper = mountComposer({ modelValue: 'a'.repeat(3999) })
      expect(live(wrapper).text()).toBe('1 character left')
    })

    it('says so outright at the cap', () => {
      const wrapper = mountComposer({ modelValue: 'a'.repeat(4000) })
      expect(live(wrapper).text()).toBe('Character limit reached')
    })
  })
})
