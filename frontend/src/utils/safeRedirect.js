// F-49: only follow same-origin relative paths; anything else (protocol-
// relative //host, absolute URLs) is an open-redirect vector.
export function safeRedirect(raw) {
  if (typeof raw !== 'string') return null

  if (!raw.startsWith('/') || raw.startsWith('//')) return null

  return raw
}
