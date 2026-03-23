from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db_session
from app.schemas.auth import AuthCallbackResponse, AuthMeResponse, OAuthStartResponse
from app.services.auth import (
    SESSION_HEADER_NAME,
    AuthError,
    complete_google_login,
    get_auth_me,
    logout_session,
    POST_AUTH_ACTION_CONNECT_DRIVE,
    start_google_login,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.get("/google/start", response_model=OAuthStartResponse)
async def start_google_auth_route(
    return_to: str = Query(default="/"),
    post_auth_action: str | None = Query(default=None),
    owner_scope: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> OAuthStartResponse:
    try:
        return await start_google_login(
            session,
            return_path=return_to,
            post_auth_action=post_auth_action if post_auth_action == POST_AUTH_ACTION_CONNECT_DRIVE else None,
            owner_scope=owner_scope,
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/google/callback", response_model=AuthCallbackResponse)
async def google_auth_callback_route(
    state: str,
    code: str,
    session: AsyncSession = Depends(get_db_session),
) -> AuthCallbackResponse:
    try:
        return await complete_google_login(session, state=state, code=code)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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
