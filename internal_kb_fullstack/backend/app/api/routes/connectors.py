from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_authenticated_user, get_optional_authenticated_user
from app.db.engine import get_db_session
from app.schemas.auth import OAuthStartResponse
from app.schemas.connectors import (
    ConnectorBrowseResponse,
    ConnectorConnectionSummary,
    ConnectorListResponse,
    ConnectorOAuthCallbackResponse,
    ConnectorReadinessResponse,
    ConnectorSourceItemSummary,
    ConnectorTargetCreateRequest,
    ConnectorTargetSummary,
    ConnectorTargetUpdateRequest,
    ConnectorUpdateRequest,
)
from app.schemas.jobs import JobSummary
from app.services.auth import AuthenticatedUser
from app.services.connectors import (
    ConnectorError,
    ConnectorForbiddenError,
    ConnectorNotFoundError,
    browse_connection,
    complete_google_drive_oauth,
    create_target,
    delete_connection,
    delete_target,
    get_connection_detail,
    get_connectors_readiness,
    list_connections,
    list_source_items,
    request_target_sync,
    start_google_drive_oauth,
    update_connection,
    update_target,
)

router = APIRouter(prefix="/v1/connectors", tags=["connectors"])


def _raise_connector_http_error(exc: ConnectorError) -> None:
    if isinstance(exc, ConnectorForbiddenError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, ConnectorNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/readiness", response_model=ConnectorReadinessResponse)
async def connectors_readiness_route(
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser | None = Depends(get_optional_authenticated_user),
) -> ConnectorReadinessResponse:
    return await get_connectors_readiness(session, auth_user)


@router.get("", response_model=ConnectorListResponse)
async def list_connections_route(
    scope: str = Query(default="shared"),
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorListResponse:
    return await list_connections(session, auth_user, scope=scope)


@router.get("/{connection_id}", response_model=ConnectorConnectionSummary)
async def get_connection_route(
    connection_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorConnectionSummary:
    try:
        return await get_connection_detail(session, auth_user, connection_id)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.patch("/{connection_id}", response_model=ConnectorConnectionSummary)
async def update_connection_route(
    connection_id: UUID,
    payload: ConnectorUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorConnectionSummary:
    try:
        return await update_connection(session, auth_user, connection_id, payload)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection_route(
    connection_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> None:
    try:
        await delete_connection(session, auth_user, connection_id)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.post("/google-drive/oauth/start", response_model=OAuthStartResponse)
async def start_google_drive_oauth_route(
    owner_scope: str = Query(default="user"),
    return_to: str = Query(default="/connectors"),
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> OAuthStartResponse:
    try:
        payload = await start_google_drive_oauth(
            session,
            auth_user,
            owner_scope=owner_scope,
            return_path=return_to,
        )
    except ConnectorError as exc:
        _raise_connector_http_error(exc)
    return OAuthStartResponse(**payload)


@router.get("/google-drive/oauth/callback", response_model=ConnectorOAuthCallbackResponse)
async def complete_google_drive_oauth_route(
    state: str,
    code: str,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorOAuthCallbackResponse:
    try:
        return await complete_google_drive_oauth(session, auth_user, state=state, code=code)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.get("/{connection_id}/browse", response_model=ConnectorBrowseResponse)
async def browse_connection_route(
    connection_id: UUID,
    kind: str = Query(default="folder"),
    parent_id: str | None = Query(default=None),
    drive_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorBrowseResponse:
    try:
        return await browse_connection(
            session,
            auth_user,
            connection_id,
            kind=kind,
            parent_id=parent_id,
            drive_id=drive_id,
        )
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.post("/{connection_id}/targets", response_model=ConnectorTargetSummary, status_code=status.HTTP_201_CREATED)
async def create_target_route(
    connection_id: UUID,
    payload: ConnectorTargetCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorTargetSummary:
    try:
        return await create_target(session, auth_user, connection_id, payload)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.patch("/{connection_id}/targets/{target_id}", response_model=ConnectorTargetSummary)
async def update_target_route(
    connection_id: UUID,
    target_id: UUID,
    payload: ConnectorTargetUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ConnectorTargetSummary:
    try:
        return await update_target(session, auth_user, connection_id, target_id, payload)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.delete("/{connection_id}/targets/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target_route(
    connection_id: UUID,
    target_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> None:
    try:
        await delete_target(session, auth_user, connection_id, target_id)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.post("/{connection_id}/targets/{target_id}/sync", response_model=JobSummary, status_code=status.HTTP_202_ACCEPTED)
async def request_target_sync_route(
    connection_id: UUID,
    target_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> JobSummary:
    try:
        return await request_target_sync(session, auth_user, connection_id, target_id)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)


@router.get("/{connection_id}/items", response_model=list[ConnectorSourceItemSummary])
async def list_source_items_route(
    connection_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> list[ConnectorSourceItemSummary]:
    try:
        return await list_source_items(session, auth_user, connection_id)
    except ConnectorError as exc:
        _raise_connector_http_error(exc)
