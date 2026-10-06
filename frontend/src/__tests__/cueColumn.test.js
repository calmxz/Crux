import { describe, it, expect, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

import CueColumn from '@/components/chat/CueColumn.vue'
import { __test__ as panelTest } from '@/composables/usePanel.js'

// ConceptEntry per docs/api/openapi.yaml: the concept key is `name`.
const entry = (name) => ({ name, evidence_type: null, last_event_at: null })

const profile = (overrides = {}) => ({
  knowledge_level: null,
  subtopic_levels: {},
  confirmed_gaps: [entry('ATP yield'), entry('glycolysis steps')],
  mastered_concepts: [entry('enzyme kinetics')],
  focus_target_gap: 'ATP yield',
  last_session_summary: null,
  ...overrides,
})

const mountCue = (p = profile(), props = {}) =>
  mount(CueColumn, { props: { profile: p, sessionId: 's1', ...props } })

describe('CueColumn', () => {
  it('renders the focus cue, the remaining gaps and the mastered concepts', () => {
    const w = mountCue()
    expect(w.get('[data-testid="cue-focus"]').text()).toContain('ATP yield')
    const gaps = w.findAll('[data-testid="cue-gap"]')
    // The focus cue has its own section and is not repeated under Gaps.
    expect(gaps).toHaveLength(1)
    expect(gaps[0].text()).toContain('glycolysis steps')
    const mastered = w.findAll('[data-testid="cue-mastered"]')
    expect(mastered).toHaveLength(1)
    expect(mastered[0].text()).toContain('enzyme kinetics')
  })

  it('tolerates legacy bare-string concept entries', () => {
    const w = mountCue(profile({ confirmed_gaps: ['plain gap'], focus_target_gap: null }))
    expect(w.get('[data-testid="cue-gap"]').text()).toContain('plain gap')
  })

  it('marks the focus cue rather than setting the word in red', () => {
    const w = mountCue()
    const row = w.get('[data-testid="cue-focus"]')
    // The mark is a separate red SVG; the word itself stays a plain cue word.
    expect(row.find('svg.cue-mark--focus').exists()).toBe(true)
    expect(row.get('.cue-word').text()).toBe('ATP yield')
    expect(row.get('.cue-word').classes()).not.toContain('cue-mark--focus')
  })

  it('underlines the cue under an open check without recolouring it', () => {
    const w = mountCue(profile(), { testingGap: 'glycolysis steps' })
    const gap = w.get('[data-testid="cue-gap"]')
    expect(gap.get('.cue-word').classes()).toContain('is-testing')
  })

  it('steps the level mark stroke weight across the enum, hairline when unset', () => {
    const stroke = (lvl) => {
      const w = mountCue(profile({ knowledge_level: lvl }))

      return Number(w.get('[data-testid="cue-level"] path').attributes('stroke-width'))
    }

    const unset = stroke(null)
    const beginner = stroke('beginner')
    const intermediate = stroke('intermediate')
    const advanced = stroke('advanced')
    expect(unset).toBeLessThan(beginner)
    expect(beginner).toBeLessThan(intermediate)
    expect(intermediate).toBeLessThan(advanced)
  })

  it('labels an unset level in words', () => {
    const w = mountCue(profile({ knowledge_level: null }))
    expect(w.get('[data-testid="cue-level"]').text()).toContain('level not set')
  })

  it('renders the same stepped mark per subtopic level', () => {
    const w = mountCue(
      profile({ knowledge_level: 'beginner', subtopic_levels: { fermentation: 'advanced' } }),
    )

    const row = w.get('[data-testid="cue-subtopic"]')
    expect(row.text()).toContain('fermentation')
    expect(Number(row.get('path').attributes('stroke-width'))).toBeGreaterThan(
      Number(w.get('[data-testid="cue-level"] path').attributes('stroke-width')),
    )
  })

  it('seeds silently on first load, then lands only the cues added afterwards', async () => {
    const w = mountCue()
    // First non-null profile for this session must not replay as new ink.
    expect(w.emitted('landed')).toBeUndefined()
    expect(w.findAll('.is-fresh')).toHaveLength(0)

    await w.setProps({
      profile: profile({
        mastered_concepts: [entry('enzyme kinetics'), entry('Krebs cycle')],
      }),
    })
    expect(w.emitted('landed')).toHaveLength(1)
    expect(w.emitted('landed')[0][0]).toEqual(['mastered:Krebs cycle'])
    const freshRows = w.findAll('.is-fresh')
    expect(freshRows).toHaveLength(1)
    expect(freshRows[0].text()).toContain('Krebs cycle')
  })

  it('reseeds without landing when the session changes', async () => {
    const w = mountCue()
    await w.setProps({
      sessionId: 's2',
      profile: profile({
        confirmed_gaps: [entry('brand new gap')],
        mastered_concepts: [],
        focus_target_gap: null,
      }),
    })
    expect(w.emitted('landed')).toBeUndefined()
    expect(w.findAll('.is-fresh')).toHaveLength(0)
  })

  it('counts only the open gaps in the strip and says "1 gap"', () => {
    // The default fixture has two confirmed gaps, one of which is the focus
    // cue -- the strip must count the one gap the Gaps section actually lists.
    const strip = mountCue().get('[data-testid="cue-strip"]').text()
    expect(strip).toContain('1 gap')
    expect(strip).not.toContain('1 gaps')
    expect(strip).toContain('1 mastered')
  })

  it('says "0 gaps" when the only gap is the focus cue', () => {
    const strip = mountCue(
      profile({ confirmed_gaps: [entry('ATP yield')], focus_target_gap: 'ATP yield' }),
    )
      .get('[data-testid="cue-strip"]')
      .text()

    expect(strip).toContain('0 gaps')
  })

  it('exposes the strip disclosure with aria-expanded', async () => {
    const w = mountCue()
    const btn = w.get('[data-testid="cue-disclosure"]')
    expect(btn.attributes('aria-expanded')).toBe('false')
    await btn.trigger('click')
    expect(btn.attributes('aria-expanded')).toBe('true')
  })

  // The panel collapse state is a module singleton in usePanel.js, so every
  // case that touches it has to hand the module back the way it found it.
  afterEach(() => {
    panelTest._setExpanded(true)

    try {
      window.localStorage.removeItem(panelTest.LS_KEY)
    } catch {
      /* private mode, ignore */
    }
  })

  it('flips the collapse toggle label when the panel collapses', async () => {
    const w = mountCue()
    const btn = w.get('[data-testid="cue-collapse-toggle"]')
    expect(btn.attributes('aria-label')).toBe('Collapse profile')
    await btn.trigger('click')
    expect(btn.attributes('aria-label')).toBe('Expand profile')
  })

  it('renders the vertical tab rail and drops the sections when collapsed', () => {
    panelTest._setExpanded(false)
    const w = mountCue()
    expect(w.get('[data-testid="cue-column"]').classes()).toContain('is-collapsed')
    // Focus / Gaps / Mastered, the three coloured tabs; Level is not on the rail.
    expect(w.findAll('.cue-rail-tab')).toHaveLength(3)
    expect(w.findAll('[data-testid="cue-gap"]')).toHaveLength(0)
  })

  it('renders empty-section copy when the profile has nothing yet', () => {
    const w = mountCue(
      profile({ confirmed_gaps: [], mastered_concepts: [], focus_target_gap: null }),
    )

    expect(w.text()).toContain('no focus cue yet')
    expect(w.text()).toContain('none open')
    expect(w.text()).toContain('none yet')
  })
})
