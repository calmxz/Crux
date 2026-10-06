# anti-slop provenance

- Source: https://github.com/dmmulroy/anti-slop (`skills/install-anti-slop/assets/anti-slop`)
- Source commit: unknown. Copied on 2026-10-03 from the `install-anti-slop` skill installed
  via the skills CLI (`~/.agents/.skill-lock.json`, skillFolderHash
  `89044d21c75a367eac1ddbaf208e650b1a7d5820`, which is a folder hash, not a commit).
- Installed paths: this directory; entry point `index.ts`. The `effect/` plugin is copied but not
  registered (no direct `effect` dependency).
- Nested vendor: `vendor/eslint-stylistic/` (see its own `LICENSE` and `UPSTREAM.md`).
- Local deviations to the plugin source: none.
- Config deviations (`frontend/.oxlintrc.json`): `no-module-mocking` and `no-runtime-typeof` are
  `"off"`. See `docs/decisions.md` (2026-10-03) and #470.
