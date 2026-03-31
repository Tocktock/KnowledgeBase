---
date: 2026-03-30
feature: system-overview
type: intent
related_specs:
  - /docs/specs/system-overview/spec.md
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/concepts/spec.md
  - /docs/specs/glossary-validation/spec.md
related_decisions:
  - /docs/decisions/0001-canonical-write-boundary.md
  - /docs/decisions/0005-workspace-data-connectors.md
status: active
---

# Intent: Workspace-Scoped Verified Knowledge Foundation

## Context

The product review for March 30, 2026 pushed two priorities to the top of the roadmap:

- knowledge must connect cleanly across workspace tools without exposing cross-workspace bleed
- key glossaries must be verifiable at creation time and continuously while they remain active

## Decision

M1 hardens the existing `documents` and `knowledge_concepts` tables instead of introducing a new generic knowledge-object layer. Workspace scope becomes the primary storage boundary for both documents and concepts, and glossary approval moves behind a policy-driven verification gate.

## Why this shape

- It fixes the product-level tenancy leak with the smallest durable schema change.
- It lets connectors, search, docs, glossary, and home overview converge on one workspace model instead of bolting on filters later.
- It keeps the approved glossary visible during drift while reopening QA, which preserves member UX and admin accountability at the same time.

## Follow-on consequence

Slack stays out of M1 runtime surfaces. Only provider abstractions and evidence-first policy language are reserved now so Slack can land later without changing the verification model again.
