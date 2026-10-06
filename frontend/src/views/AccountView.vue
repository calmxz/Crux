<template>
  <section class="account" data-testid="account">
    <header class="head">
      <h1 class="title">Account</h1>
    </header>

    <div class="panel" data-testid="settings-account">
      <form class="form" @submit.prevent="save">
        <section class="sec">
          <h2 class="sec-title">Account</h2>
          <div class="field">
            <label class="lbl" for="set-name">Display name</label>
            <input
              id="set-name"
              v-model="displayName"
              data-testid="settings-name"
              maxlength="40"
              class="input"
              type="text"
              placeholder="Learner"
            />
            <p class="hint">How the tutor refers to you.</p>
          </div>
          <div class="field" data-testid="account-email">
            <span class="lbl">Email</span>
            <p class="static">{{ emailDisplay }}</p>
          </div>
        </section>

        <div class="btn-fill-row">
          <button
            type="submit"
            class="btn-fill"
            :class="{ 'btn-fill--busy': saving }"
            data-testid="settings-save"
            :disabled="!dirty || saving"
          >
            Save name
          </button>
          <span v-if="savedFlash" class="saved-flash" data-testid="settings-saved">
            <svg
              class="tick"
              viewBox="0 0 12 12"
              width="12"
              height="12"
              aria-hidden="true"
              focusable="false"
            >
              <path :d="TICK_PATH" />
            </svg>
            Saved.
          </span>
        </div>

        <p v-if="saveError" class="error" role="alert" data-testid="settings-error">
          {{ saveError }}
        </p>
      </form>

      <section v-if="authStore.isAuthenticated" class="sec" data-testid="settings-security">
        <h2 class="sec-title">Security</h2>
        <form class="pw-form" @submit.prevent="changePassword">
          <div class="field">
            <label class="lbl" for="pw-current">Current password</label>
            <input
              id="pw-current"
              v-model="pwCurrent"
              data-testid="settings-pw-current"
              class="input"
              type="password"
              autocomplete="current-password"
            />
          </div>
          <div class="field">
            <label class="lbl" for="pw-new">New password</label>
            <input
              id="pw-new"
              v-model="pwNew"
              data-testid="settings-pw-new"
              class="input"
              type="password"
              autocomplete="new-password"
              placeholder="At least 8 characters"
            />
          </div>
          <div class="field">
            <label class="lbl" for="pw-confirm">Confirm new password</label>
            <input
              id="pw-confirm"
              v-model="pwConfirm"
              data-testid="settings-pw-confirm"
              class="input"
              type="password"
              autocomplete="new-password"
            />
          </div>
          <p v-if="pwMismatch" class="hint" data-testid="settings-pw-mismatch">
            New passwords do not match.
          </p>
          <p v-if="pwError" class="error" role="alert" data-testid="settings-pw-error">
            {{ pwError }}
          </p>
          <div class="btn-fill-row">
            <button
              type="submit"
              class="btn-fill"
              :class="{ 'btn-fill--busy': pwSubmitting }"
              data-testid="settings-pw-submit"
              :disabled="!pwCanSubmit || pwSubmitting"
            >
              {{ pwSubmitting ? 'Updating…' : 'Update password' }}
            </button>
            <span
              v-if="pwSuccess"
              class="saved-flash"
              role="status"
              data-testid="settings-pw-success"
            >
              <svg
                class="tick"
                viewBox="0 0 12 12"
                width="12"
                height="12"
                aria-hidden="true"
                focusable="false"
              >
                <path :d="TICK_PATH" />
              </svg>
              Password updated.
            </span>
          </div>
        </form>
      </section>

      <section v-if="authStore.isAuthenticated" class="sec" data-testid="account-export">
        <h2 class="sec-title">Export your data</h2>
        <p class="export-copy">
          Download your sessions, messages, check answers, topic profiles, upload list, and
          preferences as one JSON file. Uploaded PDFs are not included.
        </p>
        <div class="btn-fill-row">
          <button
            type="button"
            class="btn-fill"
            :class="{ 'btn-fill--busy': exportBusy }"
            data-testid="account-export-btn"
            :disabled="exportBusy"
            @click="downloadExport"
          >
            {{ exportBusy ? 'Preparing…' : 'Download my data' }}
          </button>
        </div>
        <p v-if="exportError" class="error" role="alert" data-testid="account-export-error">
          {{ exportError }}
        </p>
      </section>

      <section v-if="authStore.isAuthenticated" class="sec sec-danger" data-testid="account-danger">
        <h2 class="sec-title">Delete account</h2>
        <p class="danger-copy">
          Deleting your account permanently erases your sessions, topic profiles, uploaded files,
          learning history, and the sign-in itself. This cannot be undone.
        </p>
        <button
          type="button"
          class="danger-open-btn"
          data-testid="account-delete-open"
          @click="openDeleteDialog"
        >
          Delete account
        </button>
      </section>
    </div>

    <Dialog
      :visible="deleteDialogOpen"
      modal
      header="Delete account"
      class="crux-dialog"
      :style="{ width: 'min(28rem, calc(100vw - 2rem))' }"
      data-testid="account-delete-dialog"
      :closable="!deleteBusy"
      :close-on-escape="!deleteBusy"
      @update:visible="handleDialogVisible"
    >
      <p class="danger-copy">
        This permanently erases your sessions, topic profiles, uploaded files, learning history, and
        the sign-in itself. This cannot be undone.
      </p>
      <div class="field">
        <label class="lbl" for="account-delete-confirm">Type delete to confirm</label>
        <input
          id="account-delete-confirm"
          v-model="deleteConfirmText"
          data-testid="account-delete-confirm-input"
          class="input"
          type="text"
          autocomplete="off"
        />
      </div>
      <p v-if="deleteError" class="error" role="alert" data-testid="account-delete-error">
        {{ deleteError }}
      </p>
      <template #footer>
        <button
          type="button"
          class="dialog-cancel-btn"
          data-testid="account-delete-cancel"
          @click="closeDeleteDialog"
        >
          Cancel
        </button>
        <button
          type="button"
          class="p-button p-button-danger confirm-delete-strong danger-submit-btn"
          data-testid="account-delete-submit"
          :disabled="!deleteArmed || deleteBusy"
          @click="submitDelete"
        >
          {{ deleteBusy ? 'Deleting…' : 'Delete my account' }}
        </button>
      </template>
    </Dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Dialog from 'primevue/dialog'

import '@/assets/sheet.css'
import { authErrorCopy } from '@/lib/authErrors.js'
import { friendlyError } from '@/lib/errors.js'
import { useUserStore } from '../stores/user.js'
import { useAuthStore } from '../stores/auth.js'
import { useToast } from '../composables/useToast.js'
import { TICK_PATH } from '../components/chat/levelMark.js'
import { downloadJson } from '@/lib/download.js'
import { deleteAccount, exportData } from '../services/meApi.js'

const user = useUserStore()

const authStore = useAuthStore()

const router = useRouter()

const { showSuccess } = useToast()

// The deep-desk ground must fill the whole routed pane, not just the
// account element -- same mechanism SettingsView uses (a body class painted
// on .page via assets/sheet.css).
onMounted(() => document.body.classList.add('settings-page'))

onUnmounted(() => document.body.classList.remove('settings-page'))

const emailDisplay = computed(() => authStore.userEmail || 'No email')

const displayName = ref(user.name || '')

const savedFlash = ref(false)

const saving = ref(false)

const saveError = ref(null)

const dirty = computed(() => (displayName.value || '').trim() !== (user.name || ''))

async function save() {
  if (!dirty.value || saving.value) return
  saving.value = true
  saveError.value = null

  try {
    await user.updateProfile({ name: displayName.value })
    savedFlash.value = true
    showSuccess('Name saved.')
  } catch (e) {
    // F-11: inline surface (LoginView pattern); the errorBus toast alone
    // left the form frozen with no explanation and an unhandled rejection.
    saveError.value = friendlyError(e)
  } finally {
    saving.value = false
  }
}

watch(displayName, () => {
  savedFlash.value = false
})

const pwCurrent = ref('')

const pwNew = ref('')

const pwConfirm = ref('')

const pwError = ref('')

const pwSuccess = ref(false)

const pwSubmitting = ref(false)

const pwMismatch = computed(() => pwConfirm.value.length > 0 && pwConfirm.value !== pwNew.value)

const pwCanSubmit = computed(
  () => pwCurrent.value.length > 0 && pwNew.value.length >= 8 && pwNew.value === pwConfirm.value,
)

async function changePassword() {
  if (!pwCanSubmit.value) return
  pwError.value = ''
  pwSuccess.value = false
  pwSubmitting.value = true

  try {
    await authStore.signIn(authStore.userEmail, pwCurrent.value)
  } catch {
    pwError.value = 'Current password is incorrect.'
    pwSubmitting.value = false

    return
  }

  try {
    await authStore.updatePassword(pwNew.value)
    pwCurrent.value = ''
    pwNew.value = ''
    pwConfirm.value = ''
    pwSuccess.value = true
    showSuccess('Password updated.')
  } catch (e) {
    // E-13: code-keyed copy, never SDK prose (see lib/authErrors.js).
    pwError.value = authErrorCopy(e, 'Could not update password. Try again.')
  } finally {
    pwSubmitting.value = false
  }
}

const exportBusy = ref(false)

const exportError = ref('')

// #361: fixed copy rather than friendlyError -- its 503 line talks about the
// tutor, which is wrong on this page.
async function downloadExport() {
  if (exportBusy.value) return
  exportBusy.value = true
  exportError.value = ''

  try {
    const data = await exportData()
    // The server's UTC exported_at, so the name matches its Content-Disposition.
    const day = String(data?.exported_at ?? new Date().toISOString()).slice(0, 10)
    downloadJson(data, `crux-export-${day}.json`)
    showSuccess('Your data was downloaded.')
  } catch {
    exportError.value = 'Could not prepare your export. Try again.'
  } finally {
    exportBusy.value = false
  }
}

// R2-22/23/24/25: the 503 the backend returns once app data is already gone
// but the auth user removal failed (docs/api/openapi.yaml `DELETE /api/me`).
// That literal detail string means the delete didn't fully finish -- the
// learner should never see the raw backend prose for it. This constant must
// match backend/routes/me.py's `detail=` string byte for byte or the
// friendly copy below silently stops matching.
const DELETE_AUTH_STEP_DETAIL = 'app data deleted; auth user removal failed'

// Same rule: these two must match backend/routes/me.py byte for byte.
const DELETE_NOT_CONFIGURED_DETAIL = 'auth admin not configured'

const DELETE_CONFLICT_DETAIL = 'account changed during deletion; try again'

const deleteDialogOpen = ref(false)

const deleteConfirmText = ref('')

const deleteBusy = ref(false)

const deleteError = ref('')

// Case-sensitive, trimmed exact match -- "Delete" or "delet" must not arm it.
const deleteArmed = computed(() => deleteConfirmText.value.trim() === 'delete')

function openDeleteDialog() {
  deleteDialogOpen.value = true
}

function closeDeleteDialog() {
  // A request is in flight -- closing now would let the learner reopen and
  // resubmit over it. Dialog is also bound :closable/:close-on-escape=false
  // while busy, so this guard only matters for the Cancel button itself.
  if (deleteBusy.value) return
  deleteDialogOpen.value = false
  deleteConfirmText.value = ''
  deleteError.value = ''
}

// Dialog's own Escape / outside-click handling emits update:visible(false);
// route it through the same reset as Cancel so no path leaves stale state.
function handleDialogVisible(v) {
  if (v) {
    deleteDialogOpen.value = true
  } else {
    closeDeleteDialog()
  }
}

function deleteErrorMessage(e) {
  const detail = e?.body?.detail

  if (typeof detail === 'string' && detail) {
    if (detail === DELETE_AUTH_STEP_DETAIL) {
      // The backend delete is idempotent, so a retry can finish the job
      // without support -- only point the learner at support if it keeps failing.
      return (
        'Your data was removed but the sign-in could not be deleted. ' +
        'Try again, or contact support if this keeps happening.'
      )
    }

    if (detail === DELETE_NOT_CONFIGURED_DETAIL) {
      return 'Account deletion is not available right now. Nothing was removed. Contact support.'
    }

    if (detail === DELETE_CONFLICT_DETAIL) {
      return 'Something was still being saved to your account. Nothing was removed. Try again in a moment.'
    }

    return detail
  }

  return friendlyError(e) || 'Could not delete your account. Try again.'
}

async function submitDelete() {
  if (!deleteArmed.value || deleteBusy.value) return
  deleteBusy.value = true
  deleteError.value = ''

  try {
    await deleteAccount()
    user.clearForAccountDeletion()

    try {
      await authStore.signOut()
    } catch {
      // The auth user is already gone server-side by this point; a local
      // signOut failure must not strand the learner mid-delete.
    }

    showSuccess('Your account has been deleted.')
    router.push({ name: 'login' })
  } catch (e) {
    // Keep the dialog open and do NOT sign out -- the account may still be
    // fully intact (e.g. 503 with no key configured, nothing deleted).
    deleteError.value = deleteErrorMessage(e)
  } finally {
    deleteBusy.value = false
  }
}
</script>

<style scoped>
.account {
  display: flex;
  flex-direction: column;
}

.head {
  display: flex;
  flex-direction: column;
  padding-bottom: var(--line-pitch);
}

.title {
  font-family: var(--font-display);
  font-size: var(--fs-h1);
  font-weight: 600;
  letter-spacing: var(--tracking-display);
  line-height: var(--lh-display);
  color: var(--ink);
  margin: 0;
}

.form {
  display: flex;
  flex-direction: column;
}

/* Card shell, .sec-title, .saved-flash and .tick come from assets/sheet.css
   (shared with SettingsView's .panel); only this page's own alignment is
   declared here. */
.sec {
  align-items: flex-start;
  gap: 0.5rem;
}

.field {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 28rem;
}

.lbl {
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--line-pitch);
  color: var(--pencil);
}

/* Field on a rule: no box, one bottom rule that inks up on focus. */
.input {
  width: 100%;
  padding: 0;
  border: 0;
  border-bottom: 1px solid var(--rule-strong);
  border-radius: 0;
  background: transparent;
  color: var(--ink-learner);
  caret-color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: calc(var(--line-pitch) - 1px);
}

.input::placeholder {
  color: var(--pencil);
}

.input:focus {
  outline: none;
  border-bottom-color: var(--ink-learner);
}

/* Read-only email line: same rule-on-a-line look as .input but static text,
   not a field. */
.static {
  margin: 0;
  padding-bottom: 1px;
  border-bottom: 1px solid var(--rule-strong);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: calc(var(--line-pitch) - 1px);
}

.hint {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-label);
  line-height: var(--line-pitch);
  color: var(--pencil);
}

.error {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  line-height: var(--line-pitch);
  color: var(--ink-marker-text);
}

.pw-form {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
}

.export-copy,
.danger-copy {
  margin: 0;
  font-family: var(--font-sans);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  color: var(--ink);
}

/* Marks the whole delete-account section as the danger zone: its own
   .sec-title (shared rule in assets/sheet.css) reads text-safe red here
   instead of the default heading ink. */
.sec-danger .sec-title {
  color: var(--ink-marker-text);
}

/* Text-safe red, underlined like the other in-card text buttons (see
   ProfileView's .text-btn) but never set on the delete confirm itself --
   that stays the shared .confirm-delete-strong filled control. */
.danger-open-btn {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--ink-marker-text);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  line-height: var(--lh-body);
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}

.danger-open-btn:hover {
  color: var(--ink-marker-text-hover);
}

.dialog-cancel-btn {
  padding: 0.5rem 1rem;
  border: 0;
  background: transparent;
  color: var(--ink-learner);
  font-family: var(--font-sans);
  font-size: var(--fs-caption);
  font-weight: 700;
  cursor: pointer;
}

.dialog-cancel-btn:hover {
  color: var(--color-accent-hover);
}

.danger-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
