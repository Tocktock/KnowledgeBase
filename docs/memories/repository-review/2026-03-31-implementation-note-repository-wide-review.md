---
date: 2026-03-31
feature: repository-review
type: implementation-note
related_specs:
  - /docs/specs/system-overview/spec.md
  - /docs/specs/public-surface-coverage.md
  - /docs/specs/workspace-auth/spec.md
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/concepts/spec.md
  - /docs/specs/glossary-validation/spec.md
  - /docs/specs/home-navigation-admin/spec.md
  - /docs/specs/sync-status/spec.md
related_decisions:
  - /docs/decisions/0001-canonical-write-boundary.md
  - /docs/decisions/0003-document-links-are-a-projection.md
  - /docs/decisions/0005-workspace-data-connectors.md
status: active
---

# Repository-wide code and ontology review

## Context

This note records a repository-wide review requested on 2026-03-31 with two explicit lenses:

- implementation review across authored repository content
- ontology review across business/domain semantics and formal entity-state-relation modeling

The review used two coverage layers:

- deep review of tracked authored repository content
- inventory and risk review of large generated or third-party trees on disk

Baseline evidence captured during the review:

- `git ls-files | wc -l` => `243`
- tracked implementation-bearing groups reviewed => `161` files / `28,224` lines
- `cd internal_kb_fullstack/backend && .venv/bin/pytest -q` => `89 passed in 2.07s`
- `cd internal_kb_fullstack/frontend && npm run typecheck` => passed
- `cd internal_kb_fullstack/frontend && npm run build` => passed

Appendices:

- [backend review appendix](./2026-03-31-implementation-note-backend-review-appendix.md)
- [frontend review appendix](./2026-03-31-implementation-note-frontend-review-appendix.md)
- [ontology and corpus review](./2026-03-31-rationale-ontology-and-corpus-review.md)
- [external and generated inventory](./2026-03-31-implementation-note-external-generated-inventory.md)

## Coverage ledger

### Tracked authored groups

| Group | Files | Lines | Coverage mode | Primary review lens |
| --- | ---: | ---: | --- | --- |
| root governance, scripts, manifests, runtime docs | 30 | 7,111 | read for repo rules, setup shape, script boundaries, artifact handling | governance, build surface, documentation drift |
| `docs/specs` | 25 | 2,192 | read as current behavior source of truth | spec/code drift, ontology contract |
| `docs/decisions` | 7 | 250 | read as durable invariants | architecture drift |
| existing `docs/memories` | 19 | 584 | read for intent history and doc governance | traceability hygiene |
| `backend/app` | 61 | 14,546 | deep-read behavior-bearing models, routes, services, schemas | security, tenancy, ontology, contract drift |
| `backend/scripts` | 4 | 742 | read import and operational tooling | corpus ingestion and provenance |
| `backend/tests` | 17 | 3,537 | read regression intent and gap coverage | missing test cases |
| `frontend/app` | 52 | 1,962 | deep-read routes and server entrypoints | redirect handling, access boundaries, surfaced ontology |
| `frontend/components` | 22 | 6,231 | read member/admin surfaces and link behavior | UI contract drift |
| `frontend/lib` | 6 | 1,226 | read typed public surface and proxy behavior | API/UI ontology alignment |

### On-disk inventory-only groups

| Tree | Files | Size | Coverage mode | Reason |
| --- | ---: | ---: | --- | --- |
| `internal_kb_fullstack/frontend/node_modules` | 17,309 | 406M | inventory only | third-party packages, not repository-authored logic |
| `internal_kb_fullstack/frontend/.next` | 3,018 | 85M | inventory only | generated build output |
| `internal_kb_fullstack/backend/.venv` | 6,773 | 176M | inventory only | local virtualenv |
| `internal_kb_fullstack/backend/.venv312` | 4,462 | 102M | inventory only | second local virtualenv |
| `output` | 1 | 504K | inventory only | generated artifact |

### Corpus coverage

`sample-data/` was reviewed as repository-owned corpus rather than executable code:

- `13,893` files / `71M`
- dominated by `sample-data/sendy-knowledge`
- top-level distribution is overwhelmingly `Product Home`, with a smaller `센디 iOS 차량정리` branch
- representative Markdown and CSV files were inspected together with the import pipeline in `internal_kb_fullstack/backend/scripts/import_sample_corpus.py`

### Explicit blind spots

- Generated and third-party trees were not reviewed line by line; they were classified by origin, file counts, representative samples, and operational risk.
- The sample corpus was not semantically validated document by document; review focused on structure, naming, provenance, and the ontology implied by the import pipeline.

## Cross-cutting findings

| Severity | Finding | Evidence | Impact |
| --- | --- | --- | --- |
| P1 | Auth and connector return paths accept protocol-relative targets, completing an open redirect chain. | `internal_kb_fullstack/backend/app/services/auth.py:112-140`, `internal_kb_fullstack/backend/app/services/connectors.py:179-182`, `internal_kb_fullstack/frontend/app/api/auth/google/callback/route.ts:6-20`, `internal_kb_fullstack/frontend/app/api/connectors/[provider]/oauth/callback/route.ts:5-27`, `internal_kb_fullstack/frontend/app/login/page.tsx:70-151` | A crafted `return_to=//host` can survive sanitization and become an external redirect after login or connector OAuth completion. |
| P1 | Evidence-only documents are filtered in browse/search flows but remain readable through direct document-detail and glossary-support paths. | `internal_kb_fullstack/backend/app/services/catalog.py:13-33`, `internal_kb_fullstack/backend/app/services/catalog.py:92-138`, `internal_kb_fullstack/backend/app/api/routes/documents.py:237-310`, `internal_kb_fullstack/backend/app/services/glossary.py:951-1004`, `internal_kb_fullstack/frontend/app/glossary/[slug]/page.tsx:127-144` | The member-visible ontology boundary can be bypassed by direct links, which weakens the spec promise around evidence-only corpora. |
| P2 | Glossary route identity is derived from `display_term` instead of a persisted unique slug. | `internal_kb_fullstack/backend/app/services/glossary.py:226-227`, `internal_kb_fullstack/backend/app/services/glossary.py:605-608`, `internal_kb_fullstack/backend/app/services/glossary.py:1037-1051`, `internal_kb_fullstack/backend/app/db/models.py:612-614` | Distinct concepts can converge on the same public slug, making concept URLs ambiguous and unstable. |
| P2 | Document slug uniqueness is workspace-scoped in the migration contract but still globally unique in ORM declarations. | `internal_kb_fullstack/backend/app/db/models.py:171-194`, `internal_kb_fullstack/backend/app/db/sql/011_workspace_scoped_verified_knowledge.sql:81-84` | The storage ontology and model ontology disagree; future schema generation or test setup can accidentally reintroduce a global constraint. |
| P2 | Memory-note governance is enforced by convention but not by repository state. Several tracked notes are missing required frontmatter. | `docs/memories/README.md:21-31`, `docs/memories/connectors/2026-03-30-intent-workspace-safe-ingestion-and-slack-readiness.md`, `docs/memories/glossary-validation/2026-03-30-intent-verification-policy-gated-approval.md`, `docs/memories/search-and-docs/2026-03-30-intent-workspace-bounded-retrieval.md`, `docs/memories/system-overview/2026-03-30-intent-workspace-scoped-verified-knowledge-foundation.md` | The repo’s stated traceability contract is already drifting, which weakens spec-driven governance. |
| P3 | Security helpers fall back to stable development secrets when env vars are absent. | `internal_kb_fullstack/backend/app/core/security.py:46-64` | Production misconfiguration can silently degrade token secrecy instead of failing closed. |

## Ontology conclusions

### Business/domain ontology

- `workspace` is the primary business boundary. Search, docs, glossary, connectors, overview, and admin surfaces all resolve behavior from workspace context.
- `knowledge` is intentionally split into two business audiences: member-visible documents and evidence-only support material.
- `concept` is a curated domain object with its own lifecycle and review policy, not just a document tag.
- `connector` is modeled as an ownership and synchronization pipeline rather than just an auth token.
- `job` is an operator-facing readiness surface, not the main end-user ontology.

### Formal entity-state-relation ontology

- Identity is persistent for workspaces, users, sessions, documents, revisions, chunks, connector resources, source items, jobs, and concepts.
- State machines are explicit for documents, jobs, connector status, concept status, validation state, and verification state.
- The biggest formal drift is between persisted identity and surfaced identity:
  - concepts persist `normalized_term` uniqueness but expose a derived slug
  - documents migrate toward workspace-scoped uniqueness but one ORM field still declares global uniqueness
  - evidence-only is formal on `documents.visibility_scope`, but not uniformly enforced across read paths
- Worker identity is absent from the formal model. Jobs exist, but no lease owner, worker id, or execution provenance is persisted.

## Spec versus implementation versus UI drift

| Topic | Spec ontology | Implemented ontology | Surfaced UI ontology | Drift |
| --- | --- | --- | --- | --- |
| evidence-only visibility | `connectors`, `search-and-docs`, and `glossary-validation` treat evidence-only as non-browsable member knowledge | list/search paths filter `member_visible`, but direct detail and glossary support assembly do not | glossary detail renders support links as ordinary doc links | visibility contract is only partially enforced |
| concept public identity | concepts behave like stable knowledge objects | concept route key is recalculated from `display_term` on every read | UI links concepts by derived slug | public identity is unstable and not uniqueness-backed |
| workspace-scoped document identity | workspace is the primary tenancy boundary | migration scopes document slug uniqueness by workspace | UI and APIs assume slug is workspace-relative | ORM declaration still implies global uniqueness |
| job/worker modeling | sync-status is an admin-facing operational surface | jobs are persisted, but worker execution identity is absent | UI exposes job summaries only | worker ontology is implicit rather than modeled |
| documentation governance | every memory note carries structured metadata | multiple tracked notes omit frontmatter | no UI surface | governance contract has no enforcement mechanism |

## Prioritized remediation backlog

1. Close the redirect chain by rejecting protocol-relative or otherwise non-local `return_to` values in both backend and frontend entrypoints, and add regression tests for `//...`, backslash-prefixed, and control-character variants.
2. Enforce `member_visible` filtering on document detail, content, relations, and glossary support assembly, then add route-level tests proving evidence-only material cannot be opened through direct links.
3. Introduce a persisted, uniqueness-backed glossary route identity or expose canonical concept ids in the public route model, and add collision tests.
4. Reconcile the `Document.slug` ORM declaration with migration `011_workspace_scoped_verified_knowledge.sql` so the model, migrations, and tests all encode the same tenancy contract.
5. Add repository linting or CI checks for memory-note frontmatter to keep the documentation governance rules enforceable.
6. Fail closed when encryption and session secrets are unset outside an explicit development mode.

## Impact

- The repository now has a documented review artifact set under `docs/memories/repository-review/`.
- The findings connect behavior drift back to the owning specs and decisions rather than treating the review as a detached audit.
- The ontology appendix records where the current data model is coherent and where identity and visibility semantics still drift.

## Follow-up

- This pass did not change runtime behavior, APIs, schemas, or types.
- A follow-up implementation pass should fix the P1 items first, then the identity and governance drift.
