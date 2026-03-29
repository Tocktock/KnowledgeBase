---
date: 2026-03-29
feature: connectors
type: intent
related_specs:
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/glossary-validation/spec.md
related_decisions:
  - /docs/decisions/0005-workspace-data-connectors.md
status: active
---

# GitHub ingestion splits docs and glossary evidence paths

## Context

GitHub was added as a workspace connector after the product direction shifted toward synced workspace knowledge and glossary validation. A single GitHub path would either under-serve member-visible docs or pollute normal browsing with raw repository evidence.

## Decision or observation

GitHub now has two explicit intents:

- `repository_docs` for member-visible repository documentation
- `repository_evidence` for glossary validation evidence drawn from text-based repository files

The evidence path defaults to `evidence_only`, while the docs path defaults to `member_visible`.

## Impact

- GitHub supports both searchable knowledge and glossary QA without collapsing those corpora into one browsing surface.
- Search, Docs, Concepts, and Knowledge QA can share trust and provenance while still filtering evidence-only material from normal member retrieval.

## Follow-up

If GitHub later adds issue, PR, or code-search support, those capabilities must declare whether they are member-visible knowledge, evidence-only corpus, or an entirely separate feature area.
