# Tools

**Draft: not locked.** Part of the [Crux v1 spec](README.md). Terms are as [`GLOSSARY.md`](../../GLOSSARY.md) defines them.

This file covers the tools the backend and the frontend are built with, and how each side's API code comes from the contract. Where the code runs is in [`hosting.md`](hosting.md). The checks that guard the repo are in [`quality-bar.md`](quality-bar.md), and the tests in [`ordinary-tests.md`](ordinary-tests.md).

## Terms

These are build terms, so they stay out of the glossary.

- **Gap rule:** one of the four ESLint rules oxlint lacks, which ESLint runs after oxlint ([#769]).
- **Tools package:** a separate `package.json` and lockfile for a tool that needs an older TypeScript than the app ([#769]).

## The backend's tools

- Python 3.14, uv for dependencies and the lockfile, ruff for style, basedpyright for types ([#750]).
- The API is contract-first. `docs/api/openapi.yaml` is written by hand, `gen_contracts.py` generates the request and response models from it, and CI fails on drift between them ([#750]).

## The frontend's tools

- TypeScript 7 for the app and its type check (`tsc`, no emit), and for oxlint, including oxlint's type-aware rules ([#769]).
- Vite builds, Prettier formats, and Vitest runs the component tests with React Testing Library ([#769]).
- The Node version, npm and the lockfile are left to the build ticket ([#769]).

### Lint

- Lint is `oxlint && eslint`, on the owner's computer and in CI ([#769]).
- ESLint 9 runs only the four gap rules: `react/jsx-no-leaked-render`, `react/no-typos`, `react/no-invalid-html-attribute` and `require-atomic-updates` ([#769]).
- `eslint-plugin-oxlint` turns off every rule oxlint already runs. The build ticket checks that the oxlint config loads, so ESLint never falls back to all its rules ([#769]).
- ESLint and its TypeScript parser sit in a tools package on TypeScript 6.0, since that parser does not accept 7 ([#769]).
- osv-scanner and Dependabot cover the tools package's lockfile as well as the app's. Dependabot does not propose a new TypeScript major there: the tools package has its own Dependabot entry, which ignores TypeScript's major version updates ([#769]).

### The API on the frontend

- The API is contract-first on the frontend too. Hey API (`@hey-api/openapi-ts`) generates the types, a fetch client and TanStack Query options from `docs/api/openapi.yaml`, and the reply stream as typed events ([#769]).
- CI fails on drift between the YAML and the generated files ([#769]).
- Hey API is pinned to an exact version. Each bump is read before it merges, since Hey API is before 1.0 ([#769]).
- The build ticket sets the command and where the generated files sit ([#769]).

### Build checks

The build ticket checks three things ([#769]):

1. That Hey API runs on TypeScript 7.
2. That ESLint on TypeScript 6.0 reads the app's `tsconfig`.
3. That the YAML's description of the reply stream works for both Hey API and `gen_contracts.py`.

If the third check fails, the stream's events are written as named schemas in the YAML, each with its own `type` field, joined as one union on the stream's response ([#769]).

### The fallback

If either of the first two checks fails ([#769]):

- TypeScript 6.0 everywhere, Hey API kept, ESLint in the app's own install, and the type-aware rules run by ESLint's typescript-eslint.
- Only if Hey API itself is dropped does the app go to TypeScript 5.9, with `openapi-typescript`, `openapi-fetch` and `openapi-react-query`, and the type-aware rules in ESLint.

[#750]: https://github.com/calmxz/Crux/issues/750
[#769]: https://github.com/calmxz/Crux/issues/769
