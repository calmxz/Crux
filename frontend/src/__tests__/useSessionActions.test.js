import { describe, it, expect, beforeEach, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const routerPush = vi.fn()

const routeRef = { name: 'home', params: {}, fullPath: '/' }

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
  useRoute: () => routeRef,
}))

const toastSuccess = vi.fn()

const toastError = vi.fn()

vi.mock('@/composables/useToast.js', () => ({
  useToast: () => ({ showSuccess: toastSuccess, showError: toastError, showWarn: vi.fn() }),
}))

// E-12: capture the confirm config so a test can invoke accept itself.
// Nothing is accepted implicitly here -- that is the point of the dialog.
let lastConfirm = null

vi.mock('primevue/useconfirm', () => ({
  useConfirm: () => ({
    require: (cfg) => {
      lastConfirm = cfg
    },
  }),
}))

import { useSessionActions } from '@/composables/useSessionActions.js'
import { useSessionStore } from '@/stores/session.js'
import { useSidebar } from '@/composables/useSidebar.js'

// The composable must be called inside setup(), so tests mount a tiny host
// component and capture the returned API via closure.
function mountHost() {
  let actions

  const Host = defineComponent({
    setup() {
      actions = useSessionActions()

      return () => h('div')
    },
  })

  mount(Host)

  return actions
}

beforeEach(() => {
  setActivePinia(createPinia())
  routerPush.mockClear()
  toastSuccess.mockClear()
  toastError.mockClear()
  lastConfirm = null
  routeRef.name = 'home'
  routeRef.params = {}
})

describe('useSessionActions — confirmEnd', () => {
  it('opens the shared destructive-dialog contract and defers the store call to accept', async () => {
    const store = useSessionStore()
    const endSpy = vi.spyOn(store, 'endSession').mockResolvedValue({})
    const actions = mountHost()

    actions.confirmEnd({ id: 's1', topic: 'Glycolysis' })

    expect(lastConfirm.header).toBe('End session')
    expect(lastConfirm.message).toBe(
      'End "Glycolysis"? You can still read it, but you cannot continue the conversation.',
    )
    expect(lastConfirm.rejectLabel).toBe('Cancel')
    expect(lastConfirm.acceptLabel).toBe('End session')
    expect(lastConfirm.rejectClass).toBe('p-button-text p-button-secondary')
    expect(lastConfirm.acceptClass).toBe('p-button-danger confirm-delete-strong')
    expect(lastConfirm.icon).toBeUndefined()
    expect(endSpy).not.toHaveBeenCalled()

    await lastConfirm.accept()
    expect(endSpy).toHaveBeenCalledWith('s1')
  })

  it('does not open the dialog while an end is already in flight', async () => {
    const store = useSessionStore()
    let resolveEnd
    vi.spyOn(store, 'endSession').mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveEnd = resolve
        }),
    )
    const actions = mountHost()

    const inFlight = actions.endSession({ id: 's1', topic: 'X' })
    expect(actions.busy.value).toBe(true)

    actions.confirmEnd({ id: 's1', topic: 'X' })
    expect(lastConfirm).toBeNull()

    resolveEnd({})
    await inFlight
    expect(actions.busy.value).toBe(false)
  })
})

describe('useSessionActions — endSession pending-summary toast', () => {
  it('toasts and consumes the pending summary when navigated away from that session', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'endSession').mockImplementation(async () => {
      store.pendingSummary = { sessionId: 's1', kind: 'summary', text: 'Great work.' }

      return {}
    })
    routeRef.name = 'home'
    routeRef.params = {}
    const actions = mountHost()

    await actions.endSession({ id: 's1', topic: 'X' })

    expect(toastSuccess).toHaveBeenCalledWith('Great work.')
    expect(store.pendingSummary).toBeNull()
  })

  it('does not toast when still on that session route', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'endSession').mockImplementation(async () => {
      store.pendingSummary = { sessionId: 's1', kind: 'summary', text: 'Great work.' }

      return {}
    })
    routeRef.name = 'session'
    routeRef.params = { id: 's1' }
    const actions = mountHost()

    await actions.endSession({ id: 's1', topic: 'X' })

    expect(toastSuccess).not.toHaveBeenCalled()
    expect(store.pendingSummary).toEqual({ sessionId: 's1', kind: 'summary', text: 'Great work.' })
  })

  it('guards against a double submit', async () => {
    const store = useSessionStore()
    let resolveEnd

    const endSpy = vi.spyOn(store, 'endSession').mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveEnd = resolve
        }),
    )

    const actions = mountHost()

    const p1 = actions.endSession({ id: 's1', topic: 'X' })
    const p2 = actions.endSession({ id: 's1', topic: 'X' })
    resolveEnd({})
    await Promise.all([p1, p2])

    expect(endSpy).toHaveBeenCalledTimes(1)
    expect(actions.busy.value).toBe(false)
  })
})

describe('useSessionActions — resume', () => {
  it('reopens the session, closes the drawer, and navigates to it', async () => {
    const store = useSessionStore()
    const reopenSpy = vi.spyOn(store, 'reopenSession').mockResolvedValue({})
    const { drawerOpen } = useSidebar()
    drawerOpen.value = true
    const actions = mountHost()

    await actions.resume({ id: 's2' })

    expect(reopenSpy).toHaveBeenCalledWith('s2')
    expect(drawerOpen.value).toBe(false)
    expect(routerPush).toHaveBeenCalledWith({ name: 'session', params: { id: 's2' } })
  })
})

describe('useSessionActions — continueTopic', () => {
  it('navigates to the newly created session', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'continueTopic').mockResolvedValue({ id: 's3' })
    const actions = mountHost()

    await actions.continueTopic({ id: 's2', topic: 'X' })

    expect(routerPush).toHaveBeenCalledWith({ name: 'session', params: { id: 's3' } })
  })

  it('does not navigate when nothing was created', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'continueTopic').mockResolvedValue(undefined)
    const actions = mountHost()

    await actions.continueTopic({ id: 's2', topic: 'X' })

    expect(routerPush).not.toHaveBeenCalled()
  })
})

describe('useSessionActions — setPinned', () => {
  it('toasts on pin failure', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'setPinned').mockRejectedValue(new Error('nope'))
    const actions = mountHost()

    await actions.setPinned({ id: 's1' }, true)

    expect(toastError).toHaveBeenCalledWith('Could not pin the session.')
  })

  it('toasts on unpin failure', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'setPinned').mockRejectedValue(new Error('nope'))
    const actions = mountHost()

    await actions.setPinned({ id: 's1' }, false)

    expect(toastError).toHaveBeenCalledWith('Could not unpin the session.')
  })
})

describe('useSessionActions — rename', () => {
  it('no-ops on empty input', async () => {
    const store = useSessionStore()
    const renameSpy = vi.spyOn(store, 'renameSession').mockResolvedValue({})
    const actions = mountHost()

    const result = await actions.rename({ id: 's1', topic: 'Old' }, '   ')

    expect(renameSpy).not.toHaveBeenCalled()
    expect(result).toBe(false)
  })

  it('no-ops when unchanged', async () => {
    const store = useSessionStore()
    const renameSpy = vi.spyOn(store, 'renameSession').mockResolvedValue({})
    const actions = mountHost()

    const result = await actions.rename({ id: 's1', topic: 'Old' }, 'Old')

    expect(renameSpy).not.toHaveBeenCalled()
    expect(result).toBe(false)
  })

  it('toasts on failure', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'renameSession').mockRejectedValue(new Error('nope'))
    const actions = mountHost()

    const result = await actions.rename({ id: 's1', topic: 'Old' }, 'New')

    expect(toastError).toHaveBeenCalledWith('Could not rename the session.')
    expect(result).toBe(false)
  })

  it('renames on success', async () => {
    const store = useSessionStore()
    const renameSpy = vi.spyOn(store, 'renameSession').mockResolvedValue({})
    const actions = mountHost()

    const result = await actions.rename({ id: 's1', topic: 'Old' }, 'New')

    expect(renameSpy).toHaveBeenCalledWith('s1', 'New')
    expect(result).toBe(true)
  })
})
