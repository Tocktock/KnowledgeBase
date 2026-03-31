---
date: 2026-04-01
feature: connectors
type: rationale
related_specs:
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/search-and-docs/contracts.md
  - /docs/specs/document-authoring/contracts.md
related_decisions:
  - /docs/decisions/0005-workspace-data-connectors.md
  - /docs/decisions/project-memory.md
status: active
---

# Rationale: source_url contract and connector ratification

## Context

The 2026-04-01 repository review found two related documentation drifts:

- the durable connector decision layer still needed ratification language cleanup even though workspace-first connectors were already live
- the shared `source_url` field was described as if it were always an external original link, while the implementation and sample corpus already used pseudo-source locators

## ADR 0005 ratification

`0005 - Workspace data connectors are zero-config for end users` is now treated as an accepted architectural rule instead of a migration plan. The live product already uses workspace-scoped connector ownership, invite-only workspace membership, template-first admin setup, and sync-first ingestion into the shared document layer.

## source_url contract

The shared provenance contract is now explicit across read and write specs:

- `https://...` means an external original source
- `generic://<source_system>/<percent-encoded locator>` means normalized internal or pseudo-source provenance
- `null` means no stable provenance value exists

Only `https://...` is rendered as an outbound link. `generic://...` is visible provenance text.

## Why generic:// for non-external sources

KnowledgeHub keeps normalized Markdown or text as the primary in-app reading surface. Some sources do not have a stable external original that should send the user away from the app, and some imported or generated content only has an internal locator. `generic://...` keeps provenance explicit without pretending every source is a browser-safe external URL.

## Legacy normalization and backfill

Legacy non-HTTPS values such as relative corpus paths or older pseudo-source schemes are normalized into the shared `generic://...` form. The runtime normalizes on write and read boundaries, and the maintenance script backfills persisted legacy values so stored data converges on the same contract.

## Affected specs and surfaces

- Search, docs, and concept trust surfaces now use the same provenance rule.
- Connector item summaries use the same `source_url` contract as the read-side trust objects.
- Manual and upload-backed authoring now document the write-time normalization behavior.
