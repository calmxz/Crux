import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

import ReferenceStatusBanner from '@/components/chat/ReferenceStatusBanner.vue'

const deleteDocument = vi.fn()

vi.mock('@/services/uploadApi.js', () => ({
  deleteDocument: (...a) => deleteDocument(...a),
}))

// Capture the confirm config so a test can invoke accept/reject deterministically.
let lastConfirm = null

vi.mock('primevue/useconfirm', () => ({
  useConfirm: () => ({
    require: (cfg) => {
      lastConfirm = cfg
    },
  }),
}))

const showSuccess = vi.fn()

const showError = vi.fn()

vi.mock('@/composables/useToast.js', () => ({
  useToast: () => ({ showSuccess, showError, showWarn: vi.fn() }),
}))

// F-12: the banner no longer polls -- SessionView owns one useReferencePoll and
// passes its state down, so these are plain props.
function mountBanner(props = {}) {
  return mount(ReferenceStatusBanner, {
    props: { status: null, documents: [], failed: false, ...props },
  })
}

describe('ReferenceStatusBanner', () => {
  beforeEach(() => {
    deleteDocument.mockReset()
    showSuccess.mockReset()
    showError.mockReset()
    lastConfirm = null
  })

  it('renders nothing when the session has no documents', () => {
    const wrapper = mountBanner()
    expect(wrapper.find('[data-testid="reference-status"]').exists()).toBe(false)
  })

  it('shows an indexing message while pending', () => {
    const wrapper = mountBanner({
      status: 'pending',
      documents: [{ id: 1, filename: 'a.pdf', status: 'pending' }],
    })

    expect(wrapper.get('[data-testid="reference-status"]').text()).toMatch(/indexing/i)
  })

  it('counts only in-flight documents in the indexing message', () => {
    const wrapper = mountBanner({
      status: 'pending',
      documents: [
        { id: 1, filename: 'a.pdf', status: 'ready' },
        { id: 2, filename: 'b.pdf', status: 'ready' },
        { id: 3, filename: 'c.pdf', status: 'ready' },
        { id: 4, filename: 'd.pdf', status: 'pending' },
      ],
    })

    expect(wrapper.get('[data-testid="reference-status"]').text()).toContain(
      'Indexing 1 reference...',
    )
  })

  it('shows a ready message when all documents are ready', () => {
    const wrapper = mountBanner({
      status: 'ready',
      documents: [{ id: 1, filename: 'a.pdf', status: 'ready' }],
    })

    expect(wrapper.get('[data-testid="reference-status"]').text()).toMatch(/ready/i)
  })

  it('shows a failure message when a document failed', () => {
    const wrapper = mountBanner({
      status: 'failed',
      documents: [{ id: 1, filename: 'a.pdf', status: 'failed', error: 'bad pdf' }],
    })

    expect(wrapper.get('[data-testid="reference-status"]').text()).toMatch(/could not|failed/i)
  })

  it('re-renders from new props when the parent switches session', async () => {
    const wrapper = mountBanner({
      status: 'ready',
      documents: [{ id: 1, filename: 'a.pdf', status: 'ready' }],
    })

    expect(wrapper.get('[data-testid="reference-status"]').text()).toMatch(/1 reference ready/i)
    await wrapper.setProps({ status: null, documents: [] })
    expect(wrapper.find('[data-testid="reference-status"]').exists()).toBe(false)
  })

  it('expands to show a per-file list with filenames', async () => {
    const wrapper = mountBanner({
      status: 'ready',
      documents: [
        { id: 1, filename: 'a.pdf', status: 'ready' },
        { id: 2, filename: 'b.md', status: 'pending' },
      ],
    })

    // List hidden until expanded.
    expect(wrapper.find('[data-testid="ref-file-list"]').exists()).toBe(false)
    await wrapper.get('[data-testid="ref-toggle"]').trigger('click')
    expect(wrapper.get('[data-testid="ref-file-list"]').text()).toContain('a.pdf')
    expect(wrapper.get('[data-testid="ref-file-list"]').text()).toContain('b.md')
  })

  // F-12: a poll threw. The row is the whole banner when the very first poll
  // failed (no status yet), and an extra line when we have a last-known list.
  describe('failed (references unavailable)', () => {
    it('renders the unavailable row with a Retry control when there is no status yet', () => {
      const wrapper = mountBanner({ status: null, documents: [], failed: true })
      const row = wrapper.get('[data-testid="ref-unavailable"]')
      expect(row.text()).toMatch(/references unavailable/i)
      expect(wrapper.get('[data-testid="ref-retry"]').text()).toBe('Retry')
      // No last-known list, so no toggle to expand.
      expect(wrapper.find('[data-testid="ref-toggle"]').exists()).toBe(false)
    })

    it('emits refresh when Retry is clicked', async () => {
      const wrapper = mountBanner({ status: null, documents: [], failed: true })
      await wrapper.get('[data-testid="ref-retry"]').trigger('click')
      expect(wrapper.emitted('refresh')).toHaveLength(1)
    })

    it('keeps the last-known list and its delete buttons reachable during an outage', async () => {
      const wrapper = mountBanner({
        status: 'pending',
        documents: [{ id: 1, filename: 'a.pdf', status: 'pending' }],
        failed: true,
      })

      expect(wrapper.find('[data-testid="ref-unavailable"]').exists()).toBe(true)
      await wrapper.get('[data-testid="ref-toggle"]').trigger('click')
      expect(wrapper.find('[data-testid="ref-delete-1"]').exists()).toBe(true)
    })

    it('carries the unavailable modifier class', () => {
      const wrapper = mountBanner({ status: 'ready', documents: [], failed: true })
      expect(wrapper.get('[data-testid="reference-status"]').classes()).toContain('is-unavailable')
    })

    it('never emits an is-null status class', () => {
      const wrapper = mountBanner({ status: null, documents: [], failed: true })
      expect(wrapper.get('[data-testid="reference-status"]').classes()).not.toContain('is-null')
    })
  })

  it('deletes a file on confirm-accept, shows a success toast and asks for a refresh', async () => {
    deleteDocument.mockResolvedValue(undefined)

    const wrapper = mountBanner({
      status: 'ready',
      documents: [{ id: 1, filename: 'a.pdf', status: 'ready' }],
    })

    await wrapper.get('[data-testid="ref-toggle"]').trigger('click')
    await wrapper.get('[data-testid="ref-delete-1"]').trigger('click')
    // Simulate the user accepting the confirm dialog.
    await lastConfirm.accept()
    await flushPromises()
    expect(deleteDocument).toHaveBeenCalledWith(1)
    expect(showSuccess).toHaveBeenCalled()
    expect(wrapper.emitted('refresh')).toHaveLength(1)
  })

  it('styles confirm buttons: a darker destructive accept and a neutral, non-coral cancel', async () => {
    const wrapper = mountBanner({
      status: 'ready',
      documents: [{ id: 1, filename: 'a.pdf', status: 'ready' }],
    })

    await wrapper.get('[data-testid="ref-toggle"]').trigger('click')
    await wrapper.get('[data-testid="ref-delete-1"]').trigger('click')
    // Accept carries the darker-delete hook class (styled globally).
    expect(lastConfirm.acceptClass).toContain('confirm-delete-strong')
    // Cancel must opt out of the default primary (coral) fill.
    expect(lastConfirm.rejectClass).toContain('p-button-secondary')
    expect(lastConfirm.rejectClass).not.toContain('p-button-danger')
  })

  it('does not delete when confirm is rejected', async () => {
    const wrapper = mountBanner({
      status: 'ready',
      documents: [{ id: 1, filename: 'a.pdf', status: 'ready' }],
    })

    await wrapper.get('[data-testid="ref-toggle"]').trigger('click')
    await wrapper.get('[data-testid="ref-delete-1"]').trigger('click')

    if (lastConfirm.reject) await lastConfirm.reject()
    expect(deleteDocument).not.toHaveBeenCalled()
  })

  it('shows an error toast and asks for a refresh when delete fails', async () => {
    deleteDocument.mockRejectedValue(new Error('500'))

    const wrapper = mountBanner({
      status: 'ready',
      documents: [{ id: 1, filename: 'a.pdf', status: 'ready' }],
    })

    await wrapper.get('[data-testid="ref-toggle"]').trigger('click')
    await wrapper.get('[data-testid="ref-delete-1"]').trigger('click')
    await lastConfirm.accept()
    await flushPromises()
    expect(showError).toHaveBeenCalled()
    expect(showSuccess).not.toHaveBeenCalled()
    expect(wrapper.emitted('refresh')).toHaveLength(1)
  })
})
