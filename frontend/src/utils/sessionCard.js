import { formatRelative } from '@/utils/formatDate.js'

const AUTO_RE = /^\[auto\]\s*/

export function stripAutoPrefix(s) {
  return (s || '').replace(AUTO_RE, '')
}

// Secondary meta line: "<n> messages · last active <rel>".
export function cardMeta(session) {
  const count = session.message_count || 0
  const noun = count === 1 ? 'message' : 'messages'
  const ts = session.last_activity_at || session.created_at
  const left = `${count} ${noun}`

  return ts ? `${left} · last active ${formatRelative(ts)}` : left
}

const DISPLAY_MATH_RE = /\$\$[\s\S]*?\$\$/g

const INLINE_MATH_RE = /\$[^$\n]+?\$/g

const SHORT_PREVIEW = 12

// Line-start block markers. Run before the inline passes so a bullet's "* "
// is never mistaken for an emphasis opener.
const MD_HEADING_RE = /^[ \t]*#{1,6}[ \t]+/gm

const MD_QUOTE_RE = /^[ \t]*>[ \t]?/gm

const MD_BULLET_RE = /^[ \t]*[-*+][ \t]+/gm

const MD_ORDERED_RE = /^[ \t]*\d+\.[ \t]+/gm

// Images before links, or "![alt](url)" would leave a stray "!".
const MD_IMAGE_RE = /!\[([^\]]*)\]\([^)]*\)/g

const MD_LINK_RE = /\[([^\]]*)\]\([^)]*\)/g

const MD_CODE_RE = /`([^`\n]+)`/g

const MD_STRIKE_RE = /~~([^~\n]+?)~~/g

// Double markers before single ones, or "**x**" would only lose one pair.
// The underscore forms require a word boundary on both sides so "snake_case"
// survives untouched.
const MD_BOLD_STAR_RE = /\*\*([^*\n]+?)\*\*/g

const MD_BOLD_UNDER_RE = /(^|[^\w])__([^_\n]+?)__(?=[^\w]|$)/g

// The single-marker forms also require the marker to hug its text, so prose
// arithmetic ("5 * 3 and 2 * 4") keeps its asterisks.
const MD_ITALIC_STAR_RE = /\*(\S(?:[^*\n]*?\S)?)\*/g

const MD_ITALIC_UNDER_RE = /(^|[^\w])_(\S(?:[^_\n]*?\S)?)_(?=[^\w]|$)/g

// Strips LaTeX source (display and inline math) down to a placeholder and then
// strips inline markdown syntax down to its text, so card previews never show
// raw formula or markup characters.
export function cleanPreview(text) {
  return (text || '')
    .replace(DISPLAY_MATH_RE, '[formula]')
    .replace(INLINE_MATH_RE, '[formula]')
    .replace(MD_HEADING_RE, '')
    .replace(MD_QUOTE_RE, '')
    .replace(MD_BULLET_RE, '')
    .replace(MD_ORDERED_RE, '')
    .replace(MD_IMAGE_RE, '$1')
    .replace(MD_LINK_RE, '$1')
    .replace(MD_CODE_RE, '$1')
    .replace(MD_STRIKE_RE, '$1')
    .replace(MD_BOLD_STAR_RE, '$1')
    .replace(MD_BOLD_UNDER_RE, '$1$2')
    .replace(MD_ITALIC_STAR_RE, '$1')
    .replace(MD_ITALIC_UNDER_RE, '$1$2')
    .replace(/\s+/g, ' ')
    .trim()
}

// Narrative line for home/library cards. Ended: summary (auto-stripped) -> 'Completed'.
// Active: cleaned preview, falling back to the summary when the preview is too
// short to be useful (e.g. a one-word reply). Structured signals (focus/mastered)
// never appear here — they are chips.
export function cardStory(session) {
  if (session.ended_at) {
    return stripAutoPrefix(session.last_session_summary) || 'Completed'
  }

  const preview = cleanPreview(session.last_message_preview)
  const summary = stripAutoPrefix(session.last_session_summary)

  if (preview.length < SHORT_PREVIEW && summary) return summary

  return preview
}

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

// Structured signals for chip rendering on both surfaces. Focus, then level,
// then mastered. Chip appears only when its signal is meaningful (focus set /
// level set / mastered > 0).
export function cardChips(session) {
  const chips = []
  const progress = session.progress

  if (progress && progress.focus_target_gap) {
    chips.push({ type: 'focus', label: progress.focus_target_gap })
  }

  if (progress && progress.level) {
    chips.push({ type: 'level', label: capitalize(progress.level), level: progress.level })
  }

  const mastered = (progress && progress.mastered_count) || 0

  if (mastered > 0) {
    chips.push({ type: 'mastered', label: `${mastered} mastered`, count: mastered })
  }

  return chips
}
