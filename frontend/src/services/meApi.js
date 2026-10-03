import { apiDelete, apiGet } from './apiClient.js'

// R2-54/55/56: DELETE /api/me removes every row, the uploaded files, and the
// Supabase auth user itself, in that order. silent: true -- AccountView's
// delete dialog is the sole error surface (an inline error line), so the
// generic errorBus toast must not also fire.
export const deleteAccount = () => apiDelete('/me', { silent: true })

// #361: GET /api/me/export returns the learner's whole account as one JSON
// document. fresh: true -- the 5s GET cache must never hand back an export
// taken before the learner's latest message. silent for the same reason as
// deleteAccount: AccountView shows the error inline.
export const exportData = () => apiGet('/me/export', null, { silent: true, fresh: true })
