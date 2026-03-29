# Workspace Auth

## Summary

KnowledgeHub uses workspace-first authentication and membership. Users sign in through a single `/login` entry point, land in a current workspace context, and receive permissions through workspace membership rather than product-wide admin flags.

## Primary users

- workspace members who consume synced knowledge
- workspace owners and admins who manage shared sources and review flows
- invited users who need a controlled way to join a workspace

## Current surfaces and owned routes

- Frontend pages:
  - `/login`
  - `/invite/[token]`
- Backend public routes:
  - auth APIs under `/v1/auth/*`
  - workspace membership and invitation APIs under `/v1/workspace/*`

## Current behavior

- Authentication entry lives at `/login`.
- Supported sign-in methods are Google OAuth and invite-only email/password accounts.
- Local password accounts are not self-serve. They are created only from a workspace invite flow.
- Password reset links are admin-generated and link-based.
- Sessions carry `current_workspace_id`.
- Workspace membership roles are `owner`, `admin`, and `member`.
- `owner` and `admin` can manage shared connectors, invites, Knowledge QA, and sync operations.
- `member` can consume workspace knowledge but does not operate admin workflows.
- Workspace joins are invite-only.
- A signed-in user without any workspace membership remains authenticated, but has no current workspace context until an invite is accepted.
- Google login callback returns the same session payload contract as password login and must not fail on response-model conversion.
- When `google_oauth_redirect_uri` is configured, Google app login uses that callback URI for both the authorization redirect and the token exchange. Otherwise it falls back to `app_public_url + /api/auth/google/callback`.

## Key workflows

- Normal sign-in:
  - the user reaches `/login`
  - the page supports Google OAuth and password login on the same surface
  - on success the user receives a server session and returns to `return_to`
- Invite-driven account creation:
  - `/invite/[token]` accepts the invite immediately if the user already has a session
  - otherwise it redirects the user to `/login?invite_token=...`
  - local password signup is allowed only through a valid invite token
  - successful invite signup accepts the invite and creates the session in one flow
- Admin-driven password reset:
  - only owners and admins can create reset links
  - reset links are copied and delivered out of band
  - the reset page is routed back through `/login` with reset-specific copy and completion flow
- Current workspace:
  - the active session resolves a current workspace summary
  - role and connector-management permissions are derived from the current workspace membership

## Permissions and visibility

- Anonymous users can access `/login`, invite preview, and password reset preview/consume routes.
- Workspace owners and admins can:
  - create invitations
  - view invitations
  - create password reset links
  - manage workspace connectors
- Members can:
  - sign in
  - accept invites addressed to them
  - consume workspace knowledge
  - inspect their current workspace summary and membership list
- GitHub, Google Drive, and Notion are connector providers only. They are not alternative application-login providers.

## Important contracts owned by this spec

- shared auth session contract (`AuthSessionResponse`)
- viewer/session contract (`AuthMeResponse`)
- workspace overview and membership summary contracts
- invite preview, invite acceptance, and reset-link creation contracts

## Constraints and non-goals

- Self-serve public signup is out of scope.
- Password resets do not send email automatically in v1.
- Permission derives from workspace membership; feature specs must not treat connector-management ability as a separate source of truth.
- This spec owns the account and membership model, but not connector setup behavior or admin page behavior outside auth entry and role resolution.

## Supporting docs

- [`contracts.md`](./contracts.md)
- [`flows.md`](./flows.md)
