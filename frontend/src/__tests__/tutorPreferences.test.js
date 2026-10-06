import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { TUTOR_PREFERENCES, preferenceValue } from '@/lib/tutorPreferences.js'

/* global process */

// The fallbacks mirror the MeResponse defaults and the option values mirror
// the enums in the API contract; read the YAML so a contract change that is
// not carried here fails loudly instead of drifting (#381).
// CRLF on Windows checkouts; the patterns below match on \n.
const openapi = readFileSync(resolve(process.cwd(), '../docs/api/openapi.yaml'), 'utf8').replace(
  /\r\n/g,
  '\n',
)

const SCHEMAS = {
  feedback: 'FeedbackPref',
  checkIns: 'CheckIns',
  replyLength: 'ReplyLength',
}

function contractEnum(schema) {
  const m = openapi.match(
    new RegExp(`\\n {4}${schema}:\\n {6}type: string\\n {6}enum: \\[([^\\]]+)\\]`),
  )

  if (!m) throw new Error(`enum for ${schema} not found in openapi.yaml`)

  return m[1].split(',').map((s) => s.trim())
}

function contractDefault(field) {
  const block = openapi.split('\n    MeResponse:\n')[1].split('\n\n')[0]
  const m = block.match(new RegExp(`\\n {8}${field}:\\n[^\\n]*\\n {10}default: (\\w+)`))

  if (!m) throw new Error(`MeResponse default for ${field} not found in openapi.yaml`)

  return m[1]
}

describe('tutorPreferences', () => {
  it('covers exactly the three tutor preferences', () => {
    expect(Object.keys(TUTOR_PREFERENCES)).toEqual(['feedback', 'checkIns', 'replyLength'])
  })

  it.each(Object.keys(SCHEMAS))('%s options match the contract enum', (key) => {
    const values = TUTOR_PREFERENCES[key].options.map((o) => o.value)
    expect(values).toEqual(contractEnum(SCHEMAS[key]))
  })

  it.each(Object.keys(SCHEMAS))('%s fallback matches the MeResponse default', (key) => {
    const { field, fallback } = TUTOR_PREFERENCES[key]
    expect(fallback).toBe(contractDefault(field))
  })

  it('every option has a label', () => {
    for (const { options } of Object.values(TUTOR_PREFERENCES)) {
      for (const opt of options) expect(opt.label).toBeTruthy()
    }
  })

  it('preferenceValue returns the stored choice, else the fallback', () => {
    expect(preferenceValue({ checkIns: 'often' }, 'checkIns')).toBe('often')
    expect(preferenceValue({}, 'checkIns')).toBe('sometimes')
    expect(preferenceValue(null, 'feedback')).toBe('hints')
    expect(preferenceValue(undefined, 'replyLength')).toBe('balanced')
  })
})
