from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db_session
from app.services.auth import (
    SESSION_HEADER_NAME,
    AuthForbiddenError,
    AuthRequiredError,
    AuthenticatedUser,
    require_admin_user,
    require_authenticated_user,
    resolve_authenticated_user,
)


async def get_optional_authenticated_user(
    session_token: Annotated[str | None, Header(alias=SESSION_HEADER_NAME)] = None,
    session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser | None:
    return await resolve_authenticated_user(session, session_token)


async def get_authenticated_user(
    session_token: Annotated[str | None, Header(alias=SESSION_HEADER_NAME)] = None,
    session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser:
    try:
        return await require_authenticated_user(session, session_token)
    except AuthRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


async def get_admin_user(
    session_token: Annotated[str | None, Header(alias=SESSION_HEADER_NAME)] = None,
    session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser:
    try:
        return await require_admin_user(session, session_token)
    except AuthRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

