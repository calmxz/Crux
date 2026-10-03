import { setActivePinia, createPinia } from 'pinia'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useSessionStore } from '@/stores/session.js'
import * as sessionsApi from '@/services/sessionsApi.js'
import * as streamSvc from '@/services/chatStreamService.js'

vi.mock('@/services/sessionsApi.js')

vi.mock('@/services/chatStreamService.js')

vi.mock('@/services/costBus.js', () => ({ reportCostWarning: vi.fn() }))

class ApiErrorLike extends Error {
  constructor(status, body) {
    super('api error')
    this.status = status
    this.body = body
  }
}

function batchEvent() {
  return {
    gap: 'atp',
    total: 2,
    items: [
      { question: 'Q1', options: ['a', 'b'] },
      { question: 'Q2', options: ['a', 'b'] },
    ],
  }
}

describe('multi-check store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('answer advances currentIndex but keeps viewIndex (verdict visible)', async () => {
    const s = useSessionStore()
    s.currentSessionId = 'sid'
    s.handleCheckQuestion(batchEvent())
    expect(s.pendingCheck.viewIndex).toBe(0)
    sessionsApi.answerCheck.mockResolvedValue({
      correct: true,
      explanation: 'a.',
      correct_index: 0,
      current_index: 1,
      total: 2,
      has_next: true,
      done: false,
    })
    await s.answerCheck(0)
    expect(s.pendingCheck.currentIndex).toBe(1)
    expect(s.pendingCheck.viewIndex).toBe(0)
    expect(s.pendingCheck.items[0].status).toBe('answered')
    expect(s.pendingCheck.items[0].correct).toBe(true)
  })

  it('#340 stopCheck streams the stop follow-up and clears the card', async () => {
    const s = useSessionStore()
    s.currentSessionId = 'sid'
    s.handleCheckQuestion(batchEvent())
    streamSvc.streamCheckStop.mockResolvedValue(undefined)
    await s.stopCheck()
    expect(streamSvc.streamCheckStop).toHaveBeenCalledTimes(1)
    expect(streamSvc.streamCheckStop.mock.calls[0][0].sessionId).toBe('sid')
    expect(streamSvc.streamCheckComplete).not.toHaveBeenCalled()
    expect(s.pendingCheck).toBeNull()
  })

  it('#340 stopCheck restores the card when the stop fails before streaming', async () => {
    const s = useSessionStore()
    s.currentSessionId = 'sid'
    s.handleCheckQuestion(batchEvent())
    streamSvc.streamCheckStop.mockRejectedValue(new ApiErrorLike(409, { detail: {} }))
    await s.stopCheck().catch(() => {})
    expect(s.pendingCheck).not.toBeNull()
  })

  it('nextCheck moves view to the next unanswered item', async () => {
    const s = useSessionStore()
    s.currentSessionId = 'sid'
    s.handleCheckQuestion(batchEvent())
    sessionsApi.answerCheck.mockResolvedValue({
      correct: true,
      explanation: 'a.',
      correct_index: 0,
      current_index: 1,
      total: 2,
      has_next: true,
      done: false,
    })
    await s.answerCheck(0)
    s.nextCheck()
    expect(s.pendingCheck.viewIndex).toBe(1)
  })

  // #348: free navigation within one set.
  it('#348 nextCheck / prevCheck move the view without answering, clamped', () => {
    const s = useSessionStore()
    s.currentSessionId = 'sid'
    s.handleCheckQuestion(batchEvent())
    s.prevCheck()
    expect(s.pendingCheck.viewIndex).toBe(0)
    s.nextCheck()
    expect(s.pendingCheck.viewIndex).toBe(1)
    s.nextCheck()
    expect(s.pendingCheck.viewIndex).toBe(1)
    s.prevCheck()
    expect(s.pendingCheck.viewIndex).toBe(0)
    expect(s.pendingCheck.items.every((it) => it.status === 'pending')).toBe(true)
  })

  it('#348 answerCheck grades the viewed item, not the first unresolved one', async () => {
    const s = useSessionStore()
    s.currentSessionId = 'sid'
    s.handleCheckQuestion(batchEvent())
    sessionsApi.answerCheck.mockResolvedValue({
      correct: false,
      explanation: 'b.',
      correct_index: 0,
      current_index: 0,
      total: 2,
      has_next: true,
      done: false,
    })
    s.nextCheck()
    await s.answerCheck(1)
    expect(sessionsApi.answerCheck).toHaveBeenCalledWith('sid', 1, 1)
    expect(s.pendingCheck.items[1].status).toBe('answered')
    expect(s.pendingCheck.items[0].status).toBe('pending')
    expect(s.pendingCheck.currentIndex).toBe(0)
    expect(s.pendingCheck.viewIndex).toBe(1)
  })

  it('#348 skipCheck skips the viewed item and lands on the next unresolved one, wrapping', async () => {
    const s = useSessionStore()
    s.currentSessionId = 'sid'
    s.handleCheckQuestion({
      gap: 'atp',
      total: 3,
      items: [
        { question: 'Q1', options: ['a', 'b'] },
        { question: 'Q2', options: ['a', 'b'] },
        { question: 'Q3', options: ['a', 'b'] },
      ],
    })
    sessionsApi.skipCheck.mockResolvedValue({
      current_index: 0,
      total: 3,
      has_next: true,
      done: false,
    })
    s.nextCheck()
    await s.skipCheck()
    expect(sessionsApi.skipCheck).toHaveBeenCalledWith('sid', 1)
    expect(s.pendingCheck.items[1].status).toBe('skipped')
    expect(s.pendingCheck.viewIndex).toBe(2)
    await s.skipCheck()
    expect(sessionsApi.skipCheck).toHaveBeenLastCalledWith('sid', 2)
    expect(s.pendingCheck.viewIndex).toBe(0)
    expect(streamSvc.streamCheckComplete).not.toHaveBeenCalled()
  })

  it('answering the last item marks done; completeCheck fires once', async () => {
    const s = useSessionStore()
    s.currentSessionId = 'sid'
    s.handleCheckQuestion(batchEvent())
    sessionsApi.answerCheck
      .mockResolvedValueOnce({
        correct: true,
        explanation: 'a.',
        correct_index: 0,
        current_index: 1,
        total: 2,
        has_next: true,
        done: false,
      })
      .mockResolvedValueOnce({
        correct: true,
        explanation: 'a.',
        correct_index: 0,
        current_index: 2,
        total: 2,
        has_next: false,
        done: true,
      })
    streamSvc.streamCheckComplete.mockResolvedValue(undefined)
    await s.answerCheck(0)
    s.nextCheck()
    await s.answerCheck(0)
    expect(s.pendingCheck.items[1].status).toBe('answered')
    await s.completeCheck()
    await s.completeCheck()
    expect(streamSvc.streamCheckComplete).toHaveBeenCalledTimes(1)
    expect(s.pendingCheck).toBeNull()
  })

  it('per-item skip that resolves the batch fires completeCheck', async () => {
    const s = useSessionStore()
    s.currentSessionId = 'sid'
    s.handleCheckQuestion({
      gap: 'atp',
      total: 1,
      items: [{ question: 'Q1', options: ['a', 'b'] }],
    })
    sessionsApi.skipCheck.mockResolvedValue({
      current_index: 1,
      total: 1,
      has_next: false,
      done: true,
    })
    streamSvc.streamCheckComplete.mockResolvedValue(undefined)
    await s.skipCheck()
    expect(streamSvc.streamCheckComplete).toHaveBeenCalledTimes(1)
    expect(s.pendingCheck).toBeNull()
  })

  it('loadSession rebuilds batch at current_index with prior verdicts', async () => {
    const s = useSessionStore()
    sessionsApi.getSession.mockResolvedValue({
      id: 'sid',
      messages: [],
      pending_check: {
        gap: 'atp',
        current_index: 1,
        total: 2,
        items: [
          {
            question: 'Q1',
            options: ['a', 'b'],
            status: 'answered',
            selected_index: 0,
            correct_index: 0,
            correct: true,
            explanation: 'a.',
          },
          {
            question: 'Q2',
            options: ['a', 'b'],
            status: 'pending',
            selected_index: null,
            correct_index: null,
            correct: null,
            explanation: null,
          },
        ],
      },
    })
    await s.loadSession('sid')
    expect(s.pendingCheck.currentIndex).toBe(1)
    expect(s.pendingCheck.viewIndex).toBe(1)
    expect(s.pendingCheck.items[0].correct).toBe(true)
  })

  it('#348 loadSession of a fully resolved batch views the last item, not past it', async () => {
    const s = useSessionStore()

    const resolved = (q) => ({
      question: q,
      options: ['a', 'b'],
      status: 'skipped',
      selected_index: null,
      correct_index: 0,
      correct: null,
      explanation: null,
    })

    sessionsApi.getSession.mockResolvedValue({
      id: 'sid',
      messages: [],
      pending_check: {
        gap: 'atp',
        current_index: 2,
        total: 2,
        items: [resolved('Q1'), resolved('Q2')],
      },
    })
    await s.loadSession('sid')
    expect(s.pendingCheck.currentIndex).toBe(2)
    expect(s.pendingCheck.viewIndex).toBe(1)
  })

  it('followup_skipped clears stream state and sets a quiet notice', async () => {
    const s = useSessionStore()
    s.currentSessionId = 'sid'
    s.handleCheckQuestion(batchEvent())
    streamSvc.streamCheckComplete.mockImplementation(async ({ onEvent }) => {
      onEvent({ event: 'followup_skipped', data: { reason: 'daily_cap' } })
    })
    await s.completeCheck()
    expect(s.followupNotice).toMatch(/daily message limit/i)
    expect(s.streamingMessage).toBeNull()
    expect(s.streamState).toBe('idle')
    expect(s.error).toBeNull()
  })

  it('loadSession maps check_batch onto messages (camelCase)', async () => {
    const store = useSessionStore()
    sessionsApi.getSession.mockResolvedValue({
      id: 's1',
      messages: [
        {
          id: 1,
          role: 'assistant',
          content: '',
          created_at: '2026-06-07T00:00:00Z',
          citations: [],
          tool_calls: [],
          check_batch: {
            gap: 'atp',
            current_index: 1,
            total: 1,
            items: [
              {
                question: 'Q?',
                options: ['a', 'b'],
                status: 'answered',
                selected_index: 0,
                correct_index: 0,
                correct: true,
                explanation: 'a.',
              },
            ],
          },
        },
      ],
      pending_check: null,
    })
    await store.loadSession('s1')
    const cb = store.messages[0].check_batch
    expect(cb.gap).toBe('atp')
    expect(cb.items[0].selectedIndex).toBe(0)
    expect(cb.items[0].correctIndex).toBe(0)
    expect(cb.items[0].correct).toBe(true)
  })

  // #364: set_index / set_total ride every path the card and recap read from.
  it('#364 stream check_question carries set_index / set_total', () => {
    const s = useSessionStore()
    s.handleCheckQuestion({ ...batchEvent(), set_index: 2, set_total: 3 })
    expect(s.pendingCheck.setIndex).toBe(2)
    expect(s.pendingCheck.setTotal).toBe(3)
  })

  it('#364 a pre-set stream event maps set fields to null', () => {
    const s = useSessionStore()
    s.handleCheckQuestion(batchEvent())
    expect(s.pendingCheck.setIndex).toBeNull()
    expect(s.pendingCheck.setTotal).toBeNull()
  })

  it('#364 set_index / set_total survive reload on pending_check and check_batch', async () => {
    const s = useSessionStore()

    const item = {
      question: 'Q1',
      options: ['a', 'b'],
      status: 'answered',
      selected_index: 0,
      correct_index: 0,
      correct: true,
      explanation: 'a.',
    }

    sessionsApi.getSession.mockResolvedValue({
      id: 'sid',
      messages: [
        {
          id: 1,
          role: 'assistant',
          content: '',
          created_at: '2026-06-07T00:00:00Z',
          citations: [],
          check_batch: {
            gap: 'atp',
            current_index: 1,
            total: 1,
            set_index: 1,
            set_total: 3,
            items: [item],
          },
        },
        {
          id: 2,
          role: 'assistant',
          content: '',
          created_at: '2026-06-07T00:00:00Z',
          citations: [],
          check_batch: { gap: 'old', current_index: 1, total: 1, items: [item] },
        },
      ],
      pending_check: {
        gap: 'atp',
        current_index: 0,
        total: 1,
        set_index: 2,
        set_total: 3,
        items: [{ question: 'Q2', options: ['a', 'b'], status: 'pending' }],
      },
    })
    await s.loadSession('sid')
    expect(s.pendingCheck.setIndex).toBe(2)
    expect(s.pendingCheck.setTotal).toBe(3)
    expect(s.messages[0].check_batch.setIndex).toBe(1)
    expect(s.messages[0].check_batch.setTotal).toBe(3)
    expect(s.messages[1].check_batch.setIndex).toBeNull()
    expect(s.messages[1].check_batch.setTotal).toBeNull()
  })

  it('restores pendingCheck when the completion stream fails before any event', async () => {
    const store = useSessionStore()
    store.currentSessionId = 'sid'
    store.handleCheckQuestion(batchEvent())
    streamSvc.streamCheckComplete.mockRejectedValue(new ApiErrorLike(0, { detail: 'offline' }))
    await store.completeCheck().catch(() => {})
    expect(store.pendingCheck).not.toBeNull()
  })

  // E-17: the in-flight guard was invisible to the view, so the card kept its
  // options live while the POST was out and swallowed the second click.
  it('exposes checkAnswering while an answer POST is in flight', async () => {
    const s = useSessionStore()
    s.currentSessionId = 'sid'
    s.handleCheckQuestion(batchEvent())
    let release
    sessionsApi.answerCheck.mockImplementation(
      () =>
        new Promise((res) => {
          release = res
        }),
    )
    expect(s.checkAnswering).toBe(false)
    const p = s.answerCheck(0)
    expect(s.checkAnswering).toBe(true)
    release({
      correct: true,
      explanation: 'a.',
      correct_index: 0,
      current_index: 1,
      total: 2,
      has_next: true,
      done: false,
    })
    await p
    expect(s.checkAnswering).toBe(false)
  })

  // E-20: the composer never locked on an open check, so the constant-false
  // computed and its binding went.
  it('no longer exposes checkLocked', () => {
    const s = useSessionStore()
    expect(s.checkLocked).toBeUndefined()
  })
})
