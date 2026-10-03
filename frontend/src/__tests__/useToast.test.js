import { describe, it, expect, vi } from 'vitest'

const addMock = vi.fn()

vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: addMock }),
}))

import { useToast } from '@/composables/useToast.js'

describe('useToast', () => {
  it('showError forwards to PrimeVue with error severity', () => {
    const { showError } = useToast()
    showError('boom')
    expect(addMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ severity: 'error', detail: 'boom', summary: 'Error', life: 6000 }),
    )
  })

  it('showWarn forwards with warn severity and custom summary', () => {
    const { showWarn } = useToast()
    showWarn('careful', { summary: 'Whoa', life: 1000 })
    expect(addMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ severity: 'warn', detail: 'careful', summary: 'Whoa', life: 1000 }),
    )
  })

  it('showSuccess uses success severity', () => {
    const { showSuccess } = useToast()
    showSuccess('saved')
    expect(addMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ severity: 'success', detail: 'saved' }),
    )
  })
})
