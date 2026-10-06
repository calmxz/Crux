import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import AccountView from '@/views/AccountView.vue'
import { AUTH_CODE_COPY } from '@/lib/authErrors.js'
import { useUserStore } from '@/stores/user.js'
import { useAuthStore } from '@/stores/auth.js'
import { ApiError } from '@/services/apiClient.js'
import { deleteAccount, exportData } from '@/services/meApi.js'

vi.mock('@/services/meApi.js', () => ({
  deleteAccount: vi.fn(),
  exportData: vi.fn(),
}))

const showSuccess = vi.fn()

const showError = vi.fn()

vi.mock('@/composables/useToast.js', () => ({
  useToast: () => ({ showSuccess, showError, showWarn: vi.fn() }),
}))

const routerPush = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
  RouterLink: { template: '<a><slot /></a>', props: ['to'] },
}))

// Matches the fallthrough-attrs pattern already used in gapPickerDialog's
// spec for GapPickerDialog: declaring only the props/emits the stub cares
// about lets data-testid/class/etc. from the real usage land on the stub
// root via Vue's default attr inheritance. Both the default slot and the
// named #footer slot are rendered (unlike GapPickerDialog, our dialog puts
// its action buttons in #footer) so both are reachable from a spec.
const DialogStub = {
  props: ['visible'],
  emits: ['update:visible'],
  template: '<div v-if="visible"><slot /><slot name="footer" /></div>',
}

const stubs = {
  RouterLink: { template: '<a><slot /></a>', props: ['to'] },
  Dialog: DialogStub,
}

// F-46: updateProfile writes through to PATCH /me via the real apiClient
// (dynamic import) -- mock global fetch, same pattern as settingsView.test.js.
function ok(body) {
  return Promise.resolve({
    ok: true,
    status: 200,
    headers: { get: () => null },
    text: () => Promise.resolve(JSON.stringify(body)),
  })
}

describe('AccountView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    showSuccess.mockClear()
    showError.mockClear()
    routerPush.mockClear()
    deleteAccount.mockReset()
    exportData.mockReset()
    globalThis.fetch = vi.fn().mockReturnValue(ok({}))
    const user = useUserStore()
    user.userId = 'u_test'
    user.name = 'Eddy'
    user.interactionPreferences = { feedback: 'hints' }
    user.onboardingComplete = true
  })

  it('renders name field testids', () => {
    const w = mount(AccountView, { global: { stubs } })

    for (const id of ['settings-name', 'settings-save']) {
      expect(w.find(`[data-testid="${id}"]`).exists()).toBe(true)
    }
  })

  // Sign out is a navigation act, not a setting: it lives on the sidebar
  // footer rail (see sidebar.test.js), never inside the Account tab.
  it('does not render any sign-out control', async () => {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1' }, access_token: 't' }
    const w = mount(AccountView, { global: { stubs } })
    await flushPromises()
    expect(w.find('[data-testid="settings-signout-section"]').exists()).toBe(false)
    expect(w.find('[data-testid="settings-sign-out"]').exists()).toBe(false)
  })

  it('does not render the security card when unauthenticated', () => {
    const w = mount(AccountView, { global: { stubs } })
    expect(w.find('[data-testid="settings-security"]').exists()).toBe(false)
  })

  it('renders the security card when authenticated', async () => {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1', email: 'a@b.c' }, access_token: 't' }
    const w = mount(AccountView, { global: { stubs } })
    await flushPromises()
    expect(w.find('[data-testid="settings-security"]').exists()).toBe(true)
  })

  // D2: every submit in Settings is the filled control now, not a text line.
  it('both submits are filled buttons', async () => {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1', email: 'a@b.c' }, access_token: 't' }
    const w = mount(AccountView, { global: { stubs } })
    await flushPromises()
    expect(w.get('[data-testid="settings-save"]').classes()).toContain('btn-fill')
    expect(w.get('[data-testid="settings-pw-submit"]').classes()).toContain('btn-fill')
    expect(w.find('.text-btn').exists()).toBe(false)
  })

  it('save button disabled until name changes (feedback no longer affects dirty)', async () => {
    const w = mount(AccountView, { global: { stubs } })
    expect(w.find('[data-testid="settings-save"]').attributes('disabled')).toBeDefined()
    await w.find('[data-testid="settings-name"]').setValue('New Name')
    expect(w.find('[data-testid="settings-save"]').attributes('disabled')).toBeUndefined()
  })

  // #357: tutor preferences autosave on the Learning tab; Save name sends
  // the name alone and never re-writes them.
  it('save sends the name alone', async () => {
    const user = useUserStore()
    const updateProfile = vi.spyOn(user, 'updateProfile').mockResolvedValue()
    const w = mount(AccountView, { global: { stubs } })
    await w.find('[data-testid="settings-name"]').setValue('New Name')
    await w.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(updateProfile).toHaveBeenCalledExactlyOnceWith({ name: 'New Name' })
    expect(w.find('[data-testid="settings-saved"]').exists()).toBe(true)
  })

  it('shows inline error and re-enables on API failure', async () => {
    const user = useUserStore()
    vi.spyOn(user, 'updateProfile').mockRejectedValue(new Error('down'))
    const w = mount(AccountView, { global: { stubs } })
    await w.find('[data-testid="settings-name"]').setValue('New Name')
    await w.find('form').trigger('submit.prevent')
    await flushPromises()
    expect(w.find('[data-testid="settings-error"]').exists()).toBe(true)
    expect(w.find('[data-testid="settings-save"]').attributes('disabled')).toBeUndefined()
  })

  it('password mismatch hint shows when confirm differs', async () => {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1', email: 'a@b.c' }, access_token: 't' }
    const w = mount(AccountView, { global: { stubs } })
    await flushPromises()
    await w.find('[data-testid="settings-pw-new"]').setValue('longenough1')
    await w.find('[data-testid="settings-pw-confirm"]').setValue('different1')
    expect(w.find('[data-testid="settings-pw-mismatch"]').exists()).toBe(true)
  })

  it('change-password submit is gated until current + matching 8+ new password', async () => {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1', email: 'a@b.c' }, access_token: 't' }
    const w = mount(AccountView, { global: { stubs } })
    await flushPromises()
    const btn = w.get('[data-testid="settings-pw-submit"]')
    expect(btn.attributes('disabled')).toBeDefined()
    await w.get('[data-testid="settings-pw-current"]').setValue('oldpass12')
    await w.get('[data-testid="settings-pw-new"]').setValue('newpass12')
    await w.get('[data-testid="settings-pw-confirm"]').setValue('newpass12')
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('wrong current password shows an error and does not update', async () => {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1', email: 'a@b.c' }, access_token: 't' }
    vi.spyOn(auth, 'signIn').mockRejectedValue(new Error('Invalid login credentials'))
    const update = vi.spyOn(auth, 'updatePassword').mockResolvedValue()
    const w = mount(AccountView, { global: { stubs } })
    await flushPromises()
    await w.get('[data-testid="settings-pw-current"]').setValue('wrongpass')
    await w.get('[data-testid="settings-pw-new"]').setValue('newpass12')
    await w.get('[data-testid="settings-pw-confirm"]').setValue('newpass12')
    // The button submits the form rather than carrying its own click handler;
    // jsdom does not run implicit submission for a synthetic click, so the
    // test drives the form and asserts the button is wired to it.
    expect(w.get('[data-testid="settings-pw-submit"]').attributes('type')).toBe('submit')
    await w.get('form.pw-form').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="settings-pw-error"]').exists()).toBe(true)
    expect(w.find('[data-testid="settings-pw-error"]').attributes('role')).toBe('alert')
    expect(update).not.toHaveBeenCalled()
  })

  it('valid change verifies current password then updates and shows success', async () => {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1', email: 'a@b.c' }, access_token: 't' }
    const signIn = vi.spyOn(auth, 'signIn').mockResolvedValue()
    const update = vi.spyOn(auth, 'updatePassword').mockResolvedValue()
    const w = mount(AccountView, { global: { stubs } })
    await flushPromises()
    await w.get('[data-testid="settings-pw-current"]').setValue('oldpass12')
    await w.get('[data-testid="settings-pw-new"]').setValue('newpass12')
    await w.get('[data-testid="settings-pw-confirm"]').setValue('newpass12')
    expect(w.get('[data-testid="settings-pw-submit"]').attributes('type')).toBe('submit')
    await w.get('form.pw-form').trigger('submit')
    await flushPromises()
    expect(signIn).toHaveBeenCalledWith('a@b.c', 'oldpass12')
    expect(update).toHaveBeenCalledWith('newpass12')
    expect(w.find('[data-testid="settings-pw-success"]').exists()).toBe(true)
    expect(w.find('[data-testid="settings-pw-success"]').attributes('role')).toBe('status')
    expect(showSuccess).toHaveBeenCalled()
  })

  // E-13: our copy for the SDK code, never the SDK's prose.
  it('maps an updatePassword AuthError code to our own copy', async () => {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1', email: 'a@b.c' }, access_token: 't' }
    vi.spyOn(auth, 'signIn').mockResolvedValue()
    vi.spyOn(auth, 'updatePassword').mockRejectedValue(
      Object.assign(new Error('New password should be different from the old password.'), {
        code: 'same_password',
        status: 422,
      }),
    )
    const w = mount(AccountView, { global: { stubs } })
    await flushPromises()
    await w.get('[data-testid="settings-pw-current"]').setValue('oldpass12')
    await w.get('[data-testid="settings-pw-new"]').setValue('oldpass12x')
    await w.get('[data-testid="settings-pw-confirm"]').setValue('oldpass12x')
    await w.get('form.pw-form').trigger('submit')
    await flushPromises()
    const text = w.get('[data-testid="settings-pw-error"]').text()
    expect(text).toBe(AUTH_CODE_COPY.same_password)
    expect(text).not.toContain('should be different')
  })

  // R2-18/20: the Account page shows the signed-in email, read-only, sourced
  // from the auth store (never editable here).
  it('renders the signed-in email from the auth store', async () => {
    const auth = useAuthStore()
    auth.session = { user: { id: 'u-1', email: 'learner@example.com' }, access_token: 't' }
    const w = mount(AccountView, { global: { stubs } })
    await flushPromises()
    expect(w.get('[data-testid="account-email"]').text()).toContain('learner@example.com')
  })

  it('falls back to "No email" when the auth store has none', () => {
    const w = mount(AccountView, { global: { stubs } })
    expect(w.get('[data-testid="account-email"]').text()).toContain('No email')
  })

  // #361: "take it or destroy it" -- the export sits right above Delete.
  describe('export data', () => {
    let createObjectURL
    let revokeObjectURL
    let clickSpy
    let connectedAtClick

    function mountAuthed() {
      const auth = useAuthStore()
      auth.session = { user: { id: 'u-1', email: 'learner@example.com' }, access_token: 't' }

      return mount(AccountView, { global: { stubs } })
    }

    beforeEach(() => {
      // jsdom has no object URLs and does not implement anchor navigation.
      createObjectURL = vi.fn(() => 'blob:export')
      revokeObjectURL = vi.fn()
      URL.createObjectURL = createObjectURL
      URL.revokeObjectURL = revokeObjectURL
      connectedAtClick = null
      clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
        connectedAtClick = this.isConnected
      })
    })

    afterEach(() => {
      clickSpy.mockRestore()
      delete URL.createObjectURL
      delete URL.revokeObjectURL
    })

    it('is hidden when unauthenticated', () => {
      const w = mount(AccountView, { global: { stubs } })
      expect(w.find('[data-testid="account-export"]').exists()).toBe(false)
    })

    it('sits directly above the delete section', async () => {
      const w = mountAuthed()
      await flushPromises()
      const exportSec = w.get('[data-testid="account-export"]').element
      expect(exportSec.nextElementSibling).toBe(w.get('[data-testid="account-danger"]').element)
    })

    it('downloads the export as a dated JSON file', async () => {
      const payload = { format_version: 1, exported_at: '2026-09-26T23:59:30Z', sessions: [] }
      exportData.mockResolvedValue(payload)
      const w = mountAuthed()
      await flushPromises()

      await w.get('[data-testid="account-export-btn"]').trigger('click')
      await flushPromises()

      expect(exportData).toHaveBeenCalledOnce()
      const blob = createObjectURL.mock.calls[0][0]
      expect(blob.type).toBe('application/json')
      expect(JSON.parse(await blob.text())).toEqual(payload)
      expect(clickSpy).toHaveBeenCalledOnce()
      const anchor = clickSpy.mock.contexts[0]
      // Same UTC day the server stamps into Content-Disposition, whatever the local zone.
      expect(anchor.download).toBe('crux-export-2026-09-26.json')
      expect(anchor.href).toBe('blob:export')
      expect(connectedAtClick).toBe(true)
      expect(anchor.isConnected).toBe(false)
      await new Promise((r) => setTimeout(r, 0))
      expect(revokeObjectURL).toHaveBeenCalledWith('blob:export')
      expect(showSuccess).toHaveBeenCalledWith('Your data was downloaded.')
      expect(w.find('[data-testid="account-export-error"]').exists()).toBe(false)
    })

    it('disables the button while the export is in flight', async () => {
      let resolveExport
      exportData.mockReturnValue(new Promise((r) => (resolveExport = r)))
      const w = mountAuthed()
      await flushPromises()

      await w.get('[data-testid="account-export-btn"]').trigger('click')
      const btn = w.get('[data-testid="account-export-btn"]')
      expect(btn.attributes('disabled')).toBeDefined()
      expect(btn.text()).toBe('Preparing…')

      await w.get('[data-testid="account-export-btn"]').trigger('click')
      expect(exportData).toHaveBeenCalledOnce()

      resolveExport({})
      await flushPromises()
      expect(w.get('[data-testid="account-export-btn"]').attributes('disabled')).toBeUndefined()
    })

    it('shows an inline error and downloads nothing when the export fails', async () => {
      exportData.mockRejectedValue(new ApiError(503, { detail: 'x' }, '/me/export'))
      const w = mountAuthed()
      await flushPromises()

      await w.get('[data-testid="account-export-btn"]').trigger('click')
      await flushPromises()

      expect(w.get('[data-testid="account-export-error"]').text()).toBe(
        'Could not prepare your export. Try again.',
      )
      expect(createObjectURL).not.toHaveBeenCalled()
      expect(clickSpy).not.toHaveBeenCalled()
      expect(showSuccess).not.toHaveBeenCalled()
    })
  })

  // R2-22 through R2-25: the delete-account section and its confirm dialog.
  describe('delete account', () => {
    function mountAuthed() {
      const auth = useAuthStore()
      auth.session = { user: { id: 'u-1', email: 'learner@example.com' }, access_token: 't' }

      return mount(AccountView, { global: { stubs } })
    }

    it('the danger section copy lists every category that is erased', async () => {
      const w = mountAuthed()
      await flushPromises()
      const text = w.get('[data-testid="account-danger"]').text()
      expect(text).toContain('sessions')
      expect(text).toContain('profiles')
      expect(text).toContain('uploaded files')
      expect(text).toContain('learning history')
      expect(text).toContain('sign-in')
    })

    it('submit stays disabled until the confirmation word matches exactly', async () => {
      const w = mountAuthed()
      await flushPromises()
      await w.get('[data-testid="account-delete-open"]').trigger('click')
      const submit = w.get('[data-testid="account-delete-submit"]')
      expect(submit.attributes('disabled')).toBeDefined()

      await w.get('[data-testid="account-delete-confirm-input"]').setValue('Delete')
      expect(w.get('[data-testid="account-delete-submit"]').attributes('disabled')).toBeDefined()

      await w.get('[data-testid="account-delete-confirm-input"]').setValue('delet')
      expect(w.get('[data-testid="account-delete-submit"]').attributes('disabled')).toBeDefined()

      await w.get('[data-testid="account-delete-confirm-input"]').setValue('delete')
      expect(w.get('[data-testid="account-delete-submit"]').attributes('disabled')).toBeUndefined()
    })

    it('cancel closes the dialog and resets the input', async () => {
      const w = mountAuthed()
      await flushPromises()
      await w.get('[data-testid="account-delete-open"]').trigger('click')
      await w.get('[data-testid="account-delete-confirm-input"]').setValue('delete')
      await w.get('[data-testid="account-delete-cancel"]').trigger('click')
      expect(w.find('[data-testid="account-delete-confirm-input"]').exists()).toBe(false)

      await w.get('[data-testid="account-delete-open"]').trigger('click')
      expect(w.get('[data-testid="account-delete-confirm-input"]').element.value).toBe('')
    })

    it('success clears the user store, signs out, toasts and routes to login', async () => {
      deleteAccount.mockResolvedValue(undefined)
      const w = mountAuthed()
      await flushPromises()
      const user = useUserStore()
      const auth = useAuthStore()
      const clearSpy = vi.spyOn(user, 'clearForAccountDeletion')
      const signOutSpy = vi.spyOn(auth, 'signOut').mockResolvedValue()

      await w.get('[data-testid="account-delete-open"]').trigger('click')
      await w.get('[data-testid="account-delete-confirm-input"]').setValue('delete')
      await w.get('[data-testid="account-delete-submit"]').trigger('click')
      await flushPromises()

      expect(deleteAccount).toHaveBeenCalled()
      expect(clearSpy).toHaveBeenCalled()
      expect(signOutSpy).toHaveBeenCalled()
      expect(showSuccess).toHaveBeenCalledWith('Your account has been deleted.')
      expect(routerPush).toHaveBeenCalledWith({ name: 'login' })
    })

    it('failure keeps the dialog open, shows the detail, and does not sign out', async () => {
      deleteAccount.mockRejectedValue(
        new ApiError(503, { detail: 'auth admin not configured' }, '/me'),
      )
      const w = mountAuthed()
      await flushPromises()
      const auth = useAuthStore()
      const signOutSpy = vi.spyOn(auth, 'signOut')

      await w.get('[data-testid="account-delete-open"]').trigger('click')
      await w.get('[data-testid="account-delete-confirm-input"]').setValue('delete')
      await w.get('[data-testid="account-delete-submit"]').trigger('click')
      await flushPromises()

      expect(w.find('[data-testid="account-delete-dialog"]').exists()).toBe(true)
      const notConfigured = w.get('[data-testid="account-delete-error"]').text()
      expect(notConfigured).toContain('not available right now')
      expect(notConfigured).toContain('Nothing was removed')
      expect(notConfigured).not.toContain('auth admin not configured')
      expect(signOutSpy).not.toHaveBeenCalled()
      expect(routerPush).not.toHaveBeenCalled()
    })

    it('the auth-removal 503 detail renders a retry-invite sentence, not the raw detail', async () => {
      deleteAccount.mockRejectedValue(
        new ApiError(503, { detail: 'app data deleted; auth user removal failed' }, '/me'),
      )
      const w = mountAuthed()
      await flushPromises()

      await w.get('[data-testid="account-delete-open"]').trigger('click')
      await w.get('[data-testid="account-delete-confirm-input"]').setValue('delete')
      await w.get('[data-testid="account-delete-submit"]').trigger('click')
      await flushPromises()

      const text = w.get('[data-testid="account-delete-error"]').text()
      expect(text).toContain('Try again')
      expect(text).toContain('contact support')
      expect(text).not.toContain('auth user removal failed')
    })

    it('signs out before routing to login on success (order matters)', async () => {
      deleteAccount.mockResolvedValue(undefined)
      const w = mountAuthed()
      await flushPromises()
      const auth = useAuthStore()
      const signOutSpy = vi.spyOn(auth, 'signOut').mockResolvedValue()

      await w.get('[data-testid="account-delete-open"]').trigger('click')
      await w.get('[data-testid="account-delete-confirm-input"]').setValue('delete')
      await w.get('[data-testid="account-delete-submit"]').trigger('click')
      await flushPromises()

      expect(signOutSpy).toHaveBeenCalled()
      expect(routerPush).toHaveBeenCalled()
      expect(signOutSpy.mock.invocationCallOrder[0]).toBeLessThan(
        routerPush.mock.invocationCallOrder[0],
      )
    })

    it('still toasts and routes to login when signOut rejects after a successful delete', async () => {
      deleteAccount.mockResolvedValue(undefined)
      const w = mountAuthed()
      await flushPromises()
      const auth = useAuthStore()
      vi.spyOn(auth, 'signOut').mockRejectedValue(new Error('network'))

      await w.get('[data-testid="account-delete-open"]').trigger('click')
      await w.get('[data-testid="account-delete-confirm-input"]').setValue('delete')
      await w.get('[data-testid="account-delete-submit"]').trigger('click')
      await flushPromises()

      expect(showSuccess).toHaveBeenCalledWith('Your account has been deleted.')
      expect(routerPush).toHaveBeenCalledWith({ name: 'login' })
    })

    it('Escape (Dialog emitting update:visible(false)) resets the input and error', async () => {
      deleteAccount.mockRejectedValue(
        new ApiError(503, { detail: 'auth admin not configured' }, '/me'),
      )
      const w = mountAuthed()
      await flushPromises()

      await w.get('[data-testid="account-delete-open"]').trigger('click')
      await w.get('[data-testid="account-delete-confirm-input"]').setValue('delete')
      await w.get('[data-testid="account-delete-submit"]').trigger('click')
      await flushPromises()
      expect(w.get('[data-testid="account-delete-error"]').text()).toContain(
        'not available right now',
      )

      // Drive the same event the Dialog stub emits on Escape / outside-click.
      const dialog = w.findComponent(DialogStub)
      await dialog.vm.$emit('update:visible', false)
      await flushPromises()

      expect(w.find('[data-testid="account-delete-dialog"]').exists()).toBe(false)
      await w.get('[data-testid="account-delete-open"]').trigger('click')
      expect(w.get('[data-testid="account-delete-confirm-input"]').element.value).toBe('')
      expect(w.find('[data-testid="account-delete-error"]').exists()).toBe(false)
    })

    it('while a delete request is in flight, Cancel does nothing', async () => {
      let resolveDelete
      deleteAccount.mockReturnValue(
        new Promise((resolve) => {
          resolveDelete = resolve
        }),
      )
      const w = mountAuthed()
      await flushPromises()

      await w.get('[data-testid="account-delete-open"]').trigger('click')
      await w.get('[data-testid="account-delete-confirm-input"]').setValue('delete')
      await w.get('[data-testid="account-delete-submit"]').trigger('click')
      await flushPromises()

      // Request is still pending -- the dialog must still be open and the
      // input must still hold its value; Cancel is a no-op while busy.
      await w.get('[data-testid="account-delete-cancel"]').trigger('click')
      expect(w.find('[data-testid="account-delete-dialog"]').exists()).toBe(true)
      expect(w.get('[data-testid="account-delete-confirm-input"]').element.value).toBe('delete')

      resolveDelete(undefined)
      await flushPromises()
    })
  })
})
