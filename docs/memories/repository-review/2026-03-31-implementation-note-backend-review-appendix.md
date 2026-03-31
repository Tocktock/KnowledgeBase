---
date: 2026-03-31
feature: repository-review
type: implementation-note
related_specs:
  - /docs/specs/workspace-auth/spec.md
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/concepts/spec.md
  - /docs/specs/glossary-validation/spec.md
  - /docs/specs/sync-status/spec.md
related_decisions:
  - /docs/decisions/0003-document-links-are-a-projection.md
  - /docs/decisions/0005-workspace-data-connectors.md
status: active
---

# Backend review appendix

## Context

The backend review covered:

- database models and migration contracts
- auth, workspace, connector, document, search, glossary, and jobs services
- public API routes under `internal_kb_fullstack/backend/app/api/routes`
- operational scripts under `internal_kb_fullstack/backend/scripts`
- the current regression suite under `internal_kb_fullstack/backend/tests`

Verification baseline:

- `pytest -q` passed with `89` tests
- no backend contract changes were made during this review

## Findings

### P1. Open redirect chain across auth and connector completion

Evidence:

- `internal_kb_fullstack/backend/app/services/auth.py:112-140`
- `internal_kb_fullstack/backend/app/services/connectors.py:179-182`
- `internal_kb_fullstack/frontend/app/api/auth/google/callback/route.ts:6-20`
- `internal_kb_fullstack/frontend/app/api/connectors/[provider]/oauth/callback/route.ts:5-27`

Observation:

- backend sanitization accepts any string beginning with `/`
- protocol-relative values such as `//evil.example` therefore survive `_safe_return_path`
- frontend callback routes rehydrate those values with `new URL(path, base)`, which treats `//host` as an external target

Why this matters:

- the workspace-auth and connectors flows are carrying attacker-controlled redirect material across login state changes and OAuth completion
- the defect spans backend state storage and frontend redirect execution, so it is a system bug rather than a single-file bug

Recommended remediation:

- replace prefix-only checks with strict local-path validation
- reject `//`, `\\`, encoded variants that decode to protocol-relative forms, and control characters
- add explicit regression tests around malicious `return_to` inputs in auth and connector flows

### P1. Evidence-only visibility is not enforced on direct document reads

Evidence:

- browse/search filters: `internal_kb_fullstack/backend/app/services/catalog.py:13-33`, `internal_kb_fullstack/backend/app/services/search.py:199-223`, `internal_kb_fullstack/backend/app/services/search.py:470-488`
- detail helpers: `internal_kb_fullstack/backend/app/services/catalog.py:92-138`
- routes: `internal_kb_fullstack/backend/app/api/routes/documents.py:237-310`
- glossary support assembly: `internal_kb_fullstack/backend/app/services/glossary.py:951-1004`

Observation:

- the normal list and search surfaces correctly filter `Document.visibility_scope == member_visible`
- direct detail helpers only scope by `workspace_id`
- glossary concept detail joins `ConceptSupport` to `Document` without applying a visibility rule

Why this matters:

- the docs and glossary system claims that evidence-only corpora support validation without becoming ordinary member-browsable knowledge
- that ontology holds for search/list, but not for direct reads or support link expansion

Recommended remediation:

- centralize a reusable “member-visible read” guard for document reads
- apply it to slug detail, id detail, content, relations, and glossary support assembly
- add route tests for evidence-only documents to prove 404 or filtered behavior

### P2. Glossary slug identity is derived, ambiguous, and untested

Evidence:

- `internal_kb_fullstack/backend/app/services/glossary.py:226-227`
- `internal_kb_fullstack/backend/app/services/glossary.py:605-608`
- `internal_kb_fullstack/backend/app/services/glossary.py:1037-1051`
- `internal_kb_fullstack/backend/app/db/models.py:603-614`

Observation:

- `knowledge_concepts` persist `normalized_term` and `display_term`, but no dedicated slug field
- API summaries emit `slug=concept_slug(display_term)`
- slug lookup scans concepts and returns the first derived match

Why this matters:

- URL identity is not uniqueness-backed by storage
- changes to `display_term` change public routes
- two concepts with distinct normalized values can still collide after slugification

Recommended remediation:

- persist a unique, workspace-scoped public slug or move routes to a stable id-based key
- add collision tests for display-term variants that normalize differently but slugify identically

### P2. ORM/migration drift on document slug uniqueness

Evidence:

- model: `internal_kb_fullstack/backend/app/db/models.py:171-194`
- migration: `internal_kb_fullstack/backend/app/db/sql/011_workspace_scoped_verified_knowledge.sql:81-84`

Observation:

- the migration contract says document slugs are unique per workspace
- the ORM column still declares `unique=True`, which encodes a global uniqueness assumption

Why this matters:

- the repository now has two incompatible statements about document identity
- future schema bootstraps or local test DB creation can drift from the intended tenancy model

Recommended remediation:

- remove the global ORM uniqueness declaration and rely on the workspace-scoped constraint only
- add a schema assertion in tests or migration smoke checks

### P2. Security helpers silently fall back to development secrets

Evidence:

- `internal_kb_fullstack/backend/app/core/security.py:46-64`

Observation:

- token encryption and session hashing fall back to hard-coded development strings when env vars are absent

Why this matters:

- a production deployment can become insecure through omission instead of failing fast
- this is especially risky because connector tokens and session integrity both depend on these helpers

Recommended remediation:

- make secret presence mandatory outside an explicit development mode
- emit a startup failure instead of silently deriving keys from development literals

### P3. Job ontology is persisted, but worker execution ontology is absent

Evidence:

- models: `internal_kb_fullstack/backend/app/db/models.py:493-545`, `internal_kb_fullstack/backend/app/db/models.py:683-737`
- service aggregation: `internal_kb_fullstack/backend/app/services/jobs.py:107-205`
- admin routes: `internal_kb_fullstack/backend/app/api/routes/admin.py:14-38`

Observation:

- embedding, connector sync, glossary jobs, and validation runs are all first-class persisted entities
- however, no worker id, lease owner, runner hostname, or execution provenance is stored

Why this matters:

- Sync Status is modeled as job-centric rather than worker-centric
- this is workable for a single-process or low-complexity system, but it limits debugging once concurrent workers or retries matter operationally

Recommended remediation:

- decide whether worker identity is intentionally out of scope
- if not, add minimal execution provenance fields before the operational surface grows further

## Tests and coverage observations

The existing backend suite is healthy but does not currently prove the highest-risk edge cases:

- auth tests exercise ordinary `return_to` flows, but this review found no malicious protocol-relative redirect case
- search tests confirm evidence-only exclusion for assembled support hits, but direct document detail routes are not covered by the same visibility contract
- glossary route tests verify happy-path slug lookup, but not slug collision behavior

## Impact

- The backend architecture is coherent around workspace scope, document revisions, connector-owned ingestion, and glossary verification policy.
- The sharpest problems are not random defects; they are places where one layer of the intended ontology is enforced and another layer is not.

## Follow-up

- Fix order should be redirect chain, visibility enforcement, identity drift, then secret hardening and operational provenance.
