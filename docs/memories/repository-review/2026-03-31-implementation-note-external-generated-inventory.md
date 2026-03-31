---
date: 2026-03-31
feature: repository-review
type: implementation-note
related_specs:
  - /docs/specs/system-overview/spec.md
  - /docs/specs/public-surface-coverage.md
related_decisions: []
status: active
---

# External and generated tree inventory

## Context

The repository-wide review explicitly separated authored code review from low-signal or non-authored trees on disk. This note records that inventory so coverage is explicit rather than implied.

## Inventory

| Tree | Files | Size | Sampled contents | Classification |
| --- | ---: | ---: | --- | --- |
| `internal_kb_fullstack/frontend/node_modules` | 17,309 | 406M | package payloads and transitive dependencies | third-party |
| `internal_kb_fullstack/frontend/.next` | 3,018 | 85M | manifests, `standalone/server.js`, route type output, build traces | generated |
| `internal_kb_fullstack/backend/.venv` | 6,773 | 176M | Python executables, wheels, installed libraries | generated/local environment |
| `internal_kb_fullstack/backend/.venv312` | 4,462 | 102M | second Python environment | generated/local environment |
| `output` | 1 | 504K | `KnowledgeHub-review-2026-03-30.zip` | generated artifact |

Representative evidence:

- `.next` sample: `fallback-build-manifest.json`, `types/routes.d.ts`, `standalone/server.js`, `required-server-files.json`
- `.venv` sample: `bin/pytest`, `bin/uvicorn`, `bin/httpx`, activation scripts
- `output` sample: `output/KnowledgeHub-review-2026-03-30.zip`

## Review method

The inventory pass used:

- file counts and size summaries
- representative file sampling
- origin classification: authored, third-party, generated, or local environment
- anomaly check for unexpected repository-owned logic hidden inside generated trees

The review did not treat these trees as first-class authored code because:

- `node_modules` is external supply-chain content
- `.next` is build output from authored frontend sources
- `.venv` and `.venv312` are environment material
- `output` is artifact storage rather than runtime logic

## Observations

### `frontend/node_modules`

- Large but expected for a Next.js and React stack.
- Supply-chain review should focus on lockfiles and declared dependencies, not on line-by-line inspection of installed packages.

### `frontend/.next`

- Output is consistent with a recent successful build.
- Presence of `standalone/server.js` and multiple manifest files confirms that build artifacts are being kept locally.
- This tree should not be used as a source of truth for application behavior.

### `backend/.venv` and `backend/.venv312`

- Two separate virtual environments are present.
- This is not a correctness bug by itself, but it does create operational ambiguity about which interpreter environment is authoritative.

### `output`

- The tracked worktree currently contains a generated ZIP artifact outside the docs tree.
- It is low-risk, but it is operational noise and should remain outside spec or memory authority.

## Risks

- Duplicate virtualenvs can hide “works on my machine” drift when contributors run different interpreter builds.
- Generated output under `.next` and `output/` can confuse repository-level reviews if not explicitly classified.
- Third-party trees were not audited for package-level CVEs in this pass; that requires dependency-focused tooling, not repository code review.

## Impact

- Coverage is now explicit: these trees were reviewed as inventory and risk surfaces, not as authored behavior.
- This keeps the repository-wide review honest about what was and was not treated as source-of-truth code.

## Follow-up

- If dependency or runtime-environment hardening becomes a priority, run a dedicated supply-chain pass rather than expanding normal code review into generated trees.
