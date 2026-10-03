import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import {
  uploadPdf,
  uploadDocument,
  getUploadStatus,
  validateFile,
  ACCEPT_ATTR,
  MAX_UPLOAD_BYTES,
  deleteDocument,
} from '@/services/uploadApi.js'
import { ApiError, setUnauthorizedHandler } from '@/services/apiClient.js'

function fakeFile(name, size) {
  return { name, size }
}

describe('validateFile', () => {
  it('accepts pdf, pptx, txt, md by extension', () => {
    for (const ext of ['ref.pdf', 'deck.PPTX', 'notes.txt', 'readme.md', 'readme.markdown']) {
      expect(validateFile(fakeFile(ext, 1000)).ok).toBe(true)
    }
  })

  it('rejects unsupported extensions', () => {
    const r = validateFile(fakeFile('paper.docx', 1000))
    expect(r.ok).toBe(false)
    expect(r.reason).toMatch(/supported/i)
  })

  it('rejects oversize files', () => {
    const r = validateFile(fakeFile('big.pdf', MAX_UPLOAD_BYTES + 1))
    expect(r.ok).toBe(false)
    expect(r.reason).toMatch(/too large/i)
  })

  it('exposes an accept attribute string', () => {
    expect(ACCEPT_ATTR).toContain('.pdf')
    expect(ACCEPT_ATTR).toContain('.pptx')
  })
})

describe('uploadApi', () => {
  let fetchMock
  let unauthorizedHandler
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchMock = vi.fn()
    globalThis.fetch = fetchMock
    // F-16: apiClient no longer imports the router directly -- main.js wires
    // the redirect at boot, so tests supply their own handler stub.
    unauthorizedHandler = vi.fn()
    setUnauthorizedHandler(unauthorizedHandler)
  })
  afterEach(() => {
    setUnauthorizedHandler(null)
    vi.restoreAllMocks()
  })

  function ok(body) {
    return Promise.resolve({
      ok: true,
      status: 200,
      text: () => Promise.resolve(JSON.stringify(body)),
    })
  }

  function fail(status, body) {
    return Promise.resolve({
      ok: false,
      status,
      text: () => Promise.resolve(typeof body === 'string' ? body : JSON.stringify(body)),
    })
  }

  it('uploadPdf posts FormData with session_id and file (no user_id)', async () => {
    fetchMock.mockReturnValueOnce(ok({ document_id: 'd1' }))
    const file = new File(['x'], 'a.pdf', { type: 'application/pdf' })
    const out = await uploadPdf({ sessionId: 's1', file })
    expect(out.document_id).toBe('d1')
    const init = fetchMock.mock.calls[0][1]
    expect(init.method).toBe('POST')
    expect(init.body).toBeInstanceOf(FormData)
    // Phase 7: server resolves user_id from the Authorization header.
    expect(init.body.get('user_id')).toBeNull()
    expect(init.body.get('session_id')).toBe('s1')
  })

  it('uploadPdf throws ApiError(0) on network failure', async () => {
    fetchMock.mockRejectedValueOnce(new Error('offline'))
    const err = await uploadPdf({ sessionId: 's', file: new File([''], 'a.pdf') }).catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(0)
  })

  it('uploadPdf throws ApiError with parsed body on non-ok', async () => {
    fetchMock.mockReturnValueOnce(fail(413, { detail: 'too big' }))
    const err = await uploadPdf({ sessionId: 's', file: new File([''], 'a.pdf') }).catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(413)
    expect(err.body.detail).toBe('too big')
  })

  it('uploadPdf returns null body for empty response', async () => {
    fetchMock.mockReturnValueOnce(
      Promise.resolve({ ok: true, status: 204, text: () => Promise.resolve('') }),
    )
    const out = await uploadPdf({ sessionId: 's', file: new File([''], 'a.pdf') })
    expect(out).toBeNull()
  })

  it('uploadPdf returns raw text in body when not JSON', async () => {
    fetchMock.mockReturnValueOnce(fail(500, 'plain text'))
    const err = await uploadPdf({ sessionId: 's', file: new File([''], 'a.pdf') }).catch((e) => e)
    expect(err.body).toBe('plain text')
  })

  it('getUploadStatus hits /upload/:id with no user_id query', async () => {
    fetchMock.mockReturnValueOnce(ok({ status: 'ready' }))
    const out = await getUploadStatus('d1')
    expect(out.status).toBe('ready')
    expect(fetchMock.mock.calls[0][0]).toContain('/upload/d1')
    expect(fetchMock.mock.calls[0][0]).not.toContain('user_id=')
  })

  it('issues DELETE to /documents/{id}', async () => {
    fetchMock.mockResolvedValue(
      Promise.resolve({ ok: true, status: 204, text: () => Promise.resolve('') }),
    )
    await deleteDocument(7)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/documents\/7$/)
    expect(init.method).toBe('DELETE')
  })

  it('throws ApiError on non-ok response', async () => {
    fetchMock.mockResolvedValue(
      Promise.resolve({ ok: false, status: 404, text: () => Promise.resolve('') }),
    )
    await expect(deleteDocument(7)).rejects.toThrow(/404/)
  })

  // F-12: uploadDocument gets the same timeout + 401 refresh-retry discipline
  // as the main request() path (F-06/F-09), which uploadPdf's raw fetch lacked.
  it('passes an abort timeout signal to fetch', async () => {
    fetchMock.mockReturnValueOnce(ok({}))
    await uploadDocument({ sessionId: 's1', file: new File(['x'], 'a.pdf') })
    expect(fetchMock.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal)
  })

  it('retries once with a refreshed token on 401', async () => {
    fetchMock.mockReturnValueOnce(fail(401, {})).mockReturnValueOnce(ok({}))
    await uploadDocument({ sessionId: 's1', file: new File(['x'], 'a.pdf') })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('signs out and calls the unauthorized handler when the retry also gets a 401 (F-12)', async () => {
    fetchMock.mockReturnValueOnce(fail(401, {})).mockReturnValueOnce(fail(401, {}))
    await expect(
      uploadDocument({ sessionId: 's1', file: new File(['x'], 'a.pdf') }),
    ).rejects.toMatchObject({ status: 401 })
    expect(globalThis.__supabaseAuthStub.signOut).toHaveBeenCalled()
    expect(unauthorizedHandler).toHaveBeenCalledTimes(1)
  })

  // F-18 review finding: the multipart POST is a raw fetch, so it must drop the
  // session tree from the short GET cache itself (ingestion_status lives on
  // the session body).
  it('uploadPdf invalidates the cached session GET whether it succeeds or fails', async () => {
    const { apiGet, _resetApiCache } = await import('@/services/apiClient.js')
    _resetApiCache()

    const json = (body, status = 200) =>
      new Response(JSON.stringify(body), {
        status,
        headers: { 'content-type': 'application/json' },
      })

    fetchMock.mockResolvedValueOnce(json({ n: 1 }))
    await apiGet('/sessions/s1')
    fetchMock.mockResolvedValueOnce(json({ document_id: 'd1' }))
    await uploadPdf({ sessionId: 's1', file: new File([''], 'a.pdf') })
    fetchMock.mockResolvedValueOnce(json({ n: 2 }))
    await expect(apiGet('/sessions/s1')).resolves.toEqual({ n: 2 })

    fetchMock.mockRejectedValueOnce(new Error('offline'))
    await expect(
      uploadPdf({ sessionId: 's1', file: new File([''], 'a.pdf') }),
    ).rejects.toBeInstanceOf(ApiError)
    fetchMock.mockResolvedValueOnce(json({ n: 3 }))
    await expect(apiGet('/sessions/s1')).resolves.toEqual({ n: 3 })
  })
})
