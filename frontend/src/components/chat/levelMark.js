// The level mark: one stroke glyph drawn at five stepped weights.
// KnowledgeLevel (docs/api/openapi.yaml) carries three values, so the scale
// reads: unset hairline, then three inked steps with one step of headroom
// below the top so "advanced" sits at the top of the scale.
export const LEVEL_STEPS = [0.75, 1.5, 2.25, 3, 3.75]

const LEVEL_STEP_INDEX = { beginner: 1, intermediate: 2, advanced: 4 }

export const LEVEL_MARK_PATH = 'M2 17 L22 7'

// The drawn tick (mastered, saved, selected), on a 12x12 viewBox.
export const TICK_PATH = 'M2 6.5 L4.8 9.2 L10 3.2'

export function levelStroke(level) {
  return LEVEL_STEPS[LEVEL_STEP_INDEX[level] ?? 0]
}
