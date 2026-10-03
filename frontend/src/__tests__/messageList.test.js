import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageList from '../components/chat/MessageList.vue'
import UserBubble from '../components/chat/UserBubble.vue'
import AssistantBubble from '../components/chat/AssistantBubble.vue'

const userMsg = { message_id: 'u1', role: 'user', content: 'q' }

const assistantMsg = {
  message_id: 'a1',
  role: 'assistant',
  content: 'a',
  tool_calls: [],
  citations: [],
  status: 'complete',
}

const streamingMsg = {
  role: 'assistant',
  content: 'stream',
  tool_calls: [],
  citations: [],
}

describe('MessageList', () => {
  it('renders user and assistant messages in order', () => {
    const w = mount(MessageList, {
      props: { messages: [userMsg, assistantMsg] },
    })

    expect(w.findAllComponents(UserBubble)).toHaveLength(1)
    expect(w.findAllComponents(AssistantBubble)).toHaveLength(1)
    expect(w.findAllComponents(AssistantBubble)[0].props('streaming')).toBe(false)
  })

  // U-01: assistant rows with nothing renderable (no content, no batch, no
  // tool calls, no citations, not cancelled/partial) painted empty bubbles.
  it('skips assistant messages with nothing to render (U-01)', () => {
    const empty = {
      message_id: 'a-empty',
      role: 'assistant',
      content: '',
      tool_calls: [],
      citations: [],
      status: 'complete',
      check_batch: null,
    }

    const w = mount(MessageList, {
      props: { messages: [userMsg, empty, assistantMsg] },
    })

    expect(w.findAllComponents(AssistantBubble)).toHaveLength(1)
    expect(w.findAllComponents(UserBubble)).toHaveLength(1)
  })

  it('keeps empty-content assistant rows that carry a marker or attachments (U-01)', () => {
    const cancelled = {
      message_id: 'a-c',
      role: 'assistant',
      content: '',
      tool_calls: [],
      citations: [],
      status: 'cancelled',
    }

    const recap = {
      message_id: 'a-r',
      role: 'assistant',
      content: '',
      tool_calls: [],
      citations: [],
      status: 'complete',
      check_batch: { gap: 'g', total: 1, items: [] },
    }

    const w = mount(MessageList, {
      props: { messages: [cancelled, recap] },
    })

    expect(w.findAllComponents(AssistantBubble)).toHaveLength(2)
  })

  it('streamingMessage renders an extra AssistantBubble with streaming===true', () => {
    const w = mount(MessageList, {
      props: {
        messages: [userMsg, assistantMsg],
        streamingMessage: streamingMsg,
      },
    })

    const bubbles = w.findAllComponents(AssistantBubble)
    // one for the regular assistant msg, one for streaming
    expect(bubbles).toHaveLength(2)
    const streamingBubble = bubbles.find((b) => b.props('streaming') === true)
    expect(streamingBubble).toBeDefined()
    expect(w.find('[data-testid="msg-streaming"]').exists()).toBe(true)
  })

  it('typing indicator shows when awaiting=true and no streamingMessage', () => {
    const w = mount(MessageList, {
      props: { messages: [userMsg], awaiting: true },
    })

    expect(w.find('[data-testid="msg-typing"]').exists()).toBe(true)
  })

  // D-07: aria-label is not a supported name source on a <p>, so the text is a
  // visually-hidden sibling of the dots instead.
  it('typing indicator names itself with visually-hidden text, not aria-label', () => {
    const w = mount(MessageList, {
      props: { messages: [userMsg], awaiting: true },
    })

    const typing = w.find('[data-testid="msg-typing"]')
    expect(typing.find('.sr-only').text()).toBe('Tutor is thinking')
    expect(typing.find('p.typing-dots').attributes('aria-label')).toBeUndefined()
    // The sr-only span must not sit inside the dot row: `.typing-dots span`
    // would style it as a fourth dot.
    expect(typing.findAll('p.typing-dots .sr-only')).toHaveLength(0)
    expect(typing.findAll('p.typing-dots > span')).toHaveLength(3)
  })

  it('typing indicator NOT shown when awaiting=false', () => {
    const w = mount(MessageList, {
      props: { messages: [userMsg], awaiting: false },
    })

    expect(w.find('[data-testid="msg-typing"]').exists()).toBe(false)
  })

  it('typing indicator NOT shown when streamingMessage is set (even if awaiting=true)', () => {
    const w = mount(MessageList, {
      props: {
        messages: [userMsg],
        streamingMessage: streamingMsg,
        awaiting: true,
      },
    })

    expect(w.find('[data-testid="msg-typing"]').exists()).toBe(false)
  })

  it('idle state: no msg-typing and no msg-streaming', () => {
    const w = mount(MessageList, {
      props: { messages: [userMsg, assistantMsg], awaiting: false },
    })

    expect(w.find('[data-testid="msg-typing"]').exists()).toBe(false)
    expect(w.find('[data-testid="msg-streaming"]').exists()).toBe(false)
  })

  // F-21: an optimistic user row has no message_id, so two of them in a row
  // both fell back to the array index and shared a key. client_id is the
  // stand-in until (and only until) a real server id exists.
  describe('keying (F-21)', () => {
    // The rendered key is not reachable from the component tree (TransitionGroup
    // consumes it), so this asserts what the key buys: a row keeps its own
    // component instance when the list shifts underneath it.
    it('keeps an id-less row on its own instance when older messages are prepended', async () => {
      const rows = [
        { message_id: 'u9', role: 'user', content: 'one' },
        { role: 'user', content: 'two', client_id: 'c-2' },
      ]

      const w = mount(MessageList, { props: { messages: rows } })
      const firstUid = w.findAllComponents(UserBubble)[0].vm.$.uid
      await w.setProps({
        messages: [{ message_id: 'u8', role: 'user', content: 'older' }, ...rows],
      })
      const after = w.findAllComponents(UserBubble)
      expect(after.map((b) => b.props('content'))).toEqual(['older', 'one', 'two'])
      // Index keys re-point the first instance at 'older'; a stable id keeps
      // 'one' on the instance that already rendered it.
      expect(after[1].vm.$.uid).toBe(firstUid)
    })

    it('keeps an optimistic row on its own instance too', async () => {
      const rows = [
        { role: 'user', content: 'one', client_id: 'c-1' },
        { role: 'user', content: 'two', client_id: 'c-2' },
      ]

      const w = mount(MessageList, { props: { messages: rows } })
      const firstUid = w.findAllComponents(UserBubble)[0].vm.$.uid
      await w.setProps({
        messages: [{ role: 'user', content: 'older', client_id: 'c-0' }, ...rows],
      })
      const after = w.findAllComponents(UserBubble)
      expect(after.map((b) => b.props('content'))).toEqual(['older', 'one', 'two'])
      expect(after[1].vm.$.uid).toBe(firstUid)
    })

    it('still renders rows that carry neither id', () => {
      const w = mount(MessageList, {
        props: { messages: [{ role: 'user', content: 'q' }] },
      })

      expect(w.findAllComponents(UserBubble)).toHaveLength(1)
    })

    // Dup-key fix: a local Stop cancel appends an assistant row with the
    // literal message_id 'pending' (session.js handleCancelled). `??` does
    // not skip that string, so two such rows shared a key. The fallback must
    // treat 'pending' as absent and use client_id instead.
    //
    // The dupe only breaks Vue's keyed diff when both 'pending' rows land in
    // the "unknown middle" range of a patch (i.e. neither the head nor tail
    // sync can resolve them positionally) -- which is exactly what happens
    // when an older row drops off the front and a new one lands at the back
    // in the same update. A same-key-at-tail shuffle (see the other tests in
    // this describe block) happens to resolve correctly by luck, so this
    // case is asserted separately.
    it('keeps two locally-cancelled rows (both message_id="pending") on distinct instances across a full reshuffle', async () => {
      const pending1 = {
        message_id: 'pending',
        role: 'assistant',
        content: 'one',
        tool_calls: [],
        citations: [],
        status: 'cancelled',
        client_id: 'c-1',
      }

      const pending2 = {
        message_id: 'pending',
        role: 'assistant',
        content: 'two',
        tool_calls: [],
        citations: [],
        status: 'cancelled',
        client_id: 'c-2',
      }

      const older = {
        message_id: 'a-older',
        role: 'assistant',
        content: 'zero',
        tool_calls: [],
        citations: [],
        status: 'complete',
      }

      const newer = {
        message_id: 'a-newer',
        role: 'assistant',
        content: 'three',
        tool_calls: [],
        citations: [],
        status: 'complete',
      }

      const w = mount(MessageList, { props: { messages: [older, pending1, pending2] } })
      const bubbles = w.findAllComponents(AssistantBubble)
      const oneUid = bubbles.find((b) => b.props('message').content === 'one').vm.$.uid

      await w.setProps({ messages: [pending1, pending2, newer] })

      const after = w.findAllComponents(AssistantBubble)
      expect(after.map((b) => b.props('message').content)).toEqual(['one', 'two', 'three'])
      const oneAfter = after.find((b) => b.props('message').content === 'one')
      expect(oneAfter.vm.$.uid).toBe(oneUid)
    })
  })

  // F-18: the transcript is no longer a live region — it spammed screen
  // readers with every token mutation while streaming. Discrete
  // announcements live in SessionView instead (see sessionView.test.js).
  it('message list is not a live region', () => {
    const w = mount(MessageList, { props: { messages: [userMsg] } })
    expect(w.find('[aria-live]').exists()).toBe(false)
    const list = w.find('.message-list')
    expect(list.exists()).toBe(true)
    expect(list.attributes('aria-atomic')).toBeUndefined()
  })

  // Thread redesign: the gap between turns grows only at a change of voice.
  describe('speaker-change gap', () => {
    it('marks a voice change, not a run of the same voice', () => {
      const messages = [
        { message_id: 'a1', role: 'assistant', content: 'a1', tool_calls: [], citations: [] },
        { message_id: 'u1', role: 'user', content: 'u1' },
        { message_id: 'u2', role: 'user', content: 'u2' },
        { message_id: 'a2', role: 'assistant', content: 'a2', tool_calls: [], citations: [] },
      ]

      const w = mount(MessageList, { props: { messages } })
      const rows = w.findAll('.msg')
      expect(rows).toHaveLength(4)
      expect(rows[0].classes()).not.toContain('msg-row--speaker-change')
      expect(rows[1].classes()).toContain('msg-row--speaker-change')
      expect(rows[2].classes()).not.toContain('msg-row--speaker-change')
      expect(rows[3].classes()).toContain('msg-row--speaker-change')
    })

    it('marks the typing row when the last rendered turn was the learner', () => {
      const w = mount(MessageList, { props: { messages: [userMsg], awaiting: true } })
      expect(w.find('[data-testid="msg-typing"]').classes()).toContain('msg-row--speaker-change')
    })

    it('does not mark the typing row when the last rendered turn was the tutor', () => {
      const w = mount(MessageList, { props: { messages: [assistantMsg], awaiting: true } })
      expect(w.find('[data-testid="msg-typing"]').classes()).not.toContain(
        'msg-row--speaker-change',
      )
    })

    it('marks the streaming bubble when the last rendered turn was the learner', () => {
      const w = mount(MessageList, {
        props: { messages: [userMsg], streamingMessage: streamingMsg },
      })

      expect(w.find('[data-testid="msg-streaming"]').classes()).toContain('msg-row--speaker-change')
    })
  })
})
