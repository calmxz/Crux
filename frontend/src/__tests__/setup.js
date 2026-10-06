// Global vitest setup. Mocks `@supabase/supabase-js` so importing
// `services/supabase.js` in any test never touches the network.
//
// Tests can refine the default behavior by accessing
// `globalThis.__supabaseAuthStub` and calling .mockResolvedValueOnce(...)
// on individual stub methods.

import { vi, beforeEach } from 'vitest'

const authStub = {
  getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
  onAuthStateChange: vi.fn().mockReturnValue({
    data: { subscription: { unsubscribe: vi.fn() } },
  }),
  signUp: vi.fn().mockResolvedValue({
    data: { user: { id: 'u-new', email: 'new@example.com' }, session: null },
    error: null,
  }),
  signInWithPassword: vi.fn().mockResolvedValue({
    data: { session: { access_token: 'tok', user: { id: 'u-1' } } },
    error: null,
  }),
  resend: vi.fn().mockResolvedValue({ data: {}, error: null }),
  signOut: vi.fn().mockResolvedValue({ error: null }),
  resetPasswordForEmail: vi.fn().mockResolvedValue({ data: {}, error: null }),
  updateUser: vi.fn().mockResolvedValue({
    data: { user: { id: 'u-1' } },
    error: null,
  }),
}

vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => ({ auth: authStub })),
}))

globalThis.__supabaseAuthStub = authStub

// jsdom has no layout, so its window.scrollTo only logs "Not implemented".
// SessionView scrolls the document (#346); tests that care spy on this.
if (typeof window !== 'undefined') window.scrollTo = () => {}

beforeEach(() => {
  authStub.getSession.mockClear()
  authStub.getSession.mockResolvedValue({ data: { session: null }, error: null })
  authStub.onAuthStateChange.mockClear()
  authStub.signUp.mockClear()
  authStub.signUp.mockResolvedValue({
    data: { user: { id: 'u-new', email: 'new@example.com' }, session: null },
    error: null,
  })
  authStub.signInWithPassword.mockClear()
  authStub.signInWithPassword.mockResolvedValue({
    data: { session: { access_token: 'tok', user: { id: 'u-1' } } },
    error: null,
  })
  authStub.resend.mockClear()
  authStub.resend.mockResolvedValue({ data: {}, error: null })
  authStub.signOut.mockClear()
  authStub.signOut.mockResolvedValue({ error: null })
  authStub.resetPasswordForEmail.mockClear()
  authStub.resetPasswordForEmail.mockResolvedValue({ data: {}, error: null })
  authStub.updateUser.mockClear()
  authStub.updateUser.mockResolvedValue({ data: { user: { id: 'u-1' } }, error: null })
})
