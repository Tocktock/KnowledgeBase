# Workspace Auth Flows

## Login and continuation

1. The user reaches `/login` directly or via an anonymous protected action.
2. The page preserves `return_to`, `post_auth_action`, `owner_scope`, and `provider`.
3. The user signs in through Google or password.
4. The backend returns `AuthCallbackResponse` for Google login and `AuthSessionResponse` for password-based flows.
5. The frontend resumes the requested destination:
   - normal login returns to `return_to`
   - connector login resumes the provider OAuth flow
   - invite and reset flows continue their dedicated completion path

## Invite-based local signup

1. An admin creates a workspace invitation.
2. The invited user opens `/invite/[token]`.
3. If the user already has a session, the invite is accepted immediately.
4. If the user is anonymous, the frontend redirects to `/login?invite_token=...`.
5. The user completes `POST /v1/auth/password/invite-signup`.
6. The backend validates the invite, creates or updates the user password, creates the session, accepts the invite, and returns a redirect target.
7. If the invite token is invalid or missing, `/login` shows a normalized request error message instead of exposing a raw JSON backend payload.

## Admin-generated password reset

1. A workspace owner or admin creates a reset link.
2. The link is copied and delivered outside the product.
3. The recipient opens `/login?reset_token=...` or the direct reset preview route.
4. The backend previews the token, accepts the new password, and returns a fresh session.
5. If the reset token is invalid, expired, or already used, `/login` shows a user-facing error message on the same page.

## Role propagation

1. Session resolution determines the current workspace.
2. Membership role resolves to `owner`, `admin`, or `member`.
3. Frontend navigation and admin surfaces consume that role and the derived `can_manage_workspace_connectors` flag.
4. Other feature specs consume the role decision rather than redefining it.
