# CI Security Inventory — Crux

**Audience:** future maintainers ("why is this CI job here?")
**Companion to:** `.github/workflows/ci.yml`. The 2026-05-23 security review it was written against is archived in git history (see `docs/decisions.md`).
**Phase introduced:** Phase 6 (`phase/6-ci-security-tests`, 2026-05-23).

Every job below blocks PR merge: branch protection is live on `dev` (staging)
and `main` (prod). See "Branch protection — current state" at the end of this
file.

---

## SAST and code analysis

| Tool | Catches | Where | Fail threshold | Upstream |
|---|---|---|---|---|
| **bandit** | Python SAST: insecure use of `subprocess`, weak crypto, `eval`, hardcoded secrets, etc. | `security` job in `ci.yml` | `-lll -iii` (high severity + high confidence only — suppresses noise) | https://bandit.readthedocs.io |
| **semgrep** | Cross-language pattern-based rules: OWASP top-10 + security-audit ruleset | `security` job in `ci.yml` | Any rule match (`semgrep ci --error`) | https://semgrep.dev |
| **CodeQL** | GitHub-native semantic analysis for Python + JavaScript/TypeScript | `.github/workflows/codeql.yml` | Default `security-and-quality` query pack | https://codeql.github.com |

## Dependency and supply-chain

| Tool | Catches | Where | Fail threshold | Upstream |
|---|---|---|---|---|
| **pip-audit** | Known CVEs in Python deps (resolves transitive tree from `pyproject.toml`) | `security` job in `ci.yml` | Any advisory | https://github.com/pypa/pip-audit |
| **npm audit** | Known CVEs in npm prod deps (skips devDeps) | `security` job in `ci.yml` | `--audit-level=high` | https://docs.npmjs.com/cli/v10/commands/npm-audit |
| **Dependabot** | Weekly automated PRs to bump outdated deps (pip + npm + github-actions + docker) | `.github/dependabot.yml` | Opens PRs, doesn't fail CI directly | https://docs.github.com/en/code-security/dependabot |

## Container and Dockerfile

| Tool | Catches | Where | Fail threshold | Upstream |
|---|---|---|---|---|
| **hadolint** (backend + frontend) | Dockerfile lint: unsafe `apt-get`, missing `USER`, latest tags, etc. | `security` job in `ci.yml` | `warning+` | https://github.com/hadolint/hadolint |
| **trivy** (backend image) | OS + lang-pkg CVEs in the built backend image | `security` job in `ci.yml` | `CRITICAL` only (with `ignore-unfixed`) | https://aquasecurity.github.io/trivy |
| **trivy** (frontend image) | OS + lang-pkg CVEs in the built frontend (nginx) image | `security` job in `ci.yml` | `CRITICAL` only | same |

## Secrets

| Tool | Catches | Where | Fail threshold | Upstream |
|---|---|---|---|---|
| **gitleaks** | API keys, tokens, private-key PEMs in full git history + PR diff | `security` job in `ci.yml` | Any leak | https://github.com/gitleaks/gitleaks |

## Coverage

| Tool | Purpose | Where | Threshold |
|---|---|---|---|
| **pytest-cov** | Enforces minimum backend coverage on `services/` + `lib/` | `backend/pyproject.toml` (`--cov-fail-under=75`) | 75% (current: ~92%) |
| **Codecov** | Trend visibility + PR coverage delta comments | `backend` + `frontend` jobs in `ci.yml` | No-op on failure (`fail_ci_if_error: false`) |

---

## Regression tests added in Phase 6

These tests lock the resolutions from the 2026-05-23 security review so a future
refactor reintroducing the finding will fail CI deterministically.

| Finding | Test | Location |
|---|---|---|
| H-3 (maxLength caps) | `test_field_rejects_above_max_length` / `test_field_accepts_at_max_length` (15 parametrized cases each) | `backend/tests/test_max_length_validation.py` |
| H-4 (sessions/end ownership 404) | `test_post_end_404_for_wrong_user` | `backend/tests/test_sessions_route.py` |
| H-4 (profile ownership 404) | `test_profile_route_404_for_wrong_user` (pre-existing, retained) | `backend/tests/test_profile_route.py` |
| H-5 (generic retrieval error, no internal leak) | `test_chroma_exception_returns_failed` + `test_chroma_exception_does_not_leak_internal_message` | `backend/tests/test_retrieval_service.py` |
| M-3 (chunk wrapper present + payload preserved + immutable-rule warns) | `test_retrieved_chunks_wrapped_as_untrusted_in_tool_message`, `test_immutable_rules_warn_about_document_excerpt_tags`, and citation-cleanliness assertion at line 155 (all pre-existing from Phase 3, retained) | `backend/tests/test_tutor_loop.py` |

---

## Branch protection — current state (verified 2026-09-23 via `gh api`)

Branch model:
- `dev` = staging (PRs land here first)
- `main` = production (promoted from `dev` after staging verification)

| Setting | `dev` | `main` |
|---|---|---|
| Required checks | `Backend (pytest)`, `Frontend (Vitest + lint)`, `Security (SAST + deps + secrets + images)`, `Analyze (javascript-typescript)` | same plus `Analyze (python)` |
| Required approving reviews | 1 (solo maintainer merges with `--admin`) | none |
| Include administrators (enforce_admins) | OFF | OFF |
| Require signed commits | OFF | ON |
| Force pushes / deletions | blocked | blocked |

Deviations from the Phase 6 plan, recorded in `docs/decisions.md` (2026-09-23):
`dev` requires one review instead of zero, `enforce_admins` is off on both,
`Playwright (chromium)` is not a required check, and `Analyze (python)` is
required on `main` only.

CodeQL: the `Analyze (*)` checks come from `.github/workflows/codeql.yml`
(advanced setup). GitHub's code-scanning *default setup* is `not-configured`.
GitHub does not allow both; enabling default setup would require removing
`codeql.yml` first.

Verify or reapply:

```bash
gh api repos/calmxz/Crux/branches/dev/protection --jq '.required_status_checks.contexts'
gh api repos/calmxz/Crux/branches/main/protection/required_signatures --jq '.enabled'
```
