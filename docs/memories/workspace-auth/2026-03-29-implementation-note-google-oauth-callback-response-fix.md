---
date: 2026-03-29
feature: workspace-auth
type: implementation-note
related_specs:
  - /docs/specs/workspace-auth/spec.md
related_decisions:
  - /docs/decisions/project-memory.md
status: active
---

# Google OAuth callback response conversion fix

## Context

Google OAuth login on localhost completed the token exchange and userinfo lookup successfully, but the backend callback returned `500` before the frontend could set the session cookie.

## Decision or observation

The failure came from validating an `AuthSessionResponse` model instance directly into `AuthCallbackResponse` with Pydantic v2. The callback flow now converts the session response to plain data before validating it into the callback model, and app-login Google redirect resolution now respects `google_oauth_redirect_uri` when configured.

## Impact

- Successful Google OAuth callbacks return a valid `AuthCallbackResponse` instead of crashing at serialization time.
- The frontend callback route can set the session cookie and complete the login flow.
- Deployments with a custom public callback can override the Google login redirect URI without changing `app_public_url`.

## Follow-up

If connector OAuth callbacks need the same redirect-override behavior, add a shared helper only when that change is intentionally tested and documented.
