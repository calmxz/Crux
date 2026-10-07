import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { parse } from 'yaml'

import * as errorCodes from '@/lib/errorCodes.js'

/* global process */

// #464: the spec's x-error-codes block is the list's home. The frontend keeps
// only the codes it handles, so each must be a key there; a typo or a code the
// backend never sends fails here instead of silently never matching.
// CRLF on Windows checkouts; normalise before parsing.
const spec = parse(
  readFileSync(resolve(process.cwd(), '../docs/api/openapi.yaml'), 'utf8').replace(/\r\n/g, '\n'),
)

describe('errorCodes', () => {
  it('exports only codes listed in x-error-codes', () => {
    const listed = Object.keys(spec['x-error-codes'])
    const exported = Object.entries(errorCodes).filter(([name]) => name.startsWith('ERR_'))

    expect(exported.length).toBeGreaterThan(0)

    for (const [name, value] of exported) {
      expect(listed, `${name} = '${value}'`).toContain(value)
    }
  })
})
