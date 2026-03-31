---
date: 2026-04-01
feature: repository-review
type: implementation-note
related_specs:
  - /docs/specs/workspace-auth/spec.md
  - /docs/specs/home-navigation-admin/spec.md
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/document-authoring/spec.md
  - /docs/specs/concepts/spec.md
  - /docs/specs/glossary-validation/spec.md
  - /docs/specs/sync-status/spec.md
related_decisions:
  - /docs/decisions/0003-document-links-are-a-projection.md
status: active
---

# Implementation note: frontend review appendix

## Context

This appendix covers the current working-tree frontend:

- route families under `internal_kb_fullstack/frontend/app`
- API bridge handlers and server helpers under `internal_kb_fullstack/frontend/lib`
- shared UI and guards under `internal_kb_fullstack/frontend/components`
- the current-tree authored deltas around glossary slug handling:
  - `app/api/documents/slug/[slug]/route.ts`
  - `app/api/glossary/slug/[slug]/route.ts`
  - `app/glossary/[slug]/page.tsx`
  - `lib/api/server.ts`
  - `lib/path-segments.ts`

Baseline checks:

- `cd internal_kb_fullstack/frontend && npm run typecheck` => passed
- `cd internal_kb_fullstack/frontend && npm run build` => passed

## Findings

### P2. Authoring actor is workspace member in code, authenticated user in the spec

Severity:

- `P2`

Spec reference:

- `docs/specs/document-authoring/spec.md:56-60`
- `docs/specs/document-authoring/contracts.md:10-32`

Code reference:

- `internal_kb_fullstack/frontend/app/new/page.tsx:1-13`
- `internal_kb_fullstack/frontend/app/new/manual/page.tsx:1-13`
- `internal_kb_fullstack/frontend/app/new/upload/page.tsx:1-13`
- `internal_kb_fullstack/frontend/app/new/definition/page.tsx:1-13`
- `internal_kb_fullstack/frontend/components/auth/manage-access-guard.tsx:130-173`

Observed behavior:

- Every `/new*` page uses `WorkspaceMemberGuard`.
- `WorkspaceMemberGuard` permits anonymous users only to the login CTA, then blocks signed-in users without `current_workspace`, and only then renders the authoring surface.

Ontology impact:

- The surfaced actor is `workspace-scoped member`, not generic `authenticated user`.
- This is consistent with the rest of the workspace model, but it is stricter than the owning spec currently states.

Recommendation:

- Update the document-authoring spec and contracts to say `active workspace member`, unless product intent is to reopen authoring for signed-in users without a workspace.

### P2. The frontend write surface omits `visibility_scope` even though the authoring contract still owns it

Severity:

- `P2`

Spec reference:

- `docs/specs/document-authoring/spec.md:58-60`
- `docs/specs/document-authoring/contracts.md:41-50`

Code reference:

- `internal_kb_fullstack/frontend/components/editor/document-editor.tsx:345-361`
- `internal_kb_fullstack/frontend/components/editor/document-editor.tsx:451-486`
- `internal_kb_fullstack/frontend/components/editor/document-editor.tsx:651-688`
- `internal_kb_fullstack/frontend/lib/types.ts:330-346`

Observed behavior:

- `buildIngestPayload()` sets `source_system`, `title`, `slug`, `source_url`, `content`, `doc_type`, `owner_team`, `status`, `priority`, `allow_slug_update`, and `metadata`, but not `visibility_scope`.
- the shared frontend `IngestDocumentRequest` type also omits `visibility_scope`
- the upload form exposes no visibility field either

Ontology impact:

- The write surface treats visibility as if it were connector-owned or backend-defaulted metadata rather than a first-class authored document property.

Recommendation:

- Either restore `visibility_scope` to the frontend authoring contract and UI or remove it from the authoring spec if manual authoring is now intentionally default-only.

### P3. The spec-owned reindex workflow is not surfaced in the current frontend

Severity:

- `P3`

Spec reference:

- `docs/specs/document-authoring/spec.md:28-32,53-55`
- `docs/specs/document-authoring/contracts.md:91-97`

Code reference:

- `internal_kb_fullstack/frontend/components/editor/document-editor.tsx:60-694`
- `internal_kb_fullstack/frontend/app/api/documents/route.ts`
- `internal_kb_fullstack/frontend/app/api/documents/upload/route.ts`
- `internal_kb_fullstack/frontend/app/api/documents/generate-definition/route.ts`

Observed behavior:

- The current frontend exposes create, upload, and definition-draft flows.
- No current route handler, API bridge, or UI action exposes `POST /v1/documents/{document_id}/reindex`.

Ontology impact:

- The surfaced lifecycle for authored documents ends at creation/update.
- The spec still promises reindex as part of the user-facing maintenance model.

Recommendation:

- Either add a reindex UI/API bridge or downgrade the spec so reindex remains backend-only until intentionally surfaced.

### P2. Provenance rendering still assumes `source_url` is safely navigable

Severity:

- `P2`

Spec reference:

- `docs/specs/search-and-docs/spec.md:38-69`
- `docs/specs/system-overview/spec.md:70-81`

Code reference:

- `internal_kb_fullstack/frontend/app/docs/[slug]/page.tsx:57-63`
- `internal_kb_fullstack/frontend/components/trust/trust-badges.tsx:23-30`
- `internal_kb_fullstack/frontend/lib/types.ts:1-8,22-39`

Observed behavior:

- Document detail renders `data.document.source_url` directly into an `<a href=... target="_blank">`.
- `TrustBadges` renders `trust.source_url` directly into a `next/link` external target.
- The type surface exposes `source_url` as a plain optional string with no distinction between canonical URLs and non-URL locators.

Ontology impact:

- The UI presents provenance as a guaranteed outbound navigation target.
- That assumption does not hold for sample imports and locator-like values elsewhere in the system.

Recommendation:

- Split rendering rules between canonical external URLs and non-navigable source locators, or tighten backend/spec semantics so `source_url` is guaranteed to be an external URL.

## Areas now aligned

- redirect and continuation hardening are aligned across login, auth callback, and connector callback flows
- the current-tree non-ASCII glossary slug canonicalization change aligns frontend routing with stored `public_slug` behavior
- member/admin surface separation remains coherent across home, glossary review, jobs, and request flows
- trust and provenance badges are consistently present across search, docs, concepts, and home surfaces

Representative evidence:

- redirect normalization: `internal_kb_fullstack/frontend/lib/internal-paths.ts:12-35`, `internal_kb_fullstack/frontend/app/login/page.tsx:72-153`
- current-tree slug handling: `internal_kb_fullstack/frontend/lib/path-segments.ts:1-16`, `internal_kb_fullstack/frontend/app/glossary/[slug]/page.tsx:20-27`, `internal_kb_fullstack/frontend/lib/api/server.ts:47-49,92-94`
- admin/member guards: `internal_kb_fullstack/frontend/components/auth/manage-access-guard.tsx:21-173`

## Impact

No validated P0 or P1 frontend regression was found in the current working tree. The frontend is largely aligned with the repository model, but the authoring surface and provenance rendering still trail the owning contracts.
