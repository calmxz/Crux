import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

/* global process */
// Pure file read; vitest root is frontend/, so cwd-relative is stable in jsdom too.
const css = readFileSync(resolve(process.cwd(), 'src/assets/base.css'), 'utf8')

const DARK_MARKER = "[data-theme='dark']"

const light = css.slice(0, css.indexOf(DARK_MARKER))

const dark = css.slice(css.indexOf(DARK_MARKER))

function hex(varName, block) {
  const re = new RegExp(`${varName}:\\s*(#[0-9a-fA-F]{6})`, 'g')
  const matches = [...block.matchAll(re)].map((m) => m[1])

  if (!matches.length) throw new Error(`token ${varName} not found`)

  return matches
}

function lum(h) {
  const c = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
  const l = c.map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))

  return 0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2]
}

const ratio = (a, b) => (Math.max(lum(a), lum(b)) + 0.05) / (Math.min(lum(a), lum(b)) + 0.05)

// Every ink that ever sets text, checked against the ground it sits on. The
// red mark (--ink-marker) is deliberately absent: it is a drawn mark only and
// does not clear 4.5:1 on paper, which is why --ink-marker-text exists.
const FOREGROUNDS = [
  '--color-text',
  '--color-text-muted',
  '--color-text-faint',
  '--color-accent-text',
  '--ink-marker-text',
  '--color-success-text',
  '--color-error-text',
  '--color-warning-text',
  '--color-info-text',
]

describe('base.css tokens', () => {
  for (const [themeName, block] of [
    ['light', light],
    ['dark', dark],
  ]) {
    it(`${themeName}: every text ink is >= 4.5:1 on --color-background in every block`, () => {
      const bgs = hex('--color-background', block)
      expect(bgs.length).toBeGreaterThan(0)

      for (const token of FOREGROUNDS) {
        const inks = hex(token, block)
        expect(inks.length, `${token} must be declared once per ${themeName} block`).toBe(
          bgs.length,
        )
        inks.forEach((ink, i) => {
          expect(
            ratio(ink, bgs[i]),
            `${token} on --color-background (${themeName})`,
          ).toBeGreaterThanOrEqual(4.5)
        })
      }
    })

    it(`${themeName}: --color-text-on-accent is >= 4.5:1 on --color-accent-strong`, () => {
      const fills = hex('--color-accent-strong', block)
      const labels = hex('--color-text-on-accent', block)
      expect(labels.length).toBe(fills.length)
      labels.forEach((label, i) => {
        expect(
          ratio(label, fills[i]),
          `filled control label (${themeName})`,
        ).toBeGreaterThanOrEqual(4.5)
      })
    })

    it(`${themeName}: --color-text-on-accent is >= 4.5:1 on --ink-marker-text-hover`, () => {
      const fills = hex('--ink-marker-text-hover', block)
      const labels = hex('--color-text-on-accent', block)
      expect(labels.length).toBe(fills.length)
      labels.forEach((label, i) => {
        expect(
          ratio(label, fills[i]),
          `confirm-delete hover label (${themeName})`,
        ).toBeGreaterThanOrEqual(4.5)
      })
    })

    // D-20 (WCAG 1.4.11 Non-text Contrast): the resting edge of a text control
    // is a UI component boundary and needs 3:1, which --card-edge (card chrome)
    // does not reach. --control-edge is the token controls use instead.
    it(`${themeName}: --control-edge is >= 3:1 on --card in every block`, () => {
      const cards = hex('--card', block)
      const edges = hex('--control-edge', block)
      expect(edges.length).toBe(cards.length)
      edges.forEach((edge, i) => {
        expect(
          ratio(edge, cards[i]),
          `--control-edge on --card (${themeName})`,
        ).toBeGreaterThanOrEqual(3)
      })
    })

    // WCAG 1.4.11: past-day columns in the Usage week chart are graphical
    // marks on --desk-deep and need 3:1.
    it(`${themeName}: --chart-bar-past is >= 3:1 on --desk-deep in every block`, () => {
      const grounds = hex('--desk-deep', block)
      const bars = hex('--chart-bar-past', block)
      expect(bars.length).toBe(grounds.length)
      bars.forEach((bar, i) => {
        expect(
          ratio(bar, grounds[i]),
          `--chart-bar-past on --desk-deep (${themeName})`,
        ).toBeGreaterThanOrEqual(3)
      })
    })

    it(`${themeName}: --tab-ink is >= 4.5:1 on every --tab-* fill`, () => {
      const inks = hex('--tab-ink', block)

      for (const tabToken of ['--tab-focus', '--tab-gaps', '--tab-mastered', '--tab-level']) {
        const fills = hex(tabToken, block)
        expect(fills.length).toBe(inks.length)
        fills.forEach((fill, i) => {
          expect(
            ratio(inks[i], fill),
            `${tabToken} tab label (${themeName})`,
          ).toBeGreaterThanOrEqual(4.5)
        })
      }
    })
  }
})

// --- Drift guard: dark tokens are declared twice (attribute override +
// prefers-color-scheme media query, for users who never toggle explicitly).
// This walks the raw file by selector, not the light/dark slices above, so it
// can tell the two dark blocks apart from each other and from :root.
function blockBody(fullCss, selectorMarker) {
  const start = fullCss.indexOf(selectorMarker)

  if (start === -1) throw new Error(`selector "${selectorMarker}" not found in base.css`)
  const braceStart = fullCss.indexOf('{', start)
  let depth = 1
  let i = braceStart + 1

  while (depth > 0) {
    if (fullCss[i] === '{') depth++
    else if (fullCss[i] === '}') depth--
    i++
  }

  return fullCss.slice(braceStart + 1, i - 1)
}

function customPropNames(body) {
  const re = /--[a-z0-9-]+(?=\s*:)/g

  return new Set([...body.matchAll(re)].map((m) => m[0]))
}

function setDiff(a, b) {
  return [...a].filter((x) => !b.has(x))
}

describe('base.css dark-token drift guard', () => {
  // :root { ... } — matched with a trailing space+brace so it does not also
  // match :root[data-theme='dark'] or :root:not([data-theme='light']).
  const lightNames = customPropNames(blockBody(css, ':root {'))
  const darkAttrNames = customPropNames(blockBody(css, ":root[data-theme='dark']"))
  const darkMediaNames = customPropNames(blockBody(css, ":root:not([data-theme='light'])"))

  it('declares the same tokens in the attribute-dark and media-dark blocks', () => {
    const onlyInAttr = setDiff(darkAttrNames, darkMediaNames)
    const onlyInMedia = setDiff(darkMediaNames, darkAttrNames)
    expect(
      onlyInAttr.length + onlyInMedia.length,
      `tokens only in :root[data-theme='dark']: ${onlyInAttr.join(', ') || '(none)'}; tokens only in the prefers-color-scheme block: ${onlyInMedia.join(', ') || '(none)'}`,
    ).toBe(0)
  })

  // The light :root block additionally carries non-colour tokens (spacing,
  // motion, typography, radii) that dark never overrides, so the strictest
  // assertion that holds is subset-of, not set-equals.
  it('every dark-block token is also declared in :root (light)', () => {
    const missingFromLight = setDiff(darkAttrNames, lightNames)
    expect(
      missingFromLight,
      `dark tokens missing from :root: ${missingFromLight.join(', ') || '(none)'}`,
    ).toEqual([])
  })
})
