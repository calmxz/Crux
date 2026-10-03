import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const routerPush = vi.fn()

const routeRef = { params: {}, fullPath: '/' }

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
  useRoute: () => routeRef,
}))

vi.mock('@/composables/useToast.js', () => ({
  useToast: () => ({ showSuccess: vi.fn(), showError: vi.fn(), showWarn: vi.fn() }),
}))

// E-12: capture the confirm config so a test can invoke accept/reject itself.
// Nothing is accepted implicitly here -- that is the point of the dialog.
let lastConfirm = null

vi.mock('primevue/useconfirm', () => ({
  useConfirm: () => ({
    require: (cfg) => {
      lastConfirm = cfg
    },
  }),
}))

import SidebarSessionRow from '@/components/sidebar/SidebarSessionRow.vue'
import { useSessionStore } from '@/stores/session.js'

const baseSession = (over = {}) => ({
  id: 's1',
  topic: 'Glycolysis',
  ended_at: null,
  pinned: false,
  progress: null,
  ...over,
})

function mountRow(session) {
  return mount(SidebarSessionRow, {
    props: { session, state: 'active' },
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  routerPush.mockClear()
  lastConfirm = null
})

// Opens the row menu and clicks End, which is all the row exposes.
async function clickEnd(wrapper) {
  await wrapper.get('[data-testid="sidebar-row-menu-trigger"]').trigger('click')
  await wrapper.get('[data-testid="sidebar-row-menu-end"]').trigger('click')
}

describe('SidebarSessionRow — accessible row label', () => {
  it('includes the level in the accessible row label', () => {
    const wrapper = mountRow(
      baseSession({
        progress: { level: 'advanced', focus_target_gap: 'ATP yield', mastered_count: 3 },
      }),
    )

    const label = wrapper.get('[data-testid="sidebar-row-open"]').attributes('aria-label')
    expect(label).toContain('level advanced')
    expect(label).toContain('focus ATP yield')
    expect(label).toContain('3 mastered')
  })

  it('omits level from the row label when unset', () => {
    const wrapper = mountRow(baseSession({ progress: { mastered_count: 0 } }))
    const label = wrapper.get('[data-testid="sidebar-row-open"]').attributes('aria-label')
    expect(label).not.toContain('level')
  })
})

describe('SidebarSessionRow — End session confirmation (E-12)', () => {
  it('asks before ending and does not call the store until accept', async () => {
    const store = useSessionStore()
    const endSpy = vi.spyOn(store, 'endSession').mockResolvedValue({})
    const wrapper = mountRow(baseSession())

    await clickEnd(wrapper)

    expect(lastConfirm).toBeTruthy()
    expect(endSpy).not.toHaveBeenCalled()

    await lastConfirm.accept()
    expect(endSpy).toHaveBeenCalledWith('s1')
  })

  it('never calls the store when the dialog is dismissed', async () => {
    const store = useSessionStore()
    const endSpy = vi.spyOn(store, 'endSession').mockResolvedValue({})
    const wrapper = mountRow(baseSession())

    await clickEnd(wrapper)
    // Cancel is the dialog's own control; the row registers no reject handler,
    // so dismissing simply leaves the store untouched.
    expect(lastConfirm.reject).toBeUndefined()
    expect(endSpy).not.toHaveBeenCalled()

    // And the row stays usable: a second End still opens the dialog.
    lastConfirm = null
    await clickEnd(wrapper)
    expect(lastConfirm).toBeTruthy()
    expect(endSpy).not.toHaveBeenCalled()
  })

  it('uses the shared destructive-dialog contract', async () => {
    const store = useSessionStore()
    vi.spyOn(store, 'endSession').mockResolvedValue({})
    const wrapper = mountRow(baseSession())

    await clickEnd(wrapper)

    expect(lastConfirm.header).toBe('End session')
    expect(lastConfirm.message).toBe(
      'End "Glycolysis"? You can still read it, but you cannot continue the conversation.',
    )
    expect(lastConfirm.rejectLabel).toBe('Cancel')
    expect(lastConfirm.acceptLabel).toBe('End session')
    expect(lastConfirm.rejectClass).toBe('p-button-text p-button-secondary')
    expect(lastConfirm.acceptClass).toBe('p-button-danger confirm-delete-strong')
    expect(lastConfirm.icon).toBeUndefined()
  })
})
