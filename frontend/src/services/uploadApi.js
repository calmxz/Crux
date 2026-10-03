import {
  ApiError,
  apiGet,
  apiDelete,
  getFreshAccessToken,
  _refreshAccessToken,
  _onAuthExpired,
  invalidateGetCache,
} from './apiClient.js'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

// F-12: uploads get the same timeout discipline as request() (F-06) but a
// longer budget - multipart PDF bodies legitimately exceed 30 s.
const UPLOAD_TIMEOUT_MS = 120000

// Mirror of the backend cap (backend/routes/upload.py MAX_UPLOAD_BYTES). This is
// a client-side pre-check for instant feedback only; the backend remains the
// authoritative limit and still returns 413 FILE_TOO_LARGE if bypassed.
export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024 // 25 MB

export const ACCEPTED_EXTENSIONS = ['.pdf', '.pptx', '.txt', '.md', '.markdown']

// File-picker hint. `.markdown` is accepted by validateFile but omitted here so
// the picker advertises the common four; derived from ACCEPTED_EXTENSIONS so the
// two cannot silently drift when a type is added.
export const ACCEPT_ATTR = ACCEPTED_EXTENSIONS.filter((ext) => ext !== '.markdown').join(',')

// Client-side pre-check only; the backend re-validates by extension and size.
export function validateFile(file) {
  const name = (file?.name || '').toLowerCase()

  if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return {
      ok: false,
      reason: `${file?.name || 'File'} is not a supported type. Use PDF, PPTX, TXT, or MD.`,
    }
  }

  if (file.size > MAX_UPLOAD_BYTES) {
    const maxMb = Math.round(MAX_UPLOAD_BYTES / (1024 * 1024))

    return { ok: false, reason: `${file.name} is too large (max ${maxMb} MB).` }
  }

  return { ok: true }
}

async function _authHeaders() {
  const token = await getFreshAccessToken()

  return token ? { authorization: `Bearer ${token}` } : {}
}

async function _postUpload(fd, headers) {
  return fetch(`${BASE_URL}/upload`, {
    method: 'POST',
    body: fd,
    headers,
    signal:
      typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function'
        ? AbortSignal.timeout(UPLOAD_TIMEOUT_MS)
        : undefined,
  })
}

export async function uploadDocument({ sessionId, file }) {
  const fd = new FormData()
  fd.append('session_id', sessionId)
  fd.append('file', file)

  let resp
  let retried = false

  try {
    resp = await _postUpload(fd, await _authHeaders())

    if (resp.status === 401) {
      // F-12: one silent refresh-retry, same policy as request() (F-09).
      retried = true
      const token = await _refreshAccessToken()
      resp = await _postUpload(fd, token ? { authorization: `Bearer ${token}` } : {})
    }
  } catch (e) {
    invalidateGetCache(`/sessions/${sessionId}`)
    const detail = e?.name === 'TimeoutError' ? 'upload timed out' : e.message
    throw new ApiError(0, { detail }, '/upload')
  }

  // Raw multipart fetch bypasses request(): drop the session tree (ingestion
  // status lives on the session body) from the GET cache whatever the status.
  invalidateGetCache(`/sessions/${sessionId}`)

  const text = await resp.text()
  let parsed = null

  try {
    parsed = text ? JSON.parse(text) : null
  } catch {
    /* leave parsed null */
  }

  if (!resp.ok) {
    // F-12: still-401 after the retry means the session is dead; sign out and
    // redirect to login rather than leave the app looking signed in (F-09).
    if (resp.status === 401 && retried) await _onAuthExpired()
    throw new ApiError(resp.status, parsed ?? text, '/upload')
  }

  return parsed
}

/** @deprecated Back-compat alias for existing PDF-only call sites; use uploadDocument. */
export const uploadPdf = uploadDocument

export const getUploadStatus = (documentId) => apiGet(`/upload/${documentId}`)

// opts is forwarded to request(): useReferencePoll passes { silent: true } (the
// banner's "References unavailable" row is the sole error surface, so errorBus
// must not also toast every failed poll) and { fresh: true } to bypass the
// F-18 GET cache, which would otherwise hand a poll its own last response back.
export const getSessionIngestion = (sessionId, opts = {}) =>
  apiGet(`/sessions/${sessionId}/ingestion`, undefined, opts)

// silent: true — the banner's delete handler is the sole error surface. Without
// it, request()/errorBus would auto-toast non-404 failures AND the component's
// catch would toast again (double toast).
export const deleteDocument = (documentId) =>
  apiDelete(`/documents/${documentId}`, { silent: true })
