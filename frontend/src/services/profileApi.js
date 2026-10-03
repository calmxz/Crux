import { apiDelete, apiGet, apiPatch } from './apiClient.js'

// Paths are relative to VITE_API_BASE_URL which already includes the /api
// prefix. user_id is resolved from the Authorization header server-side.
// fresh: true -- the response carries the etag that patchProfile/
// deleteProfileItem send back as If-Match. Our own writes invalidate the F-18
// GET cache by path prefix, but the tutor agent writes this profile server-side
// during a turn (update_topic_profile); a cached read taken within the 5s TTL
// of a pre-turn read would hand the next write a stale etag and 412 it.
export const getSessionProfile = (sessionId) =>
  apiGet(`/profile/${sessionId}`, undefined, { fresh: true })

// Cross-session aggregate dashboard (AggregateProfileResponse). This does
// carry tutor-written data -- recent_topics[].progress comes from each
// session's topic_profile_json -- but its reader (the /profile page, #358)
// is a read-only overview, not a write path like getSessionProfile above, so the plain
// short GET cache is acceptable here: it needs neither `fresh` nor an etag
// round-trip.
export const getAggregateProfile = () => apiGet('/profile/aggregate')

export const getUsageSummary = () => apiGet('/usage/summary')

// Both write calls send If-Match so the server can enforce optimistic
// concurrency against the profile's current etag. Callers must pass the
// etag from the most recent GET (or the previous write's response).
//
// silent: true -- ProfileView's own write handler (_applyWrite) is the sole
// error surface (conflict notice on 412, inline banner otherwise). Without
// it, request()/errorBus would auto-toast every non-2xx AND the component
// would show its own message (double signal).
export const patchProfile = (sessionId, body, etag) =>
  apiPatch(`/profile/${sessionId}`, body, { headers: { 'If-Match': etag }, silent: true })

export const deleteProfileItem = (sessionId, listName, item, etag) =>
  apiDelete(`/profile/${sessionId}/${listName}/${encodeURIComponent(item)}`, {
    headers: { 'If-Match': etag },
    silent: true,
  })
