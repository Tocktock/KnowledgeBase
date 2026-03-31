---
date: 2026-04-01
feature: repository-review
type: implementation-note
related_specs:
  - /docs/specs/system-overview/spec.md
  - /docs/specs/public-surface-coverage.md
  - /docs/specs/workspace-auth/spec.md
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/document-authoring/spec.md
  - /docs/specs/concepts/spec.md
  - /docs/specs/glossary-validation/spec.md
related_decisions:
  - /docs/decisions/0005-workspace-data-connectors.md
  - /docs/decisions/project-memory.md
status: active
---

# Implementation note: docs and governance review

## Context

This pass reviewed:

- root governance and pointer docs
- all current spec files under `docs/specs`
- all current decision notes under `docs/decisions`
- all current memory notes under `docs/memories`, including the current-tree untracked concepts note

Baseline governance evidence:

- SoT routing is consistent across `AGENTS.md`, `README.md`, `PRODUCT.md`, `docs/README.md`, and `docs/specs/README.md`
- memory-note frontmatter is now enforced by `internal_kb_fullstack/backend/tests/test_memory_notes_frontmatter.py`

## Findings

### P2. Durable decision docs still describe workspace-first connectors as proposed or pending

Severity:

- `P2`

Spec reference:

- `docs/specs/system-overview/spec.md:5-18`
- `docs/specs/connectors/spec.md:22-43`
- `docs/specs/workspace-auth/spec.md:22-36`

Docs and code reference:

- `docs/decisions/0005-workspace-data-connectors.md:3-5,102-105`
- `docs/decisions/project-memory.md:19-31`
- `internal_kb_fullstack/backend/app/db/models.py:233-345`

Observed behavior:

- current specs and live storage model already depend on workspaces, memberships, current-workspace sessions, workspace-owned connector oauth state, and workspace-owned connections as active behavior
- `0005` still says `Status: Proposed`
- `project-memory.md` still lists workspace and connector migration as pending follow-up work

Ontology impact:

- The durable architecture layer understates a live tenancy invariant.
- Future review or design work can misread the workspace-first connector model as optional roadmap instead of current foundation.

Recommendation:

- ratify or rewrite `0005` to describe the current live state
- remove completed connector/workspace migrations from `project-memory.md` and leave only genuinely pending follow-ups

### P2. Provenance vocabulary is under-specified for mixed URL and locator semantics

Severity:

- `P2`

Spec reference:

- `docs/specs/system-overview/spec.md:70-81`
- `docs/specs/search-and-docs/spec.md:38-69`
- `docs/specs/search-and-docs/contracts.md:117-132`

Docs and code reference:

- `internal_kb_fullstack/backend/app/schemas/documents.py:13-30`
- `internal_kb_fullstack/backend/scripts/import_sample_corpus.py:182-199`
- `internal_kb_fullstack/frontend/app/docs/[slug]/page.tsx:57-63`

Observed behavior:

- specs require a shared trust field named `source_url` and describe it as the original source location
- the formal request/response model allows a plain nullable string without URL validation
- current code uses the same field for relative sample-corpus paths and other locator-like identifiers

Ontology impact:

- the docs present provenance as if it were one stable concept, but the code currently carries at least two concepts:
  - canonical external source URL
  - source locator or opaque origin identifier

Recommendation:

- either split the vocabulary into separate fields such as external URL and source locator
- or explicitly redefine `source_url` in the specs and contracts so rendering rules and operator expectations are consistent with mixed semantics

## Areas now aligned

- SoT routing is now coherent:
  - `README.md` points behavior authority to `/docs`
  - `PRODUCT.md` is explicitly a compatibility pointer, not a behavior source
  - `docs/README.md` and `docs/specs/README.md` reinforce the same boundaries
- memory-note governance is no longer convention-only:
  - `docs/memories/README.md:21-36` defines required metadata
  - `internal_kb_fullstack/backend/tests/test_memory_notes_frontmatter.py:7-41` enforces it
- the 2026-03-31 runtime drifts that were documented in the prior review now have an explicit remediation record in `docs/memories/repository-review/2026-04-01-implementation-note-reviewed-findings-remediation.md`

## Coverage notes

- reviewed spec count: `25`
- reviewed decision count: `7`
- reviewed memory-note count in the current tree: `26`, including one authored untracked note

## Impact

The documentation system itself is materially healthier than it was on 2026-03-31. The remaining governance work is not broad SoT confusion; it is concentrated in stale durable connector decisions and under-specified provenance terminology.
