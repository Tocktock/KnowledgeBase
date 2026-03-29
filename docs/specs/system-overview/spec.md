# System Overview

## Summary

KnowledgeHub is a workspace knowledge layer with a glossary-first administrative purpose. Members primarily search, browse docs, and consume concepts. Owners and admins connect sources, run validation, and keep glossary definitions trustworthy over time.

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

## Cross-feature loop

1. Admin connects sources.
2. Source sync or snapshot upload creates or updates documents.
3. Member-visible documents feed Search, Docs, and Concepts.
4. Evidence-only documents feed glossary support and validation without polluting normal browsing.
5. Admin runs validation.
6. Changed evidence can keep the approved concept published while reopening QA with a fresh draft.

## Trust model

Shared user-facing trust fields:

- `source_label`
- `source_url`
- `authority_kind`
- `last_synced_at`
- `freshness_state`
- `evidence_count`

The trust model must be consistent across Search, Docs, and Concepts.

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
