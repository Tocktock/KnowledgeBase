from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UserSummary(BaseModel):
    id: UUID
    email: str
    name: str
    avatar_url: str | None = None
    roles: list[str]
    is_admin: bool
    last_login_at: datetime | None = None


class AuthMeResponse(BaseModel):
    authenticated: bool
    user: UserSummary | None = None


class OAuthStartResponse(BaseModel):
    authorization_url: str
    state: str


class AuthCallbackResponse(BaseModel):
    session_token: str
    redirect_to: str
    user: UserSummary

