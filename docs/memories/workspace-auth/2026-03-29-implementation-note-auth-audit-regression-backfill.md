---
date: 2026-03-29
feature: workspace-auth
type: implementation-note
related_specs:
  - /docs/specs/workspace-auth/spec.md
  - /docs/specs/workspace-auth/contracts.md
  - /docs/specs/workspace-auth/flows.md
  - /docs/specs/home-navigation-admin/contracts.md
related_decisions:
  - /docs/decisions/project-memory.md
status: active
---

# Auth audit regression backfill

## Context

The auth audit found that the backend auth-adjacent suite was green while the signed-in home page for normal workspace members still failed at runtime. The same audit also identified missing route coverage for `/v1/auth/me`, `/v1/auth/logout`, `/v1/auth/password/invite-signup`, and connector OAuth callback error handling.

## Decision or observation

The authenticated workspace overview path now has an explicit regression test that exercises the real service branch with a workspace-bound user and catches result-handling mistakes in async SQL execution. The auth and connector test suites now also cover the missing route shells and error mappings that define the public auth contract.

## Impact

- The primary signed-in home-page data path is protected by an automated regression test.
- Public auth route coverage is broader and closer to the actual browser-visible surface.
- The SoT auth contracts now match the current Google callback and workspace context response models.
