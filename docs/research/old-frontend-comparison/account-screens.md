# The account screens' modules against the old frontend

Part of [the old frontend comparison](../old-frontend-comparison.md) (#768). The modules are the ones in [`account-screens.md`](../../spec/account-screens.md) (Frontend modules). Old paths are under `frontend/src/`. The size key and the sizing rule are in the index.

## Sign-in

- **Old code:** `views/LoginView.vue` (email and password, "Forgot password?"), `RegisterView.vue` (email, password twice, one consent box), `ForgotPasswordView.vue`, `ResetPasswordView.vue`, `components/auth/AuthCover.vue`, `lib/authErrors.js`, and `stores/auth.js`, which calls Supabase Auth from the browser (`services/supabase.js`).
- **Matches:** a page of its own with one centred card and no app around it ([`account-screens.md`](../../spec/account-screens.md), Signing in).
- **Differs:**
  - Passwords, reset links and confirmation emails, against "There is no password, no emailed sign-in link and no other provider" ([`accounts.md`](../../spec/accounts.md), Ways in).
  - The browser talks to Supabase, against "Supabase never sees the browser" ([`hosting.md`](../../spec/hosting.md), The database).
  - Sign-in and sign-up are two pages, against one page that serves both.
  - An error shows in one line under the form, against each message under the button or field it is about (Messages).
  - One box, "I agree to the Terms of Service and Privacy Policy", at sign-up, against "One more thing" with two required ticks after the code or Google ([`accounts.md`](../../spec/accounts.md), New learners).
- **Missing:** "Continue with Google"; the code step with its boxes, "Send a new code" and "Use another email"; the human check; every message in the Messages table; "Crux is full for now"; the misuse block's card; the note after closing; the trial-time refusal ([`landing-screens.md`](../../spec/landing-screens.md), Signing in during the trial).
- **Stack:** `@supabase/supabase-js` in the browser, and a bearer token on each call.
- **Size:** Large: the way in is replaced.

## Opening steps

- **Old code:** the router guard in `router/index.js` sends a signed-in learner to `views/OnboardingView.vue` until onboarding is complete. Onboarding asks "What we call you" and "When you get stuck".
- **Matches:** a guard that puts a step before the app, on a page without the shell.
- **Differs:** the step asks for a name and a feedback style, against "No name is asked or kept" ([`accounts.md`](../../spec/accounts.md), What an account holds about the person).
- **Missing:** the opening page and its order; the lock page with "Read my sessions"; "Keep my account" with its feedback list; the terms step; the under-18 closure; the lock bar and the read-only states with their greyed items ([`account-screens.md`](../../spec/account-screens.md), Steps on opening; A locked account).
- **Stack:** vue-router's `beforeEach`, and the Pinia user store reading `GET /me`.
- **Size:** Large: none of the steps exists; only the routing pattern does.

## Settings

- **Old code:** `views/SettingsView.vue` with three tabs: Learning (`components/settings/LearningTab.vue`), Usage (`UsageTab.vue` and `components/profile/UsagePanel.vue`) and Appearance (`AppearanceTab.vue`). `views/AccountView.vue` is its own page: display name, email, password change, "Export your data", and "Delete account" with "Type delete to confirm". Sign out is in the sidebar's account menu.
- **Matches:** the email shown; an account delete behind a dialog where the learner types "delete"; Sign out ([`account-screens.md`](../../spec/account-screens.md), The Settings page; Closing an account).
- **Differs:**
  - Usage shows dollars spent today against soft, urgent and hard caps, against "Today's tutoring: 70% used" with the week under it, and "A learner never sees money" ([`spending.md`](../../spec/spending.md), Seeing the limit).
  - Learning offers fixed choices, including "Direct answers: Explain outright when I ask", against preferences the learner states and removes in the panel ([`teaching.md`](../../spec/teaching.md), Preferences), and "Crux gives no bare answers" ([`learning-loop.md`](../../spec/learning-loop.md), A single problem).
  - Delete erases at once, against a closing with 7 days to keep the account ([`privacy.md`](../../spec/privacy.md), Closing an account). The typed word must be lower case, against "in any case".
  - Export downloads a file at once, against "Send me a copy first", which emails a link on the closing day.
  - The tabs and the separate Account page are not the spec's one page of four parts.
- **Missing:** the Files part with "See your files"; the Your feedback part with its ticks to untick; the Terms, Privacy Policy and "Who runs Crux" links; the trial link's part with "Erase this trial link"; the close-account dialog's wording.
- **Stack:** Vue, PrimeVue `Dialog`, and Supabase Auth for the password change.
- **Size:** Large: two of the four parts are missing, and the other two differ.

## Feedback

- **Old code:** none.
- **Missing:** the feedback page with its four questions and counters, the three ticks, the share list and its warning, the 5-a-day stop, the sent state, and the sidebar link hidden during a check ([`account-screens.md`](../../spec/account-screens.md), The feedback page; [`feedback.md`](../../spec/feedback.md)).
- **Size:** Large: nothing exists.
