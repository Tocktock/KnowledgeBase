from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_user
from app.db.engine import get_db_session
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
)
from app.services.auth import (
    SESSION_HEADER_NAME,
    AuthError,
    AuthForbiddenError,
    AuthNotFoundError,
    AuthRequiredError,
    AuthenticatedUser,
    complete_google_login,
    consume_password_reset,
    create_password_reset_link,
    get_auth_me,
    logout_session,
    POST_AUTH_ACTION_CONNECT_PROVIDER,
    invite_signup_with_password,
    password_login,
    preview_password_reset,
    start_google_login,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _raise_auth_http_error(exc: AuthError) -> None:
    if isinstance(exc, AuthRequiredError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    if isinstance(exc, AuthForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, AuthNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/google/start", response_model=OAuthStartResponse)
async def start_google_auth_route(
    return_to: str = Query(default="/"),
    post_auth_action: str | None = Query(default=None),
    owner_scope: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> OAuthStartResponse:
    try:
        return await start_google_login(
            session,
            return_path=return_to,
            post_auth_action=post_auth_action if post_auth_action == POST_AUTH_ACTION_CONNECT_PROVIDER else None,
            owner_scope=owner_scope,
            provider=provider,
        )
    except AuthError as exc:
        _raise_auth_http_error(exc)


@router.get("/google/callback", response_model=AuthCallbackResponse)
async def google_auth_callback_route(
    state: str,
    code: str,
    session: AsyncSession = Depends(get_db_session),
) -> AuthCallbackResponse:
    try:
        return await complete_google_login(session, state=state, code=code)
    except AuthError as exc:
        _raise_auth_http_error(exc)


@router.post("/password/login", response_model=AuthSessionResponse)
async def password_login_route(
    payload: PasswordLoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthSessionResponse:
    try:
        return await password_login(session, payload)
    except AuthError as exc:
        _raise_auth_http_error(exc)


@router.post("/password/invite-signup", response_model=AuthSessionResponse)
async def password_invite_signup_route(
    payload: PasswordInviteSignupRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthSessionResponse:
    try:
        return await invite_signup_with_password(session, payload)
    except AuthError as exc:
        _raise_auth_http_error(exc)


@router.post("/password/reset-links", response_model=PasswordResetLinkCreateResponse)
async def password_reset_link_route(
    payload: PasswordResetLinkCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> PasswordResetLinkCreateResponse:
    try:
        return await create_password_reset_link(session, auth_user, payload)
    except AuthError as exc:
        _raise_auth_http_error(exc)


@router.get("/password/reset/{token}", response_model=PasswordResetPreviewResponse)
async def password_reset_preview_route(
    token: str,
    session: AsyncSession = Depends(get_db_session),
) -> PasswordResetPreviewResponse:
    try:
        return await preview_password_reset(session, token=token)
    except AuthError as exc:
        _raise_auth_http_error(exc)


@router.post("/password/reset/{token}", response_model=AuthSessionResponse)
async def password_reset_consume_route(
    token: str,
    payload: PasswordResetConsumeRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AuthSessionResponse:
    try:
        return await consume_password_reset(session, token=token, payload=payload)
    except AuthError as exc:
        _raise_auth_http_error(exc)


@router.get("/me", response_model=AuthMeResponse)
async def auth_me_route(
    session: AsyncSession = Depends(get_db_session),
    x_kb_session: Annotated[str | None, Header(alias=SESSION_HEADER_NAME)] = None,
) -> AuthMeResponse:
    return await get_auth_me(session, x_kb_session)


@router.post("/logout")
async def logout_route(
    session: AsyncSession = Depends(get_db_session),
    x_kb_session: Annotated[str | None, Header(alias=SESSION_HEADER_NAME)] = None,
) -> dict[str, bool]:
    await logout_session(session, x_kb_session)
    return {"ok": True}
