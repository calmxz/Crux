// #453 (card refactor 1/6): pins the look of every card surface before the
// global `.card` class replaces the 21 copied boxes (#454-#458). Each move
// must look identical before and after, and a lost cascade tie or a scoped
// rule leaking onto a child root fails nothing else.
//
// For each surface it reads getComputedStyle and compares against values
// recorded from `dev` in the light theme. They are literals on purpose: a
// value computed at test time from the same CSS variables would move with the
// bug. To re-record after an intended visual change, run
//   CARD_LOOK_RECORD=1 npx playwright test e2e/card-look.spec.js
// and paste the printed objects into LOOK.
//
// Like auth.spec.js and mobile-390-check-card.spec.js it runs entirely
// offline: Supabase GoTrue and every /api call are stubbed with page.route,
// so only the Vite dev server is needed. Surfaces are selected by test id,
// role or text, never by a class a later part renames.
//
// Not covered: the loading skeletons (hard to hold on screen; part 6's manual
// look covers them) and the dark theme (same rules, other tokens).
import { test, expect } from '@playwright/test'

const RECORD = !!process.env.CARD_LOOK_RECORD

const DESKTOP = { width: 1366, height: 900 }

const MOBILE = { width: 390, height: 844 }

const BOX_PROPS = [
  'backgroundColor',
  'borderTopColor',
  'borderRightColor',
  'borderBottomColor',
  'borderLeftColor',
  'borderTopWidth',
  'borderRightWidth',
  'borderBottomWidth',
  'borderLeftWidth',
  'borderTopLeftRadius',
  'borderTopRightRadius',
  'borderBottomRightRadius',
  'borderBottomLeftRadius',
  'boxShadow',
  'padding',
]

// The library error line, its Retry and the profile text button have no box,
// so BOX_PROPS alone would pin nothing #457 can break. They also pin the text
// look that the shared `.error-line` / `.text-btn` classes take over.
const TEXT_PROPS = ['color', 'textDecorationLine', 'fontSize']

// Recorded from `dev` (light theme). The shared shapes below are the parts
// whose recorded values were identical across surfaces; each surface adds its
// own padding and any property that differs.
const EDGE = 'rgb(207, 211, 218)'

const DROP = 'rgb(196, 200, 208) 0px 1px 0px 0px'

const ALERT = 'rgb(184, 53, 44)'

const LINK = 'rgb(29, 79, 196)'

// The four border colours always move together.
function edges(color) {
  return {
    borderTopColor: color,
    borderRightColor: color,
    borderBottomColor: color,
    borderLeftColor: color,
  }
}

const CARD = {
  backgroundColor: 'rgb(255, 255, 255)',
  ...edges(EDGE),
  borderTopWidth: '1px',
  borderRightWidth: '1px',
  borderBottomWidth: '1px',
  borderLeftWidth: '1px',
  borderTopLeftRadius: '6px',
  borderTopRightRadius: '6px',
  borderBottomRightRadius: '6px',
  borderBottomLeftRadius: '6px',
  boxShadow: DROP,
}

// Hangs from a tab: square top-left corner.
const JOINED = { ...CARD, borderTopLeftRadius: '0px' }

const LEARNER_EDGE = 'rgb(185, 205, 245)'

const LEARNER = {
  ...CARD,
  backgroundColor: 'rgb(219, 230, 251)',
  ...edges(LEARNER_EDGE),
}

// Notice strip: coloured 3px top edge, square top corners, no drop.
function strip(tab, padding) {
  return {
    ...CARD,
    borderTopColor: tab,
    borderTopWidth: '3px',
    borderTopLeftRadius: '0px',
    borderTopRightRadius: '0px',
    boxShadow: 'none',
    padding,
  }
}

// No box at all: only the text colour shows.
function bare(color, textDecorationLine, fontSize) {
  return {
    backgroundColor: 'rgba(0, 0, 0, 0)',
    ...edges(color),
    borderTopWidth: '0px',
    borderRightWidth: '0px',
    borderBottomWidth: '0px',
    borderLeftWidth: '0px',
    borderTopLeftRadius: '0px',
    borderTopRightRadius: '0px',
    borderBottomRightRadius: '0px',
    borderBottomLeftRadius: '0px',
    boxShadow: 'none',
    padding: '0px',
    color,
    textDecorationLine,
    fontSize,
  }
}

const BUBBLE_PAD = '8.8px 14.4px 11.2px'

const AUTH_LIFT = `${DROP}, rgba(0, 0, 0, 0.25) 0px 12px 24px -12px`

const LOOK = {
  // Login
  authCover: { ...CARD, boxShadow: AUTH_LIFT, padding: '40px' },
  loginStatus: strip(ALERT, '6.4px 12px'),
  // Legal and 404
  legalPage: { ...CARD, padding: '40px' },
  notFound: { ...CARD, padding: '40px' },
  // Home
  homeCover: { ...CARD, padding: '40px 40px 44px' },
  topicIntercept: { ...CARD, padding: '14px 40px 14px 16px' },
  // Library
  libraryRow: { ...CARD, padding: '14px 16px' },
  focusChip: { ...CARD, padding: '2.4px 8px' },
  libraryEmpty: { ...CARD, padding: '32px 28px' },
  libraryError: bare(ALERT, 'none', '17px'),
  libraryRetry: bare(LINK, 'underline', '14px'),
  // Session page
  checkCard: { ...CARD, padding: BUBBLE_PAD },
  recapCard: { ...CARD, padding: BUBBLE_PAD },
  learnerTurn: { ...LEARNER, padding: BUBBLE_PAD },
  composer: {
    ...CARD,
    ...edges('rgb(118, 124, 134)'),
    padding: '8.8px 14.4px',
  },
  cueCard: { ...JOINED, padding: '6.4px 11.2px' },
  sessionEnded: { ...CARD, padding: BUBBLE_PAD },
  topicSuggest: { ...CARD, padding: BUBBLE_PAD },
  levelPicker: { ...CARD, padding: BUBBLE_PAD },
  sessionEmpty: { ...CARD, padding: '16px 20px 19.2px' },
  referenceBanner: strip(LINK, '6.4px 12px'),
  uploadStatus: strip(ALERT, '6.4px 12px'),
  capBanner: strip(ALERT, '6.4px 12px'),
  statusLine: strip(ALERT, '4px 12px'),
  // Recall
  recallSheet: { ...JOINED, padding: '16px' },
  recallCard: { ...LEARNER, padding: '10px 12px' },
  // Focus adds only an outline; this pins that the box does not change, in
  // particular that base.css's :focus-visible radius does not win.
  recallCardFocused: { ...LEARNER, padding: '10px 12px' },
  // Settings and Account
  settingsPanel: { ...JOINED, padding: '24px 32px 32px' },
  accountPanel: { ...CARD, padding: '24px 32px 32px' },
  // Session profile
  profileDivider: { ...JOINED, padding: '20px 24px' },
  profileSection: { ...CARD, padding: '20px 24px' },
  profileConflict: strip(ALERT, '4px 12px'),
  // Aggregate profile
  aggregateTopic: { ...CARD, padding: BUBBLE_PAD },
  textButton: bare(LINK, 'underline', '14px'),
  // Sidebar
  sidebarCurrentRow: { ...CARD, padding: '0px' },
  // 390px
  authCoverMobile: { ...CARD, boxShadow: AUTH_LIFT, padding: '24px' },
  recallSheetMobile: { ...JOINED, padding: '12px' },
  recallCardMobile: { ...LEARNER, padding: '10px 12px' },
  cueCardMobile: { ...JOINED, padding: '6.4px 11.2px' },
  // Edge lines top and bottom only, the lift instead of the drop. The side
  // colours are the text colour, since those borders have no width.
  cueDrawerMobile: {
    backgroundColor: 'rgb(255, 255, 255)',
    borderTopColor: EDGE,
    borderRightColor: 'rgb(27, 27, 26)',
    borderBottomColor: EDGE,
    borderLeftColor: 'rgb(27, 27, 26)',
    borderTopWidth: '1px',
    borderRightWidth: '0px',
    borderBottomWidth: '1px',
    borderLeftWidth: '0px',
    borderTopLeftRadius: '0px',
    borderTopRightRadius: '0px',
    borderBottomRightRadius: '6px',
    borderBottomLeftRadius: '6px',
    boxShadow: 'rgba(0, 0, 0, 0.25) 0px 12px 24px -12px',
    padding: '8px 16px',
  },
}

function readLook(locator, props) {
  return locator.evaluate(
    (el, names) => Object.fromEntries(names.map((n) => [n, getComputedStyle(el)[n]])),
    props,
  )
}

// Polls, so land animations and border transitions settle before the compare.
async function expectLook(name, locator, extra = []) {
  await expect(locator).toHaveCount(1)
  await expect(locator).toBeVisible()
  const props = [...BOX_PROPS, ...extra]

  if (RECORD) {
    await locator.page().waitForTimeout(800)
    console.log(`  ${JSON.stringify(name)}: ${JSON.stringify(await readLook(locator, props))},`)

    return
  }

  expect(LOOK[name], `no recorded look for ${name}`).toBeDefined()
  await expect.poll(() => readLook(locator, props)).toEqual(LOOK[name])
}

// --- Fixtures -------------------------------------------------------------

const SESSION_ID = 's-card-look'

const NOW = '2026-01-01T00:00:00Z'

function message(id, role, content, extra = {}) {
  return { id, role, content, citations: [], created_at: NOW, status: 'complete', ...extra }
}

const RECAP_BATCH = {
  gap: 'proton gradient coupling',
  total: 1,
  set_index: 1,
  set_total: 2,
  items: [
    {
      question: 'What drives ATP synthase?',
      options: ['the proton gradient', 'NADH directly'],
      status: 'answered',
      selected_index: 0,
      correct_index: 0,
      correct: true,
      explanation: 'Protons flow back through it.',
    },
  ],
}

const PENDING_CHECK = {
  gap: 'ATP yield per glucose',
  total: 2,
  current_index: 0,
  set_index: 2,
  set_total: 2,
  items: [
    {
      question: 'How many ATP does one glucose yield through aerobic respiration?',
      options: ['2', '18', '30-32'],
      status: 'pending',
    },
    {
      question: 'Where does the Krebs cycle run?',
      options: ['cytosol', 'matrix'],
      status: 'pending',
    },
  ],
}

function makeProfile(overrides = {}) {
  return {
    knowledge_level: 'intermediate',
    subtopic_levels: { glycolysis: 'intermediate' },
    focus_target_gap: 'ATP yield per glucose',
    confirmed_gaps: [
      { name: 'ATP yield per glucose', evidence_type: 'tested', last_event_at: null },
    ],
    mastered_concepts: [
      { name: 'glycolysis net yield', evidence_type: 'tested', last_event_at: null },
    ],
    last_session_summary: 'Worked through glycolysis.',
    ...overrides,
  }
}

const TURNS = [
  message('m0', 'user', 'How does cellular respiration make ATP?'),
  message('m1', 'assistant', 'Mostly through the electron transport chain.'),
]

function makeSession(overrides = {}) {
  return {
    id: SESSION_ID,
    topic: 'Cellular respiration',
    created_at: NOW,
    ended_at: null,
    pinned: false,
    messages: TURNS,
    has_more_messages: false,
    topic_profile: makeProfile(),
    pending_check: null,
    ...overrides,
  }
}

const LIBRARY_ITEM = {
  id: SESSION_ID,
  topic: 'Cellular respiration',
  ended_at: null,
  pinned: false,
  created_at: NOW,
  last_activity_at: NOW,
  message_count: 2,
  last_message_preview: 'Mostly through the electron transport chain.',
  last_session_summary: null,
  progress: { focus_target_gap: 'ATP yield per glucose', level: 'intermediate', mastered_count: 1 },
}

const REVIEW_QUEUE = {
  items: [
    {
      concept: 'glycolysis net yield',
      source_session_id: SESSION_ID,
      source_topic: 'Cellular respiration',
      due_at: NOW,
      streak: 1,
    },
  ],
  total: 1,
}

// --- Stubs ----------------------------------------------------------------

function json(route, body, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
}

async function stubAuth(page, { tokenStatus = 200 } = {}) {
  await page.route('**/auth/v1/settings**', (route) =>
    json(route, { external: {}, mfa: {}, disable_signup: false }),
  )
  await page.route('**/auth/v1/token**', (route) =>
    tokenStatus === 200
      ? json(route, {
          access_token: 'e2e-access-token',
          token_type: 'bearer',
          expires_in: 3600,
          expires_at: Math.floor(Date.now() / 1000) + 3600,
          refresh_token: 'e2e-refresh-token',
          user: {
            id: 'u-e2e',
            aud: 'authenticated',
            role: 'authenticated',
            email: 'me@example.com',
            app_metadata: {},
            user_metadata: {},
            created_at: NOW,
          },
        })
      : json(
          route,
          {
            error: 'invalid_grant',
            error_code: 'invalid_credentials',
            error_description: 'Invalid login credentials',
          },
          tokenStatus,
        ),
  )
  await page.route('**/auth/v1/user**', (route) =>
    json(route, { id: 'u-e2e', email: 'me@example.com', app_metadata: {}, user_metadata: {} }),
  )
}

// `api` maps "METHOD /path" or "/path" to a body, or to a function of the
// route returning [status, body]. Tests may mutate it between navigations.
// Anything unmapped gets an empty payload rather than a network error toast.
async function stubApi(page, api) {
  await page.route('**/api/**', async (route) => {
    const req = route.request()
    const url = new URL(req.url())
    const path = url.pathname.replace(/^.*\/api/, '')
    const hit = api[`${req.method()} ${path}`] ?? api[path]

    if (typeof hit === 'function') {
      const [status, body] = hit(url)

      return json(route, body, status)
    }

    return json(route, hit ?? {})
  })
}

function baseApi() {
  return {
    '/me': { display_name: 'Eddy', feedback_pref: 'hints', onboarding_complete: true },
    '/sessions/library': (url) => {
      const items = url.searchParams.get('status') === 'ended' ? [] : [LIBRARY_ITEM]

      return [200, { items, total: items.length, limit: 40, offset: 0 }]
    },
    '/review/queue': { items: [], total: 0 },
    [`/sessions/${SESSION_ID}`]: makeSession(),
    [`/sessions/${SESSION_ID}/ingestion`]: { status: null, documents: [] },
    [`/profile/${SESSION_ID}`]: {
      profile: makeProfile(),
      etag: 'e2e-etag',
      recent_learning_events: [],
    },
  }
}

// Unlike e2e/support/auth.js's signIn, needs no backend. Signs in through the
// real form so supabase-js persists the session itself, then parks the mouse where it hovers nothing: a pointer left over the
// submit button's spot would put whatever lands there next in :hover.
async function signInOffline(page, api) {
  await stubAuth(page)
  await stubApi(page, api)
  await page.goto('/login')
  await page.getByTestId('login-email').fill('me@example.com')
  await page.getByTestId('login-password').fill('hunter2pw')
  await page.getByTestId('login-submit').click()
  await expect(page).toHaveURL(/\/$/)
  const { width, height } = page.viewportSize()
  await page.mouse.move(width - 1, height - 1)
}

async function openSession(page) {
  await page.goto(`/session/${SESSION_ID}`)
  // The page focuses the composer once the session loads. Wait for that, then
  // blur, so the read pins its resting look and not its :focus-within border.
  const input = page.getByTestId('session-input')
  await expect(input).toBeFocused()
  await input.blur()
}

// Real Tab presses, so Chromium's :focus-visible heuristic matches the way a
// keyboard user sees it (script focus() may not).
async function tabTo(page, locator) {
  for (let i = 0; i < 40; i++) {
    await page.keyboard.press('Tab')

    if (await locator.evaluate((el) => el === document.activeElement)) {
      expect(await locator.evaluate((el) => el.matches(':focus-visible'))).toBe(true)

      return
    }
  }

  throw new Error('Tab never reached the element')
}

// --- Tests ----------------------------------------------------------------

test.use({ colorScheme: 'light' })

test.describe('card look at desktop', () => {
  test.use({ viewport: DESKTOP })

  test.beforeEach(async ({ context }) => {
    await context.clearCookies()
  })

  test('login: auth cover and the wrong-password status box', async ({ page }) => {
    await stubAuth(page, { tokenStatus: 400 })
    await page.goto('/login')
    await expectLook('authCover', page.getByTestId('login-form').locator('..'))

    await page.getByTestId('login-email').fill('me@example.com')
    await page.getByTestId('login-password').fill('wrongpass')
    await page.getByTestId('login-submit').click()
    await expectLook('loginStatus', page.getByTestId('login-error'))
  })

  test('legal and 404: the page card', async ({ page }) => {
    await stubAuth(page)
    await page.goto('/tos')
    await expectLook('legalPage', page.getByRole('main'))

    await page.goto('/no-such-page')
    await expectLook('notFound', page.getByTestId('not-found-title').locator('..'))
  })

  test('home: cover card and topic intercept', async ({ page }) => {
    const api = baseApi()
    api['/sessions/lookup'] = {
      active_match: { session_id: SESSION_ID, title: 'Cellular respiration' },
    }
    await signInOffline(page, api)

    await expectLook(
      'homeCover',
      page.getByRole('heading', { name: 'What do you want to learn?' }).locator('..'),
    )

    await page.getByTestId('home-quick-topic').fill('Cellular respiration')
    await page.getByTestId('home-quick-go').click()
    await expectLook('topicIntercept', page.getByTestId('start-intercept'))
  })

  test('library: row, focus chip, empty state, error line and Retry', async ({ page }) => {
    const api = baseApi()
    await signInOffline(page, api)

    await page.goto('/sessions')
    const row = page.getByTestId(`library-card-${SESSION_ID}`)
    await expectLook('libraryRow', row)
    await expectLook('focusChip', row.getByTestId('chip-focus'))

    api['/sessions/library'] = { items: [], total: 0, limit: 20, offset: 0 }
    await page.goto('/sessions')
    await expectLook(
      'libraryEmpty',
      page.getByRole('heading', { name: 'No sessions found' }).locator('..'),
    )

    api['/sessions/library'] = () => [500, { detail: 'boom' }]
    await page.goto('/sessions')
    await expectLook('libraryError', page.getByTestId('library-error'), TEXT_PROPS)
    await expectLook('libraryRetry', page.getByTestId('library-error-retry'), TEXT_PROPS)
  })

  test('session: check, recap, learner turn, composer, cue card, sidebar row', async ({ page }) => {
    const api = baseApi()
    api[`/sessions/${SESSION_ID}`] = makeSession({
      messages: [
        ...TURNS,
        message('m2', 'assistant', 'Quick check.', { check_batch: RECAP_BATCH }),
      ],
      pending_check: PENDING_CHECK,
    })
    await signInOffline(page, api)
    await openSession(page)

    await expectLook('checkCard', page.getByTestId('check-card'))
    await expectLook('recapCard', page.getByTestId('check-recap'))
    await expectLook('learnerTurn', page.getByTestId('msg-user'))
    await expectLook('composer', page.getByTestId('session-input').locator('..'))
    await expectLook('cueCard', page.getByTestId('cue-focus').locator('..'))
    await expectLook('sidebarCurrentRow', page.getByTestId(`sidebar-row-${SESSION_ID}`))
  })

  test('session: ended card', async ({ page }) => {
    const api = baseApi()
    api[`/sessions/${SESSION_ID}`] = makeSession({ ended_at: NOW })
    await signInOffline(page, api)

    await page.goto(`/session/${SESSION_ID}`)
    await expectLook('sessionEnded', page.getByTestId('session-ended-banner'))
  })

  test('session: topic suggestion card', async ({ page }) => {
    const api = baseApi()
    api[`/sessions/${SESSION_ID}`] = makeSession({
      messages: [
        ...TURNS,
        message('m2', 'assistant', 'Where next?', {
          topic_suggestions: {
            mode: 'broad',
            topic: 'Cellular respiration',
            items: [
              { label: 'Glycolysis', hint: 'The first stage' },
              { label: 'Krebs cycle', hint: 'In the matrix' },
            ],
          },
        }),
      ],
    })
    await signInOffline(page, api)
    await openSession(page)

    await expectLook('topicSuggest', page.getByTestId('topic-suggest-card'))
  })

  test('session: level picker and empty-session state', async ({ page }) => {
    const profile = makeProfile({ knowledge_level: null })
    const api = baseApi()
    api[`/sessions/${SESSION_ID}`] = makeSession({ messages: [], topic_profile: profile })
    api[`/profile/${SESSION_ID}`] = { profile, etag: 'e2e-etag', recent_learning_events: [] }
    await signInOffline(page, api)
    await openSession(page)

    await expectLook('levelPicker', page.getByTestId('diagnostic-consent-card'))
    await expectLook('sessionEmpty', page.getByTestId('session-empty'))
  })

  test('session: the four notice strips', async ({ page }) => {
    const api = baseApi()
    api[`/sessions/${SESSION_ID}/ingestion`] = {
      status: 'pending',
      documents: [{ id: 'd1', filename: 'notes.pdf', status: 'pending', error: null }],
    }
    api['POST /chat/stream'] = () => [
      429,
      {
        detail: {
          code: 'daily_cap_reached',
          cap: 2,
          used: 2,
          resets_at: '2099-01-01T00:00:00+00:00',
        },
      },
    ]
    await signInOffline(page, api)
    await openSession(page)

    await expectLook('referenceBanner', page.getByTestId('reference-status'))

    // A .png fails client-side validation, so no upload request is needed.
    await page.getByTestId('session-upload-input').setInputFiles({
      name: 'diagram.png',
      mimeType: 'image/png',
      buffer: Buffer.from('not a pdf'),
    })
    await expectLook('uploadStatus', page.getByTestId('upload-status-failed'))

    // One capped send shows both the daily-cap banner and the status line.
    await page.getByTestId('session-input').fill('one more please')
    await page.getByTestId('session-send').click()
    await expectLook('capBanner', page.getByTestId('session-cap-banner'))
    await expectLook('statusLine', page.getByTestId('session-error'))
  })

  test('recall: joined sheet, concept card at rest and keyboard-focused', async ({ page }) => {
    const api = baseApi()
    api['/review/queue'] = REVIEW_QUEUE
    await signInOffline(page, api)
    await page.goto('/recall')

    const card = page.getByTestId('recall-card')
    await expectLook('recallSheet', page.getByTestId('recall-divider').first().locator('> div'))
    await expectLook('recallCard', card)

    await tabTo(page, card)
    await expectLook('recallCardFocused', card)
  })

  test('settings and account: the sheet panels', async ({ page }) => {
    await signInOffline(page, baseApi())

    await page.goto('/settings/learning')
    await expectLook('settingsPanel', page.getByRole('tabpanel'))

    await page.goto('/account')
    await expectLook('accountPanel', page.getByTestId('settings-account'))
  })

  test('session profile: divider body, section card, conflict notice', async ({ page }) => {
    const api = baseApi()
    api[`PATCH /profile/${SESSION_ID}`] = () => [412, { detail: 'etag mismatch' }]
    await signInOffline(page, api)
    await page.goto(`/session/${SESSION_ID}/profile`)

    await expectLook('profileDivider', page.getByTestId('sprof-level').locator('> div'))
    await expectLook('profileSection', page.getByTestId('sprof-events'))

    await page.getByTestId('level-select').getByRole('button', { name: 'beginner' }).click()
    await expectLook('profileConflict', page.getByTestId('sprof-conflict'))
  })

  test('aggregate profile: topic card and text button', async ({ page }) => {
    const api = baseApi()
    api['/profile/aggregate'] = {
      total_sessions: 1,
      last_active_at: NOW,
      recent_topics: [
        {
          id: SESSION_ID,
          topic: 'Cellular respiration',
          created_at: NOW,
          ended_at: null,
          last_activity_at: NOW,
          last_message_preview: 'Mostly through the electron transport chain.',
          last_session_summary: null,
          progress: {
            level: 'intermediate',
            focus_target_gap: 'ATP yield per glucose',
            mastered_count: 1,
          },
        },
      ],
      knowledge_level_distribution: { beginner: 0, intermediate: 1, advanced: 0, unknown: 0 },
      combined_confirmed_gaps: [],
      combined_mastered_concepts: [],
      weekly_mastery: [],
      concept_accuracy: [],
    }
    await signInOffline(page, api)
    await page.goto('/profile')

    const topic = page.getByTestId('aprof-topic-card')
    await expectLook('aggregateTopic', topic)
    await expectLook('textButton', topic.getByRole('link', { name: 'Open profile' }), TEXT_PROPS)
  })
})

// Their mobile media queries change card rules at this width.
test.describe('card look at 390px', () => {
  test.use({ viewport: MOBILE })

  test.beforeEach(async ({ context }) => {
    await context.clearCookies()
  })

  test('auth cover', async ({ page }) => {
    await stubAuth(page)
    await page.goto('/login')
    await expectLook('authCoverMobile', page.getByTestId('login-form').locator('..'))
  })

  test('recall concept card', async ({ page }) => {
    const api = baseApi()
    api['/review/queue'] = REVIEW_QUEUE
    await signInOffline(page, api)
    await page.goto('/recall')
    // The sheet's padding is what this width's media query changes.
    await expectLook(
      'recallSheetMobile',
      page.getByTestId('recall-divider').first().locator('> div'),
    )
    await expectLook('recallCardMobile', page.getByTestId('recall-card'))
  })

  test('cue card and its drawer', async ({ page }) => {
    await signInOffline(page, baseApi())
    await openSession(page)
    // Below 900px the cue body is a collapsed strip; disclosed, it becomes a
    // drawer card hanging below the strip.
    await page.getByTestId('cue-disclosure').click()
    await page.mouse.move(MOBILE.width - 1, MOBILE.height - 1)
    const cueCard = page.getByTestId('cue-focus').locator('..')
    await expectLook('cueCardMobile', cueCard)
    // cue card -> its section -> the cue body
    await expectLook('cueDrawerMobile', cueCard.locator('../..'))
  })
})
