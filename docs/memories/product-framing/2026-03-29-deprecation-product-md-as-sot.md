---
date: 2026-03-29
feature: product-framing
type: deprecation
related_specs:
  - /docs/specs/home-navigation-admin/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/glossary-validation/spec.md
related_decisions:
  - /docs/decisions/0005-workspace-data-connectors.md
status: active
---

# PRODUCT.md is no longer a product Source of Truth

## Context

`PRODUCT.md` contained a large product-level description of behavior outside the canonical docs tree. That created a second, manually maintained product narrative alongside the implementation and decision docs.

## Decision or observation

`PRODUCT.md` is retained only as a compatibility pointer for readers who still look for that file. Canonical product behavior now lives in `docs/specs/`.

## Impact

- Future product changes should not expand `PRODUCT.md`.
- Feature detail must be added to the relevant spec folders instead.

## Follow-up

If no external references depend on `PRODUCT.md`, it can be removed in a later cleanup after its replacement links have been stable for a while.
