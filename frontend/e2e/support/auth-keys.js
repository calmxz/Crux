// #518: throwaway signing key for e2e sign-in, so specs can make real
// authenticated calls to the e2e backend without a real Supabase.
//
//   node e2e/support/auth-keys.js
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
import { generateKeyPairSync } from 'node:crypto'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const AUTH_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '.auth')

export const PRIVATE_KEY_PATH = join(AUTH_DIR, 'private.pem')

export const KID = 'crux-e2e'

// Must equal the backend's SUPABASE_URL (e2e.yml): the token's `iss` is this
// plus /auth/v1.
export const ISSUER_ORIGIN = 'http://e2e-auth.invalid'

function writeKeys() {
  const { publicKey, privateKey } = generateKeyPairSync('rsa', { modulusLength: 2048 })
  const jwk = { ...publicKey.export({ format: 'jwk' }), kid: KID, alg: 'RS256', use: 'sig' }

  mkdirSync(join(AUTH_DIR, 'jwks'), { recursive: true })
  writeFileSync(PRIVATE_KEY_PATH, privateKey.export({ type: 'pkcs8', format: 'pem' }))
  writeFileSync(join(AUTH_DIR, 'jwks', 'jwks.json'), JSON.stringify({ keys: [jwk] }))
  console.log(`[OK] e2e signing key written to ${AUTH_DIR}`)
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  writeKeys()
}
