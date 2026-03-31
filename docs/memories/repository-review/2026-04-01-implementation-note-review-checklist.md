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

# Implementation note: review checklist

## Scope and baseline

This checklist records the current working tree, not the previous commit and not the earlier 2026-04-01 planning baseline.

Actual baseline captured during this pass:

- `git status --porcelain=v1` =>
  - `M internal_kb_fullstack/frontend/app/api/documents/slug/[slug]/route.ts`
  - `M internal_kb_fullstack/frontend/app/api/glossary/slug/[slug]/route.ts`
  - `M internal_kb_fullstack/frontend/app/glossary/[slug]/page.tsx`
  - `M internal_kb_fullstack/frontend/lib/api/server.ts`
  - `?? docs/memories/concepts/`
  - `?? internal_kb_fullstack/frontend/lib/path-segments.ts`
  - `?? output/`
- `git ls-files | wc -l` => `254`
- `cd internal_kb_fullstack/backend && ./.venv/bin/pytest -q` => `112 passed in 2.50s`
- `cd internal_kb_fullstack/frontend && npm run typecheck` => passed
- `cd internal_kb_fullstack/frontend && npm run build` => passed

Current-tree authored deltas explicitly included in review scope:

- `docs/memories/concepts/2026-04-01-implementation-note-non-ascii-glossary-slug-canonicalization.md`
- `internal_kb_fullstack/frontend/lib/path-segments.ts`
- the four modified frontend slug-routing files listed above

## Feature and spec matrix

| area | sources reviewed | implementation surfaces | coverage mode | status | findings summary | evidence anchors |
| --- | --- | --- | --- | --- | --- | --- |
| `system-overview` | `docs/specs/system-overview/spec.md`; `docs/specs/public-surface-coverage.md` | backend models and route families; frontend app shell and primary route families | deep read + cross-feature reconciliation | `partially meets` | Core workspace/document/concept model is aligned, but the trust field `source_url` still behaves as a mixed URL or locator type in code and corpus import. | `docs/specs/system-overview/spec.md:70-81`; `internal_kb_fullstack/backend/scripts/import_sample_corpus.py:182-199`; `internal_kb_fullstack/frontend/app/docs/[slug]/page.tsx:57-63`; `internal_kb_fullstack/frontend/components/trust/trust-badges.tsx:23-30` |
| `workspace-auth` | `docs/specs/workspace-auth/spec.md`; `docs/specs/workspace-auth/contracts.md` | backend auth routes/services; frontend login and callback routes | deep read + regression check review | `meets` | Internal-path redirect normalization is aligned in spec, backend, frontend, and tests. | `docs/specs/workspace-auth/spec.md:37-40`; `internal_kb_fullstack/backend/app/core/redirects.py:17-42`; `internal_kb_fullstack/frontend/lib/internal-paths.ts:12-35`; `internal_kb_fullstack/backend/tests/test_auth_routes.py:411-420` |
| `home-navigation-admin` | `docs/specs/home-navigation-admin/spec.md`; `docs/specs/public-surface-coverage.md` | frontend home, review, jobs, and access-guard surfaces | deep read | `meets` | Home and operator surfaces preserve member/admin separation through shared guards and distinct no-workspace states. | `docs/specs/home-navigation-admin/spec.md:46-63`; `internal_kb_fullstack/frontend/components/auth/manage-access-guard.tsx:21-173`; `internal_kb_fullstack/frontend/components/home/workspace-home-page.tsx:47-190` |
| `connectors` | `docs/specs/connectors/spec.md`; `docs/specs/connectors/contracts.md` | backend connector models/routes/services; frontend setup and connectors UI | deep read | `meets` | Workspace-first connector behavior is implemented and matches feature specs; remaining drift is in durable decision docs, not feature behavior. | `docs/specs/connectors/spec.md:22-43`; `internal_kb_fullstack/backend/app/db/models.py:320-370`; `internal_kb_fullstack/frontend/components/connectors/connectors-page.tsx:1-1706`; `docs/decisions/0005-workspace-data-connectors.md:3-5` |
| `search-and-docs` | `docs/specs/search-and-docs/spec.md`; `docs/specs/search-and-docs/contracts.md` | backend catalog/search services and document routes; frontend docs/search/trust surfaces | deep read + current-tree runtime reasoning | `partially meets` | Evidence-only read rules now align, but provenance rendering still assumes `source_url` is a navigable original-source URL even when sample imports provide relative locators. | `docs/specs/search-and-docs/spec.md:38-69`; `internal_kb_fullstack/backend/app/services/catalog.py:92-127`; `internal_kb_fullstack/frontend/app/docs/[slug]/page.tsx:54-63`; `internal_kb_fullstack/frontend/components/trust/trust-badges.tsx:23-30` |
| `document-authoring` | `docs/specs/document-authoring/spec.md`; `docs/specs/document-authoring/contracts.md` | backend document write routes and jobs service; frontend `/new*` pages and editor | deep read + direct probes | `partially meets` | The live surface is stricter and narrower than the spec: UI requires active workspace membership, omits `visibility_scope`, does not surface reindex, and backend reindex excludes `evidence_only` documents. | `docs/specs/document-authoring/spec.md:28-32,53-60`; `docs/specs/document-authoring/contracts.md:10-20,41-50,91-97`; `internal_kb_fullstack/frontend/app/new/page.tsx:1-13`; `internal_kb_fullstack/frontend/components/editor/document-editor.tsx:345-361,451-486,651-688`; `internal_kb_fullstack/backend/app/services/jobs.py:63-82`; direct probe of `request_document_reindex()` showed `get_document_detail(..., workspace_id=...)` only |
| `concepts` | `docs/specs/concepts/spec.md`; `docs/specs/concepts/contracts.md` | backend glossary models/routes/services; frontend glossary pages and current-tree slug helper | deep read + current-tree delta review | `meets` | Stored `public_slug` identity is aligned end-to-end, and the current working-tree non-ASCII slug canonicalization change is coherent with that contract. | `docs/specs/concepts/spec.md:28-30`; `docs/specs/concepts/contracts.md:29-37,49-58`; `internal_kb_fullstack/backend/app/db/models.py:603-614`; `internal_kb_fullstack/frontend/app/glossary/[slug]/page.tsx:20-27`; `internal_kb_fullstack/frontend/lib/path-segments.ts:1-16` |
| `glossary-validation` | `docs/specs/glossary-validation/spec.md`; `docs/specs/glossary-validation/contracts.md` | backend validation/verification services and glossary support assembly; frontend review/request pages | deep read + test review | `meets` | Stable concept identity and role-sensitive evidence support now align with current specs and tests. | `docs/specs/glossary-validation/spec.md:47,122-123`; `internal_kb_fullstack/backend/app/services/glossary.py:1001-1061`; `internal_kb_fullstack/backend/tests/test_glossary_routes.py:482-600`; `internal_kb_fullstack/frontend/components/glossary/glossary-review-page.tsx:1-525` |
| `sync-status` | `docs/specs/sync-status/spec.md`; `docs/specs/public-surface-coverage.md` | backend jobs route/service; frontend `/jobs` page | deep read + direct runtime probe | `drifts` | The admin-only route contract exists, but connector-job reads fail at runtime because `ConnectorConnection` is referenced without import in `jobs.py`. | `docs/specs/sync-status/spec.md:22-49`; `internal_kb_fullstack/backend/app/api/routes/admin.py:17-38`; `internal_kb_fullstack/backend/app/services/jobs.py:11-12,140-150,244-252`; direct probe => `NameError: name 'ConnectorConnection' is not defined` |
| `public-surface-coverage` | `docs/specs/public-surface-coverage.md` | backend route modules; frontend page and proxy route files | spec-to-route inventory check | `meets` | The page/API ownership matrix is current for the live route families, including the current-tree glossary slug-routing changes. | `docs/specs/public-surface-coverage.md:5-60`; `internal_kb_fullstack/frontend/app`; `internal_kb_fullstack/backend/app/api/routes` |

## Implementation and documentation buckets

| area | sources reviewed | implementation surfaces | coverage mode | status | findings summary | evidence anchors |
| --- | --- | --- | --- | --- | --- | --- |
| `root governance and manifests` | `AGENTS.md`; `README.md`; `PRODUCT.md`; root `.gitignore`; runtime manifests | root governance pointers, env handling, inventory boundaries | deep read | `meets` | Root docs consistently route behavior authority to `/docs`; root `.gitignore` cleanly separates generated/local trees such as `.venv`, `.next`, `.playwright-cli`, and `sample-data`. | `README.md:3-13,37-46`; `.gitignore:1-14`; `docs/README.md:11-30` |
| `backend routes, services, schemas, models, SQL, scripts, tests` | `internal_kb_fullstack/backend/app/**`; `internal_kb_fullstack/backend/app/db/sql/**`; `internal_kb_fullstack/backend/tests/**` | auth, connectors, documents, search, glossary, jobs, config, import scripts | deep read + direct probes + test run | `partially meets` | Prior redirect, visibility, slug, and config drifts are fixed, but Sync Status has a live runtime defect, reindex couples write maintenance to member-visible reads, and sample import still flattens provenance. | `internal_kb_fullstack/backend/app/services/jobs.py:63-82,107-204,244-252`; `internal_kb_fullstack/backend/scripts/import_sample_corpus.py:95-112,182-199`; `internal_kb_fullstack/backend/tests/test_config_security.py:1-89`; `./.venv/bin/pytest -q` => `112 passed in 2.50s` |
| `frontend app routes, API bridge handlers, components, lib, store` | `internal_kb_fullstack/frontend/app/**`; `components/**`; `lib/**`; `store/**` | auth, docs, glossary, `/new*`, jobs, proxy routes, current-tree slug helpers | deep read + build/typecheck + current-tree delta review | `partially meets` | Redirect hardening and glossary slug canonicalization align, but document authoring and provenance-link behavior still drift from the owning specs/contracts. | `internal_kb_fullstack/frontend/app/new/page.tsx:1-13`; `internal_kb_fullstack/frontend/components/editor/document-editor.tsx:345-361,451-486,651-688`; `internal_kb_fullstack/frontend/app/docs/[slug]/page.tsx:57-63`; `npm run typecheck`; `npm run build` |
| `docs/specs` | `docs/specs/**` | all feature specs, contracts, flows, states, and public-surface inventory | deep read | `meets` | Feature specs are the current SoT and now reflect the March remediation work; remaining issues are mainly vocabulary gaps around provenance and one stale authoring contract. | `docs/specs/README.md:1-35`; `docs/specs/public-surface-coverage.md:5-60`; `docs/specs/document-authoring/spec.md:56-67`; `docs/specs/search-and-docs/spec.md:38-69` |
| `docs/decisions` | `docs/decisions/**` | ADRs and durable rule notes | deep read | `partially meets` | `0005` and `project-memory` still describe workspace-first connectors as proposed or pending even though specs and storage already rely on that model. | `docs/decisions/0005-workspace-data-connectors.md:3-5,102-105`; `docs/decisions/project-memory.md:19-31`; `internal_kb_fullstack/backend/app/db/models.py:233-345` |
| `docs/memories` | `docs/memories/**` including current-tree untracked note | traceability notes, remediation note, feature intent history | deep read + metadata enforcement check | `meets` | Memory-note governance is now enforced by automated tests, and the current untracked glossary slug note matches the live frontend delta. | `docs/memories/README.md:21-36`; `internal_kb_fullstack/backend/tests/test_memory_notes_frontmatter.py:7-41`; `docs/memories/concepts/2026-04-01-implementation-note-non-ascii-glossary-slug-canonicalization.md:1-19` |
| `sample corpus and generated/local inventory` | `sample-data/**`; ignored/local trees listed in root `.gitignore` | `sample-data`; `.venv*`; `.next`; `node_modules`; `.playwright-cli`; caches; `output` | corpus read + inventory classification | `partially meets` | Generated/local trees are correctly classified away from authored review, but the sample corpus still compresses provenance and owner semantics during import and must stay explicitly out of SoT claims. | `.gitignore:4-14`; `internal_kb_fullstack/backend/scripts/import_sample_corpus.py:95-112,182-199`; `sample-data` local inventory => `13,893` files / `71M` |
