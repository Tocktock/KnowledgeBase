---
date: 2026-04-01
feature: repository-review
type: implementation-note
related_specs:
  - /docs/specs/workspace-auth/spec.md
  - /docs/specs/workspace-auth/contracts.md
  - /docs/specs/connectors/spec.md
  - /docs/specs/connectors/contracts.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/search-and-docs/contracts.md
  - /docs/specs/concepts/spec.md
  - /docs/specs/concepts/contracts.md
  - /docs/specs/glossary-validation/spec.md
related_decisions:
  - /docs/decisions/0001-canonical-write-boundary.md
  - /docs/decisions/0003-document-links-are-a-projection.md
  - /docs/decisions/0005-workspace-data-connectors.md
status: active
---

# Implementation note: reviewed findings remediation

## Context

The 2026-03-31 repository-wide review identified four fix classes that required coordinated runtime, schema, and documentation changes:

- auth and connector continuation flows trusted unsafe redirect targets
- evidence-only documents were hidden from list and search views but still readable through direct detail routes
- glossary public identity was derived from mutable display terms instead of a persisted workspace-scoped key
- security and documentation governance had drifted from the intended contracts

## Implemented changes

### Redirect hardening

- Added one shared backend redirect normalizer and reused it in auth and connector OAuth services.
- Added one shared frontend internal-path coercion helper and reused it in login continuation plus auth and connector callback routes.
- Restricted continuation targets to single-origin internal paths and preserved only valid path, query, and fragment components.

### Evidence-only visibility

- Kept search and docs list member-visible only for every viewer.
- Made document slug detail, id detail, content, and relations role-sensitive so only current-workspace owners and admins can directly read evidence-only documents.
- Applied the same role-sensitive evidence visibility to concept detail support rows so member reads stay member-visible while admin review links still work.

### Glossary public identity

- Added a persisted workspace-scoped `public_slug` to glossary concepts.
- Backfilled canonical slugs deterministically and resolved collisions with stable id-derived suffixes.
- Switched member-facing glossary summaries and detail lookups to use stored `public_slug` values, with one legacy fallback for unique old-style slugs.

### Security and governance

- Removed the stale global ORM uniqueness contract from `Document.slug` so workspace-scoped uniqueness remains the only declared contract.
- Required explicit connector and session encryption keys in staging and production while preserving development fallbacks.
- Backfilled missing memory-note frontmatter and added an automated repository test that enforces the required metadata keys for dated memory notes.

## Verification

- Added regression coverage for redirect normalization, evidence-only route access, glossary slug stability, config validation, and memory-note frontmatter.
- Re-ran backend pytest, frontend typecheck, and frontend production build after the coordinated patch set.

