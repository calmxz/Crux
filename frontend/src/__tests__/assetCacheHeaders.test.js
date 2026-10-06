import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

/* global process */

// F-17: Vite content-hashes every file under /assets/, so those responses can
// be cached for a year. Both deploy fronts (Vercel for the hosted build, nginx
// for the docker compose stack) must say so, and neither may lose the security
// headers doing it.

const read = (p) => readFileSync(resolve(process.cwd(), p), 'utf8')

describe('F-17: immutable caching for hashed assets', () => {
  it('vercel.json long-caches /assets/ and keeps the security header block', () => {
    const cfg = JSON.parse(read('vercel.json'))
    const assets = cfg.headers.find((h) => h.source === '/assets/(.*)')
    expect(assets).toBeDefined()
    expect(assets.headers).toEqual([
      { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
    ])
    // The catch-all security block must still be there: Vercel applies every
    // matching entry, so the asset entry adds to it rather than replacing it.
    const all = cfg.headers.find((h) => h.source === '/(.*)')
    expect(all.headers.map((h) => h.key)).toContain('X-Content-Type-Options')
  })

  it('nginx sets asset Cache-Control from the server block, not the location', () => {
    const conf = read('nginx.conf')
    expect(conf).toMatch(/map \$uri \$asset_cache \{/)
    expect(conf).toContain('"public, max-age=31536000, immutable"')
    expect(conf).toContain('add_header Cache-Control $asset_cache always;')
    // An add_header inside location /assets/ would silently drop every
    // server-block add_header (CSP, HSTS, X-Frame-Options) for asset
    // responses. `expires` there would emit a second, conflicting header.
    // lastIndexOf: the phrase also appears in the explanatory comments above.
    const loc = conf.slice(conf.lastIndexOf('location /assets/'))
    const body = loc.slice(0, loc.indexOf('}'))
    expect(body).not.toContain('add_header')
    expect(body).not.toContain('expires')
  })
})
