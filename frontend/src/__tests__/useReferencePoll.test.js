import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'

import {
  useReferencePoll,
  POLL_DELAYS_MS,
  WATCH_CEILING_MS,
} from '@/composables/useReferencePoll.js'

const getSessionIngestion = vi.fn()

vi.mock('@/services/uploadApi.js', () => ({
  getSessionIngestion: (...a) => getSessionIngestion(...a),
}))

const pending = (docs = [{ id: 1, filename: 'a.pdf', status: 'pending' }]) => ({
  status: 'pending',
  documents: docs,
})

const ready = (docs = [{ id: 1, filename: 'a.pdf', status: 'ready' }]) => ({
  status: 'ready',
  documents: docs,
})

// One macrotask hop per await inside poll(), so a bare advanceTimersByTime is
// not enough -- the timer fires, then the fetch promise has to settle.
async function tick(ms) {
  await vi.advanceTimersByTimeAsync(ms)
  await flushPromises()
}

describe('useReferencePoll', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    getSessionIngestion.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('polls once immediately and exposes status and documents', async () => {
    getSessionIngestion.mockResolvedValue(ready())
    const poll = useReferencePoll('s1')
    await flushPromises()
    expect(getSessionIngestion).toHaveBeenCalledTimes(1)
    expect(getSessionIngestion).toHaveBeenCalledWith('s1', { fresh: true, silent: true })
    expect(poll.status.value).toBe('ready')
    expect(poll.documents.value).toHaveLength(1)
    poll.stop()
  })

  it('does not poll at all without a session id', async () => {
    const poll = useReferencePoll(null)
    await flushPromises()
    expect(getSessionIngestion).not.toHaveBeenCalled()
    poll.stop()
  })

  it('stops polling once nothing is pending', async () => {
    getSessionIngestion.mockResolvedValue(ready())
    const poll = useReferencePoll('s1')
    await flushPromises()
    await tick(60000)
    expect(getSessionIngestion).toHaveBeenCalledTimes(1)
    poll.stop()
  })

  it('backs off 2s -> 4s -> 8s -> 15s (capped) while pending', async () => {
    getSessionIngestion.mockResolvedValue(pending())
    const poll = useReferencePoll('s1')
    await flushPromises()
    expect(getSessionIngestion).toHaveBeenCalledTimes(1)

    // Each step: nothing fires one millisecond early, the poll fires on time.
    for (const [i, delay] of [...POLL_DELAYS_MS, 15000, 15000].entries()) {
      await tick(delay - 1)
      expect(getSessionIngestion).toHaveBeenCalledTimes(i + 1)
      await tick(1)
      expect(getSessionIngestion).toHaveBeenCalledTimes(i + 2)
    }

    poll.stop()
  })

  it('resets the backoff to the fast cadence after recovering from a failure', async () => {
    getSessionIngestion.mockRejectedValueOnce(new Error('offline'))
    getSessionIngestion.mockResolvedValue(pending())
    const poll = useReferencePoll('s1')
    await flushPromises()
    expect(poll.failed.value).toBe(true)

    // Retry #1 at 2s recovers; the next poll must be 2s later, not 4s.
    await tick(2000)
    expect(poll.failed.value).toBe(false)
    expect(getSessionIngestion).toHaveBeenCalledTimes(2)
    await tick(2000)
    expect(getSessionIngestion).toHaveBeenCalledTimes(3)
    poll.stop()
  })

  it('sets failed on the FIRST poll failure, keeps retrying, and clears on success', async () => {
    getSessionIngestion.mockRejectedValue(new Error('offline'))
    const poll = useReferencePoll('s1')
    await flushPromises()
    // status is still null here -- the failed flag is the only signal.
    expect(poll.status.value).toBe(null)
    expect(poll.failed.value).toBe(true)

    await tick(2000)
    expect(getSessionIngestion).toHaveBeenCalledTimes(2)
    await tick(4000)
    expect(getSessionIngestion).toHaveBeenCalledTimes(3)

    getSessionIngestion.mockResolvedValue(ready())
    await tick(8000)
    expect(poll.failed.value).toBe(false)
    expect(poll.status.value).toBe('ready')
    poll.stop()
  })

  // A 404 means the session is unknown or not ours: it will 404 forever, so
  // retrying forever at the 15s cap only keeps "References unavailable" on a
  // page that has no references.
  it('stops the loop on a 4xx and leaves failed false', async () => {
    getSessionIngestion.mockRejectedValue(Object.assign(new Error('nope'), { status: 404 }))
    const poll = useReferencePoll('s1')
    await flushPromises()
    expect(getSessionIngestion).toHaveBeenCalledTimes(1)
    expect(poll.failed.value).toBe(false)
    expect(poll.status.value).toBe(null)
    await tick(60000)
    expect(getSessionIngestion).toHaveBeenCalledTimes(1)
    poll.stop()
  })

  it('settles a pending watcher as unavailable on a 4xx', async () => {
    const err = Object.assign(new Error('gone'), { status: 403 })
    getSessionIngestion.mockResolvedValueOnce(pending())
    const poll = useReferencePoll('s1')
    await flushPromises()
    getSessionIngestion.mockRejectedValue(err)
    const outcome = poll.watch(1, 'a.pdf')
    await flushPromises()
    await expect(outcome).resolves.toEqual({ unavailable: true, error: err })
    expect(poll.failed.value).toBe(false)
    poll.stop()
  })

  it('keeps retrying with backoff on a 5xx', async () => {
    getSessionIngestion.mockRejectedValue(Object.assign(new Error('boom'), { status: 503 }))
    const poll = useReferencePoll('s1')
    await flushPromises()
    expect(poll.failed.value).toBe(true)
    await tick(2000)
    expect(getSessionIngestion).toHaveBeenCalledTimes(2)
    await tick(4000)
    expect(getSessionIngestion).toHaveBeenCalledTimes(3)
    poll.stop()
  })

  it('keeps retrying when the error carries no status (network failure)', async () => {
    getSessionIngestion.mockRejectedValue(new TypeError('Failed to fetch'))
    const poll = useReferencePoll('s1')
    await flushPromises()
    expect(poll.failed.value).toBe(true)
    await tick(2000)
    expect(getSessionIngestion).toHaveBeenCalledTimes(2)
    await tick(4000)
    expect(getSessionIngestion).toHaveBeenCalledTimes(3)
    poll.stop()
  })

  it('keeps retrying on an explicit status 0', async () => {
    getSessionIngestion.mockRejectedValue(Object.assign(new Error('offline'), { status: 0 }))
    const poll = useReferencePoll('s1')
    await flushPromises()
    expect(poll.failed.value).toBe(true)
    await tick(2000)
    expect(getSessionIngestion).toHaveBeenCalledTimes(2)
    poll.stop()
  })

  it('keeps the last known document list when a poll throws', async () => {
    getSessionIngestion.mockResolvedValueOnce(pending())
    getSessionIngestion.mockRejectedValue(new Error('offline'))
    const poll = useReferencePoll('s1')
    await flushPromises()
    await tick(2000)
    expect(poll.failed.value).toBe(true)
    // Delete buttons stay reachable: the documents survive the outage.
    expect(poll.documents.value).toHaveLength(1)
    expect(poll.status.value).toBe('pending')
    poll.stop()
  })

  it('retry() polls immediately and restarts the backoff', async () => {
    getSessionIngestion.mockRejectedValue(new Error('offline'))
    const poll = useReferencePoll('s1')
    await flushPromises()
    getSessionIngestion.mockResolvedValue(pending())
    poll.retry()
    await flushPromises()
    expect(getSessionIngestion).toHaveBeenCalledTimes(2)
    expect(poll.failed.value).toBe(false)
    await tick(2000)
    expect(getSessionIngestion).toHaveBeenCalledTimes(3)
    poll.stop()
  })

  describe('watch(documentId, filename)', () => {
    it('resolves ready when the document reaches ready', async () => {
      getSessionIngestion.mockResolvedValueOnce(pending())
      const poll = useReferencePoll('s1')
      await flushPromises()
      getSessionIngestion.mockResolvedValue(ready())
      const outcome = poll.watch(1, 'a.pdf')
      await flushPromises()
      await expect(outcome).resolves.toEqual({ status: 'ready' })
      poll.stop()
    })

    it('resolves failed with the ingestion error', async () => {
      getSessionIngestion.mockResolvedValue({
        status: 'failed',
        documents: [{ id: 1, filename: 'a.pdf', status: 'failed', error: 'bad pdf' }],
      })
      const poll = useReferencePoll('s1')
      await flushPromises()
      const outcome = poll.watch(1, 'a.pdf')
      await flushPromises()
      await expect(outcome).resolves.toEqual({ status: 'failed', error: 'bad pdf' })
      poll.stop()
    })

    it('resolves unavailable immediately when a poll throws', async () => {
      const err = new Error('offline')
      getSessionIngestion.mockRejectedValue(err)
      const poll = useReferencePoll('s1')
      await flushPromises()
      const outcome = poll.watch(1, 'a.pdf')
      await flushPromises()
      await expect(outcome).resolves.toEqual({ unavailable: true, error: err })
      poll.stop()
    })

    it('resolves timedOut at the 90s ceiling, not a backoff step past it', async () => {
      getSessionIngestion.mockResolvedValue(pending())
      const poll = useReferencePoll('s1')
      await flushPromises()
      const outcome = poll.watch(1, 'a.pdf')
      let settled = null
      outcome.then((o) => {
        settled = o
      })
      await flushPromises()

      await tick(WATCH_CEILING_MS - 1)
      expect(settled).toBe(null)
      await tick(1)
      expect(settled).toEqual({ timedOut: true })
      poll.stop()
    })

    it('resolves cancelled when the poller is stopped', async () => {
      getSessionIngestion.mockResolvedValue(pending())
      const poll = useReferencePoll('s1')
      await flushPromises()
      const outcome = poll.watch(1, 'a.pdf')
      await flushPromises()
      poll.stop()
      await expect(outcome).resolves.toEqual({ cancelled: true })
    })

    it('stops the loop after the watcher settles and nothing is pending', async () => {
      getSessionIngestion.mockResolvedValue(ready())
      const poll = useReferencePoll('s1')
      await flushPromises()
      await poll.watch(1, 'a.pdf')
      const calls = getSessionIngestion.mock.calls.length
      await tick(60000)
      expect(getSessionIngestion).toHaveBeenCalledTimes(calls)
      poll.stop()
    })

    // The session-switch reset only runs through the watcher the composable
    // registers when it has a component instance, so exercise it mounted.
    describe('inside a component, on a session switch', () => {
      const Host = defineComponent({
        props: { id: { type: String, required: true } },
        setup(props) {
          const poll = useReferencePoll(() => props.id)

          return { poll }
        },
        render: () => h('div'),
      })

      it('cancels the watcher, polls the new id, and ignores the late old response', async () => {
        let resolveFirst
        getSessionIngestion.mockImplementationOnce(
          () =>
            new Promise((res) => {
              resolveFirst = res
            }),
        )
        const wrapper = mount(Host, { props: { id: 's1' } })
        const poll = wrapper.vm.poll
        await flushPromises()
        const outcome = poll.watch(1, 'a.pdf')

        getSessionIngestion.mockResolvedValue(ready())
        await wrapper.setProps({ id: 's2' })
        await flushPromises()

        await expect(outcome).resolves.toEqual({ cancelled: true })
        expect(getSessionIngestion).toHaveBeenLastCalledWith('s2', {
          fresh: true,
          silent: true,
        })

        // s1's poll resolves after the switch; it must not paint s1's state.
        resolveFirst({
          status: 'failed',
          documents: [{ id: 9, filename: 'stale.pdf', status: 'failed' }],
        })
        await flushPromises()
        expect(poll.status.value).toBe('ready')
        expect(poll.documents.value.map((d) => d.id)).toEqual([1])
        wrapper.unmount()
      })

      it('stops polling on unmount', async () => {
        getSessionIngestion.mockResolvedValue(pending())
        const wrapper = mount(Host, { props: { id: 's1' } })
        await flushPromises()
        wrapper.unmount()
        const calls = getSessionIngestion.mock.calls.length
        await tick(60000)
        expect(getSessionIngestion).toHaveBeenCalledTimes(calls)
      })
    })

    it('stop() prevents any further polling', async () => {
      getSessionIngestion.mockResolvedValue(pending())
      const poll = useReferencePoll('s1')
      await flushPromises()
      poll.stop()
      const calls = getSessionIngestion.mock.calls.length
      await tick(60000)
      expect(getSessionIngestion).toHaveBeenCalledTimes(calls)
    })
  })
})
