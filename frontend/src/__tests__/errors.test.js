import { describe, it, expect } from 'vitest'
import {
  friendlyError,
  sseErrorCopy,
  StreamAbortedError,
  GENERIC_STREAM_ERROR_COPY,
  SESSION_ENDED_COPY,
} from '../lib/errors'

describe('friendlyError', () => {
  const coded = (status, code) => ({ status, body: { detail: { code } } })

  it('distinguishes nginx throttle 429 from daily-cap 429', () => {
    expect(friendlyError(coded(429, 'daily_cap_reached'))).toMatch(/daily limit/i)
    expect(friendlyError({ status: 429, body: '<html>429</html>' })).toMatch(/wait a moment/i)
  })

  it('maps daily_cost_cap_reached to the daily-limit copy', () => {
    expect(friendlyError(coded(429, 'daily_cost_cap_reached'))).toMatch(/daily limit/i)
  })

  it('maps global_cost_cap_reached to service-budget copy, not per-user copy', () => {
    const msg = friendlyError(coded(429, 'global_cost_cap_reached'))
    expect(msg).toMatch(/service has reached its daily budget/i)
    expect(msg).not.toMatch(/you've hit/i)
  })

  it('maps too_many_requests to the wait-and-retry copy', () => {
    expect(friendlyError(coded(429, 'too_many_requests'))).toMatch(/wait a moment/i)
  })

  it('maps chunk_limit_exceeded (413) to the split-the-document copy', () => {
    expect(friendlyError(coded(413, 'chunk_limit_exceeded'))).toMatch(/too large to ingest/i)
  })

  it('maps page_limit_exceeded (413) to the too-many-pages copy', () => {
    expect(friendlyError(coded(413, 'page_limit_exceeded'))).toMatch(/too many pages to ingest/i)
  })

  it('falls back to the status copy for an unknown code', () => {
    expect(friendlyError(coded(429, 'something_new'))).toMatch(/daily limit/i)
    expect(friendlyError(coded(400, 'something_new'))).toMatch(/rejected/i)
  })

  // #330: five backend codes that previously fell through to the generic
  // status copy ("That request was rejected...") now have their own sentence.
  it('maps empty_message (422) to the type-a-message copy', () => {
    expect(friendlyError(coded(422, 'empty_message'))).toMatch(/type a message before sending/i)
  })

  it('maps empty_topic (422) to the enter-a-topic copy', () => {
    expect(friendlyError(coded(422, 'empty_topic'))).toMatch(/enter a topic/i)
  })

  it('maps body_too_large (413) to the shorten-it copy', () => {
    expect(friendlyError(coded(413, 'body_too_large'))).toMatch(/too much text to send at once/i)
  })

  it('maps session_ended (409) to the shared ended-elsewhere copy', () => {
    expect(friendlyError(coded(409, 'session_ended'))).toBe(SESSION_ENDED_COPY)
  })

  it('maps tool_failed to the could-not-finish-that-step copy', () => {
    expect(friendlyError(coded(500, 'tool_failed'))).toMatch(/could not finish that step/i)
  })
})

// E-04: both SSE stream loops used to render `data.message || data.code`, so a
// bare code string ("tool_failed") could reach the error banner verbatim.
describe('sseErrorCopy', () => {
  it('prefers the coded copy over the backend message', () => {
    expect(sseErrorCopy({ code: 'tool_failed', message: 'dispatch blew up' })).toMatch(
      /could not finish that step/i,
    )
  })

  it('maps every #330 code to its own sentence, never the raw code', () => {
    for (const code of [
      'empty_message',
      'empty_topic',
      'body_too_large',
      'session_ended',
      'tool_failed',
    ]) {
      const copy = sseErrorCopy({ code })
      expect(copy).not.toBe(code)
      expect(copy).not.toBe(GENERIC_STREAM_ERROR_COPY)
    }
  })

  it('falls back to the backend message for an unknown code', () => {
    expect(sseErrorCopy({ code: 'brand_new', message: 'something specific' })).toBe(
      'something specific',
    )
  })

  it('falls back to the generic sentence with no code and no message', () => {
    expect(sseErrorCopy({})).toBe(GENERIC_STREAM_ERROR_COPY)
    expect(sseErrorCopy({ code: 'brand_new' })).toBe(GENERIC_STREAM_ERROR_COPY)
    expect(sseErrorCopy({ code: 'brand_new', message: '' })).toBe(GENERIC_STREAM_ERROR_COPY)
    expect(sseErrorCopy(null)).toBe(GENERIC_STREAM_ERROR_COPY)
    expect(sseErrorCopy(undefined)).toBe(GENERIC_STREAM_ERROR_COPY)
  })
})

describe('StreamAbortedError', () => {
  it('carries reason and cause', () => {
    const cause = Object.assign(new Error('API 401'), { status: 401 })
    const e = new StreamAbortedError('auth_expired', cause)
    expect(e).toBeInstanceOf(Error)
    expect(e.name).toBe('StreamAbortedError')
    expect(e.reason).toBe('auth_expired')
    expect(e.cause).toBe(cause)
  })
})
