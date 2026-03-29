---
date: 2026-03-29
feature: workspace-auth
type: rationale
related_specs:
  - /docs/specs/workspace-auth/spec.md
  - /docs/specs/home-navigation-admin/spec.md
related_decisions:
  - /docs/decisions/project-memory.md
status: active
---

# Workspace-first auth and membership rationale

## Context

The product shifted from a generic internal-doc tool toward a workspace knowledge layer with shared connectors, shared review workflows, and role-aware operational surfaces. That required permissions to follow workspace membership rather than ad hoc feature-specific checks.

## Decision or observation

Authentication and authorization now center on the current workspace. Login is unified under `/login`, membership is invite-only, and connector-management or QA access derives from the current workspace role.

## Impact

- Product surfaces can rely on `owner`, `admin`, and `member` as the stable permission vocabulary.
- App login stays separate from connector providers.
- Home, navigation, connectors, glossary review, and sync status can consume the same role model.

## Follow-up

If future multi-workspace switching is introduced, the workspace-auth spec should remain the canonical place that defines current-workspace selection and role propagation.
