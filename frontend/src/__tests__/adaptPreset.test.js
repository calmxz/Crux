import { describe, it, expect } from 'vitest'
import { adaptPresetConfig } from '@/theme/adaptPreset.js'

// WCAG relative luminance + contrast ratio from a #RRGGBB hex string.
function relativeLuminance(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex)

  if (!m) throw new Error(`not a 6-digit hex: ${hex}`)
  const int = parseInt(m[1], 16)

  const chan = [(int >> 16) & 255, (int >> 8) & 255, int & 255].map((v) => {
    const s = v / 255

    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
  })

  return 0.2126 * chan[0] + 0.7152 * chan[1] + 0.0722 * chan[2]
}

function contrastRatio(a, b) {
  const la = relativeLuminance(a)
  const lb = relativeLuminance(b)
  const [hi, lo] = la >= lb ? [la, lb] : [lb, la]

  return (hi + 0.05) / (lo + 0.05)
}

const RAMP_STEPS = [0, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]

describe('adaptPreset surface ramps', () => {
  // Aura selects surface indices per colorScheme: dark overlays use
  // surface.900 for background and surface.0 for text. An inverted dark ramp
  // (the original bug) made surface.900 near-white, rendering the
  // ConfirmDialog and every other PrimeVue overlay white-on-white in dark mode.
  for (const scheme of ['light', 'dark']) {
    it(`${scheme} ramp is monotonic light -> dark (0 lightest, 950 darkest)`, () => {
      const surface = adaptPresetConfig.semantic.colorScheme[scheme].surface
      const lums = RAMP_STEPS.map((s) => relativeLuminance(surface[s]))

      for (let i = 1; i < lums.length; i++) {
        // Each higher index must be no lighter than the previous one.
        expect(lums[i]).toBeLessThanOrEqual(lums[i - 1])
      }
    })

    it(`${scheme} overlay text (surface.0) is readable on overlay bg (surface.900)`, () => {
      const surface = adaptPresetConfig.semantic.colorScheme[scheme].surface
      // Maps to Aura's overlay.modal.color (surface.0) over
      // overlay.modal.background (surface.900). WCAG AA body text >= 4.5.
      expect(contrastRatio(surface[0], surface[900])).toBeGreaterThanOrEqual(4.5)
    })
  }
})
