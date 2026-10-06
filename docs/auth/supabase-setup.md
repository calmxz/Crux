# Supabase Auth Setup

Crux uses Supabase Auth with email + password sign-in. This doc is the
end-to-end setup path for a fresh Supabase project, the env vars the app
reads, and the JWT verification model.

## 1. Create the Supabase project

1. Sign up / sign in at <https://supabase.com>.
2. New project → free tier. Region close to you (e.g. `Southeast Asia (Singapore)`).
3. Database password: generate + store. You will not need it for the app
   (the app authenticates with the secret API key, not the password) but
   you need it for direct `psql` access from `docs/db/postgres-pgvector-setup.md`.
4. Wait for provisioning to finish (~1-2 min).

## 2. Enable Email + password

`Authentication → Providers → Email`:

- **Enable** Email provider.
- **Enable** "Email + Password" sign-in (password provider ON).
- **Confirm email**: ON — new self-service registrations must confirm via the
  emailed link before first sign-in.
- **Secure email change**: ON.
- Magic-link / OTP-only sign-in: not used by the app (the app calls
  `signUp` / `signInWithPassword`). The OTP toggle can stay at its default.

`Authentication → URL Configuration`:

- **Site URL**: `http://localhost:5173` for dev; the Vercel frontend URL in
  production (see `docs/deploy/RUNBOOK.md`).
- **Redirect URLs**: add `http://localhost:5173/**` for dev. The confirmation
  link redirects back here and `supabase-js` (`detectSessionInUrl: true`)
  completes the session.

Disable every other provider (GitHub, Google, etc.) under `Providers`.

### Debug accounts (pre-confirmed)

Real registrations require email confirmation. For local debugging, create
pre-confirmed accounts that skip the inbox step:

1. Copy `docs/dev/debug-accounts.example.txt` to `docs/dev/debug-accounts.txt`
   (gitignored) and set throwaway dev credentials.
2. From `backend/`, run `python scripts/seed_debug_accounts.py`. It calls the
   GoTrue Admin API with `email_confirm: true` using `SUPABASE_SECRET_KEY`
   (backend-only) and is idempotent. The seeded accounts log in via the normal
   `/login` form.

## 3. Collect the four env vars

Crux uses Supabase's **2025+ API key model** — `publishable` (frontend)
+ `secret` (backend). Legacy `anon` + `service_role` keys are not used.
Enable the new keys at `Project Settings → API Keys` and rotate the legacy
keys off after migration.

`Project Settings → API Keys`:

| Env var | Where in Supabase | Used by |
|---|---|---|
| `SUPABASE_URL` | `Project URL` (under `Project Settings → API`) | backend + frontend |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | `API Keys → Publishable` (`sb_publishable_…`) | frontend |
| `SUPABASE_SECRET_KEY` | `API Keys → Secret` (`sb_secret_…`) | backend only — never ship to client |
| `DATABASE_URL` | `Project Settings → Database → Connection string → URI (pooler)` | backend |

Notes:
- `SUPABASE_SECRET_KEY` is **secret** — bypasses RLS. Backend-only. Treat
  rotation like the old `service_role` key: dashboard → API Keys → Roll.
- The publishable key is safe to ship in the frontend bundle by design.
- `DATABASE_URL` from the **pooler** (port 6543, mode `transaction`). The
  direct connection (port 5432) is fine for migrations but the pooler is what
  the app uses at runtime.

## 4. Populate `.env`

Backend (`.env` at repo root, gitignored):

```dotenv
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SECRET_KEY=sb_secret_<...>
DATABASE_URL=postgresql+psycopg://postgres.<ref>:<password>@<region>.pooler.supabase.com:6543/postgres
# Local default; the Render blueprint pins lower values, see docs/reference.md.
LLM_SOFT_CAP_USD=2.00
LLM_HARD_CAP_USD=3.00
```

Frontend (`frontend/.env.local`, gitignored):

```dotenv
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_<...>
```

`.env.example` files in each location already document the placeholders;
fill in real values locally, never commit.

## 5. How verification works

- Frontend: `frontend/src/services/supabase.js` exposes a lazy singleton
  `@supabase/supabase-js` client. `frontend/src/stores/auth.js` calls
  `supabase.auth.signUp` (registration) and `supabase.auth.signInWithPassword`
  (login) from `RegisterView.vue` / `LoginView.vue`. On email confirmation the
  link redirects back to the app; `supabase-js` parses the URL and emits a
  `SIGNED_IN` event, which the auth store consumes.
- Every API call carries `Authorization: Bearer <access_token>`, injected by
  `frontend/src/services/apiClient.js` and `uploadApi.js` from the auth store.
- Backend: `backend/services/auth.py` fetches and caches the Supabase JWKS
  (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`), then verifies the JWT
  signature, `exp`, and `aud` on every request. Returns the `sub` claim as
  `user_id`.
  FastAPI dependency `current_user_id` raises `401` on any failure mode.
- All routes in `backend/routes/*` take `user_id: str = Depends(current_user_id)`.
  No route accepts a client-provided `user_id` any longer; H-4 closed.

## 6. RLS — not used

Supabase Postgres ships with Row Level Security available. Crux does
**not** enable RLS. The backend uses `SUPABASE_SECRET_KEY` (or a direct
`DATABASE_URL`) which bypasses RLS, and enforces ownership in application
code via the `current_user_id` dependency + `session.user_id` checks already
present in routes. Reasons:

- A single trust boundary (the backend) is easier to reason about than two
  (backend + RLS policies).
- ORM-level filtering already proved correct in Phase 6 regression tests
  (`test_session_isolation.py`, etc.).
- pgvector queries are app-side and don't benefit from RLS.

If you ever expose the database to direct client connections (e.g. Supabase
JS client doing direct table reads), revisit this and enable RLS.

## 7. Local dev shortcut

For local dev you don't strictly need a Supabase project — the frontend's
`getSupabase()` falls back to a placeholder URL so the module imports, and
the backend test suite injects a fake `current_user_id` via dependency
override (`backend/tests/conftest.py`). Live auth flows obviously need real
values from §3.

## Password reset + change password

The forgot-password flow uses GoTrue's recovery email. For the emailed link to
land correctly, allowlist the redirect target in the Supabase dashboard:

- Dashboard -> Authentication -> URL Configuration -> Redirect URLs, add:
  - `http://localhost:5173/reset-password` (dev)
  - `https://<your-prod-host>/reset-password` (prod)

Flows:
- **Forgot password:** `/forgot` calls `resetPasswordForEmail(email, { redirectTo:
  <origin>/reset-password })`. The email link lands on `/reset-password`, where
  `detectSessionInUrl` establishes a short-lived recovery session. The user sets
  a new password (`updateUser`), is signed out, and is redirected to
  `/login?reset=1`.
- **Change password (signed in):** Settings -> Security re-verifies the current
  password (`signInWithPassword`) then calls `updateUser({ password })`. The
  session is retained.

No backend or database change is involved -- GoTrue handles email, token, and
password update.

## 8. Session lifetime (token expiry)

The app uses short-lived access tokens (JWT, ~1hr default) backed by a
long-lived refresh token. `persistSession: true` + `autoRefreshToken: true`
(in `frontend/src/services/supabase.js`) keep the user logged in across app
restarts and silently refresh the access token while a tab is open. Explicit
sign-out clears the local session.

To make a session eventually expire (low-sensitivity-app behavior) instead of
living forever while it keeps refreshing, configure the Supabase dashboard:

1. Supabase Dashboard -> Authentication -> Sessions.
2. Set **Inactivity timeout** to **30 days**. A session not refreshed within
   30 days expires. Adjust the value to taste.
3. Leave **Time-box user sessions** (absolute max session duration) **unset**,
   so an actively-used session is never force-logged-out mid-work.
4. Keep **refresh token rotation** enabled (the Supabase default).
5. Leave the **access token (JWT) expiry** at its default (~1hr).

This is dashboard configuration only; there is no corresponding frontend code.
The dashboard state is not version-controlled, so these steps are the
reproducible record.
