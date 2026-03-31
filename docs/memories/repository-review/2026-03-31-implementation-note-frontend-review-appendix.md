---
date: 2026-03-31
feature: repository-review
type: implementation-note
related_specs:
  - /docs/specs/workspace-auth/spec.md
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/concepts/spec.md
  - /docs/specs/home-navigation-admin/spec.md
  - /docs/specs/sync-status/spec.md
related_decisions: []
status: active
---

# Frontend review appendix

## Context

The frontend review covered:

- `app/` routes and server-side API bridge handlers
- `components/` member, admin, docs, glossary, and guard surfaces
- `lib/` API bridge and type definitions

Baseline checks:

- `npm run typecheck` passed
- `npm run build` passed

## Findings

### P1. Frontend callback handlers complete the backend open redirect chain

Evidence:

- `internal_kb_fullstack/frontend/app/api/auth/google/callback/route.ts:6-20`
- `internal_kb_fullstack/frontend/app/api/connectors/[provider]/oauth/callback/route.ts:5-27`
- `internal_kb_fullstack/frontend/app/login/page.tsx:70-151`

Observation:

- the callback handlers trust backend `redirect_to` payloads and rehydrate them with `new URL(path, base)`
- the login page also trusts `return_to` from search params for `router.replace`, password auth payloads, and connector continuation

Why this matters:

- even though most internally generated links call `encodeURIComponent`, the page itself still accepts arbitrary query values from the browser location
- the frontend is therefore the final execution point for the redirect bug rather than a passive renderer

Recommended remediation:

- add a frontend-local “internal path only” guard before `router.replace`, `window.location.replace`, and callback redirects
- keep the backend validation as the primary control, but do not trust returned redirect strings blindly

### P1. Glossary detail renders support documents as ordinary docs links

Evidence:

- `internal_kb_fullstack/frontend/app/glossary/[slug]/page.tsx:127-144`
- `internal_kb_fullstack/frontend/lib/types.ts:219-241`

Observation:

- the UI treats every support item returned by the backend as a normal document link
- the type surface has no field that distinguishes support documents that should remain evidence-only from those safe for member browsing

Why this matters:

- once backend support assembly includes an evidence-only document, the UI has no chance to protect the contract
- the surfaced ontology collapses “supporting evidence” and “member-visible document” into the same clickable shape

Recommended remediation:

- after backend visibility enforcement, keep a typed distinction available in the frontend model
- if evidence-only support ever needs to appear in admin-only surfaces, render it with an explicit non-member-readable affordance

### P2. Surfaced concept identity assumes slug stability that the backend does not actually provide

Evidence:

- `internal_kb_fullstack/frontend/app/glossary/[slug]/page.tsx:19-22`
- `internal_kb_fullstack/frontend/app/glossary/[slug]/page.tsx:153-165`
- `internal_kb_fullstack/frontend/lib/types.ts:190-242`

Observation:

- all concept navigation is slug-based
- neither the route nor the shared types indicate that slug is a derived, potentially ambiguous field

Why this matters:

- the UI implicitly promises stable concept URLs and deterministic navigation
- the backend currently cannot guarantee that promise across rename or collision scenarios

Recommended remediation:

- keep the current UX only if backend introduces a stable unique concept route key
- otherwise surface canonical ids or route aliases explicitly in the client model

### P3. Access guards are generally aligned with the product model

Evidence:

- `internal_kb_fullstack/frontend/components/auth/manage-access-guard.tsx:21-127`
- `internal_kb_fullstack/frontend/app/jobs/page.tsx:1-18`

Observation:

- admin-only surfaces are consistently gated through `ManageAccessGuard`
- member-without-workspace cases receive a dedicated state instead of being misclassified as anonymous

Why this matters:

- this aligns well with the home-navigation-admin and sync-status specs
- the repo’s most important frontend drift is therefore not general authorization, but specific contract leaks around redirect and visibility handling

Recommended follow-up:

- preserve this guard model while tightening redirect and evidence visibility behavior

## Frontend ontology observations

- `lib/types.ts` mirrors the backend data model closely for documents, revisions, chunks, jobs, glossary concepts, support items, auth sessions, and workspace summaries.
- The strongest frontend design decision is that the UI remains contract-driven rather than duplicating business logic locally.
- The largest frontend ontology gap is absence of a “support visibility” concept in the public types.

## Impact

- The frontend is structurally sound and type-checked, but a few bridge points still assume backend payloads are already safe and final.
- The highest-value frontend fixes are narrow and should be low-diff once backend contract changes are defined.

## Follow-up

- Add targeted route tests or integration checks for redirect validation and evidence-only support rendering once the backend behavior is fixed.
