// Maps a backend cap-error envelope to the session store's cap-banner state.
// One mapper for BOTH transports so they cannot drift (choke-point pattern,
// same rationale as backend/agent/excerpt.py::wrap_chunk):
//   - pre-stream HTTP 429: ApiError.body.detail from routes/chat.py
//   - mid-turn SSE `error` event payload from agent/tutor.py (same flat
//     shape, but no resets_at -- consumers must tolerate null)
import {
  ERR_DAILY_CAP_REACHED,
  ERR_DAILY_COST_CAP_REACHED,
  ERR_GLOBAL_COST_CAP_REACHED,
} from './errorCodes.js'

export function mapCapError(detail) {
  const d = detail && typeof detail === 'object' ? detail : {}

  if (d.code === ERR_DAILY_CAP_REACHED) {
    return {
      kind: 'daily',
      info: { cap: d.cap ?? null, used: d.used ?? null, resets_at: d.resets_at ?? null },
    }
  }

  if (d.code === ERR_DAILY_COST_CAP_REACHED || d.code === ERR_GLOBAL_COST_CAP_REACHED) {
    // Global (service-wide budget) envelope has no per-user spend fields,
    // so those come through as null via the ?? fallback below.
    return {
      kind: 'cost',
      info: {
        used_usd: d.used_usd ?? null,
        soft_cap_usd: d.soft_cap_usd ?? null,
        hard_cap_usd: d.hard_cap_usd ?? null,
        resets_at: d.resets_at ?? null,
        scope: d.code === ERR_GLOBAL_COST_CAP_REACHED ? 'global' : 'user',
      },
    }
  }

  return { kind: null, info: null }
}
