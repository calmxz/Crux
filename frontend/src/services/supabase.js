// Lazy singleton Supabase client. Reads VITE_SUPABASE_URL +
// VITE_SUPABASE_PUBLISHABLE_KEY at runtime. Tests mock '@supabase/supabase-js'
// via the global setup file in src/__tests__/setup.js, so importing this
// module in a test environment yields a stub client that doesn't touch the
// network.

import { createClient } from '@supabase/supabase-js'

let _client = null

export function getSupabase() {
  if (_client) return _client
  const url = import.meta.env.VITE_SUPABASE_URL
  const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

  if (!url || !key) {
    // Construct a no-op client in dev when env vars are not provided yet.
    // The auth store will report unauthenticated state and the guard will
    // redirect to /login. Any auth attempt will fail loudly — which is what
    // we want during the env-not-configured window.
    _client = createClient('http://placeholder.invalid', 'placeholder-publishable-key')

    return _client
  }

  _client = createClient(url, key, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  })

  return _client
}

export function _resetSupabaseClientForTests() {
  _client = null
}
