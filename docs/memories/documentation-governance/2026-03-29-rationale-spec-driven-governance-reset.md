---
date: 2026-03-29
feature: documentation-governance
type: rationale
related_specs:
  - /docs/specs/home-navigation-admin/spec.md
  - /docs/specs/glossary-validation/spec.md
related_decisions:
  - /docs/decisions/project-memory.md
status: active
---

# Spec-driven documentation governance reset

## Context

The repository had durable architecture notes, but feature behavior was still spread across multiple READMEs and a large product document outside the canonical docs tree. That made feature intent harder to trace and allowed product behavior to drift away from the written description.

## Decision or observation

The repository now treats `/docs` as the only canonical home for feature behavior and requirements. Feature specs live in `/docs/specs`, architecture decisions remain in `/docs/decisions`, and traceability records live in `/docs/memories`.

## Impact

- Future feature work must update the relevant `spec.md`.
- High-level READMEs must summarize and link rather than restating behavior.
- Design intent and deprecated content must be captured under `/docs/memories`.

## Follow-up

As new features are added, extend the spec inventory instead of expanding README files into product-level Sources of Truth.
