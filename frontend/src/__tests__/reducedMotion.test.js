import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve, join } from 'node:path'

/* global process */
// Pure file read; vitest root is frontend/, so cwd-relative is stable in jsdom too.
const SRC = resolve(process.cwd(), 'src')

// The test files themselves quote the patterns they assert on, so they are not
// part of the surface under test.
function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (name === '__tests__') continue
    const p = join(dir, name)

    if (statSync(p).isDirectory()) walk(p, out)
    else if (name.endsWith('.css') || name.endsWith('.vue')) out.push(p)
  }

  return out
}

const files = walk(SRC).map((path) => ({
  path: path.slice(SRC.length + 1).replace(/\\/g, '/'),
  src: readFileSync(path, 'utf8'),
}))

describe('reduced motion is an alternative, not a blanket kill (WCAG 2.3.3)', () => {
  it('finds source files to check', () => {
    expect(files.length).toBeGreaterThan(20)
  })

  it('no file freezes animations with a near-zero duration', () => {
    const offenders = files
      .filter((f) => /animation-duration:\s*0\.01ms/.test(f.src))
      .map((f) => f.path)

    expect(offenders).toEqual([])
  })

  it('no file freezes transitions with a near-zero duration', () => {
    const offenders = files
      .filter((f) => /transition-duration:\s*0\.01ms/.test(f.src))
      .map((f) => f.path)

    expect(offenders).toEqual([])
  })

  it('every @keyframes owner declares its own reduced-motion alternative', () => {
    const owners = files.filter((f) => f.src.includes('@keyframes'))
    expect(owners.length).toBeGreaterThan(10)

    const missing = owners
      .filter((f) => !f.src.includes('prefers-reduced-motion'))
      .map((f) => f.path)

    expect(missing).toEqual([])
  })
})
