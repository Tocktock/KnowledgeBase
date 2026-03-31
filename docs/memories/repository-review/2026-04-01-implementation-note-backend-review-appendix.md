---
date: 2026-04-01
feature: repository-review
type: implementation-note
related_specs:
  - /docs/specs/system-overview/spec.md
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/document-authoring/spec.md
  - /docs/specs/concepts/spec.md
  - /docs/specs/glossary-validation/spec.md
  - /docs/specs/sync-status/spec.md
related_decisions:
  - /docs/decisions/0003-document-links-are-a-projection.md
  - /docs/decisions/0005-workspace-data-connectors.md
status: active
---

# Implementation note: backend review appendix

## Context

This appendix covers backend-owned behavior in the current working tree:

- route modules under `internal_kb_fullstack/backend/app/api/routes`
- services under `internal_kb_fullstack/backend/app/services`
- schemas, models, SQL migrations, config/security helpers
- import and operational scripts under `internal_kb_fullstack/backend/scripts`
- the current regression suite under `internal_kb_fullstack/backend/tests`

Verification baseline:

- `cd internal_kb_fullstack/backend && ./.venv/bin/pytest -q` => `112 passed in 2.50s`
- direct current-tree probes were run for `list_recent_jobs()` and `request_document_reindex()`

## Findings

### P1. Sync Status connector-job reads fail at runtime

Severity:

- `P1`

Spec reference:

- `docs/specs/sync-status/spec.md:22-49`
- `docs/specs/public-surface-coverage.md`

Code reference:

- `internal_kb_fullstack/backend/app/api/routes/admin.py:17-38`
- `internal_kb_fullstack/backend/app/services/jobs.py:11-12,140-150,244-252`
- `internal_kb_fullstack/backend/tests/test_admin_routes.py:11-46`

Observed behavior:

- `list_recent_jobs()` joins `ConnectorConnection` at `jobs.py:147`, and `get_job_summary()` fetches it at `jobs.py:250`.
- `ConnectorConnection` is not imported in `jobs.py`.
- Direct probe:
  - `.venv/bin/python ... await list_recent_jobs(session, workspace_id=UUID(...))`
  - output => `NameError: name 'ConnectorConnection' is not defined`

Ontology impact:

- The persisted job ontology includes embedding, glossary, and connector sync jobs, but the admin inspection surface cannot execute the connector branch inside the workspace boundary it claims to model.

Recommendation:

- Import `ConnectorConnection` into `jobs.py`.
- Add one non-mocked success-path route test for `/v1/jobs` and one service test that exercises connector-job scoping with a workspace id.

### P2. Document reindex couples write maintenance to member-visible reads

Severity:

- `P2`

Spec reference:

- `docs/specs/document-authoring/spec.md:28-32,53-60`
- `docs/specs/document-authoring/contracts.md:91-97`

Code reference:

- `internal_kb_fullstack/backend/app/api/routes/documents.py:354-365`
- `internal_kb_fullstack/backend/app/services/jobs.py:63-82`
- `internal_kb_fullstack/backend/app/services/catalog.py:115-127`

Observed behavior:

- `reindex_document_route()` delegates to `request_document_reindex(...)`.
- `request_document_reindex()` resolves the target through `get_document_detail(session, document_id, workspace_id=workspace_id)` with no `include_evidence_only=True`.
- Direct probe of the current function call showed only `workspace_id` was forwarded to `get_document_detail()`, so the helper keeps its default `include_evidence_only=False`.
- `catalog.py:125-126` then filters to `Document.visibility_scope == member_visible`.

Ontology impact:

- The write-side document lifecycle is incorrectly coupled to the member-facing read ontology.
- Workspace-authorized maintenance cannot fully operate on legitimate evidence artifacts.

Recommendation:

- Use a write-authorized document lookup for reindex instead of the member-visible read helper.
- Add a route or service test covering reindex of an `evidence_only` document inside the current workspace.

### P3. Sample corpus import still flattens provenance and owner semantics

Severity:

- `P3`

Spec reference:

- `docs/specs/system-overview/spec.md:70-81`
- `docs/specs/search-and-docs/spec.md:38-69`

Code reference:

- `internal_kb_fullstack/backend/scripts/import_sample_corpus.py:95-112`
- `internal_kb_fullstack/backend/scripts/import_sample_corpus.py:182-199`
- `internal_kb_fullstack/backend/app/schemas/documents.py:13-30`

Observed behavior:

- `infer_owner_team()` infers owner groups from relative path substrings such as `platform`, `ml`, `design`, `product home`, `ios`, and Korean squad labels.
- the import payload sets `source_system=source_system`, `source_external_id=file.relative_path`, and `source_url=file.relative_path`
- the same import also marks the payload as a canonical document ingest rather than as a separate sample-only provenance class

Ontology impact:

- Sample bootstrap data can look more authoritative than it is.
- `source_url` ceases to be a reliable signal for a canonical external location, and `owner_team` becomes heuristic rather than authoritative source metadata.

Recommendation:

- Keep the sample corpus explicitly sample-only in operator expectations, or enrich the import with separate locator and owner-confidence metadata before relying on it in demos or policy reasoning.

## Areas now aligned

The following backend areas that drifted on 2026-03-31 now meet current specs:

- redirect normalization in auth and connector continuation flows
- role-sensitive evidence-only reads for documents and glossary support
- stable glossary public identity through `public_slug`
- document slug uniqueness consistency in the model layer
- staging and production secret requirements plus memory-note frontmatter enforcement

Representative evidence:

- redirect hardening: `internal_kb_fullstack/backend/app/core/redirects.py:17-42`
- evidence-only read enforcement: `internal_kb_fullstack/backend/app/api/routes/documents.py:53-63,257-345`
- stable glossary slug: `internal_kb_fullstack/backend/app/db/models.py:603-614`
- config and governance tests: `internal_kb_fullstack/backend/tests/test_config_security.py`, `internal_kb_fullstack/backend/tests/test_memory_notes_frontmatter.py`

## Coverage gaps now visible

- the passing backend suite still misses the Sync Status happy path
- reindex coverage does not currently prove evidence-only maintenance
- sample corpus import behavior is lightly operational and not strongly asserted by tests

## Impact

The backend is no longer broadly drifting from the repository specs. The remaining backend issues are concentrated in one admin runtime defect, one write-path authorization coupling, and one sample-corpus provenance weakness.
