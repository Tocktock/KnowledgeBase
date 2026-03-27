from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.workspace import WorkspaceSummary


class UserSummary(BaseModel):
    id: UUID
    email: str
    name: str
    avatar_url: str | None = None
    roles: list[str]
    is_admin: bool
    last_login_at: datetime | None = None
    current_workspace: WorkspaceSummary | None = None
    current_workspace_role: str | None = None
    can_manage_workspace_connectors: bool = False


class AuthMeResponse(BaseModel):
    authenticated: bool
    user: UserSummary | None = None


class OAuthStartResponse(BaseModel):
    authorization_url: str
    state: str


class AuthSessionResponse(BaseModel):
    session_token: str
    redirect_to: str
    user: UserSummary


class AuthCallbackResponse(AuthSessionResponse):
    pass


class PasswordLoginRequest(BaseModel):
    email: str
    password: str
    return_to: str = "/connectors"
    post_auth_action: str | None = None
    owner_scope: str | None = None
    provider: str | None = None
    invite_token: str | None = None


class PasswordInviteSignupRequest(BaseModel):
    invite_token: str
    name: str
    password: str
    return_to: str = "/connectors"
    post_auth_action: str | None = None
    owner_scope: str | None = None
    provider: str | None = None


class PasswordResetLinkCreateRequest(BaseModel):
    email: str


class PasswordResetLinkCreateResponse(BaseModel):
    email: str
    reset_url: str
    expires_at: datetime


class PasswordResetPreviewResponse(BaseModel):
    email: str
    name: str
    expires_at: datetime
    used_at: datetime | None = None
    is_expired: bool


class PasswordResetConsumeRequest(BaseModel):
    password: str
    return_to: str = "/connectors"
    post_auth_action: str | None = None
    owner_scope: str | None = None
    provider: str | None = None
