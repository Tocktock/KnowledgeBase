from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
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
    User,
    UserRole,
    UserRoleKind,
    UserSession,
)
from app.schemas.auth import AuthCallbackResponse, AuthMeResponse, OAuthStartResponse, UserSummary

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
LOGIN_SCOPES = ["openid", "email", "profile"]
SESSION_HEADER_NAME = "X-KB-Session"
POST_AUTH_ACTION_CONNECT_DRIVE = "connect_drive"


class AuthError(RuntimeError):
    pass


class AuthForbiddenError(AuthError):
    pass


class AuthRequiredError(AuthError):
    pass


@dataclass(slots=True)
class AuthenticatedUser:
    user: User
    roles: list[str]

    @property
    def is_admin(self) -> bool:
        return UserRoleKind.admin.value in self.roles


def _app_callback_path(path: str) -> str:
    settings = get_settings()
    return f"{settings.app_public_url.rstrip('/')}{path}"


def _safe_return_path(value: str | None) -> str:
    if not value or not value.startswith("/"):
        return "/connectors"
    return value


def _normalize_owner_scope(value: str | None) -> str:
    if value == ConnectorOwnerScope.shared.value:
        return ConnectorOwnerScope.shared.value
    return ConnectorOwnerScope.user.value


def _ensure_google_oauth_configured() -> None:
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise AuthError("Google OAuth is not configured.")


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


def user_summary(user: User, roles: list[str]) -> UserSummary:
    return UserSummary(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        roles=roles,
        is_admin=UserRoleKind.admin.value in roles,
        last_login_at=user.last_login_at,
    )


async def start_google_login(
    session: AsyncSession,
    *,
    return_path: str = "/",
    post_auth_action: str | None = None,
    owner_scope: str | None = None,
) -> OAuthStartResponse:
    _ensure_google_oauth_configured()
    safe_return_path = _safe_return_path(return_path)
    normalized_owner_scope = _normalize_owner_scope(owner_scope)
    redirect_after_login = safe_return_path
    if post_auth_action == POST_AUTH_ACTION_CONNECT_DRIVE:
        redirect_after_login = (
            f"/api/connectors/google-drive/oauth/start?"
            f"{httpx.QueryParams({'scope': normalized_owner_scope, 'return_to': safe_return_path})}"
        )
    verifier = generate_code_verifier()
    state = generate_state_token()
    oauth_state = ConnectorOAuthState(
        state=state,
        purpose=ConnectorOAuthPurpose.login.value,
        owner_scope=normalized_owner_scope,
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

    result = await session.execute(select(User).where(User.google_subject == str(userinfo["sub"])))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            google_subject=str(userinfo["sub"]),
            email=str(userinfo["email"]).lower(),
            name=str(userinfo.get("name") or userinfo.get("email") or "Google User"),
            avatar_url=userinfo.get("picture"),
            status="active",
            last_login_at=utcnow(),
        )
        session.add(user)
        await session.flush()
    else:
        user.email = str(userinfo["email"]).lower()
        user.name = str(userinfo.get("name") or user.name)
        user.avatar_url = userinfo.get("picture")
        user.last_login_at = utcnow()
        await session.flush()

    roles = await _sync_user_roles(session, user)

    raw_session_token = generate_session_token()
    user_session = UserSession(
        user_id=user.id,
        session_token_hash=session_token_hash(raw_session_token),
        expires_at=future_utc(seconds=get_settings().session_max_age_seconds),
        last_seen_at=utcnow(),
    )
    session.add(user_session)
    await session.execute(delete(ConnectorOAuthState).where(ConnectorOAuthState.id == state_row.id))
    await session.commit()
    return AuthCallbackResponse(
        session_token=raw_session_token,
        redirect_to=state_row.return_path or "/",
        user=user_summary(user, roles),
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
    roles = list(
        (
            await session.execute(select(UserRole.role).where(UserRole.user_id == user.id))
        ).scalars().all()
    )
    await session.commit()
    return AuthenticatedUser(user=user, roles=sorted(str(role) for role in roles))


async def get_auth_me(session: AsyncSession, session_token: str | None) -> AuthMeResponse:
    auth_user = await resolve_authenticated_user(session, session_token)
    if auth_user is None:
        return AuthMeResponse(authenticated=False, user=None)
    return AuthMeResponse(authenticated=True, user=user_summary(auth_user.user, auth_user.roles))


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
