---
date: 2026-04-01
feature: repository-review
type: implementation-note
related_specs:
  - /docs/specs/system-overview/spec.md
  - /docs/specs/public-surface-coverage.md
  - /docs/specs/workspace-auth/spec.md
  - /docs/specs/home-navigation-admin/spec.md
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/document-authoring/spec.md
  - /docs/specs/concepts/spec.md
  - /docs/specs/glossary-validation/spec.md
  - /docs/specs/sync-status/spec.md
related_decisions:
  - /docs/decisions/0001-canonical-write-boundary.md
  - /docs/decisions/0003-document-links-are-a-projection.md
  - /docs/decisions/0005-workspace-data-connectors.md
  - /docs/decisions/project-memory.md
status: active
---

# Implementation note: repository-wide code and ontology review

## Context

This note records a full current-tree review of repository-authored code and docs on 2026-04-01. The earlier planning baseline was not reused blindly because the live working tree had changed by the time this pass was executed.

Actual baseline captured during the review:

- `git status --porcelain=v1` showed a dirty tree with four modified frontend files, two authored untracked paths, and untracked `output/`.
- `git ls-files | wc -l` => `254`.
- `cd internal_kb_fullstack/backend && ./.venv/bin/pytest -q` => `112 passed in 2.50s`.
- `cd internal_kb_fullstack/frontend && npm run typecheck` => passed.
- `cd internal_kb_fullstack/frontend && npm run build` => passed.

This bundle supersedes the 2026-03-31 review as the current working-tree snapshot and uses `2026-04-01-implementation-note-reviewed-findings-remediation.md` as prior context rather than as a substitute for revalidation.

Appendices:

- [review checklist](./2026-04-01-implementation-note-review-checklist.md)
- [should-fix checklist](./2026-04-01-implementation-note-should-fix-checklist.md)
- [backend review appendix](./2026-04-01-implementation-note-backend-review-appendix.md)
- [frontend review appendix](./2026-04-01-implementation-note-frontend-review-appendix.md)
- [docs and governance review](./2026-04-01-implementation-note-docs-and-governance-review.md)
- [ontology and corpus review](./2026-04-01-rationale-ontology-and-corpus-review.md)
- [external and generated inventory](./2026-04-01-implementation-note-external-generated-inventory.md)

## Coverage summary

Tracked coverage ledger:

- total tracked files: `254`
- checklist bucket coverage: `225` tracked files across backend, frontend, specs, decisions, and memories
- authored current-tree deltas reviewed in addition to tracked files:
  - `docs/memories/concepts/2026-04-01-implementation-note-non-ascii-glossary-slug-canonicalization.md`
  - `internal_kb_fullstack/frontend/lib/path-segments.ts`
  - modified frontend slug-routing files under `app/api/documents/slug/[slug]`, `app/api/glossary/slug/[slug]`, `app/glossary/[slug]`, and `lib/api/server.ts`

On-disk inventory and corpus context:

- `sample-data/` remains ignored by `.gitignore` and was reviewed as corpus context rather than tracked source: `13,893` files / `71M`
- generated/local trees were inventory-classified rather than line-reviewed: `node_modules`, `.next`, `.venv*`, `.playwright-cli`, `.pytest_cache`, `egg-info`, `output`

## Cross-cutting findings

### P1. Sync Status admin job inspection is broken on the connector-job branch

Spec reference:

- `docs/specs/sync-status/spec.md:22-49`
- `docs/specs/public-surface-coverage.md`

Code reference:

- `internal_kb_fullstack/backend/app/api/routes/admin.py:17-38`
- `internal_kb_fullstack/backend/app/services/jobs.py:11-12,140-150,244-252`
- `internal_kb_fullstack/backend/tests/test_admin_routes.py:11-46`

Observed behavior:

- `/v1/jobs` and `/v1/jobs/{job_id}` are the backend contracts behind the admin Sync Status page.
- `list_recent_jobs()` and `get_job_summary()` both reference `ConnectorConnection`, but `jobs.py` imports only `ConnectorResource`, `ConnectorSyncJob`, `Document`, `EmbeddingJob`, `GlossaryJob`, `JobStatus`, and `KnowledgeConcept`.
- A direct probe in the current tree reproduced the failure:
  - `.venv/bin/python ... await list_recent_jobs(..., workspace_id=UUID(...))`
  - output => `NameError: name 'ConnectorConnection' is not defined`

Why it matters:

- The repository can still pass `pytest` because the current admin route tests cover authentication and authorization failure paths only.
- The admin-facing operational ontology says jobs are inspectable within the current workspace boundary, but one of the three job families is not executable.

### P2. Document authoring and maintenance drift from the owning spec on both read and write sides

Spec reference:

- `docs/specs/document-authoring/spec.md:24-32,53-60`
- `docs/specs/document-authoring/contracts.md:10-20,41-50,91-97`

Code reference:

- frontend access and write surface:
  - `internal_kb_fullstack/frontend/app/new/page.tsx:1-13`
  - `internal_kb_fullstack/frontend/app/new/manual/page.tsx:1-13`
  - `internal_kb_fullstack/frontend/app/new/upload/page.tsx:1-13`
  - `internal_kb_fullstack/frontend/app/new/definition/page.tsx:1-13`
  - `internal_kb_fullstack/frontend/components/auth/manage-access-guard.tsx:130-173`
  - `internal_kb_fullstack/frontend/components/editor/document-editor.tsx:345-361,451-486,651-688`
  - `internal_kb_fullstack/frontend/lib/types.ts:330-346`
- backend maintenance path:
  - `internal_kb_fullstack/backend/app/api/routes/documents.py:354-365`
  - `internal_kb_fullstack/backend/app/services/jobs.py:63-82`
  - `internal_kb_fullstack/backend/app/services/catalog.py:115-127`

Observed behavior:

- The spec still describes `/new*` as pages for an authenticated user, but the live UI requires an active workspace membership through `WorkspaceMemberGuard`.
- The spec still treats `visibility_scope` as part of the authoring request contract, but the frontend type and form payload omit it.
- The spec still owns a reindex workflow, but the current frontend has no reindex bridge or affordance.
- On the backend, `request_document_reindex()` uses `get_document_detail(..., workspace_id=...)` without `include_evidence_only=True`, so write-authorized maintenance inherits member-visible read filtering.

Why it matters:

- The surfaced authoring actor is `workspace member`, not generic `authenticated user`.
- The surfaced write ontology no longer lets users choose document visibility.
- Reindex is specified as part of document lifecycle maintenance, but it is not consistently available and does not fully support evidence-only documents.

### P2. The provenance contract still conflates canonical URLs with generic source locators

Spec reference:

- `docs/specs/system-overview/spec.md:70-81`
- `docs/specs/search-and-docs/spec.md:38-69`
- `docs/specs/search-and-docs/contracts.md:117-132`

Code reference:

- `internal_kb_fullstack/backend/app/schemas/documents.py:13-30`
- `internal_kb_fullstack/backend/scripts/import_sample_corpus.py:182-199`
- `internal_kb_fullstack/frontend/app/docs/[slug]/page.tsx:57-63`
- `internal_kb_fullstack/frontend/components/trust/trust-badges.tsx:23-30`
- `internal_kb_fullstack/frontend/lib/types.ts:1-8,22-39`

Observed behavior:

- Specs and UI wording treat `source_url` as a user-navigable original source URL.
- The sample corpus importer writes `source_url=file.relative_path`, and other codepaths also use non-HTTP locator-like values such as `glossary://concept/...`.
- Frontend docs and trust surfaces render `source_url` directly as outbound links.

Why it matters:

- The formal model contains one field serving two ontologically different purposes: external URL and source locator.
- Trust and provenance look aligned at a glance, but the field meaning is weaker than the spec language suggests.

### P2. Durable decision documents understate a now-live workspace-first connector model

Spec reference:

- `docs/specs/system-overview/spec.md:5-18`
- `docs/specs/connectors/spec.md:22-43`
- `docs/specs/workspace-auth/spec.md:22-36`

Decision and code reference:

- `docs/decisions/0005-workspace-data-connectors.md:3-5,102-105`
- `docs/decisions/project-memory.md:19-31`
- `internal_kb_fullstack/backend/app/db/models.py:233-345`

Observed behavior:

- Specs, models, and live routes all depend on workspace, membership, and workspace-owned connector state as current behavior.
- `0005` remains `Proposed`, and `project-memory.md` still lists the workspace-first connector migration as a pending follow-up.

Why it matters:

- This is not a runtime bug, but it is durable architecture drift.
- Future contributors could treat the current tenancy model as optional roadmap rather than a core invariant.

## Areas now aligned

The current tree closes most of the high-priority 2026-03-31 findings:

- redirect hardening is aligned in specs, backend normalizers, frontend continuation handling, and tests
- evidence-only document and glossary support reads are now role-sensitive
- concept public identity is now storage-backed through `public_slug`
- document slug uniqueness no longer has the old ORM-vs-migration contradiction
- memory-note frontmatter is now enforced through a repository test
- the current working-tree glossary slug canonicalization change is internally coherent and still passes frontend build and typecheck

## Conclusion

The repository is materially closer to its specs than it was on 2026-03-31, and most previously identified P1/P2 defects are now remediated. The remaining issues are narrower but still important:

1. a live Sync Status backend runtime defect
2. a document-authoring contract drift across UI and backend maintenance
3. a provenance ontology gap around `source_url`
4. stale decision-layer language around workspace-first connectors

No runtime or API changes were made in this pass. This bundle is analysis only.
