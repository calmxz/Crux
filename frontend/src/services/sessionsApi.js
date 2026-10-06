import { apiGet, apiPost, apiPatch } from './apiClient.js'

// Paths are relative to VITE_API_BASE_URL which already includes the /api
// prefix. user_id is no longer carried in any payload — the backend resolves
// it from the Authorization: Bearer <jwt> header.
export const createSession = ({ topic, seedMode, priorSessionId, declaredLevel }) =>
  apiPost('/sessions', {
    topic,
    seed_mode: seedMode,
    prior_session_id: priorSessionId ?? null,
    declared_level: declaredLevel ?? null,
  })

// Start-page prior-topic intercept lookup; silent since a failed lookup must
// never block session creation or surface an error toast.
export const lookupTopic = (topic) => apiGet('/sessions/lookup', { topic }, { silent: true })

// U-05: silenced unconditionally here, not via a per-caller opts flag --
// every current caller fires this fire-and-forget from onMounted, and the
// store's in-flight de-dupe (session.js:listSessions) could otherwise drop
// the flag if a different caller's non-silent call wins the race.
// F-06: the route is bounded (limit default 100, max 200). params is
// optional: { limit?: number, offset?: number }. Callers that pass nothing
// keep the previous URL exactly (apiClient drops undefined/null params).
export const listSessions = (params) => apiGet('/sessions', params, { silent: true })

// H1: default the contract array key so a malformed/partial {} or null
// response from the backend can't throw in render (e.g. `items.length`)
// inside SessionsLibraryView.
const normalizeSessionLibraryPage = (res) => ({
  ...res,
  items: res?.items ?? [],
})

// params: { status?: 'all'|'active'|'ended', q?: string,
//           sort?: 'last_activity'|'created'|'topic'|'pinned_activity', limit?: number, offset?: number }
export const getSessionLibrary = (params, opts) =>
  apiGet('/sessions/library', params, opts).then(normalizeSessionLibraryPage)

// fresh: the session body carries ingestion_status, pending_check and the
// topic profile, all of which change server-side during a turn or an upload
// (raw-fetch writers). Never serve it from the short GET cache.
export const getSession = (sessionId) =>
  apiGet(`/sessions/${sessionId}`, undefined, { fresh: true })

// P3: SessionView shows its own inline error/loading for the "load earlier"
// button; silent stops the errorBus double-toast (same opt-out pattern as
// skipCheck/answerCheck below).
export const getSessionMessages = (sessionId, params = {}) =>
  apiGet(`/sessions/${sessionId}/messages`, params, { silent: true })

export const endSession = (sessionId) => apiPost(`/sessions/${sessionId}/end`, {})

export const reopenSession = (sessionId) => apiPost(`/sessions/${sessionId}/reopen`, {})

export const renameSession = (sessionId, topic) => apiPatch(`/sessions/${sessionId}`, { topic })

export const setPinned = (sessionId, pinned) => apiPatch(`/sessions/${sessionId}`, { pinned })

// F-20: SessionView banners these failures itself (lastError); silent stops
// the errorBus double-toast - same opt-out pattern as profileApi.
export const skipCheck = (sessionId, index) =>
  apiPost(`/sessions/${sessionId}/check/skip`, { index }, { silent: true })

export const answerCheck = (sessionId, index, selectedIndex) =>
  apiPost(
    `/sessions/${sessionId}/check/answer`,
    {
      index,
      selected_index: selectedIndex,
    },
    { silent: true },
  )
