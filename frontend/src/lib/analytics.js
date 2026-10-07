// Vercel Web Analytics wiring for App.vue.

// Set at build time in vite.config.js from Vercel's VERCEL=1 system variable.
// Local dev and the Docker/nginx image have no /_vercel/insights endpoint, so
// the component only mounts on Vercel builds.
export const analyticsEnabled = import.meta.env.VITE_VERCEL_ANALYTICS === '1'

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi

// beforeSend hook: strip per-user identifiers before the event leaves the
// browser. Session UUIDs in the path become [id]; query and hash (reset
// tokens, deep-link state) are dropped.
export function scrubAnalyticsEvent(event) {
  const url = new URL(event.url)

  url.search = ''
  url.hash = ''

  return { ...event, url: url.toString().replace(UUID, '[id]') }
}
