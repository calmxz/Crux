import { ref } from 'vue'

import { ERR_DUPLICATE_TOPIC } from '@/lib/errorCodes.js'

// State machine for the start pages: lookup -> intercept | create.
// Lookup is an enhancement: any failure falls through to direct create.
// No level picker up front -- the in-chat knowledge diagnostic asks after the
// tutor's first answer (DIAGNOSTIC: REQUIRED prompt state).
export function useStartFlow({ store, router, beforeNavigate }) {
  const stage = ref('idle') // 'idle' | 'intercept'
  const busy = ref(false)
  const interceptMatch = ref(null)
  const interceptKind = ref(null) // 'active' | 'ended' | null
  const topic = ref('')
  let generation = 0

  async function begin(rawTopic) {
    const trimmed = (rawTopic || '').trim()

    if (!trimmed || busy.value) return
    topic.value = trimmed
    busy.value = true
    const gen = generation

    try {
      const res = await store.lookupTopic(trimmed)

      if (gen !== generation) return

      if (res?.active_match) {
        interceptMatch.value = res.active_match
        interceptKind.value = 'active'
        stage.value = 'intercept'
      } else if (res?.ended_match) {
        interceptMatch.value = res.ended_match
        interceptKind.value = 'ended'
        stage.value = 'intercept'
      } else {
        await _create(gen)
      }
    } finally {
      busy.value = false
    }
  }

  function openExisting() {
    router.push({ name: 'session', params: { id: interceptMatch.value.session_id } })
  }

  async function continuePrior() {
    if (busy.value) return
    busy.value = true

    try {
      const created = await store.continueTopic({
        id: interceptMatch.value.session_id,
        topic: interceptMatch.value.title,
        ended_at: interceptMatch.value.ended_at,
      })

      if (created) router.push({ name: 'session', params: { id: created.id } })
    } finally {
      busy.value = false
    }
  }

  async function startFresh() {
    if (busy.value) return
    busy.value = true

    try {
      await _create(generation)
    } finally {
      busy.value = false
    }
  }

  async function _create(gen) {
    try {
      const created = await store.createSession({
        topic: topic.value,
        seedMode: 'fresh',
        priorSessionId: null,
      })

      if (!created || gen !== generation) return

      if (beforeNavigate) await beforeNavigate(created)
      router.push({ name: 'session', params: { id: created.id } })
    } catch (e) {
      if (e?.status === 409 && e?.body?.detail?.code === ERR_DUPLICATE_TOPIC) {
        // Race backstop: a session appeared between lookup and create.
        interceptMatch.value = { session_id: e.body.detail.session_id, title: topic.value }
        interceptKind.value = 'active'
        stage.value = 'intercept'

        return
      }

      throw e
    }
  }

  function cancel() {
    generation += 1
    stage.value = 'idle'
    interceptMatch.value = null
    interceptKind.value = null
  }

  return {
    stage,
    busy,
    interceptMatch,
    interceptKind,
    begin,
    openExisting,
    continuePrior,
    startFresh,
    cancel,
  }
}
