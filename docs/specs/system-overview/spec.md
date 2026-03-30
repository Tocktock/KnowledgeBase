# System Overview

## Summary

KnowledgeHub is a workspace knowledge layer with a glossary-first administrative purpose. Members primarily search, browse docs, and consume concepts inside the current workspace boundary. Owners and admins connect sources, run verification, and keep glossary definitions trustworthy over time.

## Product map

- Authentication and membership:
  - workspace-first access model
  - invite-only local accounts plus Google login
- Source setup:
  - Google Drive, GitHub, and Notion connectors
  - workspace and personal ownership scopes
  - member-visible and evidence-only corpus split
- Retrieval:
  - Search
  - Docs
  - Concepts
- Manual fallback:
  - New Document authoring
- Operational workflows:
  - Knowledge QA
  - Sync Status

## Primary roles

- Anonymous visitor
  - learns what the product is
  - signs in or follows an invite/reset flow
- Member
  - searches and reads trusted knowledge
  - consumes approved concept definitions
- Owner/Admin
  - manages workspace sources
  - runs glossary validation
  - resolves sync and quality issues

## Shared terminology

- Workspace source:
  - shared source managed for the current workspace
- Personal source:
  - source managed by an individual user
- `member_visible`:
  - source or document participates in normal docs/search and in validation
- `evidence_only`:
  - source or document participates in glossary validation but is hidden from normal docs/search
- Lifecycle status:
  - editorial state of a concept
- Validation state:
  - QA state describing whether the current evidence still supports the concept definition
- Verification policy:
  - workspace-scoped rules that define the minimum evidence, freshness, and durable-source requirements for a glossary concept to stay verifiable
- Verification state:
  - member-facing proof status for a glossary concept such as `verified`, `monitoring`, `drift_detected`, `evidence_insufficient`, or `archived`
- Knowledge passport:
  - the compact detail view that shows canonical output, supporting evidence, provenance, and backlinks for one glossary concept

## Cross-feature loop

1. Admin connects sources.
2. Source sync or snapshot upload creates or updates documents.
3. Every ingested or manually-authored knowledge object is stored inside one workspace and is never shared across workspaces implicitly.
4. Member-visible documents feed Search, Docs, and Concepts for that workspace.
5. Evidence-only documents feed glossary support and verification without polluting normal browsing.
6. Admin runs validation and verification against the current workspace policy.
7. Changed evidence can keep the approved concept published while reopening QA with a fresh draft.

## Trust model

Shared user-facing trust fields:

- `source_label`
- `source_url`
- `authority_kind`
- `last_synced_at`
- `freshness_state`
- `evidence_count`

The trust model must be consistent across Search, Docs, and Concepts.

Glossary surfaces add a second verification layer that must stay consistent across Home, Glossary, and Knowledge QA:

- `status`
- `policy_label`
- `policy_version`
- `evidence_bundle_hash`
- `verified_at`
- `due_at`
- `last_checked_at`
- `verified_by`
- `reason`

## Frontend rendering contract

- The root frontend layout must stay a stable shell. Request-time data fetching belongs in leaf pages or client queries, not in the global layout.
- Long user-visible strings such as names, emails, slugs, URLs, badges, and source titles must truncate or wrap without overflowing cards, nav items, or action rows.
- Dense operator surfaces must collapse fixed multi-column layouts before tablet/mobile widths. Search forms, review filters, connector selectors, and editor sidebars must stack cleanly instead of clipping.
- `force-dynamic` is not the default rendering mode. A route should only opt into an explicit dynamic boundary when request-time behavior cannot be expressed through a narrower server or client fetch.
- When one surface becomes operationally dense, the preferred IA pattern is a stable overview route plus deep-link detail or setup routes rather than adding more top-level navigation items.

## Feature ownership map

- [`workspace-auth`](../workspace-auth/spec.md)
- [`home-navigation-admin`](../home-navigation-admin/spec.md)
- [`connectors`](../connectors/spec.md)
- [`search-and-docs`](../search-and-docs/spec.md)
- [`document-authoring`](../document-authoring/spec.md)
- [`concepts`](../concepts/spec.md)
- [`glossary-validation`](../glossary-validation/spec.md)
- [`sync-status`](../sync-status/spec.md)

## Constraints and non-goals

- This overview defines the product map and shared vocabulary. It does not replace the feature-level specs.
- Public contract detail belongs in the owning feature folders.
- Slack ingestion is intentionally deferred in this milestone. The foundation work only reserves provider abstractions and evidence-first policy language so Slack can land without changing the workspace or verification model.
