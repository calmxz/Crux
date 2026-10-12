// #518: throwaway signing key for e2e sign-in, so specs can make real
// authenticated calls to the e2e backend without a real Supabase.
//
//   node e2e/support/gen-auth-keys.js
//
// writes a fresh RSA key pair under e2e/.auth/ (gitignored):
//   private.pem      read by the signIn helper to sign access tokens
//   jwks/jwks.json   the public half, served as the backend's JWKS
//
// Serve only the jwks/ directory, so the private key never goes over HTTP:
//   python -m http.server 8787 --bind 127.0.0.1 --directory e2e/.auth/jwks
// then start the backend with
//   SUPABASE_URL=http://e2e-auth.invalid
//   SUPABASE_JWKS_URL_OVERRIDE=http://127.0.0.1:8787/jwks.json
// The backend runs its normal JWKS verification; nothing in it is test-only.
import { generateKeyPairSync, randomUUID } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const AUTH_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '.auth')

const PRIVATE_KEY_PATH = join(AUTH_DIR, 'private.pem')

const JWKS_PATH = join(AUTH_DIR, 'jwks', 'jwks.json')

// Must equal the backend's SUPABASE_URL (e2e.yml): the token's `iss` is this
// plus /auth/v1.
export const ISSUER_ORIGIN = 'http://e2e-auth.invalid'

export function writeKeys() {
  const { publicKey, privateKey } = generateKeyPairSync('rsa', { modulusLength: 2048 })
  // A new kid per key pair: a running backend that cached the previous JWKS
  // sees an unknown kid and refetches, instead of checking the new key's
  // tokens against the old public key for up to an hour.
  const kid = `crux-e2e-${randomUUID()}`
  const jwk = { ...publicKey.export({ format: 'jwk' }), kid, alg: 'RS256', use: 'sig' }

  mkdirSync(dirname(JWKS_PATH), { recursive: true })
  writeFileSync(PRIVATE_KEY_PATH, privateKey.export({ type: 'pkcs8', format: 'pem' }))
  writeFileSync(JWKS_PATH, JSON.stringify({ keys: [jwk] }))
  console.log(`[OK] e2e signing key written to ${AUTH_DIR}`)
}

export function readSigningKey() {
  if (!existsSync(PRIVATE_KEY_PATH) || !existsSync(JWKS_PATH)) {
    throw new Error(
      `No e2e signing key in ${AUTH_DIR}. Run \`node e2e/support/gen-auth-keys.js\` ` +
        'and serve its jwks/ directory (see playwright.config.js).',
    )
  }

  return {
    kid: JSON.parse(readFileSync(JWKS_PATH, 'utf8')).keys[0].kid,
    privateKey: readFileSync(PRIVATE_KEY_PATH),
  }
}
