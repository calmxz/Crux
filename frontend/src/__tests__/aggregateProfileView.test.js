import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

const apiGetAggregate = vi.fn()

vi.mock('@/services/profileApi.js', () => ({
  getAggregateProfile: (...args) => apiGetAggregate(...args),
}))

import AggregateProfileView from '@/views/AggregateProfileView.vue'
import { TICK_PATH } from '@/components/chat/levelMark.js'

// Fixture copied from the #358 prototype (frontend/prototype/profile-page.html
// on prototype/profile-page), shaped like AggregateProfileResponse.
const S = {
  ode: 'sess-ode-0001',
  graphs: 'sess-graphs-0002',
  thermo: 'sess-thermo-0003',
  linalg: 'sess-linalg-0004',
  prob: 'sess-prob-0005',
}

const ago = (d, h = 3) => new Date(Date.now() - d * 86400000 - h * 3600000).toISOString()

function monday(n) {
  const d = new Date()
  d.setUTCHours(0, 0, 0, 0)
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7) - n * 7)

  return d.toISOString().slice(0, 10)
}

function fullFixture() {
  return {
    total_sessions: 9,
    active_sessions: 3,
    ended_sessions: 6,
    total_learning_events: 47,
    last_active_at: ago(0, 2),
    combined_mastered_concepts: [
      { concept: 'separable equations', count: 3, first_seen_session_id: S.ode },
      { concept: 'matrix rank', count: 2, first_seen_session_id: S.linalg },
      { concept: 'breadth-first search', count: 2, first_seen_session_id: S.graphs },
      { concept: 'first law of thermodynamics', count: 1, first_seen_session_id: S.thermo },
      { concept: 'conditional probability', count: 1, first_seen_session_id: S.prob },
      { concept: 'eigenvalues', count: 1, first_seen_session_id: S.linalg },
      { concept: 'Dijkstra', count: 1, first_seen_session_id: S.graphs },
    ],
    combined_confirmed_gaps: [
      { concept: 'integrating factor', count: 2, first_seen_session_id: S.ode },
      { concept: 'entropy', count: 2, first_seen_session_id: S.thermo },
      { concept: 'Bayes theorem', count: 1, first_seen_session_id: S.prob },
      { concept: 'topological sort', count: 1, first_seen_session_id: S.graphs },
      { concept: 'diagonalisation', count: 1, first_seen_session_id: S.linalg },
    ],
    knowledge_level_distribution: { beginner: 2, intermediate: 4, advanced: 1, unknown: 2 },
    recent_topics: [
      {
        id: S.ode,
        topic: 'Ordinary differential equations',
        created_at: ago(1),
        ended_at: null,
        last_session_summary: null,
        message_count: 42,
        last_activity_at: ago(0, 2),
        last_message_preview: 'So the integrating factor is e to the integral of p?',
        progress: {
          focus_target_gap: 'integrating factor',
          level: 'intermediate',
          mastered_count: 4,
        },
      },
      {
        id: S.graphs,
        topic: 'Graph algorithms',
        created_at: ago(3),
        ended_at: null,
        last_session_summary: null,
        message_count: 18,
        last_activity_at: ago(2),
        last_message_preview: 'Why does **Dijkstra** fail on $w < 0$ edges?',
        progress: { focus_target_gap: 'topological sort', level: 'advanced', mastered_count: 3 },
      },
      {
        id: S.thermo,
        topic: 'Thermodynamics',
        created_at: ago(6),
        ended_at: ago(4),
        last_session_summary:
          '[auto] Covered the first law and heat engines; entropy remains the open gap.',
        message_count: 31,
        last_activity_at: ago(4),
        last_message_preview: null,
        progress: { focus_target_gap: 'entropy', level: 'beginner', mastered_count: 1 },
      },
      {
        id: S.linalg,
        topic: 'Linear algebra',
        created_at: ago(9),
        ended_at: null,
        last_session_summary: null,
        message_count: 7,
        last_activity_at: ago(9),
        last_message_preview: null,
        progress: { focus_target_gap: null, level: null, mastered_count: 0 },
      },
      {
        id: S.prob,
        topic: 'Probability',
        created_at: ago(14),
        ended_at: ago(12),
        last_session_summary: '[auto] Conditional probability landed; Bayes still needs work.',
        message_count: 24,
        last_activity_at: ago(12),
        last_message_preview: null,
        progress: { focus_target_gap: 'Bayes theorem', level: 'intermediate', mastered_count: 2 },
      },
    ],
    concept_accuracy: [
      {
        concept: 'entropy',
        correct_count: 1,
        total_count: 5,
        accuracy: 0.2,
        last_results: [false, false, true, false, false],
        first_seen_session_id: S.thermo,
      },
      {
        concept: 'integrating factor',
        correct_count: 1,
        total_count: 3,
        accuracy: 0.33,
        last_results: [false, true, false],
        first_seen_session_id: S.ode,
      },
      {
        concept: 'Bayes theorem',
        correct_count: 2,
        total_count: 4,
        accuracy: 0.5,
        last_results: [false, true, false, true],
        first_seen_session_id: S.prob,
      },
      {
        concept: 'topological sort',
        correct_count: 1,
        total_count: 2,
        accuracy: 0.5,
        last_results: [true, false],
        first_seen_session_id: S.graphs,
      },
      {
        concept: 'eigenvalues',
        correct_count: 2,
        total_count: 3,
        accuracy: 0.67,
        last_results: [false, true, true],
        first_seen_session_id: S.linalg,
      },
      {
        concept: 'matrix rank',
        correct_count: 3,
        total_count: 4,
        accuracy: 0.75,
        last_results: [true, false, true, true],
        first_seen_session_id: S.linalg,
      },
      {
        concept: 'breadth-first search',
        correct_count: 4,
        total_count: 5,
        accuracy: 0.8,
        last_results: [true, true, false, true, true],
        first_seen_session_id: S.graphs,
      },
      {
        concept: 'conditional probability',
        correct_count: 1,
        total_count: 1,
        accuracy: 1,
        last_results: [true],
        first_seen_session_id: S.prob,
      },
      {
        concept: 'separable equations',
        correct_count: 5,
        total_count: 5,
        accuracy: 1,
        last_results: [true, true, true, true, true],
        first_seen_session_id: S.ode,
      },
    ],
    weekly_mastery: [0, 1, 0, 3, 2, 0, 0, 4, 1, 5, 2, 3].map((count, i) => ({
      week_start: monday(11 - i),
      count,
    })),
  }
}

function emptyFixture() {
  return {
    total_sessions: 0,
    active_sessions: 0,
    ended_sessions: 0,
    total_learning_events: 0,
    last_active_at: null,
    combined_mastered_concepts: [],
    combined_confirmed_gaps: [],
    knowledge_level_distribution: { beginner: 0, intermediate: 0, advanced: 0, unknown: 0 },
    recent_topics: [],
    concept_accuracy: [],
    weekly_mastery: Array.from({ length: 12 }, (_, i) => ({
      week_start: monday(11 - i),
      count: 0,
    })),
  }
}

const profileOf = (id) => ({ name: 'session-profile', params: { id } })

const sessionOf = (id) => ({ name: 'session', params: { id } })

async function mountView(data = fullFixture()) {
  apiGetAggregate.mockResolvedValue(data)
  const wrapper = mount(AggregateProfileView, { global: { stubs: { RouterLink: RouterLinkStub } } })
  await flushPromises()

  return wrapper
}

// The RouterLink targets inside one element, in document order.
function linksIn(wrapper, selector) {
  return wrapper
    .get(selector)
    .findAllComponents(RouterLinkStub)
    .map((l) => ({ text: l.text(), to: l.props('to') }))
}

describe('AggregateProfileView (/profile)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    apiGetAggregate.mockReset()
  })

  it('renders the head: one title, the pencil lede with the relative last-studied time, no Back', async () => {
    const wrapper = await mountView()
    expect(wrapper.findAll('h1')).toHaveLength(1)
    expect(wrapper.get('h1').text()).toBe('Your profile')
    const lede = wrapper.get('[data-testid="aprof-lede"]').text()
    expect(lede).toContain('What the tutor knows about you, topic by topic.')
    expect(lede).toMatch(/Last studied .*ago\./)
    expect(wrapper.text()).not.toContain('Back')
  })

  it('renders the six sections in order', async () => {
    const wrapper = await mountView()
    const ids = wrapper.findAll('[data-section]').map((s) => s.attributes('data-section'))
    expect(ids).toEqual(['head', 'topics', 'level', 'gaps', 'mastered', 'figures'])
  })

  describe('topic cards', () => {
    it('renders one card per recent topic with state, cues and actions', async () => {
      const wrapper = await mountView()
      const cards = wrapper.findAll('[data-testid="aprof-topic-card"]')
      expect(cards).toHaveLength(5)

      const ode = cards[0]
      expect(ode.get('[data-testid="aprof-topic-state"]').text()).toBe('active')
      expect(ode.get('[data-testid="aprof-topic-level"]').text()).toBe('intermediate')
      const focus = ode.get('[data-testid="aprof-topic-focus"]')
      expect(focus.text()).toContain('integrating factor')
      expect(focus.classes()).toContain('focus-word')
      expect(ode.get('[data-testid="aprof-topic-mastered"]').text()).toBe('4 mastered')
      const story = ode.get('[data-testid="aprof-topic-story"]')
      expect(story.text()).toBe('So the integrating factor is e to the integral of p?')
      expect(story.classes()).toContain('is-preview')

      const thermo = cards[2]
      expect(thermo.get('[data-testid="aprof-topic-state"]').text()).toBe('ended')
      const sum = thermo.get('[data-testid="aprof-topic-story"]')
      expect(sum.text()).toBe(
        'Covered the first law and heat engines; entropy remains the open gap.',
      )
      expect(sum.classes()).not.toContain('is-preview')
    })

    it('strips markdown and math from the last message preview', async () => {
      const wrapper = await mountView()
      const graphs = wrapper.findAll('[data-testid="aprof-topic-card"]')[1]
      expect(graphs.get('[data-testid="aprof-topic-story"]').text()).toBe(
        'Why does Dijkstra fail on [formula] edges?',
      )
    })

    it('writes the unset level and missing focus in pencil, and omits an empty story', async () => {
      const wrapper = await mountView()
      const linalg = wrapper.findAll('[data-testid="aprof-topic-card"]')[3]
      const level = linalg.get('[data-testid="aprof-topic-level"]')
      expect(level.text()).toBe('level not set')
      expect(level.classes()).toContain('is-unset')
      expect(linalg.get('[data-testid="aprof-topic-focus"]').text()).toBe('no focus cue yet')
      expect(linalg.get('[data-testid="aprof-topic-mastered"]').text()).toBe('0 mastered')
      expect(linalg.find('[data-testid="aprof-topic-story"]').exists()).toBe(false)
    })

    it('links the topic and Open profile to the session profile, and Continue / Resume to the session', async () => {
      const wrapper = await mountView()
      const cards = wrapper.findAll('[data-testid="aprof-topic-card"]')

      const odeLinks = cards[0].findAllComponents(RouterLinkStub).map((l) => ({
        text: l.text(),
        to: l.props('to'),
      }))

      expect(odeLinks).toEqual([
        { text: 'Ordinary differential equations', to: profileOf(S.ode) },
        { text: 'Continue', to: sessionOf(S.ode) },
        { text: 'Open profile', to: profileOf(S.ode) },
      ])
      const thermoLinks = cards[2].findAllComponents(RouterLinkStub).map((l) => l.text())
      expect(thermoLinks).toContain('Resume')
      expect(thermoLinks).not.toContain('Continue')
    })

    it('writes the foot line with a See all topics link to the library', async () => {
      const wrapper = await mountView()
      const foot = wrapper.get('[data-testid="aprof-topics-foot"]')
      expect(foot.text()).toContain('Showing 5 of 9 topics.')
      expect(linksIn(wrapper, '[data-testid="aprof-topics-foot"]')).toEqual([
        { text: 'See all topics', to: { name: 'sessions-library' } },
      ])
    })
  })

  describe('dividers', () => {
    it('Level: a neutral tab counting sessions, one row per level plus level not set', async () => {
      const wrapper = await mountView()
      const level = wrapper.get('[data-testid="aprof-level"]')
      expect(level.get('.divider-tab').classes()).toContain('divider-tab--level')
      expect(level.get('.divider-tab').text()).toBe('Level 9')

      const rows = level
        .findAll('[data-testid="aprof-level-row"]')
        .map((r) => [r.get('.level-word').text(), r.get('.meta').text()])

      expect(rows).toEqual([
        ['beginner', '2 topics'],
        ['intermediate', '4 topics'],
        ['advanced', '1 topic'],
        ['level not set', '2 topics'],
      ])
    })

    it('Level: omits the level-not-set row when every session has a level', async () => {
      const data = fullFixture()
      data.knowledge_level_distribution.unknown = 0
      const wrapper = await mountView(data)
      const rows = wrapper.findAll('[data-testid="aprof-level-row"]').map((r) => r.text())
      expect(rows).toHaveLength(3)
      expect(rows.join(' ')).not.toContain('not set')
    })

    it('Gaps: amber tab, every gap linking to its first-seen session profile, count when > 1', async () => {
      const wrapper = await mountView()
      const gaps = wrapper.get('[data-testid="aprof-gaps"]')
      expect(gaps.get('.divider-tab').classes()).toContain('divider-tab--gaps')
      expect(gaps.get('.divider-tab').text()).toBe('Gaps 5')
      expect(linksIn(wrapper, '[data-testid="aprof-gaps"]')).toEqual([
        { text: 'integrating factor', to: profileOf(S.ode) },
        { text: 'entropy', to: profileOf(S.thermo) },
        { text: 'Bayes theorem', to: profileOf(S.prob) },
        { text: 'topological sort', to: profileOf(S.graphs) },
        { text: 'diagonalisation', to: profileOf(S.linalg) },
      ])
      const rows = gaps.findAll('[data-testid="aprof-cue-row"]')
      expect(rows[0].text()).toContain('in 2 sessions')
      expect(rows[2].text()).not.toContain('session')
    })

    it('Mastered: green tab, every concept linking to its first-seen session profile', async () => {
      const wrapper = await mountView()
      const mastered = wrapper.get('[data-testid="aprof-mastered"]')
      expect(mastered.get('.divider-tab').classes()).toContain('divider-tab--mastered')
      expect(mastered.get('.divider-tab').text()).toBe('Mastered 7')
      const links = linksIn(wrapper, '[data-testid="aprof-mastered"]')
      expect(links).toHaveLength(7)
      expect(links[0]).toEqual({ text: 'separable equations', to: profileOf(S.ode) })
      expect(links[6]).toEqual({ text: 'Dijkstra', to: profileOf(S.graphs) })
      expect(mastered.findAll('[data-testid="aprof-cue-row"]')[0].text()).toContain('in 3 sessions')
      expect(mastered.get('.cue-mark--tick path').attributes('d')).toBe(TICK_PATH)
    })

    it('writes "none open" / "none yet" when a divider list is empty', async () => {
      const data = fullFixture()
      data.combined_confirmed_gaps = []
      data.combined_mastered_concepts = []
      const wrapper = await mountView(data)
      expect(wrapper.get('[data-testid="aprof-gaps"]').text()).toContain('none open')
      expect(wrapper.get('[data-testid="aprof-mastered"]').text()).toContain('none yet')
    })

    it('keeps the tab law: red only on Focus, amber only on Gaps, green only on Mastered', async () => {
      const wrapper = await mountView()
      // No Focus divider on this page: the focus cue is the underlined word on a card.
      expect(wrapper.find('.divider-tab--focus').exists()).toBe(false)
      expect(wrapper.findAll('.divider-tab--gaps')).toHaveLength(1)
      expect(wrapper.findAll('.divider-tab--mastered')).toHaveLength(1)
    })
  })

  describe('figures', () => {
    it('Mastered by week: 12 columns with every week written out for screen readers', async () => {
      const wrapper = await mountView()
      const weekly = wrapper.get('[data-testid="aprof-weekly"]')
      expect(weekly.findAll('rect.weekly-bar')).toHaveLength(12)
      const text = weekly.findAll('[data-testid="aprof-weekly-text"] li')
      expect(text).toHaveLength(12)
      expect(text[11].text()).toMatch(/^Week of .+: 3 mastered$/)
    })

    it('Mastered by week: "none yet" when no week has a count', async () => {
      const data = fullFixture()
      data.weekly_mastery = data.weekly_mastery.map((w) => ({ ...w, count: 0 }))
      const wrapper = await mountView(data)
      const weekly = wrapper.get('[data-testid="aprof-weekly"]')
      expect(weekly.find('rect').exists()).toBe(false)
      expect(weekly.text()).toContain('none yet')
    })

    it('Check accuracy: least and most accurate groups of 3, each concept linked to its first-seen profile', async () => {
      const wrapper = await mountView()
      const acc = wrapper.get('[data-testid="aprof-accuracy"]')
      expect(acc.text()).toContain('Least accurate')
      expect(acc.text()).toContain('Most accurate')
      expect(linksIn(wrapper, '[data-testid="aprof-accuracy"]')).toEqual([
        { text: 'entropy', to: profileOf(S.thermo) },
        { text: 'integrating factor', to: profileOf(S.ode) },
        { text: 'Bayes theorem', to: profileOf(S.prob) },
        { text: 'breadth-first search', to: profileOf(S.graphs) },
        { text: 'conditional probability', to: profileOf(S.prob) },
        { text: 'separable equations', to: profileOf(S.ode) },
      ])
      const first = acc.findAll('[data-testid="aprof-accuracy-row"]')[0]
      expect(first.text()).toContain('1 of 5')
      const marks = first.findAll('svg[role="img"]').map((m) => m.attributes('aria-label'))
      expect(marks).toEqual(['incorrect', 'incorrect', 'correct', 'incorrect', 'incorrect'])
    })

    it('Check accuracy: no group labels and no repeats when fewer than 4 concepts exist', async () => {
      const data = fullFixture()
      data.concept_accuracy = data.concept_accuracy.slice(0, 2)
      const wrapper = await mountView(data)
      const acc = wrapper.get('[data-testid="aprof-accuracy"]')
      expect(acc.text()).not.toContain('Least accurate')
      expect(acc.findAll('[data-testid="aprof-accuracy-row"]')).toHaveLength(2)
    })

    it('Check accuracy: "none yet" when nothing has been checked', async () => {
      const data = fullFixture()
      data.concept_accuracy = []
      const wrapper = await mountView(data)
      expect(wrapper.get('[data-testid="aprof-accuracy"]').text()).toContain('none yet')
    })
  })

  it('shows the EmptyState under the head at zero sessions, and nothing else', async () => {
    const wrapper = await mountView(emptyFixture())
    expect(wrapper.get('h1').text()).toBe('Your profile')
    const empty = wrapper.get('[data-testid="aprof-empty"]')
    expect(empty.text()).toContain('No sessions yet')
    expect(empty.text()).toContain('Start one. Your profile builds itself as you go.')
    expect(linksIn(wrapper, '[data-testid="aprof-empty"]')).toEqual([
      { text: 'Start your first session', to: { name: 'home' } },
    ])
    expect(wrapper.find('[data-section="topics"]').exists()).toBe(false)
    expect(wrapper.find('.divider').exists()).toBe(false)
    expect(wrapper.get('[data-testid="aprof-lede"]').text()).not.toContain('Last studied')
  })

  it('shows a loading skeleton, then the page', async () => {
    let resolve
    apiGetAggregate.mockReturnValue(new Promise((r) => (resolve = r)))

    const wrapper = mount(AggregateProfileView, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })

    await flushPromises()
    expect(wrapper.find('[data-testid="aprof-loading"]').exists()).toBe(true)
    resolve(fullFixture())
    await flushPromises()
    expect(wrapper.find('[data-testid="aprof-loading"]').exists()).toBe(false)
    expect(wrapper.findAll('[data-testid="aprof-topic-card"]')).toHaveLength(5)
  })

  it('shows the error with a retry that refetches', async () => {
    apiGetAggregate.mockRejectedValueOnce(new Error('boom'))

    const wrapper = mount(AggregateProfileView, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })

    await flushPromises()
    expect(wrapper.find('[data-testid="aprof-error"]').exists()).toBe(true)
    apiGetAggregate.mockResolvedValueOnce(fullFixture())
    await wrapper.get('[data-testid="aprof-retry"]').trigger('click')
    await flushPromises()
    expect(apiGetAggregate).toHaveBeenCalledTimes(2)
    expect(wrapper.find('[data-testid="aprof-error"]').exists()).toBe(false)
    expect(wrapper.findAll('[data-testid="aprof-topic-card"]')).toHaveLength(5)
  })
})
