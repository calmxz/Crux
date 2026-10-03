const DATE_FMT = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  timeZoneName: 'short',
})

export const formatDate = (iso) => (iso ? DATE_FMT.format(new Date(iso)) : '')

const SHORT_FMT = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'short',
  timeStyle: 'short',
})

export const formatShortDateTime = (iso) => (iso ? SHORT_FMT.format(new Date(iso)) : '')

// Cap banners and cap toasts both say "Resets at <x>." and both fall back to
// the UTC rollover when the server sent no timestamp.
export const formatResetTime = (iso) => formatShortDateTime(iso) || 'midnight UTC'

const TIME_FMT = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' })

// A turn's head line carries the time only when the server sent one.
export const formatTime = (iso) => (iso ? TIME_FMT.format(new Date(iso)) : '')

const RTF = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })

const STEPS = [
  { limit: 60, divisor: 1, unit: 'second' },
  { limit: 3600, divisor: 60, unit: 'minute' },
  { limit: 86400, divisor: 3600, unit: 'hour' },
  { limit: 604800, divisor: 86400, unit: 'day' },
  { limit: 2629800, divisor: 604800, unit: 'week' },
  { limit: 31557600, divisor: 2629800, unit: 'month' },
  { limit: Infinity, divisor: 31557600, unit: 'year' },
]

export const formatRelative = (iso) => {
  if (!iso) return ''
  const diffSec = (new Date(iso).getTime() - Date.now()) / 1000
  const absSec = Math.abs(diffSec)

  for (const { limit, divisor, unit } of STEPS) {
    if (absSec < limit) {
      return RTF.format(Math.round(diffSec / divisor), unit)
    }
  }

  return RTF.format(Math.round(diffSec / 31557600), 'year')
}
