---
date: 2026-03-29
feature: connectors
type: rationale
related_specs:
  - /docs/specs/connectors/spec.md
  - /docs/specs/home-navigation-admin/spec.md
related_decisions:
  - /docs/decisions/0005-workspace-data-connectors.md
status: active
---

# Zero-config connector setup becomes the default admin path

## Context

The raw connector model exposed too much implementation detail too early. Admins needed to understand provider internals, raw identifiers, and low-level source selection just to bring shared knowledge into the product.

## Decision or observation

The default connector UX is now template-first. Provider cards explain the intended job, hide raw connector internals, and guide admins through a browse-or-upload flow with sane sync and visibility defaults.

## Impact

- Workspace source setup is now easier to explain and document.
- Personal sources remain supported but are visually secondary.
- Advanced selection stays available only as a secondary admin tool.

## Follow-up

Any future provider should document its default template path before introducing advanced provider-specific controls.
