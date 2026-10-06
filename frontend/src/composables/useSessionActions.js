import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useSessionStore } from '@/stores/session.js'
import { useToast } from '@/composables/useToast.js'
import { useSidebar } from '@/composables/useSidebar.js'

// Ticket 08: shared session actions (rename, pin, end-with-confirm, continue
// topic, resume) so any surface -- not just the sidebar row -- can call the
// same behaviour. Pure lift-and-share: no visual or behavioural change for
// the learner. Must be called inside setup(), since it calls useRoute,
// useRouter, useConfirm, useSessionStore, useSidebar and useToast itself.
// Each call site gets its own `busy` ref, so two callers never block each
// other's in-flight guard.
export function useSessionActions() {
  const route = useRoute()
  const router = useRouter()
  const store = useSessionStore()
  const { closeDrawer } = useSidebar()
  const { showSuccess, showError } = useToast()
  const confirm = useConfirm()

  const busy = ref(false)

  // E-12: ending a session is one-way from the caller's point of view -- there
  // is no undo and the learner may be several screens from the transcript --
  // so it asks first. Same dialog contract as the file delete in
  // ReferenceStatusBanner: no icon, neutral cancel, strong destructive accept.
  function confirmEnd(session) {
    if (busy.value) return
    confirm.require({
      header: 'End session',
      message: `End "${session.topic || 'Untitled'}"? You can still read it, but you cannot continue the conversation.`,
      rejectLabel: 'Cancel',
      acceptLabel: 'End session',
      rejectClass: 'p-button-text p-button-secondary',
      acceptClass: 'p-button-danger confirm-delete-strong',
      accept: () => endSession(session),
    })
  }

  // busy is raised here rather than in confirmEnd: a cancelled dialog must
  // leave the caller usable, and it also guards a second accept arriving
  // mid-request.
  async function endSession(session) {
    if (busy.value) return
    busy.value = true

    try {
      await store.endSession(session.id)
      // F-44: the summary dialog lives in SessionView; ending from anywhere
      // else would silently drop the pending summary. Toast it instead.
      const s = store.pendingSummary
      const onThatSession = route.name === 'session' && route.params.id === session.id

      if (s && s.sessionId === session.id && !onThatSession) {
        showSuccess(s.text)
        store.consumePendingSummary()
      }
    } catch {
      /* store.error populated */
    } finally {
      busy.value = false
    }
  }

  async function resume(session) {
    if (busy.value) return
    busy.value = true

    try {
      await store.reopenSession(session.id)
      closeDrawer()
      router.push({ name: 'session', params: { id: session.id } })
    } catch {
      /* store.error populated */
    } finally {
      busy.value = false
    }
  }

  async function continueTopic(session) {
    if (busy.value) return
    busy.value = true

    try {
      const created = await store.continueTopic(session)

      if (created) router.push({ name: 'session', params: { id: created.id } })
      closeDrawer()
    } catch {
      /* F-06: store.error populated; without this the rethrow is unhandled */
    } finally {
      busy.value = false
    }
  }

  function setPinned(session, on) {
    const id = session.id

    return store
      .setPinned(id, on)
      .catch(() => showError(on ? 'Could not pin the session.' : 'Could not unpin the session.'))
  }

  async function rename(session, nextTopic) {
    const next = (nextTopic || '').trim()

    if (!next || next === (session.topic || '')) return false

    try {
      await store.renameSession(session.id, next)

      return true
    } catch {
      showError('Could not rename the session.')

      return false
    }
  }

  return {
    busy,
    confirmEnd,
    endSession,
    resume,
    continueTopic,
    setPinned,
    rename,
  }
}
