// frontend/src/__tests__/sseParser.test.js
import { describe, it, expect } from 'vitest'
import { parseSSEStream } from '../lib/sseParser.js'

function readableFromChunks(chunks) {
  const encoder = new TextEncoder()
  let i = 0

  return new ReadableStream({
    pull(controller) {
      if (i >= chunks.length) {
        controller.close()

        return
      }

      controller.enqueue(encoder.encode(chunks[i++]))
    },
  })
}

describe('parseSSEStream', () => {
  it('parses a single complete event', async () => {
    const stream = readableFromChunks(['event: foo\ndata: {"x":1}\n\n'])
    const events = []
    await parseSSEStream(stream, (ev) => events.push(ev))
    expect(events).toEqual([{ event: 'foo', data: { x: 1 } }])
  })

  it('parses multiple events in one chunk', async () => {
    const stream = readableFromChunks(['event: a\ndata: 1\n\nevent: b\ndata: 2\n\n'])
    const events = []
    await parseSSEStream(stream, (ev) => events.push(ev))
    expect(events).toEqual([
      { event: 'a', data: 1 },
      { event: 'b', data: 2 },
    ])
  })

  it('parses an event split across multiple chunks', async () => {
    const stream = readableFromChunks(['event: a\nda', 'ta: 1\n\n'])
    const events = []
    await parseSSEStream(stream, (ev) => events.push(ev))
    expect(events).toEqual([{ event: 'a', data: 1 }])
  })

  it('parses non-JSON data as a string', async () => {
    const stream = readableFromChunks(['event: hello\ndata: world\n\n'])
    const events = []
    await parseSSEStream(stream, (ev) => events.push(ev))
    expect(events).toEqual([{ event: 'hello', data: 'world' }])
  })

  it('handles multi-line data fields (joined by newline)', async () => {
    const stream = readableFromChunks(['event: m\ndata: line1\ndata: line2\n\n'])
    const events = []
    await parseSSEStream(stream, (ev) => events.push(ev))
    expect(events).toEqual([{ event: 'm', data: 'line1\nline2' }])
  })

  it('handles trailing whitespace and bare events', async () => {
    const stream = readableFromChunks([':comment\nevent: a\ndata: 1\n\n'])
    const events = []
    await parseSSEStream(stream, (ev) => events.push(ev))
    expect(events).toEqual([{ event: 'a', data: 1 }])
  })

  it('aborts cleanly via AbortSignal', async () => {
    const ctrl = new AbortController()

    const stream = new ReadableStream({
      pull() {
        /* never resolves */
      },
    })

    const promise = parseSSEStream(stream, () => {}, { signal: ctrl.signal })
    ctrl.abort()
    await expect(promise).rejects.toThrow(/abort/i)
  })
})
