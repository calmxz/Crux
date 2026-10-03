// The tutor preferences in one place (#381): for each interactionPreferences
// key, its /api/me field, the fallback used before the server answers, and
// the choices offered. Fallbacks mirror the MeResponse defaults and option
// values mirror the enums in docs/api/openapi.yaml; tutorPreferences.test.js
// reads the contract so the two cannot drift. A new tutor preference is an
// entry here plus its control (title, test ids) in settings/LearningTab.vue.
export const TUTOR_PREFERENCES = {
  feedback: {
    field: 'feedback_pref',
    fallback: 'hints',
    options: [
      { value: 'hints', label: 'Hints', sub: 'Nudge me toward the answer.' },
      { value: 'direct_answers', label: 'Direct answers', sub: 'Explain outright when I ask.' },
    ],
  },
  checkIns: {
    field: 'check_ins',
    fallback: 'sometimes',
    options: [
      { value: 'often', label: 'Often' },
      { value: 'sometimes', label: 'Sometimes' },
      { value: 'only_when_asked', label: 'Only when I ask' },
    ],
  },
  replyLength: {
    field: 'reply_length',
    fallback: 'balanced',
    options: [
      { value: 'brief', label: 'Brief' },
      { value: 'balanced', label: 'Balanced' },
      { value: 'thorough', label: 'Thorough' },
    ],
  },
}

// The learner's choice for `key`, or the fallback when none is stored yet.
export function preferenceValue(prefs, key) {
  return prefs?.[key] || TUTOR_PREFERENCES[key].fallback
}
