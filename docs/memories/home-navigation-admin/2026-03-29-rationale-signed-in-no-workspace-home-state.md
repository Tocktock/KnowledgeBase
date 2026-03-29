---
date: 2026-03-29
feature: home-navigation-admin
type: rationale
related_specs:
  - /docs/specs/home-navigation-admin/spec.md
  - /docs/specs/workspace-auth/spec.md
related_decisions:
  - /docs/decisions/project-memory.md
status: active
---

# Signed-in users without workspace membership must not look anonymous

## Context

After Google login, a user could land on the home page with an authenticated account surface but still see the anonymous marketing hero and `로그인하고 시작하기` CTA.

## Decision or observation

The product distinguishes anonymous users from signed-in users who do not yet belong to a workspace. The home page now renders a dedicated "workspace access required" state when the viewer is authenticated but has no current workspace membership.

## Impact

- The home page no longer asks a logged-in user to log in again.
- The UI makes it clear that the missing step is workspace access, not authentication.
- Workspace overview now reports `authenticated=true` with `workspace=null` for this state so the frontend can render it explicitly.
