export const TOOL_LABELS = {
  retrieve_chunks: {
    running: 'Searching your document…',
    done: 'Search complete',
    error: 'Search failed — continuing',
  },
  update_topic_profile: {
    running: 'Updating profile…',
    done: 'Profile updated',
    error: 'Profile update failed',
  },
  record_learning_event: {
    running: 'Recording answer…',
    done: 'Answer recorded',
    error: 'Recording failed',
  },
  ask_check_questions: {
    running: 'Preparing check questions…',
    done: 'Check questions ready',
    error: 'Could not ask questions',
  },
  suggest_topics: {
    running: 'Picking topics…',
    done: 'Topics ready',
    error: 'Topic card skipped',
  },
}

export function labelFor(toolName, state) {
  const labels = TOOL_LABELS[toolName]

  if (!labels) return toolName

  return labels[state] || toolName
}
