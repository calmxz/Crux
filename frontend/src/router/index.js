import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '../stores/auth.js'
import { useUserStore } from '../stores/user.js'
import {
  start as progressStart,
  finish as progressFinish,
  fail as progressFail,
} from '../services/routeProgress.js'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true, sidebar: false },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/RegisterView.vue'),
      meta: { public: true, sidebar: false },
    },
    {
      path: '/forgot',
      name: 'forgot-password',
      component: () => import('../views/ForgotPasswordView.vue'),
      meta: { public: true, sidebar: false },
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: () => import('../views/ResetPasswordView.vue'),
      meta: { public: true, sidebar: false },
    },
    {
      path: '/tos',
      name: 'tos',
      component: () => import('../views/LegalView.vue'),
      props: { doc: 'tos' },
      meta: { public: true, sidebar: false },
    },
    {
      path: '/privacy',
      name: 'privacy',
      component: () => import('../views/LegalView.vue'),
      props: { doc: 'privacy' },
      meta: { public: true, sidebar: false },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
    },
    {
      path: '/onboarding',
      name: 'onboarding',
      component: () => import('../views/OnboardingView.vue'),
      meta: { sidebar: false },
    },
    {
      path: '/settings',
      redirect: { name: 'settings', params: { tab: 'learning' } },
    },
    {
      path: '/settings/:tab',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
      props: true,
      beforeEnter: (to) => {
        // Account moved to its own route (2026-09-23): the old Account tab
        // URL redirects there instead of resolving as a Settings tab.
        if (to.params.tab === 'account') {
          return { name: 'account' }
        }

        const valid = ['learning', 'usage', 'appearance']

        if (!valid.includes(to.params.tab)) {
          return { name: 'settings', params: { tab: 'learning' } }
        }
      },
    },
    {
      // The aggregate learner profile across every session (#362, shaped in
      // #358). Replaces the interim redirect to the Learning tab.
      path: '/profile',
      name: 'profile-aggregate',
      component: () => import('../views/AggregateProfileView.vue'),
    },
    {
      // Account moved out of Settings and into its own page (2026-09-23):
      // name, read-only email and password live here now.
      path: '/account',
      name: 'account',
      component: () => import('../views/AccountView.vue'),
    },
    {
      // Unified into Home (2026-08-02): one canonical start experience.
      // Redirect kept so old links and the sidebar name keep working.
      path: '/new',
      name: 'new-session',
      redirect: { name: 'home' },
    },
    {
      path: '/recall',
      name: 'recall',
      component: () => import('../views/RecallView.vue'),
    },
    {
      // Renamed to Recall (#352). Redirect kept so old links keep working.
      path: '/review',
      redirect: { name: 'recall' },
    },
    {
      path: '/sessions',
      name: 'sessions-library',
      component: () => import('../views/SessionsLibraryView.vue'),
    },
    {
      path: '/session/:id',
      name: 'session',
      component: () => import('../views/SessionView.vue'),
      props: true,
      // The session is one full-width sheet: no centred column cap, no
      // horizontal page padding.
      meta: { sheet: true },
    },
    {
      path: '/session/:id/profile',
      name: 'session-profile',
      component: () => import('../views/ProfileView.vue'),
      props: true,
    },
    {
      // Catch-all, last by definition. Public so a logged-out visitor lands on
      // the page rather than a login redirect. Like every other public route it
      // drops the shell: App.vue does not auth-gate the sidebar, so leaving it
      // on would draw the session rail for an anonymous visitor.
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('../views/NotFoundView.vue'),
      meta: { public: true, sidebar: false },
    },
  ],
})

router.beforeEach(() => {
  progressStart()
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // If auth store hasn't booted yet (first navigation in tests/dev), do it
  // now so the guard has a deterministic answer.
  if (!auth.ready) {
    try {
      await auth.init()
    } catch {
      // F-14: a failed init means no session - proceed unauthenticated;
      // the guard below routes to /login.
    }
  }

  const isPublic = to.meta?.public === true

  if (!auth.isAuthenticated && !isPublic) {
    // F-49: carry the intended path through login so a deep link survives.
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (auth.isAuthenticated && (to.name === 'login' || to.name === 'register')) {
    return { name: 'home' }
  }

  const user = useUserStore()

  if (auth.isAuthenticated && !user.hydrated) {
    // F-46: onboarding truth lives on the server; the localStorage snapshot
    // is only a warm cache. Await one hydrate so a new device does not
    // force-route an existing user to onboarding. When the snapshot already
    // says onboarding is complete, the answer cannot get worse by waiting --
    // render immediately and refresh in the background instead of spending a
    // full round trip on the first paint.
    if (user.onboardingComplete) {
      user.hydrateFromServer()
    } else {
      await user.hydrateFromServer()
    }
  }

  if (
    auth.isAuthenticated &&
    !user.onboardingComplete &&
    !user.hydrateFailed &&
    to.name !== 'onboarding' &&
    to.name !== 'reset-password'
  ) {
    return { name: 'onboarding' }
  }

  if (user.onboardingComplete && to.name === 'onboarding' && to.query.retake !== '1') {
    return { name: 'home' }
  }
})

router.afterEach((to, from, failure) => {
  // F-08: SPA route swaps leave keyboard/SR focus on a removed node. Reset
  // to the main landmark on real navigations (skip the initial load so we
  // don't steal focus from the address bar / skip-link).
  if (failure || !from.name) return

  if (typeof document === 'undefined') return
  const el = document.getElementById('main-content')

  // D-15: a missing target used to fail silently, which is how the chrome-less
  // routes went unnoticed. App.vue now gives both branches the id; say so in
  // dev if a new layout ever drops it again.
  if (!el) {
    if (import.meta.env.DEV) {
      console.warn('[router] focus target #main-content not found for', to.path)
    }

    return
  }

  el.focus()
})

router.afterEach(() => {
  progressFinish()
})

router.onError(() => {
  progressFail()
})

export default router
