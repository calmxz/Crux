import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

/* global process */

// The tab now writes the theme directly (light / dark / system) instead of
// flipping a single switch, so the composable is mocked on `override` +
// `setTheme` rather than `isDark` + `toggle`.
const setTheme = vi.fn()

vi.mock('../composables/useTheme.js', async () => {
  const { ref } = await import('vue')
  const override = ref('auto')

  return { useTheme: () => ({ override, setTheme }) }
})

import AppearanceTab from '../components/settings/AppearanceTab.vue'

describe('AppearanceTab', () => {
  it('renders the theme swatches with their testids', () => {
    const w = mount(AppearanceTab)
    expect(w.find('[data-testid="settings-appearance"]').exists()).toBe(true)
    expect(w.find('[data-testid="settings-theme-toggle"]').exists()).toBe(true)

    for (const mode of ['light', 'dark', 'auto']) {
      expect(w.find(`[data-testid="settings-theme-${mode}"]`).exists()).toBe(true)
    }
  })

  it('labels the two lamp swatches and the system option', () => {
    const w = mount(AppearanceTab)
    const text = w.text()
    expect(text).toContain('Lamp on')
    expect(text).toContain('Lamp off')
    expect(text).toContain('Match system')
  })

  it('marks the stored override as checked', () => {
    const w = mount(AppearanceTab)
    expect(w.get('[data-testid="settings-theme-auto"]').element.checked).toBe(true)
    expect(w.get('[data-testid="settings-theme-dark"]').element.checked).toBe(false)
  })

  it('choosing a swatch writes that theme', async () => {
    const w = mount(AppearanceTab)
    setTheme.mockClear()
    await w.get('[data-testid="settings-theme-dark"]').setValue(true)
    expect(setTheme).toHaveBeenCalledWith('dark')
  })

  // Bug: selecting a mode bolds its label, which (without a width
  // reservation) widens it and shifts the other labels in the flex row.
  // jsdom can't measure widths, so this asserts the reservation hook
  // (data-label, read by the ::after bold-weight ghost in CSS) is present.
  it('gives each mode-label a data-label matching its text, for the no-reflow bold reservation', () => {
    const w = mount(AppearanceTab)
    const labels = w.findAll('.mode-label')
    expect(labels.length).toBe(3)

    for (const label of labels) {
      expect(label.attributes('data-label')).toBe(label.text())
    }
  })
})

// T3: the swatch preview colors live in base.css's --sw-* tokens, not as hex
// literals in this component, so the dark-token drift guard in
// tokenContrast.test.js stays green (these are theme-independent previews,
// declared once in the plain :root block).
describe('AppearanceTab — swatch tokens (T3)', () => {
  it('declares all 8 --sw-* tokens in base.css :root', () => {
    const css = readFileSync(resolve(process.cwd(), 'src/assets/base.css'), 'utf8')
    const root = css.slice(0, css.indexOf("[data-theme='dark']"))

    const tokens = [
      '--sw-light-paper',
      '--sw-light-ink',
      '--sw-light-rule',
      '--sw-light-margin',
      '--sw-dark-paper',
      '--sw-dark-ink',
      '--sw-dark-rule',
      '--sw-dark-margin',
    ]

    for (const token of tokens) {
      expect(root, `${token} must be declared in :root`).toMatch(
        new RegExp(`${token}:\\s*#[0-9a-fA-F]{6}`),
      )
    }
  })

  it('AppearanceTab.vue has no hex literals in its <style> block', () => {
    const src = readFileSync(
      resolve(process.cwd(), 'src/components/settings/AppearanceTab.vue'),
      'utf8',
    )

    const style = src.slice(src.indexOf('<style'), src.lastIndexOf('</style>'))
    expect(style).not.toMatch(/#[0-9a-fA-F]{3,6}/)
  })
})
