from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_code_challenge,
    future_utc,
    generate_code_verifier,
    generate_session_token,
    generate_state_token,
    session_token_hash,
    utcnow,
)
from app.db.models import (
    ConnectorOAuthPurpose,
    ConnectorOAuthState,
    ConnectorOwnerScope,
    PasswordResetToken,
    User,
    UserRole,
    UserRoleKind,
    UserSession,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
    WorkspaceMembershipRole,
)
from app.schemas.auth import (
    AuthCallbackResponse,
    AuthMeResponse,
    AuthSessionResponse,
    OAuthStartResponse,
    PasswordInviteSignupRequest,
    PasswordLoginRequest,
    PasswordResetConsumeRequest,
    PasswordResetLinkCreateRequest,
    PasswordResetLinkCreateResponse,
    PasswordResetPreviewResponse,
    UserSummary,
)
from app.schemas.workspace import WorkspaceSummary

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
LOGIN_SCOPES = ["openid", "email", "profile"]
SESSION_HEADER_NAME = "X-KB-Session"
POST_AUTH_ACTION_CONNECT_PROVIDER = "connect_provider"
WORKSPACE_ADMIN_ROLES = {WorkspaceMembershipRole.owner.value, WorkspaceMembershipRole.admin.value}
PASSWORD_MIN_LENGTH = 8
PASSWORD_HASHER = PasswordHash.recommended()


class AuthError(RuntimeError):
    pass


class AuthForbiddenError(AuthError):
    pass


class AuthRequiredError(AuthError):
    pass


class AuthNotFoundError(AuthError):
    pass


@dataclass(slots=True)
class WorkspaceContext:
    workspace: Workspace | None
    role: str | None


@dataclass(slots=True)
class AuthenticatedUser:
    user: User
    roles: list[str]
    current_workspace_id: UUID | None = None
    current_workspace_slug: str | None = None
    current_workspace_name: str | None = None
    current_workspace_role: str | None = None

    @property
    def is_admin(self) -> bool:
        return UserRoleKind.admin.value in self.roles or self.can_manage_workspace_connectors

    @property
    def can_manage_workspace_connectors(self) -> bool:
        return self.current_workspace_role in WORKSPACE_ADMIN_ROLES


def _app_callback_path(path: str) -> str:
    settings = get_settings()
    return f"{settings.app_public_url.rstrip('/')}{path}"


def _safe_return_path(value: str | None) -> str:
    if not value or not value.startswith("/"):
        return "/connectors"
    return value


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized or "@" not in normalized:
        raise AuthError("A valid email is required.")
    return normalized


def _build_post_auth_redirect(
    *,
    return_path: str = "/connectors",
    post_auth_action: str | None = None,
    owner_scope: str | None = None,
    provider: str | None = None,
) -> str:
    safe_return_path = _safe_return_path(return_path)
    if post_auth_action == POST_AUTH_ACTION_CONNECT_PROVIDER:
        normalized_owner_scope = _normalize_owner_scope(owner_scope)
        normalized_provider = _normalize_connector_provider_path(provider)
        return (
            f"/api/connectors/{normalized_provider}/oauth/start?"
            f"{httpx.QueryParams({'scope': normalized_owner_scope, 'return_to': safe_return_path})}"
        )
    return safe_return_path


def _normalize_owner_scope(value: str | None) -> str:
    if value in {ConnectorOwnerScope.workspace.value, "shared"}:
        return ConnectorOwnerScope.workspace.value
    return ConnectorOwnerScope.personal.value


def _normalize_connector_provider_path(value: str | None) -> str:
    if value == "notion":
        return "notion"
    return "google-drive"


def _ensure_google_oauth_configured() -> None:
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise AuthError("Google OAuth is not configured.")


def _workspace_summary(workspace: Workspace | None) -> WorkspaceSummary | None:
    if workspace is None:
        return None
    return WorkspaceSummary(
        id=workspace.id,
        slug=workspace.slug,
        name=workspace.name,
        is_default=workspace.is_default,
    )


def _validate_password_strength(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise AuthError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.")


def _hash_password(password: str) -> str:
    _validate_password_strength(password)
    return PASSWORD_HASHER.hash(password)


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password, password_hash)
    except Exception:
        return False


def current_workspace_summary(auth_user: AuthenticatedUser) -> WorkspaceSummary | None:
    if auth_user.current_workspace_id is None or auth_user.current_workspace_slug is None or auth_user.current_workspace_name is None:
        return None
    return WorkspaceSummary(
        id=auth_user.current_workspace_id,
        slug=auth_user.current_workspace_slug,
        name=auth_user.current_workspace_name,
        is_default=auth_user.current_workspace_slug == "default",
    )


async def _google_token_exchange(*, code: str, code_verifier: str, redirect_uri: str) -> dict[str, Any]:
    _ensure_google_oauth_configured()
    settings = get_settings()
    payload = {
        "client_id": settings.google_oauth_client_id,
        "client_secret": settings.google_oauth_client_secret,
        "code": code,
        "code_verifier": code_verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=payload)
    if response.status_code >= 400:
        raise AuthError(f"Google token exchange failed: {response.text}")
    return response.json()


async def _google_userinfo(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if response.status_code >= 400:
        raise AuthError(f"Google userinfo lookup failed: {response.text}")
    return response.json()


async def _sync_user_roles(session: AsyncSession, user: User) -> list[str]:
    settings = get_settings()
    result = await session.execute(select(UserRole).where(UserRole.user_id == user.id))
    current_roles = {role.role: role for role in result.scalars().all()}

    if UserRoleKind.member.value not in current_roles:
        session.add(UserRole(user_id=user.id, role=UserRoleKind.member.value))
        current_roles[UserRoleKind.member.value] = UserRole(user_id=user.id, role=UserRoleKind.member.value)

    should_be_admin = user.email.strip().lower() in settings.admin_emails
    if should_be_admin and UserRoleKind.admin.value not in current_roles:
        session.add(UserRole(user_id=user.id, role=UserRoleKind.admin.value))
    if not should_be_admin and UserRoleKind.admin.value in current_roles:
        await session.execute(
            delete(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role == UserRoleKind.admin.value,
            )
        )

    await session.flush()
    result = await session.execute(select(UserRole.role).where(UserRole.user_id == user.id))
    return sorted(str(role) for role in result.scalars().all())


async def _get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return (await session.execute(select(User).where(User.email == _normalize_email(email)))).scalar_one_or_none()


async def _get_default_workspace(session: AsyncSession) -> Workspace | None:
    workspace = (
        await session.execute(
            select(Workspace).where(Workspace.is_default.is_(True)).order_by(Workspace.created_at.asc()).limit(1)
        )
    ).scalar_one_or_none()
    if workspace is not None:
        return workspace
    return (
        await session.execute(select(Workspace).order_by(Workspace.created_at.asc()).limit(1))
    ).scalar_one_or_none()


def _workspace_role_sort_key(role: str | None) -> int:
    if role == WorkspaceMembershipRole.owner.value:
        return 0
    if role == WorkspaceMembershipRole.admin.value:
        return 1
    return 2


async def _resolve_workspace_context_for_user(
    session: AsyncSession,
    user: User,
    current_workspace_id: UUID | None,
) -> WorkspaceContext:
    rows = list(
        (
            await session.execute(
                select(WorkspaceMembership, Workspace)
                .join(Workspace, Workspace.id == WorkspaceMembership.workspace_id)
                .where(WorkspaceMembership.user_id == user.id)
            )
        ).all()
    )

    if not rows and user.email.strip().lower() in get_settings().admin_emails:
        default_workspace = await _get_default_workspace(session)
        if default_workspace is not None:
            membership = WorkspaceMembership(
                workspace_id=default_workspace.id,
                user_id=user.id,
                role=WorkspaceMembershipRole.owner.value,
            )
            session.add(membership)
            await session.flush()
            rows = [(membership, default_workspace)]

    if not rows:
        return WorkspaceContext(workspace=None, role=None)

    rows.sort(key=lambda item: (_workspace_role_sort_key(item[0].role), item[0].created_at))
    if current_workspace_id is not None:
        for membership, workspace in rows:
            if workspace.id == current_workspace_id:
                return WorkspaceContext(workspace=workspace, role=membership.role)

    membership, workspace = rows[0]
    return WorkspaceContext(workspace=workspace, role=membership.role)


async def _create_user_session(
    session: AsyncSession,
    user: User,
    *,
    preferred_workspace_id: UUID | None = None,
) -> tuple[str, list[str], WorkspaceContext]:
    roles = await _sync_user_roles(session, user)
    workspace_context = await _resolve_workspace_context_for_user(session, user, preferred_workspace_id)
    raw_session_token = generate_session_token()
    session.add(
        UserSession(
            user_id=user.id,
            session_token_hash=session_token_hash(raw_session_token),
            current_workspace_id=workspace_context.workspace.id if workspace_context.workspace is not None else None,
            expires_at=future_utc(seconds=get_settings().session_max_age_seconds),
            last_seen_at=utcnow(),
        )
    )
    await session.flush()
    return raw_session_token, roles, workspace_context


def _build_auth_session_response(
    *,
    user: User,
    roles: list[str],
    workspace_context: WorkspaceContext,
    session_token: str,
    redirect_to: str,
) -> AuthSessionResponse:
    return AuthSessionResponse(
        session_token=session_token,
        redirect_to=redirect_to,
        user=user_summary(
            user,
            roles,
            current_workspace=workspace_context.workspace,
            current_workspace_role=workspace_context.role,
        ),
    )


async def _get_workspace_invitation_by_token(session: AsyncSession, invitation_token: str) -> WorkspaceInvitation:
    invitation = (
        await session.execute(
            select(WorkspaceInvitation).where(WorkspaceInvitation.token_hash == session_token_hash(invitation_token))
        )
    ).scalar_one_or_none()
    if invitation is None:
        raise AuthNotFoundError("Workspace invitation not found.")
    if invitation.expires_at < utcnow():
        raise AuthError("Workspace invitation has expired.")
    return invitation


async def _accept_workspace_invitation_for_user(
    session: AsyncSession,
    *,
    user: User,
    invitation_token: str,
    session_token: str,
) -> WorkspaceContext:
    invitation = await _get_workspace_invitation_by_token(session, invitation_token)
    invited_email = invitation.invited_email.strip().lower()
    current_email = user.email.strip().lower()
    if invited_email != current_email:
        raise AuthForbiddenError("Workspace invitation email does not match the signed-in user.")

    membership = (
        await session.execute(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == invitation.workspace_id,
                WorkspaceMembership.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        membership = WorkspaceMembership(
            workspace_id=invitation.workspace_id,
            user_id=user.id,
            role=invitation.role,
        )
        session.add(membership)
        await session.flush()

    if invitation.accepted_at is None:
        invitation.accepted_at = utcnow()
        invitation.accepted_by_user_id = user.id

    workspace = await session.get(Workspace, invitation.workspace_id)
    if workspace is None:
        raise AuthNotFoundError("Workspace not found.")

    await set_current_workspace_for_session(session, session_token, invitation.workspace_id)
    await session.flush()
    return WorkspaceContext(workspace=workspace, role=membership.role)


async def _get_password_reset_token_by_raw_token(session: AsyncSession, token: str) -> PasswordResetToken:
    reset_token = (
        await session.execute(select(PasswordResetToken).where(PasswordResetToken.token_hash == session_token_hash(token)))
    ).scalar_one_or_none()
    if reset_token is None:
        raise AuthNotFoundError("Password reset token not found.")
    return reset_token


def user_summary(
    user: User,
    roles: list[str],
    *,
    current_workspace: Workspace | WorkspaceSummary | None = None,
    current_workspace_role: str | None = None,
) -> UserSummary:
    if isinstance(current_workspace, WorkspaceSummary):
        workspace_summary = current_workspace
    else:
        workspace_summary = _workspace_summary(current_workspace)
    return UserSummary(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        roles=roles,
        is_admin=UserRoleKind.admin.value in roles or current_workspace_role in WORKSPACE_ADMIN_ROLES,
        last_login_at=user.last_login_at,
        current_workspace=workspace_summary,
        current_workspace_role=current_workspace_role,
        can_manage_workspace_connectors=current_workspace_role in WORKSPACE_ADMIN_ROLES,
    )


async def start_google_login(
    session: AsyncSession,
    *,
    return_path: str = "/",
    post_auth_action: str | None = None,
    owner_scope: str | None = None,
    provider: str | None = None,
) -> OAuthStartResponse:
    _ensure_google_oauth_configured()
    redirect_after_login = _build_post_auth_redirect(
        return_path=return_path,
        post_auth_action=post_auth_action,
        owner_scope=owner_scope,
        provider=provider,
    )
    verifier = generate_code_verifier()
    state = generate_state_token()
    oauth_state = ConnectorOAuthState(
        state=state,
        purpose=ConnectorOAuthPurpose.login.value,
        workspace_id=None,
        owner_scope=_normalize_owner_scope(owner_scope),
        owner_user_id=None,
        code_verifier=verifier,
        return_path=redirect_after_login,
        expires_at=future_utc(seconds=get_settings().oauth_state_ttl_seconds),
    )
    session.add(oauth_state)
    await session.commit()

    params = httpx.QueryParams(
        {
            "client_id": get_settings().google_oauth_client_id,
            "redirect_uri": _app_callback_path("/api/auth/google/callback"),
            "response_type": "code",
            "scope": " ".join(LOGIN_SCOPES),
            "state": state,
            "code_challenge": create_code_challenge(verifier),
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    return OAuthStartResponse(authorization_url=f"{GOOGLE_AUTH_URL}?{params}", state=state)


async def complete_google_login(session: AsyncSession, *, state: str, code: str) -> AuthCallbackResponse:
    state_row = (
        await session.execute(
            select(ConnectorOAuthState).where(
                ConnectorOAuthState.state == state,
                ConnectorOAuthState.purpose == ConnectorOAuthPurpose.login.value,
            )
        )
    ).scalar_one_or_none()
    if state_row is None or state_row.expires_at < utcnow():
        raise AuthError("OAuth state is invalid or expired.")

    token_data = await _google_token_exchange(
        code=code,
        code_verifier=state_row.code_verifier,
        redirect_uri=_app_callback_path("/api/auth/google/callback"),
    )
    userinfo = await _google_userinfo(token_data["access_token"])

    google_subject = str(userinfo["sub"])
    normalized_email = _normalize_email(str(userinfo["email"]))
    result = await session.execute(select(User).where(User.google_subject == google_subject))
    user = result.scalar_one_or_none()
    if user is None:
        user = await _get_user_by_email(session, normalized_email)
        if user is not None and user.google_subject and user.google_subject != google_subject:
            raise AuthError("This email is already linked to a different Google account.")
    if user is None:
        user = User(
            google_subject=google_subject,
            email=normalized_email,
            name=str(userinfo.get("name") or userinfo.get("email") or "Google User"),
            avatar_url=userinfo.get("picture"),
            status="active",
            last_login_at=utcnow(),
        )
        session.add(user)
    else:
        user.google_subject = google_subject
        user.email = normalized_email
        user.name = str(userinfo.get("name") or user.name)
        user.avatar_url = userinfo.get("picture")
        user.last_login_at = utcnow()
    await session.flush()

    raw_session_token, roles, workspace_context = await _create_user_session(session, user)
    await session.execute(delete(ConnectorOAuthState).where(ConnectorOAuthState.id == state_row.id))
    await session.commit()
    return AuthCallbackResponse.model_validate(
        _build_auth_session_response(
            user=user,
            roles=roles,
            workspace_context=workspace_context,
            session_token=raw_session_token,
            redirect_to=state_row.return_path or "/",
        ),
    )


async def password_login(session: AsyncSession, payload: PasswordLoginRequest) -> AuthSessionResponse:
    normalized_email = _normalize_email(payload.email)
    user = await _get_user_by_email(session, normalized_email)
    if user is None or not user.password_hash:
        raise AuthRequiredError("Password sign-in is not enabled for this account.")
    if user.status != "active":
        raise AuthForbiddenError("User is disabled.")
    if not _verify_password(payload.password, user.password_hash):
        raise AuthError("Invalid email or password.")

    user.last_login_at = utcnow()
    await session.flush()
    raw_session_token, roles, workspace_context = await _create_user_session(session, user)
    if payload.invite_token:
        workspace_context = await _accept_workspace_invitation_for_user(
            session,
            user=user,
            invitation_token=payload.invite_token,
            session_token=raw_session_token,
        )
    await session.commit()
    return _build_auth_session_response(
        user=user,
        roles=roles,
        workspace_context=workspace_context,
        session_token=raw_session_token,
        redirect_to=_build_post_auth_redirect(
            return_path=payload.return_to,
            post_auth_action=payload.post_auth_action,
            owner_scope=payload.owner_scope,
            provider=payload.provider,
        ),
    )


async def invite_signup_with_password(
    session: AsyncSession,
    payload: PasswordInviteSignupRequest,
) -> AuthSessionResponse:
    invitation = await _get_workspace_invitation_by_token(session, payload.invite_token)
    invited_email = _normalize_email(invitation.invited_email)
    user = await _get_user_by_email(session, invited_email)
    if user is None:
        user = User(
            google_subject=None,
            email=invited_email,
            name=payload.name.strip() or invited_email,
            password_hash=_hash_password(payload.password),
            password_updated_at=utcnow(),
            status="active",
            last_login_at=utcnow(),
        )
        session.add(user)
        await session.flush()
    else:
        if user.status != "active":
            raise AuthForbiddenError("User is disabled.")
        if user.password_hash:
            raise AuthError("Password sign-in is already enabled for this account.")
        user.name = payload.name.strip() or user.name
        user.password_hash = _hash_password(payload.password)
        user.password_updated_at = utcnow()
        user.last_login_at = utcnow()
        await session.flush()

    raw_session_token, roles, workspace_context = await _create_user_session(session, user)
    workspace_context = await _accept_workspace_invitation_for_user(
        session,
        user=user,
        invitation_token=payload.invite_token,
        session_token=raw_session_token,
    )
    await session.commit()
    return _build_auth_session_response(
        user=user,
        roles=roles,
        workspace_context=workspace_context,
        session_token=raw_session_token,
        redirect_to=_build_post_auth_redirect(
            return_path=payload.return_to,
            post_auth_action=payload.post_auth_action,
            owner_scope=payload.owner_scope,
            provider=payload.provider,
        ),
    )


async def create_password_reset_link(
    session: AsyncSession,
    auth_user: AuthenticatedUser,
    payload: PasswordResetLinkCreateRequest,
) -> PasswordResetLinkCreateResponse:
    if not auth_user.can_manage_workspace_connectors or auth_user.current_workspace_id is None:
        raise AuthForbiddenError("Workspace admin permission required.")
    normalized_email = _normalize_email(payload.email)
    user = (
        await session.execute(
            select(User)
            .join(WorkspaceMembership, WorkspaceMembership.user_id == User.id)
            .where(
                WorkspaceMembership.workspace_id == auth_user.current_workspace_id,
                User.email == normalized_email,
            )
        )
    ).scalar_one_or_none()
    if user is None:
        raise AuthNotFoundError("Workspace member not found.")

    raw_token = generate_state_token()
    reset_token = PasswordResetToken(
        user_id=user.id,
        workspace_id=auth_user.current_workspace_id,
        token_hash=session_token_hash(raw_token),
        expires_at=future_utc(seconds=get_settings().password_reset_ttl_seconds),
        created_by_user_id=auth_user.user.id,
    )
    session.add(reset_token)
    await session.commit()
    return PasswordResetLinkCreateResponse(
        email=normalized_email,
        reset_url=f"{get_settings().app_public_url.rstrip('/')}/login?reset_token={raw_token}",
        expires_at=reset_token.expires_at,
    )


async def preview_password_reset(session: AsyncSession, *, token: str) -> PasswordResetPreviewResponse:
    reset_token = await _get_password_reset_token_by_raw_token(session, token)
    user = await session.get(User, reset_token.user_id)
    if user is None:
        raise AuthNotFoundError("Password reset user not found.")
    return PasswordResetPreviewResponse(
        email=user.email,
        name=user.name,
        expires_at=reset_token.expires_at,
        used_at=reset_token.used_at,
        is_expired=reset_token.expires_at < utcnow(),
    )


async def consume_password_reset(
    session: AsyncSession,
    *,
    token: str,
    payload: PasswordResetConsumeRequest,
) -> AuthSessionResponse:
    reset_token = await _get_password_reset_token_by_raw_token(session, token)
    if reset_token.used_at is not None:
        raise AuthError("Password reset token has already been used.")
    if reset_token.expires_at < utcnow():
        raise AuthError("Password reset token has expired.")

    user = await session.get(User, reset_token.user_id)
    if user is None:
        raise AuthNotFoundError("Password reset user not found.")
    if user.status != "active":
        raise AuthForbiddenError("User is disabled.")

    user.password_hash = _hash_password(payload.password)
    user.password_updated_at = utcnow()
    user.last_login_at = utcnow()
    reset_token.used_at = utcnow()
    await session.flush()

    raw_session_token, roles, workspace_context = await _create_user_session(
        session,
        user,
        preferred_workspace_id=reset_token.workspace_id,
    )
    await session.commit()
    return _build_auth_session_response(
        user=user,
        roles=roles,
        workspace_context=workspace_context,
        session_token=raw_session_token,
        redirect_to=_build_post_auth_redirect(
            return_path=payload.return_to,
            post_auth_action=payload.post_auth_action,
            owner_scope=payload.owner_scope,
            provider=payload.provider,
        ),
    )


async def resolve_authenticated_user(session: AsyncSession, session_token: str | None) -> AuthenticatedUser | None:
    if not session_token:
        return None
    hashed = session_token_hash(session_token)
    session_row = (
        await session.execute(select(UserSession).where(UserSession.session_token_hash == hashed))
    ).scalar_one_or_none()
    if session_row is None or session_row.expires_at < utcnow():
        return None
    user = await session.get(User, session_row.user_id)
    if user is None or user.status != "active":
        return None

    session_row.last_seen_at = utcnow()
    roles = sorted(
        str(role)
        for role in (
            await session.execute(select(UserRole.role).where(UserRole.user_id == user.id))
        ).scalars().all()
    )
    workspace_context = await _resolve_workspace_context_for_user(session, user, session_row.current_workspace_id)
    resolved_workspace_id = workspace_context.workspace.id if workspace_context.workspace is not None else None
    if session_row.current_workspace_id != resolved_workspace_id:
        session_row.current_workspace_id = resolved_workspace_id
    await session.commit()
    return AuthenticatedUser(
        user=user,
        roles=roles,
        current_workspace_id=workspace_context.workspace.id if workspace_context.workspace is not None else None,
        current_workspace_slug=workspace_context.workspace.slug if workspace_context.workspace is not None else None,
        current_workspace_name=workspace_context.workspace.name if workspace_context.workspace is not None else None,
        current_workspace_role=workspace_context.role,
    )


async def get_auth_me(session: AsyncSession, session_token: str | None) -> AuthMeResponse:
    auth_user = await resolve_authenticated_user(session, session_token)
    if auth_user is None:
        return AuthMeResponse(authenticated=False, user=None)
    return AuthMeResponse(
        authenticated=True,
        user=user_summary(
            auth_user.user,
            auth_user.roles,
            current_workspace=current_workspace_summary(auth_user),
            current_workspace_role=auth_user.current_workspace_role,
        ),
    )


async def set_current_workspace_for_session(session: AsyncSession, session_token: str | None, workspace_id: UUID | None) -> None:
    if not session_token:
        return
    hashed = session_token_hash(session_token)
    session_row = (
        await session.execute(select(UserSession).where(UserSession.session_token_hash == hashed))
    ).scalar_one_or_none()
    if session_row is None:
        raise AuthRequiredError("Authentication required.")
    session_row.current_workspace_id = workspace_id
    await session.flush()


async def logout_session(session: AsyncSession, session_token: str | None) -> None:
    if not session_token:
        return
    await session.execute(delete(UserSession).where(UserSession.session_token_hash == session_token_hash(session_token)))
    await session.commit()


async def require_authenticated_user(session: AsyncSession, session_token: str | None) -> AuthenticatedUser:
    auth_user = await resolve_authenticated_user(session, session_token)
    if auth_user is None:
        raise AuthRequiredError("Authentication required.")
    return auth_user


async def require_admin_user(session: AsyncSession, session_token: str | None) -> AuthenticatedUser:
    auth_user = await require_authenticated_user(session, session_token)
    if not auth_user.is_admin:
        raise AuthForbiddenError("Admin permission required.")
    return auth_user
