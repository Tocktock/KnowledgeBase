---
date: 2026-03-29
feature: glossary-validation
type: intent
related_specs:
  - /docs/specs/glossary-validation/spec.md
  - /docs/specs/connectors/spec.md
related_decisions:
  - /docs/decisions/0005-workspace-data-connectors.md
status: active
---

# Glossary-first validation becomes the primary admin job

## Context

The product direction shifted from a general workspace knowledge layer toward a more specific admin purpose: sync connected knowledge sources, then validate whether glossary definitions still hold.

## Decision or observation

The glossary definition workflow is the primary authoritative output. Workspace sync runs must feed a validation pass so admins can decide whether a term remains correct, needs revision, or should return to review.

## Impact

- Knowledge QA is the primary admin workflow.
- Evidence-only corpora are valid for glossary validation even when they are hidden from member-facing docs and search.
- Sync and validation must be treated as a linked orchestration flow rather than separate admin tasks.

## Follow-up

Future connector additions should explain both member-visible ingestion and glossary-evidence ingestion paths explicitly in the feature specs.
