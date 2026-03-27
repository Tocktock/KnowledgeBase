from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_user, get_optional_authenticated_user
from app.db.engine import get_db_session
from app.schemas.workspace import (
    WorkspaceContextResponse,
    WorkspaceInvitationAcceptResponse,
    WorkspaceInvitationCreateRequest,
    WorkspaceInvitationCreateResponse,
    WorkspaceInvitationPreviewResponse,
    WorkspaceInvitationSummary,
    WorkspaceMemberSummary,
    WorkspaceOverviewResponse,
)
from app.services.auth import SESSION_HEADER_NAME, AuthenticatedUser
from app.services.workspace import (
    WorkspaceError,
    WorkspaceForbiddenError,
    WorkspaceNotFoundError,
    accept_workspace_invitation,
    create_workspace_invitation,
    get_current_workspace,
    get_workspace_overview,
    list_workspace_invitations,
    list_workspace_members,
    preview_workspace_invitation,
)

router = APIRouter(prefix="/v1/workspace", tags=["workspace"])


def _raise_workspace_http_error(exc: WorkspaceError) -> None:
    if isinstance(exc, WorkspaceForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, WorkspaceNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/overview", response_model=WorkspaceOverviewResponse)
async def get_workspace_overview_route(
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser | None = Depends(get_optional_authenticated_user),
) -> WorkspaceOverviewResponse:
    try:
        return await get_workspace_overview(session, auth_user)
    except WorkspaceError as exc:
        _raise_workspace_http_error(exc)


@router.get("", response_model=WorkspaceContextResponse)
async def get_workspace_route(
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> WorkspaceContextResponse:
    try:
        return await get_current_workspace(auth_user)
    except WorkspaceError as exc:
        _raise_workspace_http_error(exc)


@router.get("/members", response_model=list[WorkspaceMemberSummary])
async def list_workspace_members_route(
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[WorkspaceMemberSummary]:
    try:
        return await list_workspace_members(session, auth_user)
    except WorkspaceError as exc:
        _raise_workspace_http_error(exc)


@router.get("/invitations/{token}/preview", response_model=WorkspaceInvitationPreviewResponse)
async def preview_workspace_invitation_route(
    token: str,
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceInvitationPreviewResponse:
    try:
        return await preview_workspace_invitation(session, invitation_token=token)
    except WorkspaceError as exc:
        _raise_workspace_http_error(exc)


@router.get("/invitations", response_model=list[WorkspaceInvitationSummary])
async def list_workspace_invitations_route(
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[WorkspaceInvitationSummary]:
    try:
        return await list_workspace_invitations(session, auth_user)
    except WorkspaceError as exc:
        _raise_workspace_http_error(exc)


@router.post("/invitations", response_model=WorkspaceInvitationCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace_invitation_route(
    payload: WorkspaceInvitationCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> WorkspaceInvitationCreateResponse:
    try:
        return await create_workspace_invitation(session, auth_user, payload)
    except WorkspaceError as exc:
        _raise_workspace_http_error(exc)


@router.post("/invitations/{token}/accept", response_model=WorkspaceInvitationAcceptResponse)
async def accept_workspace_invitation_route(
    token: str,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
    x_kb_session: Annotated[str | None, Header(alias=SESSION_HEADER_NAME)] = None,
) -> WorkspaceInvitationAcceptResponse:
    try:
        return await accept_workspace_invitation(
            session,
            auth_user,
            invitation_token=token,
            session_token=x_kb_session,
        )
    except WorkspaceError as exc:
        _raise_workspace_http_error(exc)
