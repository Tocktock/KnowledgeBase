# Workspace Auth Contracts

Canonical schema modules:

- `internal_kb_fullstack/backend/app/schemas/auth.py`
- `internal_kb_fullstack/backend/app/schemas/workspace.py`

## Frontend pages

### `GET /login`

- Purpose: single entry point for application login, invite-driven signup, and password reset completion.
- Caller: anonymous or authenticated user.
- Query parameters:
  - `return_to`
  - `post_auth_action`
  - `owner_scope`
  - `provider`
  - `invite_token`
  - `reset_token`
- Response: HTML page rendered by the frontend app.
- Important states:
  - authenticated users are redirected away when the login task is already satisfied
  - invite token and reset token change the copy and action blocks shown on the page

### `GET /invite/[token]`

- Purpose: invite handoff entry for users who arrive from a shared invite link.
- Caller: anonymous or authenticated user.
- Response: frontend handoff page.
- Important states:
  - authenticated users attempt invite acceptance directly
  - anonymous users are redirected to `/login?invite_token=...`

## Backend auth APIs

### `GET /v1/auth/google/start`

- Purpose: begin Google OAuth for application login.
- Caller: anonymous user.
- Query parameters:
  - `return_to`
  - `post_auth_action`
  - `owner_scope`
  - `provider`
- Response shape: redirect response to Google OAuth.
- Important error states:
  - provider misconfiguration
  - invalid or disallowed callback state

### `GET /v1/auth/google/callback`

- Purpose: complete Google OAuth, resolve or create the user, create a session, and resume the requested post-auth flow.
- Caller: Google OAuth callback.
- Query parameters:
  - provider callback code/state payload
- Response model: `AuthSessionResponse`
- Important error states:
  - invalid callback state
  - OAuth exchange failure
  - missing workspace context for invite or connector continuation

### `POST /v1/auth/password/login`

- Purpose: authenticate an existing local-password account.
- Caller: anonymous user.
- Request model: `PasswordLoginRequest`
- Response model: `AuthSessionResponse`
- Important error states:
  - wrong password
  - Google-only account without a password
  - disabled or invalid session creation flow
- Example request:

```json
{
  "email": "member@example.com",
  "password": "correct horse battery staple",
  "return_to": "/search"
}
```

### `POST /v1/auth/password/invite-signup`

- Purpose: create a local password account from an invite or add a password to an invited existing user.
- Caller: anonymous invited user.
- Request model: `PasswordInviteSignupRequest`
- Response model: `AuthSessionResponse`
- Important error states:
  - invalid, expired, or already accepted invite
  - email mismatch between the invite and the requested signup
  - invalid password policy
- Example request:

```json
{
  "invite_token": "abc123",
  "name": "New Member",
  "password": "correct horse battery staple",
  "return_to": "/"
}
```

### `POST /v1/auth/password/reset-links`

- Purpose: create an admin-generated password reset link for a workspace member.
- Caller: authenticated `owner` or `admin`.
- Request model: `PasswordResetLinkCreateRequest`
- Response shape: reset-link payload with preview metadata and URL/token data needed to copy the link.
- Important error states:
  - non-admin caller
  - missing target user
  - user not in the current workspace

### `GET /v1/auth/password/reset/{token}`

- Purpose: preview a password reset token before submission.
- Caller: anonymous or authenticated user who holds the reset link.
- Response model: `PasswordResetPreviewResponse`
- Important error states:
  - invalid or expired token

### `POST /v1/auth/password/reset/{token}`

- Purpose: update the target user password and create a new session.
- Caller: anonymous or authenticated user with a valid reset token.
- Request body:
  - `password`
  - optional continuation fields mirrored from login
- Response model: `AuthSessionResponse`
- Important error states:
  - invalid or expired token
  - password policy violation

### `GET /v1/auth/me`

- Purpose: resolve the current authenticated viewer and current workspace context.
- Caller: any client.
- Response model: `AuthMeResponse`
- Important behavior:
  - anonymous users receive `authenticated: false`
  - authenticated users receive workspace role and `can_manage_workspace_connectors`

### `POST /v1/auth/logout`

- Purpose: destroy the current server session.
- Caller: authenticated user.
- Response shape: success payload.

## Backend workspace APIs

### `GET /v1/workspace`

- Purpose: fetch the current workspace summary for the active session.
- Caller: authenticated user.
- Response model: `WorkspaceSummary`

### `GET /v1/workspace/overview`

- Purpose: fetch role-aware home-page data for the current viewer.
- Caller: anonymous or authenticated user.
- Response model: `WorkspaceOverviewResponse`
- Important behavior:
  - anonymous viewers receive an unauthenticated overview state
  - authenticated viewers receive role-aware source health, featured content, and QA summary

### `GET /v1/workspace/members`

- Purpose: list members in the current workspace.
- Caller: authenticated user in the workspace.
- Response model: member list shape defined in `workspace.py`

### `GET /v1/workspace/invitations/{token}/preview`

- Purpose: preview invite metadata before login or signup.
- Caller: anonymous or authenticated user.
- Response model: invitation preview response from `workspace.py`
- Important behavior:
  - reports invited email, workspace, role, expiration, acceptance, and whether a local password already exists

### `GET /v1/workspace/invitations`

- Purpose: list workspace invitations.
- Caller: authenticated `owner` or `admin`.
- Response model: invitation list shape defined in `workspace.py`

### `POST /v1/workspace/invitations`

- Purpose: create an invitation link for a workspace role.
- Caller: authenticated `owner` or `admin`.
- Request model: invitation create request from `workspace.py`
- Response model: invitation detail payload with shareable token/link
- Important error states:
  - non-admin caller
  - invalid role
  - duplicate active invitation handling

### `POST /v1/workspace/invitations/{token}/accept`

- Purpose: accept a workspace invite for the current authenticated session.
- Caller: authenticated user.
- Response shape: success payload with updated workspace/member context.
- Important error states:
  - invalid, expired, or already accepted invite
  - email mismatch for the invite
