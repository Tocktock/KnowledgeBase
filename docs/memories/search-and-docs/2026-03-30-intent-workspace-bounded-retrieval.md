---
date: 2026-03-30
feature: search-and-docs
type: intent
related_specs:
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/search-and-docs/contracts.md
related_decisions:
  - /docs/decisions/0001-canonical-write-boundary.md
  - /docs/decisions/0003-document-links-are-a-projection.md
status: active
---

# Intent: Workspace-Bounded Retrieval

## Context

Read-side product surfaces were still effectively global even after workspace auth and connector ownership were introduced.

## Decision

Search, docs list, docs detail, concept grounding, backlinks, and related-document queries now share one resolved workspace boundary. Authenticated viewers use their current workspace, while anonymous read surfaces fall back to the default workspace.

## Rationale

This keeps public read surfaces usable without reintroducing cross-workspace leakage into the search and browsing experience.
